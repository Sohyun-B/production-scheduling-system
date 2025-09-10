#!/usr/bin/env python3
"""
6단계 결과 후처리 테스트 스크립트
"""

import httpx
import asyncio
import json

async def test_stage6():
    """6단계 결과 후처리 테스트"""
    print("🚀 6단계 결과 후처리 테스트 시작")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
                    {"기계인덱스": 1, "이전폭": 1000, "이후폭": 1200, "변경시간": 15, "long_to_short": 10, "short_to_long": 20}
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
            
            # 3. 2-5단계 빠르게 실행
            stages = [
                ("stage2", "preprocessing"),
                ("stage3", "yield-prediction"), 
                ("stage4", "dag-creation"),
                ("stage5", "scheduling")
            ]
            
            for stage, endpoint in stages:
                print(f"\n🔍 {stage} 실행...")
                if stage == "stage5":
                    response = await client.post(f"http://localhost:8000/api/v1/{stage}/{endpoint}", json={"session_id": session_id, "window_days": 5})
                else:
                    response = await client.post(f"http://localhost:8000/api/v1/{stage}/{endpoint}", json={"session_id": session_id})
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {stage} 성공")
                    if stage == "stage5":
                        print(f"📊 메시지: {result['message']}")
                        
                        # 5단계 완료 대기
                        print("⏳ 5단계 완료 대기 중...")
                        for i in range(10):
                            await asyncio.sleep(1)
                            status_response = await client.get(f"http://localhost:8000/api/v1/stage5/status/{session_id}")
                            if status_response.status_code == 200:
                                status = status_response.json()
                                if status['status'] == 'completed':
                                    print(f"✅ 5단계 완료: {status['scheduled_jobs']}개 작업 스케줄링")
                                    break
                                elif status['status'] == 'failed':
                                    print(f"❌ 5단계 실패: {status['message']}")
                                    return
                else:
                    print(f"❌ {stage} 실패: {response.status_code}")
                    print(f"📊 오류 내용: {response.text}")
                    return
            
            # 4. 6단계 결과 후처리
            print("\n🔍 6. 6단계 결과 후처리 테스트...")
            response = await client.post(
                "http://localhost:8000/api/v1/stage6/results",
                json={"session_id": session_id}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 6단계 성공: 결과 후처리 완료")
                print(f"📊 메시지: {result['message']}")
                print(f"📊 지각 주문: {result['late_orders']}개")
                print(f"📊 결과 요약:")
                summary = result['results_summary']
                print(f"   - 총 작업 수: {summary['total_jobs']}개")
                print(f"   - 지각 주문: {summary['late_orders']}개")
                print(f"   - 기계 수: {summary['machine_count']}개")
            else:
                print(f"❌ 6단계 실패: {response.status_code}")
                print(f"📊 오류 내용: {response.text}")
                return
            
            print("\n" + "=" * 50)
            print("🏁 6단계 테스트 완료")
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {str(e)}")
            import traceback
            print(f"📊 상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_stage6())
