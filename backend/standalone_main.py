"""
Standalone DTaaS Application
Single executable that includes backend API + frontend + worker
"""

import os
import sys
import threading
import logging
import webbrowser
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import existing routers and services
from routers import connectors_router, tasks_router, dashboard_router, variables_router, database_browser_router
from database import init_db
from logging_config import setup_logging

# Import standalone worker
from standalone_worker import StandaloneWorker

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Determine if running as compiled executable
def is_compiled():
    return getattr(sys, 'frozen', False)

# Get base path for resources
def get_base_path():
    if is_compiled():
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent.parent

# Initialize FastAPI app
app = FastAPI(
    title="DTaaS - Data Transfer as a Service",
    description="Standalone web application for data transfer and CDC",
    version="1.0.0"
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for standalone mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(connectors_router)
app.include_router(tasks_router)
app.include_router(dashboard_router)
app.include_router(variables_router)
app.include_router(database_browser_router)

# Serve frontend static files
base_path = get_base_path()
frontend_path = base_path / "frontend"

if frontend_path.exists():
    # Mount static files
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the Vue.js frontend"""
        return FileResponse(str(frontend_path / "index.html"))
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve frontend for all routes (SPA)"""
        file_path = frontend_path / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_path / "index.html"))
else:
    logger.warning(f"Frontend not found at {frontend_path}")
    
    @app.get("/")
    async def root():
        return {
            "message": "DTaaS Backend API",
            "version": "1.0.0",
            "status": "running",
            "frontend": "not_bundled",
            "docs": "/docs"
        }

# Global worker instance
worker = None

def start_worker():
    """Start the background worker in a separate thread"""
    global worker
    logger.info("Starting background worker...")
    worker = StandaloneWorker(max_workers=10)
    worker_thread = threading.Thread(target=worker.poll_tasks, daemon=True)
    worker_thread.start()
    logger.info("Background worker started")

@app.on_event("startup")
async def startup_event():
    """Initialize database and start worker on startup"""
    try:
        logger.info("=== DTaaS Standalone Application Starting ===")
        
        # Setup database directory
        import os
        if is_compiled():
            # When compiled, store database in user's home directory
            db_dir = Path.home() / ".dtaas"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "dtaas.db"
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
            logger.info(f"Database location: {db_path}")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized")
        
        # Start background worker
        start_worker()
        
        logger.info("=== DTaaS is ready! ===")
        logger.info("Access the application at: http://localhost:8000")
        logger.info("API documentation at: http://localhost:8000/docs")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Stop worker on shutdown"""
    global worker
    if worker:
        logger.info("Stopping background worker...")
        worker.stop()

def main():
    """Main entry point"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="DTaaS Standalone Application")
        parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
        parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
        parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
        parser.add_argument("--workers", type=int, default=10, help="Number of worker threads (default: 10)")
        
        args = parser.parse_args()
        
        # Open browser after short delay
        if not args.no_browser:
            def open_browser():
                import time
                time.sleep(2)  # Wait for server to start
                url = f"http://localhost:{args.port}"
                logger.info(f"Opening browser: {url}")
                webbrowser.open(url)
            
            threading.Thread(target=open_browser, daemon=True).start()
        
        # Print startup info
        print("\n" + "="*60)
        print("  DTaaS - Data Transfer as a Service")
        print("  Standalone Application")
        print("="*60)
        print(f"\n  🌐 Web Interface: http://localhost:{args.port}")
        print(f"  📚 API Documentation: http://localhost:{args.port}/docs")
        print(f"  👷 Worker Threads: {args.workers}")
        print(f"  💾 Database: {os.environ.get('DATABASE_URL', 'sqlite:///dtaas.db')}")
        print("\n  Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        # Run the server
        try:
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                log_level="info",
                access_log=False  # Reduce noise
            )
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"ERROR: Failed to start server")
            print(f"{'='*60}")
            print(f"\nError: {e}")
            print("\nCommon issues:")
            print(f"  - Port {args.port} might already be in use")
            print(f"  - Try a different port: dtaas.exe --port 9000")
            print(f"  - Check if another DTaaS instance is running")
            print("\n")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to exit...")
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {e}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()
        print("\n")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()

