"""
Performance utilities for DTaaS
Optimized helper functions for memory calculation, data processing, and monitoring
"""
import pandas as pd
import logging
from typing import Dict, Any, Optional
from functools import wraps, lru_cache
from time import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def get_dataframe_memory_mb(df: pd.DataFrame) -> float:
    """
    Accurately calculate DataFrame memory usage in MB
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        Memory usage in megabytes (float)
    """
    # Get memory usage including index
    memory_bytes = df.memory_usage(deep=True).sum()
    memory_mb = memory_bytes / (1024 * 1024)
    return round(memory_mb, 2)


def get_dataframe_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get comprehensive DataFrame statistics
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        Dictionary with size, memory, dtypes stats
    """
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_mb": get_dataframe_memory_mb(df),
        "dtypes": df.dtypes.value_counts().to_dict(),
        "null_counts": df.isnull().sum().sum()
    }


def optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by converting dtypes
    
    Converts int64/float64 to smaller types where possible
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        Optimized DataFrame
    """
    original_memory = get_dataframe_memory_mb(df)
    
    for col in df.columns:
        col_type = df[col].dtype
        
        # Optimize integers
        if col_type == 'int64':
            c_min = df[col].min()
            c_max = df[col].max()
            
            if c_min >= 0:
                if c_max < 255:
                    df[col] = df[col].astype('uint8')
                elif c_max < 65535:
                    df[col] = df[col].astype('uint16')
                elif c_max < 4294967295:
                    df[col] = df[col].astype('uint32')
            else:
                if c_min > -128 and c_max < 127:
                    df[col] = df[col].astype('int8')
                elif c_min > -32768 and c_max < 32767:
                    df[col] = df[col].astype('int16')
                elif c_min > -2147483648 and c_max < 2147483647:
                    df[col] = df[col].astype('int32')
        
        # Optimize floats
        elif col_type == 'float64':
            df[col] = df[col].astype('float32')
        
        # Optimize objects (strings)
        elif col_type == 'object':
            try:
                # Try to convert to category if unique values < 50% of total
                num_unique = df[col].nunique()
                num_total = len(df[col])
                if num_unique / num_total < 0.5:
                    df[col] = df[col].astype('category')
            except:
                pass
    
    optimized_memory = get_dataframe_memory_mb(df)
    reduction = ((original_memory - optimized_memory) / original_memory) * 100
    
    logger.info(f"DataFrame memory optimized: {original_memory:.2f} MB → {optimized_memory:.2f} MB (reduced by {reduction:.1f}%)")
    
    return df


def batch_dataframe(df: pd.DataFrame, batch_size: int):
    """
    Generator to yield DataFrame in batches
    
    Memory-efficient chunking for large DataFrames
    
    Args:
        df: Pandas DataFrame
        batch_size: Number of rows per batch
        
    Yields:
        DataFrame chunks
    """
    num_batches = (len(df) + batch_size - 1) // batch_size
    
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(df))
        yield df.iloc[start_idx:end_idx].copy()


def timing_decorator(func):
    """
    Decorator to measure function execution time
    
    Usage:
        @timing_decorator
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        elapsed_time = time() - start_time
        
        logger.info(f"{func.__name__} completed in {elapsed_time:.2f} seconds")
        return result
    
    return wrapper


@contextmanager
def timer(operation_name: str):
    """
    Context manager to time operations
    
    Usage:
        with timer("Data Transfer"):
            # ... code ...
    """
    start_time = time()
    logger.info(f"⏱️  Starting: {operation_name}")
    
    try:
        yield
    finally:
        elapsed_time = time() - start_time
        logger.info(f"✓ {operation_name} completed in {elapsed_time:.2f} seconds")


@lru_cache(maxsize=128)
def calculate_optimal_batch_size(total_rows: int, available_memory_mb: int = 512) -> int:
    """
    Calculate optimal batch size based on available memory
    
    Args:
        total_rows: Total number of rows
        available_memory_mb: Available memory in MB
        
    Returns:
        Optimal batch size (int)
    """
    # Assume average row size of 1KB
    estimated_row_size_kb = 1
    
    # Calculate batch size that fits in available memory with 20% buffer
    batch_size = int((available_memory_mb * 1024 * 0.8) / estimated_row_size_kb)
    
    # Clamp to reasonable range
    batch_size = max(1000, min(batch_size, 100000))
    
    # If total rows is less than calculated batch size, use total rows
    if total_rows < batch_size:
        batch_size = total_rows
    
    logger.debug(f"Calculated optimal batch size: {batch_size} for {total_rows} rows")
    return batch_size


class ProgressTracker:
    """
    Track and log progress of long-running operations
    """
    
    def __init__(self, total: int, operation_name: str = "Operation", log_interval: int = 10):
        """
        Args:
            total: Total items to process
            operation_name: Name of the operation
            log_interval: Log progress every N percent
        """
        self.total = total
        self.current = 0
        self.operation_name = operation_name
        self.log_interval = log_interval
        self.start_time = time()
        self.last_logged_percent = 0
    
    def update(self, count: int = 1):
        """Update progress by count items"""
        self.current += count
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        
        # Log at intervals
        if percent - self.last_logged_percent >= self.log_interval:
            elapsed = time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            eta = (self.total - self.current) / rate if rate > 0 else 0
            
            logger.info(
                f"📊 {self.operation_name}: {self.current}/{self.total} "
                f"({percent:.1f}%) | Rate: {rate:.0f} items/sec | ETA: {eta:.0f}s"
            )
            
            self.last_logged_percent = percent
    
    def complete(self):
        """Mark operation as complete"""
        elapsed = time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"✓ {self.operation_name} completed: {self.current} items in {elapsed:.2f}s "
            f"(avg rate: {rate:.0f} items/sec)"
        )

