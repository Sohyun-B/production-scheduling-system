# 생산 스케줄링 시스템 모듈 입출력 명세

## 0. 데이터 로딩 (Excel Input)

### 위치

`main.py:32-50`

### 입력

**파일**: `data/input/생산계획 필요기준정보 내역-Ver4.xlsx`

**시트별 읽기 설정**:

```python
order_df = pd.read_excel(input_file, sheet_name="PO정보", skiprows=1)
gitem_sitem_df = pd.read_excel(input_file, sheet_name="제품군-GITEM-SITEM", skiprows=2)
linespeed_df = pd.read_excel(input_file, sheet_name="라인스피드-GITEM등", skiprows=5)
operation_df = pd.read_excel(input_file, sheet_name="GITEM-공정-순서", skiprows=1)
yield_df = pd.read_excel(input_file, sheet_name="수율-GITEM등", skiprows=5)
chemical_df = pd.read_excel(input_file, sheet_name="배합액정보", skiprows=5)
operation_delay_df = pd.read_excel(input_file, sheet_name="공정교체시간", skiprows=1)
width_change_df = pd.read_excel(input_file, sheet_name="폭변경", skiprows=1)
```

### 설정 파라미터

```python
base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
window_days = config.constants.WINDOW_DAYS
linespeed_period = config.constants.LINESPEED_PERIOD
yield_period = config.constants.YIELD_PERIOD
buffer_days = config.constants.BUFFER_DAYS
```

### 출력

- `order_df` (pd.DataFrame)
- `gitem_sitem_df` (pd.DataFrame)
- `linespeed_df` (pd.DataFrame)
- `operation_df` (pd.DataFrame)
- `yield_df` (pd.DataFrame)
- `chemical_df` (pd.DataFrame)
- `operation_delay_df` (pd.DataFrame)
- `width_change_df` (pd.DataFrame)

---

## 1. Validation - 데이터 유효성 검사 및 전처리

### 함수명

`preprocess_production_data()`

### 위치

`src/validation/__init__.py:13`
`main.py:54-68` (호출)

### 입력

```python
preprocess_production_data(
    order_df=order_df,                      # PO정보 시트
    linespeed_df=linespeed_df,              # 라인스피드-GITEM등 시트
    operation_df=operation_df,              # GITEM-공정-순서 시트
    yield_df=yield_df,                      # 수율-GITEM등 시트
    chemical_df=chemical_df,                  # 배합액정보 시트
    operation_delay_df=operation_delay_df,  # 공정교체시간 시트
    width_change_df=width_change_df,        # 폭변경 시트
    gitem_sitem_df=gitem_sitem_df,          # 제품군-GITEM-SITEM 시트 (검증용)
    linespeed_period=linespeed_period,      # 라인스피드 집계 기간 ('6_months', '1_year', '3_months')
    yield_period=yield_period,              # 수율 집계 기간 ('6_months', '1_year', '3_months')
    buffer_days=buffer_days,                # 납기 여유일자 (int)
    validate=True,                          # 유효성 검사 수행 여부 (bool)
    save_output=False                       # python_input.xlsx 저장 여부 (bool)
)
```

### 출력

`processed_data` (Dict[str, pd.DataFrame]):

```python
{
    'order_data': pd.DataFrame,           # 전처리된 주문 데이터
    'linespeed': pd.DataFrame,            # 라인스피드 피벗 테이블
    'operation_types': pd.DataFrame,      # 공정 타입 정보
    'operation_sequence': pd.DataFrame,   # 공정 순서 정보
    'yield_data': pd.DataFrame,           # 수율 정보
    'machine_master_info': pd.DataFrame,  # 설비 마스터 정보
    'chemical_data': pd.DataFrame,         # 배합액 정보
    'operation_delay': pd.DataFrame,      # 공정교체시간
    'width_change': pd.DataFrame,         # 폭변경 정보
    'machine_limit': pd.DataFrame,        # 기계 제한 정보 (빈 DataFrame)
    'machine_allocate': pd.DataFrame,     # 기계 할당 정보 (빈 DataFrame)
    'machine_rest': pd.DataFrame,         # 기계 중단시간 정보 (빈 DataFrame)
    'validation_result': dict or None     # 검증 결과
}
```

### 비고

- 이 모듈은 원본 Excel 데이터를 표준화된 형식으로 변환
- `validate=True`일 때 데이터 유효성 검사 수행
- `save_output=True`일 때 중간 결과를 `python_input.xlsx`로 저장 가능 (선택 사항)
- machine_limit, machine_allocate, machine_rest는 현재로서는 validation에서 빈 테이블을 생성하는 형식이지만 사용자 입력 받는 형식으로 변경 필요

---

## 2. Order Sequencing - 주문 시퀀스 생성

### 함수명

`generate_order_sequences()`

### 위치

`src/order_sequencing/__init__.py:8`
`main.py:95-96` (호출)

### 입력

```python
generate_order_sequences(
    order,                          # processed_data['order_data']
    operation_seperated_sequence,   # processed_data['operation_sequence']
    operation_types,                # processed_data['operation_types']
    machine_limit,                  # processed_data['machine_limit']
    machine_allocate,               # processed_data['machine_allocate']
    linespeed,                      # processed_data['linespeed']
    chemical_data                    # processed_data['chemical_data']
)
```

### 출력

```python
(
    sequence_seperated_order,  # pd.DataFrame: 공정별 분리된 주문 데이터
    linespeed,                 # pd.DataFrame: 업데이트된 라인스피드 (제약 반영)
    unable_gitems,             # list: 생산 불가능한 GITEM 목록
    unable_order,              # pd.DataFrame: 생산 불가능한 주문 데이터
    unable_details             # list: 불가능한 GITEM과 공정명 상세 정보
)
```

---

## 3. Yield Prediction - 수율 예측

### 함수명

`yield_prediction()`

### 위치

`src/yield_management/__init__.py:4`
`main.py:103-105` (호출)

### 입력

```python
yield_prediction(
    yield_data,              # processed_data['yield_data']
    sequence_seperated_order # generate_order_sequences() 출력
)
```

### 출력

`sequence_seperated_order` (pd.DataFrame): 입력과 동일한 DataFrame에 컬럼 추가/수정

---

## 4. DAG Creation - DAG 시스템 생성

### 함수명

`create_complete_dag_system()`

### 위치

`src/dag_management/__init__.py:10`
`main.py:109-110` (호출)

### 입력

```python
create_complete_dag_system(
    sequence_seperated_order,  # yield_prediction() 출력
    linespeed,                 # processed_data['linespeed']
    machine_master_info        # processed_data['machine_master_info']
)
```

### 출력

```python
(
    dag_df,         # pd.DataFrame: DAG 데이터프레임 (ID, depth, children 등)
    opnode_dict,    # dict: 노드별 상세 정보 (CHEMICAL_LIST, SELECTED_CHEMICAL 포함)
    manager,        # DAGGraphManager: DAG 그래프 관리자 인스턴스
    machine_dict,   # dict: 기계별 작업 가능 노드 리스트
    merged_df       # pd.DataFrame: 주문-공정 병합 테이블
)
```

---

## 5. Scheduling - 스케줄링 실행

### 위치

`main.py:115-160`

### 입력

```python
# 이전 단계에서 전달받는 데이터
dag_df                    # pd.DataFrame: create_complete_dag_system() 출력
opnode_dict              # dict: create_complete_dag_system() 출력
manager                  # DAGGraphManager: create_complete_dag_system() 출력
machine_dict             # dict: create_complete_dag_system() 출력
sequence_seperated_order # pd.DataFrame: yield_prediction() 출력
machine_master_info      # pd.DataFrame: processed_data['machine_master_info']
operation_delay_df       # pd.DataFrame: processed_data['operation_delay']
width_change_df          # pd.DataFrame: processed_data['width_change']
machine_rest             # pd.DataFrame: processed_data['machine_rest']
base_date                # datetime: 기준 시간
window_days              # int: 윈도우 크기 (config.constants.WINDOW_DAYS)
```

### 출력

```python
(
    result,      # pd.DataFrame: 스케줄링 결과 (모든 노드의 시작/종료 시간, 할당 기계)
    scheduler    # Scheduler: 스케줄러 인스턴스 (results processing에서 사용)
)
```

### 비고

- 이 모듈이 가장 많은 시간을 소요함 (전체 실행 시간의 60-85%)
- 배합액 최적화가 포함된 SetupMinimizedStrategy 사용

---

## 6. Results Processing - 결과 후처리

### 함수명

`create_results()`

### 위치

`src/results/__init__.py:14`
`main.py:166-174` (호출)

### 입력

```python
create_results(
    raw_scheduling_result=result,          # DispatchPriorityStrategy.execute() 출력
    merged_df=merged_df,                   # create_complete_dag_system() 출력
    original_order=order,                  # processed_data['order_data']
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    machine_master_info=machine_master_info,  # processed_data['machine_master_info']
    base_date=base_date,                   # datetime 객체
    scheduler=scheduler                    # Scheduler 인스턴스
)
```

### 출력

`final_results` (dict):

```python
{
    # Makespan 정보
    'actual_makespan': float,      # 실제 makespan (depth -1 제외)
    'total_makespan': float,       # 전체 makespan

    # 지각 처리 결과
    'new_output_final_result': pd.DataFrame,  # 최종 결과 DataFrame
    'late_days_sum': int,                     # 총 지각 일수
    'late_products': pd.DataFrame,            # 지각 제품 목록
    'late_po_numbers': list,                  # 지각 주문번호 리스트

    # 병합 처리 결과
    'merged_result': pd.DataFrame,  # 주문-공정-스케줄 통합 데이터
    'order_info': pd.DataFrame,     # 주문 정보

    # 기계 정보 결과
    'machine_info': pd.DataFrame,   # 기계별 작업 스케줄

    # 주문 요약
    'order_summary': pd.DataFrame,  # 주문 생산 요약본 (PoNo, GITEM, 납기, 종료일, 지각일수)

    # 분석 결과
    'gap_analyzer': GapAnalyzer,         # 간격 분석기 인스턴스
    'detailed_gaps': pd.DataFrame,       # 상세 간격 분석 결과
    'machine_summary': pd.DataFrame,     # 기계별 간격 요약
    'gantt_filename': str                # 간트차트 파일 경로
}
```

### 비고

- 이 모듈이 최종 사용자에게 보여질 모든 결과 생성
- Excel, PNG, JSON 파일 생성
- CSV 파일 생성은 디버깅용으로 추후 삭제 예정

## 7. 파일 저장 (Final Output)

### 위치

`main.py:191-219`

### 저장되는 파일

#### 7-1. 원본 결과

**`data/output/result.xlsx`**

- `result` DataFrame 그대로 저장
- 모든 노드의 스케줄링 상세 정보

#### 7-2. 최종 결과 Excel

**`data/output/0829 스케줄링결과.xlsx`**

```python
with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
    final_results['order_summary'].to_excel(writer, sheet_name="주문_생산_요약본", index=False)
    final_results['order_info'].to_excel(writer, sheet_name="주문_생산_정보", index=False)
    final_results['machine_info'].to_excel(writer, sheet_name="호기_정보", index=False)
    final_results['detailed_gaps'].to_excel(writer, sheet_name="지연시간분석", index=False)
    final_results['machine_summary'].to_excel(writer, sheet_name="지연시간호기요약", index=False)
```

#### 7-3. 간트차트

**`data/output/level4_gantt.png`**

- GanttChartGenerator에서 자동 생성
- ***

## 엔드포인트 설계

### 옵션 1: 단일 엔드포인트

```
POST /api/scheduling/run
- 전체 파이프라인을 한 번에 실행
- 입력: Excel 파일 업로드 + 설정 파라미터
- 출력: 최종 결과 파일들 (Excel, PNG, JSON)
```

### 옵션 2: 단계별 엔드포인트

```
POST /api/scheduling/1-validation        → processed_data
POST /api/scheduling/2-order-sequencing  → sequence_seperated_order
POST /api/scheduling/3-yield-prediction  → sequence_seperated_order (updated)
POST /api/scheduling/4-dag-creation      → dag_df, opnode_dict, manager, machine_dict, merged_df
POST /api/scheduling/5-scheduling        → result
POST /api/scheduling/6-results           → final_results
```

### 옵션 3: 하이브리드

```
POST /api/scheduling/preprocess          → 1+2+3+4 통합 (데이터 준비)
POST /api/scheduling/schedule            → 5 (스케줄링 실행, 시간이 가장 많이 소모되는 단계)
POST /api/scheduling/postprocess         → 6 (결과 처리)
```
