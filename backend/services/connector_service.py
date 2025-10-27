from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import models
import schemas
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
    def test_connector_config(connector_data: schemas.ConnectorCreate) -> schemas.ConnectorTestResponse:
        """Test connector configuration without saving to database"""
        try:
            # Create a temporary connector object for testing
            temp_connector = models.Connector(
                name=connector_data.name,
                connector_type=connector_data.connector_type,
                source_type=connector_data.source_type,
                destination_type=connector_data.destination_type,
                connection_config=connector_data.connection_config
            )
            
            # Get connector instance and test
            connector_instance = ConnectorService._get_connector_instance(temp_connector)
            result = connector_instance.test_connection()
            
            return schemas.ConnectorTestResponse(**result)
        except Exception as e:
            logger.error(f"Error testing connector config: {str(e)}")
            return schemas.ConnectorTestResponse(
                success=False,
                message=f"Test failed: {str(e)}",
                details={"error_type": type(e).__name__}
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
            
            # Use the data already returned by list_tables() to avoid hundreds of additional queries
            for table in tables:
                schema_name = table.get('schema_name', 'dbo')
                table_name = table.get('table_name')
                
                # Use columns and cdc_enabled from the table dict (already populated by sql_server.py)
                columns = table.get('columns', [])
                cdc_enabled = table.get('cdc_enabled', False)
                
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
    def _get_default_schema(db_connector: models.Connector) -> Optional[str]:
        """Get default schema based on database type"""
        if db_connector.source_type == "sql_server":
            return "dbo"
        elif db_connector.source_type == "postgresql":
            return "public"
        elif db_connector.source_type == "mysql":
            return None  # MySQL doesn't use schemas the same way
        elif db_connector.source_type == "oracle":
            # For Oracle, use the username as schema if not specified
            return db_connector.connection_config.get("username", "").upper()
        return None
    
    @staticmethod
    def get_table_columns(db: Session, connector_id: int, table_name: str, schema: Optional[str] = None) -> List[str]:
        """Get column names for a specific table from a source connector"""
        db_connector = ConnectorService.get_connector(db, connector_id)
        if not db_connector or db_connector.connector_type != "source":
            raise ValueError("Connector not found or is not a source connector")
        
        try:
            connector = ConnectorService._get_connector_instance(db_connector)
            connector.connect()
            
            # Use provided schema or get default based on database type
            if schema is None:
                schema = ConnectorService._get_default_schema(db_connector)
            
            # Get table schema (which includes column info)
            schema_info = connector.get_table_schema(table_name=table_name, schema=schema)
            
            # Extract just column names (handle different response formats)
            if schema_info and len(schema_info) > 0:
                # Try different possible column name keys
                first_col = schema_info[0]
                if 'column_name' in first_col:
                    columns = [col['column_name'] for col in schema_info]
                elif 'name' in first_col:
                    columns = [col['name'] for col in schema_info]
                else:
                    columns = [col.get('column_name', col.get('name', '')) for col in schema_info]
            else:
                columns = []
            
            connector.disconnect()
            schema_display = f"{schema}." if schema else ""
            logger.info(f"Retrieved {len(columns)} columns for table {schema_display}{table_name}")
            return columns
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {str(e)}")
            raise
    
    @staticmethod
    def _get_connector_class(connector_type_str: str):
        """Get connector class based on type string (with lazy imports)"""
        try:
            if connector_type_str == "sql_server":
                from connectors import SQLServerConnector
                return SQLServerConnector
            elif connector_type_str == "postgresql":
                from connectors import PostgreSQLConnector
                return PostgreSQLConnector
            elif connector_type_str == "mysql":
                from connectors import MySQLConnector
                return MySQLConnector
            elif connector_type_str == "oracle":
                try:
                    from connectors import OracleConnector
                    return OracleConnector
                except ImportError as e:
                    logger.error(f"Oracle connector not available: {e}")
                    raise ValueError(
                        "Oracle connector requires cx_Oracle package which is not installed. "
                        "Please install it with: pip install cx-Oracle"
                    )
            elif connector_type_str == "snowflake":
                try:
                    from connectors import SnowflakeConnector
                    return SnowflakeConnector
                except ImportError as e:
                    logger.error(f"Snowflake connector not available: {e}")
                    raise ValueError(
                        "Snowflake connector requires snowflake-connector-python package which is not installed. "
                        "Please install it with: pip install snowflake-connector-python"
                    )
            elif connector_type_str == "s3":
                from connectors import S3Connector
                return S3Connector
            else:
                raise ValueError(f"Unknown connector type: {connector_type_str}")
        except ImportError as e:
            logger.error(f"Failed to import connector for type {connector_type_str}: {e}")
            raise ValueError(f"Connector type '{connector_type_str}' is not available: {str(e)}")
    
    @staticmethod
    def _get_connector_instance_from_config(config: dict):
        """Create connector instance from configuration dict (for parallel processing)"""
        connector_type = config.get('source_type') or config.get('destination_type')
        connector_class = ConnectorService._get_connector_class(connector_type)
        return connector_class(config.get('connection_config', {}))
    
    @staticmethod
    def _get_connector_instance(db_connector: models.Connector):
        """Get connector instance based on type"""
        if db_connector.connector_type == "source":
            if db_connector.source_type == "sql_server":
                return SQLServerConnector(db_connector.connection_config)
            elif db_connector.source_type == "postgresql":
                return PostgreSQLConnector(db_connector.connection_config)
            elif db_connector.source_type == "mysql":
                return MySQLConnector(db_connector.connection_config)
            elif db_connector.source_type == "oracle":
                return OracleConnector(db_connector.connection_config)
        
        elif db_connector.connector_type == "destination":
            if db_connector.destination_type == "snowflake":
                return SnowflakeConnector(db_connector.connection_config)
            elif db_connector.destination_type == "s3":
                return S3Connector(db_connector.connection_config)
        
        raise ValueError(f"Unsupported connector type: {db_connector.connector_type}/{db_connector.source_type or db_connector.destination_type}")

