# DTaaS - Data Transfer as a Service

A comprehensive web application for transferring data between databases and cloud storage with CDC (Change Data Capture) support.

## 🚀 Features

### Core Features
- ✅ **Multiple Source Connectors**: SQL Server (extensible to others)
- ✅ **Multiple Destination Connectors**: Snowflake, AWS S3
- ✅ **Full Load Transfer**: Complete table data transfer with batching
- ✅ **CDC Support**: Real-time change data capture and sync
- ✅ **Flexible Scheduling**: On-demand, continuous, or interval-based
- ✅ **Data Transformations**: Add/modify/filter data during transfer
- ✅ **Schema Drift Handling**: Automatic schema evolution
- ✅ **Real-time Monitoring**: WebSocket-based progress tracking
- ✅ **Visual Task Builder**: Drag-and-drop interface
- ✅ **Comprehensive Dashboard**: Metrics and execution history

### Technical Features
- 🔄 Background job processing with Celery
- 📊 Real-time progress updates via WebSocket
- 🎯 Batch processing with configurable sizes
- 🔍 Table discovery and metadata extraction
- 📈 Performance metrics and monitoring
- 🛠️ Data transformation pipeline
- 💾 Multiple file formats (Parquet, CSV, JSON)

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Vue 3     │◄────►│   FastAPI    │◄────►│   Celery    │
│  Frontend   │      │   Backend    │      │   Workers   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                       │
                            ▼                       ▼
                     ┌──────────────┐      ┌─────────────┐
                     │   SQLite/    │      │    Redis    │
                     │  PostgreSQL  │      │   (Broker)  │
                     └──────────────┘      └─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ SQL Server  │    │  Snowflake   │    │  AWS S3     │
│  (Source)   │    │(Destination) │    │(Destination)│
└─────────────┘    └──────────────┘    └─────────────┘
```

## 📋 Prerequisites

### Backend
- Python 3.10+
- Redis 6.0+
- SQL Server (for source)
- Snowflake account or AWS S3 (for destination)

### Frontend
- Node.js 16+
- npm or yarn

## 🛠️ Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd dtaas
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -c "from database import init_db; init_db()"
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install locally and run
redis-server
```

## 🚀 Running the Application

### Start Backend API

```bash
cd backend
python main.py
```

API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

### Start Celery Worker

```bash
cd backend
celery -A celery_app worker --loglevel=info --pool=solo
```

Note: On Linux/Mac, you can omit `--pool=solo`

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## 📖 Usage Guide

### 1. Create Connectors

#### Source Connector (SQL Server)
1. Navigate to "Connectors" page
2. Click "Create Connector"
3. Select "Source" type
4. Choose "SQL Server"
5. Enter connection details:
   - Server address
   - Database name
   - Username/Password
   - Port (default: 1433)
6. Click "Test" to verify connection

#### Destination Connector (Snowflake)
1. Click "Create Connector"
2. Select "Destination" type
3. Choose "Snowflake"
4. Enter:
   - Account (e.g., account.region)
   - User/Password
   - Warehouse
   - Database
   - Schema
5. Test connection

#### Destination Connector (S3)
1. Click "Create Connector"
2. Select "Destination" type
3. Choose "S3"
4. Enter:
   - Bucket name
   - Prefix (optional)
   - Region
   - Access Key ID
   - Secret Access Key
   - File format (Parquet/CSV/JSON)
5. Test connection

### 2. Create a Task

#### Using Task Builder
1. Navigate to "Task Builder"
2. **Configure Task**:
   - Enter task name and description
   - Select source connector
   - Choose tables to transfer
   - Select destination connector

3. **Transfer Settings**:
   - **Mode**:
     - **Full Load**: One-time complete transfer
     - **CDC**: Continuous change sync
     - **Full Load + CDC**: Initial load then CDC
   - **Schedule**:
     - **On Demand**: Manual execution
     - **Continuous**: Auto-restart after completion
     - **Interval**: Run every N seconds
   - **Batch Size**: Configure MB or row limits
   - **Schema Drift**: Enable/disable automatic schema updates

4. **Add Transformations** (optional):
   - Add Column (with constant/function)
   - Rename Column
   - Drop Column
   - Cast Type
   - Filter Rows
   - Replace Values

5. Click "Create Task"

### 3. Run Tasks

1. Navigate to "Tasks" page
2. Find your task
3. Click "Start" to begin transfer
4. Monitor progress in real-time
5. Use "Pause" or "Stop" as needed
6. View "History" for execution details

### 4. Monitor Dashboard

- View total tasks and execution metrics
- See success/failure rates
- Monitor data transfer volumes
- Track performance (rows/second)
- Review recent executions

## 🔧 Configuration

### SQL Server CDC Setup

To use CDC features, enable CDC on your SQL Server:

```sql
-- Enable CDC on database
USE YourDatabase;
EXEC sys.sp_cdc_enable_db;

-- Enable CDC on specific table
EXEC sys.sp_cdc_enable_table
    @source_schema = 'dbo',
    @source_name = 'YourTable',
    @role_name = NULL,
    @supports_net_changes = 1;

-- Verify CDC is enabled
SELECT name, is_cdc_enabled 
FROM sys.databases 
WHERE name = 'YourDatabase';
```

### Performance Tuning

**Batch Size**:
- Larger batches = faster but more memory
- Smaller batches = slower but more stable
- Recommended: 10,000-50,000 rows or 50-100 MB

**CDC Polling**:
- Continuous: Polls every 10 seconds
- Interval: Custom polling frequency
- Balance between latency and load

## 📊 Data Transformations

### Available Transformations

1. **Add Column**
   ```json
   {
     "type": "add_column",
     "config": {
       "column_name": "created_date",
       "value": "current_timestamp",
       "expression_type": "function"
     }
   }
   ```

2. **Rename Column**
   ```json
   {
     "type": "rename_column",
     "config": {
       "old_name": "customer_id",
       "new_name": "cust_id"
     }
   }
   ```

3. **Filter Rows**
   ```json
   {
     "type": "filter_rows",
     "config": {
       "column_name": "status",
       "operator": "==",
       "value": "active"
     }
   }
   ```

4. **Cast Type**
   ```json
   {
     "type": "cast_type",
     "config": {
       "column_name": "amount",
       "target_type": "float64"
     }
   }
   ```

## 🐛 Troubleshooting

### Celery Worker Not Starting
- Ensure Redis is running
- Check Redis connection in `.env`
- On Windows, use `--pool=solo` flag

### CDC Not Working
- Verify CDC is enabled on database and tables
- Check SQL Server permissions
- Ensure SQL Server Agent is running

### Connection Failures
- Test connectors individually
- Verify network connectivity
- Check firewall rules
- Validate credentials

### Performance Issues
- Reduce batch size
- Increase polling intervals
- Check network bandwidth
- Monitor database load

## 🔐 Security Considerations

- Store credentials securely (use environment variables)
- Use SSL/TLS for database connections
- Implement authentication (extend the app)
- Use IAM roles for AWS S3 instead of access keys
- Rotate credentials regularly
- Monitor access logs

## 📈 Monitoring & Logging

- Check backend logs: `backend/*.log`
- Monitor Celery tasks: Use Flower
  ```bash
  celery -A celery_app flower
  ```
- View task execution history in dashboard
- Set up alerts for failed transfers

## 🚀 Deployment

### Production Checklist

1. **Database**: Use PostgreSQL instead of SQLite
2. **Redis**: Use managed Redis (AWS ElastiCache, etc.)
3. **Backend**: 
   - Use Gunicorn with multiple workers
   - Set up proper logging
   - Configure CORS appropriately
4. **Frontend**: 
   - Build and serve static files
   - Use CDN for assets
5. **Security**:
   - Enable authentication
   - Use HTTPS
   - Secure credentials
6. **Monitoring**:
   - Set up health checks
   - Configure alerts
   - Monitor resource usage

### Docker Deployment (Future)

A `docker-compose.yml` file can be created for easy deployment.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

[Your License Here]

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Contact: [Your Contact Info]

## 🎯 Roadmap

- [ ] Additional source connectors (MySQL, PostgreSQL, Oracle)
- [ ] More destination options (Azure Blob, GCS)
- [ ] Advanced transformations (joins, aggregations)
- [ ] User authentication and authorization
- [ ] Multi-tenancy support
- [ ] Data quality checks
- [ ] Retry logic and error handling
- [ ] API rate limiting
- [ ] Audit logging
- [ ] Email notifications

## 🙏 Acknowledgments

Built with:
- FastAPI
- Vue 3
- Celery
- SQLAlchemy
- Element Plus
- Vue Flow
- And many other great open-source projects

