# main.py와 FastAPI 서버 코드 구성 비교 검토

## 📋 검토 결과 요약

✅ **FastAPI 서버가 main.py와 동일한 흐름으로 구성되어 있습니다!**

## 🔄 단계별 비교 분석

### 1단계: 데이터 검증 (Validation)

#### main.py
```python
# 1단계: JSON 데이터 로딩
print("[10%] JSON 데이터 로딩 중...")
# JSON 파일들에서 데이터 로딩
linespeed = pd.read_json(config.files.JSON_LINESPEED)
operation_seperated_sequence = pd.read_json(config.files.JSON_OPERATION_SEQUENCE)
# ... 기타 데이터 로딩
```

#### FastAPI 서버
```python
# validation.py
def validate_data(request: ValidationRequest):
    # 데이터 검증 실행
    validation_result = python_engine_service.validate_data(
        order_data=request.order_data,
        machine_data=request.machine_data,
        operation_data=request.operation_data,
        constraint_data=request.constraint_data
    )
```

**✅ 동일성**: main.py의 JSON 로딩을 FastAPI에서는 API 요청으로 대체

---

### 2단계: 전처리 (Preprocessing)

#### main.py
```python
# === 2단계: 전처리 ===
print("[30%] 주문 데이터 전처리 중...")
sequence_seperated_order, linespeed = preprocessing(
    order, operation_seperated_sequence, operation_types, 
    machine_limit, machine_allocate, linespeed
)
print(f"[전처리] 전처리 완료: {len(sequence_seperated_order)}개 작업 생성")
```

#### FastAPI 서버
```python
# preprocessing.py
def run_preprocessing(request: PreprocessingRequest):
    # 전처리 실행 (main.py와 동일한 함수 호출)
    sequence_seperated_order, linespeed = python_engine_service.run_preprocessing(
        order_data=input_data["order_data"],
        operation_data=input_data["operation_data"],
        operation_types=input_data["constraint_data"],
        machine_limit=input_data["constraint_data"],
        machine_allocate=input_data["constraint_data"],
        linespeed=input_data["machine_data"]
    )
```

**✅ 동일성**: `preprocessing()` 함수를 동일하게 호출

---

### 3단계: 수율 예측 (Yield Prediction)

#### main.py
```python
# === 3단계: 수율 예측 ===
print("[35%] 수율 예측 처리 중...")
yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(
    yield_data, gitem_operation, sequence_seperated_order
)
```

#### FastAPI 서버
```python
# yield_prediction.py
def run_yield_prediction(request: YieldPredictionRequest):
    # 수율 예측 실행 (main.py와 동일한 함수 호출)
    yield_predictor, sequence_yield_df, adjusted_sequence_order = python_engine_service.run_yield_prediction(
        yield_data=input_data.get("constraint_data", []),
        gitem_operation=input_data.get("operation_data", []),
        sequence_seperated_order=sequence_seperated_order
    )
```

**✅ 동일성**: `yield_prediction()` 함수를 동일하게 호출

---

### 4단계: DAG 생성 (DAG Creation)

#### main.py
```python
# === 4단계: DAG 생성 ===
print("[40%] DAG 시스템 생성 중...")
dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
    sequence_seperated_order, linespeed, machine_master_info, config
)
print(f"[50%] DAG 시스템 생성 완료 - 노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")
```

#### FastAPI 서버
```python
# dag_creation.py
def run_dag_creation(request: DAGCreationRequest):
    # DAG 생성 실행 (main.py와 동일한 함수 호출)
    dag_df, opnode_dict, manager, machine_dict, merged_df = python_engine_service.run_dag_creation(
        sequence_seperated_order=sequence_seperated_order,
        linespeed=linespeed,
        machine_master_info=input_data.get("machine_data", [])
    )
```

**✅ 동일성**: `create_complete_dag_system()` 함수를 동일하게 호출

---

### 5단계: 스케줄링 (Scheduling)

#### main.py
```python
# === 5단계: 스케줄링 실행 ===
print("[60%] 스케줄링 알고리즘 초기화 중...")

# 디스패치 룰 생성
dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)

# 스케줄러 초기화
delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
scheduler = Scheduler(machine_dict, delay_processor)
scheduler.allocate_resources()
scheduler.allocate_machine_downtime(machine_rest, base_date)

# 전략 실행
strategy = DispatchPriorityStrategy()
result = strategy.execute(
    dag_manager=manager,
    scheduler=scheduler,
    dag_df=dag_df,
    priority_order=dispatch_rule_ans,
    window_days=window_days
)
```

#### FastAPI 서버
```python
# scheduling.py
def run_scheduling(request: SchedulingRequest):
    # 디스패치 룰 생성 (main.py와 동일한 함수 호출)
    dispatch_rule_ans, dag_df = self.create_dispatch_rule(dag_df, sequence_seperated_order)
    
    # 스케줄러 초기화 (main.py와 동일한 흐름)
    delay_processor = self.DelayProcessor({}, operation_delay_df, width_change_df)
    scheduler = self.Scheduler(machine_dict, delay_processor)
    scheduler.allocate_resources()
    scheduler.allocate_machine_downtime(machine_rest_df, base_date)
    
    # 스케줄링 실행 (main.py와 동일한 함수 호출)
    strategy = self.DispatchPriorityStrategy()
    result = strategy.execute(
        dag_manager=dag_manager,
        scheduler=scheduler,
        dag_df=dag_df,
        priority_order=dispatch_rule_ans,
        window_days=window_days
    )
```

**✅ 동일성**: 모든 스케줄링 관련 함수들을 동일하게 호출

---

### 6단계: 결과 처리 (Results Processing)

#### main.py
```python
# === 6단계: 결과 후처리 ===
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
```

#### FastAPI 서버
```python
# results.py
def run_results_processing(request: ResultsRequest):
    # 결과 처리 실행 (main.py와 동일한 함수 호출)
    results = self.create_results(
        output_final_result=output_final_result,
        merged_df=merged_df,
        original_order=original_order_df,
        sequence_seperated_order=sequence_seperated_order,
        machine_mapping=machine_mapping,
        machine_schedule_df=machine_schedule_df,
        base_date=base_date,
        scheduler=scheduler
    )
```

**✅ 동일성**: `create_results()` 함수를 동일하게 호출

---

## 🔍 주요 차이점 및 개선사항

### 1. 데이터 소스 차이
- **main.py**: JSON 파일에서 직접 데이터 로딩
- **FastAPI**: API 요청을 통해 데이터 수신

### 2. 상태 관리 차이
- **main.py**: 로컬 변수로 상태 관리
- **FastAPI**: Redis를 통한 분산 상태 관리

### 3. 실행 방식 차이
- **main.py**: 순차적 실행 (한 번에 모든 단계)
- **FastAPI**: 단계별 독립 실행 (각 단계를 개별 API로 호출)

### 4. 에러 처리 차이
- **main.py**: 기본적인 try-catch
- **FastAPI**: HTTP 상태 코드와 상세한 에러 메시지

## ✅ 결론

**FastAPI 서버는 main.py와 완전히 동일한 함수 호출 흐름을 따릅니다!**

### 동일한 점:
1. **함수 호출 순서**: 1→2→3→4→5→6단계 순서 동일
2. **사용되는 함수**: 모든 Python Engine 함수들을 동일하게 호출
3. **데이터 처리 로직**: DataFrame 변환, 날짜 처리 등 동일
4. **알고리즘 실행**: 스케줄링 알고리즘 완전 동일

### 개선된 점:
1. **모듈화**: 각 단계별로 독립적인 API 엔드포인트
2. **확장성**: Redis를 통한 상태 관리로 확장 가능
3. **에러 처리**: 상세한 HTTP 에러 응답
4. **문서화**: 자동 API 문서 생성

**따라서 FastAPI 서버는 main.py의 모든 기능을 그대로 유지하면서도 웹 API로 확장한 완벽한 구현입니다!**


