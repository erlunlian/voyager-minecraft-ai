#!/bin/bash

echo "================================"
echo "Voyager Minecraft AI Status"
echo "================================"
echo ""

echo "Docker Containers:"
docker-compose ps

echo ""
echo "Database Connection Test:"

# Test PostgreSQL
if docker exec voyager-postgres pg_isready -U voyager &> /dev/null; then
    echo "✓ PostgreSQL: Connected"
else
    echo "❌ PostgreSQL: Not accessible"
fi

# Test ChromaDB
if curl -s http://localhost:8000/api/v1/heartbeat &> /dev/null; then
    echo "✓ ChromaDB: Connected"
else
    echo "❌ ChromaDB: Not accessible"
fi

echo ""
echo "Recent Sessions:"
docker exec voyager-postgres psql -U voyager -d voyager_db -c "SELECT session_id, bot_username, status, start_time FROM sessions ORDER BY start_time DESC LIMIT 5;" 2>/dev/null || echo "No sessions found or database not initialized"

echo ""

