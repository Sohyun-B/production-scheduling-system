# Redis 데이터 흐름 및 구조

## 📋 개요

FastAPI 서버에서 각 단계별로 Redis에 저장되는 데이터 구조와 흐름을 설명합니다.

## 🔄 데이터 흐름

```
Node.js → FastAPI → Python Engine → Redis
   ↓
1. Validation → Redis 저장
   ↓
2. Preprocessing (Redis 조회) → Redis 저장
   ↓
3. Yield Prediction (Redis 조회) → Redis 저장
   ↓
4. DAG Creation (Redis 조회) → Redis 저장
   ↓
5. Scheduling (Redis 조회) → Redis 저장
   ↓
6. Results (Redis 조회) → Redis 저장
   ↓
최종 결과 반환
```

## 🗂️ Redis 키 구조

### 기본 키 패턴
```
{session_id}:{stage}
```

### 예시
```
session-1234567890:validation
session-1234567890:preprocessing
session-1234567890:yield_prediction
session-1234567890:dag_creation
session-1234567890:scheduling
session-1234567890:results
```

## 📊 각 단계별 데이터 구조

### 1단계: Validation (검증)

**Redis 키**: `{session_id}:validation`

```json
{
  "stage": "validation",
  "session_id": "session-1234567890",
  "validation_result": {
    "order_count": 100,
    "linespeed_count": 50,
    "operation_sequence_count": 200,
    "machine_master_count": 10,
    "yield_data_count": 150,
    "gitem_operation_count": 300,
    "operation_types_count": 25,
    "operation_delay_count": 40,
    "width_change_count": 30,
    "machine_rest_count": 15,
    "machine_allocate_count": 20,
    "machine_limit_count": 18,
    "validation_passed": true,
    "errors": []
  },
  "input_data": {
    "order_data": [...],
    "linespeed": [...],
    "operation_seperated_sequence": [...],
    "machine_master_info": [...],
    "yield_data": [...],
    "gitem_operation": [...],
    "operation_types": [...],
    "operation_delay_df": [...],
    "width_change_df": [...],
    "machine_rest": [...],
    "machine_allocate": [...],
    "machine_limit": [...]
  }
}
```

### 2단계: Preprocessing (전처리)

**Redis 키**: `{session_id}:preprocessing`

```json
{
  "stage": "preprocessing",
  "session_id": "session-1234567890",
  "preprocessing_result": {
    "input_orders": 100,
    "processed_jobs": 500,
    "machine_constraints": {
      "machine_rest": [...],
      "machine_allocate": [...],
      "machine_limit": [...]
    }
  },
  "sequence_seperated_order": [...],
  "linespeed": [...]
}
```

### 3단계: Yield Prediction (수율 예측)

**Redis 키**: `{session_id}:yield_prediction`

```json
{
  "stage": "yield_prediction",
  "session_id": "session-1234567890",
  "yield_prediction_result": {
    "yield_predictor_created": true,
    "sequence_yield_count": 500,
    "adjusted_sequence_count": 500
  },
  "sequence_yield_df": [...],
  "sequence_seperated_order": [...]
}
```

### 4단계: DAG Creation (DAG 생성)

**Redis 키**: `{session_id}:dag_creation`

```json
{
  "stage": "dag_creation",
  "session_id": "session-1234567890",
  "dag_creation_result": {
    "dag_nodes": 1000,
    "machine_count": 10,
    "merged_df_count": 800
  },
  "dag_df": [...],
  "opnode_dict": {...},
  "manager": {...},
  "machine_dict": {...},
  "merged_df": [...],
  "sequence_seperated_order": [...]
}
```

### 5단계: Scheduling (스케줄링)

**Redis 키**: `{session_id}:scheduling`

```json
{
  "stage": "scheduling",
  "session_id": "session-1234567890",
  "scheduling_result": {
    "window_days_used": 5,
    "makespan_slots": 2000,
    "makespan_hours": 1000,
    "total_days": 41.67,
    "processed_jobs_count": 500
  },
  "result": [...],
  "machine_schedule": [...],
  "dag_df": [...],
  "sequence_seperated_order": [...]
}
```

### 6단계: Results (결과 처리)

**Redis 키**: `{session_id}:results`

```json
{
  "stage": "results",
  "session_id": "session-1234567890",
  "results": {
    "late_days_sum": 15,
    "total_makespan": 2000,
    "total_days": 41.67,
    "machine_info": [...],
    "order_summary": [...],
    "gantt_data": [...]
  }
}
```

## 🔧 Redis 매니저 함수

### 데이터 저장
```python
def save_stage_data(session_id: str, stage: str, data: dict) -> bool:
    key = f"{session_id}:{stage}"
    return redis_manager.set_data(key, data)
```

### 데이터 조회
```python
def get_stage_data(session_id: str, stage: str) -> dict:
    key = f"{session_id}:{stage}"
    return redis_manager.get_data(key)
```

### 데이터 삭제
```python
def delete_stage_data(session_id: str, stage: str) -> bool:
    key = f"{session_id}:{stage}"
    return redis_manager.delete_data(key)
```

## 📈 데이터 의존성

### 1단계 → 2단계
- **필요한 데이터**: `validation.input_data`
- **사용하는 데이터**: `order_data`, `operation_seperated_sequence`, `operation_types`, `machine_limit`, `machine_allocate`, `linespeed`

### 2단계 → 3단계
- **필요한 데이터**: `preprocessing.sequence_seperated_order`, `validation.input_data`
- **사용하는 데이터**: `yield_data`, `gitem_operation`, `sequence_seperated_order`

### 3단계 → 4단계
- **필요한 데이터**: `preprocessing.sequence_seperated_order`, `preprocessing.linespeed`, `validation.input_data`
- **사용하는 데이터**: `sequence_seperated_order`, `linespeed`, `machine_master_info`

### 4단계 → 5단계
- **필요한 데이터**: `dag_creation.dag_df`, `dag_creation.sequence_seperated_order`, `validation.input_data`
- **사용하는 데이터**: `dag_df`, `sequence_seperated_order`, `operation_delay_df`, `width_change_df`, `machine_rest`

### 5단계 → 6단계
- **필요한 데이터**: `scheduling.result`, `dag_creation.merged_df`, `validation.input_data`
- **사용하는 데이터**: `result`, `merged_df`, `order_data`, `sequence_seperated_order`, `machine_schedule`

## 🚀 사용 예시

### Node.js에서 데이터 조회
```javascript
// 특정 단계 결과 조회
const response = await apiClient.get(`/api/v1/status/${sessionId}`);
const validationData = response.data.stages.validation;
const preprocessingData = response.data.stages.preprocessing;
```

### Python에서 데이터 조회
```python
# Redis에서 직접 조회
validation_data = redis_manager.get_stage_data(session_id, "validation")
preprocessing_data = redis_manager.get_stage_data(session_id, "preprocessing")
```

## ⚠️ 주의사항

1. **세션 ID**: 각 요청마다 고유한 세션 ID 사용
2. **데이터 크기**: Redis 메모리 제한 고려
3. **TTL**: 데이터 자동 만료 시간 설정 (기본 24시간)
4. **에러 처리**: 각 단계별 실패 시 이전 단계 데이터 유지
5. **동시성**: 동일 세션 ID로 동시 요청 방지

이제 Redis를 통한 데이터 흐름이 명확해졌습니다!


