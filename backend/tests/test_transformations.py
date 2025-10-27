"""
Unit Tests for Data Transformations
Tests all transformation functions
"""
import pytest
import pandas as pd
from datetime import datetime
import transformations


@pytest.mark.unit
class TestColumnTransformations:
    """Test column-level transformations"""
    
    def test_rename_column(self, mock_dataframe):
        """Test renaming a column"""
        result = transformations.rename_column(
            mock_dataframe, 
            "name", 
            "full_name"
        )
        assert "full_name" in result.columns
        assert "name" not in result.columns
        assert len(result) == len(mock_dataframe)
    
    def test_drop_column(self, mock_dataframe):
        """Test dropping a column"""
        result = transformations.drop_column(mock_dataframe, "age")
        assert "age" not in result.columns
        assert "name" in result.columns
        assert len(result) == len(mock_dataframe)
    
    def test_cast_column_type(self, mock_dataframe):
        """Test casting column types"""
        result = transformations.cast_column(
            mock_dataframe, 
            "age", 
            "str"
        )
        assert result["age"].dtype == object
        assert isinstance(result["age"].iloc[0], str)
    
    def test_uppercase_column(self, mock_dataframe):
        """Test uppercase transformation"""
        result = transformations.uppercase(mock_dataframe, "name")
        assert result["name"].iloc[0] == "ALICE"
        assert result["name"].iloc[1] == "BOB"
    
    def test_lowercase_column(self, mock_dataframe):
        """Test lowercase transformation"""
        result = transformations.lowercase(mock_dataframe, "name")
        assert result["name"].iloc[0] == "alice"
        assert result["name"].iloc[1] == "bob"
    
    def test_trim_column(self):
        """Test trimming whitespace"""
        df = pd.DataFrame({
            'name': ['  Alice  ', '  Bob  ', '  Charlie  ']
        })
        result = transformations.trim(df, "name")
        assert result["name"].iloc[0] == "Alice"
        assert result["name"].iloc[2] == "Charlie"
    
    def test_replace_value(self, mock_dataframe):
        """Test replacing values"""
        result = transformations.replace_value(
            mock_dataframe,
            "name",
            "Alice",
            "Alicia"
        )
        assert result["name"].iloc[0] == "Alicia"
        assert result["name"].iloc[1] == "Bob"
    
    def test_add_prefix(self, mock_dataframe):
        """Test adding prefix to column values"""
        result = transformations.add_prefix(
            mock_dataframe,
            "name",
            "Mr. "
        )
        assert result["name"].iloc[0] == "Mr. Alice"
        assert result["name"].iloc[1] == "Mr. Bob"
    
    def test_add_suffix(self, mock_dataframe):
        """Test adding suffix to column values"""
        result = transformations.add_suffix(
            mock_dataframe,
            "name",
            " Jr."
        )
        assert result["name"].iloc[0] == "Alice Jr."


@pytest.mark.unit
class TestRowTransformations:
    """Test row-level transformations"""
    
    def test_filter_rows(self, mock_dataframe):
        """Test filtering rows"""
        result = transformations.filter_rows(
            mock_dataframe,
            "age > 28"
        )
        assert len(result) == 2  # Bob and Charlie
        assert result["name"].iloc[0] == "Bob"
    
    def test_remove_duplicates(self):
        """Test removing duplicate rows"""
        df = pd.DataFrame({
            'id': [1, 2, 2, 3],
            'name': ['Alice', 'Bob', 'Bob', 'Charlie']
        })
        result = transformations.remove_duplicates(df)
        assert len(result) == 3
    
    def test_sort_rows(self, mock_dataframe):
        """Test sorting rows"""
        result = transformations.sort_rows(
            mock_dataframe,
            "age",
            ascending=False
        )
        assert result["age"].iloc[0] == 35  # Charlie
        assert result["age"].iloc[-1] == 25  # Alice
    
    def test_limit_rows(self, mock_dataframe):
        """Test limiting number of rows"""
        result = transformations.limit_rows(mock_dataframe, 2)
        assert len(result) == 2


@pytest.mark.unit
class TestDataTypeTransformations:
    """Test data type transformations"""
    
    def test_to_datetime(self):
        """Test converting to datetime"""
        df = pd.DataFrame({
            'date_str': ['2024-01-01', '2024-01-02', '2024-01-03']
        })
        result = transformations.to_datetime(df, "date_str")
        assert pd.api.types.is_datetime64_any_dtype(result["date_str"])
    
    def test_to_numeric(self):
        """Test converting to numeric"""
        df = pd.DataFrame({
            'value': ['100', '200', '300']
        })
        result = transformations.to_numeric(df, "value")
        assert pd.api.types.is_numeric_dtype(result["value"])
    
    def test_to_string(self, mock_dataframe):
        """Test converting to string"""
        result = transformations.to_string(mock_dataframe, "age")
        assert result["age"].dtype == object
        assert isinstance(result["age"].iloc[0], str)


@pytest.mark.unit
class TestAggregationTransformations:
    """Test aggregation transformations"""
    
    def test_group_by_aggregate(self, mock_dataframe):
        """Test group by with aggregation"""
        df = pd.DataFrame({
            'category': ['A', 'A', 'B', 'B'],
            'value': [10, 20, 30, 40]
        })
        result = transformations.group_by(
            df,
            ['category'],
            {'value': 'sum'}
        )
        assert len(result) == 2
        assert result[result['category'] == 'A']['value'].iloc[0] == 30
    
    def test_pivot_table(self):
        """Test pivot table transformation"""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-01', '2024-01-02'],
            'category': ['A', 'B', 'A'],
            'value': [10, 20, 30]
        })
        result = transformations.pivot_table(
            df,
            values='value',
            index='date',
            columns='category',
            aggfunc='sum'
        )
        assert 'A' in result.columns
        assert 'B' in result.columns


@pytest.mark.unit
class TestNullHandling:
    """Test null value handling"""
    
    def test_fill_null_with_value(self):
        """Test filling nulls with a specific value"""
        df = pd.DataFrame({
            'value': [1, None, 3, None, 5]
        })
        result = transformations.fill_null(df, "value", 0)
        assert result["value"].isnull().sum() == 0
        assert result["value"].iloc[1] == 0
    
    def test_drop_null_rows(self):
        """Test dropping rows with nulls"""
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [1, None, 3, None, 5]
        })
        result = transformations.drop_nulls(df, "value")
        assert len(result) == 3
        assert result["value"].isnull().sum() == 0
    
    def test_forward_fill(self):
        """Test forward fill for nulls"""
        df = pd.DataFrame({
            'value': [1, None, None, 4, None]
        })
        result = transformations.forward_fill(df, "value")
        assert result["value"].iloc[1] == 1
        assert result["value"].iloc[2] == 1


@pytest.mark.unit
class TestStringTransformations:
    """Test string-specific transformations"""
    
    def test_substring(self):
        """Test extracting substring"""
        df = pd.DataFrame({
            'text': ['Hello World', 'Test String', 'Another Test']
        })
        result = transformations.substring(df, "text", start=0, length=5)
        assert result["text"].iloc[0] == "Hello"
        assert result["text"].iloc[1] == "Test "
    
    def test_concatenate_columns(self, mock_dataframe):
        """Test concatenating columns"""
        result = transformations.concatenate_columns(
            mock_dataframe,
            ["name", "age"],
            "name_age",
            separator=" - "
        )
        assert "name_age" in result.columns
        assert "Alice - 25" in result["name_age"].iloc[0]
    
    def test_split_column(self):
        """Test splitting column into multiple columns"""
        df = pd.DataFrame({
            'full_name': ['John Doe', 'Jane Smith', 'Bob Johnson']
        })
        result = transformations.split_column(
            df,
            "full_name",
            " ",
            ["first_name", "last_name"]
        )
        assert "first_name" in result.columns
        assert "last_name" in result.columns
        assert result["first_name"].iloc[0] == "John"
        assert result["last_name"].iloc[0] == "Doe"


@pytest.mark.unit
class TestDateTransformations:
    """Test date/time transformations"""
    
    def test_extract_year(self, mock_dataframe):
        """Test extracting year from datetime"""
        result = transformations.extract_year(mock_dataframe, "created_at", "year")
        assert "year" in result.columns
        assert result["year"].iloc[0] == datetime.now().year
    
    def test_extract_month(self, mock_dataframe):
        """Test extracting month from datetime"""
        result = transformations.extract_month(mock_dataframe, "created_at", "month")
        assert "month" in result.columns
        assert 1 <= result["month"].iloc[0] <= 12
    
    def test_extract_day(self, mock_dataframe):
        """Test extracting day from datetime"""
        result = transformations.extract_day(mock_dataframe, "created_at", "day")
        assert "day" in result.columns
        assert 1 <= result["day"].iloc[0] <= 31
    
    def test_date_diff(self):
        """Test calculating date difference"""
        df = pd.DataFrame({
            'start_date': [datetime(2024, 1, 1), datetime(2024, 1, 1)],
            'end_date': [datetime(2024, 1, 10), datetime(2024, 1, 20)]
        })
        result = transformations.date_diff(
            df,
            "start_date",
            "end_date",
            "days_diff"
        )
        assert "days_diff" in result.columns
        assert result["days_diff"].iloc[0] == 9
        assert result["days_diff"].iloc[1] == 19


@pytest.mark.unit
class TestConditionalTransformations:
    """Test conditional transformations"""
    
    def test_case_when(self, mock_dataframe):
        """Test conditional case when transformation"""
        result = transformations.case_when(
            mock_dataframe,
            "age_group",
            conditions=[
                ("age < 30", "Young"),
                ("age >= 30", "Adult")
            ],
            default="Unknown"
        )
        assert "age_group" in result.columns
        assert result["age_group"].iloc[0] == "Young"  # Alice, 25
        assert result["age_group"].iloc[1] == "Adult"  # Bob, 30
    
    def test_apply_custom_function(self, mock_dataframe):
        """Test applying custom function"""
        def double_age(row):
            return row['age'] * 2
        
        result = transformations.apply_function(
            mock_dataframe,
            double_age,
            "double_age"
        )
        assert "double_age" in result.columns
        assert result["double_age"].iloc[0] == 50  # Alice, 25 * 2


@pytest.mark.unit
class TestBulkTransformations:
    """Test applying multiple transformations"""
    
    def test_apply_multiple_transformations(self, mock_dataframe):
        """Test applying a chain of transformations"""
        transformations_list = [
            {"type": "uppercase", "column": "name"},
            {"type": "filter", "condition": "age > 25"},
            {"type": "sort", "column": "age", "ascending": True}
        ]
        result = mock_dataframe.copy()
        
        for transform in transformations_list:
            if transform["type"] == "uppercase":
                result = transformations.uppercase(result, transform["column"])
            elif transform["type"] == "filter":
                result = transformations.filter_rows(result, transform["condition"])
            elif transform["type"] == "sort":
                result = transformations.sort_rows(
                    result, 
                    transform["column"], 
                    transform.get("ascending", True)
                )
        
        assert len(result) == 2  # Bob and Charlie
        assert result["name"].iloc[0] == "BOB"
        assert result["age"].iloc[0] == 30


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in transformations"""
    
    def test_invalid_column_name(self, mock_dataframe):
        """Test transformation with invalid column name"""
        with pytest.raises((KeyError, ValueError)):
            transformations.rename_column(mock_dataframe, "nonexistent", "new_name")
    
    def test_invalid_data_type_conversion(self):
        """Test invalid data type conversion"""
        df = pd.DataFrame({
            'text': ['not', 'a', 'number']
        })
        with pytest.raises((ValueError, TypeError)):
            transformations.to_numeric(df, "text", errors='raise')
    
    def test_empty_dataframe(self):
        """Test transformations on empty dataframe"""
        df = pd.DataFrame()
        result = transformations.remove_duplicates(df)
        assert len(result) == 0

