"""
Pytest Configuration and Fixtures
Shared fixtures for all tests
"""
import pytest
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Generator, Dict, Any

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database import Base
from main import app
import models

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_dtaas.db"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Clean up test database
    if os.path.exists("./test_dtaas.db"):
        os.remove("./test_dtaas.db")


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> TestClient:
    """Create FastAPI test client"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    from database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_sql_server_connector_config() -> Dict[str, Any]:
    """Sample SQL Server connector configuration"""
    return {
        "host": "localhost",
        "port": 1433,
        "database": "TestDB",
        "username": "sa",
        "password": "TestPassword123!",
        "driver": "ODBC Driver 17 for SQL Server"
    }


@pytest.fixture
def sample_postgresql_connector_config() -> Dict[str, Any]:
    """Sample PostgreSQL connector configuration"""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "postgres",
        "password": "postgres"
    }


@pytest.fixture
def sample_mysql_connector_config() -> Dict[str, Any]:
    """Sample MySQL connector configuration"""
    return {
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "root",
        "password": "password"
    }


@pytest.fixture
def sample_snowflake_connector_config() -> Dict[str, Any]:
    """Sample Snowflake connector configuration"""
    return {
        "account": "test_account",
        "user": "test_user",
        "password": "test_password",
        "warehouse": "TEST_WH",
        "database": "TEST_DB",
        "schema": "PUBLIC"
    }


@pytest.fixture
def sample_s3_connector_config() -> Dict[str, Any]:
    """Sample S3 connector configuration"""
    return {
        "bucket_name": "test-bucket",
        "aws_access_key_id": "test_access_key",
        "aws_secret_access_key": "test_secret_key",
        "region": "us-west-2",
        "prefix": "test/"
    }


@pytest.fixture
def sample_connector(db_session) -> models.Connector:
    """Create a sample connector in database"""
    connector = models.Connector(
        name="Test SQL Server",
        description="Test connector",
        connector_type=models.ConnectorType.SOURCE,
        source_type=models.SourceType.SQL_SERVER,
        connection_config={
            "host": "localhost",
            "port": 1433,
            "database": "TestDB",
            "username": "sa",
            "password": "TestPassword123!"
        }
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    return connector


@pytest.fixture
def sample_source_connector(db_session) -> models.Connector:
    """Create a sample source connector"""
    connector = models.Connector(
        name="Test Source",
        description="Test source connector",
        connector_type=models.ConnectorType.SOURCE,
        source_type=models.SourceType.SQL_SERVER,
        connection_config={"host": "localhost"}
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    return connector


@pytest.fixture
def sample_destination_connector(db_session) -> models.Connector:
    """Create a sample destination connector"""
    connector = models.Connector(
        name="Test Destination",
        description="Test destination connector",
        connector_type=models.ConnectorType.DESTINATION,
        destination_type=models.DestinationType.SNOWFLAKE,
        connection_config={"account": "test_account"}
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    return connector


@pytest.fixture
def sample_task(db_session, sample_source_connector, sample_destination_connector) -> models.Task:
    """Create a sample task"""
    task = models.Task(
        name="Test Task",
        description="Test data transfer task",
        source_connector_id=sample_source_connector.id,
        destination_connector_id=sample_destination_connector.id,
        mode=models.TaskMode.FULL_LOAD,
        schedule_type=models.TaskScheduleType.ON_DEMAND,
        config={
            "tables": ["table1", "table2"],
            "batch_size": 10000
        },
        status=models.TaskStatus.CREATED
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def sample_variable(db_session) -> models.GlobalVariable:
    """Create a sample global variable"""
    variable = models.GlobalVariable(
        name="test_variable",
        description="Test variable",
        variable_type=models.VariableType.STATIC,
        config={"value": "test_value"}
    )
    db_session.add(variable)
    db_session.commit()
    db_session.refresh(variable)
    return variable


@pytest.fixture
def mock_dataframe():
    """Create a mock pandas DataFrame for testing"""
    import pandas as pd
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'created_at': [datetime.now()] * 3
    })


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)

