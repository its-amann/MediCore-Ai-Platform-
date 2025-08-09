# Neo4j Database Initialization Scripts

This directory contains the initialization scripts for the Unified Medical AI Platform's Neo4j database. These scripts should be executed in order to properly set up the database schema, indexes, and seed data.

## Script Execution Order

Execute the scripts in the following order:

1. **001_create_constraints.cypher** - Creates unique constraints for all node types
2. **002_create_indexes.cypher** - Creates performance indexes for optimized queries
3. **003_create_vector_indexes.cypher** - Creates vector indexes for semantic search
4. **004_seed_doctors.cypher** - Creates the AI doctor specialties
5. **005_seed_test_data.cypher** - Creates sample data for testing (optional for production)
6. **006_create_functions.cypher** - Creates useful query templates and procedures

## Manual Execution

To execute these scripts manually using the Neo4j Browser or cypher-shell:

### Using Neo4j Browser:
1. Open Neo4j Browser (http://localhost:7474)
2. Copy and paste each script's content
3. Execute using the play button

### Using cypher-shell:
```bash
# Connect to your Neo4j instance
cypher-shell -u neo4j -p your-password

# Execute each script
:source /path/to/001_create_constraints.cypher
:source /path/to/002_create_indexes.cypher
# ... continue for all scripts
```

## Automated Execution

For automated execution during deployment, use the provided initialization script:

```bash
# Using the Docker setup
docker exec -i neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD < /init/001_create_constraints.cypher
docker exec -i neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD < /init/002_create_indexes.cypher
# ... continue for all scripts
```

Or use the Python initialization script:

```python
python initialize_neo4j.py --host localhost --port 7687 --username neo4j --password your-password
```

## Script Descriptions

### 001_create_constraints.cypher
- Creates unique constraints on node identifiers
- Ensures data integrity for primary keys
- Must be run before creating any nodes

### 002_create_indexes.cypher
- Creates standard indexes for query performance
- Includes composite indexes for common query patterns
- Optimizes search and filtering operations

### 003_create_vector_indexes.cypher
- Creates vector indexes for semantic similarity search
- Configured for 1536-dimensional embeddings (OpenAI standard)
- Uses cosine similarity for matching

### 004_seed_doctors.cypher
- Creates the AI doctor specialties
- Includes cardiologist, BP scanner, general consultant, emergency, and radiology doctors
- Configures each doctor's expertise and capabilities

### 005_seed_test_data.cypher
- Creates sample users, cases, analyses, and relationships
- Provides realistic test data for development
- Should be skipped in production environments

### 006_create_functions.cypher
- Provides query templates for common operations
- Includes dashboard queries, search functions, and analytics
- Can be customized based on application needs

## Important Notes

1. **Idempotency**: All scripts use `IF NOT EXISTS` clauses where possible to ensure they can be run multiple times safely.

2. **Vector Indexes**: The vector index creation syntax may vary depending on your Neo4j version. The provided syntax works with Neo4j 5.x+.

3. **Test Data**: The seed test data script (005) should only be run in development/testing environments, not in production.

4. **Performance**: After running these scripts, you may want to run `CALL db.stats.retrieve("GRAPH COUNTS")` to update database statistics.

5. **Backups**: Always backup your database before running initialization scripts in production.

## Troubleshooting

### Common Issues:

1. **Constraint already exists**: This is safe to ignore - the script is idempotent.

2. **Vector index syntax error**: Ensure you're using Neo4j 5.x or later with vector index support.

3. **Memory issues**: For large databases, you may need to increase Neo4j heap memory settings.

### Verification Queries:

Check constraints:
```cypher
SHOW CONSTRAINTS;
```

Check indexes:
```cypher
SHOW INDEXES;
```

Check node counts:
```cypher
MATCH (n) RETURN labels(n) as label, count(n) as count;
```

Check relationships:
```cypher
MATCH ()-[r]->() RETURN type(r) as type, count(r) as count;
```