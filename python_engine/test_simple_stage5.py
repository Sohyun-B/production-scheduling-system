#!/usr/bin/env python3
"""
간단한 5단계 스케줄링 테스트
"""

import httpx
import asyncio

async def test_simple_stage5():
    """간단한 5단계 스케줄링 테스트"""
    print("🚀 간단한 5단계 스케줄링 테스트 시작")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. 헬스 체크
            print("🔍 헬스 체크...")
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ 서버 정상")
            else:
                print("❌ 서버 오류")
                return
            
            # 2. 간단한 데이터로 1단계
            print("🔍 1단계 데이터 로딩...")
            simple_data = {
                "linespeed": [{"GITEM": "G001", "공정명": "C2010", "C2010": 100, "C2250": 0, "C2260": 0, "C2270": 0, "O2310": 0, "O2340": 0}],
                "operation_sequence": [{"공정순서": 1, "공정명": "C2010", "공정분류": "CUT", "배합코드": "BH001"}],
                "machine_master_info": [{"기계인덱스": 1, "기계코드": "C2010", "기계이름": "커팅기1"}],
                "yield_data": [{"GITEM": "G001", "공정명": "C2010", "수율": 0.95}],
                "gitem_operation": [{"GITEM": "G001", "공정명": "C2010", "공정분류": "CUT", "배합코드": "BH001"}],
                "operation_types": [{"공정명": "C2010", "공정분류": "CUT", "설명": "커팅공정1"}],
                "operation_delay": [{"선행공정분류": "CUT", "후행공정분류": "CUT", "타입교체시간": 30, "long_to_short": 10, "short_to_long": 20}],
                "width_change": [{"기계인덱스": 1, "이전폭": 1000, "이후폭": 1200, "변경시간": 15, "long_to_short": 10, "short_to_long": 20}],
                "machine_rest": [{"기계인덱스": 1, "시작시간": "2024-01-01 00:00:00", "종료시간": "2024-01-01 08:00:00", "사유": "야간휴무"}],
                "machine_allocate": [{"기계인덱스": 1, "공정명": "C2010", "할당유형": "EXCLUSIVE"}],
                "machine_limit": [{"기계인덱스": 1, "공정명": "C2010", "시작시간": "2024-01-01 08:00:00", "종료시간": "2024-01-01 18:00:00", "제한사유": "작업시간"}],
                "order_data": [{"P/O NO": "PO001", "GITEM": "G001", "GITEM명": "제품1", "너비": 1000, "길이": 2000, "의뢰량": 100, "원단길이": 914, "납기일": "2024-01-15"}]
            }
            
            response = await client.post("http://localhost:8000/api/v1/stage1/load-data", json=simple_data)
            if response.status_code == 200:
                session_id = response.json()["session_id"]
                print(f"✅ 1단계 성공: {session_id}")
            else:
                print(f"❌ 1단계 실패: {response.text}")
                return
            
            # 3. 2-4단계 빠르게 실행
            stages = [
                ("stage2", "preprocessing"),
                ("stage3", "yield-prediction"), 
                ("stage4", "dag-creation")
            ]
            
            for stage, endpoint in stages:
                print(f"🔍 {stage} 실행...")
                response = await client.post(f"http://localhost:8000/api/v1/{stage}/{endpoint}", json={"session_id": session_id})
                if response.status_code == 200:
                    print(f"✅ {stage} 성공")
                else:
                    print(f"❌ {stage} 실패: {response.text}")
                    return
            
            # 4. 5단계 스케줄링 (비동기)
            print("🔍 5단계 스케줄링 시작...")
            response = await client.post("http://localhost:8000/api/v1/stage5/scheduling", json={"session_id": session_id, "window_days": 1})
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 5단계 시작: {result['message']}")
            else:
                print(f"❌ 5단계 실패: {response.text}")
                return
            
            # 5. 상태 확인
            print("🔍 상태 확인...")
            for i in range(5):
                await asyncio.sleep(2)
                response = await client.get(f"http://localhost:8000/api/v1/stage5/status/{session_id}")
                if response.status_code == 200:
                    status = response.json()
                    print(f"📊 상태: {status['status']} - {status['message']}")
                    if status['status'] == 'completed':
                        print("✅ 스케줄링 완료!")
                        break
            
            print("🏁 테스트 완료")
            
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_stage5())
