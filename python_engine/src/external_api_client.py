"""
외부 API 클라이언트 모듈
외부 시스템에서 데이터를 가져오는 기능 제공
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class ExternalAPIClient:
    """외부 API 클라이언트"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Args:
            base_url: 외부 API 기본 URL
            api_key: API 인증 키 (선택사항)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        외부 API에서 데이터 가져오기
        
        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            
        Returns:
            API 응답 데이터
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"API 요청 실패: {e}")
                raise Exception(f"외부 API 요청 실패: {e}")
    
    async def fetch_all_scheduling_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        스케줄링에 필요한 모든 데이터를 외부 API에서 가져오기
        
        Returns:
            각 데이터 타입별 데이터 리스트
        """
        # 병렬로 여러 API 호출
        tasks = [
            self.fetch_data("/api/linespeed"),
            self.fetch_data("/api/operation-sequence"),
            self.fetch_data("/api/machine-master-info"),
            self.fetch_data("/api/yield-data"),
            self.fetch_data("/api/gitem-operation"),
            self.fetch_data("/api/operation-types"),
            self.fetch_data("/api/operation-delay"),
            self.fetch_data("/api/width-change"),
            self.fetch_data("/api/machine-rest"),
            self.fetch_data("/api/machine-allocate"),
            self.fetch_data("/api/machine-limit"),
            self.fetch_data("/api/order-data")
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 검증 및 변환
            data = {}
            endpoints = [
                "linespeed", "operation_sequence", "machine_master_info",
                "yield_data", "gitem_operation", "operation_types",
                "operation_delay", "width_change", "machine_rest",
                "machine_allocate", "machine_limit", "order_data"
            ]
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"{endpoints[i]} 데이터 가져오기 실패: {result}")
                    raise result
                
                # API 응답이 리스트가 아닌 경우 처리
                if isinstance(result, dict) and 'data' in result:
                    data[endpoints[i]] = result['data']
                elif isinstance(result, list):
                    data[endpoints[i]] = result
                else:
                    logger.warning(f"{endpoints[i]} 데이터 형식이 예상과 다름: {type(result)}")
                    data[endpoints[i]] = []
            
            return data
            
        except Exception as e:
            logger.error(f"외부 API 데이터 가져오기 실패: {e}")
            raise

class MockExternalAPIClient:
    """테스트용 Mock API 클라이언트"""
    
    def __init__(self, mock_data_path: str = "data/json"):
        """
        Args:
            mock_data_path: Mock 데이터가 있는 경로
        """
        self.mock_data_path = mock_data_path
    
    async def fetch_all_scheduling_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        로컬 JSON 파일에서 Mock 데이터 가져오기
        """
        import json
        import os
        import pandas as pd
        
        data = {}
        
        # JSON 파일들 매핑
        json_files = {
            "linespeed": "md_step2_linespeed.json",
            "operation_sequence": "md_step3_operation_sequence.json",
            "machine_master_info": "md_step4_machine_master_info.json",
            "yield_data": "md_step3_yield_data.json",
            "gitem_operation": "md_step3_gitem_operation.json",
            "operation_types": "md_step2_operation_types.json",
            "operation_delay": "md_step5 operation_delay.json",
            "width_change": "md_step5_width_change.json",
            "machine_rest": "user_step5_machine_rest.json",
            "machine_allocate": "user_step2_machine_allocate.json",
            "machine_limit": "user_step2_machine_limit.json",
            "order_data": "md_step2_order_data.json"
        }
        
        for key, filename in json_files.items():
            file_path = os.path.join(self.mock_data_path, filename)
            try:
                if os.path.exists(file_path):
                    # JSON 파일을 DataFrame으로 읽고 다시 dict로 변환
                    df = pd.read_json(file_path)
                    data[key] = df.to_dict('records')
                else:
                    logger.warning(f"Mock 데이터 파일을 찾을 수 없음: {file_path}")
                    data[key] = []
            except Exception as e:
                logger.error(f"Mock 데이터 로딩 실패 ({filename}): {e}")
                data[key] = []
        
        return data

# =============================================================================
# API 서버에 통합된 외부 API 호출 엔드포인트
# =============================================================================

async def load_data_from_external_api(api_client: ExternalAPIClient) -> Dict[str, List[Dict[str, Any]]]:
    """
    외부 API에서 데이터를 가져와서 스케줄링 시스템에 전달할 수 있는 형태로 변환
    
    Args:
        api_client: 외부 API 클라이언트 인스턴스
        
    Returns:
        스케줄링 시스템에 필요한 데이터
    """
    try:
        # 외부 API에서 데이터 가져오기
        raw_data = await api_client.fetch_all_scheduling_data()
        
        # 데이터 검증 및 변환
        validated_data = {}
        required_fields = [
            "linespeed", "operation_sequence", "machine_master_info",
            "yield_data", "gitem_operation", "operation_types",
            "operation_delay", "width_change", "machine_rest",
            "machine_allocate", "machine_limit", "order_data"
        ]
        
        for field in required_fields:
            if field in raw_data and isinstance(raw_data[field], list):
                validated_data[field] = raw_data[field]
            else:
                logger.warning(f"필수 필드 {field}가 없거나 형식이 잘못됨")
                validated_data[field] = []
        
        return validated_data
        
    except Exception as e:
        logger.error(f"외부 API 데이터 로딩 실패: {e}")
        raise

# =============================================================================
# 사용 예시 및 테스트 함수
# =============================================================================

async def test_external_api():
    """외부 API 테스트 함수"""
    
    # 실제 외부 API 사용
    # api_client = ExternalAPIClient(
    #     base_url="https://your-external-api.com",
    #     api_key="your-api-key"
    # )
    
    # Mock API 사용 (테스트용)
    api_client = MockExternalAPIClient()
    
    try:
        data = await api_client.fetch_all_scheduling_data()
        print(f"데이터 로딩 성공: {len(data)}개 데이터 타입")
        for key, value in data.items():
            print(f"  {key}: {len(value)}개 레코드")
    except Exception as e:
        print(f"데이터 로딩 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_external_api())
