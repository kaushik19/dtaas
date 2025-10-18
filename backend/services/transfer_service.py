from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import models
from services.connector_service import ConnectorService
from transformations import TransformationEngine
import pandas as pd
import logging
from datetime import datetime
import sys

logger = logging.getLogger(__name__)


class TransferService:
    """Service for handling data transfers"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def execute_full_load(
        self,
        task: models.Task,
        execution: models.TaskExecution,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Execute full load data transfer"""
        try:
            # Get connectors
            source_connector = ConnectorService._get_connector_instance(task.source_connector)
            dest_connector = ConnectorService._get_connector_instance(task.destination_connector)
            
            source_connector.connect()
            dest_connector.connect()
            
            total_tables = len(task.source_tables)
            completed_tables = 0
            total_rows_transferred = 0
            total_data_size_mb = 0.0
            
            for table_name in task.source_tables:
                try:
                    logger.info(f"Starting transfer for table: {table_name}")
                    
                    # Parse schema.table if provided
                    schema_name = None
                    if '.' in table_name:
                        schema_name, table_name = table_name.split('.', 1)
                    
                    # Get table row count
                    total_rows = source_connector.get_table_row_count(table_name, schema_name)
                    
                    # Get source schema
                    source_schema = source_connector.get_table_schema(table_name, schema_name)
                    
                    # Create destination table if needed
                    dest_table_name = task.table_mappings.get(table_name, table_name) if task.table_mappings else table_name
                    
                    if not dest_connector.table_exists(dest_table_name):
                        dest_connector.create_table_if_not_exists(
                            dest_table_name,
                            source_schema
                        )
                    elif task.handle_schema_drift:
                        # Check for schema drift
                        self._handle_schema_drift(
                            source_schema,
                            dest_connector,
                            dest_table_name
                        )
                    
                    # Transfer data in batches
                    offset = 0
                    batch_size = task.batch_rows
                    rows_transferred = 0
                    
                    while offset < total_rows:
                        # Read batch from source
                        batch_df = source_connector.read_data(
                            table_name,
                            schema_name,
                            batch_size,
                            offset
                        )
                        
                        if batch_df.empty:
                            break
                        
                        # Apply transformations
                        if task.transformations:
                            batch_df = TransformationEngine.apply_transformations(
                                batch_df,
                                task.transformations
                            )
                        
                        # Calculate batch size in MB
                        batch_size_mb = sys.getsizeof(batch_df) / (1024 * 1024)
                        
                        # Write to destination
                        write_result = dest_connector.write_data(
                            batch_df,
                            dest_table_name,
                            mode="append",
                            file_format=task.s3_file_format
                        )
                        
                        rows_transferred += len(batch_df)
                        total_rows_transferred += len(batch_df)
                        total_data_size_mb += batch_size_mb
                        offset += batch_size
                        
                        # Update progress
                        table_progress = (rows_transferred / total_rows) * 100 if total_rows > 0 else 100
                        overall_progress = ((completed_tables + (rows_transferred / total_rows)) / total_tables) * 100
                        
                        # Call progress callback
                        if progress_callback:
                            progress_callback(
                                execution_id=execution.id,
                                progress_percent=overall_progress,
                                processed_rows=total_rows_transferred,
                                table_name=table_name,
                                table_progress=table_progress
                            )
                        
                        logger.info(f"Transferred {rows_transferred}/{total_rows} rows for {table_name}")
                    
                    completed_tables += 1
                    logger.info(f"Completed transfer for table: {table_name}")
                    
                except Exception as e:
                    logger.error(f"Error transferring table {table_name}: {str(e)}")
                    raise
            
            source_connector.disconnect()
            dest_connector.disconnect()
            
            return {
                "status": "success",
                "total_rows": total_rows_transferred,
                "data_size_mb": total_data_size_mb,
                "tables_transferred": completed_tables
            }
            
        except Exception as e:
            logger.error(f"Full load execution failed: {str(e)}")
            raise
    
    def execute_cdc_sync(
        self,
        task: models.Task,
        execution: models.TaskExecution,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Execute CDC synchronization"""
        try:
            source_connector = ConnectorService._get_connector_instance(task.source_connector)
            dest_connector = ConnectorService._get_connector_instance(task.destination_connector)
            
            source_connector.connect()
            dest_connector.connect()
            
            total_changes = 0
            total_data_size_mb = 0.0
            cdc_enabled_tables = task.cdc_enabled_tables or {}
            
            for table_name in task.source_tables:
                try:
                    schema_name = None
                    if '.' in table_name:
                        schema_name, table_name = table_name.split('.', 1)
                    
                    # Check if CDC is enabled
                    if not source_connector.is_cdc_enabled(table_name, schema_name):
                        logger.warning(f"CDC not enabled for {table_name}, enabling now...")
                        if not source_connector.enable_cdc(table_name, schema_name):
                            logger.error(f"Failed to enable CDC for {table_name}")
                            continue
                        cdc_enabled_tables[table_name] = True
                    
                    # Get last LSN for this table
                    last_lsn = cdc_enabled_tables.get(f"{table_name}_last_lsn")
                    
                    # Read CDC changes
                    changes_df, new_lsn = source_connector.read_cdc_changes(
                        table_name,
                        from_lsn=last_lsn,
                        schema=schema_name
                    )
                    
                    if not changes_df.empty:
                        # Apply transformations
                        if task.transformations:
                            changes_df = TransformationEngine.apply_transformations(
                                changes_df,
                                task.transformations
                            )
                        
                        # Get destination table name
                        dest_table_name = task.table_mappings.get(table_name, table_name) if task.table_mappings else table_name
                        
                        # Write changes to destination
                        batch_size_mb = sys.getsizeof(changes_df) / (1024 * 1024)
                        
                        dest_connector.write_data(
                            changes_df,
                            dest_table_name,
                            mode="append",
                            file_format=task.s3_file_format
                        )
                        
                        total_changes += len(changes_df)
                        total_data_size_mb += batch_size_mb
                        
                        logger.info(f"Synced {len(changes_df)} changes for {table_name}")
                    
                    # Update last LSN
                    cdc_enabled_tables[f"{table_name}_last_lsn"] = new_lsn
                    
                except Exception as e:
                    logger.error(f"Error syncing CDC for {table_name}: {str(e)}")
                    raise
            
            # Update task with CDC info
            task.cdc_enabled_tables = cdc_enabled_tables
            task.last_cdc_poll_at = datetime.utcnow()
            self.db.commit()
            
            source_connector.disconnect()
            dest_connector.disconnect()
            
            return {
                "status": "success",
                "total_changes": total_changes,
                "data_size_mb": total_data_size_mb
            }
            
        except Exception as e:
            logger.error(f"CDC sync execution failed: {str(e)}")
            raise
    
    def _handle_schema_drift(
        self,
        source_schema: list,
        dest_connector,
        dest_table_name: str
    ):
        """Handle schema drift by comparing and updating destination schema"""
        try:
            dest_schema = dest_connector.get_table_schema(dest_table_name)
            dest_columns = {col['column_name'] or col.get('COLUMN_NAME') for col in dest_schema}
            
            new_columns = []
            for col in source_schema:
                if col['column_name'] not in dest_columns:
                    new_columns.append(col)
            
            if new_columns:
                logger.info(f"Detected schema drift: {len(new_columns)} new columns")
                dest_connector.handle_schema_drift(dest_table_name, new_columns)
        
        except Exception as e:
            logger.error(f"Error handling schema drift: {str(e)}")
            # Don't fail the transfer, just log the error

