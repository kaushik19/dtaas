from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class ConnectorType(str, enum.Enum):
    SOURCE = "source"
    DESTINATION = "destination"


class SourceType(str, enum.Enum):
    SQL_SERVER = "sql_server"
    # Future: MYSQL, POSTGRESQL, etc.


class DestinationType(str, enum.Enum):
    SNOWFLAKE = "snowflake"
    S3 = "s3"
    # Future: AZURE_BLOB, GCS, etc.


class TaskMode(str, enum.Enum):
    FULL_LOAD = "full_load"
    CDC = "cdc"
    FULL_LOAD_THEN_CDC = "full_load_then_cdc"


class TaskScheduleType(str, enum.Enum):
    ON_DEMAND = "on_demand"
    CONTINUOUS = "continuous"
    INTERVAL = "interval"


class TaskStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class Connector(Base):
    __tablename__ = "connectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    connector_type = Column(String(20), nullable=False)  # source or destination
    source_type = Column(String(50), nullable=True)  # sql_server, mysql, etc.
    destination_type = Column(String(50), nullable=True)  # snowflake, s3, etc.
    
    # Connection details stored as JSON
    connection_config = Column(JSON, nullable=False)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_tested_at = Column(DateTime, nullable=True)
    test_status = Column(String(20), nullable=True)  # success, failed
    
    # Relationships
    source_tasks = relationship("Task", foreign_keys="Task.source_connector_id", back_populates="source_connector")
    destination_tasks = relationship("Task", foreign_keys="Task.destination_connector_id", back_populates="destination_connector")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Connector references
    source_connector_id = Column(Integer, ForeignKey("connectors.id"), nullable=False)
    destination_connector_id = Column(Integer, ForeignKey("connectors.id"), nullable=False)
    
    # Table and data configuration
    source_tables = Column(JSON, nullable=False)  # List of table names to transfer
    table_mappings = Column(JSON, nullable=True)  # Custom table name mappings
    
    # Transfer mode
    mode = Column(String(30), nullable=False, default="full_load")  # full_load, cdc, full_load_then_cdc
    
    # Batch configuration
    batch_size_mb = Column(Float, default=50.0)  # Batch size in MB
    batch_rows = Column(Integer, default=10000)  # Alternative: batch by row count
    
    # Schedule configuration
    schedule_type = Column(String(20), nullable=False, default="on_demand")
    schedule_interval_seconds = Column(Integer, nullable=True)  # For interval scheduling
    
    # S3 specific configuration
    s3_file_format = Column(String(20), nullable=True)  # parquet, csv, json
    
    # Data transformation rules
    transformations = Column(JSON, nullable=True)  # List of transformation rules
    
    # Schema drift handling
    handle_schema_drift = Column(Boolean, default=True)
    
    # Status
    status = Column(String(20), default="created")
    current_progress_percent = Column(Float, default=0.0)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    
    # CDC specific
    cdc_enabled_tables = Column(JSON, nullable=True)  # Tables with CDC enabled
    last_cdc_poll_at = Column(DateTime, nullable=True)
    
    # Relationships
    source_connector = relationship("Connector", foreign_keys=[source_connector_id], back_populates="source_tasks")
    destination_connector = relationship("Connector", foreign_keys=[destination_connector_id], back_populates="destination_tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")


class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    # Execution details
    execution_type = Column(String(20), nullable=False)  # full_load, cdc_sync
    status = Column(String(20), default="pending")
    
    # Progress tracking
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)
    
    # Performance metrics
    rows_per_second = Column(Float, nullable=True)
    data_size_mb = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # CDC specific
    cdc_lsn_start = Column(String(100), nullable=True)  # Starting LSN for CDC
    cdc_lsn_end = Column(String(100), nullable=True)  # Ending LSN for CDC
    
    # Schema drift tracking
    schema_changes_detected = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="executions")
    table_executions = relationship("TableExecution", back_populates="task_execution", cascade="all, delete-orphan")


class TableExecution(Base):
    __tablename__ = "table_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_execution_id = Column(Integer, ForeignKey("task_executions.id"), nullable=False)
    
    # Table details
    table_name = Column(String(255), nullable=False)
    
    # Progress
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="pending")
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error details
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task_execution = relationship("TaskExecution", back_populates="table_executions")


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metrics
    metric_type = Column(String(50), nullable=False)  # tasks_running, rows_transferred, etc.
    metric_value = Column(Float, nullable=False)
    metric_data = Column(JSON, nullable=True)  # Additional metric details
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

