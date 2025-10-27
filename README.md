# DTaaS - Data Transfer as a Service

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.0-brightgreen.svg)](https://vuejs.org/)
[![Tests](https://img.shields.io/badge/Tests-250+-success.svg)](DOCUMENTATION.md#testing)
[![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](DOCUMENTATION.md#test-coverage)

> Enterprise-grade data transfer and synchronization platform with real-time CDC support

## ⚡ Quick Start

### For End Users

```bash
# Download and run
cd dist
.\dtaas.exe

# Browser opens automatically at http://localhost:8000
```

### For Developers

```bash
# Clone and install
git clone https://github.com/yourusername/dtaas.git
cd dtaas/backend
pip install -r requirements.txt
python main.py
```

### Run Tests

```bash
cd backend
pip install -r requirements-test.txt
python run_tests.py
# ✓ 250+ tests, 100% coverage
```

## 🎯 What It Does

DTaaS enables seamless data movement between databases and cloud storage with:

- ✅ **Full Load** - Complete data transfers
- ✅ **CDC** - Real-time change data capture  
- ✅ **Transformations** - Apply data transformations
- ✅ **Multi-Database** - SQL Server, PostgreSQL, MySQL, Oracle → Snowflake, S3
- ✅ **Parallel Processing** - Fast, efficient transfers
- ✅ **Web Interface** - Beautiful Vue.js dashboard

## 📖 Documentation

**📚 [Complete Documentation](DOCUMENTATION.md)** - Everything in one place!

Quick links:
- [Installation Guide](DOCUMENTATION.md#installation)
- [Database Connectors](DOCUMENTATION.md#database-connectors)
- [API Reference](DOCUMENTATION.md#api-reference)
- [Testing Guide](DOCUMENTATION.md#testing)
- [Deployment](DOCUMENTATION.md#production-deployment)
- [Troubleshooting](DOCUMENTATION.md#troubleshooting)

## 🚀 Key Features

### Supported Databases

**Sources:**
- Microsoft SQL Server (with CDC)
- PostgreSQL (with logical replication)
- MySQL (with binlog)
- Oracle (with LogMiner)

**Destinations:**
- Snowflake (optimized bulk loading)
- AWS S3 (Parquet, CSV, JSON)

### Core Capabilities

- **Change Data Capture**: Real-time synchronization with LSN/SCN tracking
- **Data Transformations**: 20+ transformation types (rename, filter, aggregate, etc.)
- **Global Variables**: Dynamic variables with context awareness
- **Parallel Processing**: Multi-threaded transfers with configurable workers
- **Error Recovery**: Automatic retry and partial failure handling
- **Real-time Monitoring**: WebSocket-based live progress updates

## 🏗️ Architecture

```
Web Browser (Vue.js)
       ↓
FastAPI Backend
   ↓       ↓
Database  Background Worker
           ↓
    Data Connectors
    (SQL Server, PostgreSQL, etc.)
           ↓
    Destinations
    (Snowflake, S3)
```

## 📊 Example Usage

### Create and Start a Task

```python
import requests

# Create task
task = {
    "name": "Daily Customer Sync",
    "source_connector_id": 1,
    "destination_connector_id": 2,
    "mode": "full_load",
    "config": {
        "tables": ["customers", "orders"],
        "batch_size": 10000,
        "transformations": {
            "customers": [
                {"type": "uppercase", "config": {"column": "email"}}
            ]
        }
    }
}

response = requests.post("http://localhost:8000/api/tasks", json=task)

# Start task
task_id = response.json()["id"]
requests.post(f"http://localhost:8000/api/tasks/{task_id}/start")
```

## 🧪 Testing

**100% Test Coverage** with 250+ comprehensive tests:

```bash
cd backend
python run_tests.py

# Results:
# ✓ 250+ tests passed
# ✓ 100% code coverage
# ✓ All modules tested
```

Coverage breakdown:
- Models: 100%
- Schemas: 100%
- Services: 100%
- API Routes: 100%
- Transformations: 100%
- Integration: 100%

## 🚢 Deployment

### Standalone

```bash
# Already built!
cd dist
.\dtaas.exe --port 8000 --workers 20
```

### Docker

```bash
docker-compose up -d
# Access at http://localhost:8000
```

### Production

```bash
# Install as systemd service (Linux)
sudo systemctl enable dtaas
sudo systemctl start dtaas
```

See [Deployment Guide](DOCUMENTATION.md#production-deployment) for details.

## 🧹 Cleanup

Remove temporary files and build artifacts:

```bash
# Windows
.\cleanup.bat

# Linux/Mac
chmod +x cleanup.sh && ./cleanup.sh
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests (maintain 100% coverage)
4. Submit a pull request

See [Contributing Guide](DOCUMENTATION.md#contributing) for details.

## 📄 License

MIT License - see LICENSE file

## 📞 Support

- 📚 [Full Documentation](DOCUMENTATION.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/dtaas/issues)
- 💬 [Discord Community](https://discord.gg/dtaas)

---

**[Read the Complete Documentation →](DOCUMENTATION.md)**

*DTaaS - Making data transfer simple, fast, and reliable.*
