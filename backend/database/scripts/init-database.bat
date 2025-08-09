@echo off
echo Waiting for Neo4j to be ready...

:wait_loop
docker exec medical-ai-neo4j neo4j status | findstr "running" >nul
if errorlevel 1 (
    echo Neo4j is not ready yet. Waiting...
    timeout /t 5 /nobreak >nul
    goto wait_loop
)

echo Neo4j is ready! Initializing database...

REM Change to backend directory
cd ..\..

REM Run the database initialization script
echo Running database initialization...
python database\neo4j\init\initialize_neo4j.py

echo Database initialization complete!