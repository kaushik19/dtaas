@echo off
REM Simple build script for DTaaS Standalone Application (Windows)

REM Keep window open on error
if not "%1"=="nopause" (
    call %0 nopause
    pause
    exit /b
)

echo ========================================
echo Building DTaaS Standalone Application
echo ========================================
echo.
echo This will take 5-10 minutes...
echo.

REM Step 1: Check Node.js
echo [STEP 1/5] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found!
    echo Please install Node.js from https://nodejs.org/
    echo.
    exit /b 1
)
node --version
echo OK - Node.js found
echo.

REM Step 2: Build Frontend
echo [STEP 2/5] Building Vue.js Frontend...
if not exist frontend (
    echo ERROR: frontend folder not found!
    exit /b 1
)
cd frontend

REM Always clean to avoid npm/rollup issues
echo Cleaning previous build artifacts...
echo   - Removing node_modules (if exists)...
if exist node_modules (
    rmdir /s /q node_modules
    echo     Done
) else (
    echo     Already clean
)
echo   - Removing package-lock.json (if exists)...
if exist package-lock.json (
    del /f /q package-lock.json
    echo     Done
) else (
    echo     Already clean
)

echo Installing frontend dependencies (fresh)...
call npm install
call npm audit fix
if %errorlevel% neq 0 (
    echo ERROR: npm install failed!
    echo Try running: npm cache clean --force
    cd ..
    exit /b 1
)

echo Building frontend...
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: npm build failed!
    cd ..
    exit /b 1
)

cd ..
echo OK - Frontend built successfully
echo.

REM Step 3: Copy frontend to backend
echo [STEP 3/5] Copying frontend to backend...
if not exist frontend\dist (
    echo ERROR: frontend\dist folder not found!
    echo Frontend build may have failed.
    exit /b 1
)
if exist backend\frontend (
    echo Removing old frontend folder...
    rmdir /s /q backend\frontend
)
echo Copying files...
xcopy /E /I /Y frontend\dist backend\frontend >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy frontend files!
    exit /b 1
)
echo OK - Frontend copied to backend
echo.

REM Step 4: Check Python and Install Dependencies
echo [STEP 4/6] Checking Python and installing dependencies...
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python from https://www.python.org/
    echo.
    exit /b 1
)
py --version

echo Installing backend requirements...
echo This may take a few minutes...
cd backend

REM Install core requirements first (these should always work)
py -m pip install --quiet --only-binary :all: fastapi uvicorn sqlalchemy pydantic pydantic-settings pandas pyarrow boto3 websockets
if %errorlevel% neq 0 (
    echo ERROR: Failed to install core requirements!
    cd ..
    exit /b 1
)

REM Try to install database drivers (some may fail on Python 3.13, that's okay)
echo Installing database drivers (some may be skipped)...
py -m pip install --quiet --only-binary :all: --ignore-requires-python pyodbc pymssql psycopg2-binary mysql-connector-python 2>nul
py -m pip install --quiet --only-binary :all: --ignore-requires-python cx-Oracle snowflake-connector-python 2>nul

REM Install remaining requirements
py -m pip install --quiet --only-binary :all: celery redis python-multipart python-dotenv httpx aiofiles s3fs python-socketio 2>nul

cd ..
echo Backend requirements installed successfully
echo Note: Some database drivers may have been skipped due to Python version compatibility

echo Installing PyInstaller...
py -m pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo WARNING: pip install had issues, but continuing...
)
echo OK - PyInstaller ready
echo.

REM Step 5: Build executable
echo [STEP 5/6] Building standalone executable...
echo This may take 5-10 minutes, please wait...
echo.
if not exist backend (
    echo ERROR: backend folder not found!
    exit /b 1
)
cd backend

echo Option 1: Using PyInstaller with spec file (recommended)...
if exist standalone_main.spec (
    py -m PyInstaller standalone_main.spec --clean --noconfirm
    goto :check_build
)

echo Option 2: Using PyInstaller command line...
py -m PyInstaller --name=dtaas --onefile --clean --noconfirm ^
  --hidden-import=sqlalchemy.ext.baked ^
  --hidden-import=sqlalchemy.sql.default_comparator ^
  --hidden-import=sqlalchemy ^
  --hidden-import=pydantic ^
  --hidden-import=pydantic_core ^
  --hidden-import=fastapi ^
  --hidden-import=fastapi.routing ^
  --hidden-import=fastapi.responses ^
  --hidden-import=fastapi.staticfiles ^
  --hidden-import=fastapi.middleware ^
  --hidden-import=fastapi.middleware.cors ^
  --hidden-import=starlette ^
  --hidden-import=starlette.routing ^
  --hidden-import=starlette.responses ^
  --hidden-import=starlette.staticfiles ^
  --hidden-import=starlette.middleware ^
  --hidden-import=starlette.middleware.cors ^
  --hidden-import=uvicorn ^
  --hidden-import=uvicorn.logging ^
  --hidden-import=uvicorn.loops ^
  --hidden-import=uvicorn.loops.auto ^
  --hidden-import=uvicorn.protocols ^
  --hidden-import=uvicorn.protocols.http ^
  --hidden-import=uvicorn.protocols.http.auto ^
  --hidden-import=uvicorn.protocols.websockets ^
  --hidden-import=uvicorn.protocols.websockets.auto ^
  --hidden-import=uvicorn.lifespan ^
  --hidden-import=uvicorn.lifespan.on ^
  --hidden-import=pandas ^
  --hidden-import=pyodbc ^
  --hidden-import=psycopg2 ^
  --hidden-import=mysql.connector ^
  --hidden-import=boto3 ^
  --hidden-import=botocore ^
  --hidden-import=click ^
  --hidden-import=h11 ^
  --hidden-import=anyio ^
  --hidden-import=sniffio ^
  --copy-metadata=fastapi ^
  --copy-metadata=pydantic ^
  --copy-metadata=uvicorn ^
  --copy-metadata=starlette ^
  --collect-all=fastapi ^
  --collect-all=uvicorn ^
  --collect-all=pydantic ^
  --collect-all=starlette ^
  --add-data="frontend;frontend" ^
  standalone_main.py

:check_build
if %errorlevel% neq 0 (
    cd ..
    echo.
    echo ERROR: PyInstaller build failed!
    echo Check the error messages above.
    exit /b 1
)

cd ..
echo OK - Executable created
echo.

REM Step 6: Copy to dist folder
echo [FINALIZING] Creating distribution folder...
if not exist backend\dist\dtaas.exe (
    echo ERROR: dtaas.exe not found in backend\dist!
    echo PyInstaller may have failed.
    exit /b 1
)
if not exist dist mkdir dist
echo Copying executable to dist folder...
copy /Y backend\dist\dtaas.exe dist\dtaas.exe >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy executable!
    exit /b 1
)

REM Create README
echo DTaaS - Data Transfer as a Service > dist\README.txt
echo Standalone Application >> dist\README.txt
echo. >> dist\README.txt
echo QUICK START: >> dist\README.txt
echo 1. Double-click dtaas.exe >> dist\README.txt
echo 2. Browser opens to http://localhost:8000 >> dist\README.txt
echo 3. Start using DTaaS! >> dist\README.txt
echo. >> dist\README.txt
echo API Access: http://localhost:8000/docs >> dist\README.txt

echo.
echo ========================================
echo SUCCESS! Build Complete!
echo ========================================
echo.
echo Executable location: dist\dtaas.exe
echo.
for %%I in (dist\dtaas.exe) do echo File size: %%~zI bytes (~%%~zI / 1048576 MB)
echo.
echo To run the application:
echo   1. Open dist folder
echo   2. Double-click dtaas.exe
echo   3. Browser will open to http://localhost:8000
echo.
echo Or run from command line:
echo   cd dist
echo   dtaas.exe
echo.
echo ========================================
echo.
echo Press any key to exit...

