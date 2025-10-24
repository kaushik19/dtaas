import mysql.connector
from mysql.connector import Error
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from .base import SourceConnector

logger = logging.getLogger(__name__)


class MySQLConnector(SourceConnector):
    """MySQL source connector with CDC support via binlog"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MySQL connector
        
        Config structure:
        {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "mydb",
            "ssl_ca": None,  # Optional: path to CA certificate
            "ssl_disabled": False
        }
        """
        self.config = config
        self.host = config.get("host")
        self.port = config.get("port", 3306)
        self.username = config.get("username")
        self.password = config.get("password")
        self.database = config.get("database")
        self.ssl_ca = config.get("ssl_ca")
        self.ssl_disabled = config.get("ssl_disabled", False)
        self.connection = None
        
    def connect(self):
        """Establish connection to MySQL with retry logic"""
        import time
        import random
        
        # Add small random delay to avoid thundering herd problem
        time.sleep(random.uniform(0.1, 0.5))
        
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                conn_params = {
                    "host": self.host,
                    "port": self.port,
                    "user": self.username,
                    "password": self.password,
                    "database": self.database,
                    "connection_timeout": 120
                }
                
                if not self.ssl_disabled:
                    if self.ssl_ca:
                        conn_params["ssl_ca"] = self.ssl_ca
                    conn_params["ssl_disabled"] = False
                else:
                    conn_params["ssl_disabled"] = True
                
                self.connection = mysql.connector.connect(**conn_params)
                logger.info(f"Successfully connected to MySQL: {self.host}:{self.port}/{self.database}")
                break
            except Error as e:
                if attempt < max_retries - 1:
                    jittered_delay = retry_delay + random.uniform(0, retry_delay * 0.5)
                    logger.warning(
                        f"MySQL connection attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                        f"Retrying in {jittered_delay:.2f} seconds..."
                    )
                    time.sleep(jittered_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to connect to MySQL after {max_retries} attempts")
                    raise
    
    def disconnect(self):
        """Close MySQL connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the MySQL connection"""
        try:
            self.connect()
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            version = result['version']
            cursor.close()
            self.disconnect()
            
            return {
                "success": True,
                "message": "Successfully connected to MySQL",
                "details": {"version": version}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect: {str(e)}"
            }
    
    def list_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tables in the database"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    TABLE_SCHEMA as table_schema,
                    TABLE_NAME as table_name,
                    TABLE_ROWS as row_count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (self.database,))
            
            tables = []
            for row in cursor.fetchall():
                table_info = {
                    "schema_name": row['table_schema'],
                    "table_name": row['table_name'],
                    "row_count": row['row_count'],
                    "columns": [],
                    "cdc_enabled": False  # Will check separately
                }
                tables.append(table_info)
            
            cursor.close()
            return tables
            
        except Error as e:
            logger.error(f"Error listing tables: {e}")
            raise
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    COLUMN_NAME as column_name,
                    DATA_TYPE as data_type,
                    CHARACTER_MAXIMUM_LENGTH as max_length,
                    IS_NULLABLE as is_nullable,
                    COLUMN_DEFAULT as column_default,
                    COLUMN_KEY as column_key
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (self.database, table_name))
            
            columns = []
            for row in cursor.fetchall():
                column_info = {
                    "name": row['column_name'],
                    "type": row['data_type'],
                    "max_length": row['max_length'],
                    "nullable": row['is_nullable'] == 'YES',
                    "default": row['column_default'],
                    "is_primary_key": row['column_key'] == 'PRI'
                }
                columns.append(column_info)
            
            cursor.close()
            return columns
            
        except Error as e:
            logger.error(f"Error getting table schema: {e}")
            raise
    
    def read_data(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        batch_size: int = 10000, 
        offset: int = 0
    ) -> pd.DataFrame:
        """Read data from table in batches"""
        try:
            query = f"""
                SELECT * FROM `{self.database}`.`{table_name}`
                LIMIT {batch_size} OFFSET {offset}
            """
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query)
            
            rows = cursor.fetchall()
            cursor.close()
            
            if rows:
                df = pd.DataFrame(rows)
                logger.info(f"Read {len(df)} rows from {self.database}.{table_name} (offset: {offset})")
                return df
            else:
                return pd.DataFrame()
                
        except Error as e:
            logger.error(f"Error reading data from {self.database}.{table_name}: {e}")
            raise
    
    def get_row_count(self, table_name: str, schema: Optional[str] = None) -> int:
        """Get total row count for a table"""
        try:
            query = f"SELECT COUNT(*) as count FROM `{self.database}`.`{table_name}`"
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            return result['count'] if result else 0
            
        except Error as e:
            logger.error(f"Error getting row count: {e}")
            raise
    
    # CDC-related methods for MySQL
    
    def is_cdc_enabled(self, table_name: str, schema: Optional[str] = None) -> bool:
        """
        Check if binlog is enabled (prerequisite for CDC)
        MySQL CDC requires binlog to be enabled at server level
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Check if binlog is enabled
            cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
            result = cursor.fetchone()
            
            binlog_enabled = result and result['Value'] == 'ON'
            
            cursor.close()
            return binlog_enabled
            
        except Error as e:
            logger.error(f"Error checking CDC status: {e}")
            return False
    
    def enable_cdc(self, table_name: str, schema: Optional[str] = None) -> bool:
        """
        Enable CDC for MySQL (binlog)
        Note: Binlog must be enabled at MySQL server level in my.cnf
        This method just checks if it's enabled
        """
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Check if binlog is enabled
            cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
            result = cursor.fetchone()
            
            if result and result['Value'] == 'ON':
                logger.info("MySQL binlog is already enabled")
                cursor.close()
                return True
            else:
                logger.warning("MySQL binlog is not enabled. Enable it in my.cnf with log_bin=ON")
                cursor.close()
                return False
            
        except Error as e:
            logger.error(f"Error enabling CDC: {e}")
            return False
    
    def read_cdc_changes(
        self,
        table_name: str,
        from_lsn: Optional[str] = None,
        schema: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Read CDC changes using MySQL binlog
        
        Note: This is a simplified implementation. For production, use:
        - mysql-replication library
        - Debezium for robust CDC
        - Maxwell's daemon
        
        Returns:
            Tuple of (DataFrame with changes, new binlog position)
        """
        try:
            # For now, return empty DataFrame
            # Full implementation would use python-mysql-replication library
            logger.warning("CDC reading for MySQL requires binlog parsing")
            logger.warning("Consider using Debezium or Maxwell for production CDC")
            
            return pd.DataFrame(), from_lsn
            
        except Error as e:
            logger.error(f"Error reading CDC changes: {e}")
            raise
    
    def get_primary_keys(self, table_name: str, schema: Optional[str] = None) -> List[str]:
        """Get primary key columns for a table"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND CONSTRAINT_NAME = 'PRIMARY'
                ORDER BY ORDINAL_POSITION
            """, (self.database, table_name))
            
            primary_keys = [row['COLUMN_NAME'] for row in cursor.fetchall()]
            cursor.close()
            
            return primary_keys
            
        except Error as e:
            logger.error(f"Error getting primary keys: {e}")
            return []
    
    def get_binlog_position(self) -> Dict[str, Any]:
        """Get current binlog position"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SHOW MASTER STATUS")
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "file": result['File'],
                    "position": result['Position']
                }
            return {}
            
        except Error as e:
            logger.error(f"Error getting binlog position: {e}")
            return {}

