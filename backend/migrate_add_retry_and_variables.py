"""
Migration script to add new columns for retry feature and global variables
"""
import sqlite3
import os

DATABASE_PATH = os.getenv('DATABASE_URL', 'sqlite:///./dtaas.db').replace('sqlite:///', '')

def migrate():
    print(f"Connecting to database: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Add retry columns to tasks table
        print("Adding retry columns to tasks table...")
        
        retry_columns = [
            ("retry_enabled", "BOOLEAN DEFAULT 1"),
            ("retry_delay_seconds", "INTEGER DEFAULT 20"),
            ("max_retries", "INTEGER DEFAULT 3"),
            ("cleanup_on_retry", "BOOLEAN DEFAULT 1"),
        ]
        
        for column_name, column_def in retry_columns:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} {column_def}")
                print(f"  ✓ Added {column_name} to tasks")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Column {column_name} already exists")
                else:
                    print(f"  ✗ Error adding {column_name}: {e}")
        
        # Add retry tracking columns to table_executions
        print("\nAdding retry tracking columns to table_executions...")
        
        tracking_columns = [
            ("retry_count", "INTEGER DEFAULT 0"),
            ("last_retry_at", "DATETIME"),
        ]
        
        for column_name, column_def in tracking_columns:
            try:
                cursor.execute(f"ALTER TABLE table_executions ADD COLUMN {column_name} {column_def}")
                print(f"  ✓ Added {column_name} to table_executions")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Column {column_name} already exists")
                else:
                    print(f"  ✗ Error adding {column_name}: {e}")
        
        # Create global_variables table if it doesn't exist
        print("\nCreating global_variables table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_variables (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    variable_type VARCHAR(20) NOT NULL,
                    config JSON NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100)
                )
            """)
            print("  ✓ Created global_variables table")
        except sqlite3.OperationalError as e:
            print(f"  - Table already exists or error: {e}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()

