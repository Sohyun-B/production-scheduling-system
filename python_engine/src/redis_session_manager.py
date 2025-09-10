"""
Redis 기반 세션 관리 시스템
각 단계별 결과를 Redis에 저장하고 관리
"""

import redis
import json
import pickle
import pandas as pd
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RedisSessionManager:
    """Redis 기반 세션 관리자"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", 
                 session_timeout: int = 3600):
        """
        Args:
            redis_url: Redis 연결 URL
            session_timeout: 세션 만료 시간 (초)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.session_timeout = session_timeout
        self.prefix = "scheduling_session:"
    
    def _get_key(self, session_id: str, stage: Optional[str] = None) -> str:
        """Redis 키 생성"""
        if stage:
            return f"{self.prefix}{session_id}:{stage}"
        return f"{self.prefix}{session_id}"
    
    def save_stage_data(self, session_id: str, stage: str, data: Dict[str, Any]) -> bool:
        """
        단계별 데이터 저장
        
        Args:
            session_id: 세션 ID
            stage: 단계명 (stage1, stage2, ...)
            data: 저장할 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # DataFrame 객체들을 직렬화 가능한 형태로 변환
            serialized_data = self._serialize_data(data)
            
            # Redis에 저장
            key = self._get_key(session_id, stage)
            self.redis_client.setex(
                key, 
                self.session_timeout, 
                pickle.dumps(serialized_data)
            )
            
            # 세션 메타데이터 업데이트
            self._update_session_metadata(session_id, stage)
            
            logger.info(f"세션 {session_id}의 {stage} 데이터 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"세션 {session_id}의 {stage} 데이터 저장 실패: {e}")
            return False
    
    def load_stage_data(self, session_id: str, stage: str) -> Dict[str, Any]:
        """
        단계별 데이터 로드
        
        Args:
            session_id: 세션 ID
            stage: 단계명
            
        Returns:
            Dict[str, Any]: 로드된 데이터
            
        Raises:
            KeyError: 세션이나 단계가 존재하지 않는 경우
        """
        try:
            key = self._get_key(session_id, stage)
            data = self.redis_client.get(key)
            
            if data is None:
                raise KeyError(f"Session {session_id} stage {stage} not found")
            
            # 역직렬화
            deserialized_data = pickle.loads(data)
            
            # DataFrame 객체들을 복원
            restored_data = self._deserialize_data(deserialized_data)
            
            logger.info(f"세션 {session_id}의 {stage} 데이터 로드 완료")
            return restored_data
            
        except Exception as e:
            logger.error(f"세션 {session_id}의 {stage} 데이터 로드 실패: {e}")
            raise
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        세션 상태 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Dict[str, Any]: 세션 상태 정보
        """
        try:
            # 세션 메타데이터 조회
            meta_key = self._get_key(session_id, "metadata")
            metadata = self.redis_client.get(meta_key)
            
            if metadata is None:
                raise KeyError(f"Session {session_id} not found")
            
            meta_data = json.loads(metadata)
            
            # 완료된 단계 목록
            completed_stages = []
            for stage in ["stage1", "stage2", "stage3", "stage4", "stage5", "stage6"]:
                if self.redis_client.exists(self._get_key(session_id, stage)):
                    completed_stages.append(stage)
            
            return {
                "session_id": session_id,
                "completed_stages": completed_stages,
                "total_stages": 6,
                "created_at": meta_data.get("created_at"),
                "last_updated": meta_data.get("last_updated")
            }
            
        except Exception as e:
            logger.error(f"세션 {session_id} 상태 조회 실패: {e}")
            raise
    
    def clear_session(self, session_id: str) -> bool:
        """
        세션 데이터 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 세션 관련 모든 키 삭제
            pattern = f"{self.prefix}{session_id}*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"세션 {session_id} 삭제 완료 ({len(keys)}개 키)")
                return True
            else:
                logger.warning(f"세션 {session_id}가 존재하지 않음")
                return False
                
        except Exception as e:
            logger.error(f"세션 {session_id} 삭제 실패: {e}")
            return False
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 직렬화 (DataFrame 등을 처리)"""
        serialized = {}
        
        for key, value in data.items():
            if isinstance(value, pd.DataFrame):
                # DataFrame을 JSON으로 변환
                serialized[key] = {
                    "_type": "dataframe",
                    "data": value.to_json(orient='records', date_format='iso'),
                    "index": value.index.tolist(),
                    "columns": value.columns.tolist()
                }
            elif isinstance(value, dict) and any(isinstance(v, pd.DataFrame) for v in value.values()):
                # 딕셔너리 내 DataFrame 처리
                serialized[key] = self._serialize_data(value)
            else:
                serialized[key] = value
        
        return serialized
    
    def _deserialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 역직렬화 (DataFrame 복원)"""
        deserialized = {}
        
        for key, value in data.items():
            if isinstance(value, dict) and value.get("_type") == "dataframe":
                # DataFrame 복원
                df_data = json.loads(value["data"])
                df = pd.DataFrame(df_data)
                df.index = value["index"]
                df.columns = value["columns"]
                deserialized[key] = df
            elif isinstance(value, dict):
                # 중첩된 딕셔너리 처리
                deserialized[key] = self._deserialize_data(value)
            else:
                deserialized[key] = value
        
        return deserialized
    
    def _update_session_metadata(self, session_id: str, stage: str):
        """세션 메타데이터 업데이트"""
        try:
            meta_key = self._get_key(session_id, "metadata")
            
            # 기존 메타데이터 로드
            existing_meta = self.redis_client.get(meta_key)
            if existing_meta:
                metadata = json.loads(existing_meta)
            else:
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "stages": []
                }
            
            # 단계 추가
            if stage not in metadata["stages"]:
                metadata["stages"].append(stage)
            
            metadata["last_updated"] = datetime.now().isoformat()
            
            # 메타데이터 저장
            self.redis_client.setex(
                meta_key,
                self.session_timeout,
                json.dumps(metadata)
            )
            
        except Exception as e:
            logger.error(f"세션 {session_id} 메타데이터 업데이트 실패: {e}")
    
    def health_check(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            return False

# 전역 세션 매니저 인스턴스
session_manager = None

def get_session_manager() -> RedisSessionManager:
    """세션 매니저 인스턴스 반환"""
    global session_manager
    if session_manager is None:
        session_manager = RedisSessionManager()
    return session_manager

def init_session_manager(redis_url: str = "redis://localhost:6379/0", 
                        session_timeout: int = 3600):
    """세션 매니저 초기화"""
    global session_manager
    session_manager = RedisSessionManager(redis_url, session_timeout)
    return session_manager
