@echo off
echo ==================================================
echo Medical AI Docker Services Startup Script
echo ==================================================
echo.

REM Check if Docker Desktop is running
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Set the working directory to the database folder
cd /d "%~dp0\.."

echo Starting Neo4j and Redis services...
docker-compose up -d

echo.
echo Waiting for services to be healthy...
:wait_services
timeout /t 5 /nobreak >nul
docker exec medical-ai-neo4j neo4j status 2>nul | findstr "running" >nul
if errorlevel 1 (
    echo Still waiting for Neo4j...
    goto wait_services
)

REM Check if Redis is healthy
docker exec medical-ai-redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo Redis is not responding!
    pause
    exit /b 1
)

echo.
echo Services are running! Checking database initialization...

REM Navigate to backend directory for Python path
cd ..

REM Check if database is initialized
python -c "from database.neo4j.client import Neo4jClient; import asyncio; async def check(): client = Neo4jClient(); await client.connect(); result = await client.execute_query('MATCH (d:Doctor) RETURN count(d) as count'); await client.close(); return result[0]['count'] if result else 0; count = asyncio.run(check()); print(f'Found {count} doctors in database')" 2>nul

if errorlevel 1 (
    echo Database not initialized. Running initialization...
    cd database
    python neo4j\init\initialize_neo4j.py
    if errorlevel 1 (
        echo ERROR: Database initialization failed!
        pause
        exit /b 1
    )
    cd ..
) else (
    echo Database already initialized!
)

echo.
echo ==================================================
echo Services Status:
echo ==================================================
docker-compose -f database\docker-compose.yml ps

echo.
echo ==================================================
echo Service URLs:
echo ==================================================
echo Neo4j Browser: http://localhost:7474
echo   Username: neo4j
echo   Password: medical123
echo Neo4j Bolt:   bolt://localhost:7687
echo Redis:        redis://localhost:6379
echo ==================================================
echo.
echo Docker services are ready!
echo.
echo To start the backend server, run: python run.py
echo To stop services, run: docker-compose -f database\docker-compose.yml down
echo.
pause