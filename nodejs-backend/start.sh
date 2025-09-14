#!/bin/bash

echo "Production Scheduling Backend Server Starting..."
echo

# 환경 변수 설정
export NODE_ENV=development
export PORT=3000
export HOST=localhost
export PYTHON_API_BASE_URL=http://localhost:8000
export PYTHON_API_TIMEOUT=300000
export LOG_LEVEL=info
export CORS_ORIGIN=http://localhost:3000

# 로그 디렉토리 생성
mkdir -p logs

# 서버 시작
echo "Starting server on http://$HOST:$PORT"
echo "Python API: $PYTHON_API_BASE_URL"
echo

node src/server.js


