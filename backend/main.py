from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database import init_db
from routers import connectors_router, tasks_router, dashboard_router, variables_router, database_browser_router
from logging_config import setup_logging
import asyncio
import json
import logging
from typing import Set

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting DTaaS application...")
    init_db()
    logger.info("Database initialized")
    
    # Start background broadcast task
    logger.info("Starting background broadcast task")
    broadcast_task = asyncio.create_task(broadcast_task_updates())
    logger.info("Background broadcast task created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DTaaS application...")
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        logger.info("Broadcast task cancelled")


# Create FastAPI app
app = FastAPI(
    title="DTaaS - Data Transfer as a Service",
    description="A comprehensive data transfer service with CDC support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(connectors_router)
app.include_router(tasks_router)
app.include_router(dashboard_router)
app.include_router(variables_router)
app.include_router(database_browser_router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "DTaaS - Data Transfer as a Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            
            # Echo back or handle client messages if needed
            await websocket.send_json({
                "type": "ack",
                "message": "Connected to DTaaS"
            })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background task to broadcast updates
async def broadcast_task_updates():
    """Background task to broadcast task updates to connected clients"""
    from database import SessionLocal
    from services.task_service import TaskService
    import models
    
    logger.info("Broadcast task updates started")
    
    while True:
        try:
            db = SessionLocal()
            
            # Get running tasks
            tasks = TaskService.list_tasks(db)
            running_tasks = [t for t in tasks if t.status == "running"]
            
            logger.debug(f"Broadcasting: {len(running_tasks)} running tasks, {len(manager.active_connections)} connections")
            
            if running_tasks and manager.active_connections:
                # Prepare task updates with table-level progress
                task_updates = []
                for t in running_tasks:
                    # Get latest execution
                    latest_execution = db.query(models.TaskExecution).filter(
                        models.TaskExecution.task_id == t.id
                    ).order_by(models.TaskExecution.started_at.desc()).first()
                    
                    task_data = {
                        "id": t.id,
                        "name": t.name,
                        "status": t.status,
                        "progress": t.current_progress_percent
                    }
                    
                    # Add table execution progress if available
                    if latest_execution:
                        # Force a fresh query every time to bypass SQLAlchemy cache
                        db.expire_all()
                        table_executions = db.query(models.TableExecution).filter(
                            models.TableExecution.task_execution_id == latest_execution.id
                        ).all()
                        
                        if table_executions:
                            task_data["table_progress"] = [
                                {
                                    "table_name": te.table_name,
                                    "status": te.status,
                                    "total_rows": te.total_rows,
                                    "processed_rows": te.processed_rows,
                                    "failed_rows": te.failed_rows,
                                    "progress_percent": (te.processed_rows / te.total_rows * 100) if te.total_rows > 0 else 0,
                                    "started_at": te.started_at.isoformat() if te.started_at else None,
                                    "completed_at": te.completed_at.isoformat() if te.completed_at else None
                                }
                                for te in table_executions
                            ]
                            
                            # Log first running table for debugging
                            running_tables = [te for te in table_executions if te.status == "running"]
                            if running_tables:
                                te = running_tables[0]
                                logger.info(f"📊 Broadcasting: {te.table_name} - {te.processed_rows}/{te.total_rows} rows ({te.status})")
                    
                    task_updates.append(task_data)
                
                update = {
                    "type": "task_update",
                    "tasks": task_updates
                }
                logger.info(f"Broadcasting update for {len(task_updates)} tasks to {len(manager.active_connections)} clients")
                await manager.broadcast(update)
            
            db.close()
        except Exception as e:
            logger.error(f"Error in broadcast task: {e}", exc_info=True)
        
        await asyncio.sleep(1)  # Broadcast every 1 second for more real-time feel


# Note: Background tasks now started in lifespan context manager above


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

