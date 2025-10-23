#!/bin/bash

echo "================================"
echo "Voyager Minecraft AI Setup"
echo "================================"
echo ""

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

# Check Node.js
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi
echo "✓ Node.js found: $(node --version)"

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker"
    exit 1
fi
echo "✓ Docker found: $(docker --version)"

# Check Docker Compose
echo "Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose"
    exit 1
fi
echo "✓ Docker Compose found: $(docker-compose --version)"

echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Python dependencies installed in venv"

echo ""
echo "Installing Node.js dependencies..."
npm install

echo ""
echo "Building TypeScript..."
npm run build
echo "✓ TypeScript compiled to dist/"

echo ""
echo "Starting databases..."
docker-compose up -d

echo ""
echo "Waiting for databases to be ready..."
sleep 5

echo ""
echo "================================"
echo "Setup complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Add your Azure OpenAI credentials to .env"
echo "3. Configure Minecraft server settings in .env"
echo "4. Activate virtual environment: source venv/bin/activate"
echo "5. Run: python src/main.py"
echo ""
echo "Note: Always activate the venv before running:"
echo "  source venv/bin/activate"
echo ""

