@echo off
echo Starting database services only...
echo.

REM Check if Docker Desktop is running
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting Neo4j and Redis with Docker Compose...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
docker-compose ps

echo.
echo ========================================
echo Database services are running:
echo - Neo4j UI: http://localhost:7474
echo - Neo4j Bolt: bolt://localhost:7687
echo - Redis: redis://localhost:6379
echo ========================================
echo.
echo To stop the databases, run: stop-all.bat
pause