# Python main.py에서 UI 데이터 추출 가이드

## 🎯 현재 main.py의 데이터 추출 포인트

### 1. 통계 카드 데이터 (Stats Cards)

```python
# main.py에서 추출 가능한 데이터들

# === 주문 현황 ===
total_orders = len(order)  # line 57: 총 주문 수
reporter.log_detail("주문", f"총 {len(order)}개 주문 로딩 완료")

# === 전처리 결과 ===
total_tasks = len(sequence_seperated_order)  # line 62: 전처리 후 작업 수
reporter.log_detail("전처리", f"전처리 완료: {len(sequence_seperated_order)}개 작업 생성")

# === DAG 생성 결과 ===
total_nodes = len(dag_df)  # line 93: 총 노드 수
total_machines = len(machine_dict)  # line 94: 기계 수
reporter.log_detail("DAG", f"노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")

# === 최종 스케줄링 결과 ===
actual_makespan = result[~(result['depth'] == -1)]['node_end'].max()  # line 130
makespan_days = actual_makespan / 48  # line 137: 48시간 = 2일 (2교대 기준)
late_days_sum = results['late_days_sum']  # line 167: 총 지연 일수
```

### 2. 스케줄링 설정 파라미터

```python
# config.py에서 가져와야 할 설정값들 (UI에서 받을 값들)

# main.py line 28-29에서 현재 하드코딩된 값들
base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
window_days = config.constants.WINDOW_DAYS

# UI에서 받아야 할 파라미터들을 config로 전달하는 방법:
def run_level4_scheduling_with_config(ui_config):
    # UI에서 받은 설정값 적용
    start_date = datetime.strptime(ui_config['start_date'], '%Y-%m-%d')
    window_days = ui_config['window_size']
    scheduling_method = ui_config['scheduling_method']
    
    # 기존 base_date 대신 start_date 사용
    base_date = start_date
```

### 3. 진행 상황 데이터 (Progress Monitoring)

```python
# web_progress.py reporter에서 이미 구현된 진행 상황들

# === 1단계: 데이터 로딩 (5-25%) ===
reporter.update_progress("scheduling", 5, "Python 스케줄링 엔진 시작")
reporter.update_progress("scheduling", 10, "설정 데이터 로딩 중...")
# 상세 정보: 라인스피드 개수, 기계정보 개수 (line 40)

reporter.update_progress("scheduling", 15, "공정 분류 데이터 로딩 중...")
# 상세 정보: 공정분류 개수, 지연정보 개수 (line 47)

reporter.update_progress("scheduling", 20, "기계 제약 데이터 로딩 중...")
# 상세 정보: 기계할당 개수, 기계제한 개수 (line 54)

# === 2단계: 전처리 (25-35%) ===
reporter.update_progress("scheduling", 30, "주문 데이터 전처리 중...")
# 상세 정보: 생성된 작업 수 (line 63)

# === 3단계: 수율 예측 (35%) ===
reporter.update_progress("scheduling", 35, "수율 예측 처리 중...")
# 상세 정보: 수율 데이터 처리 결과 (line 71-73)

# === 4단계: DAG 생성 (40-55%) ===
reporter.update_progress("scheduling", 40, "작업 공정 테이블 생성 중...")
reporter.update_progress("scheduling", 45, "공정 계층구조 분석 중...")
reporter.update_progress("scheduling", 50, "DAG 의존성 그래프 생성 중...")
reporter.update_progress("scheduling", 55, f"DAG 생성 완료 (총 {len(dag_df)}개 노드)")

# === 5단계: 스케줄링 실행 (60-100%) ===
reporter.update_progress("scheduling", 60, "스케줄링 알고리즘 초기화 중...")
reporter.update_progress("scheduling", 75, "스케줄링 알고리즘 실행 중...")
reporter.update_progress("scheduling", 85, "스케줄링 알고리즘 실행 완료!")
reporter.update_progress("scheduling", 100, "스케줄링 완료! 모든 결과 파일 저장 완료")
```

### 4. 전처리 상세 정보 (Constraints Data)

```python
# main.py line 50-54에서 로딩되는 제약 조건 데이터들

# 불가능한 공정 입력값.xlsx에서 읽은 데이터
machine_rest = excel_data_3[config.sheets.MACHINE_REST]          # 기계 휴무
machine_allocate = excel_data_3[config.sheets.MACHINE_ALLOCATE]  # 기계 할당 제한  
machine_limit = excel_data_3[config.sheets.MACHINE_LIMIT]        # 기계 제한 사항

# UI로 전송할 제약 조건 데이터 구조화
def get_constraints_data():
    return {
        'machine_rest': [
            {
                'machine': row['기계코드'],
                'date_range': f"{row['시작일']} {row['시작시간']}~{row['종료시간']}" if pd.notna(row['시작시간']) else f"{row['시작일']} 전일",
                'reason': row['사유'] if '사유' in row else '휴무'
            }
            for _, row in machine_rest.iterrows()
        ],
        'machine_allocate': [
            {
                'process': row['공정명'],
                'impossible_machines': row['불가능기계'].split(',') if pd.notna(row['불가능기계']) else [],
                'reason': row['사유'] if '사유' in row else '할당 제한'
            }
            for _, row in machine_allocate.iterrows()
        ],
        'machine_limit': [
            {
                'process': row['공정명'],
                'required_machine': row['필수기계'],
                'reason': row['사유'] if '사유' in row else '제한 사항'
            }
            for _, row in machine_limit.iterrows()
        ]
    }
```

### 5. 최종 결과 데이터 (Final Results)

```python
# main.py line 155-214에서 생성되는 결과 데이터들

# create_results 함수에서 반환되는 결과
results = create_results(
    output_final_result=result_cleaned,
    merged_df=merged_df,
    original_order=order,
    sequence_seperated_order=sequence_seperated_order,
    machine_mapping=machine_master_info.set_index('기계인덱스')['기계코드'].to_dict(),
    machine_schedule_df=machine_schedule_df,
    base_date=base_date,
    scheduler=scheduler
)

# UI로 전송할 최종 결과 데이터
def get_final_results():
    return {
        'makespan': float(actual_makespan),                    # line 130
        'total_duration_days': float(actual_makespan / 48),    # line 137
        'total_orders': int(len(order)),                       # 총 주문 수
        'total_tasks': int(len(result_cleaned)),               # 총 작업 수
        'late_days_sum': int(results['late_days_sum']),        # line 167: 총 지연 일수
        'on_time_orders': int(len(order) - len([o for o in results['merged_result'] if o['지각일수'] > 0])),
        
        # 주문 요약 테이블 데이터
        'order_summary': results['new_output_final_result'].to_dict('records'),  # line 181
        
        # 기계 정보 데이터  
        'machine_info': machine_info.to_dict('records'),  # line 183
        
        # 설정 파라미터 확인
        'config': {
            'start_date': base_date.strftime('%Y-%m-%d'),
            'window_size': window_days,
            'scheduling_method': 'DispatchPriorityStrategy',  # line 119에서 사용된 전략
            'average_yield': 94.5  # 기본값 또는 실제 계산값
        }
    }
```

### 6. 간트 차트 데이터 (Gantt Chart)

```python
# main.py line 218-249에서 간트 차트 생성

# 간트 차트 이미지 파일 생성
gantt_filename = "level4_gantt.png"  # line 225
gantt = DrawChart(scheduler.Machines)  # line 221
gantt_plot = gantt.plot()  # line 222

# 간트 차트 데이터 또는 이미지 경로 반환
def get_gantt_data():
    gantt_path = os.path.abspath("level4_gantt.png")
    
    if os.path.exists(gantt_path):
        return {
            'gantt_image_path': gantt_path,
            'gantt_image_size': os.path.getsize(gantt_path),
            'machines': list(scheduler.Machines.keys()),
            'total_duration': float(actual_makespan)
        }
    else:
        return None
```

## 🚀 main.py 수정 제안

### 1. 설정 파라미터 받기 위한 수정

```python
def run_level4_scheduling_with_config(ui_config=None):
    """
    UI에서 받은 설정값으로 스케줄링 실행
    
    Args:
        ui_config (dict): {
            'start_date': '2025-05-15',
            'window_size': 5, 
            'scheduling_method': 'DispatchPriorityStrategy'
        }
    """
    if ui_config:
        # UI 설정값 적용
        start_date_str = ui_config.get('start_date', '2025-05-15')
        base_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        window_days = ui_config.get('window_size', 5)
        scheduling_method = ui_config.get('scheduling_method', 'DispatchPriorityStrategy')
    else:
        # 기본값 사용
        base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
        window_days = config.constants.WINDOW_DAYS
        scheduling_method = 'DispatchPriorityStrategy'
    
    # reporter에 설정값 전달
    reporter.log_detail("설정", f"시작일: {base_date.strftime('%Y-%m-%d')}")
    reporter.log_detail("설정", f"윈도우 크기: {window_days}일")
    reporter.log_detail("설정", f"스케줄링 방식: {scheduling_method}")
    
    # 기존 로직 계속...
```

### 2. 결과 데이터 반환을 위한 수정

```python
def run_level4_scheduling_with_config(ui_config=None):
    # ... 기존 로직 ...
    
    # 최종 결과 반환을 위한 데이터 수집
    final_results = {
        'success': True,
        'makespan': float(actual_makespan),
        'makespan_days': float(actual_makespan / 48),
        'total_orders': len(order),
        'total_tasks': len(result_cleaned),
        'late_days_sum': results['late_days_sum'],
        'order_summary': results['new_output_final_result'].to_dict('records'),
        'machine_info': machine_info.to_dict('records'),
        'gantt_chart_path': gantt_filename if os.path.exists(gantt_filename) else None,
        'excel_result_path': processed_filename,
        'config_used': {
            'start_date': base_date.strftime('%Y-%m-%d'),
            'window_size': window_days,
            'scheduling_method': scheduling_method
        }
    }
    
    # 결과를 JSON 파일로도 저장 (API에서 읽을 수 있도록)
    import json
    with open('scheduling_results.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2, default=str)
    
    return final_results
```

### 3. 명령행 인수 지원 추가

```python
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='생산 스케줄링 시스템')
    parser.add_argument('--start-date', type=str, default='2025-05-15', help='스케줄링 시작일 (YYYY-MM-DD)')
    parser.add_argument('--window-size', type=int, default=5, help='윈도우 크기 (일)')
    parser.add_argument('--method', type=str, default='DispatchPriorityStrategy', help='스케줄링 방식')
    
    args = parser.parse_args()
    
    ui_config = {
        'start_date': args.start_date,
        'window_size': args.window_size,  
        'scheduling_method': args.method
    }
    
    results = run_level4_scheduling_with_config(ui_config)
    print(f"스케줄링 완료: Makespan {results['makespan']}시간 ({results['makespan_days']}일)")
```

## 🔗 백엔드 연동 방법

```python
# FastAPI backend에서 실행
import subprocess
import json

def run_python_scheduling(config):
    cmd = [
        sys.executable, "main.py",
        "--start-date", config['start_date'],
        "--window-size", str(config['window_size']),
        "--method", config['scheduling_method']
    ]
    
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    if process.returncode == 0:
        # 결과 JSON 파일 읽기
        with open('scheduling_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
        return results
    else:
        raise Exception(f"스케줄링 실행 실패: {process.stderr}")
```

이제 main.py에서 UI 명세서에서 요구하는 모든 데이터를 추출할 수 있습니다! 🎉