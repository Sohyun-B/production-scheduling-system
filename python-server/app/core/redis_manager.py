"""
Redis 상태 관리 시스템
각 단계별 결과를 Redis에 저장하고 조회하는 기능 제공
"""
import json
import pickle
from typing import Any, Optional, Dict
import redis
from loguru import logger
from .config import settings


class RedisManager:
    """Redis 상태 관리 클래스"""
    
    def __init__(self):
        """Redis 연결 초기화"""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=False  # 바이너리 데이터 저장을 위해
        )
        logger.info(f"Redis 연결 완료: {settings.redis_host}:{settings.redis_port}")
    
    def _get_key(self, session_id: str, stage: str) -> str:
        """Redis 키 생성"""
        return f"scheduling:{session_id}:{stage}"
    
    def save_stage_data(self, session_id: str, stage: str, data: Any) -> bool:
        """
        단계별 데이터를 Redis에 저장
        
        Args:
            session_id: 세션 ID
            stage: 단계명 (validation, preprocessing, yield_prediction, dag_creation, scheduling, results)
            data: 저장할 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            key = self._get_key(session_id, stage)
            
            # 데이터 타입에 따라 다른 직렬화 방법 사용
            if isinstance(data, (dict, list, str, int, float, bool)):
                # JSON 직렬화 가능한 데이터
                serialized_data = json.dumps(data, ensure_ascii=False, default=str)
                self.redis_client.set(key, serialized_data)
            else:
                # 복잡한 객체는 pickle 사용
                serialized_data = pickle.dumps(data)
                self.redis_client.set(key, serialized_data)
            
            # TTL 설정 (24시간)
            self.redis_client.expire(key, 86400)
            
            logger.info(f"데이터 저장 완료: {key}")
            return True
            
        except Exception as e:
            logger.error(f"데이터 저장 실패: {e}")
            return False
    
    def get_stage_data(self, session_id: str, stage: str) -> Optional[Any]:
        """
        단계별 데이터를 Redis에서 조회
        
        Args:
            session_id: 세션 ID
            stage: 단계명
            
        Returns:
            Any: 조회된 데이터 또는 None
        """
        try:
            key = self._get_key(session_id, stage)
            data = self.redis_client.get(key)
            
            if data is None:
                logger.warning(f"데이터 없음: {key}")
                return None
            
            # JSON으로 파싱 시도
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                # JSON 파싱 실패시 pickle로 시도
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"데이터 조회 실패: {e}")
            return None
    
    def delete_stage_data(self, session_id: str, stage: str) -> bool:
        """
        단계별 데이터 삭제
        
        Args:
            session_id: 세션 ID
            stage: 단계명
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            key = self._get_key(session_id, stage)
            result = self.redis_client.delete(key)
            logger.info(f"데이터 삭제 완료: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"데이터 삭제 실패: {e}")
            return False
    
    def get_all_stages(self, session_id: str) -> Dict[str, Any]:
        """
        세션의 모든 단계 데이터 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Dict[str, Any]: 단계별 데이터 딕셔너리
        """
        stages = ["validation", "preprocessing", "yield_prediction", 
                 "dag_creation", "scheduling", "results"]
        
        result = {}
        for stage in stages:
            data = self.get_stage_data(session_id, stage)
            if data is not None:
                result[stage] = data
        
        return result
    
    def clear_session(self, session_id: str) -> bool:
        """
        세션의 모든 데이터 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            pattern = f"scheduling:{session_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"세션 데이터 삭제 완료: {session_id} ({len(keys)}개 키)")
            
            return True
        except Exception as e:
            logger.error(f"세션 데이터 삭제 실패: {e}")
            return False
    
    def health_check(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            return False


# 전역 Redis 매니저 인스턴스
redis_manager = RedisManager()

