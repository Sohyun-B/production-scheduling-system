@echo off
echo Production Scheduling Backend Server Starting...
echo.

REM 환경 변수 설정
set NODE_ENV=development
set PORT=3000
set HOST=localhost
set PYTHON_API_BASE_URL=http://localhost:8000
set PYTHON_API_TIMEOUT=300000
set LOG_LEVEL=info
set CORS_ORIGIN=http://localhost:3000

REM 로그 디렉토리 생성
if not exist logs mkdir logs

REM 서버 시작
echo Starting server on http://%HOST%:%PORT%
echo Python API: %PYTHON_API_BASE_URL%
echo.

node src/server.js

pause


