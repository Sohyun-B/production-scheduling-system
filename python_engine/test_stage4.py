#!/usr/bin/env python3
"""
4단계 DAG 생성 테스트 스크립트
"""

import httpx
import asyncio
import json

async def test_stage4():
    """4단계 DAG 생성 테스트"""
    print("🚀 4단계 DAG 생성 테스트 시작")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. 헬스 체크
            print("🔍 1. 헬스 체크 테스트...")
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ 헬스 체크 성공:", response.json())
            else:
                print("❌ 헬스 체크 실패:", response.status_code)
                return
            
            # 2. 1단계 데이터 로딩
            print("\n🔍 2. 1단계 데이터 로딩 테스트...")
            sample_data = {
                "linespeed": [
                    {"GITEM": "G001", "공정명": "C2010", "C2010": 100, "C2250": 0, "C2260": 0, "C2270": 0, "O2310": 0, "O2340": 0},
                    {"GITEM": "G002", "공정명": "C2250", "C2010": 0, "C2250": 120, "C2260": 0, "C2270": 0, "O2310": 0, "O2340": 0}
                ],
                "operation_sequence": [
                    {"공정순서": 1, "공정명": "C2010", "공정분류": "CUT", "배합코드": "BH001"},
                    {"공정순서": 2, "공정명": "C2250", "공정분류": "CUT", "배합코드": "BH002"}
                ],
                "machine_master_info": [
                    {"기계인덱스": 1, "기계코드": "C2010", "기계이름": "커팅기1"},
                    {"기계인덱스": 2, "기계코드": "C2250", "기계이름": "커팅기2"}
                ],
                "yield_data": [
                    {"GITEM": "G001", "공정명": "C2010", "수율": 0.95},
                    {"GITEM": "G002", "공정명": "C2250", "수율": 0.92}
                ],
                "gitem_operation": [
                    {"GITEM": "G001", "공정명": "C2010", "공정분류": "CUT", "배합코드": "BH001"},
                    {"GITEM": "G002", "공정명": "C2250", "공정분류": "CUT", "배합코드": "BH002"}
                ],
                "operation_types": [
                    {"공정명": "C2010", "공정분류": "CUT", "설명": "커팅공정1"},
                    {"공정명": "C2250", "공정분류": "CUT", "설명": "커팅공정2"}
                ],
                "operation_delay": [
                    {"선행공정분류": "CUT", "후행공정분류": "CUT", "타입교체시간": 30, "long_to_short": 10, "short_to_long": 20}
                ],
                "width_change": [
                    {"이전폭": 1000, "이후폭": 1200, "변경시간": 15}
                ],
                "machine_rest": [
                    {"기계인덱스": 1, "시작시간": "2024-01-01 00:00:00", "종료시간": "2024-01-01 08:00:00", "사유": "야간휴무"}
                ],
                "machine_allocate": [
                    {"기계인덱스": 1, "공정명": "C2010", "할당유형": "EXCLUSIVE"}
                ],
                "machine_limit": [
                    {"기계인덱스": 1, "공정명": "C2010", "시작시간": "2024-01-01 08:00:00", "종료시간": "2024-01-01 18:00:00", "제한사유": "작업시간"}
                ],
                "order_data": [
                    {"P/O NO": "PO001", "GITEM": "G001", "GITEM명": "제품1", "너비": 1000, "길이": 2000, "의뢰량": 100, "원단길이": 914, "납기일": "2024-01-15"},
                    {"P/O NO": "PO002", "GITEM": "G002", "GITEM명": "제품2", "너비": 1200, "길이": 1500, "의뢰량": 50, "원단길이": 609, "납기일": "2024-01-20"}
                ]
            }
            
            response = await client.post("http://localhost:8000/api/v1/stage1/load-data", json=sample_data)
            if response.status_code == 200:
                session_id = response.json()["session_id"]
                print(f"✅ 1단계 성공: 데이터 로딩 완료")
                print(f"📊 세션 ID: {session_id}")
            else:
                print(f"❌ 1단계 실패: {response.status_code}")
                print(f"📊 오류 내용: {response.text}")
                return
            
            # 3. 2단계 전처리
            print("\n🔍 3. 2단계 전처리 테스트...")
            response = await client.post(
                "http://localhost:8000/api/v1/stage2/preprocessing",
                json={"session_id": session_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 2단계 성공: 전처리 완료")
                print(f"📊 처리된 작업: {result['processed_jobs']}개")
            else:
                print(f"❌ 2단계 실패: {response.status_code}")
                print(f"📊 오류 내용: {response.text}")
                return
            
            # 4. 3단계 수율 예측
            print("\n🔍 4. 3단계 수율 예측 테스트...")
            response = await client.post(
                "http://localhost:8000/api/v1/stage3/yield-prediction",
                json={"session_id": session_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 3단계 성공: 수율 예측 완료")
                print(f"📊 수율 예측 수: {result['yield_predictions']}개")
            else:
                print(f"❌ 3단계 실패: {response.status_code}")
                print(f"📊 오류 내용: {response.text}")
                return
            
            # 5. 4단계 DAG 생성
            print("\n🔍 5. 4단계 DAG 생성 테스트...")
            response = await client.post(
                "http://localhost:8000/api/v1/stage4/dag-creation",
                json={"session_id": session_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 4단계 성공: DAG 생성 완료")
                print(f"📊 DAG 노드 수: {result['dag_nodes']}개")
                print(f"📊 기계 수: {result['machines']}개")
            else:
                print(f"❌ 4단계 실패: {response.status_code}")
                print(f"📊 오류 내용: {response.text}")
                return
            
            # 6. 세션 상태 확인
            print("\n🔍 6. 세션 상태 확인...")
            response = await client.get(f"http://localhost:8000/api/v1/session/{session_id}/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ 세션 상태 조회 성공")
                print(f"📊 완료된 단계: {status['completed_stages']}")
                print(f"📊 전체 단계: {status['total_stages']}")
            else:
                print(f"❌ 세션 상태 조회 실패: {response.status_code}")
            
            print("\n" + "=" * 50)
            print("🏁 4단계 테스트 완료")
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {str(e)}")
            import traceback
            print(f"📊 상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_stage4())
