# 생산 스케줄링 시스템 모듈 입출력 명세

## 개요
이 문서는 `main.py`의 `run_level4_scheduling()` 함수 내에서 호출되는 각 모듈의 입출력을 정의합니다.
백엔드 서비스(`python_Server/app/services/python_engine_service`)에서 각 모듈을 개별 엔드포인트로 호출할 수 있도록 명세합니다.

---

## 0. 데이터 로딩 (Excel Inputs)

### 위치
`main.py:31-52`

### 입력
**파일 1**: `data/input/생산계획 필요기준정보 내역-Ver4.xlsx`

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

**파일 2**: `data/input/AGING내역.xlsx`

```python
aging_df = pd.read_excel("data/input/AGING내역.xlsx", sheet_name="DB AGING 테이블", skiprows=1)
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
- `aging_df` (pd.DataFrame)

---

## 1. Validation - 데이터 유효성 검사 및 전처리

### 함수명
`preprocess_production_data()`

### 위치
`src/validation/__init__.py:13`
`main.py:105-147` (호출)

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

### 처리 과정
1. **DataValidator**: 데이터 유효성 검사 및 중복 제거
   - 제품군-GITEM-SITEM 정합성 검증
   - 공정, 수율, 라인스피드 데이터의 GITEM 존재성 검증
   - 배합액 데이터 검증

2. **ProductionDataPreprocessor**: 데이터 변환
   - 주문 데이터 전처리 및 납기 여유일자 반영
   - 라인스피드 피벗 테이블 생성
   - 공정 타입 및 순서 정보 생성
   - 수율 데이터 정제
   - 배합액 정보 변환
   - 설비 마스터 정보 생성
   - 빈 데이터프레임 생성 (machine_limit, machine_allocate, machine_rest)

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

---

## 2. Order Sequencing - 주문 시퀀스 생성

### 함수명
`generate_order_sequences()`

### 위치
`src/order_sequencing/__init__.py:8`
`main.py:150-151` (호출)

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

### 처리 과정
1. **OrderPreprocessor**: 주문 전처리
   - `seperate_order_by_month()`: 납기일 기준 월별 주문 분리
   - `same_order_groupby()`: 동일 주문 통합 (배치 효율화)

2. **SequencePreprocessor**: 공정 시퀀스 생성
   - `create_sequence_seperated_order()`: 주문별 상세 공정 순서 생성

3. **OperationMachineLimit**: 기계 제약 처리
   - `operation_machine_limit()`: 기계 제약 조건 적용
   - `operation_machine_exclusive()`: 강제 할당 처리

4. **FabricCombiner**: 폭 조합 처리
   - `combine_fabric_width()`: 너비 조합 로직 적용

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

### `sequence_seperated_order` 주요 컬럼
- `PoNo`, `GitemNo`, `PROCCODE`, `PROCSEQ`, `PROCNAME`, `ProcGbn`
- `production_length`, `fabric_width`
- `DUEDATE`, `ID` (DAG 노드 ID용)
- 기타 공정 정보

### 비고
- `unable_gitems`, `unable_order`는 생산 불가능한 항목을 사용자에게 알리기 위한 정보
- main.py에서 통계 출력 용도로 사용됨 (실제 수행한 order 수 계산 등)

---

## 3. Yield Prediction - 수율 예측

### 함수명
`yield_prediction()`

### 위치
`src/yield_management/__init__.py:4`
`main.py:157-160` (호출)

### 입력
```python
yield_prediction(
    yield_data,              # processed_data['yield_data']
    sequence_seperated_order # generate_order_sequences() 출력
)
```

### 처리 과정
1. GITEM을 문자열로 변환
2. GITEM 기준으로 yield_data와 sequence_seperated_order 병합 (left join)
3. `product_ratio = 1 / yield` 계산
4. `original_production_length` = 원본 `production_length` 백업
5. `production_length` = `original_production_length * product_ratio` (수율 반영)
6. 임시 컬럼 제거 (yield, product_ratio)

### 출력
`sequence_seperated_order` (pd.DataFrame):
- 입력과 동일한 DataFrame에 다음 컬럼 추가/수정:
  - `original_production_length`: 원본 생산길이
  - `production_length`: 수율 반영 생산길이

### 비고
- 수율이 없는 GITEM은 원본 생산길이 유지
- 수율 = 0.9 → product_ratio = 1.11 → 생산길이 11% 증가

---

## 3.5. Aging 요구사항 파싱 - NEW

### 함수명
`parse_aging_requirements()`

### 위치
`src/dag_management/dag_dataframe.py`
`main.py:164-166` (호출)

### 입력
```python
parse_aging_requirements(
    aging_df,                   # Aging 데이터 (gitemno, proccode, aging_time 포함)
    sequence_seperated_order    # 주문 공정 분리 데이터
)
```

### 처리 과정
1. **Aging Map 생성**: Aging 데이터에서 맵 생성
2. **형식**: `{(GitemNo, ProcGbn): aging_time * 2}` 딕셔너리
3. **에이징 시간**: 특정 공정 완료 후 다음 공정 시작 전 필수 대기 시간

### 출력
```python
aging_map = {
    (GitemNo1, ProcGbn1): aging_time1,
    (GitemNo2, ProcGbn2): aging_time2,
    ...
}
```

### 비고
- aging_df=None 또는 빈 DataFrame 전달 시 빈 딕셔너리 반환 (모든 노드의 AGING_TIME=0)

---

## 4. DAG Creation - DAG 시스템 생성

### 함수명
`create_complete_dag_system()`

### 위치
`src/dag_management/__init__.py:75`
`main.py:169-170` (호출)

### 입력
```python
create_complete_dag_system(
    sequence_seperated_order,  # yield_prediction() 출력
    linespeed,                 # processed_data['linespeed']
    machine_master_info,       # processed_data['machine_master_info']
    aging_map=aging_map        # parse_aging_requirements() 출력 (선택 사항, None이면 모든 aging_time=0)
)
```

### 처리 과정
0. **Aging Map 활용** (aging_map이 제공된 경우)
   - parse_aging_requirements()에서 생성된 aging_map 직접 전달
   - `{(GitemNo, ProcGbn): aging_time}` 형식
   - aging_map=None이면 빈 딕셔너리로 처리되어 모든 노드의 AGING_TIME=0

1. **DAGDataFrameCreator**: DAG 데이터프레임 생성
   - `create_full_dag()`: 전체 DAG 구조 생성 (depth, children 계산)

2. **NodeDictCreator**: 노드 딕셔너리 생성
   - `create_opnode_dict()`: 작업 노드 정보 딕셔너리 생성
   - CHEMICAL_LIST, SELECTED_CHEMICAL(초기값 None), AGING_TIME 포함

3. **DAGGraphManager**: DAG 그래프 구축
   - `build_from_dataframe()`: networkx 그래프 구조 생성 및 의존성 관리

4. **MachineDict**: 기계 정보 딕셔너리
   - `create_machine_dict()`: 기계별 작업 가능 노드 리스트 생성

5. **MergeProcessor**: 데이터 병합
   - `merge_order_operation()`: 주문-공정 정보 통합

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

### `opnode_dict` 구조 예시
```python
{
    "node_id": {
        "OPERATION_ORDER": 1,
        "OPERATION_CODE": "P001",
        "OPERATION_CLASSIFICATION": "코팅",
        "FABRIC_WIDTH": 1500,
        "CHEMICAL_LIST": ("A", "B"),      # 사용 가능한 배합액 튜플
        "PRODUCTION_LENGTH": 1000,
        "SELECTED_CHEMICAL": None,        # 초기값 None (스케줄링 시 설정)
        "AGING_TIME": 96.0               # 에이징 시간 (없으면 0)
    }
}
```

---

## 5. Scheduling - 스케줄링 실행

### 함수명
`run_scheduler_pipeline()`

### 위치
`src/scheduler/__init__.py:89`
`main.py:183-195` (호출)

### 입력
```python
result, scheduler = run_scheduler_pipeline(
    dag_df=dag_df,                              # create_complete_dag_system() 출력
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    width_change_df=width_change_df,            # processed_data['width_change']
    machine_master_info=machine_master_info,    # processed_data['machine_master_info']
    opnode_dict=opnode_dict,                    # create_complete_dag_system() 출력
    operation_delay_df=operation_delay_df,      # processed_data['operation_delay']
    machine_dict=machine_dict,                  # create_complete_dag_system() 출력
    machine_rest=machine_rest,                  # processed_data['machine_rest']
    base_date=base_date,                        # 기준 날짜 (datetime)
    manager=manager,                            # create_complete_dag_system() 출력
    window_days=window_days                     # 윈도우 크기 (int)
)
```

### 처리 과정
이 함수는 스케줄링 준비부터 실행까지 전체 파이프라인을 자동으로 처리합니다:

1. **디스패치 규칙 생성** (`create_dispatch_rule`)
   - dag_df와 sequence_seperated_order 기반으로 우선순위 생성
   - 우선순위 정렬된 노드 ID 리스트 생성

2. **DelayProcessor 초기화**
   - 공정 교체 지연시간 설정
   - 폭 변경 지연시간 설정
   - 배합액 교체 지연시간 설정

3. **Scheduler 초기화 및 자원 할당**
   - 기계별 자원 할당 (`allocate_resources`)
   - 기계 다운타임 적용 (`allocate_machine_downtime`)

4. **스케줄링 실행** (`DispatchPriorityStrategy.execute`)
   - **윈도우 기반 동적 스케줄링**: 우선순위 순으로 window_days만큼 작업 선택
   - **SetupMinimizedStrategy**: 배합액 최적화 및 같은 배합액 작업 연속 스케줄링
   - **작업 할당**: OptimalMachineStrategy 또는 ForcedMachineStrategy로 기계 선택
   - **시간 계산**: 선행 작업 완료, 기계 가용 시간, 지연시간 모두 반영

### 출력
```python
(
    result,     # pd.DataFrame: 스케줄링 결과 (node_start, node_end, allocated_machine 등)
    scheduler   # Scheduler 인스턴스 (후처리에서 사용)
)
```

#### `result` 주요 컬럼
- `ID`: 노드 ID
- `node_start`: 작업 시작 시간 (time slot)
- `node_end`: 작업 종료 시간 (time slot)
- `machine`: 할당된 기계 인덱스
- `depth`: DAG depth
- 기타 노드 정보

### 비고
- 이 함수는 wrapper function으로, 복잡한 스케줄링 파이프라인을 단순하게 호출 가능
- 배합액 최적화가 포함된 SetupMinimizedStrategy 자동 적용
- opnode_dict의 SELECTED_CHEMICAL가 이 단계에서 동적으로 설정됨
- 상세 알고리즘은 `src/scheduler/CHEMICAL_LOGIC.md` 참조

---

## 6. Results Processing - 결과 후처리

### 함수명
`create_results()`

### 위치
`src/results/__init__.py:14`
`main.py:202-210` (호출)

### 입력
```python
create_results(
    raw_scheduling_result=result,          # run_scheduler_pipeline() 출력
    merged_df=merged_df,                   # create_complete_dag_system() 출력
    original_order=order,                  # processed_data['order_data']
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    machine_master_info=machine_master_info,  # processed_data['machine_master_info']
    base_date=base_date,                   # datetime 객체
    scheduler=scheduler                    # run_scheduler_pipeline() 출력
)
```

### 처리 과정

1. **DataCleaner**: 가짜 작업 제거 및 makespan 계산
   - depth -1 노드 제거
   - 실제 makespan, 전체 makespan 계산

2. **LateProcessor**: 납기 지연 분석
   - 지각 주문 식별
   - 지각 일수 계산
   - 지각 주문번호 리스트 생성

3. **MergeProcessor**: 데이터 병합
   - 주문-공정-스케줄 정보 통합
   - CSV 파일 생성 (추후 삭제 예정):
     - `merged_result.csv`
     - `order_info.csv`
     - `지각작업처리결과.csv`

4. **GapAnalysisProcessor**: 간격 분석
   - 작업 간 유휴 시간 분석
   - 지연시간 세부 분류:
     - 대기 시간
     - 공정 교체 시간
     - 폭 변경 시간
     - 배합액 교체 시간
   - 기계별 간격 요약

5. **MachineProcessor**: 기계 스케줄 처리
   - 읽기 쉬운 기계 스케줄 생성
   - 기계별 정보 정리

6. **GanttChartGenerator**: 간트차트 생성
   - PNG 형식 시각화
   - 기계별 작업 타임라인 표시
   - 간격(gap) 표시 옵션

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

---

## 7. 파일 저장 (Final Output)

### 위치
`main.py:227-244`

### 저장되는 파일 (main.py:227-244 참조)

#### 7-1. 원본 결과
**`data/output/result.xlsx`** (Line 227-229)
- `result` DataFrame 그대로 저장
- 모든 노드의 스케줄링 상세 정보

#### 7-2. 최종 결과 Excel
**`data/output/0829 스케줄링결과.xlsx`** (Line 233-241)
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
- GanttChartGenerator에서 자동 생성 (final_results['gantt_filename'] 참조)

---

## 데이터 흐름 요약

```
┌─────────────────────────────────────────────────────────────────┐
│  0. Excel 데이터 로딩                                            │
│     ├─ 생산계획 필요기준정보 내역-Ver4.xlsx (8개 시트)            │
│     └─ AGING내역.xlsx (1개 시트)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  1. preprocess_production_data()                                │
│     ├─ DataValidator: 유효성 검사 및 중복 제거                   │
│     └─ ProductionDataPreprocessor: 표준 형식 변환                │
│     → processed_data (dict)                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. generate_order_sequences()                                  │
│     ├─ 월별 주문 분리 및 통합                                     │
│     ├─ 공정 시퀀스 생성                                           │
│     ├─ 기계 제약 및 강제 할당                                     │
│     └─ 폭 조합 로직                                              │
│     → sequence_seperated_order, unable_gitems, unable_order     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. yield_prediction()                                          │
│     └─ 수율 기반 생산길이 조정                                    │
│     → sequence_seperated_order (updated)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. create_complete_dag_system()                                │
│     ├─ Aging Map 생성 (aging_df → aging_map)                    │
│     ├─ DAG 데이터프레임 생성                                      │
│     ├─ opnode_dict 생성 (CHEMICAL_LIST, AGING_TIME 포함)         │
│     ├─ DAG 그래프 구축 (aging_time 설정)                        │
│     └─ 기계 딕셔너리 생성                                         │
│     → dag_df, opnode_dict, manager, machine_dict, merged_df     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. run_scheduler_pipeline()                                    │
│     ├─ 디스패치 규칙 생성 (create_dispatch_rule)                 │
│     ├─ DelayProcessor 초기화                                     │
│     ├─ Scheduler 초기화 및 자원 할당                              │
│     └─ 스케줄링 실행 (DispatchPriorityStrategy)                  │
│        └─ SetupMinimizedStrategy: 배합액 최적화                  │
│     → (result, scheduler)                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. create_results()                                            │
│     ├─ DataCleaner: 가짜 작업 제거 및 makespan 계산              │
│     ├─ LateProcessor: 납기 지연 분석                             │
│     ├─ MergeProcessor: 데이터 병합                               │
│     ├─ GapAnalysisProcessor: 간격 분석                           │
│     ├─ MachineProcessor: 기계 스케줄 처리                         │
│     └─ GanttChartGenerator: 간트차트 생성                        │
│     → final_results (dict)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. 파일 저장                                                     │
│     ├─ result.xlsx: 원본 결과                                    │
│     ├─ 0829 스케줄링결과.xlsx: 최종 결과 (5개 시트)               │
│     └─ level4_gantt.png: 간트차트                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 엔드포인트 설계 권장사항

백엔드 서비스에서 각 모듈을 API 엔드포인트로 노출할 경우:

### 옵션 1: 단일 엔드포인트 (권장)
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
POST /api/scheduling/5-run-scheduler     → (result, scheduler)
POST /api/scheduling/6-results           → final_results
```

### 옵션 3: 하이브리드
```
POST /api/scheduling/preprocess          → 1+2+3 통합 (데이터 준비)
POST /api/scheduling/schedule            → 4+5 통합 (스케줄링 실행)
POST /api/scheduling/postprocess         → 6 (결과 처리)
```

---

## 주의사항

1. **데이터 직렬화**
   - pandas DataFrame은 JSON으로 직렬화 시 `df.to_dict('records')` 사용
   - datetime 객체는 ISO 8601 문자열로 변환

2. **메모리 관리**
   - 대용량 DataFrame 전달 시 메모리 사용량 주의
   - 필요시 파일 기반 전달 (임시 파일) 고려

3. **에러 처리**
   - 각 단계별 validation 실패 시 명확한 에러 메시지 반환
   - unable_gitems, unable_order 정보 사용자에게 전달

4. **성능**
   - 전체 파이프라인 실행 시간: 데이터 크기에 따라 수십 초 ~ 수 분
   - 단계별 실행 시 중간 데이터 캐싱 고려

5. **버전 관리**
   - 설정 파라미터 변경 시 API 버전 업데이트
   - 입출력 스키마 변경 시 문서 업데이트 필수
