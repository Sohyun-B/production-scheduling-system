# 데이터 흐름 분석 및 API 사용 가이드

## 📊 단계별 데이터 흐름 분석

### 1단계: 데이터 로딩
**입력**: 외부 API 또는 직접 데이터
**출력**: DataFrame 형태의 마스터 데이터

```python
# 입력 데이터 구조
{
    "linespeed": [...],           # 품목별 라인스피드
    "operation_sequence": [...],  # 공정 순서
    "machine_master_info": [...], # 기계 마스터 정보
    "yield_data": [...],          # 수율 데이터
    "gitem_operation": [...],     # GITEM별 공정
    "operation_types": [...],     # 공정 분류
    "operation_delay": [...],     # 공정 지연
    "width_change": [...],        # 폭 변경
    "machine_rest": [...],        # 기계 휴식
    "machine_allocate": [...],    # 기계 할당
    "machine_limit": [...],       # 기계 제한
    "order_data": [...]           # 주문 데이터
}

# 출력 (Redis 저장)
{
    "dataframes": {
        "linespeed": DataFrame,
        "operation_sequence": DataFrame,
        "machine_master_info": DataFrame,
        "yield_data": DataFrame,
        "gitem_operation": DataFrame,
        "operation_types": DataFrame,
        "operation_delay": DataFrame,
        "width_change": DataFrame,
        "machine_rest": DataFrame,
        "machine_allocate": DataFrame,
        "machine_limit": DataFrame,
        "order_data": DataFrame
    },
    "data_summary": {
        "linespeed_count": int,
        "machine_count": int,
        "total_orders": int,
        ...
    }
}
```

### 2단계: 전처리
**입력**: 1단계의 order_data, operation_sequence, operation_types, machine_limit, machine_allocate, linespeed
**출력**: sequence_seperated_order, linespeed (수정됨)

```python
# 입력 (1단계에서 로드)
order_data = load_stage_data(session_id, "stage1")["dataframes"]["order_data"]
operation_sequence = load_stage_data(session_id, "stage1")["dataframes"]["operation_sequence"]
operation_types = load_stage_data(session_id, "stage1")["dataframes"]["operation_types"]
machine_limit = load_stage_data(session_id, "stage1")["dataframes"]["machine_limit"]
machine_allocate = load_stage_data(session_id, "stage1")["dataframes"]["machine_allocate"]
linespeed = load_stage_data(session_id, "stage1")["dataframes"]["linespeed"]

# 출력 (Redis 저장)
{
    "sequence_seperated_order": DataFrame,  # 공정별 분리된 주문
    "linespeed": DataFrame,                 # 수정된 라인스피드
    "machine_constraints": {
        "machine_rest": [...],
        "machine_allocate": [...],
        "machine_limit": [...]
    }
}
```

### 3단계: 수율 예측
**입력**: 1단계의 yield_data, gitem_operation + 2단계의 sequence_seperated_order
**출력**: yield_predictor, sequence_yield_df, sequence_seperated_order (수정됨)

```python
# 입력 (이전 단계에서 로드)
yield_data = load_stage_data(session_id, "stage1")["dataframes"]["yield_data"]
gitem_operation = load_stage_data(session_id, "stage1")["dataframes"]["gitem_operation"]
sequence_seperated_order = load_stage_data(session_id, "stage2")["sequence_seperated_order"]

# 출력 (Redis 저장)
{
    "yield_predictor": YieldPredictor,           # 수율 예측기 객체
    "sequence_yield_df": DataFrame,              # 수율 예측 결과
    "sequence_seperated_order": DataFrame        # 수율이 적용된 주문 데이터
}
```

### 4단계: DAG 생성
**입력**: 3단계의 sequence_seperated_order + 1단계의 linespeed, machine_master_info
**출력**: dag_df, opnode_dict, manager, machine_dict, merged_df

```python
# 입력 (이전 단계에서 로드)
sequence_seperated_order = load_stage_data(session_id, "stage3")["sequence_seperated_order"]
linespeed = load_stage_data(session_id, "stage1")["dataframes"]["linespeed"]
machine_master_info = load_stage_data(session_id, "stage1")["dataframes"]["machine_master_info"]

# 출력 (Redis 저장)
{
    "dag_df": DataFrame,                    # DAG 데이터프레임
    "opnode_dict": dict,                    # 노드 딕셔너리
    "manager": DAGGraphManager,             # DAG 관리자
    "machine_dict": dict,                   # 기계 딕셔너리
    "merged_df": DataFrame                  # 병합된 데이터프레임
}
```

### 5단계: 스케줄링 실행
**입력**: 4단계의 dag_df, opnode_dict, manager, machine_dict + 1단계의 operation_delay, width_change, machine_rest + 2단계의 sequence_seperated_order
**출력**: result, scheduler, delay_processor, actual_makespan

```python
# 입력 (이전 단계에서 로드)
dag_df = load_stage_data(session_id, "stage4")["dag_df"]
opnode_dict = load_stage_data(session_id, "stage4")["opnode_dict"]
manager = load_stage_data(session_id, "stage4")["manager"]
machine_dict = load_stage_data(session_id, "stage4")["machine_dict"]
operation_delay = load_stage_data(session_id, "stage1")["dataframes"]["operation_delay"]
width_change = load_stage_data(session_id, "stage1")["dataframes"]["width_change"]
machine_rest = load_stage_data(session_id, "stage1")["dataframes"]["machine_rest"]
sequence_seperated_order = load_stage_data(session_id, "stage2")["sequence_seperated_order"]

# 출력 (Redis 저장)
{
    "result": DataFrame,                    # 스케줄링 결과
    "scheduler": Scheduler,                 # 스케줄러 객체
    "delay_processor": DelayProcessor,      # 지연 처리기
    "actual_makespan": float               # 실제 Makespan
}
```

### 6단계: 결과 후처리
**입력**: 5단계의 result, scheduler + 4단계의 merged_df + 1단계의 order_data + 2단계의 sequence_seperated_order
**출력**: results (지각 분석, 기계 정보 등)

```python
# 입력 (이전 단계에서 로드)
result = load_stage_data(session_id, "stage5")["result"]
scheduler = load_stage_data(session_id, "stage5")["scheduler"]
merged_df = load_stage_data(session_id, "stage4")["merged_df"]
order_data = load_stage_data(session_id, "stage1")["dataframes"]["order_data"]
sequence_seperated_order = load_stage_data(session_id, "stage2")["sequence_seperated_order"]

# 출력 (Redis 저장)
{
    "results": {
        "new_output_final_result": DataFrame,
        "late_days_sum": int,
        "merged_result": DataFrame,
        "machine_info": DataFrame
    },
    "late_po_numbers": [...]
}
```

## 🔄 Redis 세션 관리

### 세션 구조
```
scheduling_session:{session_id}:stage1    # 1단계 데이터
scheduling_session:{session_id}:stage2    # 2단계 데이터
scheduling_session:{session_id}:stage3    # 3단계 데이터
scheduling_session:{session_id}:stage4    # 4단계 데이터
scheduling_session:{session_id}:stage5    # 5단계 데이터
scheduling_session:{session_id}:stage6    # 6단계 데이터
scheduling_session:{session_id}:metadata  # 세션 메타데이터
```

### 데이터 직렬화
- **DataFrame**: JSON으로 변환 후 pickle로 직렬화
- **객체**: pickle로 직접 직렬화
- **기본 타입**: JSON으로 직렬화

## 📝 API 사용 예시

### 1. 샘플 데이터 생성
```python
from sample_data_generator import SampleDataGenerator

generator = SampleDataGenerator()
sample_data = generator.generate_stage1_data()
```

### 2. 단계별 API 호출
```python
import httpx

async def run_scheduling_pipeline():
    async with httpx.AsyncClient() as client:
        # 1단계: 데이터 로딩
        response = await client.post(
            "http://localhost:8000/api/v1/stage1/load-external-data",
            json={
                "api_config": {
                    "base_url": "http://mock-api.com",
                    "use_mock": True
                }
            }
        )
        session_id = response.json()["session_id"]
        
        # 2단계: 전처리
        response = await client.post(
            "http://localhost:8000/api/v1/stage2/preprocessing",
            json={"session_id": session_id}
        )
        
        # 3단계: 수율 예측
        response = await client.post(
            "http://localhost:8000/api/v1/stage3/yield-prediction",
            json={"session_id": session_id}
        )
        
        # 4단계: DAG 생성
        response = await client.post(
            "http://localhost:8000/api/v1/stage4/dag-creation",
            json={"session_id": session_id}
        )
        
        # 5단계: 스케줄링
        response = await client.post(
            "http://localhost:8000/api/v1/stage5/scheduling",
            json={"session_id": session_id, "window_days": 5}
        )
        
        # 6단계: 결과 후처리
        response = await client.post(
            "http://localhost:8000/api/v1/stage6/results",
            json={"session_id": session_id}
        )
        
        return response.json()
```

### 3. 세션 상태 확인
```python
# 세션 상태 조회
response = await client.get(
    f"http://localhost:8000/api/v1/session/{session_id}/status"
)
status = response.json()
print(f"완료된 단계: {status['completed_stages']}")
```

## ⚠️ 주의사항

### 1. 데이터 의존성
- 각 단계는 이전 단계의 결과에 의존합니다
- 단계를 건너뛰거나 순서를 바꿀 수 없습니다
- Redis에 저장된 데이터는 세션 만료 시간 후 자동 삭제됩니다

### 2. 객체 직렬화
- DataFrame과 같은 복잡한 객체는 pickle로 직렬화됩니다
- Redis 메모리 사용량을 고려하여 적절한 세션 만료 시간을 설정하세요

### 3. 에러 처리
- 각 단계에서 오류가 발생하면 해당 단계부터 다시 시작해야 합니다
- 세션 데이터는 오류 발생 시에도 유지되므로 재시도 가능합니다
