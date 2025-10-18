# DTaaS Architecture Documentation

## System Overview

DTaaS (Data Transfer as a Service) is a distributed web application designed to transfer data between heterogeneous data sources with support for both batch (full load) and real-time (CDC) synchronization.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Vue 3 Application                                        │  │
│  │  ├─ Dashboard (Metrics & Monitoring)                      │  │
│  │  ├─ Connectors (Source/Destination Management)            │  │
│  │  ├─ Tasks (Task Management & Control)                     │  │
│  │  └─ Task Builder (Visual Drag-and-Drop)                   │  │
│  │                                                            │  │
│  │  State Management: Pinia                                  │  │
│  │  UI Framework: Element Plus                               │  │
│  │  Flow Builder: Vue Flow                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ HTTP/REST + WebSocket
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                      │  │
│  │  ├─ /api/connectors/* (Connector CRUD)                    │  │
│  │  ├─ /api/tasks/* (Task CRUD & Control)                    │  │
│  │  ├─ /api/dashboard/* (Metrics & Stats)                    │  │
│  │  └─ /ws (WebSocket for Real-time Updates)                 │  │
│  │                                                            │  │
│  │  Middleware: CORS, Error Handling                         │  │
│  │  Authentication: (Future Enhancement)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│  Service Layer  │  │  Task Queue     │
│                 │  │  (Celery)       │
│  ┌───────────┐  │  │                 │
│  │Connector  │  │  │  Workers:       │
│  │Service    │  │  │  - execute_task │
│  └───────────┘  │  │  - cdc_polling  │
│  ┌───────────┐  │  │  - start/stop   │
│  │Task       │  │  │  - pause/resume │
│  │Service    │  │  │                 │
│  └───────────┘  │  │  Pool: Solo/    │
│  ┌───────────┐  │  │        Prefork  │
│  │Transfer   │  │  └─────────────────┘
│  │Service    │  │           │
│  └───────────┘  │           │ Broker
└────────┬────────┘           ▼
         │            ┌─────────────────┐
         │            │  Redis          │
         │            │  - Task Queue   │
         │            │  - Results      │
         │            │  - State        │
         │            └─────────────────┘
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Metadata Database (SQLite/PostgreSQL)                    │  │
│  │  ├─ connectors (Connection configs)                       │  │
│  │  ├─ tasks (Transfer job definitions)                      │  │
│  │  ├─ task_executions (Execution logs)                      │  │
│  │  ├─ table_executions (Per-table metrics)                  │  │
│  │  └─ system_metrics (Performance data)                     │  │
│  │                                                            │  │
│  │  ORM: SQLAlchemy                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Connector Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Source      │  │ Destination  │  │ Destination  │          │
│  │  SQL Server  │  │  Snowflake   │  │  AWS S3      │          │
│  │              │  │              │  │              │          │
│  │ - Table List │  │ - Bulk Load  │  │ - Parquet    │          │
│  │ - Schema     │  │ - Staging    │  │ - CSV        │          │
│  │ - Full Load  │  │ - Copy       │  │ - JSON       │          │
│  │ - CDC        │  │ - Schema     │  │ - Partition  │          │
│  │ - LSN Track  │  │   Evolution  │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │                     │                   │
         ▼                     ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  SQL Server  │    │  Snowflake   │    │   AWS S3     │
│   Database   │    │   Warehouse  │    │   Bucket     │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Component Details

### 1. Frontend Layer

**Technology Stack:**
- Vue 3 (Composition API)
- Pinia (State Management)
- Vue Router (Navigation)
- Element Plus (UI Components)
- Vue Flow (Visual Builder)
- Axios (HTTP Client)
- Chart.js (Visualization)

**Responsibilities:**
- User interface rendering
- User interaction handling
- State management
- API communication
- Real-time updates via WebSocket
- Visual task builder

**Key Features:**
- Responsive dashboard with metrics
- Connector CRUD operations
- Task creation and management
- Drag-and-drop task builder
- Real-time progress monitoring
- Execution history visualization

### 2. API Layer

**Technology Stack:**
- FastAPI (Web Framework)
- Uvicorn (ASGI Server)
- Pydantic (Data Validation)
- WebSocket (Real-time Communication)

**Endpoints:**

**Connectors:**
- `POST /api/connectors/` - Create connector
- `GET /api/connectors/` - List connectors
- `GET /api/connectors/{id}` - Get connector
- `PUT /api/connectors/{id}` - Update connector
- `DELETE /api/connectors/{id}` - Delete connector
- `POST /api/connectors/{id}/test` - Test connection
- `GET /api/connectors/{id}/tables` - List tables

**Tasks:**
- `POST /api/tasks/` - Create task
- `GET /api/tasks/` - List tasks
- `GET /api/tasks/{id}` - Get task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/control` - Control (start/stop/pause/resume)
- `GET /api/tasks/{id}/executions` - Get execution history

**Dashboard:**
- `GET /api/dashboard/metrics` - Get system metrics

**WebSocket:**
- `WS /ws` - Real-time updates

**Responsibilities:**
- Request validation
- Business logic orchestration
- Database operations
- Task queue management
- Real-time event broadcasting
- Error handling

### 3. Service Layer

**ConnectorService:**
- Manages connector lifecycle
- Tests connections
- Discovers tables and schemas
- Factory pattern for connector instances

**TaskService:**
- Task CRUD operations
- Execution tracking
- Status management
- History management

**TransferService:**
- Orchestrates data transfers
- Handles full load operations
- Manages CDC synchronization
- Schema drift detection
- Transformation application
- Progress tracking

### 4. Task Queue (Celery)

**Workers:**
- `execute_task` - Full load execution
- `execute_cdc_polling` - CDC synchronization
- `start_task` - Task initialization
- `stop_task` - Task termination
- `pause_task` - Pause execution
- `resume_task` - Resume execution

**Configuration:**
- Broker: Redis
- Result Backend: Redis
- Serializer: JSON
- Task tracking enabled
- Time limit: 12 hours
- Pool: Solo (Windows) / Prefork (Linux)

### 5. Data Layer

**Database Schema:**

```sql
-- Connectors
CREATE TABLE connectors (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    description TEXT,
    connector_type VARCHAR(20),
    source_type VARCHAR(50),
    destination_type VARCHAR(50),
    connection_config JSON,
    is_active BOOLEAN,
    created_at DATETIME,
    updated_at DATETIME,
    last_tested_at DATETIME,
    test_status VARCHAR(20)
);

-- Tasks
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    description TEXT,
    source_connector_id INTEGER,
    destination_connector_id INTEGER,
    source_tables JSON,
    table_mappings JSON,
    mode VARCHAR(30),
    batch_size_mb FLOAT,
    batch_rows INTEGER,
    schedule_type VARCHAR(20),
    schedule_interval_seconds INTEGER,
    s3_file_format VARCHAR(20),
    transformations JSON,
    handle_schema_drift BOOLEAN,
    status VARCHAR(20),
    current_progress_percent FLOAT,
    is_active BOOLEAN,
    created_at DATETIME,
    updated_at DATETIME,
    last_run_at DATETIME,
    cdc_enabled_tables JSON,
    last_cdc_poll_at DATETIME
);

-- Task Executions
CREATE TABLE task_executions (
    id INTEGER PRIMARY KEY,
    task_id INTEGER,
    execution_type VARCHAR(20),
    status VARCHAR(20),
    total_rows INTEGER,
    processed_rows INTEGER,
    failed_rows INTEGER,
    progress_percent FLOAT,
    rows_per_second FLOAT,
    data_size_mb FLOAT,
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds FLOAT,
    error_message TEXT,
    cdc_lsn_start VARCHAR(100),
    cdc_lsn_end VARCHAR(100),
    schema_changes_detected JSON,
    created_at DATETIME
);
```

### 6. Connector Layer

**Base Classes:**
- `BaseConnector` - Abstract base
- `SourceConnector` - Source operations
- `DestinationConnector` - Destination operations

**Implementations:**

**SQL Server Source:**
- Connection management
- Table discovery
- Schema extraction
- Full load reading (with batching)
- CDC enablement
- CDC change tracking
- LSN management

**Snowflake Destination:**
- Bulk load via staging
- PUT/COPY commands
- Schema mapping
- Table creation
- Schema drift handling

**S3 Destination:**
- Multiple format support (Parquet, CSV, JSON)
- Partitioned writes
- Metadata management
- Overwrite/Append modes

## Data Flow

### Full Load Transfer

```
1. User creates task with source/dest connectors
2. User clicks "Start" on task
3. API sends task to Celery queue
4. Celery worker picks up task
5. Worker:
   a. Connects to source
   b. Gets table schema
   c. Creates destination table
   d. Reads data in batches
   e. Applies transformations
   f. Writes to destination
   g. Updates progress
   h. Broadcasts progress via WebSocket
6. Frontend updates progress bar in real-time
7. Execution completes, metrics saved
```

### CDC Transfer

```
1. User creates task with CDC mode
2. System enables CDC on source tables
3. Task starts CDC polling
4. Every N seconds:
   a. Worker queries CDC changes since last LSN
   b. Reads change records
   c. Applies transformations
   d. Writes changes to destination
   e. Updates last LSN
   f. Saves metrics
5. Process repeats continuously or at intervals
6. Dashboard shows real-time sync status
```

## Transformation Pipeline

```
Data Flow:
Source → Read Batch → Transform → Write → Destination

Transformation Types:
1. add_column - Add computed/constant columns
2. rename_column - Rename fields
3. drop_column - Remove fields
4. cast_type - Convert data types
5. filter_rows - Filter records
6. replace_value - Value substitution
7. concatenate_columns - Merge columns
8. split_column - Split into multiple
9. apply_function - Custom functions
```

## Scaling Considerations

### Horizontal Scaling

**API Servers:**
- Deploy multiple FastAPI instances behind load balancer
- Share database connection pool
- Use sticky sessions for WebSocket

**Celery Workers:**
- Deploy multiple worker instances
- Distribute tasks across workers
- Use Redis Sentinel for HA

**Database:**
- Migrate to PostgreSQL for production
- Use read replicas for reporting
- Partition large tables

### Vertical Scaling

**Memory:**
- Adjust batch sizes based on available memory
- Monitor worker memory usage
- Use memory-efficient data structures (Pandas)

**CPU:**
- Increase worker concurrency
- Use multiprocessing for parallel transfers
- Optimize transformation logic

**Network:**
- Use compression for data transfer
- Batch network operations
- Use connection pooling

## Security Architecture

### Current Implementation

- No authentication (development only)
- Credentials stored in database (encrypted recommended)
- CORS enabled for localhost

### Production Recommendations

1. **Authentication & Authorization:**
   - JWT tokens
   - OAuth 2.0
   - Role-based access control (RBAC)

2. **Data Security:**
   - Encrypt credentials at rest
   - Use secrets management (Vault, AWS Secrets Manager)
   - SSL/TLS for all connections

3. **Network Security:**
   - VPC/Private subnets
   - Security groups
   - API rate limiting

4. **Audit & Compliance:**
   - Audit logging
   - Data lineage tracking
   - Compliance reporting

## Monitoring & Observability

### Metrics

- Task execution count
- Success/failure rates
- Data throughput (rows/sec, MB/sec)
- Latency metrics
- Queue depth
- Worker utilization

### Logging

- Application logs (structured JSON)
- Access logs
- Error logs with stack traces
- Audit logs

### Alerting

- Failed executions
- High error rates
- Queue backlog
- Resource exhaustion
- Connection failures

## Future Enhancements

1. **Additional Connectors:**
   - MySQL, PostgreSQL, Oracle
   - Azure Blob, Google Cloud Storage
   - MongoDB, Cassandra

2. **Advanced Features:**
   - Data quality checks
   - Schema versioning
   - Incremental updates
   - Deduplication
   - Complex transformations (joins, aggregations)

3. **Operations:**
   - Blue-green deployments
   - Canary releases
   - Automatic failover
   - Disaster recovery

4. **User Experience:**
   - Workflow templates
   - Scheduling calendar
   - Email notifications
   - Mobile app

## Deployment Architecture

### Development

```
localhost:
  - Frontend (Vite dev server): 5173
  - Backend (Uvicorn): 8000
  - Redis: 6379
  - SQLite: ./dtaas.db
```

### Production

```
Load Balancer
    │
    ├─ Frontend (Nginx) → Static Files + CDN
    │
    ├─ API Gateway
    │   ├─ Backend API (Multiple instances)
    │   └─ WebSocket Server
    │
    ├─ Celery Workers (Auto-scaling group)
    │
    ├─ Redis Cluster (HA)
    │
    └─ PostgreSQL (RDS/Managed)
```

## Performance Benchmarks

Typical performance (single worker, default settings):

- **Full Load**: 10,000-50,000 rows/second
- **CDC**: 1,000-10,000 changes/second
- **Latency**: < 100ms for API calls
- **WebSocket Latency**: < 50ms

Performance varies based on:
- Network bandwidth
- Source/destination performance
- Data complexity
- Transformation overhead
- Batch sizes

## Conclusion

DTaaS is designed as a scalable, extensible data transfer platform with support for both batch and real-time synchronization. The architecture separates concerns clearly, allowing for independent scaling and development of each layer.

