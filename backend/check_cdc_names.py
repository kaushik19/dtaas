import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=vr-saas-dev.rds.dev.vr.avalara.net,1433;'
    'DATABASE=impenduloredux;'
    'UID=admin;'
    'PWD=^Va!Ar^123;'
    'TrustServerCertificate=yes;'
    'Connection Timeout=60;'
    'Login Timeout=60;'
)

cursor = conn.cursor()
cursor.execute("""
    SELECT 
        t.name as table_name, 
        ct.capture_instance,
        OBJECT_NAME(ct.object_id) as function_name
    FROM cdc.change_tables ct 
    INNER JOIN sys.tables t ON ct.source_object_id = t.object_id
    WHERE t.name IN ('VAT Returns', 'ZIP Codes CZ', 'ZIP Codes PT', 'Changes Log', 'Companies', 'Ledgers')
    ORDER BY t.name
""")

results = cursor.fetchall()
for r in results:
    print(f"Table: '{r[0]:25s}' -> Capture: '{r[1]:35s}' -> Function: '{r[2]}'")

conn.close()

