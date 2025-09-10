"""
API 서버 설정 파일
"""

import os
from typing import Optional

class APIConfig:
    """API 서버 설정 클래스"""
    
    # 서버 설정
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))
    RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("API_LOG_LEVEL", "info")
    
    # CORS 설정
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    
    # 외부 API 설정
    EXTERNAL_API_BASE_URL: Optional[str] = os.getenv("EXTERNAL_API_BASE_URL")
    EXTERNAL_API_KEY: Optional[str] = os.getenv("EXTERNAL_API_KEY")
    USE_MOCK_API: bool = os.getenv("USE_MOCK_API", "true").lower() == "true"
    
    # 데이터 저장소 설정
    DATA_STORAGE_TYPE: str = os.getenv("DATA_STORAGE_TYPE", "memory")  # memory, redis, database
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # 세션 설정
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1시간
    
    # 로깅 설정
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    @classmethod
    def get_cors_origins(cls) -> list:
        """CORS 허용 오리진 목록 반환"""
        return cls.CORS_ORIGINS + [
            origin.strip() 
            for origin in os.getenv("CORS_ORIGINS", "").split(",") 
            if origin.strip()
        ]
    
    @classmethod
    def get_external_api_config(cls) -> dict:
        """외부 API 설정 반환"""
        return {
            "base_url": cls.EXTERNAL_API_BASE_URL,
            "api_key": cls.EXTERNAL_API_KEY,
            "use_mock": cls.USE_MOCK_API
        }

# 환경별 설정
class DevelopmentConfig(APIConfig):
    """개발 환경 설정"""
    RELOAD = True
    LOG_LEVEL = "debug"
    USE_MOCK_API = True

class ProductionConfig(APIConfig):
    """운영 환경 설정"""
    RELOAD = False
    LOG_LEVEL = "info"
    USE_MOCK_API = False

class TestingConfig(APIConfig):
    """테스트 환경 설정"""
    RELOAD = False
    LOG_LEVEL = "debug"
    USE_MOCK_API = True

def get_config() -> APIConfig:
    """환경에 따른 설정 반환"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()
