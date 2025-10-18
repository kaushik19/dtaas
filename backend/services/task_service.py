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

