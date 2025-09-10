"""
API 테스트 클라이언트
각 단계별 API 엔드포인트를 테스트하는 스크립트
"""

import httpx
import asyncio
import json
from typing import Dict, Any

class APITestClient:
    """API 테스트 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
    
    async def test_health_check(self):
        """헬스 체크 테스트"""
        print("🔍 헬스 체크 테스트...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            print(f"✅ 상태: {response.status_code}")
            print(f"📄 응답: {response.json()}")
            return response.status_code == 200
    
    async def test_stage1_external_data(self):
        """1단계: 외부 API 데이터 로딩 테스트"""
        print("\n🔍 1단계: 외부 API 데이터 로딩 테스트...")
        
        # Mock API 사용
        request_data = {
            "api_config": {
                "base_url": "http://mock-api.com",
                "api_key": "test-key",
                "use_mock": True
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage1/load-external-data",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                print(f"✅ 세션 ID: {self.session_id}")
                print(f"📊 데이터 요약: {data['data_summary']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_stage2_preprocessing(self):
        """2단계: 전처리 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다. 1단계를 먼저 실행하세요.")
            return False
        
        print(f"\n🔍 2단계: 전처리 테스트 (세션: {self.session_id})...")
        
        request_data = {"session_id": self.session_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage2/preprocessing",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 처리된 작업 수: {data['processed_jobs']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_stage3_yield_prediction(self):
        """3단계: 수율 예측 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다. 1단계를 먼저 실행하세요.")
            return False
        
        print(f"\n🔍 3단계: 수율 예측 테스트 (세션: {self.session_id})...")
        
        request_data = {"session_id": self.session_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage3/yield-prediction",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 수율 예측 완료: {data['yield_prediction_completed']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_stage4_dag_creation(self):
        """4단계: DAG 생성 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다. 1단계를 먼저 실행하세요.")
            return False
        
        print(f"\n🔍 4단계: DAG 생성 테스트 (세션: {self.session_id})...")
        
        request_data = {"session_id": self.session_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage4/dag-creation",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ DAG 노드 수: {data['dag_nodes']}")
                print(f"✅ 기계 수: {data['machines']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_stage5_scheduling(self):
        """5단계: 스케줄링 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다. 1단계를 먼저 실행하세요.")
            return False
        
        print(f"\n🔍 5단계: 스케줄링 테스트 (세션: {self.session_id})...")
        
        request_data = {
            "session_id": self.session_id,
            "window_days": 5
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage5/scheduling",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Makespan: {data['makespan_slots']} 슬롯")
                print(f"✅ 소요 시간: {data['makespan_hours']:.2f} 시간")
                print(f"✅ 총 일수: {data['total_days']:.2f} 일")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_stage6_results(self):
        """6단계: 결과 후처리 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다. 1단계를 먼저 실행하세요.")
            return False
        
        print(f"\n🔍 6단계: 결과 후처리 테스트 (세션: {self.session_id})...")
        
        request_data = {"session_id": self.session_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/stage6/results",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 지각 일수: {data['late_days_sum']}")
                print(f"✅ 지각 제품 수: {data['late_products_count']}")
                print(f"✅ 지각 PO 번호: {data['late_po_numbers']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_session_status(self):
        """세션 상태 조회 테스트"""
        if not self.session_id:
            print("❌ 세션 ID가 없습니다.")
            return False
        
        print(f"\n🔍 세션 상태 조회 테스트 (세션: {self.session_id})...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/session/{self.session_id}/status"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 완료된 단계: {data['completed_stages']}")
                print(f"✅ 총 단계 수: {data['total_stages']}")
                return True
            else:
                print(f"❌ 실패: {response.status_code} - {response.text}")
                return False
    
    async def test_full_pipeline(self):
        """전체 파이프라인 테스트"""
        print("🚀 전체 파이프라인 테스트 시작...")
        
        tests = [
            self.test_health_check,
            self.test_stage1_external_data,
            self.test_stage2_preprocessing,
            self.test_stage3_yield_prediction,
            self.test_stage4_dag_creation,
            self.test_stage5_scheduling,
            self.test_stage6_results,
            self.test_session_status
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append(result)
            except Exception as e:
                print(f"❌ 테스트 실패: {e}")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        print(f"\n📊 테스트 결과: {success_count}/{total_count} 성공")
        
        if success_count == total_count:
            print("🎉 모든 테스트 통과!")
        else:
            print("⚠️ 일부 테스트 실패")
        
        return success_count == total_count

async def main():
    """메인 테스트 함수"""
    client = APITestClient()
    
    print("=" * 50)
    print("🧪 Production Scheduling API 테스트")
    print("=" * 50)
    
    # 서버가 실행 중인지 확인
    try:
        await client.test_health_check()
    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        print("💡 서버 실행: python run_server.py")
        return
    
    # 전체 파이프라인 테스트
    await client.test_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
