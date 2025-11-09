# 스케줄링 프로젝트 구조 분석

## 🎯 프로젝트 개요
생산 스케줄링 시스템: 주문(Order) → 공정(Operation) → 기계(Machine) 할당을 최적화하는 DAG 기반 스케줄러

---

## 📂 핵심 실행 흐름 (main.py 기준)

### 1. 데이터 로딩 및 전처리
```
main.py:124 → src/validation/preprocess_production_data()
```
- 원본 엑셀 데이터 로딩 및 검증
- 출력: linespeed, operation_types, yield_data, order 등

### 2. 주문 시퀀스 생성
```
main.py:168 → src/order_sequencing/generate_order_sequences()
```
- 각 주문을 공정별로 분리
- 출력: `sequence_seperated_order` (각 행 = 하나의 공정)

### 3. DAG 시스템 생성 ⭐
```
main.py:182 → src/dag_management/create_complete_dag_system()
```
**핵심 4개 객체 생성:**
- `opnode_dict`: 노드 메타데이터
- `machine_dict`: 기계별 소요시간
- `manager` (DAGGraphManager): DAG 구조 관리
- `machine_dict`: 기계별 처리시간 딕셔너리

### 4. 스케줄링 실행 ⭐⭐⭐
```
main.py:198 → src/scheduler/run_scheduler_pipeline()
  └─> DispatchPriorityStrategy.execute()
      └─> SetupMinimizedStrategy.execute()
          └─> SchedulingCore.schedule_single_node()
```

---

## 🔧 핵심 객체 구조

### 1. opnode_dict (노드 메타데이터)
**위치:** `src/dag_management/node_dict.py:create_opnode_dict()`

**구조:**
```python
{
    node_id: {
        "OPERATION_ORDER": 공정 순서 (1, 2, 3, ...),
        "OPERATION_CODE": 공정 코드 (예: "OP1", "OP2"),
        "OPERATION_CLASSIFICATION": 공정 분류,
        "FABRIC_WIDTH": 원단 너비,
        "CHEMICAL_LIST": (배합액1, 배합액2, ...) # 튜플,
        "PRODUCTION_LENGTH": 생산 길이,
        "SELECTED_CHEMICAL": None  # 스케줄링 중 할당됨
    }
}
```

**역할:**
- 각 공정(노드)의 속성 정보 저장
- 스케줄링 중 `SELECTED_CHEMICAL`이 업데이트됨

---

### 2. machine_dict (기계별 소요시간)
**위치:** `src/dag_management/node_dict.py:create_machine_dict()`

**구조:**
```python
{
    node_id: [기계0_소요시간, 기계1_소요시간, 기계2_소요시간, ...]
}
```

**특징:**
- 소요시간 = `생산길이 / linespeed / TIME_MULTIPLIER`
- 9999 = 해당 기계에서 처리 불가능
- 예: `{"N00001": [120, 9999, 150, 200]}` → 기계1에서는 처리 불가

**역할:**
- 스케줄러가 최적 기계 선택 시 참조
- `scheduler.assign_operation()`에서 사용

---

### 3. DAGGraphManager (DAG 구조 관리자)
**위치:** `src/dag_management/dag_manager.py:DAGGraphManager`

**주요 속성:**
```python
class DAGGraphManager:
    self.nodes = {}  # {node_id: DAGNode 객체}
    self.opnode_dict = opnode_dict  # 노드 메타데이터 참조
```

**주요 메서드:**
- `build_from_dataframe(dag_df)`: DAG 구조 빌드
- `to_dataframe()`: 스케줄링 결과를 DataFrame으로 변환

**역할:**
- 모든 DAGNode 객체 관리
- 노드 간 선후 관계(children) 연결
- 스케줄링 중 노드 상태 추적

---

### 4. DAGNode (개별 노드 객체)
**위치:** `src/dag_management/dag_dataframe.py:DAGNode`

**주요 속성:**
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
    self.machine = None  # 할당된 기계 인덱스
    self.node_start = None  # 실제 시작 시간
    self.node_end = None  # 실제 종료 시간
    self.processing_time = None  # 처리 소요 시간
```

**핵심 로직:**
- `parent_node_count == 0` → 스케줄링 가능 (선행작업 모두 완료)
- 스케줄링 완료 시 → children의 `parent_node_count -= 1`
- `earliest_start = max(parent_node_end)` → 부모들이 모두 끝난 후 시작

**역할:**
- 각 공정의 스케줄링 상태 저장
- 선후 의존성 관리 (parent_node_count, children)

---

### 5. Scheduler (기계 자원 관리자)
**위치:** `src/scheduler/scheduler.py:Scheduler`

**주요 속성:**
```python
class Scheduler:
    self.machine_dict = machine_dict  # 노드별 기계 소요시간
    self.Machines = []  # Machine_Time_window 객체 리스트
    self.machine_numbers = 기계 개수
    self.delay_processor = delay_processor  # 공정교체시간 계산
```

**주요 메서드:**
- `allocate_resources()`: Machine_Time_window 객체들 생성
- `assign_operation(earliest_start, node_id, depth)`: 최적 기계 자동 선택
- `force_assign_operation(machine_idx, ...)`: 특정 기계에 강제 할당
- `machine_earliest_start(...)`: 특정 기계의 최적 시작시간 계산

**역할:**
- 기계별 스케줄 관리
- 빈 시간창(Empty_time_window) 분석
- 공정교체시간(delay) 고려한 할당

---

### 6. Machine_Time_window (기계 객체)
**위치:** `src/scheduler/machine.py:Machine_Time_window`

**주요 속성:**
```python
class Machine_Time_window:
    self.Machine_index = Machine_index  # 기계 인덱스
    self.assigned_task = []  # [(depth, node_id), ...]
    self.O_start = []  # 각 작업의 시작시간
    self.O_end = []    # 각 작업의 종료시간
    self.End_time = 0  # 기계의 마지막 작업 종료시간
```

**주요 메서드:**
- `Empty_time_window()`: 빈 시간창 계산 → (시작시간, 종료시간, 길이)
- `_Input(depth, node_id, M_Earliest, P_t)`: 작업 추가 및 정렬
- `force_Input(...)`: 기계 사용 불가 시간대 설정

**역할:**
- 각 기계의 작업 스케줄 저장
- 빈 시간창 제공 (새 작업 끼워넣기 가능)
- 작업들을 시작시간 순으로 자동 정렬

---

## 🔥 스케줄링 실행 흐름 (상세)

### 전체 구조
```
DispatchPriorityStrategy (우선순위 디스패치)
  └─> 윈도우 생성 (납기일 ±window_days)
      └─> SetupMinimizedStrategy (셋업시간 최소화)
          └─> 배합액 그룹별로 묶음
              └─> SchedulingCore.schedule_single_node() (단일 노드 스케줄링)
```

### schedule_single_node() 상세 흐름
**위치:** `src/scheduler/scheduling_core.py:105`

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
    node.machine = assignment_result.machine_index
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
2. machine_dict[node.id] 조회 → [기계별 소요시간]
   ↓
3. 각 기계의 scheduler.Machines[i].Empty_time_window() 분석
   ↓
4. 최적 기계 선택 → Machine_Time_window._Input() 호출
   ↓
5. DAGNode 업데이트:
   - node.machine = 선택된 기계
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

| 정보 유형 | 저장 위치 | 예시 |
|----------|----------|------|
| **노드 메타데이터** | `opnode_dict[node_id]` | 공정코드, 너비, 배합액 리스트 |
| **선택된 배합액** | `opnode_dict[node_id]["SELECTED_CHEMICAL"]` | "CHEM_A" |
| **기계별 소요시간** | `machine_dict[node_id]` | [120, 9999, 150] |
| **노드 스케줄 결과** | `DAGNode 객체` | machine=0, node_start=100, node_end=220 |
| **기계 스케줄** | `Machine_Time_window 객체` | assigned_task, O_start, O_end |
| **DAG 구조** | `DAGGraphManager.nodes` | 모든 DAGNode 보유, children 연결 |
| **공정교체시간** | `DelayProcessor` | 공정/배합액/너비 변경 시 지연시간 |

---

## 🎯 주요 설계 패턴

### 1. 전략 패턴 (Strategy Pattern)
**위치:** `src/scheduler/scheduling_core.py`

```python
# 기계 할당 전략
- OptimalMachineStrategy: 최적 기계 자동 선택
- ForcedMachineStrategy: 특정 기계 강제 할당

# 스케줄링 전략
- DispatchPriorityStrategy: 우선순위 디스패치
- SetupMinimizedStrategy: 셋업시간 최소화
- UserRescheduleStrategy: 사용자 재스케줄링
```

### 2. DAG (방향성 비순환 그래프)
- 각 노드는 후속 작업(children)만 알고 있음
- `parent_node_count`로 선행작업 완료 여부 추적
- 완료 시 children에게 전파 (count 감소, end_time 추가)

### 3. 빈 시간창 활용 (Empty Time Window)
- 기계의 작업 사이 빈 시간에 끼워넣기 가능
- 공정교체시간(delay)도 고려

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
scheduler.Machines[i].Empty_time_window()

# 체크 2: delay 확인
delay_processor.delay_calc_whole_process(prev_node_id, node_id, machine_idx)

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
MACHINE_INDEX = "기계인덱스"

# 결과 관련
WORK_START_TIME = "작업시작시각"
WORK_END_TIME = "작업종료시각"
ALLOCATED_WORK = "할당된일"
LATE_DAYS = "지각일수"
```

---

## 🚀 빠른 참조

### 전체 흐름 다시 보기
```
1. main.py:124 → 데이터 전처리
2. main.py:168 → 주문 시퀀스 생성
3. main.py:182 → DAG 생성 (opnode_dict, machine_dict, manager 생성)
4. main.py:198 → 스케줄링 실행
   4-1. scheduler 생성 및 초기화
   4-2. DispatchPriorityStrategy.execute()
   4-3. SetupMinimizedStrategy.execute()
   4-4. SchedulingCore.schedule_single_node()
5. main.py:217 → 결과 후처리
```

### 핵심 파일 위치
- **DAG 생성**: `src/dag_management/`
  - `dag_dataframe.py`: DAGNode, Create_dag_dataframe
  - `dag_manager.py`: DAGGraphManager
  - `node_dict.py`: opnode_dict, machine_dict 생성

- **스케줄링**: `src/scheduler/`
  - `scheduling_core.py`: 전략 패턴, 핵심 로직
  - `scheduler.py`: Scheduler 클래스
  - `machine.py`: Machine_Time_window 클래스
  - `dispatch_rules.py`: 디스패치 룰 생성

- **진입점**: `main.py`

---

## ⚠️ 중요 주의사항

1. **parent_node_count 관리가 핵심**
   - 0이어야 스케줄링 가능
   - 스케줄링 완료 시 children의 count 감소 필수

2. **machine_dict의 9999**
   - 9999 = 처리 불가능한 기계
   - 모든 기계가 9999면 스케줄링 불가

3. **opnode_dict["SELECTED_CHEMICAL"] 업데이트 시점**
   - SetupMinimizedStrategy에서만 업데이트
   - None이면 배합액 미사용 공정

4. **빈 시간창 끼워넣기**
   - 공정교체시간(delay)도 고려해야 함
   - 시간창이 충분히 큰지 검증 필요

5. **스케줄링은 단방향 전파**
   - 부모 → 자식 순서로만 진행
   - 역방향 의존성 없음 (DAG 특성)
