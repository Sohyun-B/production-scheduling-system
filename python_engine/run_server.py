"""
FastAPI 서버 실행 스크립트
"""

import uvicorn
import os
import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """서버 실행"""
    # 환경 변수 설정
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print(f"🚀 Production Scheduling API Server 시작")
    print(f"📍 Host: {host}")
    print(f"📍 Port: {port}")
    print(f"📍 Reload: {reload}")
    print(f"📍 Log Level: {log_level}")
    print(f"🌐 API 문서: http://{host}:{port}/docs")
    print(f"🌐 ReDoc: http://{host}:{port}/redoc")
    
    # 서버 실행
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
