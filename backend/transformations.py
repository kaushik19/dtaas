import pandas as pd
from typing import List, Dict, Any
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class TransformationEngine:
    """Engine for applying data transformations"""
    
    @staticmethod
    def apply_transformations(df: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply a list of transformations to a DataFrame
        
        Transformation types:
        - add_column: Add a new column with constant value or expression
        - rename_column: Rename a column
        - drop_column: Drop a column
        - cast_type: Change column data type
        - filter_rows: Filter rows based on condition
        - replace_value: Replace values in a column
        - concatenate_columns: Concatenate multiple columns
        - split_column: Split a column into multiple columns
        - apply_function: Apply a custom function
        """
        
        if not transformations:
            return df
        
        result_df = df.copy()
        
        for transform in transformations:
            transform_type = transform.get('type')
            config = transform.get('config', {})
            
            try:
                if transform_type == 'add_column':
                    result_df = TransformationEngine._add_column(result_df, config)
                
                elif transform_type == 'rename_column':
                    result_df = TransformationEngine._rename_column(result_df, config)
                
                elif transform_type == 'drop_column':
                    result_df = TransformationEngine._drop_column(result_df, config)
                
                elif transform_type == 'cast_type':
                    result_df = TransformationEngine._cast_type(result_df, config)
                
                elif transform_type == 'filter_rows':
                    result_df = TransformationEngine._filter_rows(result_df, config)
                
                elif transform_type == 'replace_value':
                    result_df = TransformationEngine._replace_value(result_df, config)
                
                elif transform_type == 'concatenate_columns':
                    result_df = TransformationEngine._concatenate_columns(result_df, config)
                
                elif transform_type == 'split_column':
                    result_df = TransformationEngine._split_column(result_df, config)
                
                elif transform_type == 'apply_function':
                    result_df = TransformationEngine._apply_function(result_df, config)
                
                else:
                    logger.warning(f"Unknown transformation type: {transform_type}")
                
            except Exception as e:
                logger.error(f"Error applying transformation {transform_type}: {str(e)}")
                raise
        
        return result_df
    
    @staticmethod
    def _add_column(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Add a new column
        Config: {
            "column_name": "new_col",
            "value": "constant_value" or expression,
            "expression_type": "constant" | "column_reference" | "function"
        }
        """
        column_name = config.get('column_name')
        value = config.get('value')
        expression_type = config.get('expression_type', 'constant')
        
        if expression_type == 'constant':
            df[column_name] = value
        
        elif expression_type == 'column_reference':
            # Reference another column
            df[column_name] = df[value]
        
        elif expression_type == 'function':
            # Apply built-in functions
            if value == 'current_timestamp':
                df[column_name] = datetime.utcnow()
            elif value == 'row_number':
                df[column_name] = range(1, len(df) + 1)
            elif value.startswith('uuid'):
                import uuid
                df[column_name] = [str(uuid.uuid4()) for _ in range(len(df))]
            else:
                # Try to evaluate as expression
                df[column_name] = df.eval(value)
        
        return df
    
    @staticmethod
    def _rename_column(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Rename a column
        Config: {"old_name": "col1", "new_name": "col2"}
        """
        old_name = config.get('old_name')
        new_name = config.get('new_name')
        
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
        
        return df
    
    @staticmethod
    def _drop_column(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Drop a column
        Config: {"column_name": "col1"}
        """
        column_name = config.get('column_name')
        
        if column_name in df.columns:
            df = df.drop(columns=[column_name])
        
        return df
    
    @staticmethod
    def _cast_type(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Cast column to a different type
        Config: {"column_name": "col1", "target_type": "int64"}
        """
        column_name = config.get('column_name')
        target_type = config.get('target_type')
        
        if column_name in df.columns:
            df[column_name] = df[column_name].astype(target_type)
        
        return df
    
    @staticmethod
    def _filter_rows(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Filter rows based on condition
        Config: {
            "column_name": "col1",
            "operator": "==", ">", "<", ">=", "<=", "!=", "in", "not_in",
            "value": value_to_compare
        }
        """
        column_name = config.get('column_name')
        operator = config.get('operator')
        value = config.get('value')
        
        if column_name not in df.columns:
            return df
        
        if operator == '==':
            df = df[df[column_name] == value]
        elif operator == '!=':
            df = df[df[column_name] != value]
        elif operator == '>':
            df = df[df[column_name] > value]
        elif operator == '<':
            df = df[df[column_name] < value]
        elif operator == '>=':
            df = df[df[column_name] >= value]
        elif operator == '<=':
            df = df[df[column_name] <= value]
        elif operator == 'in':
            df = df[df[column_name].isin(value)]
        elif operator == 'not_in':
            df = df[~df[column_name].isin(value)]
        
        return df
    
    @staticmethod
    def _replace_value(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Replace values in a column
        Config: {
            "column_name": "col1",
            "old_value": "old",
            "new_value": "new"
        }
        """
        column_name = config.get('column_name')
        old_value = config.get('old_value')
        new_value = config.get('new_value')
        
        if column_name in df.columns:
            df[column_name] = df[column_name].replace(old_value, new_value)
        
        return df
    
    @staticmethod
    def _concatenate_columns(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Concatenate multiple columns
        Config: {
            "column_names": ["col1", "col2"],
            "separator": " ",
            "target_column": "new_col"
        }
        """
        column_names = config.get('column_names', [])
        separator = config.get('separator', '')
        target_column = config.get('target_column')
        
        if all(col in df.columns for col in column_names):
            df[target_column] = df[column_names].astype(str).agg(separator.join, axis=1)
        
        return df
    
    @staticmethod
    def _split_column(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Split a column into multiple columns
        Config: {
            "column_name": "col1",
            "separator": ",",
            "target_columns": ["col1_part1", "col1_part2"]
        }
        """
        column_name = config.get('column_name')
        separator = config.get('separator', ',')
        target_columns = config.get('target_columns', [])
        
        if column_name in df.columns:
            split_data = df[column_name].str.split(separator, expand=True)
            for idx, target_col in enumerate(target_columns):
                if idx < split_data.shape[1]:
                    df[target_col] = split_data[idx]
        
        return df
    
    @staticmethod
    def _apply_function(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply a function to a column
        Config: {
            "column_name": "col1",
            "function": "upper" | "lower" | "trim" | "length" | custom_expression,
            "target_column": "col1_transformed"
        }
        """
        column_name = config.get('column_name')
        function = config.get('function')
        target_column = config.get('target_column', column_name)
        
        if column_name not in df.columns:
            return df
        
        if function == 'upper':
            df[target_column] = df[column_name].str.upper()
        elif function == 'lower':
            df[target_column] = df[column_name].str.lower()
        elif function == 'trim':
            df[target_column] = df[column_name].str.strip()
        elif function == 'length':
            df[target_column] = df[column_name].str.len()
        else:
            # Try to apply as lambda expression
            try:
                df[target_column] = df[column_name].apply(eval(function))
            except Exception as e:
                logger.warning(f"Could not apply function {function}: {str(e)}")
        
        return df

