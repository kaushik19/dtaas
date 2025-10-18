import boto3
import pandas as pd
from typing import List, Dict, Any, Optional
from .base import DestinationConnector
import logging
import io
from datetime import datetime
import json

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
    
    def connect(self):
        """Establish connection to S3"""
        try:
            session_params = {"region_name": self.region}
            
            if self.access_key_id and self.secret_access_key:
                session_params["aws_access_key_id"] = self.access_key_id
                session_params["aws_secret_access_key"] = self.secret_access_key
            
            session = boto3.Session(**session_params)
            self.connection = session.client('s3')
            
            logger.info(f"Connected to S3: {self.bucket}")
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to S3: {str(e)}")
            raise
    
    def disconnect(self):
        """S3 client doesn't need explicit disconnect"""
        logger.info("S3 connector closed")
    
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
                "details": None
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
        
        # Construct S3 key
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
    
    def create_table_if_not_exists(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """
        For S3, we don't create tables, but we can write metadata
        """
        if schema:
            base_path = f"{self.prefix}/{schema}/{table_name}"
        else:
            base_path = f"{self.prefix}/{table_name}"
        
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

