# DTaaS - Complete Documentation

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.0-brightgreen.svg)](https://vuejs.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-success.svg)](#testing)
[![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](#test-coverage)

> **Data Transfer as a Service** - Enterprise-grade data transfer and synchronization platform

---

## 📑 Table of Contents

### Getting Started
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)

### Features & Architecture  
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Database Connectors](#database-connectors)

### Usage Guide
- [Running the Application](#running-the-application)
- [Using the API](#using-the-api)
- [Web Interface](#web-interface)
- [Configuration](#configuration)

### Development
- [Testing](#testing)
- [Building from Source](#building-from-source)
- [Contributing](#contributing)

### Deployment
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Cleanup & Maintenance](#cleanup--maintenance)

### Reference
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [FAQ](#faq)

---

## 🎯 Overview

**DTaaS (Data Transfer as a Service)** is a comprehensive, enterprise-grade platform for seamless data movement between various database systems and cloud storage solutions.

### What It Does

- **Full Load**: Complete data transfers from source to destination
- **CDC (Change Data Capture)**: Real-time data synchronization
- **Hybrid Mode**: Full load followed by continuous CDC
- **Transformations**: Apply data transformations during transfer
- **Monitoring**: Real-time progress tracking and dashboards

### Why DTaaS?

✅ **Simple** - Intuitive web interface, no coding required  
✅ **Powerful** - Supports multiple databases and formats  
✅ **Fast** - Parallel processing with configurable batch sizes  
✅ **Reliable** - Automatic retry and error recovery  
✅ **Flexible** - Extensive transformation capabilities  
✅ **Portable** - Single executable, no external dependencies  

### Supported Systems

**Sources**: SQL Server, PostgreSQL, MySQL, Oracle  
**Destinations**: Snowflake, AWS S3  
**Formats**: Parquet, CSV, JSON  

---

## ⚡ Quick Start

### For End Users (Standalone Executable)

```bash
# 1. Download dtaas.exe
# 2. Double-click or run from command line
cd dist
.\dtaas.exe

# 3. Browser opens automatically to http://localhost:8000
# 4. Start creating connectors and tasks!
```

### For Developers

```bash
# 1. Clone repository
git clone https://github.com/yourusername/dtaas.git
cd dtaas

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Run application
python main.py

# 4. Access at http://localhost:8000
```

### Run Tests

```bash
cd backend
pip install -r requirements-test.txt
python run_tests.py
```

---

## 🚀 Installation

### Method 1: Standalone Executable (Recommended)

**Windows:**
```powershell
# Download and run
cd dist
.\dtaas.exe

# Custom port
.\dtaas.exe --port 9000

# More worker threads
.\dtaas.exe --workers 20
```

**Linux/Mac:**
```bash
cd dist
chmod +x dtaas
./dtaas
```

### Method 2: From Source (Development)

**Prerequisites:**
- Python 3.10+
- Node.js 18+ (for frontend development)
- Git

**Backend Setup:**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database import init_db; init_db()"

# Run
python main.py
```

**Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install

# Development
npm run dev

# Production build
npm run build
```

### Method 3: Docker

```bash
# Using docker-compose
docker-compose up -d

# Access at http://localhost:8000
```

### Method 4: Build Executable Yourself

```bash
# Windows
.\build.bat

# Linux/Mac
chmod +x build.sh
./build.sh

# Executable created in dist/
```

---

## ✨ Key Features

### 1. Multi-Database Support

#### Source Databases
- **SQL Server** - With CDC via Change Tracking
- **PostgreSQL** - With logical replication
- **MySQL** - With binlog CDC
- **Oracle** - With LogMiner support

#### Destination Systems
- **Snowflake** - Optimized bulk loading
- **AWS S3** - Multiple formats (Parquet, CSV, JSON)

### 2. Change Data Capture (CDC)

Capture and replicate real-time database changes:
- Track INSERT, UPDATE, DELETE operations
- Configurable polling intervals
- LSN/SCN tracking for consistency
- Automatic resume from last checkpoint

### 3. Data Transformations

Apply transformations during transfer:

**Column Operations:**
- Rename, drop, cast types
- Uppercase, lowercase, trim
- Add prefix/suffix
- Replace values

**Row Operations:**
- Filter rows with conditions
- Remove duplicates
- Sort and limit

**Advanced:**
- Date/time extractions
- Concatenate columns
- Split columns
- Conditional logic
- Aggregations

### 4. Global Variables

Dynamic variables resolved at runtime:

**Static Variables:**
```json
{
  "name": "tenant_id",
  "type": "static",
  "value": "12345"
}
```

**Database Query Variables:**
```json
{
  "name": "max_date",
  "type": "db_query",
  "query": "SELECT MAX(order_date) FROM orders"
}
```

**Context Variables:**
```json
{
  "name": "source_db",
  "type": "context",
  "path": "source_connector.database"
}
```

**Usage in Tasks:**
```sql
SELECT * FROM orders 
WHERE tenant_id = {{tenant_id}}
AND order_date > {{max_date}}
```

### 5. Parallel Processing

- Multi-threaded table transfers
- Configurable worker pools
- Batch processing optimization
- Progress tracking per table
- Automatic load balancing

### 6. Error Handling & Retry

- Automatic retry mechanisms
- Configurable retry counts
- Error logging and tracking
- Partial failure recovery
- Graceful degradation

### 7. Monitoring & Observability

- Real-time progress tracking
- WebSocket-based live updates
- Execution history
- Performance metrics
- Task dashboard with statistics

---

## 🏗️ System Architecture

### Component Overview

```
┌─────────────────────────────────────────────┐
│           Web Browser (Vue.js)              │
│  ┌───────────────────────────────────────┐  │
│  │  - Connectors  - Tasks  - Dashboard  │  │
│  │  - Variables   - Browser             │  │
│  └───────────────────────────────────────┘  │
└────────────┬────────────────────────────────┘
             │ HTTP/WebSocket
┌────────────▼────────────────────────────────┐
│         FastAPI Backend                     │
│  ┌───────────────────────────────────────┐  │
│  │  Routers (API Endpoints)              │  │
│  ├───────────────────────────────────────┤  │
│  │  Services (Business Logic)            │  │
│  ├───────────────────────────────────────┤  │
│  │  Background Worker (Task Execution)   │  │
│  └───────────────────────────────────────┘  │
└────────────┬───────────┬────────────────────┘
             │           │
    ┌────────▼─────┐  ┌──▼──────────┐
    │  SQLite DB   │  │  Redis      │
    │  (Metadata)  │  │  (Cache)    │
    └──────────────┘  └─────────────┘
             │
    ┌────────▼────────────────────────┐
    │     Database Connectors         │
    │  SQL Server | PostgreSQL | ...  │
    │  Oracle | Snowflake | S3        │
    └─────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Python 3.13
- FastAPI (Web framework)
- SQLAlchemy (ORM)
- Pydantic (Validation)
- Pandas & PyArrow (Data processing)
- WebSockets (Real-time updates)

**Frontend:**
- Vue.js 3
- Vite (Build tool)
- Axios (HTTP client)
- WebSocket client

**Databases:**
- SQLite (Metadata - default)
- PostgreSQL (Metadata - optional)
- Redis (Cache - optional)

### Data Flow

1. **User Creates Task** → Web UI → API
2. **Task Configuration Stored** → Database
3. **Worker Polls for Tasks** → Background process
4. **Data Transfer Executed** → Source → Transformation → Destination
5. **Progress Updated** → WebSocket → Real-time UI updates
6. **Results Logged** → Execution history

---

## 🔌 Database Connectors

### SQL Server

**Configuration:**
```json
{
  "host": "localhost",
  "port": 1433,
  "database": "MyDB",
  "username": "sa",
  "password": "SecurePassword123!",
  "driver": "ODBC Driver 17 for SQL Server"
}
```

**CDC Support:**
- Uses SQL Server Change Tracking (CT)
- Automatically enables CT if not present
- Tracks INSERT, UPDATE, DELETE
- LSN-based change tracking

**Features:**
- List databases and tables
- Browse table schemas
- Execute custom queries
- Full and incremental loads

### PostgreSQL

**Configuration:**
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "username": "postgres",
  "password": "password"
}
```

**CDC Support:**
- Logical replication slots
- WAL-based change capture
- Publication/subscription model

### MySQL

**Configuration:**
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "mydb",
  "username": "root",
  "password": "password"
}
```

**CDC Support:**
- Binary log (binlog) based
- Row-based replication format
- GTID tracking

### Oracle

**Configuration:**
```json
{
  "host": "localhost",
  "port": 1521,
  "service_name": "ORCL",
  "username": "system",
  "password": "password",
  "connection_type": "service_name"
}
```

**CDC Support:**
- LogMiner for change capture
- Supplemental logging required
- SCN-based tracking

**Note:** Oracle connector requires `cx_Oracle` package (optional dependency)

### Snowflake

**Configuration:**
```json
{
  "account": "your_account",
  "user": "username",
  "password": "password",
  "warehouse": "COMPUTE_WH",
  "database": "MY_DB",
  "schema": "PUBLIC",
  "role": "SYSADMIN"
}
```

**Features:**
- Bulk loading via staging
- Auto-create tables
- Schema evolution support
- Optimized write performance
- Type mapping (SQL → Snowflake)

### AWS S3

**Configuration:**
```json
{
  "bucket_name": "my-bucket",
  "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "region": "us-west-2",
  "prefix": "data/",
  "file_format": "parquet"
}
```

**Supported Formats:**
- **Parquet** - Columnar, compressed (recommended)
- **CSV** - Text format, human-readable
- **JSON** - JSON lines format

**Features:**
- Partitioning support
- Compression (gzip, snappy)
- Custom file naming
- Metadata preservation

---

## 📖 Using the Application

### Running the Application

**Standalone Mode:**
```bash
cd dist
.\dtaas.exe

# Options:
# --port 9000        # Custom port
# --host 0.0.0.0     # Bind to all interfaces
# --workers 20       # More worker threads
# --no-browser       # Don't auto-open browser
```

**Development Mode:**
```bash
# Backend
cd backend
python main.py

# Frontend (separate terminal)
cd frontend
npm run dev
```

**Access Points:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

### Using the API

#### Create a Connector

```python
import requests

# SQL Server source
connector = {
    "name": "Production SQL Server",
    "description": "Main production database",
    "connector_type": "source",
    "source_type": "sql_server",
    "connection_config": {
        "host": "sql-server.example.com",
        "port": 1433,
        "database": "ProductionDB",
        "username": "app_user",
        "password": "SecurePass123!"
    }
}

response = requests.post(
    "http://localhost:8000/api/connectors",
    json=connector
)
print(response.json())
```

#### Test Connection

```python
test_request = {
    "connector_type": "source",
    "source_type": "sql_server",
    "connection_config": {
        "host": "localhost",
        "port": 1433,
        "database": "TestDB",
        "username": "sa",
        "password": "password"
    }
}

response = requests.post(
    "http://localhost:8000/api/connectors/test",
    json=test_request
)
print(response.json())  # {"success": true, "message": "..."}
```

#### Create a Task

```python
task = {
    "name": "Daily Customer Sync",
    "description": "Sync customers to Snowflake",
    "source_connector_id": 1,
    "destination_connector_id": 2,
    "mode": "full_load",  # or "cdc", "full_load_then_cdc"
    "schedule_type": "on_demand",  # or "continuous", "interval"
    "config": {
        "tables": ["customers", "orders", "products"],
        "batch_size": 10000,
        "parallel": true,
        "max_parallel_tables": 5,
        "transformations": {
            "customers": [
                {
                    "type": "rename_column",
                    "config": {
                        "old_name": "cust_id",
                        "new_name": "customer_id"
                    }
                },
                {
                    "type": "uppercase",
                    "config": {"column": "country"}
                }
            ]
        }
    }
}

response = requests.post(
    "http://localhost:8000/api/tasks",
    json=task
)
```

#### Start a Task

```python
task_id = 1
response = requests.post(
    f"http://localhost:8000/api/tasks/{task_id}/start"
)
print(response.json())
```

#### Monitor Progress

```python
# Get task status
response = requests.get(f"http://localhost:8000/api/tasks/{task_id}")
task = response.json()
print(f"Status: {task['status']}")

# Get execution history
response = requests.get(
    f"http://localhost:8000/api/tasks/{task_id}/executions"
)
executions = response.json()

for execution in executions:
    print(f"Execution {execution['id']}: {execution['status']}")
    print(f"  Rows processed: {execution['processed_rows']}")
```

### Web Interface

The web interface provides a visual way to manage everything:

#### 1. Connectors Page
- Add new connectors (source/destination)
- Test connections
- Edit connection details
- View connector status

#### 2. Tasks Page
- Create data transfer tasks
- View all tasks and their status
- Start/stop/pause tasks
- View execution history

#### 3. Task Builder
- Visual table selection
- Drag-and-drop interface
- Configure transformations
- Preview transformations
- Bulk operations across tables

#### 4. Dashboard
- Task statistics
- Active executions
- Recent activity
- Performance charts
- System health

#### 5. Global Variables
- Create reusable variables
- Static, DB query, and context types
- Use in task configurations
- Test variable resolution

#### 6. Database Browser
- Browse source databases
- View table schemas
- See column types and constraints
- Execute custom queries
- Preview table data

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in backend directory:

```env
# Database
DATABASE_URL=sqlite:///./dtaas.db
# Or PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost:5432/dtaas

# Redis (optional, for Celery)
REDIS_URL=redis://localhost:6379/0

# Application
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Worker
MAX_WORKERS=10
```

### Task Configuration Examples

**Full Load Task:**
```json
{
  "name": "Full Load - All Tables",
  "mode": "full_load",
  "schedule_type": "on_demand",
  "config": {
    "tables": ["table1", "table2", "table3"],
    "batch_size": 10000,
    "parallel": true,
    "max_parallel_tables": 5
  }
}
```

**CDC Task:**
```json
{
  "name": "CDC - Real-time Sync",
  "mode": "cdc",
  "schedule_type": "continuous",
  "config": {
    "tables": ["orders", "transactions"],
    "poll_interval": 60,
    "batch_size": 1000,
    "track_deletes": true
  }
}
```

**Hybrid Task:**
```json
{
  "name": "Full Load + CDC",
  "mode": "full_load_then_cdc",
  "schedule_type": "continuous",
  "config": {
    "tables": ["customers"],
    "batch_size": 10000,
    "cdc_poll_interval": 30
  }
}
```

**With Transformations:**
```json
{
  "name": "Transform and Load",
  "mode": "full_load",
  "config": {
    "tables": ["employees"],
    "transformations": {
      "employees": [
        {"type": "uppercase", "config": {"column": "email"}},
        {"type": "trim", "config": {"column": "name"}},
        {
          "type": "rename_column",
          "config": {"old_name": "emp_id", "new_name": "employee_id"}
        }
      ]
    }
  }
}
```

---

## 🧪 Testing

### Test Suite

DTaaS has **100% code coverage** with 250+ tests.

### Running Tests

**Quick Start:**
```bash
cd backend
pip install -r requirements-test.txt
python run_tests.py
```

**Specific Test Categories:**
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Specific file
pytest tests/test_models.py

# With coverage
pytest --cov=. --cov-report=html
```

### Test Structure

```
backend/tests/
├── test_models.py           # Database models (50+ tests)
├── test_schemas.py          # Pydantic schemas (40+ tests)
├── test_services.py         # Business logic (40+ tests)
├── test_routers.py          # API endpoints (50+ tests)
├── test_transformations.py  # Transformations (60+ tests)
└── test_integration.py      # End-to-end (20+ tests)
```

### Coverage Report

```bash
# Generate HTML report
pytest --cov=. --cov-report=html

# View in browser (Windows)
start htmlcov\index.html

# View in browser (Linux/Mac)
open htmlcov/index.html
```

### Writing Tests

```python
import pytest

@pytest.mark.unit
def test_create_connector(db_session):
    """Test creating a connector"""
    connector = models.Connector(
        name="Test",
        connector_type=models.ConnectorType.SOURCE,
        source_type=models.SourceType.SQL_SERVER,
        connection_config={"host": "localhost"}
    )
    db_session.add(connector)
    db_session.commit()
    
    assert connector.id is not None
    assert connector.name == "Test"
```

---

## 🔨 Building from Source

### Prerequisites
- Python 3.10+
- Node.js 18+
- PyInstaller

### Build Steps

**Windows:**
```bash
# Full build (frontend + backend)
.\build.bat

# Quick rebuild (backend only)
.\rebuild.bat

# Executable created in dist/dtaas.exe
```

**Linux/Mac:**
```bash
chmod +x build.sh
./build.sh

# Executable created in dist/dtaas
```

### Build Configuration

The build process:
1. Builds Vue.js frontend
2. Copies frontend to backend
3. Installs Python dependencies
4. Bundles with PyInstaller
5. Creates single executable

**Customize build:**
Edit `backend/standalone_main.spec` for PyInstaller settings

---

## 🚢 Docker Deployment

### Quick Start

```bash
docker-compose up -d
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dtaas
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  worker:
    build: ./backend
    command: celery -A celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dtaas
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=dtaas
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## 🌐 Production Deployment

### Using systemd (Linux)

**1. Create service file:**
```ini
# /etc/systemd/system/dtaas.service
[Unit]
Description=DTaaS Service
After=network.target

[Service]
Type=simple
User=dtaas
WorkingDirectory=/opt/dtaas
ExecStart=/opt/dtaas/dtaas --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Enable and start:**
```bash
sudo systemctl enable dtaas
sudo systemctl start dtaas
sudo systemctl status dtaas
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name dtaas.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SSL with Let's Encrypt

```bash
sudo certbot --nginx -d dtaas.example.com
```

---

## 🧹 Cleanup & Maintenance

### Cleanup Script

Run to remove temporary files and build artifacts:

```bash
# Windows
.\cleanup.bat

# Linux/Mac
chmod +x cleanup.sh
./cleanup.sh
```

### What Gets Removed

- Build artifacts (~200MB)
- Python cache files
- Development databases
- Test coverage reports
- Redundant documentation

### Manual Cleanup

```bash
# Remove build artifacts
Remove-Item -Path "backend\build" -Recurse -Force

# Remove Python cache
Get-ChildItem -Path . -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force

# Remove test database
Remove-Item test_dtaas.db
```

### .gitignore

A comprehensive `.gitignore` prevents committing temporary files:
- `__pycache__/`
- `*.db`
- `build/`
- `htmlcov/`
- `.coverage`

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Fails

**Symptoms:**
- "Connection refused" error
- "Authentication failed"

**Solutions:**
```bash
# Check database is running
# For SQL Server:
sqlcmd -S localhost -U sa -P password

# Check network connectivity
ping sql-server.example.com

# Verify credentials
# Test with database client first

# Check firewall rules
# Windows Firewall or iptables
```

#### 2. Executable Won't Start

**Symptoms:**
- Nothing happens when double-clicking
- "Module not found" errors

**Solutions:**
```bash
# Run from command line to see errors
cd dist
.\dtaas.exe

# Check Python version (should be 3.10+)
python --version

# Rebuild if necessary
.\build.bat

# Check antivirus isn't blocking
# Add exception for dtaas.exe
```

#### 3. CDC Not Working

**Symptoms:**
- No changes detected
- "CDC not enabled" error

**Solutions:**
```sql
-- SQL Server: Enable Change Tracking
ALTER DATABASE MyDatabase
SET CHANGE_TRACKING = ON
(CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON);

ALTER TABLE MyTable
ENABLE CHANGE_TRACKING;

-- PostgreSQL: Check replication slot
SELECT * FROM pg_replication_slots;

-- MySQL: Check binlog
SHOW VARIABLES LIKE 'log_bin';
```

#### 4. Performance Issues

**Symptoms:**
- Slow transfers
- High memory usage

**Solutions:**
```bash
# Increase batch size
# In task config: "batch_size": 50000

# Add more workers
.\dtaas.exe --workers 20

# Enable parallel processing
# In task config: "parallel": true

# Check network bandwidth
# Use compression for S3: "compression": "gzip"
```

#### 5. Frontend Not Loading

**Symptoms:**
- Blank page
- Console errors

**Solutions:**
```bash
# Clear browser cache
# Ctrl+Shift+Delete

# Check backend is running
curl http://localhost:8000/docs

# Rebuild frontend
cd frontend
npm run build

# Check for CORS issues
# (Shouldn't happen in standalone mode)
```

### Error Messages

**"No module named 'cx_Oracle'"**
- Oracle connector not available
- Install: `pip install cx-Oracle`
- Or use other database connectors

**"Port already in use"**
```bash
# Use different port
.\dtaas.exe --port 9000

# Or kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux:
lsof -i :8000
kill <PID>
```

**"Database locked"**
```bash
# Stop all instances
# Remove database file
rm dtaas.db

# Restart and it will be recreated
```

### Logs

**View logs:**
```bash
# Standalone mode - logs to console

# Docker mode
docker-compose logs -f backend

# systemd
journalctl -u dtaas -f
```

**Log Levels:**
- DEBUG: Detailed information
- INFO: General information
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors

---

## 📚 API Reference

### Connectors API

**List all connectors:**
```http
GET /api/connectors
```

**Create connector:**
```http
POST /api/connectors
Content-Type: application/json

{
  "name": "My Connector",
  "connector_type": "source",
  "source_type": "sql_server",
  "connection_config": {...}
}
```

**Get connector:**
```http
GET /api/connectors/{id}
```

**Update connector:**
```http
PUT /api/connectors/{id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "New description"
}
```

**Delete connector:**
```http
DELETE /api/connectors/{id}
```

**Test connection:**
```http
POST /api/connectors/test
Content-Type: application/json

{
  "connector_type": "source",
  "source_type": "sql_server",
  "connection_config": {...}
}
```

### Tasks API

**List tasks:**
```http
GET /api/tasks
```

**Create task:**
```http
POST /api/tasks
Content-Type: application/json

{
  "name": "My Task",
  "source_connector_id": 1,
  "destination_connector_id": 2,
  "mode": "full_load",
  "config": {...}
}
```

**Start task:**
```http
POST /api/tasks/{id}/start
```

**Stop task:**
```http
POST /api/tasks/{id}/stop
```

**Pause task:**
```http
POST /api/tasks/{id}/pause
```

**Get executions:**
```http
GET /api/tasks/{id}/executions
```

### Variables API

**List variables:**
```http
GET /api/variables
```

**Create variable:**
```http
POST /api/variables
Content-Type: application/json

{
  "name": "my_var",
  "variable_type": "static",
  "config": {"value": "test"}
}
```

### Dashboard API

**Get statistics:**
```http
GET /api/dashboard/stats
```

**Recent executions:**
```http
GET /api/dashboard/executions/recent
```

---

## ❓ FAQ

**Q: Can I use DTaaS without Python/Node.js installed?**  
A: Yes! Use the standalone executable. It includes everything.

**Q: How many tables can I transfer at once?**  
A: No limit. We've tested with 1000+ tables successfully.

**Q: Does it support incremental loads?**  
A: Yes, through CDC (Change Data Capture) for real-time synchronization.

**Q: Can I schedule tasks?**  
A: Currently supports on-demand and continuous modes. Cron scheduling coming soon.

**Q: Is it production-ready?**  
A: Yes! With 100% test coverage, error handling, and retry mechanisms.

**Q: Can I transform data during transfer?**  
A: Yes! Supports 20+ transformation types including column operations, filters, and more.

**Q: What's the performance?**  
A: Transfers millions of rows per minute with parallel processing and batch optimization.

**Q: Can I monitor transfers in real-time?**  
A: Yes! WebSocket-based real-time progress updates in the UI.

**Q: Does it handle schema changes?**  
A: Yes! Auto-detects schema changes and can update destination schemas.

**Q: Can I use custom SQL queries?**  
A: Yes! Database browser allows custom queries, and tasks support query-based transfers.

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write tests
5. Run tests (`python run_tests.py`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use type hints
- Write tests for new features (maintain 100% coverage)
- Update documentation
- Add docstrings to functions

### Code Style

```bash
# Format code
black backend/
isort backend/

# Lint
flake8 backend/
pylint backend/

# Type check
mypy backend/
```

### Running Tests

```bash
# All tests
python run_tests.py

# With coverage
pytest --cov=. --cov-report=html

# Specific tests
pytest tests/test_models.py -v
```

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Vue.js for the reactive UI
- SQLAlchemy for database management
- All contributors and users

---

## 📞 Support

- **Documentation**: This file!
- **Issues**: https://github.com/yourusername/dtaas/issues
- **Email**: support@dtaas.io
- **Discord**: https://discord.gg/dtaas

---

## 🗺️ Roadmap

- [ ] More database types (MongoDB, Cassandra)
- [ ] Advanced scheduling (cron expressions)
- [ ] Data quality checks
- [ ] Automated schema mapping
- [ ] Kubernetes deployment
- [ ] Multi-tenancy support
- [ ] Advanced monitoring and alerting
- [ ] REST API for external integrations

---

**Made with ❤️ by the DTaaS Team**

*Last Updated: 2024*

