from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import schemas
import models
from database import get_db
from services.task_service import TaskService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Get dashboard metrics and statistics"""
    
    # Total tasks
    total_tasks = db.query(func.count(models.Task.id)).scalar() or 0
    
    # Active tasks
    active_tasks = db.query(func.count(models.Task.id)).filter(
        models.Task.is_active == True
    ).scalar() or 0
    
    # Running tasks
    running_tasks = db.query(func.count(models.Task.id)).filter(
        models.Task.status == "running"
    ).scalar() or 0
    
    # Total rows transferred
    total_rows = db.query(func.sum(models.TaskExecution.processed_rows)).scalar() or 0
    
    # Total data transferred
    total_data_mb = db.query(func.sum(models.TaskExecution.data_size_mb)).scalar() or 0.0
    
    # Successful executions
    successful_executions = db.query(func.count(models.TaskExecution.id)).filter(
        models.TaskExecution.status == "success"
    ).scalar() or 0
    
    # Failed executions
    failed_executions = db.query(func.count(models.TaskExecution.id)).filter(
        models.TaskExecution.status == "failed"
    ).scalar() or 0
    
    # Average rows per second
    avg_rps = db.query(func.avg(models.TaskExecution.rows_per_second)).filter(
        models.TaskExecution.rows_per_second.isnot(None)
    ).scalar() or 0.0
    
    # Recent executions
    recent_executions = TaskService.get_recent_executions(db, limit=10)
    
    return schemas.DashboardMetrics(
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        running_tasks=running_tasks,
        total_rows_transferred=total_rows,
        total_data_transferred_mb=total_data_mb,
        successful_executions=successful_executions,
        failed_executions=failed_executions,
        avg_rows_per_second=avg_rps,
        recent_executions=recent_executions
    )

