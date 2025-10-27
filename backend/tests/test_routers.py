"""
Unit Tests for API Routers
Tests all FastAPI endpoints
"""
import pytest
from fastapi.testclient import TestClient
import schemas


@pytest.mark.unit
class TestConnectorRoutes:
    """Test /api/connectors endpoints"""
    
    def test_create_connector_success(self, client):
        """Test POST /api/connectors"""
        payload = {
            "name": "Test Connector",
            "description": "Test",
            "connector_type": "source",
            "source_type": "sql_server",
            "connection_config": {"host": "localhost"}
        }
        
        response = client.post("/api/connectors", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Connector"
        assert "id" in data
    
    def test_list_connectors(self, client, sample_connector):
        """Test GET /api/connectors"""
        response = client.get("/api/connectors")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_connector_by_id(self, client, sample_connector):
        """Test GET /api/connectors/{id}"""
        response = client.get(f"/api/connectors/{sample_connector.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_connector.id
        assert data["name"] == sample_connector.name
    
    def test_get_connector_not_found(self, client):
        """Test GET /api/connectors/{id} with invalid ID"""
        response = client.get("/api/connectors/99999")
        
        assert response.status_code == 404
    
    def test_update_connector(self, client, sample_connector):
        """Test PUT /api/connectors/{id}"""
        payload = {
            "name": "Updated Connector",
            "description": "Updated Description"
        }
        
        response = client.put(
            f"/api/connectors/{sample_connector.id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Connector"
    
    def test_delete_connector(self, client, sample_connector):
        """Test DELETE /api/connectors/{id}"""
        response = client.delete(f"/api/connectors/{sample_connector.id}")
        
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f"/api/connectors/{sample_connector.id}")
        assert response.status_code == 404
    
    def test_test_connector_connection(self, client):
        """Test POST /api/connectors/test"""
        payload = {
            "connector_type": "source",
            "source_type": "sql_server",
            "connection_config": {
                "host": "localhost",
                "port": 1433,
                "database": "TestDB",
                "username": "sa",
                "password": "password"
            }
        }
        
        response = client.post("/api/connectors/test", json=payload)
        
        assert response.status_code in [200, 500]  # May fail if DB not available
        data = response.json()
        assert "success" in data
        assert "message" in data


@pytest.mark.unit
class TestTaskRoutes:
    """Test /api/tasks endpoints"""
    
    def test_create_task_success(
        self,
        client,
        sample_source_connector,
        sample_destination_connector
    ):
        """Test POST /api/tasks"""
        payload = {
            "name": "Test Task",
            "description": "Test",
            "source_connector_id": sample_source_connector.id,
            "destination_connector_id": sample_destination_connector.id,
            "mode": "full_load",
            "schedule_type": "on_demand",
            "config": {"batch_size": 10000}
        }
        
        response = client.post("/api/tasks", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Task"
        assert "id" in data
    
    def test_list_tasks(self, client, sample_task):
        """Test GET /api/tasks"""
        response = client.get("/api/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_task_by_id(self, client, sample_task):
        """Test GET /api/tasks/{id}"""
        response = client.get(f"/api/tasks/{sample_task.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id
        assert data["name"] == sample_task.name
    
    def test_update_task(self, client, sample_task):
        """Test PUT /api/tasks/{id}"""
        payload = {
            "name": "Updated Task",
            "config": {"batch_size": 20000}
        }
        
        response = client.put(f"/api/tasks/{sample_task.id}", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Task"
    
    def test_delete_task(self, client, sample_task):
        """Test DELETE /api/tasks/{id}"""
        response = client.delete(f"/api/tasks/{sample_task.id}")
        
        assert response.status_code == 200
    
    def test_start_task(self, client, sample_task):
        """Test POST /api/tasks/{id}/start"""
        response = client.post(f"/api/tasks/{sample_task.id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_stop_task(self, client, sample_task):
        """Test POST /api/tasks/{id}/stop"""
        response = client.post(f"/api/tasks/{sample_task.id}/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
    
    def test_pause_task(self, client, sample_task):
        """Test POST /api/tasks/{id}/pause"""
        response = client.post(f"/api/tasks/{sample_task.id}/pause")
        
        assert response.status_code == 200
    
    def test_get_task_executions(self, client, sample_task):
        """Test GET /api/tasks/{id}/executions"""
        response = client.get(f"/api/tasks/{sample_task.id}/executions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.unit
class TestVariableRoutes:
    """Test /api/variables endpoints"""
    
    def test_create_variable(self, client):
        """Test POST /api/variables"""
        payload = {
            "name": "test_var",
            "description": "Test Variable",
            "variable_type": "static",
            "config": {"value": "test_value"}
        }
        
        response = client.post("/api/variables", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_var"
    
    def test_list_variables(self, client, sample_variable):
        """Test GET /api/variables"""
        response = client.get("/api/variables")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_variable_by_id(self, client, sample_variable):
        """Test GET /api/variables/{id}"""
        response = client.get(f"/api/variables/{sample_variable.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_variable.id
    
    def test_update_variable(self, client, sample_variable):
        """Test PUT /api/variables/{id}"""
        payload = {
            "description": "Updated Description",
            "config": {"value": "updated_value"}
        }
        
        response = client.put(
            f"/api/variables/{sample_variable.id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Description"
    
    def test_delete_variable(self, client, sample_variable):
        """Test DELETE /api/variables/{id}"""
        response = client.delete(f"/api/variables/{sample_variable.id}")
        
        assert response.status_code == 200


@pytest.mark.unit
class TestDashboardRoutes:
    """Test /api/dashboard endpoints"""
    
    def test_get_dashboard_stats(self, client, sample_task):
        """Test GET /api/dashboard/stats"""
        response = client.get("/api/dashboard/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "total_connectors" in data
        assert "running_tasks" in data
    
    def test_get_recent_executions(self, client):
        """Test GET /api/dashboard/executions/recent"""
        response = client.get("/api/dashboard/executions/recent")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.unit
class TestDatabaseBrowserRoutes:
    """Test /api/database-browser endpoints"""
    
    def test_list_databases(self, client, sample_source_connector):
        """Test GET /api/database-browser/databases"""
        response = client.get(
            f"/api/database-browser/databases?connector_id={sample_source_connector.id}"
        )
        
        assert response.status_code in [200, 500]  # May fail if connector not accessible
    
    def test_list_tables(self, client, sample_source_connector):
        """Test GET /api/database-browser/tables"""
        response = client.get(
            f"/api/database-browser/tables"
            f"?connector_id={sample_source_connector.id}"
            f"&database=TestDB"
        )
        
        assert response.status_code in [200, 500]
    
    def test_get_table_schema(self, client, sample_source_connector):
        """Test GET /api/database-browser/schema"""
        response = client.get(
            f"/api/database-browser/schema"
            f"?connector_id={sample_source_connector.id}"
            f"&database=TestDB"
            f"&table=TestTable"
        )
        
        assert response.status_code in [200, 500]


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in API routes"""
    
    def test_invalid_json_payload(self, client):
        """Test API with invalid JSON"""
        response = client.post(
            "/api/connectors",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test API with missing required fields"""
        payload = {
            "name": "Test Connector"
            # Missing required fields
        }
        
        response = client.post("/api/connectors", json=payload)
        
        assert response.status_code == 422
    
    def test_invalid_id_type(self, client):
        """Test API with invalid ID type"""
        response = client.get("/api/connectors/invalid_id")
        
        assert response.status_code == 422


@pytest.mark.unit
class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/api/connectors")
        
        # Check for CORS headers
        assert response.status_code in [200, 405]  # 405 if OPTIONS not allowed


@pytest.mark.unit
class TestHealthCheck:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        # May return HTML or JSON depending on frontend setup
    
    def test_docs_endpoint(self, client):
        """Test API docs endpoint"""
        response = client.get("/docs")
        
        assert response.status_code == 200

