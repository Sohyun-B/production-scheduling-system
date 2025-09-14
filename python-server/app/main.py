"""
FastAPI 메인 서버
Production Scheduling System API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.redis_manager import redis_manager
from api import validation, validation_with_data, preprocessing, yield_prediction, dag_creation, scheduling, status

# FastAPI 앱 생성
app = FastAPI(
    title="Production Scheduling System API",
    description="제조업 생산 스케줄링 시스템 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(validation.router)
app.include_router(validation_with_data.router)
app.include_router(preprocessing.router)
app.include_router(yield_prediction.router)
app.include_router(dag_creation.router)
app.include_router(scheduling.router)
app.include_router(status.router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("Production Scheduling System API 서버 시작")
    
    # Redis 연결 확인
    if redis_manager.health_check():
        logger.info("Redis 연결 성공")
    else:
        logger.warning("Redis 연결 실패 - 일부 기능이 제한될 수 있습니다")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("Production Scheduling System API 서버 종료")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Production Scheduling System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/status/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리"""
    logger.error(f"전역 예외 발생: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "서버 내부 오류가 발생했습니다.",
            "error": str(exc) if settings.api_debug else "Internal Server Error"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # 로깅 설정
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 서버 실행
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower()
    )

