@echo off
echo Starting Unified Medical AI Platform...
echo.

REM Check if Docker Desktop is running
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/4] Starting database services with Docker Compose...
docker-compose up -d

echo.
echo [2/4] Waiting for Neo4j to be ready (this may take up to 60 seconds)...
:wait_neo4j
timeout /t 5 /nobreak >nul
docker exec medical-ai-neo4j neo4j status 2>nul | findstr "running" >nul
if errorlevel 1 (
    echo Still waiting for Neo4j...
    goto wait_neo4j
)

echo.
echo [3/4] Neo4j is ready! Checking database initialization...
cd ..\..
python -c "from database.neo4j.client import Neo4jClient; client = Neo4jClient(); result = client.execute_query('MATCH (d:Doctor) RETURN count(d) as count')[0]; print(f'Found {result[\"count\"]} doctors in database')" 2>nul
if errorlevel 1 (
    echo Database not initialized. Running initialization...
    python database\neo4j\init\initialize_neo4j.py
) else (
    echo Database already initialized!
)

echo.
echo [4/4] Starting backend server...
echo.
echo ========================================
echo Services are starting:
echo - Neo4j UI: http://localhost:7474
echo - Backend API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the backend server
echo.

REM Start the backend server
python run.py