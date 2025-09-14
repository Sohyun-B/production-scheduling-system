#!/usr/bin/env python3
"""
API 서버에서 실행한 결과를 Redis에서 조회하는 스크립트
"""

import redis
import json
import sys
from datetime import datetime

def connect_redis():
    """Redis에 연결합니다."""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()  # 연결 테스트
        print("✅ Redis 연결 성공")
        return r
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        return None

def get_session_keys(redis_client):
    """모든 session 키를 조회합니다."""
    try:
        keys = redis_client.keys("session_*")
        return sorted(keys)
    except Exception as e:
        print(f"❌ Session 키 조회 실패: {e}")
        return []

def get_stage_data(redis_client, session_id, stage):
    """특정 session의 특정 stage 데이터를 조회합니다."""
    try:
        key = f"{session_id}:stage:{stage}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"❌ Stage 데이터 조회 실패 ({session_id}:{stage}): {e}")
        return None

def compare_with_main_py(api_data, stage_name):
    """API 결과와 main.py 결과를 비교합니다."""
    print(f"\n=== {stage_name} 결과 비교 ===")
    
    if not api_data:
        print("❌ API 데이터가 없습니다.")
        return False
    
    # main.py 결과 로드
    main_file = f"python_engine/data/output/stage{stage_name.split('(')[0].strip()}.json"
    try:
        with open(main_file, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
    except Exception as e:
        print(f"❌ main.py 결과 파일 로드 실패: {e}")
        return False
    
    api_stage_data = api_data.get('data', {})
    main_stage_data = main_data.get('data', {})
    
    if stage_name.startswith("2단계"):
        # 전처리 결과 비교
        api_orders = api_stage_data.get('input_orders', 0)
        main_orders = main_stage_data.get('input_orders', 0)
        api_jobs = api_stage_data.get('processed_jobs', 0)
        main_jobs = main_stage_data.get('processed_jobs', 0)
        
        print(f"입력 주문 수: API={api_orders}, main.py={main_orders}, 일치={api_orders == main_orders}")
        print(f"처리된 작업 수: API={api_jobs}, main.py={main_jobs}, 일치={api_jobs == main_jobs}")
        
        return api_orders == main_orders and api_jobs == main_jobs
        
    elif stage_name.startswith("5단계"):
        # 스케줄링 결과 비교
        metrics = ['processed_jobs_count', 'makespan_slots', 'makespan_hours', 'total_days']
        all_match = True
        
        for metric in metrics:
            api_val = api_stage_data.get(metric, 0)
            main_val = main_stage_data.get(metric, 0)
            match = api_val == main_val
            print(f"{metric}: API={api_val}, main.py={main_val}, 일치={match}")
            if not match:
                all_match = False
        
        # 기계 정보 개수 비교
        api_machines = len(api_stage_data.get('machine_info', []))
        main_machines = len(main_stage_data.get('machine_info', []))
        print(f"기계 정보 개수: API={api_machines}, main.py={main_machines}, 일치={api_machines == main_machines}")
        
        if api_machines != main_machines:
            all_match = False
            
        return all_match
    
    return False

def main():
    print("API 서버 결과 조회 및 main.py와 비교")
    print("=" * 50)
    
    # Redis 연결
    redis_client = connect_redis()
    if not redis_client:
        return
    
    # Session 키 조회
    session_keys = get_session_keys(redis_client)
    if not session_keys:
        print("❌ Session 키를 찾을 수 없습니다.")
        return
    
    print(f"\n📋 발견된 Session 키: {len(session_keys)}개")
    for i, key in enumerate(session_keys[-5:], 1):  # 최근 5개만 표시
        print(f"  {i}. {key}")
    
    # 가장 최근 session 선택
    latest_session = session_keys[-1]
    print(f"\n🔍 최근 Session 분석: {latest_session}")
    
    # 각 단계별 데이터 조회 및 비교
    stages = [
        ("2단계", "preprocessing"),
        ("3단계", "yield_prediction"), 
        ("4단계", "dag_creation"),
        ("5단계", "scheduling")
    ]
    
    all_stages_match = True
    
    for stage_name, stage_key in stages:
        stage_data = get_stage_data(redis_client, latest_session, stage_key)
        if stage_data:
            print(f"\n✅ {stage_name} 데이터 발견")
            if stage_name in ["2단계", "5단계"]:
                match = compare_with_main_py(stage_data, stage_name)
                if not match:
                    all_stages_match = False
        else:
            print(f"❌ {stage_name} 데이터 없음")
            all_stages_match = False
    
    print("\n" + "=" * 50)
    if all_stages_match:
        print("🎉 모든 단계의 결과가 main.py와 일치합니다!")
    else:
        print("⚠️  일부 단계에서 차이가 발견되었습니다.")

if __name__ == "__main__":
    main()


