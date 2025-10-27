# Import connectors with optional dependencies
from .sql_server import SQLServerConnector
from .postgresql import PostgreSQLConnector
from .mysql import MySQLConnector
from .s3 import S3Connector
from .base import SourceConnector, DestinationConnector

# Optional connectors (may not be available in all environments)
__all__ = [
    'SQLServerConnector',
    'PostgreSQLConnector',
    'MySQLConnector',
    'S3Connector',
    'SourceConnector',
    'DestinationConnector',
]

# Try to import Oracle connector (requires cx_Oracle)
try:
    from .oracle import OracleConnector
    __all__.append('OracleConnector')
except ImportError:
    OracleConnector = None

# Try to import Snowflake connector (requires snowflake-connector-python)
try:
    from .snowflake import SnowflakeConnector
    __all__.append('SnowflakeConnector')
except ImportError:
    SnowflakeConnector = None

