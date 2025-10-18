from celery_app import celery_app
from database import SessionLocal
from services.task_service import TaskService
from services.transfer_service import TransferService
import models
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def execute_task(self, task_id: int):
    """Execute a data transfer task"""
    db = SessionLocal()
    
    try:
        # Get task
        task = TaskService.get_task(db, task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}
        
        # Update task status
        TaskService.update_task_status(db, task_id, "running", 0.0)
        
        # Create execution record
        execution_type = task.mode
        execution = TaskService.create_execution(db, task_id, execution_type)
        
        # Progress callback
        def progress_callback(**kwargs):
            TaskService.update_execution(db, execution.id, **kwargs)
            TaskService.update_task_status(
                db,
                task_id,
                "running",
                kwargs.get('progress_percent', 0)
            )
            
            # Update Celery task state for monitoring
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': kwargs.get('progress_percent', 0),
                    'processed_rows': kwargs.get('processed_rows', 0)
                }
            )
        
        # Execute transfer
        transfer_service = TransferService(db)
        
        if task.mode == "full_load":
            result = transfer_service.execute_full_load(task, execution, progress_callback)
        
        elif task.mode == "cdc":
            result = transfer_service.execute_cdc_sync(task, execution, progress_callback)
        
        elif task.mode == "full_load_then_cdc":
            # First do full load
            result = transfer_service.execute_full_load(task, execution, progress_callback)
            # Then switch to CDC mode
            task.mode = "cdc"
            db.commit()
        
        else:
            raise ValueError(f"Unknown task mode: {task.mode}")
        
        # Update execution
        TaskService.update_execution(
            db,
            execution.id,
            status="success",
            total_rows=result.get('total_rows', result.get('total_changes', 0)),
            processed_rows=result.get('total_rows', result.get('total_changes', 0)),
            data_size_mb=result.get('data_size_mb', 0),
            progress_percent=100.0
        )
        
        # Update task status
        TaskService.update_task_status(db, task_id, "completed", 100.0)
        
        # If continuous mode, schedule next execution
        if task.schedule_type == "continuous":
            execute_task.apply_async(args=[task_id], countdown=10)
        
        logger.info(f"Task {task_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        
        # Update execution
        if 'execution' in locals():
            TaskService.update_execution(
                db,
                execution.id,
                status="failed",
                error_message=str(e)
            )
        
        # Update task status
        TaskService.update_task_status(db, task_id, "failed", 0.0)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()


@celery_app.task
def execute_cdc_polling(task_id: int):
    """Execute CDC polling for a task (runs continuously)"""
    db = SessionLocal()
    
    try:
        task = TaskService.get_task(db, task_id)
        if not task or task.status != "running":
            return
        
        # Create CDC execution
        execution = TaskService.create_execution(db, task_id, "cdc_sync")
        
        # Execute CDC sync
        transfer_service = TransferService(db)
        result = transfer_service.execute_cdc_sync(task, execution)
        
        # Update execution
        TaskService.update_execution(
            db,
            execution.id,
            status="success",
            total_rows=result.get('total_changes', 0),
            processed_rows=result.get('total_changes', 0),
            data_size_mb=result.get('data_size_mb', 0)
        )
        
        logger.info(f"CDC polling for task {task_id}: {result.get('total_changes', 0)} changes")
        
        # Schedule next poll based on schedule type
        if task.schedule_type == "continuous":
            # Poll every 10 seconds for continuous
            execute_cdc_polling.apply_async(args=[task_id], countdown=10)
        elif task.schedule_type == "interval" and task.schedule_interval_seconds:
            # Poll at specified interval
            execute_cdc_polling.apply_async(args=[task_id], countdown=task.schedule_interval_seconds)
        
    except Exception as e:
        logger.error(f"CDC polling for task {task_id} failed: {str(e)}")
    
    finally:
        db.close()


@celery_app.task
def start_task(task_id: int):
    """Start a task based on its mode and schedule"""
    db = SessionLocal()
    
    try:
        task = TaskService.get_task(db, task_id)
        if not task:
            return {"status": "error", "message": "Task not found"}
        
        TaskService.update_task_status(db, task_id, "running")
        
        if task.mode == "full_load":
            # Execute full load once
            execute_task.delay(task_id)
        
        elif task.mode == "cdc":
            # Start CDC polling
            execute_cdc_polling.delay(task_id)
        
        elif task.mode == "full_load_then_cdc":
            # Execute full load, then start CDC
            execute_task.delay(task_id)
        
        return {"status": "success", "message": "Task started"}
        
    finally:
        db.close()


@celery_app.task
def stop_task(task_id: int):
    """Stop a running task"""
    db = SessionLocal()
    
    try:
        TaskService.update_task_status(db, task_id, "stopped")
        # Note: Active Celery tasks will check status and stop themselves
        return {"status": "success", "message": "Task stopped"}
    
    finally:
        db.close()


@celery_app.task
def pause_task(task_id: int):
    """Pause a running task"""
    db = SessionLocal()
    
    try:
        TaskService.update_task_status(db, task_id, "paused")
        return {"status": "success", "message": "Task paused"}
    
    finally:
        db.close()


@celery_app.task
def resume_task(task_id: int):
    """Resume a paused task"""
    db = SessionLocal()
    
    try:
        task = TaskService.get_task(db, task_id)
        if not task or task.status != "paused":
            return {"status": "error", "message": "Task not paused"}
        
        TaskService.update_task_status(db, task_id, "running")
        
        # Restart based on mode
        if task.mode in ["cdc", "full_load_then_cdc"]:
            execute_cdc_polling.delay(task_id)
        else:
            execute_task.delay(task_id)
        
        return {"status": "success", "message": "Task resumed"}
    
    finally:
        db.close()

