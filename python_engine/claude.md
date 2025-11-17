# 스케줄링 프로젝트 구조 분석

## 🎯 프로젝트 개요

생산 스케줄링 시스템: 주문(Order) → 공정(Operation) → 기계(Machine) 할당을 최적화하는 DAG 기반 스케줄러
에이징 공정, 배합액 최적화, 셋업 시간 최소화, 기계 제약조건을 종합적으로 고려합니다.

---

## 📂 핵심 실행 흐름 (main.py 기준)

### 0. 진입점

**파일**: `main.py`
**함수**: `run_level4_scheduling()`

### 1. 데이터 로딩 및 설정 (main.py:26-93)

```python
# 기준 날짜 및 설정 파라미터
base_date = datetime(config.constants.BASE_YEAR, BASE_MONTH, BASE_DAY)
window_days = config.constants.WINDOW_DAYS
linespeed_period = config.constants.LINESPEED_PERIOD
yield_period = config.constants.YIELD_PERIOD

# Excel 파일 로딩
input_file = "data/input/생산계획 입력정보.xlsx"
- order_df (tb_polist)
- gitem_sitem_df (tb_itemspec)
- linespeed_df (tb_linespeed)
- operation_df (tb_itemproc)
- yield_df (tb_productionyield)
- chemical_df (tb_chemical)
- operation_delay_df (tb_changetime)
- width_change_df (tb_changewidth)
- aging_gitem, aging_gbn (tb_agingtime_gitem, tb_agingtime_gbn)

global_machine_limit_raw = "data/input/tb_commomconstraint.xlsx"
시나리오 파일 = "data/input/시나리오_공정제약조건.xlsx"
- local_machine_limit (machine_limit 시트)
- machine_allocate (machine_allocate 시트)
- machine_rest (machine_rest 시트)
```

**출력**:

- 원본 DataFrame들 (order_df, linespeed_df, operation_df 등)
- 설정 파라미터 (base_date, window_days 등)

---

### 2. Validation - 데이터 유효성 검사 및 전처리 (main.py:59-88)

**함수**: `src/validation/preprocess_production_data()`
**진행률**: 10% → 30%

**입력**:

- 원본 DataFrame들 (order_df, linespeed_df, operation_df, yield_df, chemical_df 등)
- aging_gitem_df, aging_gbn_df (에이징 정보)
- global_machine_limit_df (글로벌 기계 제약조건)
- linespeed_period, yield_period (집계 기간)
- validate=True, save_output=True (옵션)

**처리 과정**:

1. DataValidator: 데이터 유효성 검사 및 중복 제거
2. ProductionDataPreprocessor: 데이터 변환
   - 주문 데이터 전처리 (버퍼일자 반영 삭제됨)
   - 라인스피드 피벗 테이블 생성
   - 공정 타입 및 순서 정보 생성
   - 수율 데이터 정제
   - 배합액 정보 변환
   - Aging 데이터 병합 및 처리

**출력**: `processed_data` (dict)

- `order_data`: 전처리된 주문 데이터
- `linespeed`: 라인스피드 피벗 테이블 (wide format)
- `operation_types`: 공정 타입 정보
- `operation_sequence`: 공정 순서 정보
- `yield_data`: 수율 정보
- `chemical_data`: 배합액 정보
- `operation_delay`: 공정교체시간
- `width_change`: 폭변경 정보
- `aging_data`: 에이징 정보 (gitem + gbn 통합)
- `global_machine_limit`: 글로벌 기계 제약조건

---

### 3. 기계 마스터 정보 로딩 및 MachineMapper 생성 (main.py:100-111)

**진행률**: 31%

**입력**:

- `machine_master_file = "data/input/machine_master_info.xlsx"`

**처리**:

```python
machine_master_info_df = pd.read_excel(machine_master_file)
machine_mapper = MachineMapper(machine_master_info_df)
```

**출력**:

- `machine_mapper` (MachineMapper 인스턴스)
  - `machine_code_to_no`: {기계코드 → machineno} 매핑
  - `machine_no_to_code`: {machineno → 기계코드} 매핑
  - `machine_code_to_type`: {기계코드 → 공정구분} 매핑

**역할**:

- 기계 인덱스 대신 기계번호(machineno) 기반으로 작업
- 기계코드 ↔ machineno 양방향 변환
- 기계별 공정구분(type) 조회

---

### 4. 주문 시퀀스 생성 (main.py:114-116)

**함수**: `src/order_sequencing/generate_order_sequences()`
**진행률**: 30%

**입력**:

- order, operation_seperated_sequence, operation_types
- local_machine_limit, global_machine_limit, machine_allocate
- linespeed, chemical_data

**처리 과정**:

1. OrderPreprocessor: 주문 전처리 (월별 분리 삭제됨)
2. SequencePreprocessor: 공정 시퀀스 생성
3. OperationMachineLimit: 기계 제약 처리
4. FabricCombiner: 폭 조합 처리

**출력**:

- `sequence_seperated_order`: 공정별 분리된 주문 데이터 (각 행 = 하나의 공정)
- `linespeed`: 업데이트된 라인스피드 (제약 반영)
- `unable_gitems`, `unable_order`, `unable_details`: 생산 불가능 항목

---

### 5. 수율 예측 (main.py:119-122)

**함수**: `src/yield_management/yield_prediction()`
**진행률**: 35%

**입력**:

- yield_data, sequence_seperated_order

**처리**:

- GITEM + PROCCODE 기준으로 수율 매칭 (기존: GITEM만)
- `production_length = original_production_length * (1 / yield)`
- 수율 적용 후 생산길이를 10 단위로 반올림

**출력**:

- `sequence_seperated_order` (업데이트됨)
  - `original_production_length`: 원본 생산길이
  - `production_length`: 수율 반영 + 10단위 반올림된 생산길이

---

### 6. Aging 요구사항 파싱 (main.py:126-128)

**함수**: `src/dag_management/dag_dataframe.py:parse_aging_requirements()`
**진행률**: 38%

**입력**:

- aging_df (gitemno, procgbn, aging_time 포함)
- sequence_seperated_order

**처리**:

- Aging Map 생성: `{(GitemNo, ProcGbn): aging_time}`
- 해당 공정 완료 후 다음 공정 시작 전 필수 대기 시간

**출력**:

- `aging_map` (dict)
  ```python
  {
      ("GITEM001", "염색"): 96.0,
      ("GITEM002", "코팅"): 48.0,
      ...
  }
  ```

---

### 7. DAG 시스템 생성 ⭐ (main.py:133-136)

**함수**: `src/dag_management/create_complete_dag_system()`
**진행률**: 50%

**입력**:

- sequence_seperated_order (수율 반영 후)
- linespeed (제약 반영 후)
- machine_mapper (MachineMapper 인스턴스)
- aging_map (Aging 맵)

**처리**:

1. **DAGDataFrameCreator**: DAG 데이터프레임 생성

   - `create_full_dag()`: depth, children, aging 노드 삽입
   - Aging 노드 자동 생성 (sequential insertion으로 depth 중복 제거)

2. **NodeDictCreator**: 노드 딕셔너리 생성

   - `create_opnode_dict()`: CHEMICAL_LIST, SELECTED_CHEMICAL(초기 None), AGING_TIME 포함

3. **DAGGraphManager**: DAG 그래프 구축

   - `build_from_dataframe()`: DAGNode 객체 생성 및 children 연결

4. **MachineDict**: 기계 정보 딕셔너리

   - `create_machine_dict()`: 노드별 기계 소요시간 리스트

5. **MergeProcessor**: 데이터 병합
   - `merge_order_operation()`: 주문-공정 정보 통합

**출력** (5개 객체):

- `dag_df`: DAG 데이터프레임 (ID, depth, children, aging 노드 포함)
- `opnode_dict`: 노드별 상세 정보 (메타데이터)
- `manager`: DAGGraphManager (DAG 그래프 관리자)
- `machine_dict`: 기계별 소요시간 딕셔너리
- `merged_df`: 주문-공정 병합 테이블

---

### 8. 스케줄링 실행 ⭐⭐⭐ (main.py:143-155)

**함수**: `src/scheduler/run_scheduler_pipeline()`
**진행률**: 60% → 80%

**입력**:

- dag_df, opnode_dict, manager, machine_dict (DAG 시스템)
- sequence_seperated_order (주문 정보)
- width_change_df, operation_delay_df (지연시간)
- machine_mapper (기계 매핑)
- machine_rest (기계 다운타임)
- base_date, window_days (스케줄링 설정)

**처리 과정** (자동 파이프라인):

1. **디스패치 규칙 생성** (`create_dispatch_rule`)

   - 우선순위 정렬된 노드 ID 리스트 생성

2. **DelayProcessor 초기화**

   - 공정 교체 지연시간, 폭 변경 지연시간, 배합액 교체 지연시간 설정

3. **Scheduler 초기화 및 자원 할당**

   - 기계별 자원 할당 (`allocate_resources`)
   - 기계 다운타임 적용 (`allocate_machine_downtime`)

4. **스케줄링 실행**
   - **DispatchPriorityStrategy**: 우선순위 디스패치
     - 윈도우 기반 동적 스케줄링 (window_days만큼 작업 선택)
   - **SetupMinimizedStrategy**: 셋업시간 최소화
     - 배합액 최적화 및 같은 배합액 작업 연속 스케줄링
   - **SchedulingCore**: 단일 노드 스케줄링
     - OptimalMachineStrategy 또는 ForcedMachineStrategy
     - 선행 작업 완료, 기계 가용 시간, 지연시간 모두 반영

**출력**:

- `result` (pd.DataFrame): 스케줄링 결과
  - node_start, node_end, machine (machineno), processing_time 등
- `scheduler` (Scheduler 인스턴스): 후처리에서 사용

---

### 9. 결과 후처리 ⭐ (main.py:162-170)

**함수**: `src/results/create_results()`
**진행률**: 80% → 99%

**입력**:

- raw_scheduling_result (result)
- merged_df, original_order, sequence_seperated_order
- machine_mapper, base_date, scheduler

**처리**:

1. **PerformanceMetrics**: 성과 지표 계산

   - PO 개수, makespan, 납기준수율, 평균 장비가동률

2. **MachineDetailedAnalyzer**: 장비별 상세 성과 분석

   - 기계별 작업 수, 가동시간, 가동률, 간격(gap) 분석

3. **OrderLatenessReporter**: 주문 지각 정보 분석

   - 주문별 납기 대비 완료 일자, 지각일수, 준수 여부

4. **SimplifiedGapAnalyzer**: 간격 분석 (간소화 버전)
   - 작업 간 간격(gap) 상세 분석

**출력**: `final_results` (dict)

```python
{
    'metadata': {
        'actual_makespan': float,  # 실제 makespan
        'total_tasks': int,
        'total_machines': int
    },
    'performance_metrics': {
        'po_count': int,
        'makespan_hours': float,
        'ontime_delivery_rate': float,
        'avg_utilization': float
    },
    'lateness_summary': {
        'ontime_orders': int,
        'late_orders': int,
        'avg_lateness_days': float
    },
    'performance_summary': List[dict],           # 시트1: 스케줄링_성과_지표
    'machine_info': pd.DataFrame,                # 시트2: 호기_정보
    'machine_detailed_performance': pd.DataFrame, # 시트3: 장비별_상세_성과
    'order_lateness_report': pd.DataFrame,       # 시트4: 주문_지각_정보
    'gap_analysis': pd.DataFrame                 # 시트5: 간격_분석
}
```

---

### 10. 파일 저장 (main.py:196-230)

**진행률**: 99% → 100%

#### 10-1. 원본 결과 (임시)

**파일**: `data/output/result.xlsx`

- result DataFrame 그대로 저장

#### 10-2. 최종 결과 Excel (5개 시트)

**파일**: `data/output/0829 스케줄링결과.xlsx`

1. **스케줄링*성과*지표**: 전체 성과 요약 (PO 개수, makespan, 납기준수율, 평균가동률)
2. **호기\_정보**: 기계별 작업 스케줄 (기계별 타임라인)
3. **장비별*상세*성과**: 기계별 가동률, 가동시간, 작업 수, 간격 분석
4. **주문*지각*정보**: 주문별 납기 대비 완료 일자, 지각일수
5. **간격\_분석**: 작업 간 간격(gap) 상세 분석

---

## 🔧 핵심 객체 구조

### 1. MachineMapper (기계 매핑 관리자) ⭐ NEW

**위치**: `src/utils/machine_mapper.py:MachineMapper`

**주요 속성**:

```python
class MachineMapper:
    self.machine_master_df = machine_master_info_df
    self.machine_code_to_no = {기계코드: machineno}
    self.machine_no_to_code = {machineno: 기계코드}
    self.machine_code_to_type = {기계코드: 공정구분}
```

**주요 메서드**:

- `get_machine_no(machine_code)`: 기계코드 → machineno
- `get_machine_code(machine_no)`: machineno → 기계코드
- `get_machine_type(machine_code)`: 기계코드 → 공정구분
- `get_unique_machine_nos()`: 모든 machineno 리스트

**역할**:

- 기계 인덱스 대신 기계번호(machineno) 기반으로 작업
- 기계 정보 조회 중앙화 (하드코딩 제거)

---

### 2. opnode_dict (노드 메타데이터)

**위치**: `src/dag_management/node_dict.py:create_opnode_dict()`

**구조**:

```python
{
    node_id: {
        "OPERATION_ORDER": 공정 순서 (1, 2, 3, ...),
        "OPERATION_CODE": 공정 코드 (예: "염색", "코팅"),
        "OPERATION_CLASSIFICATION": 공정 분류 (예: "DY"),
        "FABRIC_WIDTH": 원단 너비,
        "CHEMICAL_LIST": (배합액1, 배합액2, ...) # 튜플,
        "PRODUCTION_LENGTH": 생산 길이,
        "SELECTED_CHEMICAL": None,  # 스케줄링 중 할당됨
        "AGING_TIME": 96.0          # 에이징 시간 (없으면 0)
    }
}
```

**역할**:

- 각 공정(노드)의 속성 정보 저장
- 스케줄링 중 `SELECTED_CHEMICAL`이 업데이트됨

---

### 3. machine_dict (기계별 소요시간)

**위치**: `src/dag_management/node_dict.py:create_machine_dict()`

**구조**:

```python
{
    node_id: {
        machineno1: 소요시간1,
        machineno2: 소요시간2,
        ...
    }
}
```

**특징**:

- 소요시간 = `생산길이 / linespeed / TIME_MULTIPLIER`
- 9999 = 해당 기계에서 처리 불가능
- 예: `{"N00001": {1: 120, 2: 9999, 3: 150}}` → 기계2에서는 처리 불가

**역할**:

- 스케줄러가 최적 기계 선택 시 참조
- `scheduler.assign_operation()`에서 사용

---

### 4. DAGGraphManager (DAG 구조 관리자)

**위치**: `src/dag_management/dag_manager.py:DAGGraphManager`

**주요 속성**:

```python
class DAGGraphManager:
    self.nodes = {}  # {node_id: DAGNode 객체}
    self.opnode_dict = opnode_dict  # 노드 메타데이터 참조
```

**주요 메서드**:

- `build_from_dataframe(dag_df)`: DAG 구조 빌드
- `to_dataframe()`: 스케줄링 결과를 DataFrame으로 변환

**역할**:

- 모든 DAGNode 객체 관리
- 노드 간 선후 관계(children) 연결
- 스케줄링 중 노드 상태 추적

---

### 5. DAGNode (개별 노드 객체)

**위치**: `src/dag_management/dag_dataframe.py:DAGNode`

**주요 속성**:

```python
class DAGNode:
    # === 그래프 구조 (불변) ===
    self.id = node_id
    self.depth = depth  # 공정 순서 (1, 2, 3, ...)
    self.children = []  # 후속 작업 노드 리스트
    self.all_descendants = []  # 모든 후손 노드 ID 리스트

    # === 스케줄링 상태 (가변 - 스케줄링 중 업데이트) ===
    self.parent_node_count = 0  # 아직 완료되지 않은 선행작업 개수
    self.parent_node_end = [0]  # 부모들의 종료시간 리스트
    self.earliest_start = None  # 최조 시작 가능 시간

    # === 스케줄링 결과 ===
    self.machine = None  # 할당된 기계번호 (machineno)
    self.node_start = None  # 실제 시작 시간
    self.node_end = None  # 실제 종료 시간
    self.processing_time = None  # 처리 소요 시간
```

**핵심 로직**:

- `parent_node_count == 0` → 스케줄링 가능 (선행작업 모두 완료)
- 스케줄링 완료 시 → children의 `parent_node_count -= 1`
- `earliest_start = max(parent_node_end)` → 부모들이 모두 끝난 후 시작

**역할**:

- 각 공정의 스케줄링 상태 저장
- 선후 의존성 관리 (parent_node_count, children)

---

### 6. Scheduler (기계 자원 관리자)

**위치**: `src/scheduler/scheduler.py:Scheduler`

**주요 속성**:

```python
class Scheduler:
    self.machine_dict = machine_dict  # 노드별 기계 소요시간
    self.Machines = {}  # {machineno: Machine_Time_window 객체}
    self.delay_processor = delay_processor  # 공정교체시간 계산
    self.machine_mapper = machine_mapper  # 기계 매핑
```

**주요 메서드**:

- `allocate_resources()`: Machine_Time_window 객체들 생성
- `assign_operation(earliest_start, node_id, depth)`: 최적 기계 자동 선택
- `force_assign_operation(machineno, ...)`: 특정 기계에 강제 할당
- `machine_earliest_start(...)`: 특정 기계의 최적 시작시간 계산

**역할**:

- 기계별 스케줄 관리
- 빈 시간창(Empty_time_window) 분석
- 공정교체시간(delay) 고려한 할당

---

### 7. Machine_Time_window (기계 객체)

**위치**: `src/scheduler/machine.py:Machine_Time_window`

**주요 속성**:

```python
class Machine_Time_window:
    self.machineno = machineno  # 기계번호 (이전: Machine_index)
    self.assigned_task = []  # [(depth, node_id), ...]
    self.O_start = []  # 각 작업의 시작시간
    self.O_end = []    # 각 작업의 종료시간
    self.End_time = 0  # 기계의 마지막 작업 종료시간
```

**주요 메서드**:

- `Empty_time_window()`: 빈 시간창 계산 → (시작시간, 종료시간, 길이)
- `_Input(depth, node_id, M_Earliest, P_t)`: 작업 추가 및 정렬
- `force_Input(...)`: 기계 사용 불가 시간대 설정

**역할**:

- 각 기계의 작업 스케줄 저장
- 빈 시간창 제공 (새 작업 끼워넣기 가능)
- 작업들을 시작시간 순으로 자동 정렬

---

## 🔥 스케줄링 실행 흐름 (상세)

### 전체 구조

```
run_scheduler_pipeline()
  ├─> create_dispatch_rule(): 우선순위 생성
  ├─> DelayProcessor 초기화
  ├─> Scheduler 초기화 및 자원 할당
  └─> DispatchPriorityStrategy.execute()
      └─> 윈도우 생성 (납기일 ±window_days)
          └─> SetupMinimizedStrategy.execute()
              └─> 배합액 그룹별로 묶음
                  └─> SchedulingCore.schedule_single_node()
```

### schedule_single_node() 상세 흐름

**위치**: `src/scheduler/scheduling_core.py:schedule_single_node()`

```python
def schedule_single_node(node, scheduler, machine_assignment_strategy):
    # ① 선행 작업 완료 검증
    if node.parent_node_count != 0:
        return False  # 선행작업이 아직 완료되지 않음

    # ② 최조 시작 가능 시간 계산
    earliest_start = max(node.parent_node_end)
    # parent_node_end: 부모 노드들의 종료시간 리스트

    # ③ 기계 할당 (전략 패턴)
    assignment_result = machine_assignment_strategy.assign(
        scheduler, node, earliest_start
    )
    # 내부에서:
    # - machine_dict[node.id]에서 기계별 소요시간 조회
    # - 각 기계의 Empty_time_window() 분석
    # - 가장 빨리 끝낼 수 있는 기계 선택
    # - Machine_Time_window._Input()으로 작업 추가

    # ④ DAGNode 상태 업데이트
    node.machine = assignment_result.machine_no
    node.node_start = assignment_result.start_time
    node.processing_time = assignment_result.processing_time
    node.node_end = start_time + processing_time

    # ⑤ 후속 작업(children) 의존성 업데이트
    for child in node.children:
        child.parent_node_count -= 1
        child.parent_node_end.append(node.node_end)
        # parent_node_count가 0이 되면 스케줄링 가능

    return True
```

---

## 📊 객체 간 상호작용 맵

### 스케줄링 중 데이터 흐름:

```
1. DAGNode.id 조회
   ↓
2. machine_dict[node.id] 조회 → {machineno: 소요시간}
   ↓
3. 각 기계의 scheduler.Machines[machineno].Empty_time_window() 분석
   ↓
4. 최적 기계 선택 → Machine_Time_window._Input() 호출
   ↓
5. DAGNode 업데이트:
   - node.machine = 선택된 machineno
   - node.node_start = 시작시간
   - node.node_end = 종료시간
   ↓
6. 후속 노드(children) 업데이트:
   - child.parent_node_count -= 1
   - child.parent_node_end.append(node.node_end)
```

### 배합액 선택 흐름:

```
1. SetupMinimizedStrategy에서 윈도우 내 노드들 분석
   ↓
2. 첫 노드의 opnode_dict[node_id]["CHEMICAL_LIST"] 조회
   ↓
3. find_best_chemical() → 가장 많이 사용 가능한 배합액 선택
   ↓
4. opnode_dict[node_id]["SELECTED_CHEMICAL"] 업데이트
   ↓
5. 같은 배합액 사용 가능한 노드들을 같은 기계에 연속 할당
```

---

## 💾 정보 저장 위치 정리

| 정보 유형            | 저장 위치                                   | 예시                                      |
| -------------------- | ------------------------------------------- | ----------------------------------------- |
| **노드 메타데이터**  | `opnode_dict[node_id]`                      | 공정코드, 너비, 배합액 리스트, AGING_TIME |
| **선택된 배합액**    | `opnode_dict[node_id]["SELECTED_CHEMICAL"]` | "CHEM_A"                                  |
| **기계별 소요시간**  | `machine_dict[node_id]`                     | {1: 120, 2: 9999, 3: 150}                 |
| **노드 스케줄 결과** | `DAGNode 객체`                              | machine=1, node_start=100, node_end=220   |
| **기계 스케줄**      | `Machine_Time_window 객체`                  | assigned_task, O_start, O_end             |
| **DAG 구조**         | `DAGGraphManager.nodes`                     | 모든 DAGNode 보유, children 연결          |
| **공정교체시간**     | `DelayProcessor`                            | 공정/배합액/너비 변경 시 지연시간         |
| **기계 매핑**        | `MachineMapper`                             | 기계코드 ↔ machineno ↔ 공정구분           |

---

## 🎯 주요 설계 패턴

### 1. 전략 패턴 (Strategy Pattern)

**위치**: `src/scheduler/scheduling_core.py`

```python
# 기계 할당 전략
- OptimalMachineStrategy: 최적 기계 자동 선택
- ForcedMachineStrategy: 특정 기계 강제 할당

# 스케줄링 전략
- DispatchPriorityStrategy: 우선순위 디스패치
- SetupMinimizedStrategy: 셋업시간 최소화
```

### 2. DAG (방향성 비순환 그래프)

- 각 노드는 후속 작업(children)만 알고 있음
- `parent_node_count`로 선행작업 완료 여부 추적
- 완료 시 children에게 전파 (count 감소, end_time 추가)

### 3. 빈 시간창 활용 (Empty Time Window)

- 기계의 작업 사이 빈 시간에 끼워넣기 가능
- 공정교체시간(delay)도 고려

### 4. 중앙화된 기계 관리 (MachineMapper)

- 기계 정보 조회 중앙화
- 하드코딩 제거 (machineno 기반)

---

## 🔍 디버깅 시 체크포인트

### 1. 노드가 스케줄링 안 되는 경우

```python
# 체크 1: parent_node_count 확인
node.parent_node_count  # 0이어야 스케줄링 가능

# 체크 2: parent_node_end 확인
node.parent_node_end  # 부모들의 종료시간 모두 추가되었는지

# 체크 3: machine_dict 확인
machine_dict[node.id]  # 9999가 아닌 기계가 있는지
```

### 2. 기계 할당이 이상한 경우

```python
# 체크 1: Empty_time_window 확인
scheduler.Machines[machineno].Empty_time_window()

# 체크 2: delay 확인
delay_processor.delay_calc_whole_process(prev_node_id, node_id, machineno)

# 체크 3: earliest_start 확인
node.earliest_start = max(node.parent_node_end)
```

### 3. 배합액 선택이 안 되는 경우

```python
# 체크 1: CHEMICAL_LIST 확인
opnode_dict[node_id]["CHEMICAL_LIST"]  # 비어있지 않은지

# 체크 2: find_best_chemical 로그
# [LOG] find_best_chemical: selected=... 출력 확인

# 체크 3: SELECTED_CHEMICAL 확인
opnode_dict[node_id]["SELECTED_CHEMICAL"]  # None이 아닌지
```

---

## 📝 주요 컬럼명 (config.columns)

```python
# 주문 관련
PO_NO = "P/O NO"
DUE_DATE = "납기일"
GITEM = "GITEM"

# 공정 관련
OPERATION_ORDER = "공정순서"
OPERATION_CODE = "공정"
OPERATION_CLASSIFICATION = "공정구분"
ID = "ID"
PROCESS_ID_SUFFIX = "공정"

# 생산 관련
PRODUCTION_LENGTH = "생산길이"
FABRIC_WIDTH = "원단폭"
CHEMICAL_LIST = "배합액리스트"

# 기계 관련
MACHINE_CODE = "기계"
MACHINE_NO = "machineno"  # NEW

# 결과 관련
WORK_START_TIME = "작업시작시각"
WORK_END_TIME = "작업종료시각"
ALLOCATED_WORK = "할당된일"
LATE_DAYS = "지각일수"

# Aging 관련
AGING_TIME = "aging_time"
AGING_GITEM = "gitemno"
AGING_GBN = "procgbn"
```

---

## 🚀 빠른 참조

### 전체 흐름 다시 보기

```
1. main.py:26-93    → 데이터 로딩
2. main.py:59-88    → Validation (전처리)
3. main.py:100-111  → MachineMapper 생성
4. main.py:114-116  → 주문 시퀀스 생성
5. main.py:119-122  → 수율 예측
6. main.py:126-128  → Aging 파싱
7. main.py:133-136  → DAG 생성 (5개 객체)
8. main.py:143-155  → 스케줄링 실행 (run_scheduler_pipeline)
9. main.py:162-170  → 결과 후처리 (create_results)
10. main.py:196-230 → 파일 저장 (5개 시트)
```

### 핵심 파일 위치

- **DAG 생성**: `src/dag_management/`

  - `dag_dataframe.py`: DAGNode, Create_dag_dataframe, parse_aging_requirements
  - `dag_manager.py`: DAGGraphManager
  - `node_dict.py`: opnode_dict, machine_dict 생성

- **스케줄링**: `src/scheduler/`

  - `scheduling_core.py`: 전략 패턴, 핵심 로직
  - `scheduler.py`: Scheduler 클래스
  - `machine.py`: Machine_Time_window 클래스
  - `dispatch_rules.py`: 디스패치 룰 생성

- **결과 처리**: `src/results/` ⭐ NEW

  - `__init__.py`: create_results (메인 함수)
  - `performance_metrics.py`: 성과 지표 계산
  - `machine_detailed_analyzer.py`: 장비별 상세 성과
  - `order_lateness_reporter.py`: 주문 지각 정보
  - `simplified_gap_analyzer.py`: 간격 분석

- **유틸리티**: `src/utils/`

  - `machine_mapper.py`: MachineMapper 클래스 ⭐ NEW

- **진입점**: `main.py`

---

## ⚠️ 중요 주의사항

1. **parent_node_count 관리가 핵심**

   - 0이어야 스케줄링 가능
   - 스케줄링 완료 시 children의 count 감소 필수

2. **machine_dict의 9999**

   - 9999 = 처리 불가능한 기계
   - 모든 기계가 9999면 스케줄링 불가

3. **machineno 기반 작업** ⭐ NEW

   - 기계 인덱스 대신 machineno 사용
   - MachineMapper를 통한 변환

4. **opnode_dict["SELECTED_CHEMICAL"] 업데이트 시점**

   - SetupMinimizedStrategy에서만 업데이트
   - None이면 배합액 미사용 공정

5. **빈 시간창 끼워넣기**

   - 공정교체시간(delay)도 고려해야 함
   - 시간창이 충분히 큰지 검증 필요

6. **스케줄링은 단방향 전파**

   - 부모 → 자식 순서로만 진행
   - 역방향 의존성 없음 (DAG 특성)

7. **Aging 노드 자동 생성**
   - aging_map에 정의된 (GITEM, ProcGbn) 조합에 대해 자동 삽입
   - depth는 sequential insertion으로 unique 보장

---

## 🔄 주요 변경사항 (최근)

### v3.0 (현재 버전)

1. **MachineMapper 도입**

   - 기계 인덱스 → machineno 기반으로 변경
   - 기계 정보 조회 중앙화

2. **results 모듈 사용**

   - create_results → create_results
   - 5개 시트로 결과 재구성

3. **입력 파일 구조 변경**

   - aging 데이터: 통합 엑셀의 시트로 변경
   - global/local machine limit 분리

4. **run_scheduler_pipeline 도입**

   - 스케줄링 파이프라인 단순화 (wrapper function)

5. **수율 적용 로직 개선**
   - GITEM + PROCCODE 기준으로 변경
   - 10단위 반올림 추가
