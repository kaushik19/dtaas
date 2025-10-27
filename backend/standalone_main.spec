# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['standalone_main.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend', 'frontend')],
    hiddenimports=[
        # SQLAlchemy
        'sqlalchemy.ext.baked',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy',
        
        # Pydantic
        'pydantic',
        'pydantic_core',
        'pydantic_settings',
        'pydantic.fields',
        'pydantic.main',
        
        # FastAPI
        'fastapi',
        'fastapi.routing',
        'fastapi.responses',
        'fastapi.staticfiles',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.applications',
        
        # Starlette
        'starlette',
        'starlette.routing',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.applications',
        
        # Uvicorn
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        
        # Data Processing
        'pandas',
        'numpy',
        'pyarrow',
        
        # Database Drivers
        'pyodbc',
        'psycopg2',
        'mysql.connector',
        'cx_Oracle',
        'snowflake.connector',
        'snowflake.connector.pandas_tools',
        
        # AWS/S3
        'boto3',
        'botocore',
        's3fs',
        
        # Core Dependencies
        'click',
        'h11',
        'anyio',
        'sniffio',
        'websockets',
        'redis',
        'celery',
        'celery.fixups',
        'celery.fixups.django',
        'celery.loaders',
        'celery.backends',
        'celery.backends.redis',
        'celery.app',
        'celery.app.task',
        'kombu',
        'kombu.transport',
        'kombu.transport.redis',
        'python_multipart',
        'multipart',
        'aiofiles',
        'httpx',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Note: collect_all() is not needed because we have comprehensive hiddenimports above
# PyInstaller will automatically collect all necessary files for the imported modules

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dtaas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

