#!/usr/bin/env python3
"""
DTaaS Application Structure Validator
Validates all files exist and checks content without requiring imports
"""

import os
import json
from pathlib import Path

def check_file(filepath, description=""):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    desc_text = f" - {description}" if description else ""
    print(f"  {status} {filepath}{desc_text}")
    return exists

def check_dir(dirpath, description=""):
    """Check if a directory exists"""
    exists = os.path.isdir(dirpath)
    status = "✓" if exists else "✗"
    desc_text = f" - {description}" if description else ""
    print(f"  {status} {dirpath}/{desc_text}")
    return exists

def count_files_in_dir(dirpath, extension):
    """Count files with specific extension in directory"""
    if not os.path.exists(dirpath):
        return 0
    return len(list(Path(dirpath).rglob(f'*.{extension}')))

print("="*70)
print("DTaaS APPLICATION STRUCTURE VALIDATION")
print("="*70)

# Backend Structure
print("\n[1] BACKEND CORE FILES")
backend_core = [
    ("backend/main.py", "FastAPI application entry point"),
    ("backend/config.py", "Application configuration"),
    ("backend/database.py", "Database connection and session"),
    ("backend/models.py", "SQLAlchemy database models"),
    ("backend/schemas.py", "Pydantic validation schemas"),
    ("backend/celery_app.py", "Celery application setup"),
    ("backend/celery_tasks.py", "Background task definitions"),
    ("backend/transformations.py", "Data transformation engine"),
    ("backend/requirements.txt", "Python dependencies"),
]

backend_score = sum(check_file(f, desc) for f, desc in backend_core)
print(f"\n  Score: {backend_score}/{len(backend_core)}")

# Backend Connectors
print("\n[2] BACKEND CONNECTORS")
connectors = [
    ("backend/connectors/__init__.py", "Connector exports"),
    ("backend/connectors/base.py", "Base connector classes"),
    ("backend/connectors/sql_server.py", "SQL Server source connector"),
    ("backend/connectors/snowflake.py", "Snowflake destination connector"),
    ("backend/connectors/s3.py", "S3/LocalStack destination connector"),
]

connector_score = sum(check_file(f, desc) for f, desc in connectors)
print(f"\n  Score: {connector_score}/{len(connectors)}")

# Backend Services
print("\n[3] BACKEND SERVICES")
services = [
    ("backend/services/__init__.py", "Service exports"),
    ("backend/services/connector_service.py", "Connector management service"),
    ("backend/services/task_service.py", "Task management service"),
    ("backend/services/transfer_service.py", "Data transfer orchestration"),
]

service_score = sum(check_file(f, desc) for f, desc in services)
print(f"\n  Score: {service_score}/{len(services)}")

# Backend Routers
print("\n[4] BACKEND API ROUTERS")
routers = [
    ("backend/routers/__init__.py", "Router exports"),
    ("backend/routers/connectors.py", "Connector API endpoints"),
    ("backend/routers/tasks.py", "Task API endpoints"),
    ("backend/routers/dashboard.py", "Dashboard API endpoints"),
]

router_score = sum(check_file(f, desc) for f, desc in routers)
print(f"\n  Score: {router_score}/{len(routers)}")

# Frontend Core
print("\n[5] FRONTEND CORE FILES")
frontend_core = [
    ("frontend/package.json", "NPM dependencies"),
    ("frontend/vite.config.js", "Vite configuration"),
    ("frontend/index.html", "HTML entry point"),
    ("frontend/src/main.js", "Vue app initialization"),
    ("frontend/src/App.vue", "Root Vue component"),
    ("frontend/src/router/index.js", "Vue Router configuration"),
    ("frontend/src/api/index.js", "API client"),
]

frontend_score = sum(check_file(f, desc) for f, desc in frontend_core)
print(f"\n  Score: {frontend_score}/{len(frontend_core)}")

# Frontend Views
print("\n[6] FRONTEND VIEWS")
views = [
    ("frontend/src/views/Dashboard.vue", "Dashboard with metrics"),
    ("frontend/src/views/Connectors.vue", "Connector management"),
    ("frontend/src/views/Tasks.vue", "Task list and control"),
    ("frontend/src/views/TaskBuilder.vue", "Visual task builder"),
]

view_score = sum(check_file(f, desc) for f, desc in views)
print(f"\n  Score: {view_score}/{len(views)}")

# Frontend Stores
print("\n[7] FRONTEND STORES (Pinia)")
stores = [
    ("frontend/src/stores/connectorStore.js", "Connector state management"),
    ("frontend/src/stores/taskStore.js", "Task state management"),
    ("frontend/src/stores/dashboardStore.js", "Dashboard state"),
    ("frontend/src/stores/websocketStore.js", "WebSocket connection"),
]

store_score = sum(check_file(f, desc) for f, desc in stores)
print(f"\n  Score: {store_score}/{len(stores)}")

# Documentation
print("\n[8] DOCUMENTATION FILES")
docs = [
    ("README.md", "Main documentation"),
    ("QUICKSTART.md", "Quick start guide"),
    ("ARCHITECTURE.md", "Architecture documentation"),
    ("LOCALSTACK_SETUP.md", "LocalStack setup guide"),
    ("START_LOCAL.md", "Local startup guide"),
    ("PROJECT_SUMMARY.md", "Project summary"),
    ("backend/README.md", "Backend documentation"),
    ("frontend/README.md", "Frontend documentation"),
]

doc_score = sum(check_file(f, desc) for f, desc in docs)
print(f"\n  Score: {doc_score}/{len(docs)}")

# Configuration Files
print("\n[9] CONFIGURATION FILES")
configs = [
    ("docker-compose.yml", "Docker services configuration"),
    (".gitignore", "Git ignore patterns"),
    ("setup.sh", "Linux/Mac setup script"),
    ("setup.bat", "Windows setup script"),
]

config_score = sum(check_file(f, desc) for f, desc in configs)
print(f"\n  Score: {config_score}/{len(configs)}")

# Code Statistics
print("\n[10] CODE STATISTICS")
stats = {
    "Backend Python files": count_files_in_dir("backend", "py"),
    "Frontend Vue files": count_files_in_dir("frontend/src", "vue"),
    "Frontend JS files": count_files_in_dir("frontend/src", "js"),
}

for name, count in stats.items():
    print(f"  ✓ {name}: {count}")

total_code_files = sum(stats.values())
print(f"\n  Total code files: {total_code_files}")

# Content Validation
print("\n[11] CONTENT VALIDATION")

# Check main.py has key features
if os.path.exists("backend/main.py"):
    with open("backend/main.py", "r", encoding="utf-8") as f:
        main_content = f.read()
        checks = [
            ("FastAPI app", "app = FastAPI" in main_content),
            ("WebSocket endpoint", "@app.websocket" in main_content),
            ("CORS middleware", "CORSMiddleware" in main_content),
            ("Health check", "/health" in main_content),
            ("Router inclusion", "include_router" in main_content),
        ]
        for name, result in checks:
            status = "✓" if result else "✗"
            print(f"  {status} {name}")

# Check docker-compose.yml
if os.path.exists("docker-compose.yml"):
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        docker_content = f.read()
        checks = [
            ("Redis service", "redis:" in docker_content),
            ("LocalStack service", "localstack:" in docker_content),
            ("Redis port 6379", "6379:6379" in docker_content),
            ("LocalStack port 4566", "4566:4566" in docker_content),
        ]
        for name, result in checks:
            status = "✓" if result else "✗"
            print(f"  {status} {name}")

# Check package.json
if os.path.exists("frontend/package.json"):
    with open("frontend/package.json", "r", encoding="utf-8") as f:
        package = json.load(f)
        deps = package.get("dependencies", {})
        required_deps = ["vue", "vue-router", "pinia", "axios", "element-plus", "@vueflow/core"]
        print(f"\n  Frontend dependencies:")
        for dep in required_deps:
            has_dep = dep in deps
            status = "✓" if has_dep else "✗"
            version = deps.get(dep, "missing")
            print(f"    {status} {dep}: {version}")

# Final Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

total_score = (backend_score + connector_score + service_score + router_score + 
               frontend_score + view_score + store_score + doc_score + config_score)
total_possible = (len(backend_core) + len(connectors) + len(services) + len(routers) +
                 len(frontend_core) + len(views) + len(stores) + len(docs) + len(configs))

percentage = (total_score / total_possible) * 100

print(f"\nStructure Completeness: {total_score}/{total_possible} files ({percentage:.1f}%)")
print(f"Total Code Files: {total_code_files}")

if percentage == 100:
    print("\n✓ EXCELLENT! Application structure is 100% complete!")
    print("✓ All files are in place and ready to use.")
elif percentage >= 95:
    print("\n✓ GREAT! Application structure is nearly complete.")
    print("  A few optional files may be missing.")
elif percentage >= 80:
    print("\n⚠ GOOD! Most files are present.")
    print("  Some files may need to be created.")
else:
    print("\n✗ WARNING! Application structure is incomplete.")
    print("  Several important files are missing.")

print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)
print("\n1. ✓ Install Docker and Docker Compose")
print("2. Run: docker-compose up -d")
print("3. Setup backend: cd backend && python -m venv venv")
print("4. Activate venv and install: pip install -r requirements.txt")
print("5. Setup frontend: cd frontend && npm install")
print("6. Follow START_LOCAL.md for detailed instructions")
print("\n" + "="*70)

