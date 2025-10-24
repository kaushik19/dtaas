import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
import time
import random
from datetime import datetime
from .base import SourceConnector

logger = logging.getLogger(__name__)


class PostgreSQLConnector(SourceConnector):
    """PostgreSQL source connector with CDC support via logical replication"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL connector
        
        Config structure:
        {
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "password",
            "database": "mydb",
            "ssl_mode": "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
        }
        """
        self.config = config
        self.host = config.get("host")
        self.port = config.get("port", 5432)
        self.username = config.get("username")
        self.password = config.get("password")
        self.database = config.get("database")
        self.ssl_mode = config.get("ssl_mode", "prefer")
        self.connection = None
        
    def connect(self):
        """Establish connection to PostgreSQL with retry logic"""
        # Add small random delay to avoid thundering herd problem
        time.sleep(random.uniform(0.1, 0.5))
        
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    database=self.database,
                    sslmode=self.ssl_mode,
                    cursor_factory=RealDictCursor,
                    connect_timeout=120
                )
                logger.info(f"Successfully connected to PostgreSQL: {self.host}:{self.port}/{self.database}")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    jittered_delay = retry_delay + random.uniform(0, retry_delay * 0.5)
                    logger.warning(
                        f"PostgreSQL connection attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                        f"Retrying in {jittered_delay:.2f} seconds..."
                    )
                    time.sleep(jittered_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to connect to PostgreSQL after {max_retries} attempts")
                    raise
    
    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the PostgreSQL connection"""
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()['version']
            cursor.close()
            self.disconnect()
            
            return {
                "success": True,
                "message": "Successfully connected to PostgreSQL",
                "details": {"version": version}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect: {str(e)}"
            }
    
    def list_tables(self, schema: str = "public") -> List[Dict[str, Any]]:
        """List all tables in the specified schema"""
        try:
            cursor = self.connection.cursor()
            
            query = sql.SQL("""
                SELECT 
                    table_schema,
                    table_name,
                    (SELECT COUNT(*) FROM {schema}.{table}) as row_count
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            cursor.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                "ORDER BY table_name",
                (schema,)
            )
            
            tables = []
            for row in cursor.fetchall():
                table_info = {
                    "schema_name": row['table_schema'],
                    "table_name": row['table_name'],
                    "row_count": None,  # Row count can be expensive, get on demand
                    "columns": [],
                    "cdc_enabled": False  # Will check separately
                }
                tables.append(table_info)
            
            cursor.close()
            return tables
            
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise
    
    def get_table_schema(self, table_name: str, schema: str = "public") -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table_name))
            
            columns = []
            for row in cursor.fetchall():
                column_info = {
                    "name": row['column_name'],
                    "type": row['data_type'],
                    "max_length": row['character_maximum_length'],
                    "nullable": row['is_nullable'] == 'YES',
                    "default": row['column_default']
                }
                columns.append(column_info)
            
            cursor.close()
            return columns
            
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            raise
    
    def read_data(
        self, 
        table_name: str, 
        schema: str = "public",
        batch_size: int = 10000, 
        offset: int = 0
    ) -> pd.DataFrame:
        """Read data from table in batches"""
        try:
            query = sql.SQL("""
                SELECT * FROM {schema}.{table}
                ORDER BY (SELECT NULL)
                LIMIT %s OFFSET %s
            """).format(
                schema=sql.Identifier(schema),
                table=sql.Identifier(table_name)
            )
            
            cursor = self.connection.cursor()
            cursor.execute(query, (batch_size, offset))
            
            rows = cursor.fetchall()
            cursor.close()
            
            if rows:
                df = pd.DataFrame([dict(row) for row in rows])
                logger.info(f"Read {len(df)} rows from {schema}.{table_name} (offset: {offset})")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error reading data from {schema}.{table_name}: {e}")
            raise
    
    def get_row_count(self, table_name: str, schema: str = "public") -> int:
        """Get total row count for a table"""
        try:
            query = sql.SQL("SELECT COUNT(*) as count FROM {schema}.{table}").format(
                schema=sql.Identifier(schema),
                table=sql.Identifier(table_name)
            )
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting row count: {e}")
            raise
    
    # CDC-related methods for PostgreSQL
    
    def is_cdc_enabled(self, table_name: str, schema: str = "public") -> bool:
        """Check if CDC (logical replication) is enabled for the table"""
        try:
            cursor = self.connection.cursor()
            
            # Check if table has REPLICA IDENTITY set
            cursor.execute("""
                SELECT relreplident
                FROM pg_class
                WHERE oid = %s::regclass
            """, (f"{schema}.{table_name}",))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                # 'd' = default (primary key), 'f' = full, 'i' = index, 'n' = nothing
                return result['relreplident'] in ('d', 'f', 'i')
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking CDC status: {e}")
            return False
    
    def enable_cdc(self, table_name: str, schema: str = "public") -> bool:
        """
        Enable CDC for a table by setting REPLICA IDENTITY to FULL
        Note: Requires superuser or table owner privileges
        """
        try:
            cursor = self.connection.cursor()
            
            # Set REPLICA IDENTITY to FULL to capture all column values
            query = sql.SQL("ALTER TABLE {schema}.{table} REPLICA IDENTITY FULL").format(
                schema=sql.Identifier(schema),
                table=sql.Identifier(table_name)
            )
            
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Enabled CDC for {schema}.{table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling CDC: {e}")
            self.connection.rollback()
            return False
    
    def read_cdc_changes(
        self,
        table_name: str,
        from_lsn: Optional[str] = None,
        schema: str = "public"
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Read CDC changes using PostgreSQL logical replication
        
        Note: This is a simplified implementation. For production, consider using:
        - wal2json or pgoutput logical decoding plugins
        - Debezium for robust CDC
        - pg_logical_slot_get_changes()
        
        Returns:
            Tuple of (DataFrame with changes, new LSN position)
        """
        try:
            # For now, return empty DataFrame
            # Full implementation would use logical replication slots
            logger.warning("CDC reading for PostgreSQL requires logical replication setup")
            logger.warning("Consider using Debezium or wal2json for production CDC")
            
            return pd.DataFrame(), from_lsn
            
        except Exception as e:
            logger.error(f"Error reading CDC changes: {e}")
            raise
    
    def get_primary_keys(self, table_name: str, schema: str = "public") -> List[str]:
        """Get primary key columns for a table"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                  AND i.indisprimary
            """, (f"{schema}.{table_name}",))
            
            primary_keys = [row['attname'] for row in cursor.fetchall()]
            cursor.close()
            
            return primary_keys
            
        except Exception as e:
            logger.error(f"Error getting primary keys: {e}")
            return []

