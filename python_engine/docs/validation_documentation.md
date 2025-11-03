# Validation 모듈 문서

## 1. 전체 워크플로우 개요

### main.py 실행 흐름

```
1. Excel 파일 로딩 (L30-L80)
   └─ 생산계획 입력정보.xlsx에서 8개 시트 읽기
   
2. Validation - 데이터 유효성 검사 및 전처리 (L122-L137)
   └─ preprocess_production_data() 호출
   
3. Order Sequencing - 주문 시퀀스 생성 (L168-L169)
   └─ generate_order_sequences() 호출
   
4. Yield Prediction - 수율 예측 (L175-L178)
   └─ yield_prediction() 호출
   
5. DAG Management - DAG 시스템 생성 (L181-L183)
   └─ create_complete_dag_system() 호출
   
6. Scheduler - 스케줄링 실행 (L194-L210)
   └─ run_scheduler_pipeline() 호출
   
7. Results - 결과 후처리 및 저장 (L214-L256)
   └─ create_results() 호출
```

### Validation 모듈의 역할

Validation 모듈은 **1단계**에서 실행되며, 다음 두 가지 핵심 기능을 수행합니다:

1. **데이터 유효성 검사 (Validator)**: 입력 데이터의 무결성 확인
2. **데이터 전처리 (ProductionDataPreprocessor)**: 스케줄링에 필요한 형태로 데이터 변환

---

## 2. Validation 모듈 상세 분석

### 2.1 preprocess_production_data() 함수

**위치**: `src/validation/__init__.py` (L13-L138)

**입력 파라미터**:
- `order_df`: PO정보 (주문 데이터)
- `linespeed_df`: 라인스피드-GITEM등 (생산 속도 정보)
- `operation_df`: GITEM-공정-순서 (제품별 공정 순서)
- `yield_df`: 수율-GITEM등 (제품별 수율 정보)
- `chemical_df`: 배합액정보 (공정별 배합액 정보)
- `operation_delay_df`: 공정교체시간
- `width_change_df`: 폭변경 정보
- `gitem_sitem_df`: 제품군-GITEM-SITEM (제품 마스터 정보)
- `linespeed_period`: 라인스피드 기간 설정 (기본값: '6_months')
- `yield_period`: 수율 기간 설정 (기본값: '6_months')
- `validate`: 데이터 유효성 검사 수행 여부 (기본값: True)
- `save_output`: 중간 결과 저장 여부 (기본값: False)

**출력**:
- 전처리된 데이터 딕셔너리 (order_data, linespeed, operation_types, operation_sequence, yield_data, machine_master_info, chemical_data, operation_delay, width_change, validation_result)

---

## 3. 1단계: 데이터 검증 및 중복 제거 (Validator)

### 3.1 실행 흐름

```python
# src/validation/__init__.py L63-L96
if validate and gitem_sitem_df is not None:
    validator = DataValidator()
    cleaned_data, validation_result = validator.validate_and_clean(
        order_df=order_df,
        gitem_sitem_df=gitem_sitem_df,
        operation_df=operation_df,
        yield_df=yield_df,
        linespeed_df=linespeed_df,
        chemical_df=chemical_df
    )
```

### 3.2 DataValidator 클래스

**위치**: `src/validation/validator.py`

**주요 메서드**:
1. `validate_and_clean()`: 검증 및 정제 통합 메서드
2. `validate_all()`: 전체 데이터 유효성 검사
3. `clean_duplicates()`: 중복 데이터 제거

---

## 4. 데이터 검증 상세 (5단계 검증)

### 4.1 검증 1/5: 제품군-GITEM-SITEM 테이블

**메서드**: `_validate_gitem_sitem()` (L78-L103)

**검증 기준**: `order_df` (주문 정보 - PO정보)

**검증 대상**: `gitem_sitem_df` (제품 마스터 정보)

**검증 목적**: 주문에 포함된 모든 제품이 제품 마스터에 등록되어 있는지 확인

**예상 데이터 형태**:
```
order_df:
  - gitemno (제품코드): 문자열, 예) "G001", "G002"
  - spec (규격): 문자열, 예) "1000x2000", "800x1500"

gitem_sitem_df:
  - gitemno (제품코드): 문자열
  - spec (규격): 문자열
```

**제약 조건**:
- 주문 데이터의 모든 (제품코드, 규격) 조합이 제품 마스터 테이블에 존재해야 함

**검증 로직**:
1. `order_df`에서 (gitemno, spec) 조합 집합 생성
2. `gitem_sitem_df`에서 (gitemno, spec) 조합 집합 생성
3. 차집합 연산으로 누락된 조합 찾기
4. 누락된 조합이 있으면 경고(warning) 발생

**제약 조건 미충족 시**:
- **경고(Warning)** 발생
- 프로그램은 계속 실행됨
- 해당 제품은 제품 마스터에 등록되지 않은 제품으로 간주

---

### 4.2 검증 2/5: GITEM-공정-순서 테이블

**메서드**: `_validate_operation_sequence()` (L105-L151)

**검증 기준**: `order_df` (주문 정보)

**검증 대상**: `operation_df` (공정 순서 정보)

**검증 목적**: 주문에 포함된 모든 제품의 공정 정보가 존재하고 올바른지 확인

**예상 데이터 형태**:
```
order_df:
  - gitemno (제품코드): 문자열

operation_df:
  - gitemno (제품코드): 문자열
  - proccode (공정코드): 문자열, 예) "P001", "P002"
  - procseq (공정순서): 정수, 1부터 시작하는 연속된 숫자
```

**제약 조건**:
1. 주문 데이터의 모든 제품코드가 공정 순서 테이블에 존재해야 함
2. 각 제품코드별 공정순서(procseq)는 1부터 시작하여 연속적이어야 함
   - 예) 올바른 경우: [1, 2, 3, 4]
   - 예) 잘못된 경우: [1, 3, 4] (2가 누락), [0, 1, 2] (0부터 시작)

**검증 로직**:
1. `order_df`에서 고유한 제품코드 추출
2. `operation_df`에서 고유한 제품코드 추출
3. 차집합 연산으로 누락된 제품코드 찾기 → 오류 발생
4. 각 제품코드별로:
   - 공정순서를 정렬
   - 1부터 시작하는 연속된 숫자인지 확인
   - 연속적이지 않으면 오류 발생
   - 정상이면 (제품코드, 공정코드) 쌍을 저장 (후속 검증에 사용)

**제약 조건 미충족 시**:
- **오류(Error)** 발생
- 검증 결과 `is_valid = False`
- 프로그램은 계속 실행되지만, 해당 제품은 스케줄링에서 제외될 가능성 높음
- 콘솔에 상세한 오류 메시지 출력

---

### 4.3 검증 3/5: 수율-GITEM등 테이블

**메서드**: `_validate_yield_data()` (L153-L186)

**검증 기준**: `order_df` (주문 정보)

**검증 대상**: `yield_df` (수율 정보)

**검증 목적**: 주문에 포함된 모든 제품의 수율 정보가 존재하는지 확인

**예상 데이터 형태**:
```
order_df:
  - gitemno (제품코드): 문자열

yield_df:
  - gitemno (제품코드): 문자열
  - yield (수율): 실수, 0.0 ~ 1.0 범위 (예: 0.95 = 95%)
  - gitemname (제품명): 문자열 (선택적)
```

**제약 조건**:
1. 주문 데이터의 모든 제품코드가 수율 테이블에 존재해야 함
2. 각 제품코드는 수율 테이블에 정확히 1개의 행만 존재해야 함 (중복 불가)

**검증 로직**:
1. 주문 데이터의 각 제품코드에 대해:
   - 수율 테이블에서 해당 제품코드 검색
   - 행 개수 확인
2. 행 개수가 0개인 경우 → 오류 발생
3. 행 개수가 2개 이상인 경우 → 경고 발생 (중복 제거 단계에서 첫 번째 행만 유지)

**제약 조건 미충족 시**:
- **누락 (행 개수 = 0)**:
  - 오류(Error) 발생
  - 검증 결과 `is_valid = False`
  - 해당 제품은 수율 정보가 없어 생산 길이 계산 불가
  
- **중복 (행 개수 > 1)**:
  - 경고(Warning) 발생
  - 프로그램은 계속 실행
  - `clean_duplicates()` 메서드에서 첫 번째 행만 자동으로 유지

---

### 4.4 검증 4/5: 라인스피드-GITEM등 테이블

**메서드**: `_validate_linespeed_data()` (L188-L230)

**검증 기준**: 검증 2에서 추출한 `gitem_proccode_pairs` (제품코드, 공정코드) 쌍

**검증 대상**: `linespeed_df` (라인스피드 정보)

**검증 목적**: 주문 제품의 모든 공정에 대한 라인스피드 정보가 존재하는지 확인

**예상 데이터 형태**:
```
linespeed_df:
  - gitemno (제품코드): 문자열
  - proccode (공정코드): 문자열
  - machineno (기계코드): 문자열, 예) "C2010", "C2250"
  - linespeed (라인스피드): 실수, 단위: m/h (미터/시간)
```

**제약 조건**:
1. 검증 2에서 추출한 모든 (제품코드, 공정코드) 쌍이 라인스피드 테이블에 존재해야 함
2. 각 (제품코드, 공정코드) 쌍은 라인스피드 테이블에 정확히 1개의 행만 존재해야 함

**검증 로직**:
1. 검증 2에서 저장된 `gitem_proccode_pairs` 집합 사용
2. 각 (제품코드, 공정코드) 쌍에 대해:
   - 라인스피드 테이블에서 해당 쌍 검색
   - 행 개수 확인
3. 행 개수가 0개인 경우 → 오류 발생
4. 행 개수가 2개 이상인 경우 → 경고 발생

**제약 조건 미충족 시**:
- **누락 (행 개수 = 0)**:
  - 오류(Error) 발생
  - 검증 결과 `is_valid = False`
  - 해당 제품-공정 조합은 생산 속도를 알 수 없어 작업 시간 계산 불가
  
- **중복 (행 개수 > 1)**:
  - 경고(Warning) 발생
  - `clean_duplicates()` 메서드에서 첫 번째 행만 자동으로 유지

**특이사항**:
- 검증 2가 실패한 경우 (gitem_proccode_pairs가 비어있는 경우), 이 검증은 건너뜀

**JSON 결과 형식**:

누락된 경우 (미존재):
```json
{
  "table_name": "tb_linespeed",
  "severity": "error",
  "columns": ["gitemno", "proccode"],
  "constraint": "existence",
  "issue_type": "missing",
  "values": {
    "gitemno": "31600",
    "proccode": "20902"
  },
  "action_taken": "none"
}
```

중복된 경우:
```json
{
  "table_name": "tb_linespeed",
  "severity": "warning",
  "columns": ["gitemno", "proccode"],
  "constraint": "uniqueness",
  "issue_type": "duplicate",
  "duplicate_count": 2,
  "values": {
    "gitemno": "31600",
    "proccode": "20902"
  },
  "action_taken": "keep_first"
}
```

전체 검증 결과 구조:
```json
{
  "validation_summary": {
    "table_name": "tb_linespeed",
    "is_valid": false,
    "total_errors": 5,
    "total_warnings": 13
  },
  "issues": [
    {
      "table_name": "tb_linespeed",
      "severity": "warning",
      "columns": ["gitemno", "proccode"],
      "constraint": "uniqueness",
      "issue_type": "duplicate",
      "duplicate_count": 2,
      "values": {
        "gitemno": "31600",
        "proccode": "20902"
      },
      "action_taken": "keep_first"
    },
    {
      "table_name": "tb_linespeed",
      "severity": "error",
      "columns": ["gitemno", "proccode"],
      "constraint": "existence",
      "issue_type": "missing",
      "values": {
        "gitemno": "25000",
        "proccode": "20500"
      },
      "action_taken": "none"
    }
  ]
}
```

---

### 4.5 검증 5/5: 배합액정보 테이블

**메서드**: `_validate_chemical_data()` (L232-L274)

**검증 기준**: 검증 2에서 추출한 `gitem_proccode_pairs` (제품코드, 공정코드) 쌍

**검증 대상**: `chemical_df` (배합액 정보)

**검증 목적**: 주문 제품의 공정에 필요한 배합액 정보가 올바른지 확인

**예상 데이터 형태**:
```
chemical_df:
  - gitemno (제품코드): 문자열
  - proccode (공정코드): 문자열
  - che1 (배합코드1): 문자열, 예) "CH001"
  - che2 (배합코드2): 문자열 (선택적)
```

**제약 조건**:
1. 검증 2에서 추출한 (제품코드, 공정코드) 쌍이 배합액 테이블에 존재하는 것이 권장됨
   - 단, 배합액이 필요 없는 공정도 있을 수 있으므로 누락은 경고로 처리
2. 각 (제품코드, 공정코드) 쌍은 배합액 테이블에 최대 1개의 행만 존재해야 함 (중복 불가)

**검증 로직**:
1. 검증 2에서 저장된 `gitem_proccode_pairs` 집합 사용
2. 각 (제품코드, 공정코드) 쌍에 대해:
   - 배합액 테이블에서 해당 쌍 검색
   - 행 개수 확인
3. 행 개수가 0개인 경우 → 경고 발생 (배합액이 필요 없는 공정일 수 있음)
4. 행 개수가 2개 이상인 경우 → 오류 발생

**제약 조건 미충족 시**:
- **누락 (행 개수 = 0)**:
  - 경고(Warning) 발생
  - 프로그램은 계속 실행
  - 해당 공정은 배합액 없이 진행 (배합액이 필요 없는 공정으로 간주)
  
- **중복 (행 개수 > 1)**:
  - 오류(Error) 발생
  - 검증 결과 `is_valid = False`
  - 어떤 배합액을 사용해야 할지 명확하지 않음

**특이사항**:
- 검증 2가 실패한 경우, 이 검증은 건너뜀
- 배합액 누락은 오류가 아닌 경고로 처리 (배합액이 필요 없는 공정 존재 가능)

---

## 5. 중복 데이터 제거

### 5.1 clean_duplicates() 메서드

**위치**: `src/validation/validator.py` (L293-L353)

**처리 대상**:
1. 라인스피드 데이터 (`linespeed_df`)
2. 수율 데이터 (`yield_df`)

**처리 로직**:

#### 라인스피드 중복 제거
```python
# 완전히 동일한 행 제거 (모든 컬럼 값이 같은 경우)
linespeed_cleaned = linespeed_df.drop_duplicates(keep='first')
```
- 첫 번째 행만 유지, 나머지 중복 행 삭제
- 중복된 (제품코드, 공정코드) 쌍 목록 출력

#### 수율 중복 제거
```python
# 제품코드(와 제품명) 기준으로 중복 제거
subset_cols = [gitemno, gitemname] if gitemname exists else [gitemno]
yield_cleaned = yield_df.drop_duplicates(subset=subset_cols, keep='first')
```
- 제품코드 기준으로 첫 번째 행만 유지
- 중복된 제품코드 목록 출력

---

## 6. 검증 결과 처리

### 6.1 검증 결과 구조

```python
validation_result = {
    'is_valid': bool,  # True: 모든 검증 통과, False: 오류 발생
    'errors': List[str],  # 오류 메시지 리스트
    'warnings': List[str],  # 경고 메시지 리스트
    'gitem_proccode_pairs': Set[Tuple[str, str]]  # (제품코드, 공정코드) 쌍 집합
}
```

### 6.2 검증 결과에 따른 처리

**src/validation/__init__.py L78-L87**:

```python
if not validation_result['is_valid']:
    print("\n" + "!"*80)
    print(f"⚠️  데이터 검증에서 {len(validation_result['errors'])}개의 문제가 발견되었습니다.")
    print("⚠️  아래 문제들을 확인하고 필요시 원본 데이터를 수정하세요.")
    print("!"*80)
else:
    print("\n" + "="*80)
    print("✅ 데이터 검증 완료: 모든 검증 통과!")
    print("="*80 + "\n")
```

**처리 방식**:
- 검증 실패 시에도 프로그램은 중단되지 않음
- 사용자에게 문제를 알리고, 2단계(데이터 변환)로 진행
- 문제가 있는 데이터는 후속 단계에서 자동으로 필터링되거나 오류 발생 가능

---

## 7. 정제된 데이터 반환

### 7.1 cleaned_data 구조

```python
cleaned_data = {
    'order_df': order_df,  # 원본 주문 데이터 (변경 없음)
    'linespeed_df': linespeed_cleaned,  # 중복 제거된 라인스피드
    'yield_df': yield_cleaned,  # 중복 제거된 수율
    'operation_df': operation_df,  # 원본 공정 순서 (변경 없음)
    'chemical_df': chemical_df  # 원본 배합액 정보 (변경 없음)
}
```

### 7.2 후속 처리

정제된 데이터는 **2단계: 데이터 변환 (ProductionDataPreprocessor)**로 전달되어:
- 스케줄링에 필요한 형태로 변환
- 피벗 테이블 생성
- 컬럼명 표준화
- 데이터 타입 변환

---

## 8. 요약

### 검증 단계별 요약

| 검증 단계 | 검증 대상 | 제약 조건 | 실패 시 처리 |
|---------|---------|---------|------------|
| 1. 제품군-GITEM-SITEM | (제품코드, 규격) 조합 | 주문의 모든 조합이 마스터에 존재 | 경고 (계속 진행) |
| 2. GITEM-공정-순서 | 제품코드, 공정순서 | 제품코드 존재, 공정순서 연속성 | 오류 (is_valid=False) |
| 3. 수율-GITEM등 | 제품코드 | 제품코드 존재, 중복 없음 | 오류/경고 |
| 4. 라인스피드-GITEM등 | (제품코드, 공정코드) 쌍 | 쌍 존재, 중복 없음 | 오류/경고 |
| 5. 배합액정보 | (제품코드, 공정코드) 쌍 | 중복 없음 (누락 허용) | 경고/오류 |

### 핵심 포인트

1. **검증은 필수가 아님**: `validate=False`로 설정하면 검증 건너뛰기 가능
2. **검증 실패 시에도 계속 진행**: 프로그램이 중단되지 않고 경고/오류 메시지만 출력
3. **중복 데이터 자동 제거**: 라인스피드와 수율의 중복은 자동으로 첫 번째 행만 유지
4. **계층적 검증**: 검증 2의 결과를 검증 4, 5에서 활용
5. **오류 vs 경고**: 
   - 오류: 스케줄링에 필수적인 데이터 누락 (is_valid=False)
   - 경고: 데이터 품질 문제이지만 진행 가능 (is_valid는 영향 없음)
