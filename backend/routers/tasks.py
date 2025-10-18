from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import schemas
from database import get_db
from services.task_service import TaskService
import celery_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.TaskResponse)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db)
):
    """Create a new task"""
    # Check if task with same name exists
    existing = TaskService.get_task_by_name(db, task.name)
    if existing:
        raise HTTPException(status_code=400, detail="Task with this name already exists")
    
    return TaskService.create_task(db, task)


@router.get("/", response_model=List[schemas.TaskResponse])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all tasks"""
    return TaskService.list_tasks(db, skip, limit)


@router.get("/{task_id}", response_model=schemas.TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get task by ID"""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db)
):
    """Update task"""
    task = TaskService.update_task(db, task_id, task_update)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Delete task"""
    if not TaskService.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/control")
def control_task(
    task_id: int,
    control: schemas.TaskControlRequest,
    db: Session = Depends(get_db)
):
    """Control task execution (start, stop, pause, resume)"""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    action = control.action.lower()
    
    if action == "start":
        celery_tasks.start_task.delay(task_id)
        return {"message": "Task started"}
    
    elif action == "stop":
        celery_tasks.stop_task.delay(task_id)
        return {"message": "Task stopped"}
    
    elif action == "pause":
        celery_tasks.pause_task.delay(task_id)
        return {"message": "Task paused"}
    
    elif action == "resume":
        celery_tasks.resume_task.delay(task_id)
        return {"message": "Task resumed"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.get("/{task_id}/executions", response_model=List[schemas.TaskExecutionResponse])
def get_task_executions(
    task_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get task execution history"""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskService.get_task_executions(db, task_id, limit)

