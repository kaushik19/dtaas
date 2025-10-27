"""
Unit Tests for Database Models
Tests all SQLAlchemy models
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import models


@pytest.mark.unit
class TestConnectorModel:
    """Test Connector model"""
    
    def test_create_connector(self, db_session):
        """Test creating a connector"""
        connector = models.Connector(
            name="Test Connector",
            description="Test Description",
            connector_type=models.ConnectorType.SOURCE,
            source_type=models.SourceType.SQL_SERVER,
            connection_config={"host": "localhost"}
        )
        db_session.add(connector)
        db_session.commit()
        
        assert connector.id is not None
        assert connector.name == "Test Connector"
        assert connector.connector_type == models.ConnectorType.SOURCE
        assert connector.source_type == models.SourceType.SQL_SERVER
        assert connector.created_at is not None
    
    def test_connector_unique_name(self, db_session):
        """Test connector name uniqueness"""
        connector1 = models.Connector(
            name="Unique Name",
            connector_type=models.ConnectorType.SOURCE,
            source_type=models.SourceType.SQL_SERVER,
            connection_config={}
        )
        db_session.add(connector1)
        db_session.commit()
        
        connector2 = models.Connector(
            name="Unique Name",
            connector_type=models.ConnectorType.SOURCE,
            source_type=models.SourceType.SQL_SERVER,
            connection_config={}
        )
        db_session.add(connector2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_connector_relationships(self, db_session, sample_connector):
        """Test connector relationships with tasks"""
        task = models.Task(
            name="Test Task",
            source_connector_id=sample_connector.id,
            destination_connector_id=sample_connector.id,
            mode=models.TaskMode.FULL_LOAD,
            schedule_type=models.TaskScheduleType.ON_DEMAND,
            config={},
            status=models.TaskStatus.CREATED
        )
        db_session.add(task)
        db_session.commit()
        
        assert len(sample_connector.source_tasks) == 1
        assert sample_connector.source_tasks[0].name == "Test Task"


@pytest.mark.unit
class TestTaskModel:
    """Test Task model"""
    
    def test_create_task(self, db_session, sample_source_connector, sample_destination_connector):
        """Test creating a task"""
        task = models.Task(
            name="Test Task",
            description="Test Task Description",
            source_connector_id=sample_source_connector.id,
            destination_connector_id=sample_destination_connector.id,
            mode=models.TaskMode.FULL_LOAD,
            schedule_type=models.TaskScheduleType.ON_DEMAND,
            config={"batch_size": 10000},
            status=models.TaskStatus.CREATED
        )
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.name == "Test Task"
        assert task.mode == models.TaskMode.FULL_LOAD
        assert task.status == models.TaskStatus.CREATED
        assert task.config["batch_size"] == 10000
    
    def test_task_status_transitions(self, db_session, sample_task):
        """Test task status transitions"""
        assert sample_task.status == models.TaskStatus.CREATED
        
        sample_task.status = models.TaskStatus.RUNNING
        db_session.commit()
        assert sample_task.status == models.TaskStatus.RUNNING
        
        sample_task.status = models.TaskStatus.COMPLETED
        db_session.commit()
        assert sample_task.status == models.TaskStatus.COMPLETED
    
    def test_task_executions_relationship(self, db_session, sample_task):
        """Test task execution relationships"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        assert len(sample_task.executions) == 1
        assert sample_task.executions[0].status == models.ExecutionStatus.RUNNING


@pytest.mark.unit
class TestTaskExecutionModel:
    """Test TaskExecution model"""
    
    def test_create_execution(self, db_session, sample_task):
        """Test creating a task execution"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_rows=1000,
            processed_rows=0,
            failed_rows=0
        )
        db_session.add(execution)
        db_session.commit()
        
        assert execution.id is not None
        assert execution.task_id == sample_task.id
        assert execution.status == models.ExecutionStatus.RUNNING
        assert execution.total_rows == 1000
    
    def test_execution_progress_calculation(self, db_session, sample_task):
        """Test execution progress calculation"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_rows=1000,
            processed_rows=500,
            failed_rows=10
        )
        db_session.add(execution)
        db_session.commit()
        
        progress = (execution.processed_rows / execution.total_rows) * 100
        assert progress == 50.0
    
    def test_table_executions_relationship(self, db_session, sample_task):
        """Test table execution relationships"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        table_exec = models.TableExecution(
            task_execution_id=execution.id,
            table_name="test_table",
            total_rows=100,
            processed_rows=0,
            failed_rows=0,
            status="running",
            started_at=datetime.utcnow()
        )
        db_session.add(table_exec)
        db_session.commit()
        
        assert len(execution.table_executions) == 1
        assert execution.table_executions[0].table_name == "test_table"


@pytest.mark.unit
class TestGlobalVariableModel:
    """Test GlobalVariable model"""
    
    def test_create_static_variable(self, db_session):
        """Test creating a static variable"""
        variable = models.GlobalVariable(
            name="static_var",
            description="Static Variable",
            variable_type=models.VariableType.STATIC,
            config={"value": "test_value"}
        )
        db_session.add(variable)
        db_session.commit()
        
        assert variable.id is not None
        assert variable.name == "static_var"
        assert variable.variable_type == models.VariableType.STATIC
        assert variable.config["value"] == "test_value"
    
    def test_create_db_query_variable(self, db_session):
        """Test creating a database query variable"""
        variable = models.GlobalVariable(
            name="db_query_var",
            description="DB Query Variable",
            variable_type=models.VariableType.DB_QUERY,
            config={
                "server": "localhost",
                "database": "testdb",
                "table": "config",
                "column": "value"
            }
        )
        db_session.add(variable)
        db_session.commit()
        
        assert variable.id is not None
        assert variable.variable_type == models.VariableType.DB_QUERY
        assert variable.config["server"] == "localhost"
    
    def test_variable_unique_name(self, db_session):
        """Test variable name uniqueness"""
        var1 = models.GlobalVariable(
            name="unique_var",
            variable_type=models.VariableType.STATIC,
            config={"value": "value1"}
        )
        db_session.add(var1)
        db_session.commit()
        
        var2 = models.GlobalVariable(
            name="unique_var",
            variable_type=models.VariableType.STATIC,
            config={"value": "value2"}
        )
        db_session.add(var2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.unit
class TestTableExecutionModel:
    """Test TableExecution model"""
    
    def test_create_table_execution(self, db_session, sample_task):
        """Test creating a table execution"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        table_exec = models.TableExecution(
            task_execution_id=execution.id,
            table_name="customers",
            total_rows=5000,
            processed_rows=1000,
            failed_rows=0,
            status="running",
            started_at=datetime.utcnow()
        )
        db_session.add(table_exec)
        db_session.commit()
        
        assert table_exec.id is not None
        assert table_exec.table_name == "customers"
        assert table_exec.total_rows == 5000
        assert table_exec.processed_rows == 1000
    
    def test_table_execution_retry(self, db_session, sample_task):
        """Test table execution retry mechanism"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        table_exec = models.TableExecution(
            task_execution_id=execution.id,
            table_name="orders",
            total_rows=100,
            processed_rows=0,
            failed_rows=0,
            status="failed",
            retry_count=0,
            started_at=datetime.utcnow()
        )
        db_session.add(table_exec)
        db_session.commit()
        
        # Simulate retry
        table_exec.retry_count += 1
        table_exec.status = "running"
        db_session.commit()
        
        assert table_exec.retry_count == 1
        assert table_exec.status == "running"


@pytest.mark.unit
class TestEnums:
    """Test all enum types"""
    
    def test_connector_type_enum(self):
        """Test ConnectorType enum"""
        assert models.ConnectorType.SOURCE.value == "source"
        assert models.ConnectorType.DESTINATION.value == "destination"
    
    def test_source_type_enum(self):
        """Test SourceType enum"""
        assert models.SourceType.SQL_SERVER.value == "sql_server"
        assert models.SourceType.POSTGRESQL.value == "postgresql"
        assert models.SourceType.MYSQL.value == "mysql"
        assert models.SourceType.ORACLE.value == "oracle"
    
    def test_destination_type_enum(self):
        """Test DestinationType enum"""
        assert models.DestinationType.SNOWFLAKE.value == "snowflake"
        assert models.DestinationType.S3.value == "s3"
    
    def test_task_mode_enum(self):
        """Test TaskMode enum"""
        assert models.TaskMode.FULL_LOAD.value == "full_load"
        assert models.TaskMode.CDC.value == "cdc"
        assert models.TaskMode.FULL_LOAD_THEN_CDC.value == "full_load_then_cdc"
    
    def test_task_status_enum(self):
        """Test TaskStatus enum"""
        assert models.TaskStatus.CREATED.value == "created"
        assert models.TaskStatus.RUNNING.value == "running"
        assert models.TaskStatus.COMPLETED.value == "completed"
        assert models.TaskStatus.FAILED.value == "failed"

