"""
Database Browser Router
API endpoints for browsing databases and tables with dynamic credentials
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pyodbc
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database-browser", tags=["database-browser"])


class DatabaseConnection(BaseModel):
    server: str
    username: str
    password: str
    port: int = 1433


class DatabaseListResponse(BaseModel):
    databases: List[str]


class TableInfo(BaseModel):
    schema: str
    table: str
    row_count: Optional[int] = None


class TablesListResponse(BaseModel):
    tables: List[TableInfo]


class ColumnsListResponse(BaseModel):
    columns: List[str]


@router.post("/databases", response_model=DatabaseListResponse)
def list_databases(connection: DatabaseConnection):
    """List all databases on a SQL Server"""
    try:
        # Build connection string
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={connection.server},{connection.port};"
            f"UID={connection.username};"
            f"PWD={connection.password};"
            f"TrustServerCertificate=yes;"
        )
        
        # Connect
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Query databases
        cursor.execute("""
            SELECT name 
            FROM sys.databases 
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
            ORDER BY name
        """)
        
        databases = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        logger.info(f"Listed {len(databases)} databases from {connection.server}")
        
        return DatabaseListResponse(databases=databases)
    
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to database: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing databases: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list databases: {str(e)}"
        )


@router.post("/tables", response_model=TablesListResponse)
def list_tables(connection: DatabaseConnection, database: str):
    """List all tables in a specific database"""
    try:
        # Build connection string with specific database
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={connection.server},{connection.port};"
            f"DATABASE={database};"
            f"UID={connection.username};"
            f"PWD={connection.password};"
            f"TrustServerCertificate=yes;"
        )
        
        # Connect
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Query tables
        cursor.execute("""
            SELECT 
                s.name AS schema_name,
                t.name AS table_name,
                p.rows AS row_count
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            LEFT JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
            ORDER BY s.name, t.name
        """)
        
        tables = []
        for row in cursor.fetchall():
            tables.append(TableInfo(
                schema=row[0],
                table=row[1],
                row_count=row[2] if row[2] else 0
            ))
        
        cursor.close()
        conn.close()
        
        logger.info(f"Listed {len(tables)} tables from {database}")
        
        return TablesListResponse(tables=tables)
    
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to database: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tables: {str(e)}"
        )


@router.post("/columns", response_model=ColumnsListResponse)
def list_columns(connection: DatabaseConnection, database: str, schema: str, table: str):
    """List all columns in a specific table"""
    try:
        # Build connection string with specific database
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={connection.server},{connection.port};"
            f"DATABASE={database};"
            f"UID={connection.username};"
            f"PWD={connection.password};"
            f"TrustServerCertificate=yes;"
        )
        
        # Connect
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Query columns
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (schema, table))
        
        columns = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        logger.info(f"Listed {len(columns)} columns from {schema}.{table}")
        
        return ColumnsListResponse(columns=columns)
    
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to database: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing columns: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list columns: {str(e)}"
        )

