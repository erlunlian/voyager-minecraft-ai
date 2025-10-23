#!/bin/bash

echo "================================"
echo "Voyager Minecraft AI Reset"
echo "================================"
echo ""
echo "⚠️  This will delete ALL data including:"
echo "  - All sessions"
echo "  - All learned skills"
echo "  - All task history"
echo "  - Database volumes"
echo ""
read -p "Are you sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

echo ""
echo "Stopping containers..."
docker-compose down -v

echo "Removing data directories..."
rm -rf data/postgres data/chroma

echo "Creating fresh directories..."
mkdir -p data/postgres data/chroma

echo "Starting databases..."
docker-compose up -d

echo ""
echo "================================"
echo "Reset complete!"
echo "================================"
echo ""
echo "You can now run: python src/main.py"
echo ""

