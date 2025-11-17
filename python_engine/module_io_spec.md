# 생산 스케줄링 시스템 모듈 입출력 명세

## 개요
이 문서는 `main.py`의 `run_level4_scheduling()` 함수 내에서 호출되는 각 모듈의 입출력을 정의합니다.
백엔드 서비스(`python_Server/app/services/python_engine_service`)에서 각 모듈을 개별 엔드포인트로 호출할 수 있도록 명세합니다.

---

## 0. 데이터 로딩 (Excel Inputs)

### 위치
`main.py:26-93`

### 입력 파일

#### 파일 1: 생산계획 입력정보.xlsx
**경로**: `data/input/생산계획 입력정보.xlsx`

**시트별 읽기 설정**:
```python
order_df = pd.read_excel(input_file, sheet_name="tb_polist",
                         dtype={config.columns.GITEM: str},
                         parse_dates=[config.columns.DUE_DATE])

gitem_sitem_df = pd.read_excel(input_file, sheet_name="tb_itemspec",
                               dtype={config.columns.GITEM: str})

linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed",
                             dtype={config.columns.GITEM: str,
                                    config.columns.OPERATION_CODE: str})

operation_df = pd.read_excel(input_file, sheet_name="tb_itemproc",
                             dtype={config.columns.GITEM: str,
                                    config.columns.OPERATION_CODE: str})

yield_df = pd.read_excel(input_file, sheet_name="tb_productionyield",
                        dtype={config.columns.GITEM: str,
                               config.columns.OPERATION_CODE: str})

chemical_df = pd.read_excel(input_file, sheet_name="tb_chemical",
                            dtype={config.columns.GITEM: str,
                                   config.columns.OPERATION_CODE: str})

operation_delay_df = pd.read_excel(input_file, sheet_name="tb_changetime")

width_change_df = pd.read_excel(input_file, sheet_name="tb_changewidth")

aging_gitem = pd.read_excel(input_file, sheet_name="tb_agingtime_gitem",
                            dtype={config.columns.GITEM: str})

aging_gbn = pd.read_excel(input_file, sheet_name="tb_agingtime_gbn")
```

#### 파일 2: 글로벌 기계 제약조건
**경로**: `data/input/tb_commomconstraint.xlsx`
```python
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")
```

#### 파일 3: 시나리오 공정제약조건
**경로**: `data/input/시나리오_공정제약조건.xlsx`
```python
local_machine_limit = pd.read_excel("data/input/시나리오_공정제약조건.xlsx",
                                    sheet_name="machine_limit")

machine_allocate = pd.read_excel("data/input/시나리오_공정제약조건.xlsx",
                                 sheet_name="machine_allocate")

machine_rest = pd.read_excel("data/input/시나리오_공정제약조건.xlsx",
                             sheet_name="machine_rest",
                             parse_dates=[config.columns.MACHINE_REST_START,
                                         config.columns.MACHINE_REST_END])
```

#### 파일 4: 기계 마스터 정보
**경로**: `data/input/machine_master_info.xlsx`
```python
machine_master_info_df = pd.read_excel(machine_master_file,
                                       dtype={config.columns.MACHINE_CODE: str})
```

### 설정 파라미터
```python
base_date = datetime(config.constants.BASE_YEAR,
                    config.constants.BASE_MONTH,
                    config.constants.BASE_DAY)
window_days = config.constants.WINDOW_DAYS
linespeed_period = config.constants.LINESPEED_PERIOD
yield_period = config.constants.YIELD_PERIOD
```

### 출력
- `order_df` (pd.DataFrame): 주문 정보
- `gitem_sitem_df` (pd.DataFrame): 제품군-GITEM-SITEM 매핑
- `linespeed_df` (pd.DataFrame): 라인스피드 정보
- `operation_df` (pd.DataFrame): GITEM-공정-순서 정보
- `yield_df` (pd.DataFrame): 수율 정보
- `chemical_df` (pd.DataFrame): 배합액 정보
- `operation_delay_df` (pd.DataFrame): 공정교체시간
- `width_change_df` (pd.DataFrame): 폭변경 정보
- `aging_gitem`, `aging_gbn` (pd.DataFrame): 에이징 정보
- `global_machine_limit_raw` (pd.DataFrame): 글로벌 기계 제약조건
- `local_machine_limit` (pd.DataFrame): 로컬 기계 제약조건
- `machine_allocate` (pd.DataFrame): 기계 강제 할당 정보
- `machine_rest` (pd.DataFrame): 기계 다운타임 정보
- `machine_master_info_df` (pd.DataFrame): 기계 마스터 정보

---

## 1. Validation - 데이터 유효성 검사 및 전처리

### 함수명
`preprocess_production_data()`

### 위치
`src/validation/__init__.py:13`
`main.py:59-88` (호출)

### 입력
```python
processed_data = preprocess_production_data(
    order_df=order_df,                          # PO정보 (tb_polist)
    linespeed_df=linespeed_df,                  # 라인스피드 (tb_linespeed)
    operation_df=operation_df,                  # 공정-순서 (tb_itemproc)
    yield_df=yield_df,                          # 수율 (tb_productionyield)
    chemical_df=chemical_df,                    # 배합액 (tb_chemical)
    operation_delay_df=operation_delay_df,      # 공정교체시간 (tb_changetime)
    width_change_df=width_change_df,            # 폭변경 (tb_changewidth)
    gitem_sitem_df=gitem_sitem_df,              # 제품군-GITEM-SITEM (tb_itemspec)
    aging_gitem_df=aging_gitem,                 # 에이징-GITEM (tb_agingtime_gitem)
    aging_gbn_df=aging_gbn,                     # 에이징-구분 (tb_agingtime_gbn)
    global_machine_limit_df=global_machine_limit_raw,  # 글로벌 기계 제약
    linespeed_period=linespeed_period,          # 라인스피드 집계 기간
    yield_period=yield_period,                  # 수율 집계 기간
    validate=True,                              # 유효성 검사 수행 여부
    save_output=True                            # python_input.xlsx 저장 여부
)
```

### 처리 과정
1. **DataValidator**: 데이터 유효성 검사 및 중복 제거
   - 제품군-GITEM-SITEM 정합성 검증
   - 공정, 수율, 라인스피드 데이터의 GITEM 존재성 검증
   - 배합액 데이터 검증

2. **ProductionDataPreprocessor**: 데이터 변환
   - 주문 데이터 전처리
   - 라인스피드 피벗 테이블 생성 (wide format)
   - 공정 타입 및 순서 정보 생성
   - 수율 데이터 정제 (GITEM + PROCCODE 기준)
   - 배합액 정보 변환
   - Aging 데이터 병합 (aging_gitem + aging_gbn)

### 출력
`processed_data` (Dict[str, Any]):
```python
{
    'order_data': pd.DataFrame,           # 전처리된 주문 데이터
    'linespeed': pd.DataFrame,            # 라인스피드 피벗 테이블 (wide format)
    'operation_types': pd.DataFrame,      # 공정 타입 정보
    'operation_sequence': pd.DataFrame,   # 공정 순서 정보
    'yield_data': pd.DataFrame,           # 수율 정보 (GITEM + PROCCODE)
    'chemical_data': pd.DataFrame,        # 배합액 정보
    'operation_delay': pd.DataFrame,      # 공정교체시간
    'width_change': pd.DataFrame,         # 폭변경 정보
    'aging_data': pd.DataFrame,           # 에이징 정보 (gitem + gbn 통합)
    'global_machine_limit': pd.DataFrame, # 글로벌 기계 제약조건
    'validation_result': dict or None     # 검증 결과
}
```

### 비고
- 이 모듈은 원본 Excel 데이터를 표준화된 형식으로 변환
- `validate=True`일 때 데이터 유효성 검사 수행
- `save_output=True`일 때 중간 결과를 `python_input.xlsx`로 저장 가능 (선택 사항)

---

## 2. MachineMapper 생성 - 기계 매핑 관리자 초기화

### 클래스명
`MachineMapper`

### 위치
`src/utils/machine_mapper.py:MachineMapper`
`main.py:100-111` (호출)

### 입력
```python
machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(
    machine_master_file,
    dtype={config.columns.MACHINE_CODE: str}
)
machine_mapper = MachineMapper(machine_master_info_df)
```

### 처리 과정
1. machine_master_info_df에서 기계 정보 추출
2. 기계코드 → machineno 매핑 딕셔너리 생성
3. machineno → 기계코드 매핑 딕셔너리 생성
4. 기계코드 → 공정구분 매핑 딕셔너리 생성

### 출력
`machine_mapper` (MachineMapper 인스턴스):
```python
class MachineMapper:
    machine_master_df: pd.DataFrame
    machine_code_to_no: dict       # {기계코드: machineno}
    machine_no_to_code: dict       # {machineno: 기계코드}
    machine_code_to_type: dict     # {기계코드: 공정구분}

    # 주요 메서드
    get_machine_no(machine_code: str) -> int
    get_machine_code(machine_no: int) -> str
    get_machine_type(machine_code: str) -> str
    get_unique_machine_nos() -> List[int]
```

### 비고
- 기계 인덱스 대신 machineno 기반으로 작업
- 기계 정보 조회 중앙화 (하드코딩 제거)

---

## 3. Order Sequencing - 주문 시퀀스 생성

### 함수명
`generate_order_sequences()`

### 위치
`src/order_sequencing/__init__.py:8`
`main.py:114-116` (호출)

### 입력
```python
sequence_seperated_order, linespeed, unable_gitems, unable_order, unable_details = generate_order_sequences(
    order=order,                                # processed_data['order_data']
    operation_seperated_sequence=operation_seperated_sequence,  # processed_data['operation_sequence']
    operation_types=operation_types,            # processed_data['operation_types']
    machine_limit=local_machine_limit,          # 로컬 기계 제약조건
    global_machine_limit=global_machine_limit,  # processed_data['global_machine_limit']
    machine_allocate=machine_allocate,          # 기계 강제 할당
    linespeed=linespeed,                        # processed_data['linespeed']
    chemical_data=chemical_data                 # processed_data['chemical_data']
)
```

### 처리 과정
1. **OrderPreprocessor**: 주문 전처리
   - `same_order_groupby()`: 동일 주문 통합 (배치 효율화)

2. **SequencePreprocessor**: 공정 시퀀스 생성
   - `create_sequence_seperated_order()`: 주문별 상세 공정 순서 생성

3. **OperationMachineLimit**: 기계 제약 처리
   - `operation_machine_limit()`: 로컬/글로벌 기계 제약 조건 적용
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

#### `sequence_seperated_order` 주요 컬럼
- `PoNo`, `GitemNo`, `PROCCODE`, `PROCSEQ`, `PROCNAME`, `ProcGbn`
- `production_length`, `fabric_width`
- `DUEDATE`, `ID` (DAG 노드 ID용)
- 기타 공정 정보

### 비고
- `unable_gitems`, `unable_order`는 생산 불가능한 항목을 사용자에게 알리기 위한 정보
- main.py에서 통계 출력 용도로 사용됨

---

## 4. Yield Prediction - 수율 예측

### 함수명
`yield_prediction()`

### 위치
`src/yield_management/__init__.py:4`
`main.py:119-122` (호출)

### 입력
```python
sequence_seperated_order = yield_prediction(
    yield_data=yield_data,                      # processed_data['yield_data']
    sequence_seperated_order=sequence_seperated_order  # generate_order_sequences() 출력
)
```

### 처리 과정
1. GITEM을 문자열로 변환
2. **GITEM + PROCCODE** 기준으로 yield_data와 병합 (left join) ⭐ 변경됨
3. `product_ratio = 1 / yield` 계산
4. `original_production_length` = 원본 `production_length` 백업
5. `production_length = original_production_length * product_ratio` (수율 반영)
6. **10 단위로 반올림** ⭐ 신규 추가
7. 임시 컬럼 제거 (yield, product_ratio)

### 출력
`sequence_seperated_order` (pd.DataFrame):
- 입력과 동일한 DataFrame에 다음 컬럼 추가/수정:
  - `original_production_length`: 원본 생산길이
  - `production_length`: 수율 반영 + 10단위 반올림된 생산길이

### 비고
- 수율이 없는 GITEM+PROCCODE는 원본 생산길이 유지
- 수율 = 0.9 → product_ratio = 1.11 → 생산길이 11% 증가 → 10단위 반올림

---

## 5. Aging 요구사항 파싱

### 함수명
`parse_aging_requirements()`

### 위치
`src/dag_management/dag_dataframe.py:parse_aging_requirements()`
`main.py:126-128` (호출)

### 입력
```python
aging_map = parse_aging_requirements(
    aging_df=aging_df,                          # processed_data['aging_data']
    sequence_seperated_order=sequence_seperated_order  # yield_prediction() 출력
)
```

### 처리 과정
1. **Aging Map 생성**: Aging 데이터에서 맵 생성
2. **형식**: `{(GitemNo, ProcGbn): aging_time}` 딕셔너리
3. **에이징 시간**: 특정 공정 완료 후 다음 공정 시작 전 필수 대기 시간

### 출력
```python
aging_map = {
    ("GITEM001", "DY"): 96.0,    # GITEM001의 염색 공정 후 96시간 대기
    ("GITEM002", "CT"): 48.0,    # GITEM002의 코팅 공정 후 48시간 대기
    ...
}
```

### 비고
- `aging_df=None` 또는 빈 DataFrame 전달 시 빈 딕셔너리 반환
- 모든 노드의 AGING_TIME=0으로 처리됨

---

## 6. DAG Creation - DAG 시스템 생성

### 함수명
`create_complete_dag_system()`

### 위치
`src/dag_management/__init__.py:75`
`main.py:133-136` (호출)

### 입력
```python
dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    linespeed=linespeed,                                # generate_order_sequences() 출력
    machine_mapper=machine_mapper,                      # MachineMapper 인스턴스 ⭐ 변경됨
    aging_map=aging_map                                 # parse_aging_requirements() 출력
)
```

### 처리 과정
0. **Aging Map 활용** (aging_map이 제공된 경우)
   - `parse_aging_requirements()`에서 생성된 aging_map 직접 전달
   - `{(GitemNo, ProcGbn): aging_time}` 형식
   - aging_map=None이면 빈 딕셔너리로 처리

1. **DAGDataFrameCreator**: DAG 데이터프레임 생성
   - `create_full_dag()`: 전체 DAG 구조 생성
   - depth, children 계산
   - Aging 노드 자동 삽입 (sequential insertion)

2. **NodeDictCreator**: 노드 딕셔너리 생성
   - `create_opnode_dict()`: 작업 노드 정보 딕셔너리 생성
   - CHEMICAL_LIST, SELECTED_CHEMICAL(초기값 None), AGING_TIME 포함

3. **DAGGraphManager**: DAG 그래프 구축
   - `build_from_dataframe()`: DAGNode 객체 생성 및 children 연결

4. **MachineDict**: 기계 정보 딕셔너리
   - `create_machine_dict()`: 노드별 기계 소요시간 딕셔너리 생성
   - machineno 기준 ⭐ 변경됨

5. **MergeProcessor**: 데이터 병합
   - `merge_order_operation()`: 주문-공정 정보 통합

### 출력
```python
(
    dag_df,         # pd.DataFrame: DAG 데이터프레임 (ID, depth, children, aging 노드 포함)
    opnode_dict,    # dict: 노드별 상세 정보 (CHEMICAL_LIST, SELECTED_CHEMICAL, AGING_TIME 포함)
    manager,        # DAGGraphManager: DAG 그래프 관리자 인스턴스
    machine_dict,   # dict: 노드별 기계 소요시간 (machineno 기준)
    merged_df       # pd.DataFrame: 주문-공정 병합 테이블
)
```

#### `opnode_dict` 구조 예시
```python
{
    "N00001_1_공정": {
        "OPERATION_ORDER": 1,
        "OPERATION_CODE": "염색",
        "OPERATION_CLASSIFICATION": "DY",
        "FABRIC_WIDTH": 1500,
        "CHEMICAL_LIST": ("CHEM_A", "CHEM_B"),   # 사용 가능한 배합액 튜플
        "PRODUCTION_LENGTH": 1000,
        "SELECTED_CHEMICAL": None,               # 초기값 None (스케줄링 시 설정)
        "AGING_TIME": 96.0                       # 에이징 시간 (없으면 0)
    }
}
```

#### `machine_dict` 구조 예시 ⭐ 변경됨
```python
{
    "N00001_1_공정": {
        1: 120.5,    # machineno=1에서의 소요시간
        2: 9999,     # machineno=2에서는 처리 불가
        3: 150.2,    # machineno=3에서의 소요시간
        ...
    }
}
```

---

## 7. Scheduling - 스케줄링 실행

### 함수명
`run_scheduler_pipeline()`

### 위치
`src/scheduler/__init__.py:89`
`main.py:143-155` (호출)

### 입력
```python
result, scheduler = run_scheduler_pipeline(
    dag_df=dag_df,                                      # create_complete_dag_system() 출력
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    width_change_df=width_change_df,                    # processed_data['width_change']
    machine_mapper=machine_mapper,                      # MachineMapper 인스턴스 ⭐ 변경됨
    opnode_dict=opnode_dict,                            # create_complete_dag_system() 출력
    operation_delay_df=operation_delay_df,              # processed_data['operation_delay']
    machine_dict=machine_dict,                          # create_complete_dag_system() 출력
    machine_rest=machine_rest,                          # 기계 다운타임 정보
    base_date=base_date,                                # 기준 날짜 (datetime)
    manager=manager,                                    # create_complete_dag_system() 출력
    window_days=window_days                             # 윈도우 크기 (int)
)
```

### 처리 과정
이 함수는 스케줄링 준비부터 실행까지 전체 파이프라인을 자동으로 처리합니다:

1. **디스패치 규칙 생성** (`create_dispatch_rule`)
   - dag_df와 sequence_seperated_order 기반으로 우선순위 생성
   - 우선순위 정렬된 노드 ID 리스트 생성

2. **DelayProcessor 초기화**
   - 공정 교체 지연시간 설정 (operation_delay_df)
   - 폭 변경 지연시간 설정 (width_change_df)
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
    result,     # pd.DataFrame: 스케줄링 결과
    scheduler   # Scheduler 인스턴스 (후처리에서 사용)
)
```

#### `result` 주요 컬럼
- `ID`: 노드 ID
- `node_start`: 작업 시작 시간 (time slot)
- `node_end`: 작업 종료 시간 (time slot)
- `machine`: 할당된 기계번호 (machineno) ⭐ 변경됨
- `processing_time`: 처리 소요 시간
- `depth`: DAG depth
- 기타 노드 정보

### 비고
- 이 함수는 wrapper function으로, 복잡한 스케줄링 파이프라인을 단순하게 호출 가능
- 배합액 최적화가 포함된 SetupMinimizedStrategy 자동 적용
- opnode_dict의 SELECTED_CHEMICAL가 이 단계에서 동적으로 설정됨
- machineno 기반으로 작업 ⭐ 변경됨

---

## 8. Results Processing - 결과 후처리

### 함수명
`create_new_results()` ⭐ 변경됨

### 위치
`src/new_results/__init__.py:create_new_results()`
`main.py:162-170` (호출)

### 입력
```python
final_results = create_new_results(
    raw_scheduling_result=result,                       # run_scheduler_pipeline() 출력
    merged_df=merged_df,                                # create_complete_dag_system() 출력
    original_order=order,                               # processed_data['order_data']
    sequence_seperated_order=sequence_seperated_order,  # yield_prediction() 출력
    machine_mapper=machine_mapper,                      # MachineMapper 인스턴스 ⭐ 변경됨
    base_date=base_date,                                # datetime 객체
    scheduler=scheduler                                 # run_scheduler_pipeline() 출력
)
```

### 처리 과정

1. **PerformanceMetrics**: 성과 지표 계산 ⭐ 신규
   - PO 개수, makespan, 납기준수율, 평균 장비가동률 계산

2. **MachineDetailedAnalyzer**: 장비별 상세 성과 분석 ⭐ 신규
   - 기계별 작업 수, 가동시간, 가동률 계산
   - 간격(gap) 분석

3. **OrderLatenessReporter**: 주문 지각 정보 분석 ⭐ 신규
   - 주문별 납기 대비 완료 일자 계산
   - 지각일수, 준수 여부 판정

4. **SimplifiedGapAnalyzer**: 간격 분석 ⭐ 신규
   - 작업 간 간격(gap) 상세 분석
   - 지연시간 세부 분류

5. **기계 정보 처리**
   - 기계별 작업 스케줄 생성
   - 타임라인 정리

### 출력
`final_results` (dict):
```python
{
    # ===== 메타데이터 =====
    'metadata': {
        'actual_makespan': float,      # 실제 makespan
        'total_tasks': int,            # 총 작업 수
        'total_machines': int          # 총 기계 수
    },

    # ===== 성과 지표 =====
    'performance_metrics': {
        'po_count': int,                    # PO 개수
        'makespan_hours': float,            # makespan (시간)
        'ontime_delivery_rate': float,      # 납기준수율 (%)
        'avg_utilization': float            # 평균 장비가동률 (%)
    },

    # ===== 지각 요약 =====
    'lateness_summary': {
        'ontime_orders': int,               # 준수 주문 수
        'late_orders': int,                 # 지각 주문 수
        'avg_lateness_days': float          # 평균 지각일수 (지각 주문만)
    },

    # ===== Excel 시트 데이터 (5개) =====
    'performance_summary': List[dict],           # 시트1: 스케줄링_성과_지표
    'machine_info': pd.DataFrame,                # 시트2: 호기_정보
    'machine_detailed_performance': pd.DataFrame, # 시트3: 장비별_상세_성과
    'order_lateness_report': pd.DataFrame,       # 시트4: 주문_지각_정보
    'gap_analysis': pd.DataFrame                 # 시트5: 간격_분석
}
```

#### Excel 시트별 상세 구조

##### 시트1: 스케줄링_성과_지표
```python
[
    {'지표명': 'PO제품수', '값': 100, '단위': '개'},
    {'지표명': '총 생산시간', '값': 240.5, '단위': '시간'},
    {'지표명': '납기준수율', '값': 85.2, '단위': '%'},
    {'지표명': '장비가동률(평균)', '값': 78.3, '단위': '%'},
]
```

##### 시트2: 호기_정보
- 컬럼: `machineno`, `node_id`, `작업시작시각`, `작업종료시각`, 기타

##### 시트3: 장비별_상세_성과
- 컬럼: `machineno`, `작업수`, `가동시간`, `가동률`, `간격합계`, 기타

##### 시트4: 주문_지각_정보
- 컬럼: `PoNo`, `GitemNo`, `납기일`, `완료일`, `지각일수`, `준수여부`

##### 시트5: 간격_분석
- 컬럼: `machineno`, `작업1`, `작업2`, `간격`, `간격유형`, 기타

### 비고
- 이 모듈이 최종 사용자에게 보여질 모든 결과 생성
- Excel 파일 생성 (5개 시트)
- 기존 `create_results()` 대체 ⭐

---

## 9. 파일 저장 (Final Output)

### 위치
`main.py:196-230`

### 저장되는 파일

#### 9-1. 원본 결과 (임시)
**파일**: `data/output/result.xlsx`
**내용**: `result` DataFrame 그대로 저장
```python
result.to_excel(excel_filename, index=False)
```

#### 9-2. 최종 결과 Excel (5개 시트) ⭐ 변경됨
**파일**: `data/output/0829 스케줄링결과.xlsx`
```python
with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
    # 1. 스케줄링 성과 지표
    pd.DataFrame(final_results['performance_summary']).to_excel(
        writer, sheet_name="스케줄링_성과_지표", index=False
    )

    # 2. 호기 정보
    pd.DataFrame(final_results['machine_info']).to_excel(
        writer, sheet_name="호기_정보", index=False
    )

    # 3. 장비별 상세 성과
    pd.DataFrame(final_results['machine_detailed_performance']).to_excel(
        writer, sheet_name="장비별_상세_성과", index=False
    )

    # 4. 주문 지각 정보
    pd.DataFrame(final_results['order_lateness_report']).to_excel(
        writer, sheet_name="주문_지각_정보", index=False
    )

    # 5. 간격 분석
    pd.DataFrame(final_results['gap_analysis']).to_excel(
        writer, sheet_name="간격_분석", index=False
    )
```

### 출력 요약
```
data/output/result.xlsx                # 원본 결과 (임시)
data/output/0829 스케줄링결과.xlsx      # 최종 결과 (5개 시트)
```

---

## 데이터 흐름 요약

```
┌─────────────────────────────────────────────────────────────────┐
│  0. Excel 데이터 로딩                                            │
│     ├─ 생산계획 입력정보.xlsx (11개 시트)                         │
│     ├─ tb_commomconstraint.xlsx                                 │
│     ├─ 시나리오_공정제약조건.xlsx (3개 시트)                      │
│     └─ machine_master_info.xlsx                                 │
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
│  2. MachineMapper 생성                                          │
│     └─ 기계 매핑 관리자 초기화 (machineno 기반)                  │
│     → machine_mapper (MachineMapper)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. generate_order_sequences()                                  │
│     ├─ 주문 전처리 및 통합                                       │
│     ├─ 공정 시퀀스 생성                                          │
│     ├─ 기계 제약 및 강제 할당                                    │
│     └─ 폭 조합 로직                                             │
│     → sequence_seperated_order, unable_gitems, unable_order     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. yield_prediction()                                          │
│     └─ 수율 기반 생산길이 조정 (GITEM+PROCCODE, 10단위 반올림)   │
│     → sequence_seperated_order (updated)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. parse_aging_requirements()                                  │
│     └─ Aging Map 생성 {(GITEM, ProcGbn): aging_time}            │
│     → aging_map (dict)                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. create_complete_dag_system()                                │
│     ├─ DAG 데이터프레임 생성 (aging 노드 자동 삽입)              │
│     ├─ opnode_dict 생성 (CHEMICAL_LIST, AGING_TIME 포함)         │
│     ├─ DAG 그래프 구축                                           │
│     ├─ machine_dict 생성 (machineno 기준)                       │
│     └─ 데이터 병합                                              │
│     → dag_df, opnode_dict, manager, machine_dict, merged_df     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. run_scheduler_pipeline()                                    │
│     ├─ 디스패치 규칙 생성                                        │
│     ├─ DelayProcessor 초기화                                     │
│     ├─ Scheduler 초기화 및 자원 할당                             │
│     └─ 스케줄링 실행 (DispatchPriorityStrategy)                 │
│        └─ SetupMinimizedStrategy: 배합액 최적화                 │
│     → (result, scheduler)                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  8. create_new_results()                                        │
│     ├─ PerformanceMetrics: 성과 지표 계산                        │
│     ├─ MachineDetailedAnalyzer: 장비별 상세 성과                 │
│     ├─ OrderLatenessReporter: 주문 지각 정보                     │
│     └─ SimplifiedGapAnalyzer: 간격 분석                          │
│     → final_results (dict)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  9. 파일 저장                                                    │
│     ├─ result.xlsx: 원본 결과                                   │
│     └─ 0829 스케줄링결과.xlsx: 최종 결과 (5개 시트)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 엔드포인트 설계 권장사항

백엔드 서비스에서 각 모듈을 API 엔드포인트로 노출할 경우:

### 옵션 1: 단일 엔드포인트 (권장)
```
POST /api/scheduling/run
- 전체 파이프라인을 한 번에 실행
- 입력: Excel 파일 업로드 (4개) + 설정 파라미터 (JSON)
- 출력: 최종 결과 파일들 (Excel)
```

**요청 예시**:
```json
{
  "files": {
    "input_excel": "생산계획 입력정보.xlsx",
    "global_constraint": "tb_commomconstraint.xlsx",
    "scenario": "시나리오_공정제약조건.xlsx",
    "machine_master": "machine_master_info.xlsx"
  },
  "config": {
    "base_year": 2024,
    "base_month": 1,
    "base_day": 1,
    "window_days": 30,
    "linespeed_period": "6_months",
    "yield_period": "6_months"
  }
}
```

### 옵션 2: 단계별 엔드포인트
```
POST /api/scheduling/1-validation        → processed_data
POST /api/scheduling/2-machine-mapper    → machine_mapper
POST /api/scheduling/3-order-sequencing  → sequence_seperated_order
POST /api/scheduling/4-yield-prediction  → sequence_seperated_order (updated)
POST /api/scheduling/5-aging-parse       → aging_map
POST /api/scheduling/6-dag-creation      → dag_df, opnode_dict, manager, machine_dict, merged_df
POST /api/scheduling/7-run-scheduler     → (result, scheduler)
POST /api/scheduling/8-results           → final_results
```

### 옵션 3: 하이브리드 (추천)
```
POST /api/scheduling/preprocess          → 1+2+3+4+5 통합 (데이터 준비)
POST /api/scheduling/schedule            → 6+7 통합 (스케줄링 실행, 시간 소모 단계)
POST /api/scheduling/postprocess         → 8 (결과 처리)
```

---

## 주요 변경사항 (v3.0)

### 1. MachineMapper 도입 ⭐
- 기계 인덱스 → machineno 기반으로 변경
- 기계 정보 조회 중앙화
- `machine_master_info` 대신 `machine_mapper` 사용

### 2. new_results 모듈 사용 ⭐
- `create_results()` → `create_new_results()`
- 5개 시트로 결과 재구성:
  1. 스케줄링_성과_지표
  2. 호기_정보
  3. 장비별_상세_성과
  4. 주문_지각_정보
  5. 간격_분석

### 3. 입력 파일 구조 변경 ⭐
- aging 데이터: 통합 엑셀의 시트로 변경 (tb_agingtime_gitem, tb_agingtime_gbn)
- global/local machine limit 분리

### 4. run_scheduler_pipeline 도입 ⭐
- 스케줄링 파이프라인 단순화 (wrapper function)
- 복잡한 초기화 과정 자동화

### 5. 수율 적용 로직 개선 ⭐
- GITEM + PROCCODE 기준으로 변경 (기존: GITEM만)
- 10단위 반올림 추가

---

## 주의사항

1. **데이터 직렬화**
   - pandas DataFrame은 JSON으로 직렬화 시 `df.to_dict('records')` 사용
   - datetime 객체는 ISO 8601 문자열로 변환
   - MachineMapper는 pickle로 직렬화 필요

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

6. **machineno 기반 작업** ⭐
   - 모든 기계 관련 작업은 machineno 기준
   - MachineMapper를 통한 변환 필수
