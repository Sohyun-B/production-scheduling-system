# Production Scheduling System API - 단계별 상세 문서

## 📋 개요

이 문서는 Production Scheduling System의 6단계 API에 대한 상세한 설명을 제공합니다. 각 단계별로 코드 위치, 데이터 흐름, 입출력 구조를 설명합니다.

## 🏗️ 전체 아키텍처

```
프론트엔드 → Node.js → FastAPI → Python Engine → Redis
                ↓
            각 단계별 API 엔드포인트
                ↓
            Redis 상태 관리
                ↓
            Python Engine 함수 호출
```

---

## 1단계: 데이터 검증 (Validation)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/validation.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `validate_data()`
- **데이터 모델**: `app/models/schemas.py` → `ValidationRequest`, `ValidationResponse`

### 🔄 데이터 흐름
```
프론트엔드 → POST /api/v1/validation/ → validation.py → python_engine_service.validate_data() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id",
  "order_data": [
    {
      "P/O NO": "PO001",
      "GITEM": "GITEM001", 
      "납기일": "2025-01-15",
      "수량": 1000,
      "치수": "1500x1000"
    }
  ],
  "machine_data": [
    {
      "기계코드": "M001",
      "기계이름": "라인1",
      "처리속도": 100,
      "가능공정": ["PPF점착", "TOP COATING"]
    }
  ],
  "operation_data": [
    {
      "공정ID": "OP001",
      "공정명": "PPF점착",
      "소요시간": 2.5,
      "선행공정": []
    }
  ],
  "constraint_data": [
    {
      "제약조건ID": "C001",
      "기계제한": "M001",
      "공정제한": "OP001",
      "설정시간": 0.5
    }
  ]
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "데이터 검증이 완료되었습니다.",
  "data": {
    "order_count": 174,
    "machine_count": 5,
    "operation_count": 12,
    "constraint_count": 8,
    "validation_passed": true,
    "errors": []
  }
}
```

### 🔍 검증 로직
1. **필수 컬럼 검증**: 주문 데이터에 P/O NO, GITEM, 납기일 확인
2. **기계 데이터 검증**: 기계코드, 기계이름 필수 컬럼 확인
3. **날짜 형식 검증**: 납기일을 datetime으로 변환 가능한지 확인
4. **데이터 타입 검증**: 각 필드의 데이터 타입 적합성 확인

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:validation": {
    "stage": "validation",
    "session_id": "unique-session-id",
    "validation_result": { /* 검증 결과 */ },
    "input_data": { /* 원본 입력 데이터 */ }
  }
}
```

---

## 2단계: 전처리 (Preprocessing)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/preprocessing.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `run_preprocessing()`
- **Python Engine**: `python_engine/src/preprocessing/__init__.py` → `preprocessing()`

### 🔄 데이터 흐름
```
Redis(validation) → POST /api/v1/preprocessing/ → preprocessing.py → python_engine_service.run_preprocessing() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id",
  "window_days": 5
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "데이터 전처리가 완료되었습니다.",
  "data": {
    "processed_jobs_count": 474,
    "window_days": 5
  }
}
```

### 🔧 전처리 과정
1. **월별 주문 분리**: `seperate_order_by_month()` - 납기일 기준으로 주문을 월별로 분리
2. **동일 주문 통합**: `same_order_groupby()` - 동일한 주문을 통합하여 배치 효율화
3. **공정 순서 생성**: `create_sequence_seperated_order()` - 주문별 상세 공정 순서 생성
4. **기계 제약 적용**: `operation_machine_limit()` - 기계 제약 조건 적용
5. **강제 할당 처리**: `operation_machine_exclusive()` - 강제 할당 처리

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:preprocessing": {
    "stage": "preprocessing",
    "session_id": "unique-session-id",
    "window_days": 5,
    "sequence_seperated_order": [ /* 전처리된 주문 데이터 */ ],
    "linespeed": [ /* 라인스피드 데이터 */ ],
    "processed_jobs_count": 474
  }
}
```

---

## 3단계: 수율 예측 (Yield Prediction)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/yield_prediction.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `run_yield_prediction()`
- **Python Engine**: `python_engine/src/yield_management/__init__.py` → `yield_prediction()`

### 🔄 데이터 흐름
```
Redis(preprocessing) → POST /api/v1/yield-prediction/ → yield_prediction.py → python_engine_service.run_yield_prediction() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id"
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "수율 예측이 완료되었습니다.",
  "data": {
    "yield_prediction_completed": true,
    "sequence_yield_count": 120
  }
}
```

### 🔧 수율 예측 과정
1. **수율 데이터 전처리**: `YieldPredictor.preprocessing()` - 과거 수율 데이터 정리
2. **공정별 수율 예측**: `YieldPredictor.calculate_predicted_yield()` - 공정별 예측 수율 계산
3. **시퀀스별 수율 계산**: `YieldPredictor.predict_sequence_yield()` - 시퀀스별 종합 수율 계산
4. **생산량 조정**: `YieldPredictor.adjust_production_length()` - 예측 수율 반영한 생산량 조정

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:yield_prediction": {
    "stage": "yield_prediction",
    "session_id": "unique-session-id",
    "sequence_yield_df": [ /* 수율 예측 결과 */ ],
    "adjusted_sequence_order": [ /* 수율 반영된 주문 데이터 */ ],
    "yield_prediction_completed": true
  }
}
```

---

## 4단계: DAG 생성 (DAG Creation)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/dag_creation.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `run_dag_creation()`
- **Python Engine**: `python_engine/src/dag_management/__init__.py` → `create_complete_dag_system()`

### 🔄 데이터 흐름
```
Redis(preprocessing) → POST /api/v1/dag-creation/ → dag_creation.py → python_engine_service.run_dag_creation() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id"
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "DAG 생성이 완료되었습니다.",
  "data": {
    "dag_creation_completed": true,
    "node_count": 1200,
    "machine_count": 5
  }
}
```

### 🔧 DAG 생성 과정
1. **공정 정보 테이블 생성**: `make_process_table()` - 공정 정보 테이블 생성
2. **DAG 데이터프레임 생성**: `Create_dag_dataframe.create_full_dag()` - DAG 데이터프레임 생성
3. **작업 노드 딕셔너리 생성**: `create_opnode_dict()` - 작업 노드 딕셔너리 생성
4. **DAG 그래프 구축**: `DAGGraphManager.build_from_dataframe()` - DAG 그래프 구축
5. **기계 딕셔너리 생성**: `create_machine_dict()` - 기계별 정보 사전 생성

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:dag_creation": {
    "stage": "dag_creation",
    "session_id": "unique-session-id",
    "dag_df": [ /* DAG 데이터프레임 */ ],
    "merged_df": [ /* 병합된 데이터프레임 */ ],
    "node_count": 1200,
    "machine_count": 5,
    "dag_creation_completed": true
  }
}
```

---

## 5단계: 스케줄링 (Scheduling)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/scheduling.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `run_scheduling()`
- **Python Engine**: `python_engine/src/scheduler/` → `DispatchPriorityStrategy`

### 🔄 데이터 흐름
```
Redis(dag_creation) → POST /api/v1/scheduling/ → scheduling.py → python_engine_service.run_scheduling() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id",
  "window_days": 5
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "스케줄링이 완료되었습니다.",
  "data": {
    "scheduling_completed": true,
    "makespan_slots": 1088,
    "total_days": 22.67,
    "processed_jobs_count": 474
  }
}
```

### 🔧 스케줄링 과정
1. **디스패치 룰 생성**: `create_dispatch_rule()` - 우선순위 규칙 생성
2. **스케줄러 초기화**: `Scheduler()` - 스케줄러 초기화 및 자원 할당
3. **기계 다운타임 적용**: `allocate_machine_downtime()` - 기계 중단시간 설정
4. **스케줄링 실행**: `DispatchPriorityStrategy.execute()` - 우선순위 기반 작업 할당
5. **기계 스케줄 생성**: `create_machine_schedule_dataframe()` - 기계별 스케줄 생성

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:scheduling": {
    "stage": "scheduling",
    "session_id": "unique-session-id",
    "window_days_used": 5,
    "makespan_slots": 1088,
    "makespan_hours": 544.0,
    "total_days": 22.67,
    "processed_jobs_count": 474,
    "result": [ /* 스케줄링 결과 */ ],
    "machine_schedule": [ /* 기계별 스케줄 */ ],
    "scheduling_completed": true
  }
}
```

---

## 6단계: 결과 처리 (Results Processing)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/results.py`
- **서비스 로직**: `app/services/python_engine_service.py` → `run_results_processing()`
- **Python Engine**: `python_engine/src/results/__init__.py` → `create_results()`

### 🔄 데이터 흐름
```
Redis(scheduling) → POST /api/v1/results/ → results.py → python_engine_service.run_results_processing() → Redis 저장
```

### 📥 입력 데이터
```json
{
  "session_id": "unique-session-id"
}
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "결과 처리가 완료되었습니다.",
  "data": {
    "results_processing_completed": true,
    "late_days_sum": 0,
    "late_products_count": 0,
    "late_po_numbers": []
  }
}
```

### 🔧 결과 처리 과정
1. **지각 주문 계산**: `LateOrderCalculator.calculate_late_order()` - 지각 주문 식별
2. **지각 일수 계산**: `LateOrderCalculator.calc_late_days()` - 총 지각 일수 계산
3. **결과 데이터 통합**: `ResultMerger.merge_everything()` - 모든 결과 데이터 통합
4. **기계 스케줄 처리**: `MachineScheduleProcessor` - 기계 스케줄 처리
5. **Excel 파일 생성**: 최종 결과를 Excel 형태로 변환

### 💾 Redis 저장 구조
```json
{
  "scheduling:{session_id}:results": {
    "stage": "results",
    "session_id": "unique-session-id",
    "late_days_sum": 0,
    "late_products_count": 0,
    "late_po_numbers": [],
    "results": {
      "new_output_final_result": [ /* 처리된 최종 결과 */ ],
      "machine_info": [ /* 기계 정보 */ ],
      "merged_result": [ /* 병합된 결과 */ ],
      "late_days_sum": 0
    },
    "results_processing_completed": true
  }
}
```

---

## 🔄 상태 관리 (Status Management)

### 📁 코드 위치
- **API 엔드포인트**: `app/api/status.py`
- **Redis 관리**: `app/core/redis_manager.py`

### 🔄 데이터 흐름
```
Redis(모든 단계) → GET /api/v1/status/{session_id} → status.py → Redis 조회 → 응답
```

### 📤 출력 데이터
```json
{
  "success": true,
  "message": "세션 상태를 조회했습니다.",
  "data": {
    "session_id": "unique-session-id",
    "progress_percentage": 100.0,
    "completed_stages": 6,
    "total_stages": 6,
    "stage_status": {
      "validation": {
        "completed": true,
        "timestamp": "2025-01-11T17:47:00",
        "data_available": true
      },
      "preprocessing": {
        "completed": true,
        "timestamp": "2025-01-11T17:47:30",
        "data_available": true
      },
      // ... 다른 단계들
    },
    "all_stages_available": true
  }
}
```

---

## 🗂️ 데이터 흐름 요약

### 전체 데이터 흐름
```
1. 프론트엔드에서 주문/기계/공정 데이터 전송
   ↓
2. 1단계: 데이터 검증 → Redis 저장
   ↓
3. 2단계: 전처리 (검증된 데이터 사용) → Redis 저장
   ↓
4. 3단계: 수율 예측 (전처리된 데이터 사용) → Redis 저장
   ↓
5. 4단계: DAG 생성 (전처리된 데이터 사용) → Redis 저장
   ↓
6. 5단계: 스케줄링 (DAG 데이터 사용) → Redis 저장
   ↓
7. 6단계: 결과 처리 (스케줄링 결과 사용) → Redis 저장
   ↓
8. 최종 결과 반환
```

### Redis 키 구조
```
scheduling:{session_id}:validation
scheduling:{session_id}:preprocessing
scheduling:{session_id}:yield_prediction
scheduling:{session_id}:dag_creation
scheduling:{session_id}:scheduling
scheduling:{session_id}:results
```

### 각 단계별 의존성
- **2단계**: 1단계 완료 필요
- **3단계**: 2단계 완료 필요
- **4단계**: 2단계 완료 필요
- **5단계**: 4단계 완료 필요
- **6단계**: 5단계 완료 필요

이 구조를 통해 각 단계가 독립적으로 실행되면서도 이전 단계의 결과를 활용할 수 있습니다.

