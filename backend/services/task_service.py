from sqlalchemy.orm import Session
from typing import List, Optional
import models
import schemas
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing tasks"""
    
    @staticmethod
    def _filter_current_tables(task: models.Task, table_executions: list) -> list:
        """
        Filter table executions to only include tables currently configured in the task.
        This prevents showing progress for tables that were removed from the task.
        """
        if not table_executions:
            return []
        
        # Get current table names from task configuration and normalize them
        # Remove schema prefix if present (e.g., "dbo.TableName" -> "TableName")
        current_tables = set()
        current_tables_with_schema = set()
        
        for table in (task.source_tables or []):
            current_tables_with_schema.add(table)
            # Store both with and without schema prefix
            if '.' in table:
                base_name = table.split('.', 1)[1]  # Get part after first dot
                current_tables.add(base_name)
            current_tables.add(table)
        
        # Filter table executions
        filtered_executions = []
        for table_exec in table_executions:
            table_name = table_exec.table_name
            
            # Check if table is in current configuration (with or without schema)
            is_configured = table_name in current_tables
            
            # Also check with schema prefix added if not already present
            if not is_configured and '.' not in table_name:
                # Try common schema prefixes
                for schema_table in current_tables_with_schema:
                    if schema_table.endswith('.' + table_name):
                        is_configured = True
                        break
            
            if is_configured:
                # If table_configs exists, check if table is enabled
                if task.table_configs:
                    # Try to find config with or without schema prefix
                    table_config = None
                    for config_key in task.table_configs.keys():
                        if config_key == table_name or config_key.endswith('.' + table_name):
                            table_config = task.table_configs[config_key]
                            break
                    
                    if table_config and not table_config.get('enabled', True):
                        # Skip disabled tables
                        continue
                
                filtered_executions.append(table_exec)
        
        return filtered_executions
    
    @staticmethod
    def create_task(db: Session, task: schemas.TaskCreate) -> models.Task:
        """Create a new task"""
        db_task = models.Task(
            name=task.name,
            description=task.description,
            source_connector_id=task.source_connector_id,
            destination_connector_id=task.destination_connector_id,
            source_tables=task.source_tables,
            table_mappings=task.table_mappings,
            mode=task.mode,
            batch_size_mb=task.batch_size_mb,
            batch_rows=task.batch_rows,
            schedule_type=task.schedule_type,
            schedule_interval_seconds=task.schedule_interval_seconds,
            s3_file_format=task.s3_file_format,
            transformations=[t.model_dump() for t in task.transformations] if task.transformations else None,
            handle_schema_drift=task.handle_schema_drift,
        )
        
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        logger.info(f"Created task: {task.name}")
        return db_task
    
    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[models.Task]:
        """Get task by ID"""
        return db.query(models.Task).filter(models.Task.id == task_id).first()
    
    @staticmethod
    def get_task_by_name(db: Session, name: str) -> Optional[models.Task]:
        """Get task by name"""
        return db.query(models.Task).filter(models.Task.name == name).first()
    
    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[models.Task]:
        """List all tasks"""
        return db.query(models.Task).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_task(
        db: Session,
        task_id: int,
        task_update: schemas.TaskUpdate
    ) -> Optional[models.Task]:
        """Update task"""
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        update_data = task_update.model_dump(exclude_unset=True)
        
        # Handle transformations separately
        if 'transformations' in update_data and update_data['transformations']:
            update_data['transformations'] = [t.model_dump() for t in update_data['transformations']]
        
        # Clean up CDC state for removed tables
        if 'source_tables' in update_data:
            old_tables = set(db_task.source_tables or [])
            new_tables = set(update_data['source_tables'] or [])
            removed_tables = old_tables - new_tables
            
            if removed_tables and db_task.cdc_enabled_tables:
                # Remove CDC state for tables no longer in the task
                cdc_state = db_task.cdc_enabled_tables.copy()
                for table in removed_tables:
                    # Remove the table's CDC enabled flag
                    cdc_state.pop(table, None)
                    # Remove the table's last LSN (with and without schema prefix)
                    base_name = table.split('.')[-1] if '.' in table else table
                    cdc_state.pop(f"{base_name}_last_lsn", None)
                    cdc_state.pop(f"{table}_last_lsn", None)
                
                db_task.cdc_enabled_tables = cdc_state
                logger.info(f"Cleaned up CDC state for removed tables: {removed_tables}")
        
        for field, value in update_data.items():
            setattr(db_task, field, value)
        
        db.commit()
        db.refresh(db_task)
        
        logger.info(f"Updated task: {db_task.name}")
        return db_task
    
    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        """Delete task"""
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return False
        
        db.delete(db_task)
        db.commit()
        
        logger.info(f"Deleted task: {db_task.name}")
        return True
    
    @staticmethod
    def update_task_status(
        db: Session,
        task_id: int,
        status: str,
        progress: Optional[float] = None
    ) -> Optional[models.Task]:
        """Update task status and progress"""
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        db_task.status = status
        if progress is not None:
            db_task.current_progress_percent = progress
        
        if status == "running":
            db_task.last_run_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_task)
        
        return db_task
    
    @staticmethod
    def create_execution(
        db: Session,
        task_id: int,
        execution_type: str
    ) -> models.TaskExecution:
        """Create a new task execution record"""
        execution = models.TaskExecution(
            task_id=task_id,
            execution_type=execution_type,
            status="pending",
            started_at=datetime.utcnow()
        )
        
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        return execution
    
    @staticmethod
    def update_execution(
        db: Session,
        execution_id: int,
        **kwargs
    ) -> Optional[models.TaskExecution]:
        """Update task execution"""
        execution = db.query(models.TaskExecution).filter(
            models.TaskExecution.id == execution_id
        ).first()
        
        if not execution:
            return None
        
        for key, value in kwargs.items():
            if hasattr(execution, key):
                setattr(execution, key, value)
        
        # Calculate duration if completed
        if kwargs.get('status') in ['success', 'failed', 'partial_success'] and execution.started_at:
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        
        db.commit()
        db.refresh(execution)
        
        return execution
    
    @staticmethod
    def get_task_executions(
        db: Session,
        task_id: int,
        limit: int = 50
    ) -> List[models.TaskExecution]:
        """Get task execution history"""
        return db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == task_id
        ).order_by(models.TaskExecution.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_executions(db: Session, limit: int = 10) -> List[models.TaskExecution]:
        """Get recent executions across all tasks"""
        return db.query(models.TaskExecution).order_by(
            models.TaskExecution.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_task_detail(db: Session, task_id: int) -> dict:
        """Get detailed task info with table-wise progress"""
        task = TaskService.get_task(db, task_id)
        if not task:
            return None
        
        # Get latest execution
        latest_execution = db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == task_id
        ).order_by(models.TaskExecution.created_at.desc()).first()
        
        # Get full load table progress (from latest full_load or full_load_then_cdc execution)
        full_load_execution = db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == task_id,
            models.TaskExecution.execution_type.in_(["full_load", "full_load_then_cdc"])
        ).order_by(models.TaskExecution.created_at.desc()).first()
        
        full_load_progress = []
        if full_load_execution:
            all_full_load_progress = db.query(models.TableExecution).filter(
                models.TableExecution.task_execution_id == full_load_execution.id
            ).all()
            
            # Filter to only show tables that are currently in the task configuration
            full_load_progress = TaskService._filter_current_tables(task, all_full_load_progress)
        
        # Get CDC table progress (from latest cdc_sync execution)
        cdc_execution = db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == task_id,
            models.TaskExecution.execution_type == "cdc_sync"
        ).order_by(models.TaskExecution.created_at.desc()).first()
        
        cdc_progress = []
        if cdc_execution:
            all_cdc_progress = db.query(models.TableExecution).filter(
                models.TableExecution.task_execution_id == cdc_execution.id
            ).all()
            
            # Filter to only show tables that are currently in the task configuration
            cdc_progress = TaskService._filter_current_tables(task, all_cdc_progress)
        
        return {
            "task": task,
            "full_load_progress": full_load_progress,
            "cdc_progress": cdc_progress,
            "latest_execution": latest_execution
        }

