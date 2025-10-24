import cx_Oracle
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from .base import SourceConnector

logger = logging.getLogger(__name__)


class OracleConnector(SourceConnector):
    """Oracle source connector with CDC support via LogMiner"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Oracle connector
        
        Config structure:
        {
            "host": "localhost",
            "port": 1521,
            "username": "system",
            "password": "password",
            "service_name": "ORCL",  # or "sid": "XE"
            "connection_type": "service_name"  # or "sid"
        }
        """
        self.config = config
        self.host = config.get("host")
        self.port = config.get("port", 1521)
        self.username = config.get("username")
        self.password = config.get("password")
        self.service_name = config.get("service_name")
        self.sid = config.get("sid")
        self.connection_type = config.get("connection_type", "service_name")
        self.connection = None
        
    def connect(self):
        """Establish connection to Oracle"""
        try:
            # Build DSN based on connection type
            if self.connection_type == "service_name":
                dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
            else:  # sid
                dsn = cx_Oracle.makedsn(self.host, self.port, sid=self.sid)
            
            self.connection = cx_Oracle.connect(
                user=self.username,
                password=self.password,
                dsn=dsn,
                encoding="UTF-8"
            )
            
            logger.info(f"Successfully connected to Oracle: {self.host}:{self.port}")
        except cx_Oracle.Error as e:
            logger.error(f"Failed to connect to Oracle: {e}")
            raise
    
    def disconnect(self):
        """Close Oracle connection"""
        if self.connection:
            self.connection.close()
            logger.info("Oracle connection closed")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Oracle connection"""
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM v$version WHERE banner LIKE 'Oracle%'")
            result = cursor.fetchone()
            version = result[0] if result else "Unknown"
            cursor.close()
            self.disconnect()
            
            return {
                "success": True,
                "message": "Successfully connected to Oracle",
                "details": {"version": version}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect: {str(e)}"
            }
    
    def list_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tables in the schema"""
        try:
            cursor = self.connection.cursor()
            
            # If no schema specified, use the current user's schema
            if not schema:
                schema = self.username.upper()
            
            cursor.execute("""
                SELECT 
                    owner as schema_name,
                    table_name,
                    num_rows as row_count
                FROM all_tables
                WHERE owner = :schema
                ORDER BY table_name
            """, schema=schema)
            
            tables = []
            for row in cursor.fetchall():
                table_info = {
                    "schema_name": row[0],
                    "table_name": row[1],
                    "row_count": row[2],
                    "columns": [],
                    "cdc_enabled": False  # Will check separately
                }
                tables.append(table_info)
            
            cursor.close()
            return tables
            
        except cx_Oracle.Error as e:
            logger.error(f"Error listing tables: {e}")
            raise
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        try:
            cursor = self.connection.cursor()
            
            if not schema:
                schema = self.username.upper()
            
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    data_length,
                    nullable,
                    data_default
                FROM all_tab_columns
                WHERE owner = :schema AND table_name = :table_name
                ORDER BY column_id
            """, schema=schema, table_name=table_name.upper())
            
            columns = []
            for row in cursor.fetchall():
                column_info = {
                    "name": row[0],
                    "type": row[1],
                    "max_length": row[2],
                    "nullable": row[3] == 'Y',
                    "default": row[4]
                }
                columns.append(column_info)
            
            cursor.close()
            return columns
            
        except cx_Oracle.Error as e:
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
            if not schema:
                schema = self.username.upper()
            
            # Oracle uses ROWNUM for pagination, but it's not offset-based
            # Use OFFSET/FETCH for Oracle 12c+
            query = f"""
                SELECT * FROM {schema}.{table_name}
                ORDER BY 1
                OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY
            """
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            # Fetch rows
            rows = cursor.fetchall()
            cursor.close()
            
            if rows:
                df = pd.DataFrame(rows, columns=column_names)
                logger.info(f"Read {len(df)} rows from {schema}.{table_name} (offset: {offset})")
                return df
            else:
                return pd.DataFrame()
                
        except cx_Oracle.Error as e:
            logger.error(f"Error reading data from {schema}.{table_name}: {e}")
            raise
    
    def get_row_count(self, table_name: str, schema: Optional[str] = None) -> int:
        """Get total row count for a table"""
        try:
            if not schema:
                schema = self.username.upper()
            
            query = f"SELECT COUNT(*) FROM {schema}.{table_name}"
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            return result[0] if result else 0
            
        except cx_Oracle.Error as e:
            logger.error(f"Error getting row count: {e}")
            raise
    
    # CDC-related methods for Oracle
    
    def is_cdc_enabled(self, table_name: str, schema: Optional[str] = None) -> bool:
        """
        Check if supplemental logging is enabled for the table
        (prerequisite for LogMiner CDC)
        """
        try:
            if not schema:
                schema = self.username.upper()
            
            cursor = self.connection.cursor()
            
            # Check if supplemental logging is enabled at database level
            cursor.execute("SELECT supplemental_log_data_min FROM v$database")
            result = cursor.fetchone()
            db_logging = result and result[0] == 'YES'
            
            # Check if supplemental logging is enabled for the table
            cursor.execute("""
                SELECT COUNT(*)
                FROM all_log_groups
                WHERE owner = :schema AND table_name = :table_name
            """, schema=schema, table_name=table_name.upper())
            
            table_logging = cursor.fetchone()[0] > 0
            
            cursor.close()
            return db_logging and table_logging
            
        except cx_Oracle.Error as e:
            logger.error(f"Error checking CDC status: {e}")
            return False
    
    def enable_cdc(self, table_name: str, schema: Optional[str] = None) -> bool:
        """
        Enable CDC for a table by enabling supplemental logging
        Note: Requires DBA privileges
        """
        try:
            if not schema:
                schema = self.username.upper()
            
            cursor = self.connection.cursor()
            
            # Enable supplemental logging at database level (if not already)
            try:
                cursor.execute("ALTER DATABASE ADD SUPPLEMENTAL LOG DATA")
            except cx_Oracle.Error:
                pass  # Might already be enabled
            
            # Enable supplemental logging for the table
            cursor.execute(f"""
                ALTER TABLE {schema}.{table_name}
                ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS
            """)
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Enabled CDC for {schema}.{table_name}")
            return True
            
        except cx_Oracle.Error as e:
            logger.error(f"Error enabling CDC: {e}")
            self.connection.rollback()
            return False
    
    def read_cdc_changes(
        self,
        table_name: str,
        from_lsn: Optional[str] = None,
        schema: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Read CDC changes using Oracle LogMiner
        
        Note: This is a simplified implementation. For production, use:
        - Oracle GoldenGate
        - Debezium for robust CDC
        - Oracle LogMiner API
        
        Returns:
            Tuple of (DataFrame with changes, new SCN)
        """
        try:
            # For now, return empty DataFrame
            # Full implementation would use LogMiner
            logger.warning("CDC reading for Oracle requires LogMiner or GoldenGate setup")
            logger.warning("Consider using Debezium or GoldenGate for production CDC")
            
            return pd.DataFrame(), from_lsn
            
        except cx_Oracle.Error as e:
            logger.error(f"Error reading CDC changes: {e}")
            raise
    
    def get_primary_keys(self, table_name: str, schema: Optional[str] = None) -> List[str]:
        """Get primary key columns for a table"""
        try:
            if not schema:
                schema = self.username.upper()
            
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT cols.column_name
                FROM all_constraints cons
                JOIN all_cons_columns cols 
                  ON cons.constraint_name = cols.constraint_name
                  AND cons.owner = cols.owner
                WHERE cons.constraint_type = 'P'
                  AND cons.owner = :schema
                  AND cons.table_name = :table_name
                ORDER BY cols.position
            """, schema=schema, table_name=table_name.upper())
            
            primary_keys = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            return primary_keys
            
        except cx_Oracle.Error as e:
            logger.error(f"Error getting primary keys: {e}")
            return []
    
    def get_current_scn(self) -> str:
        """Get current System Change Number (SCN) for CDC"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT current_scn FROM v$database")
            result = cursor.fetchone()
            cursor.close()
            
            return str(result[0]) if result else None
            
        except cx_Oracle.Error as e:
            logger.error(f"Error getting current SCN: {e}")
            return None

