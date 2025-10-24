from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas
from database import get_db
from services.connector_service import ConnectorService

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.post("/", response_model=schemas.ConnectorResponse)
def create_connector(
    connector: schemas.ConnectorCreate,
    db: Session = Depends(get_db)
):
    """Create a new connector"""
    # Check if connector with same name exists
    existing = ConnectorService.get_connector_by_name(db, connector.name)
    if existing:
        raise HTTPException(status_code=400, detail="Connector with this name already exists")
    
    return ConnectorService.create_connector(db, connector)


@router.get("/", response_model=List[schemas.ConnectorResponse])
def list_connectors(
    connector_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all connectors"""
    return ConnectorService.list_connectors(db, connector_type, skip, limit)


@router.get("/{connector_id}", response_model=schemas.ConnectorResponse)
def get_connector(
    connector_id: int,
    db: Session = Depends(get_db)
):
    """Get connector by ID"""
    connector = ConnectorService.get_connector(db, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector


@router.put("/{connector_id}", response_model=schemas.ConnectorResponse)
def update_connector(
    connector_id: int,
    connector_update: schemas.ConnectorUpdate,
    db: Session = Depends(get_db)
):
    """Update connector"""
    connector = ConnectorService.update_connector(db, connector_id, connector_update)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector


@router.delete("/{connector_id}")
def delete_connector(
    connector_id: int,
    db: Session = Depends(get_db)
):
    """Delete connector"""
    if not ConnectorService.delete_connector(db, connector_id):
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"message": "Connector deleted successfully"}


@router.post("/{connector_id}/test", response_model=schemas.ConnectorTestResponse)
def test_connector(
    connector_id: int,
    db: Session = Depends(get_db)
):
    """Test connector connection"""
    result = ConnectorService.test_connector(db, connector_id)
    if not result.success:
        # Include detailed error information in the HTTP exception
        error_detail = result.message
        if result.details:
            error_detail += f" | Details: {result.details}"
        raise HTTPException(status_code=400, detail=error_detail)
    return result


@router.post("/test-config", response_model=schemas.ConnectorTestResponse)
def test_connector_config(
    connector: schemas.ConnectorCreate,
):
    """Test connector configuration without saving"""
    result = ConnectorService.test_connector_config(connector)
    if not result.success:
        # Include detailed error information in the HTTP exception
        error_detail = result.message
        if result.details:
            error_detail += f" | Details: {result.details}"
        raise HTTPException(status_code=400, detail=error_detail)
    return result


@router.get("/{connector_id}/tables", response_model=List[schemas.TableInfo])
def list_tables(
    connector_id: int,
    db: Session = Depends(get_db)
):
    """List tables from source connector"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Listing tables for connector {connector_id}")
        result = ConnectorService.list_tables(db, connector_id)
        logger.info(f"Successfully listed {len(result)} tables")
        return result
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{connector_id}/tables/{table_name}/columns", response_model=List[str])
def get_table_columns(
    connector_id: int,
    table_name: str,
    schema: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get column names for a specific table from source connector
    
    If schema is not provided, will use database-specific defaults:
    - SQL Server: dbo
    - PostgreSQL: public
    - MySQL: None (uses database name)
    - Oracle: username
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        schema_display = f"{schema}." if schema else ""
        logger.info(f"Getting columns for table {schema_display}{table_name} from connector {connector_id}")
        columns = ConnectorService.get_table_columns(db, connector_id, table_name, schema)
        logger.info(f"Successfully retrieved {len(columns)} columns")
        return columns
    except Exception as e:
        logger.error(f"Error getting columns: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

