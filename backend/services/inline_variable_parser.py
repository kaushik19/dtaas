"""
Inline Variable Parser
Parses and resolves inline variable definitions like:
$CustomerID = SELECT Id from dbo.Tenants.Customers where Name = $DatabaseName
"""
import re
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class InlineVariableParser:
    """Parses inline variable definitions and creates variable configs"""
    
    @staticmethod
    def parse_inline_definition(definition: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Parse inline variable definition
        
        Syntax: $VariableName = EXPRESSION
        
        Returns: (variable_name, variable_type, config)
        
        Examples:
        - $CustomerID = SELECT Id FROM dbo.Customers WHERE Name = $DatabaseName
        - $Environment = production
        - $FullPath = $Environment/$CustomerID
        """
        # Remove leading/trailing whitespace
        definition = definition.strip()
        
        # Check if it matches the pattern $VAR = VALUE
        match = re.match(r'\$(\w+)\s*=\s*(.+)', definition, re.IGNORECASE)
        
        if not match:
            raise ValueError(f"Invalid inline variable definition: {definition}")
        
        var_name = match.group(1)
        expression = match.group(2).strip()
        
        # Determine variable type based on expression
        if expression.upper().startswith('SELECT '):
            # It's a database query
            variable_type = 'db_query'
            config = InlineVariableParser._parse_sql_query(expression)
        
        elif InlineVariableParser._contains_variables(expression):
            # It contains other variables - it's an expression
            variable_type = 'expression'
            config = {'expression': expression}
        
        else:
            # It's a static value
            variable_type = 'static'
            config = {'value': expression}
        
        logger.info(f"Parsed inline variable: ${var_name} ({variable_type})")
        return var_name, variable_type, config
    
    @staticmethod
    def _parse_sql_query(query: str) -> Dict[str, Any]:
        """
        Parse a SQL query into structured config
        
        Example:
        SELECT Id FROM dbo.Customers WHERE Name = $DatabaseName
        →
        {
            "schema": "dbo",
            "table": "Customers",
            "column": "Id",
            "where_conditions": [
                {"field": "Name", "operator": "=", "value": "$DatabaseName"}
            ]
        }
        """
        # Simple SQL parser for SELECT queries
        # Format: SELECT column FROM [schema.]table WHERE conditions
        
        query = query.strip()
        
        # Extract SELECT column
        select_match = re.search(r'SELECT\s+(\w+)', query, re.IGNORECASE)
        if not select_match:
            # If we can't parse it, return as raw query
            return {'raw_query': query}
        
        column = select_match.group(1)
        
        # Extract FROM [schema.]table
        from_match = re.search(r'FROM\s+(?:(\w+)\.)?(\w+)', query, re.IGNORECASE)
        if not from_match:
            return {'raw_query': query}
        
        schema = from_match.group(1) or 'dbo'
        table = from_match.group(2)
        
        # Extract WHERE conditions
        where_conditions = []
        where_match = re.search(r'WHERE\s+(.+)', query, re.IGNORECASE)
        
        if where_match:
            where_clause = where_match.group(1).strip()
            
            # Parse simple conditions (field = value, field LIKE value, etc.)
            # Split by AND (simple parser)
            conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
            
            for condition in conditions:
                # Parse: field operator value
                cond_match = re.match(
                    r'(\w+)\s*(=|!=|>|<|>=|<=|LIKE|IN)\s*(.+)',
                    condition.strip(),
                    re.IGNORECASE
                )
                
                if cond_match:
                    field = cond_match.group(1)
                    operator = cond_match.group(2).upper()
                    value = cond_match.group(3).strip()
                    
                    # Remove quotes if present
                    if value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    elif value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    
                    where_conditions.append({
                        'field': field,
                        'operator': operator,
                        'value': value
                    })
        
        return {
            'schema': schema,
            'table': table,
            'column': column,
            'where_conditions': where_conditions
        }
    
    @staticmethod
    def _contains_variables(text: str) -> bool:
        """Check if text contains variable references ($VariableName)"""
        return bool(re.search(r'\$\w+', text))
    
    @staticmethod
    def extract_all_variables(text: str) -> list:
        """Extract all variable names from text (including inline definitions)"""
        # Find all $VariableName patterns
        return re.findall(r'\$(\w+)', text)
    
    @staticmethod
    def parse_path_template_with_inline_vars(path_template: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse a path template that may contain inline variable definitions
        
        Example:
        "data/$CustomerID/tables" where $CustomerID = SELECT Id FROM Customers
        
        Returns: (cleaned_template, inline_variables_dict)
        """
        inline_vars = {}
        
        # Look for inline definitions (pattern: "where $VAR = EXPRESSION")
        # This allows users to define variables inline in the path template
        pattern = r'where\s+\$(\w+)\s*=\s*([^,\s]+(?:\s+[^,\s]+)*)'
        
        matches = re.finditer(pattern, path_template, re.IGNORECASE)
        
        for match in matches:
            var_name = match.group(1)
            expression = match.group(2).strip()
            
            # Determine type and create config
            if expression.upper().startswith('SELECT'):
                var_type = 'db_query'
                config = InlineVariableParser._parse_sql_query(expression)
            elif InlineVariableParser._contains_variables(expression):
                var_type = 'expression'
                config = {'expression': expression}
            else:
                var_type = 'static'
                config = {'value': expression}
            
            inline_vars[var_name] = {
                'type': var_type,
                'config': config
            }
        
        # Remove inline definitions from template
        cleaned_template = re.sub(pattern, '', path_template, flags=re.IGNORECASE).strip()
        
        return cleaned_template, inline_vars


class ContextVariables:
    """Built-in context variables available automatically"""
    
    # Variables from task/connector context
    CONTEXT_VARS = {
        'sourceDatabaseName': 'source_connector.database',
        'tableName': 'current_table',
        'sourceTableName': 'current_table',
        'timestamp': 'datetime.now()',
        'date': 'datetime.now().date()',
        'uuid': 'uuid4()',
        'taskName': 'task.name',
        'taskId': 'task.id',
        'connectorName': 'source_connector.name',
    }
    
    @staticmethod
    def get_context_value(var_name: str, context: Dict[str, Any]) -> Any:
        """
        Get value of a context variable (case-insensitive)
        
        Context can contain:
        - source_connector: The source connector object
        - task: The current task object
        - current_table: Current table name
        """
        # Normalize to lowercase for comparison
        var_lower = var_name.lower()
        
        if var_lower == 'sourcedatabasename':
            return context.get('source_connector', {}).get('database', '')
        
        elif var_lower in ['tablename', 'sourcetablename']:
            return context.get('current_table', '')
        
        elif var_lower == 'taskname':
            return context.get('task', {}).get('name', '')
        
        elif var_lower == 'taskid':
            return context.get('task', {}).get('id', '')
        
        elif var_lower == 'connectorname':
            return context.get('source_connector', {}).get('name', '')
        
        # For timestamp/date/uuid, these are handled by VariableResolver
        
        return None
    
    @staticmethod
    def is_context_variable(var_name: str) -> bool:
        """Check if a variable is a built-in context variable (case-insensitive)"""
        var_lower = var_name.lower()
        context_vars_lower = {k.lower(): k for k in ContextVariables.CONTEXT_VARS.keys()}
        return var_lower in context_vars_lower

