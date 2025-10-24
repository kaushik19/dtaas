import boto3
import pandas as pd
from typing import List, Dict, Any, Optional
from .base import DestinationConnector
import logging
import io
from datetime import datetime
import json
import uuid
import re

logger = logging.getLogger(__name__)


class S3Connector(DestinationConnector):
    """S3 destination connector with support for multiple file formats"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bucket = config.get("bucket")
        self.prefix = config.get("prefix", "")
        self.region = config.get("region", "us-east-1")
        self.access_key_id = config.get("access_key_id")
        self.secret_access_key = config.get("secret_access_key")
        self.file_format = config.get("file_format", "parquet")  # parquet, csv, json
        
        # Dynamic path template support
        # If path_template not set, use prefix as template (for backward compatibility)
        self.path_template = config.get("path_template", "") or self.prefix
        
        # Structured customer query configuration (secure, no SQL injection)
        self.customer_query_config = config.get("customer_query_config", {})
        
        # Legacy support: raw SQL query (deprecated, use customer_query_config instead)
        self.customer_query = config.get("customer_query", "")
        
        # LocalStack support - use Docker service name when in container
        self.use_localstack = config.get("use_localstack", False)
        endpoint_from_config = config.get("endpoint_url", "http://localhost:4566")
        
        # Replace localhost with localstack service name for Docker network
        if self.use_localstack and "localhost" in endpoint_from_config:
            self.endpoint_url = endpoint_from_config.replace("localhost", "localstack")
        else:
            self.endpoint_url = endpoint_from_config if self.use_localstack else None
    
    def connect(self):
        """Establish connection to S3 or LocalStack"""
        try:
            session_params = {"region_name": self.region}
            
            # For LocalStack, use default credentials if not provided
            if self.use_localstack or self.endpoint_url:
                if not self.access_key_id:
                    self.access_key_id = "test"
                if not self.secret_access_key:
                    self.secret_access_key = "test"
            
            if self.access_key_id and self.secret_access_key:
                session_params["aws_access_key_id"] = self.access_key_id
                session_params["aws_secret_access_key"] = self.secret_access_key
            
            session = boto3.Session(**session_params)
            
            # Create S3 client with custom endpoint for LocalStack
            client_params = {}
            if self.endpoint_url or self.use_localstack:
                endpoint = self.endpoint_url or "http://localhost:4566"
                client_params["endpoint_url"] = endpoint
                logger.info(f"Using LocalStack endpoint: {endpoint}")
            
            self.connection = session.client('s3', **client_params)
            
            # Create bucket if it doesn't exist (useful for LocalStack)
            if self.use_localstack or self.endpoint_url:
                try:
                    self.connection.head_bucket(Bucket=self.bucket)
                except:
                    logger.info(f"Creating bucket: {self.bucket}")
                    self.connection.create_bucket(Bucket=self.bucket)
            
            logger.info(f"Connected to S3: {self.bucket}")
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to S3: {str(e)}")
            raise
    
    def disconnect(self):
        """S3 client doesn't need explicit disconnect"""
        logger.info("S3 connector closed")
    
    def resolve_path_template(
        self, 
        table_name: str, 
        source_connector=None,
        database_name: str = "",
        db_session=None
    ) -> str:
        """
        Resolve path template with dynamic variables using VariableResolver
        
        Supported variables:
        - Built-in: $tableName, $timestamp, $date, $uuid, $databaseName
        - Custom: Any user-defined global variable (e.g., $customerId)
        - Legacy: $customerId via customer_query_config (for backward compatibility)
        """
        if not self.path_template:
            # Use default prefix if no template
            return self.prefix
        
        path = self.path_template
        
        # Use VariableResolver if db_session is available
        if db_session:
            from services.variable_resolver import VariableResolver
            
            logger.info(f"=== S3 Connector: Resolving path template ===")
            logger.info(f"Path template: {path}")
            logger.info(f"Table: {table_name}")
            logger.info(f"Database: '{database_name}' (type: {type(database_name)})")
            logger.info(f"Source connector: {source_connector is not None}")
            if source_connector:
                logger.info(f"Source connector type: {type(source_connector).__name__}")
                if hasattr(source_connector, 'database'):
                    logger.info(f"Source connector.database: '{source_connector.database}'")
            
            resolver = VariableResolver(
                db=db_session,
                source_connector=source_connector,
                database_name=database_name,
                table_name=table_name
            )
            
            # First, handle legacy customerId if configured
            if "$customerId" in path and (self.customer_query_config or self.customer_query):
                try:
                    customer_id = self._get_customer_id(source_connector, database_name)
                    path = path.replace("$customerId", str(customer_id))
                except Exception as e:
                    logger.warning(f"Failed to get customerId via legacy config: {str(e)}")
            
            # Then resolve all variables (including custom global variables)
            path = resolver.resolve(path)
            logger.info(f"Resolved path: {path}")
        
        else:
            # Fallback: manual replacement (no custom variables support)
            logger.warning("No db_session provided, custom global variables will not be resolved")
            
            path = path.replace("$tableName", table_name)
            path = path.replace("$timestamp", datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            path = path.replace("$date", datetime.utcnow().strftime("%Y%m%d"))
            path = path.replace("$uuid", str(uuid.uuid4()))
            path = path.replace("$databaseName", database_name)
            
            # Legacy customerId handling
            if "$customerId" in path and source_connector:
                try:
                    customer_id = self._get_customer_id(source_connector, database_name)
                    path = path.replace("$customerId", str(customer_id))
                except Exception as e:
                    logger.warning(f"Failed to get customerId: {str(e)}. Using 'unknown'")
                    path = path.replace("$customerId", "unknown")
        
        return path
    
    def _get_customer_id(self, source_connector, database_name: str):
        """
        Get customer ID by executing a safe parameterized query on the source connector
        
        Uses structured customer_query_config to build secure query
        """
        try:
            # Check if structured config is available
            if self.customer_query_config and self.customer_query_config.get("enabled"):
                query, params = self._build_customer_query(database_name)
            elif self.customer_query:
                # Legacy support: Use raw SQL query (less secure)
                logger.warning("Using deprecated raw SQL query. Consider using customer_query_config instead.")
                query = self.customer_query.replace("$databaseName", database_name)
                params = []
            else:
                # Default query with parameterization
                query = "SELECT Id FROM dbo.Customers WHERE DatabaseName = ? OR CustomerName = ?"
                params = [database_name, database_name]
            
            # Execute query on source connector
            if hasattr(source_connector, 'connection') and source_connector.connection:
                cursor = source_connector.connection.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                result = cursor.fetchone()
                if result:
                    return result[0]
            
            return "unknown"
        except Exception as e:
            logger.error(f"Error executing customer query: {str(e)}")
            return "unknown"
    
    def _build_customer_query(self, database_name: str):
        """
        Build a safe parameterized SQL query from structured config
        
        Returns: (query_string, parameters_list)
        """
        config = self.customer_query_config
        
        # Validate required fields
        if not config.get("table") or not config.get("column"):
            raise ValueError("Customer query config must specify table and column")
        
        # Build SELECT clause with proper escaping
        schema = config.get("schema", "dbo")
        table = config.get("table")
        column = config.get("column")
        
        # Escape identifiers to prevent SQL injection
        schema_escaped = self._escape_identifier(schema)
        table_escaped = self._escape_identifier(table)
        column_escaped = self._escape_identifier(column)
        
        query = f"SELECT {column_escaped} FROM {schema_escaped}.{table_escaped}"
        params = []
        
        # Build WHERE clause
        where_conditions = config.get("where_conditions", [])
        if where_conditions:
            where_clauses = []
            for condition in where_conditions:
                field = condition.get("field")
                operator = condition.get("operator", "=")
                value = condition.get("value", "")
                
                # Validate operator
                allowed_operators = ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"]
                if operator not in allowed_operators:
                    operator = "="
                
                # Replace $databaseName placeholder with actual value
                if value == "$databaseName":
                    value = database_name
                
                field_escaped = self._escape_identifier(field)
                
                if operator == "IN":
                    # Handle IN operator
                    # Split comma-separated values
                    values = [v.strip() for v in value.split(",")]
                    placeholders = ",".join(["?" for _ in values])
                    where_clauses.append(f"{field_escaped} IN ({placeholders})")
                    params.extend(values)
                else:
                    # Use parameterized query
                    where_clauses.append(f"{field_escaped} {operator} ?")
                    params.append(value)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        logger.info(f"Built customer query: {query} with {len(params)} parameters")
        return query, params
    
    def _escape_identifier(self, identifier: str) -> str:
        """
        Escape SQL identifier to prevent SQL injection
        
        Removes dangerous characters and wraps in square brackets
        """
        # Remove dangerous characters
        safe_identifier = re.sub(r'[^\w]', '', identifier)
        
        # Wrap in square brackets for SQL Server
        return f"[{safe_identifier}]"
    
    def test_connection(self) -> Dict[str, Any]:
        """Test S3 connection"""
        try:
            self.connect()
            # Try to list objects (with limit) to verify access
            self.connection.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
            
            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "bucket": self.bucket,
                    "region": self.region
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__,
                    "bucket": self.bucket,
                    "region": self.region,
                    "endpoint": self.endpoint_url or "AWS S3"
                }
            }
    
    def write_data(
        self,
        data: pd.DataFrame,
        table_name: str,
        mode: str = "append",
        schema: Optional[str] = None,
        file_format: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Write data to S3 in specified format"""
        if not self.connection:
            self.connect()
        
        format_to_use = file_format or self.file_format
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Get optional parameters for dynamic path
        source_connector = kwargs.get('source_connector')
        database_name = kwargs.get('database_name', '')
        db_session = kwargs.get('db_session')  # For global variable resolution
        
        # Resolve path template or use default prefix
        if self.path_template:
            # Use dynamic path template
            resolved_path = self.resolve_path_template(
                table_name=table_name,
                source_connector=source_connector,
                database_name=database_name,
                db_session=db_session
            )
            # Extract directory and filename from resolved path
            if '/' in resolved_path:
                parts = resolved_path.rsplit('/', 1)
                if len(parts) == 2 and ('.' in parts[1] or '$' in parts[1]):
                    # Path includes filename pattern
                    base_path = parts[0]
                    filename_pattern = parts[1]
                    # Replace remaining variables in filename
                    filename_pattern = filename_pattern.replace("$timestamp", timestamp)
                    filename_pattern = filename_pattern.replace("$uuid", str(uuid.uuid4()))
                    
                    # Check if filename already has a valid file extension
                    valid_extensions = ['.parquet', '.csv', '.json', '.txt', '.avro', '.orc']
                    has_extension = any(filename_pattern.lower().endswith(ext) for ext in valid_extensions)
                    
                    if has_extension:
                        file_key = f"{base_path}/{filename_pattern}"
                    else:
                        # Add the file format extension
                        file_key = f"{base_path}/{filename_pattern}.{format_to_use}"
                else:
                    # Path is directory only
                    base_path = resolved_path
                    file_key = f"{base_path}/data_{timestamp}.{format_to_use}"
            else:
                base_path = resolved_path
                file_key = f"{base_path}/data_{timestamp}.{format_to_use}"
        else:
            # Use default prefix-based path
            if schema:
                base_path = f"{self.prefix}/{schema}/{table_name}"
            else:
                base_path = f"{self.prefix}/{table_name}"
            
            if mode == "overwrite":
                # Delete existing files for this table
                self._delete_table_files(base_path)
                file_key = f"{base_path}/data.{format_to_use}"
            else:
                # Append mode - create new file with timestamp
                file_key = f"{base_path}/data_{timestamp}.{format_to_use}"
        
        try:
            # Write data based on format
            if format_to_use == "parquet":
                buffer = io.BytesIO()
                data.to_parquet(buffer, index=False, engine='pyarrow')
                buffer.seek(0)
                content_type = "application/octet-stream"
            
            elif format_to_use == "csv":
                buffer = io.StringIO()
                data.to_csv(buffer, index=False)
                buffer.seek(0)
                content_type = "text/csv"
            
            elif format_to_use == "json":
                buffer = io.StringIO()
                data.to_json(buffer, orient='records', lines=True)
                buffer.seek(0)
                content_type = "application/json"
            
            else:
                raise ValueError(f"Unsupported file format: {format_to_use}")
            
            # Upload to S3
            self.connection.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=buffer.getvalue() if isinstance(buffer, io.BytesIO) else buffer.getvalue().encode(),
                ContentType=content_type
            )
            
            logger.info(f"Uploaded {len(data)} rows to s3://{self.bucket}/{file_key}")
            
            return {
                "success": True,
                "rows_written": len(data),
                "s3_key": file_key,
                "format": format_to_use
            }
        except Exception as e:
            logger.error(f"Failed to write data to S3: {str(e)}")
            raise
    
    def _delete_table_files(self, prefix: str):
        """Delete all files under a prefix"""
        try:
            # List all objects with the prefix
            response = self.connection.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                if objects_to_delete:
                    self.connection.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': objects_to_delete}
                    )
                    logger.info(f"Deleted {len(objects_to_delete)} files from {prefix}")
        except Exception as e:
            logger.error(f"Failed to delete files: {str(e)}")
    
    def cleanup_partial_files(self, table_name: str, schema: Optional[str] = None):
        """
        Clean up partial/incomplete files for a table before retry
        
        This is called when a table transfer fails and needs to be retried.
        It ensures we start fresh without partial data.
        """
        try:
            # Determine the prefix for this table's data
            if self.path_template:
                # For dynamic paths, we need to clean up potential variations
                # For simplicity, clean up based on table name in the bucket
                logger.warning(f"Partial cleanup for dynamic paths - searching for {table_name} files")
                
                # List all objects in bucket (this could be optimized with better tracking)
                paginator = self.connection.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.bucket)
                
                objects_to_delete = []
                for page in pages:
                    if 'Contents' in page:
                        # Filter objects that contain the table name
                        for obj in page['Contents']:
                            # Simple heuristic: if file contains table name, it might be partial
                            # In production, better to track files during write
                            if table_name in obj['Key']:
                                objects_to_delete.append({'Key': obj['Key']})
                
                if objects_to_delete:
                    # Delete in batches of 1000 (S3 limit)
                    for i in range(0, len(objects_to_delete), 1000):
                        batch = objects_to_delete[i:i+1000]
                        self.connection.delete_objects(
                            Bucket=self.bucket,
                            Delete={'Objects': batch}
                        )
                    logger.info(f"Cleaned up {len(objects_to_delete)} partial files for table {table_name}")
            else:
                # For standard prefix-based paths
                if schema:
                    prefix = f"{self.prefix}/{schema}/{table_name}/"
                else:
                    prefix = f"{self.prefix}/{table_name}/"
                
                self._delete_table_files(prefix)
                logger.info(f"Cleaned up partial files at {prefix}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup partial files for {table_name}: {str(e)}")
            # Don't raise - cleanup failure shouldn't prevent retry
    
    def create_table_if_not_exists(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        schema: Optional[str] = None,
        source_connector=None,
        database_name: str = "",
        db_session=None
    ) -> bool:
        """
        For S3, we don't create tables, but we can write metadata
        """
        # Resolve the path template (to handle variables like $ETLCustomerId)
        resolved_prefix = self.resolve_path_template(
            table_name=table_name,
            source_connector=source_connector,
            database_name=database_name,
            db_session=db_session
        )
        
        if schema:
            base_path = f"{resolved_prefix}/{schema}/{table_name}"
        else:
            base_path = f"{resolved_prefix}/{table_name}"
        
        metadata_key = f"{base_path}/_metadata.json"
        
        metadata = {
            "table_name": table_name,
            "schema": schema,
            "columns": columns,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            self.connection.put_object(
                Bucket=self.bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2).encode(),
                ContentType="application/json"
            )
            logger.info(f"Created metadata for {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create metadata: {str(e)}")
            return False
    
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if table (directory) exists in S3"""
        if schema:
            prefix = f"{self.prefix}/{schema}/{table_name}/"
        else:
            prefix = f"{self.prefix}/{table_name}/"
        
        try:
            response = self.connection.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=1
            )
            return 'Contents' in response and len(response['Contents']) > 0
        except Exception as e:
            logger.error(f"Error checking table existence: {str(e)}")
            return False
    
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get table schema from metadata file"""
        if schema:
            base_path = f"{self.prefix}/{schema}/{table_name}"
        else:
            base_path = f"{self.prefix}/{table_name}"
        
        metadata_key = f"{base_path}/_metadata.json"
        
        try:
            response = self.connection.get_object(
                Bucket=self.bucket,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read().decode())
            return metadata.get('columns', [])
        except Exception as e:
            logger.warning(f"Failed to read metadata: {str(e)}")
            return []
    
    def handle_schema_drift(
        self,
        table_name: str,
        new_columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """
        For S3, schema drift is handled automatically as we're writing files
        We'll just update the metadata
        """
        current_schema = self.get_table_schema(table_name, schema)
        
        # Merge schemas
        column_names = {col['column_name'] for col in current_schema}
        for new_col in new_columns:
            if new_col['column_name'] not in column_names:
                current_schema.append(new_col)
        
        # Update metadata
        return self.create_table_if_not_exists(table_name, current_schema, schema)

