from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class BaseConnector(ABC):
    """Base class for all connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status"""
        pass
    
    @abstractmethod
    def connect(self):
        """Establish connection"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection"""
        pass


class SourceConnector(BaseConnector):
    """Base class for source connectors"""
    
    @abstractmethod
    def list_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tables in the source"""
        pass
    
    @abstractmethod
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        pass
    
    @abstractmethod
    def get_table_row_count(self, table_name: str, schema: Optional[str] = None) -> int:
        """Get total row count for a table"""
        pass
    
    @abstractmethod
    def read_data(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        batch_size: int = 10000,
        offset: int = 0
    ) -> pd.DataFrame:
        """Read data from table in batches"""
        pass
    
    @abstractmethod
    def enable_cdc(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Enable CDC on a table"""
        pass
    
    @abstractmethod
    def is_cdc_enabled(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if CDC is enabled on a table"""
        pass
    
    @abstractmethod
    def read_cdc_changes(
        self, 
        table_name: str,
        from_lsn: Optional[str] = None,
        schema: Optional[str] = None
    ) -> tuple[pd.DataFrame, str]:
        """Read CDC changes. Returns (dataframe, last_lsn)"""
        pass


class DestinationConnector(BaseConnector):
    """Base class for destination connectors"""
    
    @abstractmethod
    def write_data(
        self,
        data: pd.DataFrame,
        table_name: str,
        mode: str = "append",  # append, overwrite, upsert
        schema: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Write data to destination"""
        pass
    
    @abstractmethod
    def create_table_if_not_exists(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """Create table if it doesn't exist"""
        pass
    
    @abstractmethod
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if table exists"""
        pass
    
    @abstractmethod
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get table schema"""
        pass
    
    @abstractmethod
    def handle_schema_drift(
        self,
        table_name: str,
        new_columns: List[Dict[str, Any]],
        schema: Optional[str] = None
    ) -> bool:
        """Handle schema changes (add new columns)"""
        pass

