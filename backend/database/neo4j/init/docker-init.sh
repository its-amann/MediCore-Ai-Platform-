#!/bin/bash
# Docker initialization script for Neo4j
# This script can be used to initialize Neo4j in a Docker container

set -e

echo "Starting Neo4j database initialization..."

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
until cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-password}" "RETURN 1" >/dev/null 2>&1; do
    echo "Neo4j is unavailable - sleeping"
    sleep 2
done

echo "Neo4j is ready!"

# Execute initialization scripts in order
SCRIPT_DIR="/var/lib/neo4j/init"

# Array of scripts to execute
scripts=(
    "001_create_constraints.cypher"
    "002_create_indexes.cypher"
    "003_create_vector_indexes.cypher"
    "004_seed_doctors.cypher"
    "005_seed_test_data.cypher"
    "006_create_functions.cypher"
)

# Execute each script
for script in "${scripts[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        echo "Executing $script..."
        cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-password}" -f "$SCRIPT_DIR/$script" || {
            echo "Warning: $script execution had issues (possibly constraints/indexes already exist)"
        }
    else
        echo "Warning: $script not found in $SCRIPT_DIR"
    fi
done

echo "Neo4j initialization complete!"

# Verify initialization
echo "Verifying database initialization..."
cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-password}" <<EOF
MATCH (n)
RETURN labels(n)[0] as label, count(n) as count
ORDER BY label;
EOF