#!/usr/bin/env python3
"""
API 서버 결과와 main.py 결과를 비교하는 스크립트
"""

import json
import sys
import os
from pathlib import Path

def load_json_file(file_path):
    """JSON 파일을 로드합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"파일 로드 실패 {file_path}: {e}")
        return None

def compare_stage2_results(main_py_result, api_result):
    """2단계(전처리) 결과를 비교합니다."""
    print("\n=== 2단계(전처리) 결과 비교 ===")
    
    main_data = main_py_result.get('data', {})
    api_data = api_result.get('data', {})
    
    # 입력 주문 수 비교
    main_orders = main_data.get('input_orders', 0)
    api_orders = api_data.get('input_orders', 0)
    print(f"입력 주문 수: main.py={main_orders}, API={api_orders}, 일치={main_orders == api_orders}")
    
    # 처리된 작업 수 비교
    main_jobs = main_data.get('processed_jobs', 0)
    api_jobs = api_data.get('processed_jobs', 0)
    print(f"처리된 작업 수: main.py={main_jobs}, API={api_jobs}, 일치={main_jobs == api_jobs}")
    
    return main_orders == api_orders and main_jobs == api_jobs

def compare_stage5_results(main_py_result, api_result):
    """5단계(스케줄링) 결과를 비교합니다."""
    print("\n=== 5단계(스케줄링) 결과 비교 ===")
    
    main_data = main_py_result.get('data', {})
    api_data = api_result.get('data', {})
    
    # 주요 지표들 비교
    metrics = [
        'window_days_used',
        'makespan_slots', 
        'makespan_hours',
        'total_days',
        'processed_jobs_count'
    ]
    
    all_match = True
    for metric in metrics:
        main_val = main_data.get(metric, 0)
        api_val = api_data.get(metric, 0)
        match = main_val == api_val
        print(f"{metric}: main.py={main_val}, API={api_val}, 일치={match}")
        if not match:
            all_match = False
    
    # 기계 정보 개수 비교
    main_machines = len(main_data.get('machine_info', []))
    api_machines = len(api_data.get('machine_info', []))
    print(f"기계 정보 개수: main.py={main_machines}, API={api_machines}, 일치={main_machines == api_machines}")
    
    if main_machines != api_machines:
        all_match = False
    
    return all_match

def main():
    print("API 서버 결과와 main.py 결과 비교")
    print("=" * 50)
    
    # main.py 결과 로드
    main_stage2 = load_json_file("python_engine/data/output/stage2_preprocessing.json")
    main_stage5 = load_json_file("python_engine/data/output/stage5_scheduling.json")
    
    if not main_stage2 or not main_stage5:
        print("main.py 결과 파일을 찾을 수 없습니다.")
        return
    
    # API 서버 결과는 Redis에서 가져와야 하는데, 
    # 여기서는 사용자가 제공한 응답 데이터를 사용합니다.
    # 실제로는 Redis에서 session_id로 조회해야 합니다.
    
    print("\n⚠️  API 서버 결과는 Redis에서 session_id로 조회해야 합니다.")
    print("현재는 main.py 결과만 확인했습니다.")
    
    print(f"\n📊 main.py 2단계 결과:")
    print(f"  - 입력 주문 수: {main_stage2['data']['input_orders']}")
    print(f"  - 처리된 작업 수: {main_stage2['data']['processed_jobs']}")
    
    print(f"\n📊 main.py 5단계 결과:")
    print(f"  - 처리된 작업 수: {main_stage5['data']['processed_jobs_count']}")
    print(f"  - Makespan (슬롯): {main_stage5['data']['makespan_slots']}")
    print(f"  - Makespan (시간): {main_stage5['data']['makespan_hours']}")
    print(f"  - 총 일수: {main_stage5['data']['total_days']}")
    print(f"  - 기계 정보 개수: {len(main_stage5['data']['machine_info'])}")
    
    print(f"\n✅ main.py 실행이 성공적으로 완료되었습니다.")
    print(f"   - 2단계: {main_stage2['data']['processed_jobs']}개 작업 처리")
    print(f"   - 5단계: {main_stage5['data']['processed_jobs_count']}개 작업 스케줄링")

if __name__ == "__main__":
    main()


