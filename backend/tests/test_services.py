"""
Unit Tests for Service Layer
Tests connector_service, task_service, variable_service, etc.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import models
import schemas
from services.connector_service import ConnectorService
from services.task_service import TaskService
from services.variable_service import VariableService


@pytest.mark.unit
class TestConnectorService:
    """Test ConnectorService"""
    
    def test_create_connector(self, db_session):
        """Test creating a connector"""
        connector_data = schemas.ConnectorCreate(
            name="Test Connector",
            description="Test",
            connector_type=schemas.ConnectorTypeEnum.SOURCE,
            source_type=schemas.SourceTypeEnum.SQL_SERVER,
            connection_config={"host": "localhost"}
        )
        
        result = ConnectorService.create_connector(db_session, connector_data)
        
        assert result.id is not None
        assert result.name == "Test Connector"
        assert result.source_type == models.SourceType.SQL_SERVER
    
    def test_get_connector(self, db_session, sample_connector):
        """Test getting connector by ID"""
        result = ConnectorService.get_connector(db_session, sample_connector.id)
        
        assert result is not None
        assert result.id == sample_connector.id
        assert result.name == sample_connector.name
    
    def test_get_connector_not_found(self, db_session):
        """Test getting non-existent connector"""
        result = ConnectorService.get_connector(db_session, 99999)
        assert result is None
    
    def test_get_connector_by_name(self, db_session, sample_connector):
        """Test getting connector by name"""
        result = ConnectorService.get_connector_by_name(
            db_session, 
            sample_connector.name
        )
        
        assert result is not None
        assert result.name == sample_connector.name
    
    def test_list_connectors(self, db_session, sample_connector):
        """Test listing all connectors"""
        result = ConnectorService.list_connectors(db_session)
        
        assert len(result) >= 1
        assert any(c.id == sample_connector.id for c in result)
    
    def test_list_connectors_by_type(self, db_session, sample_source_connector):
        """Test listing connectors filtered by type"""
        result = ConnectorService.list_connectors(
            db_session,
            connector_type="source"
        )
        
        assert all(c.connector_type == models.ConnectorType.SOURCE for c in result)
    
    def test_update_connector(self, db_session, sample_connector):
        """Test updating a connector"""
        update_data = schemas.ConnectorUpdate(
            name="Updated Name",
            description="Updated Description"
        )
        
        result = ConnectorService.update_connector(
            db_session,
            sample_connector.id,
            update_data
        )
        
        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
    
    def test_delete_connector(self, db_session, sample_connector):
        """Test deleting a connector"""
        connector_id = sample_connector.id
        
        result = ConnectorService.delete_connector(db_session, connector_id)
        
        assert result is True
        deleted = ConnectorService.get_connector(db_session, connector_id)
        assert deleted is None
    
    @patch('services.connector_service.SQLServerConnector')
    def test_test_connection_success(self, mock_connector_class, db_session):
        """Test successful connection test"""
        mock_instance = Mock()
        mock_instance.test_connection.return_value = {
            "success": True,
            "message": "Connection successful"
        }
        mock_connector_class.return_value = mock_instance
        
        test_request = schemas.ConnectorTestRequest(
            connector_type=schemas.ConnectorTypeEnum.SOURCE,
            source_type=schemas.SourceTypeEnum.SQL_SERVER,
            connection_config={"host": "localhost"}
        )
        
        result = ConnectorService.test_connection(db_session, test_request)
        
        assert result["success"] is True
        assert "Connection successful" in result["message"]
    
    @patch('services.connector_service.SQLServerConnector')
    def test_test_connection_failure(self, mock_connector_class, db_session):
        """Test failed connection test"""
        mock_instance = Mock()
        mock_instance.test_connection.side_effect = Exception("Connection failed")
        mock_connector_class.return_value = mock_instance
        
        test_request = schemas.ConnectorTestRequest(
            connector_type=schemas.ConnectorTypeEnum.SOURCE,
            source_type=schemas.SourceTypeEnum.SQL_SERVER,
            connection_config={"host": "invalid"}
        )
        
        result = ConnectorService.test_connection(db_session, test_request)
        
        assert result["success"] is False
        assert "Connection failed" in result["message"]


@pytest.mark.unit
class TestTaskService:
    """Test TaskService"""
    
    def test_create_task(
        self, 
        db_session, 
        sample_source_connector, 
        sample_destination_connector
    ):
        """Test creating a task"""
        task_data = schemas.TaskCreate(
            name="Test Task",
            description="Test",
            source_connector_id=sample_source_connector.id,
            destination_connector_id=sample_destination_connector.id,
            mode=schemas.TaskModeEnum.FULL_LOAD,
            schedule_type=schemas.TaskScheduleTypeEnum.ON_DEMAND,
            config={"batch_size": 10000}
        )
        
        result = TaskService.create_task(db_session, task_data)
        
        assert result.id is not None
        assert result.name == "Test Task"
        assert result.status == models.TaskStatus.CREATED
    
    def test_get_task(self, db_session, sample_task):
        """Test getting task by ID"""
        result = TaskService.get_task(db_session, sample_task.id)
        
        assert result is not None
        assert result.id == sample_task.id
        assert result.name == sample_task.name
    
    def test_list_tasks(self, db_session, sample_task):
        """Test listing all tasks"""
        result = TaskService.list_tasks(db_session)
        
        assert len(result) >= 1
        assert any(t.id == sample_task.id for t in result)
    
    def test_update_task(self, db_session, sample_task):
        """Test updating a task"""
        update_data = schemas.TaskUpdate(
            name="Updated Task",
            config={"batch_size": 20000}
        )
        
        result = TaskService.update_task(
            db_session,
            sample_task.id,
            update_data
        )
        
        assert result.name == "Updated Task"
        assert result.config["batch_size"] == 20000
    
    def test_delete_task(self, db_session, sample_task):
        """Test deleting a task"""
        task_id = sample_task.id
        
        result = TaskService.delete_task(db_session, task_id)
        
        assert result is True
        deleted = TaskService.get_task(db_session, task_id)
        assert deleted is None
    
    def test_start_task(self, db_session, sample_task):
        """Test starting a task"""
        result = TaskService.start_task(db_session, sample_task.id)
        
        assert result.status == models.TaskStatus.RUNNING
        assert result.last_run_at is not None
    
    def test_stop_task(self, db_session, sample_task):
        """Test stopping a task"""
        # First start the task
        sample_task.status = models.TaskStatus.RUNNING
        db_session.commit()
        
        result = TaskService.stop_task(db_session, sample_task.id)
        
        assert result.status == models.TaskStatus.STOPPED
    
    def test_pause_task(self, db_session, sample_task):
        """Test pausing a task"""
        sample_task.status = models.TaskStatus.RUNNING
        db_session.commit()
        
        result = TaskService.pause_task(db_session, sample_task.id)
        
        assert result.status == models.TaskStatus.PAUSED
    
    def test_resume_task(self, db_session, sample_task):
        """Test resuming a paused task"""
        sample_task.status = models.TaskStatus.PAUSED
        db_session.commit()
        
        result = TaskService.resume_task(db_session, sample_task.id)
        
        assert result.status == models.TaskStatus.RUNNING


@pytest.mark.unit
class TestVariableService:
    """Test VariableService"""
    
    def test_create_variable(self, db_session):
        """Test creating a variable"""
        var_data = schemas.GlobalVariableCreate(
            name="test_var",
            description="Test Variable",
            variable_type=schemas.VariableTypeEnum.STATIC,
            config={"value": "test_value"}
        )
        
        result = VariableService.create_variable(db_session, var_data)
        
        assert result.id is not None
        assert result.name == "test_var"
        assert result.config["value"] == "test_value"
    
    def test_get_variable(self, db_session, sample_variable):
        """Test getting variable by ID"""
        result = VariableService.get_variable(db_session, sample_variable.id)
        
        assert result is not None
        assert result.id == sample_variable.id
    
    def test_get_variable_by_name(self, db_session, sample_variable):
        """Test getting variable by name"""
        result = VariableService.get_variable_by_name(
            db_session,
            sample_variable.name
        )
        
        assert result is not None
        assert result.name == sample_variable.name
    
    def test_list_variables(self, db_session, sample_variable):
        """Test listing all variables"""
        result = VariableService.list_variables(db_session)
        
        assert len(result) >= 1
        assert any(v.id == sample_variable.id for v in result)
    
    def test_update_variable(self, db_session, sample_variable):
        """Test updating a variable"""
        update_data = schemas.GlobalVariableUpdate(
            description="Updated Description",
            config={"value": "updated_value"}
        )
        
        result = VariableService.update_variable(
            db_session,
            sample_variable.id,
            update_data
        )
        
        assert result.description == "Updated Description"
        assert result.config["value"] == "updated_value"
    
    def test_delete_variable(self, db_session, sample_variable):
        """Test deleting a variable"""
        var_id = sample_variable.id
        
        result = VariableService.delete_variable(db_session, var_id)
        
        assert result is True
        deleted = VariableService.get_variable(db_session, var_id)
        assert deleted is None


@pytest.mark.unit
class TestServiceIntegration:
    """Test integration between services"""
    
    def test_task_with_variables(
        self,
        db_session,
        sample_task,
        sample_variable
    ):
        """Test task using global variables"""
        # Update task config to use variable
        task_config = sample_task.config.copy()
        task_config["query"] = "SELECT * FROM table WHERE id = {{test_variable}}"
        sample_task.config = task_config
        db_session.commit()
        
        # Verify task config contains variable placeholder
        assert "{{test_variable}}" in sample_task.config["query"]
        
        # Verify variable exists
        var = VariableService.get_variable_by_name(
            db_session,
            "test_variable"
        )
        assert var is not None
    
    def test_connector_referenced_by_multiple_tasks(
        self,
        db_session,
        sample_source_connector,
        sample_destination_connector
    ):
        """Test connector used by multiple tasks"""
        # Create multiple tasks using same connector
        for i in range(3):
            task = models.Task(
                name=f"Task {i}",
                source_connector_id=sample_source_connector.id,
                destination_connector_id=sample_destination_connector.id,
                mode=models.TaskMode.FULL_LOAD,
                schedule_type=models.TaskScheduleType.ON_DEMAND,
                config={},
                status=models.TaskStatus.CREATED
            )
            db_session.add(task)
        db_session.commit()
        
        # Verify connector has multiple tasks
        assert len(sample_source_connector.source_tasks) == 3


@pytest.mark.unit
class TestServiceErrorHandling:
    """Test error handling in services"""
    
    def test_create_duplicate_connector(self, db_session, sample_connector):
        """Test creating connector with duplicate name"""
        duplicate_data = schemas.ConnectorCreate(
            name=sample_connector.name,
            connector_type=schemas.ConnectorTypeEnum.SOURCE,
            source_type=schemas.SourceTypeEnum.SQL_SERVER,
            connection_config={}
        )
        
        with pytest.raises(Exception):
            ConnectorService.create_connector(db_session, duplicate_data)
    
    def test_update_nonexistent_task(self, db_session):
        """Test updating non-existent task"""
        update_data = schemas.TaskUpdate(name="New Name")
        
        with pytest.raises((ValueError, AttributeError)):
            TaskService.update_task(db_session, 99999, update_data)
    
    def test_delete_connector_with_tasks(
        self,
        db_session,
        sample_source_connector,
        sample_task
    ):
        """Test deleting connector that has associated tasks"""
        # This should either fail or cascade delete depending on DB constraints
        with pytest.raises(Exception):
            ConnectorService.delete_connector(
                db_session,
                sample_source_connector.id
            )

