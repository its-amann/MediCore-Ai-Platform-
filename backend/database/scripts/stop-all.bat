@echo off
echo Stopping Unified Medical AI Platform...
echo.

echo Stopping Docker services...
docker-compose down

echo.
echo All services stopped!
pause