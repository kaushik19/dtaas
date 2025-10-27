"""
Standalone worker for DTaaS Desktop Application
Replaces Celery + Redis with a simple threading-based task executor
"""

import threading
import time
import logging
from datetime import datetime
from database import SessionLocal
import models
from services.task_service import TaskService
from services.transfer_service import TransferService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StandaloneWorker:
    """Simple worker that polls for tasks and executes them in threads"""
    
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.active_tasks = {}  # task_id -> thread
        self.running = True
        logger.info(f"Standalone worker initialized with {max_workers} max workers")
    
    def poll_tasks(self):
        """Poll database for tasks that need to be executed"""
        while self.running:
            try:
                db = SessionLocal()
                
                # Find tasks that should be running but aren't
                tasks = db.query(models.Task).filter(
                    models.Task.status.in_(['created', 'running'])
                ).all()
                
                for task in tasks:
                    # Skip if already running
                    if task.id in self.active_tasks:
                        thread = self.active_tasks[task.id]
                        if thread.is_alive():
                            continue
                        else:
                            # Thread finished, remove it
                            del self.active_tasks[task.id]
                    
                    # Check if we have capacity
                    if len(self.active_tasks) >= self.max_workers:
                        logger.debug("Max workers reached, waiting...")
                        break
                    
                    # Check if task should be started
                    if task.status == 'created':
                        # Start the task
                        logger.info(f"Starting task {task.id}: {task.name}")
                        task.status = 'running'
                        db.commit()
                    
                    if task.status == 'running':
                        # Execute in a new thread
                        thread = threading.Thread(
                            target=self.execute_task,
                            args=(task.id,),
                            daemon=True
                        )
                        thread.start()
                        self.active_tasks[task.id] = thread
                        logger.info(f"Task {task.id} execution started in thread")
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error in poll_tasks: {e}", exc_info=True)
            
            # Poll every 2 seconds
            time.sleep(2)
    
    def execute_task(self, task_id: int):
        """Execute a single task (runs in separate thread)"""
        db = SessionLocal()
        try:
            task = db.query(models.Task).filter(models.Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            logger.info(f"Executing task {task_id}: {task.name} (mode: {task.mode})")
            
            # Create transfer service and execute
            transfer_service = TransferService(db)
            
            if task.mode == 'full_load_then_cdc':
                # Execute full load first, then CDC
                transfer_service.execute_full_load_then_cdc(task)
            elif task.mode == 'full_load':
                transfer_service.execute_full_load(task)
            elif task.mode == 'cdc':
                transfer_service.execute_cdc_polling(task)
            else:
                logger.error(f"Unknown task mode: {task.mode}")
                task.status = 'failed'
                task.error_message = f"Unknown task mode: {task.mode}"
                db.commit()
                return
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            try:
                task = db.query(models.Task).filter(models.Task.id == task_id).first()
                if task:
                    task.status = 'failed'
                    task.error_message = str(e)
                    db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update task status: {commit_error}")
        finally:
            db.close()
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def stop(self):
        """Stop the worker gracefully"""
        logger.info("Stopping worker...")
        self.running = False
        
        # Wait for active tasks to complete (with timeout)
        timeout = 30
        start = time.time()
        while self.active_tasks and (time.time() - start) < timeout:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
            time.sleep(1)
        
        logger.info("Worker stopped")


def main():
    """Main entry point for standalone worker"""
    import signal
    
    worker = StandaloneWorker(max_workers=10)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        worker.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== DTaaS Standalone Worker Started ===")
    logger.info("Polling for tasks...")
    
    try:
        worker.poll_tasks()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        worker.stop()


if __name__ == "__main__":
    main()

