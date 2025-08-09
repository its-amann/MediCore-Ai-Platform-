# Database Directory - Unified Medical AI

This directory contains all database-related files for the Unified Medical AI backend, including Docker configurations, initialization scripts, and MCP server integration.

## Directory Structure

```
database/
├── docker-compose.yml      # Docker Compose configuration for Neo4j and Redis
├── SETUP_GUIDE.md         # Detailed setup instructions
├── scripts/               # All database management scripts
│   ├── start-docker-services.bat  # Main startup script
│   ├── start-all.bat      # Start databases + backend
│   ├── start-databases.bat # Start only databases
│   ├── stop-all.bat       # Stop all services
│   ├── init-database.bat  # Initialize database (Windows)
│   ├── init-database.sh   # Initialize database (Linux/Mac)
│   └── test-connection.py # Test database and MCP connectivity
├── neo4j/                 # Neo4j specific files
│   ├── init/             # Database initialization scripts
│   │   ├── *.cypher      # Cypher scripts for schema and seed data
│   │   └── initialize_neo4j.py  # Python initialization script
│   ├── conf/             # Neo4j configuration files
│   ├── data/             # Neo4j data directory
│   └── logs/             # Neo4j logs directory
└── docker-data/          # Docker volumes for data and logs
    ├── neo4j/
    │   ├── data/         # Neo4j data persistence
    │   └── logs/         # Neo4j logs
    └── redis/
        ├── data/         # Redis data persistence
        └── logs/         # Redis logs
```

## Quick Start

### 1. Start Database Services

From the scripts directory (`backend/database/scripts/`), run:

```bash
# Recommended - Start Docker services with automatic initialization
start-docker-services.bat

# Alternative - Start only databases
start-databases.bat
```

### 2. Test Connection

```bash
# Test database and MCP server connectivity
python scripts/test-connection.py
```

### 3. Stop Services

```bash
# From database directory
docker-compose down

# Or use the script
scripts/stop-all.bat
```

## Service URLs

- **Neo4j Browser**: http://localhost:7474
  - Username: `neo4j`
  - Password: `medical123`
- **Neo4j Bolt**: bolt://localhost:7687
- **Redis**: redis://localhost:6379

## MCP Server Integration

The MCP (Model Context Protocol) server is integrated into the backend application and provides:
- Medical history access for AI doctors
- PubMed literature search integration
- Secure user data isolation
- Audit logging for compliance

The MCP server automatically connects to the Dockerized Neo4j database using the same connection settings as the main application.

## Important Notes

1. **Docker Desktop** must be running before starting services
2. **First-time setup** is handled automatically by `start-docker-services.bat`
3. **Data persistence**: All data and logs are stored in `docker-data/` folder
4. **Clean reset**: To completely reset, delete the `docker-data/` folder and restart
5. **MCP Server**: Runs as part of the backend application, not as a separate service

## Troubleshooting

- **Neo4j not starting**: Check Docker Desktop is running and port 7687 is not in use
- **Redis errors**: Redis is optional; the app will work without it
- **Connection issues**: Run `python scripts/test-connection.py` to diagnose
- **Initialization failed**: Check the logs in `docker-data/neo4j/logs/`

See `SETUP_GUIDE.md` for detailed troubleshooting steps.