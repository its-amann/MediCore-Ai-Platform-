#!/bin/bash

echo "Waiting for Neo4j to be ready..."

# Wait for Neo4j to be ready
until docker exec medical-ai-neo4j neo4j status | grep -q "Neo4j is running"; do
    echo "Neo4j is not ready yet. Waiting..."
    sleep 5
done

echo "Neo4j is ready! Initializing database..."

# Change to backend directory
cd ../..

# Run the database initialization script
echo "Running database initialization..."
python database/neo4j/init/initialize_neo4j.py

echo "Database initialization complete!"