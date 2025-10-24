"""
Custom exceptions for DTaaS application
Provides better error handling and debugging capabilities
"""
from typing import Optional, Dict, Any


class DTaaSException(Exception):
    """Base exception for all DTaaS errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class TaskNotFoundException(DTaaSException):
    """Raised when a task is not found"""
    pass


class TaskStoppedException(DTaaSException):
    """Raised when a task is stopped by user"""
    pass


class ConnectorException(DTaaSException):
    """Base exception for connector errors"""
    pass


class ConnectionFailedException(ConnectorException):
    """Raised when connection to source/destination fails"""
    pass


class DataTransferException(DTaaSException):
    """Raised when data transfer fails"""
    pass


class TransformationException(DTaaSException):
    """Raised when data transformation fails"""
    pass


class VariableResolutionException(DTaaSException):
    """Raised when variable resolution fails"""
    pass


class SchemaException(DTaaSException):
    """Raised when schema-related errors occur"""
    pass


class CDCException(DTaaSException):
    """Raised when CDC-related errors occur"""
    pass


class ValidationException(DTaaSException):
    """Raised when validation fails"""
    pass


class ConfigurationException(DTaaSException):
    """Raised when configuration is invalid"""
    pass


class RetryExhaustedException(DTaaSException):
    """Raised when maximum retries are exhausted"""
    def __init__(self, table_name: str, attempts: int, last_error: str):
        super().__init__(
            f"Failed to transfer table '{table_name}' after {attempts} attempts",
            details={"table": table_name, "attempts": attempts, "last_error": last_error}
        )

