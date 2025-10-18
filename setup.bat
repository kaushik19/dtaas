@echo off
echo ==================================
echo DTaaS Setup Script (Windows)
echo ==================================
echo.

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python not found. Please install Python 3.10+
    exit /b 1
)
echo ✓ Python found

REM Check Node
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo X Node.js not found. Please install Node.js 16+
    exit /b 1
)
echo ✓ Node.js found

echo.
echo ==================================
echo Setting up Backend...
echo ==================================

cd backend

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    (
        echo DATABASE_URL=sqlite:///./dtaas.db
        echo REDIS_URL=redis://localhost:6379/0
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
        echo LOG_LEVEL=INFO
    ) > .env
    echo ✓ Created .env file
) else (
    echo ✓ .env file already exists
)

REM Initialize database
echo Initializing database...
python -c "from database import init_db; init_db()"
echo ✓ Database initialized

cd ..

echo.
echo ==================================
echo Setting up Frontend...
echo ==================================

cd frontend

REM Install dependencies
echo Installing Node dependencies...
call npm install

cd ..

echo.
echo ==================================
echo ✓ Setup Complete!
echo ==================================
echo.
echo To start the application, run these commands in separate terminals:
echo.
echo Terminal 1 - Redis:
echo   docker run -d -p 6379:6379 redis:latest
echo   (or install Redis for Windows)
echo.
echo Terminal 2 - Backend API:
echo   cd backend
echo   venv\Scripts\activate
echo   python main.py
echo.
echo Terminal 3 - Celery Worker:
echo   cd backend
echo   venv\Scripts\activate
echo   celery -A celery_app worker --loglevel=info --pool=solo
echo.
echo Terminal 4 - Frontend:
echo   cd frontend
echo   npm run dev
echo.
echo Then open: http://localhost:5173
echo.
echo For detailed instructions, see QUICKSTART.md
echo ==================================

pause

