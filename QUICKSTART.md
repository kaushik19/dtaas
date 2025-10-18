# Quick Start Guide

Get DTaaS up and running in 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.10+)
python --version

# Check Node version (need 16+)
node --version

# Check if Redis is available
redis-cli ping
```

## Installation Steps

### 1. Install Backend Dependencies (2 minutes)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Backend

```bash
# Create .env file (still in backend directory)
echo "DATABASE_URL=sqlite:///./dtaas.db" > .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# Initialize database
python -c "from database import init_db; init_db()"
```

### 3. Install Frontend Dependencies (2 minutes)

```bash
cd ../frontend
npm install
```

## Running the Application

Open **3 terminal windows**:

### Terminal 1: Start Redis

```bash
# Option A: Using Docker (recommended)
docker run -d -p 6379:6379 redis:latest

# Option B: Local Redis
redis-server
```

### Terminal 2: Start Backend

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# Start API server
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3: Start Celery Worker

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# Start Celery worker
# Windows:
celery -A celery_app worker --loglevel=info --pool=solo

# Linux/Mac:
celery -A celery_app worker --loglevel=info
```

### Terminal 4: Start Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  ➜  Local:   http://localhost:5173/
```

## Access the Application

Open your browser to: **http://localhost:5173**

You should see the DTaaS dashboard!

## Create Your First Transfer

### Step 1: Create a Source Connector

1. Click **"Connectors"** in the sidebar
2. Click **"Create Connector"**
3. Fill in:
   - Name: `My SQL Server`
   - Type: `Source`
   - Source Type: `SQL Server`
   - Server: `your-server-address`
   - Database: `your-database`
   - Username: `your-username`
   - Password: `your-password`
4. Click **"Test"** to verify
5. Click **"Create"**

### Step 2: Create a Destination Connector

**For Snowflake:**
1. Click **"Create Connector"**
2. Fill in:
   - Name: `My Snowflake`
   - Type: `Destination`
   - Destination Type: `Snowflake`
   - Account: `account.region`
   - User/Password
   - Warehouse, Database, Schema
3. Test and Create

**For S3:**
1. Click **"Create Connector"**
2. Fill in:
   - Name: `My S3`
   - Type: `Destination`
   - Destination Type: `S3`
   - Bucket name
   - Region
   - Access Key ID
   - Secret Access Key
   - File Format: `Parquet`
3. Test and Create

### Step 3: Create a Task

1. Click **"Task Builder"** in sidebar
2. Enter task name: `My First Transfer`
3. Select source connector
4. Select tables to transfer
5. Select destination connector
6. Choose mode: `Full Load`
7. Choose schedule: `On Demand`
8. Click **"Create Task"**

### Step 4: Run the Task

1. Go to **"Tasks"** page
2. Find your task
3. Click **"Start"**
4. Watch the progress bar!

## Troubleshooting

### Port Already in Use

If port 8000 or 5173 is busy, change ports:

**Backend** (`backend/config.py`):
```python
api_port: int = 8001  # Change to 8001
```

**Frontend** (`frontend/vite.config.js`):
```javascript
server: {
  port: 5174,  // Change to 5174
}
```

### Redis Connection Error

```bash
# Check if Redis is running
redis-cli ping

# Should return: PONG

# If not, start Redis:
docker run -d -p 6379:6379 redis:latest
```

### SQL Server Connection Issues

1. Check if SQL Server is accessible
2. Verify credentials
3. Check firewall rules
4. Ensure TCP/IP is enabled in SQL Server configuration

### Celery Worker Won't Start on Windows

Use the `--pool=solo` flag:
```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

## Next Steps

- ✅ Try CDC mode for real-time sync
- ✅ Add data transformations
- ✅ Schedule tasks with intervals
- ✅ Monitor the dashboard for metrics
- ✅ View execution history

## Need Help?

- Check `README.md` for detailed documentation
- Check `backend/README.md` for backend specifics
- Check `frontend/README.md` for frontend details
- Review the troubleshooting section in main README

## Testing with Sample Data

If you don't have SQL Server, you can:

1. Use SQL Server Express (free)
2. Use SQL Server in Docker:
   ```bash
   docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=YourPassword123!" \
     -p 1433:1433 --name sqlserver \
     -d mcr.microsoft.com/mssql/server:2019-latest
   ```

3. Create a sample database and enable CDC

Enjoy using DTaaS! 🚀

