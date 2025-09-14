"""
FastAPI 서버 설정 관리
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # FastAPI 설정
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    
    # Python Engine 경로
    python_engine_path: str = "../python_engine"
    
    # 로깅 설정
    log_level: str = "INFO"
    
    # 스케줄링 설정
    default_window_days: int = 5
    base_year: int = 2025
    base_month: int = 1
    base_day: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()

