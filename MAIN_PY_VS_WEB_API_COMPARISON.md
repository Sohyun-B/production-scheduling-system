# 🔍 main.py vs 웹 API 코드 구성 비교 분석

## 📊 전체 구조 비교

### **main.py 구조**
```python
def run_level4_scheduling():
    # 1. 설정값 로드
    base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
    window_days = config.constants.WINDOW_DAYS
    
    # 2. JSON 파일 직접 로딩
    linespeed = pd.read_json(config.files.JSON_LINESPEED)
    order = pd.read_json(config.files.JSON_ORDER_DATA)
    # ... 12개 파일 직접 로드
    
    # 3. 순차적 처리
    sequence_seperated_order, linespeed = preprocessing(...)
    yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(...)
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(...)
    result = strategy.execute(...)
    
    # 4. 결과 저장
    result.to_excel("data/output/result.xlsx")
```

### **웹 API 구조**
```python
# Node.js (데이터 로딩)
dataLoaderService.loadAllData() → 12개 파일 로드

# Python Server (단계별 API)
POST /api/v1/validation-with-data/ → 데이터 검증
POST /api/v1/preprocessing/ → 전처리
POST /api/v1/yield-prediction/ → 수율 예측
POST /api/v1/dag-creation/ → DAG 생성
POST /api/v1/scheduling/ → 스케줄링
POST /api/v1/results/ → 결과 처리
```

---

## 🔍 상세 비교 분석

### **1. 데이터 로딩 방식**

#### **main.py**
```python
# 직접 JSON 파일 로딩
linespeed = pd.read_json(config.files.JSON_LINESPEED)
operation_seperated_sequence = pd.read_json(config.files.JSON_OPERATION_SEQUENCE)
machine_master_info = pd.read_json(config.files.JSON_MACHINE_INFO)
yield_data = pd.read_json(config.files.JSON_YIELD_DATA)
gitem_operation = pd.read_json(config.files.JSON_GITEM_OPERATION)
operation_types = pd.read_json(config.files.JSON_OPERATION_TYPES)
operation_delay_df = pd.read_json(config.files.JSON_OPERATION_DELAY)
width_change_df = pd.read_json(config.files.JSON_WIDTH_CHANGE)
machine_rest = pd.read_json(config.files.JSON_MACHINE_REST)
machine_allocate = pd.read_json(config.files.JSON_MACHINE_ALLOCATE)
machine_limit = pd.read_json(config.files.JSON_MACHINE_LIMIT)
order = pd.read_json(config.files.JSON_ORDER_DATA)
```

#### **웹 API**
```javascript
// Node.js에서 로딩
const jsonFiles = {
  order: 'md_step2_order_data.json',
  linespeed: 'md_step2_linespeed.json',
  operation_seperated_sequence: 'md_step3_operation_sequence.json',
  // ... 12개 파일
};

// 각 파일을 processDataByType으로 처리
for (const [key, filename] of Object.entries(jsonFiles)) {
  const rawData = await this.loadJsonFile(filename);
  const processedData = this.processDataByType(key, rawData);
  loadedData[key] = processedData;
}
```

**차이점**: 
- ✅ **main.py**: 직접 pandas로 로딩
- ❌ **웹 API**: Node.js → JSON → Python으로 이중 변환

---

### **2. 설정값 처리**

#### **main.py**
```python
base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
# BASE_YEAR: 2025, BASE_MONTH: 5, BASE_DAY: 15
window_days = config.constants.WINDOW_DAYS  # 5
```

#### **웹 API**
```python
# Python Server config.py
base_year: int = 2025
base_month: int = 1  # ❌ 다름!
base_day: int = 1    # ❌ 다름!
default_window_days: int = 5
```

**차이점**:
- ❌ **기준 날짜**: main.py(2025-05-15) vs 웹 API(2025-01-01)
- ✅ **윈도우 크기**: 둘 다 5일

---

### **3. 데이터 타입 변환**

#### **main.py**
```python
# 날짜 컬럼 변환
if '시작시간' in machine_rest.columns:
    machine_rest['시작시간'] = pd.to_datetime(machine_rest['시작시간'])
if '종료시간' in machine_rest.columns:
    machine_rest['종료시간'] = pd.to_datetime(machine_rest['종료시간'])

if config.columns.DUE_DATE in order.columns:
    order[config.columns.DUE_DATE] = pd.to_datetime(order[config.columns.DUE_DATE])
```

#### **웹 API**
```python
# Python Server에서 추가 변환
if 'GITEM' in order_df.columns:
    order_df['GITEM'] = pd.to_numeric(order_df['GITEM'], errors='coerce')

if '납기일' in order_df.columns:
    order_df['납기일'] = pd.to_datetime(order_df['납기일'], utc=False)
    if order_df['납기일'].dt.tz is not None:
        order_df['납기일'] = order_df['납기일'].dt.tz_localize(None)
```

**차이점**:
- ✅ **main.py**: 기본적인 날짜 변환만
- ❌ **웹 API**: 추가적인 타입 변환 및 timezone 처리

---

### **4. 처리 흐름**

#### **main.py**
```python
# 순차적 처리 (메모리에서 직접)
sequence_seperated_order, linespeed = preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(yield_data, gitem_operation, sequence_seperated_order)
dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info, config)
result = strategy.execute(dag_manager=manager, scheduler=scheduler, dag_df=dag_df, priority_order=dispatch_rule_ans, window_days=window_days)
```

#### **웹 API**
```python
# 단계별 API 호출 (Redis를 통한 중간 저장)
# 1단계: validation → Redis 저장
# 2단계: preprocessing → Redis에서 조회 → 처리 → Redis 저장
# 3단계: yield_prediction → Redis에서 조회 → 처리 → Redis 저장
# 4단계: dag_creation → Redis에서 조회 → 처리 → Redis 저장
# 5단계: scheduling → Redis에서 조회 → 처리 → Redis 저장
```

**차이점**:
- ✅ **main.py**: 메모리에서 직접 처리
- ❌ **웹 API**: Redis를 통한 직렬화/역직렬화

---

### **5. 에러 처리**

#### **main.py**
```python
try:
    # JSON 파일 로딩
    linespeed = pd.read_json(config.files.JSON_LINESPEED)
    # ...
except FileNotFoundError as e:
    print(f"오류: {e}")

try:
    # 스케줄링 실행
    result = strategy.execute(...)
except Exception as e:
    print(f"[ERROR] Level 4 스케줄링 실행 중 오류: {e}")
    import traceback
    traceback.print_exc()
    return
```

#### **웹 API**
```python
try:
    # 각 단계별 처리
    result = self.preprocessing(...)
except Exception as e:
    logger.error(f"전처리 실패: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**차이점**:
- ✅ **main.py**: 단순한 print 기반 에러 처리
- ✅ **웹 API**: 구조화된 로깅 및 HTTP 상태 코드

---

## 🎯 완전히 동일하게 만들기 위한 개선 방안

### **1. 설정값 통일**

#### **현재 문제**
```python
# main.py
BASE_YEAR: int = 2025
BASE_MONTH: int = 5
BASE_DAY: int = 15

# Python Server
base_year: int = 2025
base_month: int = 1  # ❌ 다름
base_day: int = 1    # ❌ 다름
```

#### **해결 방안**
```python
# python-server/app/core/config.py 수정
class Settings(BaseSettings):
    base_year: int = 2025
    base_month: int = 5  # ✅ main.py와 동일
    base_day: int = 15   # ✅ main.py와 동일
```

### **2. 데이터 로딩 방식 통일**

#### **현재 문제**
- Node.js에서 JSON 로딩 → Python으로 전달
- 이중 변환으로 인한 데이터 손실 가능성

#### **해결 방안 A: Python에서 직접 로딩**
```python
# python-server/app/services/python_engine_service.py
def load_data_directly(self):
    """main.py와 동일한 방식으로 직접 로딩"""
    linespeed = pd.read_json("python_engine/data/json/md_step2_linespeed.json")
    order = pd.read_json("python_engine/data/json/md_step2_order_data.json")
    # ... 12개 파일 직접 로딩
    return {
        "linespeed": linespeed,
        "order": order,
        # ... 모든 데이터
    }
```

#### **해결 방안 B: Node.js 데이터 처리 개선**
```javascript
// nodejs-backend/src/services/dataLoaderService.js
processDataByType(key, data) {
    switch (key) {
        case 'order':
            return data.map(item => ({
                ...item,
                GITEM: parseInt(item.GITEM),  // ✅ 숫자 보장
                납기일: new Date(item.납기일).toISOString().replace('Z', '')
            }));
        // ... 다른 타입들도 정확한 변환
    }
}
```

### **3. 처리 흐름 통일**

#### **현재 문제**
- 단계별 API 호출로 인한 Redis 직렬화/역직렬화
- 데이터 일관성 문제

#### **해결 방안: 전체 스케줄링 API 강화**
```python
# python-server/app/api/scheduling.py
@router.post("/full", response_model=SchedulingResponse)
async def run_full_scheduling(request: SchedulingRequest):
    """main.py와 완전히 동일한 방식으로 실행"""
    
    # 1. 설정값 (main.py와 동일)
    base_date = datetime(2025, 5, 15)  # ✅ main.py와 동일
    window_days = 5
    
    # 2. 직접 데이터 로딩 (main.py와 동일)
    linespeed = pd.read_json("python_engine/data/json/md_step2_linespeed.json")
    order = pd.read_json("python_engine/data/json/md_step2_order_data.json")
    # ... 12개 파일 직접 로딩
    
    # 3. 순차적 처리 (main.py와 동일)
    sequence_seperated_order, linespeed = preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
    yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(yield_data, gitem_operation, sequence_seperated_order)
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info, config)
    result = strategy.execute(dag_manager=manager, scheduler=scheduler, dag_df=dag_df, priority_order=dispatch_rule_ans, window_days=window_days)
    
    # 4. 결과 반환 (Redis 저장 없이)
    return SchedulingResponse(...)
```

### **4. 데이터 타입 처리 통일**

#### **현재 문제**
- 웹 API에서 추가적인 타입 변환
- timezone 처리 차이

#### **해결 방안**
```python
# python-server/app/services/python_engine_service.py
def run_full_scheduling(self, loaded_data, window_days, base_date):
    """main.py와 완전히 동일한 데이터 처리"""
    
    # main.py와 동일한 변환만 수행
    if '시작시간' in machine_rest.columns:
        machine_rest['시작시간'] = pd.to_datetime(machine_rest['시작시간'])
    if '종료시간' in machine_rest.columns:
        machine_rest['종료시간'] = pd.to_datetime(machine_rest['종료시간'])
    
    if config.columns.DUE_DATE in order.columns:
        order[config.columns.DUE_DATE] = pd.to_datetime(order[config.columns.DUE_DATE])
    
    # 추가적인 타입 변환 제거
    # GITEM 숫자 변환 등 제거
```

---

## 📊 비교 요약

| 항목 | main.py | 웹 API | 동일도 | 개선 필요도 |
|------|---------|--------|--------|-------------|
| **데이터 로딩** | 직접 pandas | Node.js → Python | 60% | 높음 |
| **설정값** | 2025-05-15 | 2025-01-01 | 30% | 높음 |
| **처리 흐름** | 메모리 직접 | Redis 중간 저장 | 40% | 중간 |
| **데이터 타입** | 기본 변환 | 추가 변환 | 70% | 낮음 |
| **에러 처리** | print 기반 | HTTP 상태 코드 | 50% | 낮음 |
| **핵심 로직** | 동일 함수 사용 | 동일 함수 사용 | 95% | 낮음 |

## 🎯 최종 권장사항

### **1. 즉시 수정 (High Priority)**
1. **설정값 통일**: Python Server 기준 날짜를 2025-05-15로 변경
2. **전체 스케줄링 API 강화**: main.py와 동일한 방식으로 직접 처리

### **2. 중기 개선 (Medium Priority)**
1. **데이터 로딩 통일**: Python에서 직접 JSON 파일 로딩
2. **Redis 의존성 감소**: 전체 스케줄링에서는 Redis 사용 최소화

### **3. 장기 개선 (Low Priority)**
1. **에러 처리 통일**: main.py도 구조화된 로깅 도입
2. **코드 중복 제거**: 공통 로직을 별도 모듈로 분리

이러한 개선을 통해 main.py와 웹 API의 결과를 완전히 동일하게 만들 수 있습니다.
