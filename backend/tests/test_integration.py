"""
Integration Tests
End-to-end tests for complete workflows
"""
import pytest
from datetime import datetime
import models
import schemas


@pytest.mark.integration
class TestCompleteDataTransferFlow:
    """Test complete data transfer workflow"""
    
    def test_full_workflow_source_to_destination(
        self,
        db_session,
        sample_source_connector,
        sample_destination_connector
    ):
        """Test complete flow: create connectors, create task, execute"""
        # Step 1: Verify connectors exist
        assert sample_source_connector.id is not None
        assert sample_destination_connector.id is not None
        
        # Step 2: Create task
        task = models.Task(
            name="Integration Test Task",
            description="End-to-end test",
            source_connector_id=sample_source_connector.id,
            destination_connector_id=sample_destination_connector.id,
            mode=models.TaskMode.FULL_LOAD,
            schedule_type=models.TaskScheduleType.ON_DEMAND,
            config={
                "tables": ["test_table"],
                "batch_size": 10000
            },
            status=models.TaskStatus.CREATED
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Step 3: Start task
        task.status = models.TaskStatus.RUNNING
        task.last_run_at = datetime.utcnow()
        db_session.commit()
        
        # Step 4: Create execution record
        execution = models.TaskExecution(
            task_id=task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_rows=1000,
            processed_rows=0
        )
        db_session.add(execution)
        db_session.commit()
        
        # Step 5: Update execution progress
        execution.processed_rows = 500
        db_session.commit()
        assert execution.processed_rows == 500
        
        # Step 6: Complete execution
        execution.status = models.ExecutionStatus.SUCCESS
        execution.processed_rows = 1000
        execution.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Step 7: Verify task completed
        task.status = models.TaskStatus.COMPLETED
        db_session.commit()
        
        # Assertions
        assert task.status == models.TaskStatus.COMPLETED
        assert execution.status == models.ExecutionStatus.SUCCESS
        assert execution.processed_rows == 1000
    
    def test_cdc_workflow(
        self,
        db_session,
        sample_source_connector,
        sample_destination_connector
    ):
        """Test CDC (Change Data Capture) workflow"""
        # Create CDC task
        task = models.Task(
            name="CDC Test Task",
            source_connector_id=sample_source_connector.id,
            destination_connector_id=sample_destination_connector.id,
            mode=models.TaskMode.CDC,
            schedule_type=models.TaskScheduleType.CONTINUOUS,
            config={
                "tables": ["orders", "customers"],
                "cdc_interval": 60
            },
            status=models.TaskStatus.CREATED
        )
        db_session.add(task)
        db_session.commit()
        
        # Start CDC
        task.status = models.TaskStatus.RUNNING
        db_session.commit()
        
        # Create first CDC execution
        execution1 = models.TaskExecution(
            task_id=task.id,
            status=models.ExecutionStatus.SUCCESS,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_rows=10,
            processed_rows=10
        )
        db_session.add(execution1)
        db_session.commit()
        
        # Create second CDC execution (catching more changes)
        execution2 = models.TaskExecution(
            task_id=task.id,
            status=models.ExecutionStatus.SUCCESS,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_rows=5,
            processed_rows=5
        )
        db_session.add(execution2)
        db_session.commit()
        
        # Verify multiple executions
        assert len(task.executions) == 2
        assert all(e.status == models.ExecutionStatus.SUCCESS for e in task.executions)


@pytest.mark.integration
class TestVariableResolution:
    """Test variable resolution in real scenarios"""
    
    def test_static_variable_in_task(self, db_session, sample_task):
        """Test using static variable in task configuration"""
        # Create static variable
        variable = models.GlobalVariable(
            name="tenant_id",
            description="Tenant ID",
            variable_type=models.VariableType.STATIC,
            config={"value": "12345"}
        )
        db_session.add(variable)
        db_session.commit()
        
        # Update task to use variable
        task_config = sample_task.config.copy()
        task_config["query"] = "SELECT * FROM orders WHERE tenant_id = {{tenant_id}}"
        sample_task.config = task_config
        db_session.commit()
        
        # Verify variable is referenced
        assert "{{tenant_id}}" in sample_task.config["query"]
        
        # Variable resolution would happen at runtime
        # Here we just verify the setup is correct
        var = db_session.query(models.GlobalVariable).filter_by(name="tenant_id").first()
        assert var is not None
        assert var.config["value"] == "12345"
    
    def test_db_query_variable_in_task(self, db_session, sample_task):
        """Test using database query variable"""
        variable = models.GlobalVariable(
            name="max_date",
            description="Maximum date from source",
            variable_type=models.VariableType.DB_QUERY,
            config={
                "server": "localhost",
                "database": "source_db",
                "table": "orders",
                "column": "order_date",
                "aggregation": "MAX"
            }
        )
        db_session.add(variable)
        db_session.commit()
        
        # Use variable in task
        task_config = sample_task.config.copy()
        task_config["query"] = "SELECT * FROM orders WHERE order_date > {{max_date}}"
        sample_task.config = task_config
        db_session.commit()
        
        assert "{{max_date}}" in sample_task.config["query"]


@pytest.mark.integration
class TestMultiTableTransfer:
    """Test transferring multiple tables"""
    
    def test_parallel_table_transfer(
        self,
        db_session,
        sample_task
    ):
        """Test transferring multiple tables in parallel"""
        # Create execution
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        # Create table executions for multiple tables
        tables = ["customers", "orders", "products"]
        table_executions = []
        
        for table_name in tables:
            table_exec = models.TableExecution(
                task_execution_id=execution.id,
                table_name=table_name,
                total_rows=1000,
                processed_rows=0,
                failed_rows=0,
                status="running",
                started_at=datetime.utcnow()
            )
            db_session.add(table_exec)
            table_executions.append(table_exec)
        
        db_session.commit()
        
        # Simulate parallel execution completion
        for table_exec in table_executions:
            table_exec.processed_rows = table_exec.total_rows
            table_exec.status = "completed"
            table_exec.completed_at = datetime.utcnow()
        
        db_session.commit()
        
        # Verify all tables completed
        assert all(te.status == "completed" for te in table_executions)
        assert len(execution.table_executions) == 3
    
    def test_sequential_table_transfer_with_retry(
        self,
        db_session,
        sample_task
    ):
        """Test sequential table transfer with retry on failure"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        # Create table execution that fails
        table_exec = models.TableExecution(
            task_execution_id=execution.id,
            table_name="problematic_table",
            total_rows=5000,
            processed_rows=2000,
            failed_rows=0,
            status="failed",
            retry_count=0,
            started_at=datetime.utcnow(),
            error_message="Connection timeout"
        )
        db_session.add(table_exec)
        db_session.commit()
        
        # Retry the table
        table_exec.retry_count += 1
        table_exec.status = "running"
        table_exec.error_message = None
        db_session.commit()
        
        # Successfully complete on retry
        table_exec.processed_rows = 5000
        table_exec.status = "completed"
        table_exec.completed_at = datetime.utcnow()
        db_session.commit()
        
        assert table_exec.retry_count == 1
        assert table_exec.status == "completed"


@pytest.mark.integration
class TestErrorRecovery:
    """Test error handling and recovery"""
    
    def test_task_failure_and_recovery(
        self,
        db_session,
        sample_task
    ):
        """Test task failure and recovery"""
        # Start task
        sample_task.status = models.TaskStatus.RUNNING
        db_session.commit()
        
        # Create failed execution
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.FAILED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message="Database connection failed"
        )
        db_session.add(execution)
        db_session.commit()
        
        # Mark task as failed
        sample_task.status = models.TaskStatus.FAILED
        db_session.commit()
        
        # Retry task
        sample_task.status = models.TaskStatus.RUNNING
        db_session.commit()
        
        # Create successful execution
        execution2 = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.SUCCESS,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_rows=1000,
            processed_rows=1000
        )
        db_session.add(execution2)
        db_session.commit()
        
        # Complete task
        sample_task.status = models.TaskStatus.COMPLETED
        db_session.commit()
        
        # Verify recovery
        assert sample_task.status == models.TaskStatus.COMPLETED
        assert len(sample_task.executions) == 2
        assert sample_task.executions[-1].status == models.ExecutionStatus.SUCCESS


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance with large datasets"""
    
    def test_large_execution_batch(self, db_session, sample_task):
        """Test handling many table executions"""
        execution = models.TaskExecution(
            task_id=sample_task.id,
            status=models.ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db_session.add(execution)
        db_session.commit()
        
        # Create many table executions
        for i in range(100):
            table_exec = models.TableExecution(
                task_execution_id=execution.id,
                table_name=f"table_{i}",
                total_rows=1000,
                processed_rows=1000,
                failed_rows=0,
                status="completed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db_session.add(table_exec)
        
        db_session.commit()
        
        # Verify all created
        assert len(execution.table_executions) == 100

