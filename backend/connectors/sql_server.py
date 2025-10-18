import pyodbc
import pandas as pd
from typing import List, Dict, Any, Optional
from .base import SourceConnector
import logging

logger = logging.getLogger(__name__)


class SQLServerConnector(SourceConnector):
    """SQL Server source connector with CDC support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.driver = config.get("driver", "{ODBC Driver 17 for SQL Server}")
        self.server = config.get("server")
        self.database = config.get("database")
        self.username = config.get("username")
        self.password = config.get("password")
        self.port = config.get("port", 1433)
        self.trusted_connection = config.get("trusted_connection", False)
    
    def connect(self):
        """Establish connection to SQL Server"""
        try:
            if self.trusted_connection:
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server},{self.port};"
                    f"DATABASE={self.database};"
                    f"Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server},{self.port};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                )
            
            self.connection = pyodbc.connect(conn_str)
            logger.info(f"Connected to SQL Server: {self.server}/{self.database}")
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {str(e)}")
            raise
    
    def disconnect(self):
        """Close SQL Server connection"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from SQL Server")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SQL Server connection"""
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT @@VERSION")
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
    
    def list_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tables in the database"""
        if not self.connection:
            self.connect()
        
        query = """
            SELECT 
                s.name AS schema_name,
                t.name AS table_name,
                p.rows AS row_count
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
        """
        
        if schema:
            query += f" WHERE s.name = '{schema}'"
        
        query += " ORDER BY s.name, t.name"
        
        df = pd.read_sql(query, self.connection)
        return df.to_dict('records')
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        
        query = f"""
            SELECT 
                c.name AS column_name,
                t.name AS data_type,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                c.is_identity
            FROM sys.columns c
            INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
            INNER JOIN sys.tables tb ON c.object_id = tb.object_id
            INNER JOIN sys.schemas s ON tb.schema_id = s.schema_id
            WHERE tb.name = '{table_name}' AND s.name = '{schema}'
            ORDER BY c.column_id
        """
        
        df = pd.read_sql(query, self.connection)
        return df.to_dict('records')
    
    def get_table_row_count(self, table_name: str, schema: Optional[str] = None) -> int:
        """Get total row count for a table"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        query = f"SELECT COUNT(*) as cnt FROM [{schema}].[{table_name}]"
        
        cursor = self.connection.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count
    
    def read_data(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        batch_size: int = 10000,
        offset: int = 0
    ) -> pd.DataFrame:
        """Read data from table in batches"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        
        # Get primary key for stable ordering
        pk_query = f"""
            SELECT c.name
            FROM sys.indexes i
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE i.is_primary_key = 1 
            AND t.name = '{table_name}' 
            AND s.name = '{schema}'
            ORDER BY ic.key_ordinal
        """
        
        cursor = self.connection.cursor()
        cursor.execute(pk_query)
        pk_columns = [row[0] for row in cursor.fetchall()]
        
        order_by = ", ".join(pk_columns) if pk_columns else "1"
        
        query = f"""
            SELECT * FROM [{schema}].[{table_name}]
            ORDER BY {order_by}
            OFFSET {offset} ROWS
            FETCH NEXT {batch_size} ROWS ONLY
        """
        
        df = pd.read_sql(query, self.connection)
        return df
    
    def enable_cdc(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Enable CDC on a table"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        cursor = self.connection.cursor()
        
        try:
            # Check if CDC is enabled on database
            cursor.execute("SELECT is_cdc_enabled FROM sys.databases WHERE name = DB_NAME()")
            db_cdc_enabled = cursor.fetchone()[0]
            
            if not db_cdc_enabled:
                logger.info(f"Enabling CDC on database {self.database}")
                cursor.execute("EXEC sys.sp_cdc_enable_db")
            
            # Enable CDC on table
            logger.info(f"Enabling CDC on table {schema}.{table_name}")
            cursor.execute(f"""
                EXEC sys.sp_cdc_enable_table
                    @source_schema = '{schema}',
                    @source_name = '{table_name}',
                    @role_name = NULL,
                    @supports_net_changes = 1
            """)
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to enable CDC: {str(e)}")
            self.connection.rollback()
            return False
    
    def is_cdc_enabled(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if CDC is enabled on a table"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        
        query = f"""
            SELECT is_tracked_by_cdc
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = '{table_name}' AND s.name = '{schema}'
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        
        return bool(result[0]) if result else False
    
    def read_cdc_changes(
        self, 
        table_name: str,
        from_lsn: Optional[str] = None,
        schema: Optional[str] = None
    ) -> tuple[pd.DataFrame, str]:
        """Read CDC changes. Returns (dataframe, last_lsn)"""
        if not self.connection:
            self.connect()
        
        schema = schema or "dbo"
        cursor = self.connection.cursor()
        
        # Get capture instance name
        cursor.execute(f"""
            SELECT capture_instance
            FROM cdc.change_tables ct
            INNER JOIN sys.tables t ON ct.source_object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = '{table_name}' AND s.name = '{schema}'
        """)
        
        result = cursor.fetchone()
        if not result:
            raise Exception(f"CDC not enabled on table {schema}.{table_name}")
        
        capture_instance = result[0]
        
        # Get LSN range
        if from_lsn:
            start_lsn = from_lsn
        else:
            cursor.execute("SELECT sys.fn_cdc_get_min_lsn(@capture_instance)", capture_instance)
            start_lsn = cursor.fetchone()[0]
        
        cursor.execute("SELECT sys.fn_cdc_get_max_lsn()")
        end_lsn = cursor.fetchone()[0]
        
        if not end_lsn or start_lsn >= end_lsn:
            # No new changes
            return pd.DataFrame(), start_lsn.hex() if start_lsn else None
        
        # Read CDC changes
        query = f"""
            SELECT *
            FROM cdc.fn_cdc_get_all_changes_{capture_instance}(
                {start_lsn}, 
                {end_lsn}, 
                'all'
            )
            ORDER BY __$start_lsn
        """
        
        df = pd.read_sql(query, self.connection)
        
        return df, end_lsn.hex()

