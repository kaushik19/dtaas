from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class ConnectorTypeEnum(str, Enum):
    SOURCE = "source"
    DESTINATION = "destination"


class SourceTypeEnum(str, Enum):
    SQL_SERVER = "sql_server"


class DestinationTypeEnum(str, Enum):
    SNOWFLAKE = "snowflake"
    S3 = "s3"


class TaskModeEnum(str, Enum):
    FULL_LOAD = "full_load"
    CDC = "cdc"
    FULL_LOAD_THEN_CDC = "full_load_then_cdc"


class TaskScheduleTypeEnum(str, Enum):
    ON_DEMAND = "on_demand"
    CONTINUOUS = "continuous"
    INTERVAL = "interval"


class TaskStatusEnum(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class S3FileFormatEnum(str, Enum):
    PARQUET = "parquet"
    CSV = "csv"
    JSON = "json"


# Connector Schemas
class ConnectorBase(BaseModel):
    name: str
    description: Optional[str] = None
    connector_type: ConnectorTypeEnum
    source_type: Optional[SourceTypeEnum] = None
    destination_type: Optional[DestinationTypeEnum] = None
    connection_config: Dict[str, Any]


class ConnectorCreate(ConnectorBase):
    pass


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ConnectorResponse(ConnectorBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_tested_at: Optional[datetime] = None
    test_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConnectorTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class TableInfo(BaseModel):
    schema_name: str
    table_name: str
    row_count: Optional[int] = None
    columns: List[Dict[str, Any]]
    cdc_enabled: bool = False


# Transformation Schemas
class TransformationRule(BaseModel):
    type: str  # add_column, modify_column, filter, etc.
    config: Dict[str, Any]


# Task Schemas
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_connector_id: int
    destination_connector_id: int
    source_tables: List[str]
    table_mappings: Optional[Dict[str, str]] = None
    mode: TaskModeEnum = TaskModeEnum.FULL_LOAD
    batch_size_mb: float = 50.0
    batch_rows: int = 10000
    schedule_type: TaskScheduleTypeEnum = TaskScheduleTypeEnum.ON_DEMAND
    schedule_interval_seconds: Optional[int] = None
    s3_file_format: Optional[S3FileFormatEnum] = None
    transformations: Optional[List[TransformationRule]] = None
    handle_schema_drift: bool = True


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_tables: Optional[List[str]] = None
    table_mappings: Optional[Dict[str, str]] = None
    mode: Optional[TaskModeEnum] = None
    batch_size_mb: Optional[float] = None
    batch_rows: Optional[int] = None
    schedule_type: Optional[TaskScheduleTypeEnum] = None
    schedule_interval_seconds: Optional[int] = None
    s3_file_format: Optional[S3FileFormatEnum] = None
    transformations: Optional[List[TransformationRule]] = None
    handle_schema_drift: Optional[bool] = None
    is_active: Optional[bool] = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatusEnum
    current_progress_percent: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    cdc_enabled_tables: Optional[Dict[str, Any]] = None
    last_cdc_poll_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TaskControlRequest(BaseModel):
    action: str  # start, stop, pause, resume


# Task Execution Schemas
class TaskExecutionResponse(BaseModel):
    id: int
    task_id: int
    execution_type: str
    status: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    progress_percent: float
    rows_per_second: Optional[float] = None
    data_size_mb: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    schema_changes_detected: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Dashboard Metrics
class DashboardMetrics(BaseModel):
    total_tasks: int
    active_tasks: int
    running_tasks: int
    total_rows_transferred: int
    total_data_transferred_mb: float
    successful_executions: int
    failed_executions: int
    avg_rows_per_second: float
    recent_executions: List[TaskExecutionResponse]


# WebSocket Messages
class ProgressUpdate(BaseModel):
    task_id: int
    execution_id: int
    progress_percent: float
    processed_rows: int
    total_rows: int
    rows_per_second: Optional[float] = None
    status: str
    message: Optional[str] = None

