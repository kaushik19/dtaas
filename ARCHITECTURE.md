# DTaaS - Production Architecture

## System Overview

DTaaS is a production-grade, distributed data transfer platform designed for enterprise-scale data synchronization between heterogeneous data sources. It supports both batch (full load) and real-time (CDC) data replication with built-in resilience, monitoring, and scalability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Production Architecture                         │
└─────────────────────────────────────────────────────────────────────┘

                          Internet/VPN
                               │
                    ┌──────────┴──────────┐
                    │  Load Balancer      │
                    │  (SSL/TLS)          │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   Frontend   │    │   Backend    │      │   Backend    │
│   (Nginx)    │    │   API (1)    │      │   API (2)    │
│              │    │              │      │              │
│ Static Files │    │  FastAPI     │      │  FastAPI     │
│ + SPA        │    │  + WebSocket │      │  + WebSocket │
└──────────────┘    └──────┬───────┘      └──────┬───────┘
                           │                      │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │   Celery     │  │   Celery     │  │   Celery     │
            │   Worker 1   │  │   Worker 2   │  │   Worker N   │
            │              │  │              │  │              │
            │ Task Exec    │  │ Task Exec    │  │ Task Exec    │
            │ CDC Polling  │  │ CDC Polling  │  │ CDC Polling  │
            └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                   │                 │                 │
                   └─────────────────┼─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
        ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
        │  Redis Cluster   │  │ PostgreSQL   │  │  Monitoring  │
        │  (HA + Sentinel) │  │ (Primary +   │  │  (Prometheus │
        │                  │  │  Replicas)   │  │  + Grafana)  │
        │ - Task Queue     │  │              │  │              │
        │ - Results        │  │ - Metadata   │  │ - Metrics    │
        │ - Cache          │  │ - State      │  │ - Logs       │
        └──────────────────┘  └──────────────┘  └──────────────┘
                   │                 │
                   └────────┬────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  SQL Server  │ │  Snowflake   │ │   AWS S3     │
    │  (Source)    │ │ (Destination)│ │ (Destination)│
    └──────────────┘ └──────────────┘ └──────────────┘
```

## Core Components

### 1. API Layer (FastAPI)

**Responsibilities:**
- REST API endpoints for CRUD operations
- WebSocket server for real-time updates
- Request validation and authentication
- Business logic orchestration
- Rate limiting and throttling

**Technology:**
- FastAPI 0.104+ (async/await support)
- Uvicorn ASGI server
- Pydantic for validation
- JWT for authentication (production)

**Scaling:**
- Stateless design for horizontal scaling
- Multiple instances behind load balancer
- Sticky sessions for WebSocket connections
- Connection pooling for database

**Health Check Endpoint:**
```python
GET /health
Response: {"status": "healthy", "version": "1.0.0"}
```

### 2. Task Queue (Celery)

**Responsibilities:**
- Asynchronous task execution
- Task scheduling and retry logic
- Distributed task processing
- Result tracking and persistence

**Task Types:**
- `execute_task` - Full load execution
- `execute_cdc_polling` - CDC synchronization
- `start_task` - Task initialization
- `stop_task` - Graceful task termination

**Configuration:**
- Broker: Redis (with persistence)
- Result Backend: Redis
- Serializer: JSON
- Prefetch Multiplier: 4
- Task Time Limit: 12 hours
- Soft Time Limit: 11 hours

**Worker Deployment:**
```bash
# Production worker with concurrency
celery -A celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100 \
  --time-limit=43200
```

### 3. Message Broker (Redis Cluster)

**Responsibilities:**
- Task queue management
- Result storage
- Distributed locking
- Cache layer

**Production Setup:**
- Redis Cluster mode (3+ nodes)
- Redis Sentinel for HA
- AOF + RDB persistence
- Memory limit with eviction policy
- Regular backups

**Configuration:**
```redis
# Redis config for production
maxmemory 4gb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
save 900 1
save 300 10
```

### 4. Metadata Database (PostgreSQL)

**Schema:**

```sql
-- Connectors (source/destination configurations)
CREATE TABLE connectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    connector_type VARCHAR(20) NOT NULL,
    source_type VARCHAR(50),
    destination_type VARCHAR(50),
    connection_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_tested_at TIMESTAMP,
    test_status VARCHAR(20)
);

CREATE INDEX idx_connectors_type ON connectors(connector_type);
CREATE INDEX idx_connectors_active ON connectors(is_active);

-- Tasks (transfer job definitions)
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    source_connector_id INTEGER REFERENCES connectors(id),
    destination_connector_id INTEGER REFERENCES connectors(id),
    source_tables JSONB NOT NULL,
    table_configs JSONB,
    mode VARCHAR(30) NOT NULL,
    batch_size_mb FLOAT DEFAULT 100,
    batch_rows INTEGER DEFAULT 50000,
    parallel_tables INTEGER DEFAULT 1,
    schedule_type VARCHAR(20) NOT NULL,
    schedule_interval_seconds INTEGER,
    s3_file_format VARCHAR(20),
    handle_schema_drift BOOLEAN DEFAULT true,
    retry_enabled BOOLEAN DEFAULT true,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 20,
    cleanup_on_retry BOOLEAN DEFAULT true,
    status VARCHAR(20) NOT NULL,
    current_progress_percent FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    cdc_enabled_tables JSONB,
    last_cdc_poll_at TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_source ON tasks(source_connector_id);
CREATE INDEX idx_tasks_destination ON tasks(destination_connector_id);
CREATE INDEX idx_tasks_active ON tasks(is_active);

-- Task Executions (execution logs and metrics)
CREATE TABLE task_executions (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    execution_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_rows BIGINT DEFAULT 0,
    processed_rows BIGINT DEFAULT 0,
    failed_rows BIGINT DEFAULT 0,
    progress_percent FLOAT DEFAULT 0,
    rows_per_second FLOAT,
    data_size_mb FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    error_message TEXT,
    cdc_lsn_start VARCHAR(100),
    cdc_lsn_end VARCHAR(100),
    schema_changes_detected JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_executions_task ON task_executions(task_id);
CREATE INDEX idx_executions_status ON task_executions(status);
CREATE INDEX idx_executions_started ON task_executions(started_at DESC);

-- Table Executions (per-table progress)
CREATE TABLE table_executions (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    task_execution_id INTEGER REFERENCES task_executions(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_rows BIGINT DEFAULT 0,
    processed_rows BIGINT DEFAULT 0,
    failed_rows BIGINT DEFAULT 0,
    progress_percent FLOAT DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_table_executions_task ON table_executions(task_id);
CREATE INDEX idx_table_executions_status ON table_executions(status);

-- Global Variables (dynamic path templates)
CREATE TABLE global_variables (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    variable_type VARCHAR(20) NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_variables_active ON global_variables(is_active);
```

**Connection Pooling:**
```python
# SQLAlchemy engine config
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 5. Connector Layer

**Architecture:**
```python
# Base connector interface
class BaseConnector:
    def connect(self) -> None
    def disconnect(self) -> None
    def test_connection(self) -> dict

class SourceConnector(BaseConnector):
    def list_tables(self) -> List[dict]
    def get_table_schema(self, table_name: str) -> List[dict]
    def read_data(self, table_name: str, batch_size: int) -> pd.DataFrame
    
class DestinationConnector(BaseConnector):
    def create_table(self, table_name: str, schema: List[dict]) -> None
    def write_data(self, table_name: str, data: pd.DataFrame) -> None
```

**Implemented Connectors:**

**SQL Server (Source):**
- Bulk read with batching
- CDC support (Change Data Capture)
- LSN tracking for incremental sync
- Connection pooling
- Retry logic for transient failures

**Snowflake (Destination):**
- Bulk load via staging
- PUT/COPY commands
- Schema evolution support
- Warehouse auto-suspend
- Query result caching

**AWS S3 (Destination):**
- Multiple format support (Parquet, CSV, JSON)
- Partitioned writes
- Server-side encryption
- Multipart upload for large files
- Metadata management

## Data Flow - Full Load

```
┌──────────────────────────────────────────────────────────────┐
│                   Full Load Execution Flow                    │
└──────────────────────────────────────────────────────────────┘

User initiates task
        │
        ▼
API creates Celery task
        │
        ▼
Worker picks up task ─────────┐
        │                     │
        ▼                     │ (Parallel processing)
For each table: ──────────────┤
        │                     │
        ▼                     │
1. Connect to source          │
2. Get table schema           │
3. Create destination table   │
4. Read data in batches ──────┤ (Batches processed in parallel)
5. Apply transformations      │
6. Write to destination       │
7. Update progress ──────────→ WebSocket broadcast
8. Commit to DB               │
        │                     │
        ▼                     │
All tables complete ←─────────┘
        │
        ▼
Mark task complete
Broadcast final status
```

## Data Flow - CDC

```
┌──────────────────────────────────────────────────────────────┐
│                   CDC Synchronization Flow                    │
└──────────────────────────────────────────────────────────────┘

Scheduled CDC poll (every N seconds)
        │
        ▼
Get last LSN from database
        │
        ▼
Query CDC tables for changes since LSN
        │
        ▼
Group changes by table
        │
        ▼
For each table with changes:
        │
        ├─→ Get change records
        ├─→ Apply transformations
        ├─→ Write to destination
        └─→ Update last LSN
        │
        ▼
Broadcast progress
        │
        ▼
Schedule next poll
```

## Scaling Strategy

### Horizontal Scaling

**API Layer:**
- Deploy 3+ instances behind load balancer
- Use sticky sessions for WebSocket
- Stateless design (no local state)
- Shared database for coordination

**Celery Workers:**
- Auto-scaling based on queue depth
- Min: 2 workers, Max: 20 workers
- Scale up: Queue > 10 tasks for 5 minutes
- Scale down: Queue < 2 tasks for 10 minutes

**Database:**
- Primary for writes
- 2+ read replicas for queries
- Connection pooling (20 connections/instance)
- Query result caching

**Redis:**
- Redis Cluster (6 nodes: 3 primary + 3 replicas)
- Sentinel for automatic failover
- Read from replicas for non-critical operations

### Vertical Scaling

**Memory Requirements:**
- API: 1GB per instance (baseline)
- Worker: 2-4GB per worker (depends on batch size)
- Redis: 4-8GB (depends on queue size)
- PostgreSQL: 8-16GB (depends on data volume)

**CPU Requirements:**
- API: 2 cores per instance
- Worker: 4 cores per worker (parallel processing)
- Redis: 2 cores
- PostgreSQL: 4-8 cores

## Performance Optimization

### Database Optimization

**Indexes:**
```sql
-- Frequently queried fields
CREATE INDEX CONCURRENTLY idx_tasks_status_active 
ON tasks(status, is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_executions_recent 
ON task_executions(task_id, started_at DESC);

-- Partial indexes for active tasks
CREATE INDEX CONCURRENTLY idx_running_tasks 
ON tasks(id) WHERE status = 'running';
```

**Query Optimization:**
- Use EXPLAIN ANALYZE for slow queries
- Add appropriate indexes
- Use connection pooling
- Enable query result caching

### Data Transfer Optimization

**Batch Size Tuning:**
- Small tables (< 100K rows): 10,000 rows/batch
- Medium tables (100K-1M rows): 50,000 rows/batch
- Large tables (> 1M rows): 100,000 rows/batch
- Adjust based on memory and network

**Parallel Processing:**
- Process 3-5 tables concurrently (default)
- Adjust based on worker CPU/memory
- Monitor resource utilization

**Network Optimization:**
- Enable compression for data transfer
- Use connection pooling
- Batch API calls
- Minimize network round trips

## Monitoring & Observability

### Application Metrics

**Key Metrics:**
```
# Task metrics
dtaas_tasks_total{status="completed|failed"}
dtaas_task_duration_seconds{task_name}
dtaas_task_rows_processed{task_name}

# API metrics
dtaas_api_requests_total{endpoint, method, status}
dtaas_api_request_duration_seconds{endpoint}

# Worker metrics
dtaas_celery_queue_length
dtaas_celery_active_workers
dtaas_celery_task_failures_total

# Database metrics
dtaas_db_connections_active
dtaas_db_query_duration_seconds
```

### Logging

**Structured Logging (JSON):**
```json
{
  "timestamp": "2025-10-24T10:30:15Z",
  "level": "INFO",
  "module": "transfer_service",
  "task_id": 123,
  "table_name": "dbo.Orders",
  "message": "Processing batch 5/10",
  "rows_processed": 50000,
  "progress_percent": 50.0
}
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Or Datadog / Splunk
- Retention: 30 days for INFO, 90 days for ERROR

### Alerting

**Critical Alerts:**
- Task failure rate > 10%
- API error rate > 5%
- Queue depth > 100 tasks
- Worker count = 0
- Database connection pool exhausted
- Redis memory > 90%

**Warning Alerts:**
- Task duration > 2x average
- Slow database queries > 1s
- High memory usage > 80%
- Disk space < 20%

## Security Architecture

### Authentication & Authorization

**JWT-based Authentication:**
```python
# Token structure
{
  "sub": "user@example.com",
  "role": "admin|operator|viewer",
  "exp": 1698156800,
  "iat": 1698153200
}

# Role permissions
Admin: Full access
Operator: Create/edit/run tasks, view all
Viewer: Read-only access
```

### Data Security

**Encryption:**
- At rest: Database encryption, S3 server-side encryption
- In transit: TLS 1.3 for all connections
- Credentials: Encrypted in database, env variables

**Network Security:**
- VPC with private subnets
- Security groups (least privilege)
- No public database access
- API behind WAF

**Secrets Management:**
- AWS Secrets Manager or HashiCorp Vault
- Rotate credentials every 90 days
- No hardcoded secrets
- Environment-based configuration

### Audit Logging

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    changes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Actions: CREATE, UPDATE, DELETE, START, STOP, PAUSE
```

## Disaster Recovery

### Backup Strategy

**Database Backups:**
- Automated daily full backups
- Point-in-time recovery (PITR)
- Retention: 30 days
- Test restore monthly

**Redis Backups:**
- AOF persistence
- Daily RDB snapshots
- Retention: 7 days

**Application Code:**
- Version controlled in Git
- Tagged releases
- Artifact storage (Docker registry)

### Recovery Procedures

**RTO (Recovery Time Objective): 2 hours**
**RPO (Recovery Point Objective): 15 minutes**

**Recovery Steps:**
1. Restore database from backup (30 min)
2. Deploy application containers (15 min)
3. Restore Redis state (15 min)
4. Verify all services (30 min)
5. Resume tasks (30 min)

## Cost Optimization

### Resource Optimization

**Compute:**
- Use spot instances for non-critical workers
- Auto-scaling based on demand
- Rightsize instances (monitor utilization)

**Storage:**
- S3 Intelligent-Tiering
- Compress historical data
- Archive old task executions

**Database:**
- Use read replicas for reporting
- Enable query result caching
- Use reserved instances for production

### Monitoring Costs

**Cost Metrics:**
- API calls per day
- Data transferred (GB)
- Worker hours
- Database storage
- S3 storage and requests

**Cost Optimization Tips:**
- Batch small transfers
- Schedule large transfers during off-peak hours
- Clean up old data
- Monitor and optimize slow queries

## Production Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance testing done
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] DR plan documented
- [ ] Runbooks created

### Deployment
- [ ] Blue-green deployment
- [ ] Database migrations tested
- [ ] Health checks verified
- [ ] Load testing completed
- [ ] Rollback plan ready

### Post-Deployment
- [ ] Monitor metrics for 24 hours
- [ ] Verify all integrations
- [ ] Test critical flows
- [ ] Document any issues
- [ ] Update runbooks

---

For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

For production readiness checklist, see [PRODUCTION_READY.md](./PRODUCTION_READY.md)
