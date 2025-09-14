"""
API 요청/응답 스키마 정의
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool = Field(description="요청 성공 여부")
    message: str = Field(description="응답 메시지")
    data: Optional[Dict[str, Any]] = Field(default=None, description="응답 데이터")


class ValidationRequest(BaseModel):
    """1단계: Validation 요청 (JSON 파일에서 데이터 로드)"""
    session_id: str = Field(description="세션 ID")
    window_days: Optional[int] = Field(default=5, description="윈도우 기간 (일)")
    base_date: Optional[str] = Field(default=None, description="기준 날짜")
    yield_period: Optional[int] = Field(default=6, description="수율 기준 기간 (개월)")


class ValidationResponse(BaseResponse):
    """1단계: Validation 응답"""
    data: Dict[str, Any] = Field(description="검증 결과 데이터")


class PreprocessingRequest(BaseModel):
    """2단계: 전처리 요청"""
    session_id: str = Field(description="세션 ID")
    window_days: Optional[int] = Field(default=5, description="윈도우 기간 (일)")


class PreprocessingResponse(BaseResponse):
    """2단계: 전처리 응답"""
    data: Dict[str, Any] = Field(description="전처리 결과 데이터")


class YieldPredictionRequest(BaseModel):
    """3단계: 수율 예측 요청"""
    session_id: str = Field(description="세션 ID")


class YieldPredictionResponse(BaseResponse):
    """3단계: 수율 예측 응답"""
    data: Dict[str, Any] = Field(description="수율 예측 결과 데이터")


class DAGCreationRequest(BaseModel):
    """4단계: DAG 생성 요청"""
    session_id: str = Field(description="세션 ID")


class DAGCreationResponse(BaseResponse):
    """4단계: DAG 생성 응답"""
    data: Dict[str, Any] = Field(description="DAG 생성 결과 데이터")


class SchedulingRequest(BaseModel):
    """5단계: 스케줄링 요청"""
    session_id: str = Field(description="세션 ID")
    window_days: Optional[int] = Field(default=5, description="윈도우 기간 (일)")


class SchedulingResponse(BaseResponse):
    """5단계: 스케줄링 응답"""
    data: Dict[str, Any] = Field(description="스케줄링 결과 데이터")


class ResultsRequest(BaseModel):
    """6단계: 결과 처리 요청"""
    session_id: str = Field(description="세션 ID")


class ResultsResponse(BaseResponse):
    """6단계: 결과 처리 응답"""
    data: Dict[str, Any] = Field(description="결과 처리 데이터")


class StatusRequest(BaseModel):
    """상태 조회 요청"""
    session_id: str = Field(description="세션 ID")


class StatusResponse(BaseResponse):
    """상태 조회 응답"""
    data: Dict[str, Any] = Field(description="세션 상태 데이터")


class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str = Field(description="서비스 상태")
    timestamp: datetime = Field(description="응답 시간")
    redis_connected: bool = Field(description="Redis 연결 상태")

