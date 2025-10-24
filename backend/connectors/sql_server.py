import pyodbc
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from .base import SourceConnector
import logging

logger = logging.getLogger(__name__)


class SQLServerConnector(SourceConnector):
    """SQL Server source connector with CDC support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.driver = config.get("driver", "{ODBC Driver 18 for SQL Server}")
        self.server = config.get("server")
        self.database = config.get("database")
        self.username = config.get("username")
        self.password = config.get("password")
        self.port = config.get("port", 1433)
        self.trusted_connection = config.get("trusted_connection", False)
        self.trust_server_certificate = config.get("trust_server_certificate", True)
        self.sqlalchemy_engine = None
    
    def connect(self):
        """Establish connection to SQL Server"""
        try:
            if self.trusted_connection:
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server},{self.port};"
                    f"DATABASE={self.database};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'};"
                    f"Connection Timeout=60;"
                    f"Login Timeout=60;"
                )
            else:
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server},{self.port};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                    f"TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'};"
                    f"Connection Timeout=60;"
                    f"Login Timeout=60;"
                )

            self.connection = pyodbc.connect(conn_str, timeout=60)
            
            # Create SQLAlchemy engine for pandas (to avoid warnings)
            try:
                if self.trusted_connection:
                    sqlalchemy_conn_str = (
                        f"mssql+pyodbc://@{self.server}:{self.port}/{self.database}"
                        f"?driver={self.driver.replace('{', '').replace('}', '')}"
                        f"&Trusted_Connection=yes"
                        f"&TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'}"
                    )
                else:
                    params = quote_plus(conn_str)
                    sqlalchemy_conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
                
                self.sqlalchemy_engine = create_engine(
                    sqlalchemy_conn_str, 
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    pool_size=5,  # Keep 5 connections in pool
                    max_overflow=10,  # Allow up to 10 overflow connections
                    pool_timeout=60,  # Wait 60 seconds for connection from pool
                    connect_args={
                        'timeout': 60,  # Connection timeout in seconds
                        'connect_timeout': 60,
                        'login_timeout': 60
                    }
                )
                logger.info(f"SQLAlchemy engine created successfully with connection pooling")
            except Exception as e:
                logger.warning(f"Failed to create SQLAlchemy engine: {str(e)}, will use pyodbc connection")
                self.sqlalchemy_engine = None
            
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
                "details": {
                    "error_type": type(e).__name__,
                    "server": self.server,
                    "database": self.database,
                    "port": self.port
                }
            }
    
    def list_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tables in the database with columns and CDC status"""
        if not self.connection or not self.sqlalchemy_engine:
            self.connect()
        
        logger.info("Starting to list tables...")
        
        # Batch query to get tables (simplified to avoid timeout)
        query = """
            SELECT 
                s.name AS schema_name,
                t.name AS table_name,
                SUM(p.rows) AS row_count,
                CAST(t.is_tracked_by_cdc AS BIT) AS cdc_enabled
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
        """
        
        if schema:
            query += f" WHERE s.name = '{schema}'"
        
        query += """
            GROUP BY s.name, t.name, t.is_tracked_by_cdc
            ORDER BY s.name, t.name
        """
        
        logger.info("Executing table list query...")
        
        # Use SQLAlchemy engine if available, otherwise fall back to pyodbc
        connection_to_use = self.sqlalchemy_engine if self.sqlalchemy_engine else self.connection
        df = pd.read_sql(query, connection_to_use)
        tables = df.to_dict('records')
        
        logger.info(f"Found {len(tables)} tables")
        
        # Convert to proper types and add empty columns array
        for table in tables:
            # Convert cdc_enabled to boolean
            table['cdc_enabled'] = bool(table.get('cdc_enabled', False))
            # Convert row_count to int (handle None)
            table['row_count'] = int(table['row_count']) if table.get('row_count') else 0
            # Add empty columns array for frontend compatibility
            table['columns'] = []
        
        logger.info(f"Successfully processed all {len(tables)} tables")
        return tables
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        if not self.connection or not self.sqlalchemy_engine:
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
        
        # Use SQLAlchemy engine if available, otherwise fall back to pyodbc
        connection_to_use = self.sqlalchemy_engine if self.sqlalchemy_engine else self.connection
        df = pd.read_sql(query, connection_to_use)
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
        
        # Use SQLAlchemy engine if available, otherwise fall back to pyodbc
        connection_to_use = self.sqlalchemy_engine if self.sqlalchemy_engine else self.connection
        df = pd.read_sql(query, connection_to_use)
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
        
        # CDC function names may contain spaces and need square brackets
        # SQL Server creates CDC functions with the capture_instance name as-is
        cdc_function_name = f"fn_cdc_get_all_changes_{capture_instance}"
        
        # Get LSN range
        start_lsn = None
        if from_lsn:
            # Ensure hex string has 0x prefix
            start_lsn_hex = from_lsn if from_lsn.startswith('0x') else f"0x{from_lsn}"
            # Convert hex string back to bytes for comparison
            start_lsn = bytes.fromhex(start_lsn_hex.replace('0x', ''))
        else:
            cursor.execute(f"SELECT sys.fn_cdc_get_min_lsn('{capture_instance}')")
            start_lsn = cursor.fetchone()[0]
            start_lsn_hex = f"0x{start_lsn.hex()}" if start_lsn else None
        
        cursor.execute("SELECT sys.fn_cdc_get_max_lsn()")
        end_lsn = cursor.fetchone()[0]
        
        if not end_lsn:
            # No LSN available
            return pd.DataFrame(), None
        
        end_lsn_hex = f"0x{end_lsn.hex()}"
        
        # Check if there are any changes
        if start_lsn and start_lsn >= end_lsn:
            # No new changes
            return pd.DataFrame(), end_lsn_hex
        
        # Read CDC changes - use brackets for function names with spaces
        # Properly escape function name if it contains spaces or special characters
        query = f"""
            SELECT *
            FROM [cdc].[{cdc_function_name}](
                {start_lsn_hex if start_lsn_hex else end_lsn_hex}, 
                {end_lsn_hex}, 
                'all'
            )
            ORDER BY __$start_lsn
        """
        
        logger.info(f"Executing CDC query for {table_name} using function: {cdc_function_name}")
        
        # Use SQLAlchemy engine if available, otherwise fall back to pyodbc
        connection_to_use = self.sqlalchemy_engine if self.sqlalchemy_engine else self.connection
        df = pd.read_sql(query, connection_to_use)
        
        # Return end_lsn with 0x prefix for next call
        return df, end_lsn_hex

