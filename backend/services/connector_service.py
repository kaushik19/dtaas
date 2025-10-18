from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import models
import schemas
from connectors import SQLServerConnector, SnowflakeConnector, S3Connector
import logging

logger = logging.getLogger(__name__)


class ConnectorService:
    """Service for managing connectors"""
    
    @staticmethod
    def create_connector(db: Session, connector: schemas.ConnectorCreate) -> models.Connector:
        """Create a new connector"""
        db_connector = models.Connector(
            name=connector.name,
            description=connector.description,
            connector_type=connector.connector_type,
            source_type=connector.source_type,
            destination_type=connector.destination_type,
            connection_config=connector.connection_config,
        )
        
        db.add(db_connector)
        db.commit()
        db.refresh(db_connector)
        
        logger.info(f"Created connector: {connector.name}")
        return db_connector
    
    @staticmethod
    def get_connector(db: Session, connector_id: int) -> Optional[models.Connector]:
        """Get connector by ID"""
        return db.query(models.Connector).filter(models.Connector.id == connector_id).first()
    
    @staticmethod
    def get_connector_by_name(db: Session, name: str) -> Optional[models.Connector]:
        """Get connector by name"""
        return db.query(models.Connector).filter(models.Connector.name == name).first()
    
    @staticmethod
    def list_connectors(
        db: Session,
        connector_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[models.Connector]:
        """List all connectors"""
        query = db.query(models.Connector)
        
        if connector_type:
            query = query.filter(models.Connector.connector_type == connector_type)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_connector(
        db: Session,
        connector_id: int,
        connector_update: schemas.ConnectorUpdate
    ) -> Optional[models.Connector]:
        """Update connector"""
        db_connector = ConnectorService.get_connector(db, connector_id)
        if not db_connector:
            return None
        
        update_data = connector_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_connector, field, value)
        
        db.commit()
        db.refresh(db_connector)
        
        logger.info(f"Updated connector: {db_connector.name}")
        return db_connector
    
    @staticmethod
    def delete_connector(db: Session, connector_id: int) -> bool:
        """Delete connector"""
        db_connector = ConnectorService.get_connector(db, connector_id)
        if not db_connector:
            return False
        
        db.delete(db_connector)
        db.commit()
        
        logger.info(f"Deleted connector: {db_connector.name}")
        return True
    
    @staticmethod
    def test_connector(db: Session, connector_id: int) -> schemas.ConnectorTestResponse:
        """Test connector connection"""
        db_connector = ConnectorService.get_connector(db, connector_id)
        if not db_connector:
            return schemas.ConnectorTestResponse(
                success=False,
                message="Connector not found"
            )
        
        try:
            connector_instance = ConnectorService._get_connector_instance(db_connector)
            result = connector_instance.test_connection()
            
            # Update test status
            from datetime import datetime
            db_connector.last_tested_at = datetime.utcnow()
            db_connector.test_status = "success" if result["success"] else "failed"
            db.commit()
            
            return schemas.ConnectorTestResponse(**result)
        except Exception as e:
            logger.error(f"Error testing connector: {str(e)}")
            return schemas.ConnectorTestResponse(
                success=False,
                message=f"Test failed: {str(e)}"
            )
    
    @staticmethod
    def list_tables(db: Session, connector_id: int) -> List[schemas.TableInfo]:
        """List tables from source connector"""
        db_connector = ConnectorService.get_connector(db, connector_id)
        if not db_connector or db_connector.connector_type != "source":
            return []
        
        try:
            connector = ConnectorService._get_connector_instance(db_connector)
            connector.connect()
            
            tables = connector.list_tables()
            result = []
            
            for table in tables:
                schema_name = table.get('schema_name', 'dbo')
                table_name = table.get('table_name')
                
                # Get column info
                columns = connector.get_table_schema(table_name, schema_name)
                
                # Check CDC status
                cdc_enabled = connector.is_cdc_enabled(table_name, schema_name)
                
                result.append(schemas.TableInfo(
                    schema_name=schema_name,
                    table_name=table_name,
                    row_count=table.get('row_count'),
                    columns=columns,
                    cdc_enabled=cdc_enabled
                ))
            
            connector.disconnect()
            return result
        except Exception as e:
            logger.error(f"Error listing tables: {str(e)}")
            raise
    
    @staticmethod
    def _get_connector_instance(db_connector: models.Connector):
        """Get connector instance based on type"""
        if db_connector.connector_type == "source":
            if db_connector.source_type == "sql_server":
                return SQLServerConnector(db_connector.connection_config)
        
        elif db_connector.connector_type == "destination":
            if db_connector.destination_type == "snowflake":
                return SnowflakeConnector(db_connector.connection_config)
            elif db_connector.destination_type == "s3":
                return S3Connector(db_connector.connection_config)
        
        raise ValueError(f"Unsupported connector type: {db_connector.connector_type}/{db_connector.source_type or db_connector.destination_type}")

