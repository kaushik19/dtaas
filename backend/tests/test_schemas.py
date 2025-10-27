"""
Unit Tests for Pydantic Schemas
Tests all request/response schemas
"""
import pytest
from pydantic import ValidationError
import schemas


@pytest.mark.unit
class TestConnectorSchemas:
    """Test Connector schemas"""
    
    def test_connector_create_valid(self):
        """Test valid connector creation schema"""
        data = {
            "name": "Test Connector",
            "description": "Test Description",
            "connector_type": "source",
            "source_type": "sql_server",
            "connection_config": {"host": "localhost"}
        }
        schema = schemas.ConnectorCreate(**data)
        assert schema.name == "Test Connector"
        assert schema.connector_type == schemas.ConnectorTypeEnum.SOURCE
        assert schema.source_type == schemas.SourceTypeEnum.SQL_SERVER
    
    def test_connector_create_invalid_type(self):
        """Test invalid connector type"""
        with pytest.raises(ValidationError):
            schemas.ConnectorCreate(
                name="Test",
                connector_type="invalid_type",
                connection_config={}
            )
    
    def test_connector_response(self):
        """Test connector response schema"""
        data = {
            "id": 1,
            "name": "Test Connector",
            "description": "Test",
            "connector_type": "source",
            "source_type": "sql_server",
            "connection_config": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        schema = schemas.ConnectorResponse(**data)
        assert schema.id == 1
        assert schema.name == "Test Connector"
    
    def test_connector_test_request(self):
        """Test connector test request schema"""
        data = {
            "connector_type": "source",
            "source_type": "sql_server",
            "connection_config": {
                "host": "localhost",
                "port": 1433
            }
        }
        schema = schemas.ConnectorTestRequest(**data)
        assert schema.connector_type == schemas.ConnectorTypeEnum.SOURCE
        assert schema.connection_config["host"] == "localhost"


@pytest.mark.unit
class TestTaskSchemas:
    """Test Task schemas"""
    
    def test_task_create_valid(self):
        """Test valid task creation"""
        data = {
            "name": "Test Task",
            "description": "Test",
            "source_connector_id": 1,
            "destination_connector_id": 2,
            "mode": "full_load",
            "schedule_type": "on_demand",
            "config": {"batch_size": 10000}
        }
        schema = schemas.TaskCreate(**data)
        assert schema.name == "Test Task"
        assert schema.mode == schemas.TaskModeEnum.FULL_LOAD
        assert schema.config["batch_size"] == 10000
    
    def test_task_create_missing_required_fields(self):
        """Test task creation with missing required fields"""
        with pytest.raises(ValidationError):
            schemas.TaskCreate(
                name="Test Task",
                mode="full_load"
                # Missing source_connector_id, destination_connector_id
            )
    
    def test_task_update(self):
        """Test task update schema"""
        data = {
            "name": "Updated Task",
            "description": "Updated Description",
            "config": {"batch_size": 20000}
        }
        schema = schemas.TaskUpdate(**data)
        assert schema.name == "Updated Task"
        assert schema.config["batch_size"] == 20000
    
    def test_task_response(self):
        """Test task response schema"""
        data = {
            "id": 1,
            "name": "Test Task",
            "description": "Test",
            "source_connector_id": 1,
            "destination_connector_id": 2,
            "mode": "full_load",
            "schedule_type": "on_demand",
            "status": "created",
            "config": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        schema = schemas.TaskResponse(**data)
        assert schema.id == 1
        assert schema.status == schemas.TaskStatusEnum.CREATED
    
    def test_bulk_transformation_request(self):
        """Test bulk transformation request schema"""
        data = {
            "tables": ["table1", "table2"],
            "transformations": [
                {
                    "type": "rename_column",
                    "config": {"old_name": "col1", "new_name": "col2"}
                }
            ]
        }
        schema = schemas.BulkTransformationRequest(**data)
        assert len(schema.tables) == 2
        assert len(schema.transformations) == 1


@pytest.mark.unit
class TestVariableSchemas:
    """Test Variable schemas"""
    
    def test_variable_create_static(self):
        """Test static variable creation"""
        data = {
            "name": "test_var",
            "description": "Test Variable",
            "variable_type": "static",
            "config": {"value": "test_value"}
        }
        schema = schemas.GlobalVariableCreate(**data)
        assert schema.name == "test_var"
        assert schema.variable_type == schemas.VariableTypeEnum.STATIC
        assert schema.config["value"] == "test_value"
    
    def test_variable_create_db_query(self):
        """Test database query variable creation"""
        data = {
            "name": "db_var",
            "description": "DB Variable",
            "variable_type": "db_query",
            "config": {
                "server": "localhost",
                "database": "testdb",
                "table": "config",
                "column": "value"
            }
        }
        schema = schemas.GlobalVariableCreate(**data)
        assert schema.variable_type == schemas.VariableTypeEnum.DB_QUERY
        assert schema.config["server"] == "localhost"
    
    def test_variable_create_context(self):
        """Test context variable creation"""
        data = {
            "name": "context_var",
            "description": "Context Variable",
            "variable_type": "context",
            "config": {"path": "source.database"}
        }
        schema = schemas.GlobalVariableCreate(**data)
        assert schema.variable_type == schemas.VariableTypeEnum.CONTEXT
    
    def test_variable_response(self):
        """Test variable response schema"""
        data = {
            "id": 1,
            "name": "test_var",
            "description": "Test",
            "variable_type": "static",
            "config": {"value": "test"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        schema = schemas.GlobalVariableResponse(**data)
        assert schema.id == 1
        assert schema.name == "test_var"


@pytest.mark.unit
class TestTransformationSchemas:
    """Test Transformation schemas"""
    
    def test_transformation_config(self):
        """Test transformation config schema"""
        data = {
            "type": "rename_column",
            "config": {"old_name": "col1", "new_name": "col2"}
        }
        schema = schemas.TransformationConfig(**data)
        assert schema.type == "rename_column"
        assert schema.config["old_name"] == "col1"
    
    def test_column_transformation(self):
        """Test column transformation schema"""
        data = {
            "column_name": "test_column",
            "transformations": [
                {"type": "uppercase"},
                {"type": "trim"}
            ]
        }
        schema = schemas.ColumnTransformation(**data)
        assert schema.column_name == "test_column"
        assert len(schema.transformations) == 2


@pytest.mark.unit
class TestDatabaseBrowserSchemas:
    """Test Database Browser schemas"""
    
    def test_database_info(self):
        """Test database info schema"""
        data = {
            "name": "TestDB",
            "tables_count": 10
        }
        schema = schemas.DatabaseInfo(**data)
        assert schema.name == "TestDB"
        assert schema.tables_count == 10
    
    def test_table_info(self):
        """Test table info schema"""
        data = {
            "database_name": "TestDB",
            "schema": "dbo",
            "table_name": "customers",
            "row_count": 1000,
            "columns": []
        }
        schema = schemas.TableInfo(**data)
        assert schema.database_name == "TestDB"
        assert schema.table_name == "customers"
        assert schema.row_count == 1000
    
    def test_column_info(self):
        """Test column info schema"""
        data = {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": False,
            "is_primary_key": True
        }
        schema = schemas.ColumnInfo(**data)
        assert schema.column_name == "id"
        assert schema.data_type == "int"
        assert not schema.is_nullable
        assert schema.is_primary_key
    
    def test_query_request(self):
        """Test custom query request schema"""
        data = {
            "query": "SELECT * FROM customers WHERE id = @id",
            "parameters": {"id": 1},
            "limit": 100
        }
        schema = schemas.CustomerQueryRequest(**data)
        assert schema.query.startswith("SELECT")
        assert schema.parameters["id"] == 1
        assert schema.limit == 100


@pytest.mark.unit
class TestEnumSchemas:
    """Test all enum schemas"""
    
    def test_connector_type_enum(self):
        """Test ConnectorTypeEnum"""
        assert schemas.ConnectorTypeEnum.SOURCE.value == "source"
        assert schemas.ConnectorTypeEnum.DESTINATION.value == "destination"
    
    def test_source_type_enum(self):
        """Test SourceTypeEnum"""
        assert schemas.SourceTypeEnum.SQL_SERVER.value == "sql_server"
        assert schemas.SourceTypeEnum.POSTGRESQL.value == "postgresql"
        assert schemas.SourceTypeEnum.MYSQL.value == "mysql"
        assert schemas.SourceTypeEnum.ORACLE.value == "oracle"
    
    def test_destination_type_enum(self):
        """Test DestinationTypeEnum"""
        assert schemas.DestinationTypeEnum.SNOWFLAKE.value == "snowflake"
        assert schemas.DestinationTypeEnum.S3.value == "s3"
    
    def test_task_mode_enum(self):
        """Test TaskModeEnum"""
        assert schemas.TaskModeEnum.FULL_LOAD.value == "full_load"
        assert schemas.TaskModeEnum.CDC.value == "cdc"
        assert schemas.TaskModeEnum.FULL_LOAD_THEN_CDC.value == "full_load_then_cdc"
    
    def test_variable_type_enum(self):
        """Test VariableTypeEnum"""
        values = [e.value for e in schemas.VariableTypeEnum]
        assert "static" in values
        assert "db_query" in values
        assert "context" in values


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation in schemas"""
    
    def test_sql_server_config_validation(self):
        """Test SQL Server connection config validation"""
        config = {
            "host": "localhost",
            "port": 1433,
            "database": "TestDB",
            "username": "sa",
            "password": "password"
        }
        # Should not raise validation error
        connector = schemas.ConnectorCreate(
            name="Test",
            connector_type="source",
            source_type="sql_server",
            connection_config=config
        )
        assert connector.connection_config["host"] == "localhost"
    
    def test_snowflake_config_validation(self):
        """Test Snowflake connection config validation"""
        config = {
            "account": "test_account",
            "user": "test_user",
            "password": "password",
            "warehouse": "TEST_WH",
            "database": "TEST_DB"
        }
        connector = schemas.ConnectorCreate(
            name="Test",
            connector_type="destination",
            destination_type="snowflake",
            connection_config=config
        )
        assert connector.connection_config["account"] == "test_account"
    
    def test_s3_config_validation(self):
        """Test S3 connection config validation"""
        config = {
            "bucket_name": "test-bucket",
            "aws_access_key_id": "test_key",
            "aws_secret_access_key": "test_secret",
            "region": "us-west-2"
        }
        connector = schemas.ConnectorCreate(
            name="Test",
            connector_type="destination",
            destination_type="s3",
            connection_config=config
        )
        assert connector.connection_config["bucket_name"] == "test-bucket"

