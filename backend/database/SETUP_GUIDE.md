# Unified Medical AI - Setup Guide

## Prerequisites
- Docker Desktop installed and running
- Python 3.8 or higher
- Node.js 18 or higher (for frontend)
- Git

## Setup Instructions

### 1. Clone the repository (if not already done)
```bash
git clone <repository-url>
cd Medical\ Agent
```

### 2. Start the Database Services
```bash
# Start Neo4j and Redis using Docker Compose
docker-compose up -d

# Wait for services to be healthy (about 40 seconds for Neo4j)
docker-compose ps
```

### 3. Set up Backend Environment
```bash
cd unified-medical-ai/backend

# Copy environment example file
cp .env.example .env

# Edit .env file and add your API keys:
# - GROQ_API_KEY (required for AI functionality)
# - ELEVENLABS_API_KEY (optional for text-to-speech)
# - Update JWT_SECRET_KEY for production

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Initialize the Database
```bash
# From the root directory, run:
# On Windows:
init-database.bat

# On Linux/Mac:
chmod +x init-database.sh
./init-database.sh

# Or manually from backend directory:
cd unified-medical-ai/backend
python database/neo4j/init/initialize_neo4j.py
```

### 5. Start the Backend Server
```bash
cd unified-medical-ai/backend
python run.py

# The backend will start on http://localhost:8000
# API documentation available at http://localhost:8000/docs
```

### 6. Start the Frontend (if needed)
```bash
cd unified-medical-ai/frontend
npm install
npm run dev

# Frontend will be available at http://localhost:3000
```

## Services Overview

### Neo4j Database
- Web Interface: http://localhost:7474
- Bolt Connection: bolt://localhost:7687
- Default Credentials: neo4j / medical123

### Redis (Optional)
- Connection: redis://localhost:6379
- Used for caching

### Backend API
- Base URL: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Troubleshooting

### Neo4j Connection Issues
1. Check if Neo4j is running:
   ```bash
   docker-compose ps
   docker logs medical-ai-neo4j
   ```

2. Verify Neo4j is accessible:
   - Open http://localhost:7474 in browser
   - Login with neo4j / medical123

### Backend Connection Issues
1. Ensure .env file exists with correct database credentials
2. Check if Neo4j is initialized:
   ```bash
   docker exec medical-ai-neo4j cypher-shell -u neo4j -p medical123 "MATCH (n) RETURN count(n)"
   ```

### Common Commands
```bash
# Stop all services
docker-compose down

# View logs
docker-compose logs -f neo4j
docker-compose logs -f redis

# Reset database (warning: deletes all data)
docker-compose down -v
docker-compose up -d
```

## MCP Server Integration
The backend includes MCP (Medical Context Protocol) servers for:
- Patient history retrieval
- PubMed medical literature search

These are integrated into the backend and don't require separate setup.