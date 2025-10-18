import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
from typing import List, Dict, Any, Optional
from .base import DestinationConnector
import logging

logger = logging.getLogger(__name__)


class SnowflakeConnector(DestinationConnector):
    """Snowflake destination connector with bulk load support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account = config.get("account")
        self.user = config.get("user")
        self.password = config.get("password")
        self.warehouse = config.get("warehouse")
        self.database = config.get("database")
        self.schema = config.get("schema", "PUBLIC")
        self.role = config.get("role")
    
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            conn_params = {
                "account": self.account,
                "user": self.user,
                "password": self.password,
                "warehouse": self.warehouse,
                "database": self.database,
                "schema": self.schema,
            }
            
            if self.role:
                conn_params["role"] = self.role
            
            self.connection = snowflake.connector.connect(**conn_params)
            logger.info(f"Connected to Snowflake: {self.account}/{self.database}")
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    def disconnect(self):
        """Close Snowflake connection"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Snowflake connection"""
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            self.disconnect()
            
            return {
                "success": True,
                "message": "Connection successful",
                "details": {"version": version}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": None
            }
    
    def write_data(
        self,
        data: pd.DataFrame,
        table_name: str,
        mode: str = "append",
        schema: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Write data to Snowflake using bulk load via staging"""
        if not self.connection:
            self.connect()
        
        target_schema = schema or self.schema
        
        try:
            cursor = self.connection.cursor()
            
            # Create table if it doesn't exist
            if not self.table_exists(table_name, target_schema):
                self.create_table_from_dataframe(data, table_name, target_schema)
            
            # Handle overwrite mode
            if mode == "overwrite":
                cursor.execute(f"TRUNCATE TABLE {target_schema}.{table_name}")
            
            # Use write_pandas for efficient bulk load
            # This internally uses Snowflake's PUT and COPY commands
            success, nchunks, nrows, _ = write_pandas(
                conn=self.connection,
                df=data,
                table_name=table_name,
                schema=target_schema,
                auto_create_table=False,
                overwrite=(mode == "overwrite"),
                quote_identifiers=False
            )
            
            logger.info(f"Loaded {nrows} rows to {target_schema}.{table_name}")
            
            return {
                "success": success,
                "rows_written": nrows,
                "chunks": nchunks
            }
        except Exception as e:
            logger.error(f"Failed to write data to Snowflake: {str(e)}")
            raise
    
    def create_table_from_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema: Optional[str] = None
    ):
        """Create table from DataFrame schema"""
        target_schema = schema or self.schema
        
        # Map pandas dtypes to Snowflake types
        type_mapping = {
            'int64': 'NUMBER',
            'int32': 'NUMBER',
            'float64': 'FLOAT',
            'float32': 'FLOAT',
            'object': 'VARCHAR(16777216)',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP',
            'datetime64[ns, UTC]': 'TIMESTAMP_TZ',
        }
        
        columns = []
        for col_name, dtype in df.dtypes.items():
            sf_type = type_mapping.get(str(dtype), 'VARCHAR(16777216)')
            columns.append(f'"{col_name}" {sf_type}')
        
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {target_schema}.{table_name} (
                {', '.join(columns)}
            )
        """
        
        cursor = self.connection.cursor()
        cursor.execute(create_sql)
        logger.info(f"Created table {target_schema}.{table_name}")
    
    def create_table_if_not_exists(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """Create table if it doesn't exist"""
        target_schema = schema or self.schema
        
        if self.table_exists(table_name, target_schema):
            return False
        
        # Map SQL Server types to Snowflake types
        type_mapping = {
            'int': 'NUMBER',
            'bigint': 'NUMBER',
            'smallint': 'NUMBER',
            'tinyint': 'NUMBER',
            'decimal': 'NUMBER',
            'numeric': 'NUMBER',
            'float': 'FLOAT',
            'real': 'FLOAT',
            'varchar': 'VARCHAR',
            'nvarchar': 'VARCHAR',
            'char': 'CHAR',
            'nchar': 'CHAR',
            'text': 'VARCHAR',
            'ntext': 'VARCHAR',
            'datetime': 'TIMESTAMP',
            'datetime2': 'TIMESTAMP',
            'date': 'DATE',
            'time': 'TIME',
            'bit': 'BOOLEAN',
        }
        
        column_defs = []
        for col in columns:
            col_name = col['column_name']
            data_type = col['data_type'].lower()
            sf_type = type_mapping.get(data_type, 'VARCHAR(16777216)')
            
            # Handle precision and scale
            if data_type in ['decimal', 'numeric'] and col.get('precision'):
                sf_type = f"NUMBER({col['precision']}, {col.get('scale', 0)})"
            elif data_type in ['varchar', 'nvarchar'] and col.get('max_length') and col['max_length'] > 0:
                length = col['max_length']
                if length == -1:  # MAX
                    length = 16777216
                sf_type = f"VARCHAR({length})"
            
            nullable = "" if col.get('is_nullable') else " NOT NULL"
            column_defs.append(f'"{col_name}" {sf_type}{nullable}')
        
        create_sql = f"""
            CREATE TABLE {target_schema}.{table_name} (
                {', '.join(column_defs)}
            )
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_sql)
            logger.info(f"Created table {target_schema}.{table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table: {str(e)}")
            return False
    
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if table exists"""
        if not self.connection:
            self.connect()
        
        target_schema = schema or self.schema
        
        query = f"""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{target_schema}'
            AND TABLE_NAME = '{table_name.upper()}'
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count > 0
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get table schema"""
        if not self.connection:
            self.connect()
        
        target_schema = schema or self.schema
        
        query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{target_schema}'
            AND TABLE_NAME = '{table_name.upper()}'
            ORDER BY ORDINAL_POSITION
        """
        
        df = pd.read_sql(query, self.connection)
        return df.to_dict('records')
    
    def handle_schema_drift(
        self,
        table_name: str,
        new_columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """Handle schema changes by adding new columns"""
        if not self.connection:
            self.connect()
        
        target_schema = schema or self.schema
        
        try:
            cursor = self.connection.cursor()
            
            for col in new_columns:
                col_name = col['column_name']
                data_type = col.get('snowflake_type', 'VARCHAR(16777216)')
                
                alter_sql = f"""
                    ALTER TABLE {target_schema}.{table_name}
                    ADD COLUMN "{col_name}" {data_type}
                """
                
                cursor.execute(alter_sql)
                logger.info(f"Added column {col_name} to {target_schema}.{table_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to handle schema drift: {str(e)}")
            return False

