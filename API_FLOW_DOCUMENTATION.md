# 📋 Node.js ↔ Python 서버 API 흐름 상세 문서

## 🏗️ 전체 아키텍처 개요

```
[클라이언트] → [Node.js 서버] → [Python FastAPI 서버] → [Redis] → [Python Engine]
     ↓              ↓                    ↓                ↓           ↓
   요청/응답    데이터 로딩/라우팅    비즈니스 로직    세션 관리    실제 스케줄링
```

---

## 🔄 1단계: 데이터 검증 (Validation)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/validation`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid",
  "windowDays": 5,
  "baseDate": "2025-01-01",
  "yieldPeriod": 6
}
```

#### **Node.js 내부 처리**:
1. **라우터**: `schedulingRoutes.js` → `validateValidationRequest` 미들웨어
2. **컨트롤러**: `schedulingController.validateData()`
3. **데이터 로딩**: `dataLoaderService.loadAllData()`
   ```javascript
   // dataLoaderService.js
   async loadAllData() {
     const jsonFiles = {
       order: 'md_step2_order_data.json',
       linespeed: 'md_step2_linespeed.json',
       operation_seperated_sequence: 'md_step3_operation_sequence.json',
       // ... 12개 파일 로드
     };
     
     // 각 파일을 processDataByType으로 처리
     for (const [key, filename] of Object.entries(jsonFiles)) {
       const rawData = await this.loadJsonFile(filename);
       const processedData = this.processDataByType(key, rawData);
       loadedData[key] = processedData;
     }
   }
   ```

4. **Python 서버 호출**: `pythonApiService.validateDataWithData()`

#### **Python 서버로 전송**:
```javascript
// pythonApiService.js
const response = await this.client.post('/api/v1/validation-with-data/', {
  session_id: sessionId,
  window_days: data.windowDays,
  base_date: data.baseDate,
  yield_period: data.yieldPeriod,
  loaded_data: data.loadedData,  // 12개 파일의 데이터
  stats: data.stats,
  load_results: data.loadResults
});
```

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/validation-with-data/`

#### **Python 내부 처리**:
1. **라우터**: `validation_with_data.py`
2. **서비스**: `python_engine_service.validate_loaded_data()`
   ```python
   def validate_loaded_data(self, loaded_data, session_id, window_days, base_date, yield_period):
       # 데이터 검증 로직
       validation_result = {
           "validation_status": "success",
           "loaded_data": loaded_data,
           "errors": [],
           "warnings": []
       }
   ```

3. **Redis 저장**: `redis_manager.save_stage_data()`
   ```python
   stage_data = {
       "stage": "validation",
       "session_id": session_id,
       "validation_result": validation_result,
       "loaded_data": loaded_data,
       "stats": stats
   }
   ```

#### **응답 구조**:
```json
{
  "success": true,
  "message": "데이터 검증이 완료되었습니다.",
  "data": {
    "total_orders": 174,
    "total_linespeed": 997,
    "total_machines": 8,
    "total_operation_types": 37,
    "total_yield_data": 998,
    "total_gitem_operation": 292,
    "loaded_files": 12,
    "total_files": 12,
    "validation_status": "success"
  }
}
```

---

## 🔄 2단계: 전처리 (Preprocessing)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/preprocessing`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid",
  "windowDays": 5
}
```

#### **Node.js 내부 처리**:
1. **컨트롤러**: `schedulingController.runPreprocessing()`
2. **Python 서버 호출**: `pythonApiService.runPreprocessing()`

#### **Python 서버로 전송**:
```javascript
const response = await this.client.post('/api/v1/preprocessing/', {
  session_id: sessionId,
  window_days: windowDays
});
```

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/preprocessing/`

#### **Python 내부 처리**:
1. **라우터**: `preprocessing.py`
2. **Redis에서 데이터 조회**: `redis_manager.get_stage_data(session_id, "validation")`
3. **서비스**: `python_engine_service.run_preprocessing()`
   ```python
   def run_preprocessing(self, order_data, operation_data, operation_types, machine_limit, machine_allocate, linespeed):
       # DataFrame으로 변환
       order_df = pd.DataFrame(order_data)
       operation_seperated_sequence = pd.DataFrame(operation_data)
       # ... 기타 DataFrame 변환
       
       # GITEM 컬럼을 숫자로 보장
       if 'GITEM' in order_df.columns:
           order_df['GITEM'] = pd.to_numeric(order_df['GITEM'], errors='coerce')
       
       # 전처리 실행 (main.py와 동일한 함수)
       sequence_seperated_order, linespeed = self.preprocessing(
           order_df, operation_seperated_sequence, operation_types_df,
           machine_limit_df, machine_allocate_df, linespeed_df
       )
   ```

4. **Redis 저장**: 전처리 결과 저장

#### **응답 구조**:
```json
{
  "success": true,
  "message": "데이터 전처리가 완료되었습니다.",
  "data": {
    "processed_jobs_count": 466,
    "original_orders_count": 174,
    "original_gitems_count": 107,
    "processed_gitems_count": 106,
    "excluded_gitems_count": 107,
    "excluded_gitems": [32260, 32261, ...],
    "window_days": 5
  }
}
```

---

## 🔄 3단계: 수율 예측 (Yield Prediction)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/yield-prediction`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid"
}
```

#### **Node.js 내부 처리**:
1. **컨트롤러**: `schedulingController.runYieldPrediction()`
2. **Python 서버 호출**: `pythonApiService.runYieldPrediction()`

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/yield-prediction/`

#### **Python 내부 처리**:
1. **라우터**: `yield_prediction.py`
2. **Redis에서 데이터 조회**: 전처리 결과 + 검증 데이터
3. **서비스**: `python_engine_service.run_yield_prediction()`
   ```python
   def run_yield_prediction(self, yield_data, gitem_operation, sequence_seperated_order):
       # DataFrame으로 변환
       yield_df = pd.DataFrame(yield_data)
       gitem_operation_df = pd.DataFrame(gitem_operation)
       
       # 수율 예측 실행 (main.py와 동일한 함수)
       yield_predictor, sequence_yield_df, adjusted_sequence_order = self.yield_prediction(
           yield_df, gitem_operation_df, sequence_seperated_order_df
       )
   ```

---

## 🔄 4단계: DAG 생성 (DAG Creation)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/dag-creation`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid"
}
```

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/dag-creation/`

#### **Python 내부 처리**:
1. **라우터**: `dag_creation.py`
2. **서비스**: `python_engine_service.run_dag_creation()`
   ```python
   def run_dag_creation(self, sequence_seperated_order, linespeed, machine_master_info):
       # DAG 생성 실행 (main.py와 동일한 함수)
       dag_df, opnode_dict, manager, machine_dict, merged_df = self.create_complete_dag_system(
           sequence_seperated_order, linespeed, machine_master_df, self.config
       )
   ```

3. **객체 직렬화**: `manager` 객체를 pickle로 직렬화하여 Redis 저장

---

## 🔄 5단계: 스케줄링 (Scheduling)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/scheduling`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid",
  "windowDays": 5
}
```

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/scheduling/`

#### **Python 내부 처리**:
1. **라우터**: `scheduling.py`
2. **서비스**: `python_engine_service.run_scheduling()`
   ```python
   def run_scheduling(self, dag_manager, dag_df, sequence_seperated_order, operation_delay_df, width_change_df, machine_rest, machine_dict, window_days, opnode_dict, base_date):
       # 스케줄링 실행 (main.py와 동일한 함수)
       strategy = DispatchPriorityStrategy()
       result = strategy.execute(
           dag_manager=manager,
           scheduler=scheduler,
           dag_df=dag_df,
           priority_order=dispatch_rule_ans,
           window_days=window_days
       )
   ```

#### **응답 구조**:
```json
{
  "success": true,
  "message": "🎉 전체 스케줄링이 완료되었습니다!",
  "data": {
    "scheduling_completed": true,
    "total_jobs_scheduled": 466,
    "makespan": 1008,
    "total_days": 21,
    "late_jobs_count": 0,
    "late_days_sum": 0,
    "completion_message": "모든 단계가 성공적으로 완료되었습니다."
  }
}
```

---

## 🔄 6단계: 결과 처리 (Results)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/step/results`

#### **요청 구조**:
```javascript
{
  "sessionId": "session-uuid"
}
```

### 📤 Python 서버 처리

#### **엔드포인트**: `POST /api/v1/results/`

#### **Python 내부 처리**:
1. **라우터**: `results.py`
2. **서비스**: `python_engine_service.run_results_processing()`
   ```python
   def run_results_processing(self, output_final_result, merged_df, original_order, sequence_seperated_order, machine_mapping, machine_schedule_df, base_date, scheduler):
       # 결과 처리 실행 (main.py와 동일한 함수)
       results = self.create_results(
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

---

## 🔧 전체 스케줄링 (Full Scheduling)

### 📥 Node.js 요청 처리

#### **엔드포인트**: `POST /api/scheduling/full`

#### **요청 구조**:
```javascript
{
  "windowDays": 5,
  "data": {
    "baseDate": "2025-01-01",
    "yieldPeriod": 6
  }
}
```

#### **Node.js 내부 처리**:
1. **컨트롤러**: `schedulingController.runFullScheduling()`
2. **순차적 API 호출**: 1단계부터 5단계까지 순차 실행
3. **최종 응답**: 모든 단계 결과를 포함한 통합 응답

---

## 📊 데이터 흐름 요약

### **Node.js 역할**:
- ✅ JSON 파일 로딩 및 전처리
- ✅ API 라우팅 및 요청/응답 관리
- ✅ 세션 ID 생성 및 관리
- ✅ Python 서버와의 통신 중계

### **Python 서버 역할**:
- ✅ 비즈니스 로직 실행 (main.py와 동일한 함수들)
- ✅ Redis를 통한 세션 데이터 관리
- ✅ 각 단계별 결과 저장 및 조회
- ✅ 에러 처리 및 로깅

### **Redis 역할**:
- ✅ 세션별 중간 데이터 저장
- ✅ 단계별 결과 캐싱
- ✅ 데이터 일관성 보장

### **Python Engine 역할**:
- ✅ 실제 스케줄링 알고리즘 실행
- ✅ 전처리, 수율 예측, DAG 생성, 스케줄링 로직
- ✅ main.py와 동일한 핵심 비즈니스 로직

---

## ⚠️ 주요 차이점 및 이슈

### **1. 데이터 로딩 방식**:
- **main.py**: 직접 JSON 파일 로드
- **웹 API**: Node.js에서 로드 후 Python으로 전달

### **2. 설정값 차이**:
- **기준 날짜**: main.py(2025-05-15) vs Python Server(2025-01-01)
- **수율 기준 기간**: main.py(설정 없음) vs Python Server(6개월)

### **3. 결과 차이**:
- **main.py**: 474개 작업, Makespan 1088.0
- **웹 API**: 466개 작업, Makespan 1008

### **4. 데이터 타입 처리**:
- **Node.js**: GITEM을 숫자로 변환
- **Python**: 추가 타입 검증 및 변환

이 문서는 Node.js와 Python 서버 간의 전체 API 흐름을 상세히 설명하며, 각 단계별 요청/응답 구조와 내부 처리 로직을 포함합니다.
