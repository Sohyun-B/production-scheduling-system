# 생산 스케줄링 시스템 UI 데이터 명세서

## 1. 통계 카드 섹션 (Stats Cards)

### 현재 UI 표시 내용:
- **주문 현황**: 174개 주문 대기
- **Makespan**: 1047h 총 소요 시간
- **완료율**: 100% (474개 작업)
- **정시 달성**: 0 지연 일수
- **스케줄링 방식**: DispatchPriorityStrategy 선택됨

### Python에서 가져와야 할 데이터:
```python
# 주문 데이터
total_orders = len(orders_df)  # 전체 주문 수
pending_orders = len(orders_df[orders_df['status'] == 'pending'])  # 대기 주문 수

# 스케줄링 결과
makespan = max(schedule_result['end_time'])  # 최대 완료 시간
total_tasks = len(schedule_result['tasks'])  # 총 작업 수
completion_rate = (completed_tasks / total_tasks) * 100  # 완료율
late_orders = len([order for order in orders if order['end_date'] > order['due_date']])  # 지연 주문 수
total_late_days = sum([order['late_days'] for order in orders if order['late_days'] > 0])  # 총 지연 일수
```

## 2. 스케줄링 설정 (Configuration)

### 현재 UI 표시 내용:
- **스케줄링 시작일**: 2025-05-15 (사용자 입력)
- **스케줄링 방식**: DispatchPriorityStrategy, DAG기반, FIFO, SPT, EDD (선택)
- **Window Size**: 5일 (DAG 단계에서 입력)

### Python에서 처리해야 할 파라미터:
```python
# config.py 또는 main.py에서 받아야 할 파라미터
scheduling_config = {
    'start_date': '2025-05-15',  # 스케줄링 시작일
    'window_size': 5,  # 윈도우 크기 (일)
    'scheduling_method': 'DispatchPriorityStrategy',  # 스케줄링 방식
    'average_yield': 94.5  # 평균 수율
}
```

## 3. 진행 상황 모니터링 (Progress Monitoring)

### 현재 UI 표시 내용:
1. **데이터 준비** (0-25%): 라인스피드 997개, 기계정보 8개
2. **전처리** (25-50%): 474개 작업 생성, 기계 제약 조건
3. **수율 예측** (50-70%): 평균 수율 94.5% 적용
4. **DAG 생성** (70-90%): 474개 노드, 4단계 레벨
5. **스케줄링** (90-100%): 스케줄링 알고리즘 실행

### Python에서 전송해야 할 진행 상황:
```python
# web_progress.py에서 보내야 할 데이터
progress_data = {
    'step': 'data_loading',  # 현재 단계
    'step_name': '데이터 준비',
    'progress_percentage': 25,  # 진행률
    'message': '설정 데이터 로딩 중...',
    'details': [
        f'라인스피드 {len(line_speed_df)}개, 기계정보 {len(machine_df)}개',
        f'스케줄링 시작일: {config.start_date}',
        f'Window Size: {config.window_size}일',
        f'스케줄링 방식: {config.scheduling_method}'
    ],
    'started_at': datetime.now().isoformat(),
    'status': 'running'  # running, completed, failed
}
```

## 4. 전처리 상세 정보 (Preprocessing Details)

### 현재 UI 표시 내용:
#### 1. 기계 휴무 (machine_rest):
- 1호기: 2025-05-20 09:00~17:00
- 2호기: 2025-05-22 전일
- 3호기: 2025-05-25 08:00~18:00

#### 2. 기계 할당 제한 (machine_allocate):
- 공정 A: 2호기, 3호기에서 수행 불가
- 공정 B: 1호기에서 수행 불가
- 영향받는 GITEM: 31704, 32023

#### 3. 기계 제한 사항 (machine_limit):
- 공정 D: 1호기에서만 수행 가능
- 공정 E: 2호기에서만 수행 가능

### Python에서 가져와야 할 데이터:
```python
# 불가능한 공정 입력값.xlsx에서 읽어야 할 데이터
constraints_data = {
    'machine_rest': [
        {'machine': 'T0915', 'date_range': '2025-05-20 09:00~17:00', 'reason': '정기점검'},
        {'machine': 'T02149', 'date_range': '2025-05-22 전일', 'reason': '설비보수'}
    ],
    'machine_allocate': [
        {'process': 'A', 'impossible_machines': ['T02149', 'T02299'], 'reason': '기계 규격 불일치'},
        {'process': 'B', 'impossible_machines': ['T0915'], 'reason': '공정 특성 불일치'}
    ],
    'machine_limit': [
        {'process': 'D', 'required_machine': 'T0915', 'reason': '전용 장비 필요'},
        {'process': 'E', 'required_machine': 'T02149', 'reason': '특수 공정'}
    ],
    'affected_gitems': ['31704', '32023']  # machine_allocate로 영향받는 GITEM 목록
}
```

## 5. 최종 결과 (Final Results)

### 현재 UI 표시 내용:
#### 실행 결과:
- **Makespan**: 1047 시간
- **총 소요일**: 21.8 일
- **처리 주문**: 174 개
- **지연 일수**: 0 일

#### 설정 파라미터:
- **시작일**: 2025-05-15
- **Window Size**: 5 일
- **스케줄링 방식**: DispatchPriorityStrategy
- **평균 수율**: 94.5%

### Python에서 가져와야 할 결과 데이터:
```python
# 스케줄링 결과
final_results = {
    'makespan': float(max_completion_time),  # 시간
    'total_duration_days': float(makespan / 24),  # 일
    'total_orders': int(len(processed_orders)),
    'total_tasks': int(len(all_tasks)),
    'late_orders': int(len(late_orders)),
    'total_late_days': int(sum_late_days),
    'on_time_rate': float((on_time_orders / total_orders) * 100),
    
    # 설정 파라미터 (확인용)
    'config': {
        'start_date': config.start_date,
        'window_size': config.window_size,
        'scheduling_method': config.scheduling_method,
        'average_yield': config.average_yield
    }
}
```

## 6. 간트 차트 (Gantt Chart)

### 현재 UI 표시:
- Canvas로 그린 가짜 간트 차트 (5개 기계 × 시간)

### Python에서 생성해야 할 데이터:
```python
# 간트 차트 데이터
gantt_data = {
    'machines': ['T0915', 'T02149', 'T02299', 'T02300', 'T02301'],  # 기계 목록
    'schedule': [
        {
            'machine': 'T0915',
            'tasks': [
                {
                    'task_id': 'TASK_001',
                    'gitem': '31704',
                    'start_time': 0,  # 시작 시간 (시간 단위)
                    'duration': 4.5,  # 작업 시간
                    'color': '#FF6B6B'  # 색상 (선택사항)
                }
            ]
        }
    ],
    'total_duration': 1047  # 전체 스케줄 길이 (시간)
}

# 또는 이미지 파일로 저장 후 경로 반환
gantt_image_path = 'results/gantt_chart.png'
```

## 7. 주문 생산 요약 테이블 (Order Summary Table)

### 현재 UI 표시:
- P/O NO, GITEM, 품목명, 납기일, 종료날짜, 지각일수

### Python에서 가져와야 할 데이터:
```python
# 주문 요약 테이블
order_summary = [
    {
        'po_no': 'SW1250407101',
        'gitem': '31704',
        'gitem_name': 'PPF필름',
        'due_date': '2025-05-21',
        'end_date': '2025-05-15',  # 실제 완료일
        'late_days': 0  # 지연 일수 (음수면 조기 완료)
    }
]
```

## 8. 주요 Excel/데이터 파일에서 읽어야 할 내용

### 입력 데이터:
1. **preprocessed_order.xlsx**: 174개 주문 데이터
2. **불가능한 공정 입력값.xlsx**: 기계 제약 조건
3. **라인스피드 데이터**: 997개 라인스피드 정보
4. **기계 정보**: 8개 기계 정보

### 출력 데이터:
1. **스케줄링 결과 Excel**: 주문별 완료 시간, 지연 정보
2. **간트 차트 이미지**: PNG 파일
3. **기계별 작업 할당**: 각 기계의 작업 스케줄

## 9. API 엔드포인트 설계 제안

```python
# FastAPI 엔드포인트
@app.post("/api/v1/scheduling/start")
async def start_scheduling(config: SchedulingConfig):
    # 스케줄링 시작 및 진행상황 추적
    
@app.get("/api/v1/scheduling/progress/{run_id}")
async def get_progress(run_id: str):
    # 실시간 진행상황 반환
    
@app.get("/api/v1/scheduling/results/{run_id}")
async def get_results(run_id: str):
    # 최종 결과 반환
    
@app.get("/api/v1/constraints")
async def get_constraints():
    # 기계 제약 조건 정보 반환
```

이 명세서를 바탕으로 Python 백엔드에서 실제 데이터를 가져와서 UI에 표시할 수 있습니다.