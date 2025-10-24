"""
Variable Resolver Service
Resolves global variables at runtime with context awareness and inline definitions
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import models
import logging
import re
from datetime import datetime
import uuid as uuid_module
from services.inline_variable_parser import InlineVariableParser, ContextVariables

logger = logging.getLogger(__name__)


class VariableResolver:
    """Resolves global variables and built-in variables"""
    
    def __init__(self, db: Session, source_connector=None, database_name: str = "", table_name: str = "", task=None, inline_vars: Dict[str, Any] = None):
        self.db = db
        self.source_connector = source_connector
        self.database_name = database_name
        self.table_name = table_name
        self.task = task
        self.inline_vars = inline_vars or {}  # Inline variable definitions
        self._cache = {}  # Cache resolved variables
        self._global_vars = None  # Lazy load global variables
        
        # Build context for context variables
        self.context = {
            'source_connector': {
                'database': database_name,
                'name': getattr(source_connector, 'name', '') if source_connector else ''
            },
            'current_table': table_name,
            'task': {
                'name': getattr(task, 'name', '') if task else '',
                'id': getattr(task, 'id', '') if task else ''
            }
        }
    
    def resolve(self, template: str) -> str:
        """
        Resolve all variables in a template string
        
        Supports:
        - Built-in variables: $timestamp, $date, $uuid, $tableName, $databaseName
        - Custom global variables: $myCustomVar
        """
        if not template:
            return template
        
        # Find all variables in the template
        variables = re.findall(r'\$(\w+)', template)
        
        resolved = template
        for var_name in variables:
            var_placeholder = f"${var_name}"
            
            if var_placeholder in self._cache:
                # Use cached value
                value = self._cache[var_placeholder]
            else:
                # Resolve the variable
                value = self._resolve_variable(var_name)
                # Cache it (except for dynamic ones like uuid, timestamp)
                if var_name not in ['uuid', 'timestamp']:
                    self._cache[var_placeholder] = value
            
            resolved = resolved.replace(var_placeholder, str(value))
        
        return resolved
    
    def _resolve_variable(self, var_name: str) -> str:
        """
        Resolve a single variable
        
        Resolution order:
        1. Built-in dynamic variables (timestamp, uuid)
        2. Context variables (databaseName, tableName, taskName, etc.)
        3. Inline variables (user-defined inline)
        4. Global variables (from database)
        """
        # 1. Built-in dynamic variables (always fresh)
        if var_name == "timestamp":
            return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        elif var_name == "date":
            return datetime.utcnow().strftime("%Y%m%d")
        
        elif var_name == "uuid":
            return str(uuid_module.uuid4())
        
        # 2. Context variables (from task/connector context)
        elif ContextVariables.is_context_variable(var_name):
            value = ContextVariables.get_context_value(var_name, self.context)
            if value is not None:
                return str(value)
        
        # 3. Inline variables (user-defined inline)
        elif var_name in self.inline_vars:
            return self._resolve_inline_variable(var_name)
        
        # 4. Global variables (from database)
        else:
            return self._resolve_global_variable(var_name)
    
    def _resolve_inline_variable(self, var_name: str) -> str:
        """Resolve an inline variable definition"""
        var_config = self.inline_vars[var_name]
        
        try:
            if var_config['type'] == 'static':
                return self._resolve_static(var_config)
            
            elif var_config['type'] == 'db_query':
                return self._resolve_db_query(var_config)
            
            elif var_config['type'] == 'expression':
                return self._resolve_expression(var_config)
            
            else:
                logger.error(f"Unknown inline variable type: {var_config['type']}")
                return "unknown"
        
        except Exception as e:
            logger.error(f"Error resolving inline variable '{var_name}': {str(e)}")
            return "unknown"
    
    def _resolve_global_variable(self, var_name: str) -> str:
        """Resolve a custom global variable"""
        # Lazy load global variables
        if self._global_vars is None:
            self._load_global_variables()
        
        if var_name not in self._global_vars:
            logger.error(f"Variable '{var_name}' not found in global variables")
            logger.error(f"Available variables: {list(self._global_vars.keys())}")
            logger.error(f"Using 'unknown' as fallback")
            return "unknown"
        
        var_config = self._global_vars[var_name]
        
        try:
            if var_config['type'] == 'static':
                return self._resolve_static(var_config)
            
            elif var_config['type'] == 'db_query':
                return self._resolve_db_query(var_config)
            
            elif var_config['type'] == 'expression':
                return self._resolve_expression(var_config)
            
            else:
                logger.error(f"Unknown variable type: {var_config['type']}")
                return "unknown"
        
        except Exception as e:
            logger.error(f"Error resolving variable '{var_name}': {str(e)}")
            return "unknown"
    
    def _load_global_variables(self):
        """Load all active global variables from database"""
        self._global_vars = {}
        
        variables = self.db.query(models.GlobalVariable).filter(
            models.GlobalVariable.is_active == True
        ).all()
        
        for var in variables:
            self._global_vars[var.name] = {
                'type': var.variable_type,
                'config': var.config,
                'description': var.description
            }
        
        logger.info(f"Loaded {len(self._global_vars)} global variables: {list(self._global_vars.keys())}")
    
    def _resolve_static(self, var_config: Dict[str, Any]) -> str:
        """Resolve a static variable"""
        return str(var_config['config'].get('value', ''))
    
    def _resolve_db_query(self, var_config: Dict[str, Any]) -> str:
        """Resolve a DB query variable"""
        config = var_config['config']
        
        logger.info(f"=== Resolving DB query variable ===")
        logger.info(f"Config: {config}")
        logger.info(f"Source connector available: {self.source_connector is not None}")
        logger.info(f"Database name for context: {self.database_name}")
        logger.info(f"Table name for context: {self.table_name}")
        
        # Check if config has its own connection details (for querying different database)
        has_own_connection = all(k in config for k in ['server', 'username', 'password', 'database'])
        
        if has_own_connection:
            # Use the connection details from config (e.g., Tenants database)
            logger.info(f"Using dedicated connection to database: {config.get('database')}")
            connection = self._create_temp_connection(config)
            if not connection:
                logger.error("Failed to create connection for global variable")
                return "unknown"
        else:
            # Use source connector's connection (backward compatibility)
            if not self.source_connector:
                logger.error("No source connector available for DB query variable - cannot execute query")
                return "unknown"
            
            if not hasattr(self.source_connector, 'connection') or not self.source_connector.connection:
                logger.error("Source connector has no active connection")
                return "unknown"
            
            connection = self.source_connector.connection
        
        # Build query
        schema = config.get('schema', 'dbo')
        table = config.get('table')
        column = config.get('column')
        where_conditions = config.get('where_conditions', [])
        
        if not table or not column:
            logger.error("DB query variable missing table or column")
            return "unknown"
        
        # Build safe query with parameterization
        query = self._build_safe_query(schema, table, column, where_conditions)
        params = self._build_query_params(where_conditions)
        
        # Execute query
        temp_connection_created = has_own_connection
        try:
            cursor = connection.cursor()
            
            logger.info(f"Executing query: {query}")
            logger.info(f"With parameters: {params}")
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                logger.info(f"DB query returned: {result[0]}")
                return str(result[0])
            else:
                logger.warning(f"DB query returned no results for variable")
                return "unknown"
        
        except Exception as e:
            logger.error(f"Error executing DB query: {str(e)}")
            return "unknown"
        
        finally:
            # Close temporary connection if we created one
            if temp_connection_created and connection:
                try:
                    connection.close()
                    logger.info("Closed temporary database connection")
                except:
                    pass
    
    def _resolve_expression(self, var_config: Dict[str, Any]) -> str:
        """Resolve an expression variable"""
        expression = var_config['config'].get('expression', '')
        
        # Recursively resolve any variables in the expression
        resolved = self.resolve(expression)
        
        # Evaluate simple expressions (e.g., concatenation)
        # For safety, we don't use eval() - only support simple string operations
        return resolved
    
    def _build_safe_query(
        self,
        schema: str,
        table: str,
        column: str,
        where_conditions: list
    ) -> str:
        """Build a safe SQL query with escaped identifiers"""
        # Escape identifiers
        schema_safe = self._escape_identifier(schema)
        table_safe = self._escape_identifier(table)
        column_safe = self._escape_identifier(column)
        
        query = f"SELECT {column_safe} FROM {schema_safe}.{table_safe}"
        
        if where_conditions:
            where_clauses = []
            for condition in where_conditions:
                field = condition.get('field')
                operator = condition.get('operator', '=')
                
                # Validate operator
                allowed_operators = ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"]
                if operator not in allowed_operators:
                    operator = "="
                
                field_safe = self._escape_identifier(field)
                
                if operator == "IN":
                    # Handle IN operator
                    value = condition.get('value', '')
                    values = [v.strip() for v in value.split(",")]
                    placeholders = ",".join(["?" for _ in values])
                    where_clauses.append(f"{field_safe} IN ({placeholders})")
                else:
                    where_clauses.append(f"{field_safe} {operator} ?")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        return query
    
    def _build_query_params(self, where_conditions: list) -> list:
        """Build query parameters from WHERE conditions"""
        params = []
        
        for condition in where_conditions:
            operator = condition.get('operator', '=')
            value = condition.get('value', '')
            
            # Replace built-in placeholders (support multiple formats)
            if value.startswith('$'):
                # Resolve the variable
                logger.info(f"Resolving WHERE variable: {value}")
                resolved_value = self._resolve_where_variable(value)
                logger.info(f"  Resolved to: {resolved_value}")
                value = resolved_value
            
            if operator == "IN":
                # Split comma-separated values
                values = [v.strip() for v in value.split(",")]
                params.extend(values)
            else:
                params.append(value)
        
        return params
    
    def _resolve_where_variable(self, var_placeholder: str) -> str:
        """
        Resolve variables in WHERE clause values
        
        Supports:
        - $databaseName, $database, $Database → Current database name
        - $tableName, $table, $Table → Current table name
        - $serverName, $server, $Server → Server from connector
        - Any other global variable
        """ 
        # Remove $ prefix
        var_name = var_placeholder[1:] if var_placeholder.startswith('$') else var_placeholder
        
        # Normalize to lowercase for comparison
        var_lower = var_name.lower()
        
        logger.info(f"  _resolve_where_variable: var_name='{var_name}', var_lower='{var_lower}'")
        logger.info(f"  Available database_name: '{self.database_name}'")
        
        # Built-in context variables (case-insensitive)
        # Use specific name to avoid confusion with destination database or other variables
        if var_lower == 'sourcedatabasename':
            result = self.database_name if self.database_name else 'unknown'
            logger.info(f"  Resolved '{var_name}' to source database: '{result}'")
            return result
        
        elif var_lower in ['tablename', 'sourcetablename']:
            result = self.table_name if self.table_name else 'unknown'
            logger.info(f"  Resolved '{var_name}' to table: '{result}'")
            return result
        
        elif var_lower in ['server', 'servername']:
            if self.source_connector and hasattr(self.source_connector, 'server'):
                return str(self.source_connector.server)
            return 'unknown'
        
        elif var_lower in ['port']:
            if self.source_connector and hasattr(self.source_connector, 'port'):
                return str(self.source_connector.port)
            return 'unknown'
        
        # Try to resolve as global variable (use original case)
        else:
            return self._resolve_global_variable(var_name)
    
    def _escape_identifier(self, identifier: str) -> str:
        """Escape SQL identifier to prevent SQL injection"""
        # Remove dangerous characters
        safe_identifier = re.sub(r'[^\w]', '', identifier)
        # Wrap in square brackets for SQL Server
        return f"[{safe_identifier}]"
    
    def _create_temp_connection(self, config: Dict[str, Any]):
        """
        Create a temporary database connection for querying a different database
        Used when global variable needs to query a master/tenants database
        """
        try:
            import pyodbc
            
            server = config.get('server')
            database = config.get('database')
            username = config.get('username')
            password = config.get('password')
            port = config.get('port', 1433)
            
            logger.info(f"Creating temporary connection to {server}/{database}")
            
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={server},{port};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=10;"
            )
            
            connection = pyodbc.connect(conn_str)
            logger.info(f"Successfully connected to {database}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create temporary connection: {str(e)}")
            return None

