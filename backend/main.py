from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from config import settings
from database import init_db
from routers import connectors_router, tasks_router, dashboard_router
import asyncio
import json
from typing import Set

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    
    yield
    
    # Shutdown
    logger.info("Shutting down DTaaS application...")


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
    
    while True:
        try:
            db = SessionLocal()
            
            # Get running tasks
            tasks = TaskService.list_tasks(db)
            running_tasks = [t for t in tasks if t.status == "running"]
            
            if running_tasks and manager.active_connections:
                update = {
                    "type": "task_update",
                    "tasks": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "status": t.status,
                            "progress": t.current_progress_percent
                        }
                        for t in running_tasks
                    ]
                }
                await manager.broadcast(update)
            
            db.close()
        except Exception as e:
            logger.error(f"Error in broadcast task: {e}")
        
        await asyncio.sleep(2)  # Broadcast every 2 seconds


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(broadcast_task_updates())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

