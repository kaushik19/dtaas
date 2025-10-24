from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import models
from services.connector_service import ConnectorService
from transformations import TransformationEngine
import pandas as pd
import logging
from datetime import datetime
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for database sessions
thread_local = threading.local()


class TransferService:
    """Service for handling data transfers"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _check_if_stopped(self, task: models.Task) -> bool:
        """Check if task has been stopped by user"""
        self.db.refresh(task)
        if task.status == "stopped":
            logger.info(f"Task {task.id} was stopped by user")
            raise InterruptedError(f"Task {task.id} was stopped by user")
        return False
    
    def _get_thread_db(self):
        """Get or create a database session for the current thread"""
        if not hasattr(thread_local, 'db'):
            from database import SessionLocal
            thread_local.db = SessionLocal()
        return thread_local.db
    
    def execute_full_load(
        self,
        task: models.Task,
        execution: models.TaskExecution,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Execute full load data transfer"""
        # Check if parallel processing is enabled
        parallel_tables = getattr(task, 'parallel_tables', 1)
        
        if parallel_tables > 1:
            logger.info(f"Using parallel processing with {parallel_tables} threads")
            return self._execute_full_load_parallel(task, execution, progress_callback, parallel_tables)
        else:
            logger.info("Using sequential processing")
            return self._execute_full_load_sequential(task, execution, progress_callback)
    
    def _execute_full_load_sequential(
        self,
        task: models.Task,
        execution: models.TaskExecution,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Execute full load data transfer sequentially (original implementation)"""
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
                # Check if task has been stopped before starting next table
                self._check_if_stopped(task)
                
                table_execution = None
                table_transfer_success = False
                retry_count = 0
                max_retries = task.max_retries if task.retry_enabled else 0
                
                while retry_count <= max_retries and not table_transfer_success:
                    try:
                        # Check if task has been stopped at start of retry attempt
                        self._check_if_stopped(task)
                        
                        if retry_count > 0:
                            logger.info(f"Retry attempt {retry_count}/{max_retries} for table: {table_name}")
                            # Cleanup partial files if configured
                            if task.cleanup_on_retry and hasattr(dest_connector, 'cleanup_partial_files'):
                                logger.info(f"Cleaning up partial files for table: {table_name}")
                                dest_connector.cleanup_partial_files(table_name)
                            # Wait before retry
                            time.sleep(task.retry_delay_seconds)
                        
                        logger.info(f"Starting transfer for table: {table_name} (attempt {retry_count + 1})")
                        
                        # Parse schema.table if provided
                        schema_name = None
                        actual_table_name = table_name
                        if '.' in table_name:
                            schema_name, actual_table_name = table_name.split('.', 1)
                        
                        # Get table row count
                        total_rows = source_connector.get_table_row_count(actual_table_name, schema_name)
                        
                        # Create or update TableExecution record
                        if not table_execution:
                            table_execution = models.TableExecution(
                                task_execution_id=execution.id,
                                table_name=table_name,
                                total_rows=total_rows,
                                processed_rows=0,
                                failed_rows=0,
                                status="running",
                                started_at=datetime.utcnow(),
                                retry_count=retry_count
                            )
                            self.db.add(table_execution)
                            self.db.commit()
                            self.db.refresh(table_execution)
                        else:
                            # Update retry info
                            table_execution.retry_count = retry_count
                            table_execution.last_retry_at = datetime.utcnow()
                            table_execution.status = "running"
                            table_execution.error_message = None
                            table_execution.processed_rows = 0
                            self.db.commit()
                        
                        # Get source schema
                        source_schema = source_connector.get_table_schema(actual_table_name, schema_name)
                        
                        # Create destination table if needed
                        dest_table_name = task.table_mappings.get(table_name, table_name) if task.table_mappings else table_name
                        
                        # Get database name from source connector
                        database_name = ""
                        if hasattr(source_connector, 'database'):
                            database_name = source_connector.database
                        
                        if not dest_connector.table_exists(dest_table_name):
                            dest_connector.create_table_if_not_exists(
                                dest_table_name,
                                source_schema,
                                source_connector=source_connector,
                                database_name=database_name,
                                db_session=self.db
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
                            # Check if task has been stopped before processing next batch
                            self._check_if_stopped(task)
                            
                            # Read batch from source
                            batch_df = source_connector.read_data(
                                actual_table_name,
                                schema_name,
                                batch_size,
                                offset
                            )
                            
                            if batch_df.empty:
                                break
                            
                            # Apply per-table transformations (preferred) or global transformations (fallback)
                            table_transformations = None
                            if task.table_configs and table_name in task.table_configs:
                                table_config = task.table_configs.get(table_name, {})
                                if table_config.get('enabled', True):
                                    table_transformations = table_config.get('transformations')
                            
                            # Fallback to global transformations if no per-table config
                            if table_transformations is None and task.transformations:
                                table_transformations = task.transformations
                            
                            if table_transformations:
                                batch_df = TransformationEngine.apply_transformations(
                                    batch_df,
                                    table_transformations,
                                    source_connector=source_connector,
                                    db_session=self.db,
                                    database_name=database_name,
                                    table_name=table_name
                                )
                            
                            # Calculate batch size in MB
                            batch_size_mb = sys.getsizeof(batch_df) / (1024 * 1024)
                            
                            # Get database name from source connector
                            database_name = ""
                            if hasattr(source_connector, 'database'):
                                database_name = source_connector.database
                            
                            # Write to destination
                            write_result = dest_connector.write_data(
                                batch_df,
                                dest_table_name,
                                mode="append",
                                file_format=task.s3_file_format,
                                source_connector=source_connector,
                                database_name=database_name,
                                db_session=self.db
                            )
                            
                            rows_transferred += len(batch_df)
                            total_rows_transferred += len(batch_df)
                            total_data_size_mb += batch_size_mb
                            offset += batch_size
                            
                            # Update TableExecution progress
                            if table_execution:
                                table_execution.processed_rows = rows_transferred
                                self.db.commit()
                            
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
                        
                        # Mark table as completed
                        if table_execution:
                            table_execution.status = "success"
                            table_execution.completed_at = datetime.utcnow()
                            self.db.commit()
                        
                        completed_tables += 1
                        table_transfer_success = True
                        logger.info(f"Completed transfer for table: {table_name}")
                        
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error transferring table {table_name} (attempt {retry_count}/{max_retries + 1}): {str(e)}")
                        
                        # Mark table as failed
                        if table_execution:
                            table_execution.status = "failed"
                            table_execution.error_message = str(e)
                            table_execution.completed_at = datetime.utcnow()
                            self.db.commit()
                        
                        # Check if we should retry
                        if retry_count <= max_retries:
                            logger.info(f"Will retry table {table_name} after {task.retry_delay_seconds} seconds")
                            continue  # Continue to next retry iteration
                        else:
                            # Max retries exceeded - stop the entire task
                            logger.error(f"Table {table_name} failed after {retry_count} attempts. Stopping task.")
                            raise Exception(f"Table {table_name} failed after {retry_count} attempts: {str(e)}")
            
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
    
    def _execute_full_load_parallel(
        self,
        task: models.Task,
        execution: models.TaskExecution,
        progress_callback=None,
        max_workers: int = 3
    ) -> Dict[str, Any]:
        """Execute full load with parallel table processing"""
        try:
            # Get connector configurations
            source_config = {
                'source_type': task.source_connector.source_type,
                'connection_config': task.source_connector.connection_config
            }
            dest_config = {
                'destination_type': task.destination_connector.destination_type,
                'connection_config': task.destination_connector.connection_config
            }
            
            # Prepare task configuration
            task_config = {
                'batch_rows': task.batch_rows,
                'table_mappings': task.table_mappings or {},
                'table_configs': task.table_configs or {},
                'transformations': task.transformations,
                'handle_schema_drift': task.handle_schema_drift,
                'retry_enabled': task.retry_enabled,
                'retry_delay_seconds': task.retry_delay_seconds,
                'max_retries': task.max_retries,
                'cleanup_on_retry': task.cleanup_on_retry,
                's3_file_format': task.s3_file_format
            }
            
            total_tables = len(task.source_tables)
            completed_tables = 0
            total_rows_transferred = 0
            total_data_size_mb = 0.0
            
            logger.info(f"Starting parallel processing of {total_tables} tables with {max_workers} workers")
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TableTransfer") as executor:
                # Submit all tables for processing
                future_to_table = {
                    executor.submit(
                        self._process_single_table_thread,
                        table_name,
                        task.id,
                        execution.id,
                        source_config,
                        dest_config,
                        task_config
                    ): table_name
                    for table_name in task.source_tables
                }
                
                # Process results as they complete
                for future in as_completed(future_to_table):
                    table_name = future_to_table[future]
                    try:
                        result = future.result()
                        
                        if result['status'] == 'success':
                            completed_tables += 1
                            total_rows_transferred += result.get('rows_transferred', 0)
                            total_data_size_mb += result.get('data_size_mb', 0.0)
                            
                            overall_progress = (completed_tables / total_tables) * 100
                            
                            if progress_callback:
                                progress_callback(
                                    execution_id=execution.id,
                                    progress_percent=overall_progress,
                                    processed_rows=total_rows_transferred
                                )
                            
                            logger.info(f"✓ Completed {table_name}: {result.get('rows_transferred', 0)} rows")
                        elif result['status'] == 'stopped':
                            logger.info(f"Task stopped, cancelling remaining tables")
                            # Cancel remaining futures
                            for f in future_to_table:
                                f.cancel()
                            raise InterruptedError("Task stopped by user")
                        else:
                            logger.error(f"✗ Failed {table_name}: {result.get('error', 'Unknown error')}")
                            raise Exception(f"Table {table_name} failed: {result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {table_name}: {str(e)}")
                        raise
            
            logger.info(f"Parallel processing completed: {completed_tables}/{total_tables} tables, {total_rows_transferred} rows, {total_data_size_mb:.2f} MB")
            
            return {
                "status": "success",
                "total_rows": total_rows_transferred,
                "data_size_mb": total_data_size_mb,
                "tables_transferred": completed_tables
            }
            
        except Exception as e:
            logger.error(f"Parallel full load execution failed: {str(e)}")
            raise
    
    def _process_single_table_thread(
        self,
        table_name: str,
        task_id: int,
        execution_id: int,
        source_config: dict,
        dest_config: dict,
        task_config: dict
    ) -> Dict[str, Any]:
        """Process a single table in a thread"""
        db = self._get_thread_db()
        
        try:
            logger.info(f"[Thread-{threading.current_thread().name}] Starting: {table_name}")
            
            # Create connectors for this thread
            source_connector = ConnectorService._get_connector_instance_from_config(source_config)
            dest_connector = ConnectorService._get_connector_instance_from_config(dest_config)
            
            source_connector.connect()
            dest_connector.connect()
            
            # Get task
            task = db.query(models.Task).filter(models.Task.id == task_id).first()
            if not task or task.status == "stopped":
                return {"table_name": table_name, "status": "stopped", "error": "Task stopped"}
            
            # Parse schema.table
            schema_name = None
            actual_table_name = table_name
            if '.' in table_name:
                schema_name, actual_table_name = table_name.split('.', 1)
            
            # Get table row count
            total_rows = source_connector.get_table_row_count(actual_table_name, schema_name)
            
            # Create TableExecution record
            table_execution = models.TableExecution(
                task_execution_id=execution_id,
                table_name=table_name,
                total_rows=total_rows,
                processed_rows=0,
                failed_rows=0,
                status="running",
                started_at=datetime.utcnow(),
                retry_count=0
            )
            db.add(table_execution)
            db.commit()
            db.refresh(table_execution)
            
            # Get source schema
            source_schema = source_connector.get_table_schema(actual_table_name, schema_name)
            
            # Create destination table
            dest_table_name = task_config.get('table_mappings', {}).get(table_name, table_name)
            database_name = getattr(source_connector, 'database', '')
            
            if not dest_connector.table_exists(dest_table_name):
                dest_connector.create_table_if_not_exists(
                    dest_table_name,
                    source_schema,
                    source_connector=source_connector,
                    database_name=database_name,
                    db_session=db
                )
            
            # Transfer data in batches
            offset = 0
            batch_size = task_config.get('batch_rows', 10000)
            rows_transferred = 0
            data_size_mb = 0.0
            
            while offset < total_rows:
                # Check if stopped
                db.refresh(task)
                if task.status == "stopped":
                    raise InterruptedError("Task stopped")
                
                # Read batch
                batch_df = source_connector.read_data(actual_table_name, schema_name, batch_size, offset)
                if batch_df.empty:
                    break
                
                # Apply transformations
                table_transformations = None
                if task_config.get('table_configs') and table_name in task_config['table_configs']:
                    table_config = task_config['table_configs'][table_name]
                    if table_config.get('enabled', True):
                        table_transformations = table_config.get('transformations')
                
                if table_transformations is None and task_config.get('transformations'):
                    table_transformations = task_config['transformations']
                
                if table_transformations:
                    batch_df = TransformationEngine.apply_transformations(
                        batch_df,
                        table_transformations,
                        source_connector=source_connector,
                        db_session=db,
                        database_name=database_name,
                        table_name=table_name
                    )
                
                # Write to destination
                batch_size_mb = sys.getsizeof(batch_df) / (1024 * 1024)
                dest_connector.write_data(
                    batch_df,
                    dest_table_name,
                    mode="append",
                    file_format=task_config.get('s3_file_format'),
                    source_connector=source_connector,
                    database_name=database_name,
                    db_session=db
                )
                
                rows_transferred += len(batch_df)
                data_size_mb += batch_size_mb
                offset += batch_size
                
                # Update progress in DB after each batch
                table_execution.processed_rows = rows_transferred
                db.commit()
                db.refresh(table_execution)  # Verify the commit worked
                logger.info(f"[{table_name}] 📊 Batch complete: {rows_transferred}/{total_rows} rows ({(rows_transferred/total_rows*100):.1f}%) - Progress committed to DB")
            
            # Mark as completed
            table_execution.status = "success"
            table_execution.completed_at = datetime.utcnow()
            db.commit()
            
            source_connector.disconnect()
            dest_connector.disconnect()
            
            logger.info(f"[{table_name}] Completed: {rows_transferred} rows, {data_size_mb:.2f} MB")
            
            return {
                "table_name": table_name,
                "status": "success",
                "rows_transferred": rows_transferred,
                "data_size_mb": data_size_mb
            }
            
        except InterruptedError:
            return {"table_name": table_name, "status": "stopped", "error": "Task stopped"}
        except Exception as e:
            logger.error(f"[{table_name}] Error: {str(e)}")
            if 'table_execution' in locals():
                table_execution.status = "failed"
                table_execution.error_message = str(e)
                table_execution.completed_at = datetime.utcnow()
                db.commit()
            return {"table_name": table_name, "status": "failed", "error": str(e)}
    
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
                # Check if task has been stopped before processing next table
                self._check_if_stopped(task)
                
                table_execution = None
                try:
                    schema_name = None
                    if '.' in table_name:
                        schema_name, table_name = table_name.split('.', 1)
                    
                    # Create TableExecution record for CDC sync
                    table_execution = models.TableExecution(
                        task_execution_id=execution.id,
                        table_name=table_name,
                        total_rows=0,  # Will be updated as changes are captured
                        processed_rows=0,
                        failed_rows=0,
                        status="running",
                        started_at=datetime.utcnow()
                    )
                    self.db.add(table_execution)
                    self.db.commit()
                    self.db.refresh(table_execution)
                    
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
                                task.transformations,
                                source_connector=source_connector,
                                db_session=self.db,
                                database_name=database_name,
                                table_name=table_name
                            )
                        
                        # Get destination table name
                        dest_table_name = task.table_mappings.get(table_name, table_name) if task.table_mappings else table_name
                        
                        # Write changes to destination
                        batch_size_mb = sys.getsizeof(changes_df) / (1024 * 1024)
                        
                        # Get database name from source connector
                        database_name = ""
                        if hasattr(source_connector, 'database'):
                            database_name = source_connector.database
                        
                        dest_connector.write_data(
                            changes_df,
                            dest_table_name,
                            mode="append",
                            file_format=task.s3_file_format,
                            source_connector=source_connector,
                            database_name=database_name,
                            db_session=self.db
                        )
                        
                        total_changes += len(changes_df)
                        total_data_size_mb += batch_size_mb
                        
                        # Update TableExecution progress
                        if table_execution:
                            table_execution.total_rows = len(changes_df)
                            table_execution.processed_rows = len(changes_df)
                            self.db.commit()
                        
                        logger.info(f"Synced {len(changes_df)} changes for {table_name}")
                    
                    # Update last LSN
                    cdc_enabled_tables[f"{table_name}_last_lsn"] = new_lsn
                    
                    # Mark table as completed
                    if table_execution:
                        table_execution.status = "success"
                        table_execution.completed_at = datetime.utcnow()
                        self.db.commit()
                    
                except Exception as e:
                    logger.error(f"Error syncing CDC for {table_name}: {str(e)}")
                    
                    # Mark table as failed
                    if table_execution:
                        table_execution.status = "failed"
                        table_execution.error_message = str(e)
                        table_execution.completed_at = datetime.utcnow()
                        self.db.commit()
                    
                    # Continue with other tables
                    continue
            
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

