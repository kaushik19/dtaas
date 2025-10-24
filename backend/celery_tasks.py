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
        
        logger.info(f"Executing task {task_id} (current status: {task.status})")
        
        # Check if task should actually run (prevent stale queue tasks from executing)
        if task.status not in ["created", "running"]:
            logger.warning(f"Task {task_id} has status '{task.status}', skipping execution")
            return {"status": "skipped", "message": f"Task status is {task.status}, not executing"}
        
        # Ensure task status is "running" (safeguard in case start_task was skipped)
        if task.status != "running":
            logger.info(f"Task {task_id} status is '{task.status}', updating to 'running'")
            TaskService.update_task_status(db, task_id, "running", 0.0)
        else:
            logger.info(f"Task {task_id} status already 'running'")
        
        # Refresh task to get latest status
        db.refresh(task)
        
        # Create execution record
        execution_type = task.mode
        execution = TaskService.create_execution(db, task_id, execution_type)
        
        # Progress callback
        def progress_callback(**kwargs):
            # Remove execution_id from kwargs to avoid duplicate parameter error
            kwargs.pop('execution_id', None)
            
            # Check if task has been stopped
            db.refresh(task)
            if task.status == "stopped":
                logger.info(f"Task {task_id} was stopped, aborting execution")
                raise InterruptedError(f"Task {task_id} was stopped by user")
            
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
            # Check if this is the first run or if there are tables that haven't completed full load
            completed_tables = task.full_load_completed_tables or {}
            tables_needing_full_load = [t for t in task.source_tables if t not in completed_tables]
            
            if tables_needing_full_load:
                # First do full load only for tables that haven't been loaded yet
                logger.info(f"Performing full load for {len(tables_needing_full_load)} tables that haven't been loaded yet")
                result = transfer_service.execute_full_load(task, execution, progress_callback, 
                                                           tables_to_load=tables_needing_full_load)
                
                # Mark these tables as completed
                if not task.full_load_completed_tables:
                    task.full_load_completed_tables = {}
                for table in tables_needing_full_load:
                    task.full_load_completed_tables[table] = datetime.utcnow().isoformat()
                db.commit()
            else:
                logger.info("All tables have already completed full load, skipping to CDC")
            
            # Start CDC polling for continuous sync
            if task.schedule_type in ["continuous", "interval"]:
                execute_cdc_polling.delay(task_id)
        
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
        
    except InterruptedError as e:
        # Task was stopped by user
        logger.info(f"Task {task_id} was stopped: {str(e)}")
        
        # Update execution
        if 'execution' in locals():
            TaskService.update_execution(
                db,
                execution.id,
                status="stopped",
                error_message="Task stopped by user"
            )
        
        # Task status already set to stopped by stop_task
        return {"status": "stopped", "message": str(e)}
        
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
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}
        
        # Check if task should actually run
        if task.status == "stopped":
            logger.warning(f"Task {task_id} is stopped, skipping start")
            return {"status": "skipped", "message": "Task is stopped"}
        
        logger.info(f"Starting task {task_id} (current status: {task.status}, mode: {task.mode})")
        
        # Update status to running
        TaskService.update_task_status(db, task_id, "running")
        
        logger.info(f"Task {task_id} status updated to running")
        
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
        # Update task status first
        task = TaskService.get_task(db, task_id)
        if not task:
            return {"status": "error", "message": "Task not found"}
        
        TaskService.update_task_status(db, task_id, "stopped")
        
        # Update any running table executions to stopped status
        # Get the latest execution for this task
        latest_execution = db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == task_id
        ).order_by(models.TaskExecution.started_at.desc()).first()
        
        if latest_execution:
            # Update all running table executions to stopped
            running_tables = db.query(models.TableExecution).filter(
                models.TableExecution.task_execution_id == latest_execution.id,
                models.TableExecution.status == "running"
            ).all()
            
            for table_exec in running_tables:
                table_exec.status = "stopped"
                table_exec.error_message = "Task stopped by user"
                table_exec.completed_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Updated {len(running_tables)} running table executions to stopped status")
        
        # Revoke all active Celery tasks for this task_id
        # This will terminate the running task immediately
        from celery_app import celery_app as app
        
        # Get all active tasks
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task_info in tasks:
                    # Check if this task is related to our task_id
                    task_args = task_info.get('args', [])
                    if task_args and len(task_args) > 0:
                        if isinstance(task_args[0], int) and task_args[0] == task_id:
                            # Revoke the task with terminate=True to stop it immediately
                            app.control.revoke(task_info['id'], terminate=True, signal='SIGKILL')
                            logger.info(f"Revoked Celery task {task_info['id']} for task_id {task_id}")
        
        logger.info(f"Task {task_id} stopped successfully")
        return {"status": "success", "message": "Task stopped"}
    
    except Exception as e:
        logger.error(f"Error stopping task {task_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    
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

