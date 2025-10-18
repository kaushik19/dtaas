#!/bin/bash

echo "=================================="
echo "DTaaS Setup Script"
echo "=================================="
echo ""

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Check Node
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi
echo "✅ Node.js found: $(node --version)"

# Check Redis
echo "Checking Redis..."
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis CLI not found. You'll need Redis to run the app."
    echo "   Install with: brew install redis (Mac) or apt-get install redis (Linux)"
else
    echo "✅ Redis found"
fi

echo ""
echo "=================================="
echo "Setting up Backend..."
echo "=================================="

cd backend

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
DATABASE_URL=sqlite:///./dtaas.db
REDIS_URL=redis://localhost:6379/0
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

# Initialize database
echo "Initializing database..."
python -c "from database import init_db; init_db()"
echo "✅ Database initialized"

cd ..

echo ""
echo "=================================="
echo "Setting up Frontend..."
echo "=================================="

cd frontend

# Install dependencies
echo "Installing Node dependencies..."
npm install

cd ..

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "To start the application, run these commands in separate terminals:"
echo ""
echo "Terminal 1 - Redis:"
echo "  redis-server"
echo "  (or with Docker: docker run -d -p 6379:6379 redis:latest)"
echo ""
echo "Terminal 2 - Backend API:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "Terminal 3 - Celery Worker:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  celery -A celery_app worker --loglevel=info"
echo ""
echo "Terminal 4 - Frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Then open: http://localhost:5173"
echo ""
echo "For detailed instructions, see QUICKSTART.md"
echo "=================================="

