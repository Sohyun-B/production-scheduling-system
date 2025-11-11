# Aging 공정 구현 계획서

**작성일**: 2025-11-10
**최종 업데이트**: 2025-11-10
**구현 진행률**: ⚠️ **95% 완료** (Depth 중복 문제 미해결)

---

## 📊 빠른 현황 파악

| 항목 | 상태 | 비고 |
|------|-----|------|
| **전체 진행률** | ⚠️ 95% | Depth 중복 문제만 해결하면 100% |
| **Phase 1-5** | ✅ 완료 | 모든 핵심 기능 구현 완료 |
| **Phase 6-7** | ⏭️ 선택사항 | 구현 안 함 (불필요) |
| **Phase 8 (테스트)** | ⏳ 대기 | Depth 문제 해결 후 진행 |
| **미해결 이슈** | 🔥 1개 | **CRITICAL: Depth 중복 문제** |
| **수정 파일** | 7개 | 모두 수정 완료 |
| **추가 코드** | ~200줄 | 새 함수 4개, 새 클래스 1개 |

**🔥 CRITICAL 이슈**: [dag_dataframe.py:287-303](src/dag_management/dag_dataframe.py#L287-L303)의 Depth 중복 문제 해결 필요

---

## 1. 개요

Aging 공정은 실제 공정순서(tb_itemproc)에 없는 특별한 공정으로, 별도 테이블에서 관리되며 **overlapping이 가능한 가상 기계(기계 인덱스 -1)**에서 수행됩니다.

### 핵심 특징
- **Overlapping 가능**: 동시에 여러 aging 작업 수행 가능
- **가상 기계**: 기계 인덱스 -1 전용
- **즉시 시작**: earliest_start 기준으로 바로 시작 (기계 대기 시간 없음)
- **별도 테이블 관리**: tb_agingtime_gitem, tb_agingtime_gbn에서 관리

### 구현 완료 항목 ✅
1. ✅ **Hybrid Approach**: `Scheduler.Machines` 리스트 유지 + `aging_machine` 별도 속성
2. ✅ **machine_dict 구조 변경**: 리스트 → 딕셔너리
3. ✅ **Aging 노드 감지**: `set(machine_info.keys()) == {-1}`
4. ✅ **Overlapping 지원**: `Machine_Time_window.allow_overlapping=True`
5. ✅ **전략 패턴 통합**: `AgingMachineStrategy` 클래스
6. ✅ **자동 필터링**: `opnode_dict` 기반 aging 노드 자동 제외

### 미해결 항목 ⚠️
1. 🔥 **CRITICAL**: Depth 중복 문제 - [상세 내용 보기](#-미해결-이슈)

---

## 2. 구현 단계별 계획

### 단계 1: 데이터 구조 확장

#### 1.1 Aging 노드 식별

**중요**: Aging 노드는 **opnode_dict에 포함되지 않음**
- `opnode_dict`: setup 시간 계산용 (CHEMICAL_LIST 등 필요)
- Aging 기계는 setup time이 없으므로 불필요
- Aging 노드는 **DAGNode + machine_dict만 생성**

**식별 방법 (권장)**: DAGNode에 `is_aging` 속성 추가
```python
class DAGNode:
    def __init__(self, node_id, depth, is_aging=False):
        ...
        self.is_aging = is_aging

# 사용
if node.is_aging:
    return self._assign_to_aging_machine(...)
```

**보조 방법**: node_id 패턴 (`{parent_node_id}_AGING`)

**opnode_dict 미사용 시 수정 필요 위치**:
| 위치 | 해결 방법 |
|------|----------|
| SetupMinimizedStrategy | aging 노드면 스킵 |
| find_best_chemical | aging 노드 제외 |
| DAGGraphManager.build_from_dataframe | is_aging=True 설정 |

**헬퍼 함수**:
```python
def is_aging_node(node):
    return hasattr(node, 'is_aging') and node.is_aging
```

#### 1.2 machine_dict 구조 변경

**기존**: `{node_id: [time_0, time_1, ...]}`
**변경**: `{node_id: {machine_index: processing_time}}`

**변경 이유 (필수)**:
1. **enumerate 문제**: 리스트는 `enumerate(machine_info)`로 순회 시 0부터만 카운트 → aging 기계(-1) 접근 불가
2. **명시성**: 딕셔너리는 `machine_info[-1]`로 명확하게 aging 기계 구분
3. **aging 판별**: `set(machine_info.keys()) == {-1}`로 aging 노드 명확하게 식별

**일반 노드**: `{node_id: {0: time_0, 1: time_1, ..., n: time_n}}`
**Aging 노드**: `{aging_node_id: {-1: aging_time}}`

**create_machine_dict() 수정**:
```python
def create_machine_dict(sequence_seperated_order, linespeed, machine_columns, aging_nodes_dict=None):
    machine_dict = {}

    # 일반 노드: 기존 로직 + 딕셔너리 구조로 변경
    for _, row in order_linespeed.iterrows():
        node_id = row[config.columns.ID]
        machine_dict[node_id] = {}
        for idx, col in enumerate(machine_columns):
            processing_time = calculate_time(...)  # 기존 로직
            machine_dict[node_id][idx] = processing_time

    # Aging 노드
    if aging_nodes_dict:
        for aging_node_id, aging_time in aging_nodes_dict.items():
            machine_dict[aging_node_id] = {-1: aging_time}

    return machine_dict
```

**assign_operation() 주요 수정사항**:
```python
# enumerate → items
for machine_index, machine_processing_time in machine_info.items():
    if machine_index == -1:  # aging 기계 제외
        continue
    ...
```

---

### 단계 2: DAG 생성 시 Aging 노드 추가

#### 2.1 aging_df 파싱

**aging_df 컬럼 구조**:
- `gitemno`: 품목 번호
- `proccode`: aging 공정을 하기 **이전**의 공정 코드
- `aging_time`: aging 소요 시간 (30분 단위)

**parse_aging_requirements() 함수**:
```python
def parse_aging_requirements(aging_df, sequence_seperated_order):
    """
    aging_df를 파싱하여 어떤 노드 이후에 aging을 삽입할지 결정

    Returns:
        aging_map: {
            parent_node_id: {
                "aging_time": 48,
                "aging_node_id": "N00001_AGING",
                "next_node_id": "N00002"
            }
        }
    """
    aging_map = {}

    for _, row in aging_df.iterrows():
        gitemno = row['gitemno']
        proccode = row['proccode']  # aging 이전 공정
        aging_time = int(row['aging_time'])

        # sequence_seperated_order에서 해당 gitem + proccode 노드 찾기
        matches = sequence_seperated_order[
            (sequence_seperated_order[config.columns.GITEM] == gitemno) &
            (sequence_seperated_order[config.columns.OPERATION_CODE] == proccode)
        ]

        for _, match_row in matches.iterrows():
            parent_node_id = match_row[config.columns.ID]
            aging_node_id = f"{parent_node_id}_AGING"

            # 다음 노드 찾기 (같은 P/O NO, operation_order + 1)
            next_op_order = match_row[config.columns.OPERATION_ORDER] + 1
            next_node = sequence_seperated_order[
                (sequence_seperated_order[config.columns.PO_NO] == match_row[config.columns.PO_NO]) &
                (sequence_seperated_order[config.columns.OPERATION_ORDER] == next_op_order)
            ]

            next_node_id = next_node.iloc[0][config.columns.ID] if len(next_node) > 0 else None

            aging_map[parent_node_id] = {
                "aging_time": aging_time,
                "aging_node_id": aging_node_id,
                "next_node_id": next_node_id
            }

    return aging_map
```

**구현 위치**: `src/dag_management/dag_dataframe.py` 또는 별도 유틸리티 파일

#### 2.2 DAG에 Aging 노드 삽입

**Aging 노드 ID 규칙**: `{parent_node_id}_AGING`

**DAG 구조 변경**:
```
기존: [공정A] -> [공정B]
변경: [공정A] -> [공정A_AGING] -> [공정B]
```

**insert_aging_nodes_to_dag() 함수**:
```python
def insert_aging_nodes_to_dag(dag_df, aging_map):
    """
    dag_df에 aging 노드 추가 및 부모-자식 관계 재설정

    Args:
        dag_df: columns [ID, DEPTH, CHILDREN]
        aging_map: parse_aging_requirements() 결과

    Returns:
        수정된 dag_df
    """
    new_rows = []

    # 1. 기존 노드의 CHILDREN 수정
    for idx, row in dag_df.iterrows():
        parent_node_id = row['ID']

        if parent_node_id in aging_map:
            aging_info = aging_map[parent_node_id]
            aging_node_id = aging_info['aging_node_id']
            next_node_id = aging_info['next_node_id']

            # CHILDREN 파싱
            children = row['CHILDREN']
            if isinstance(children, str):
                children_list = [c.strip() for c in children.split(',') if c.strip()]
            else:
                children_list = []

            # next_node_id 제거, aging_node_id 추가
            if next_node_id and next_node_id in children_list:
                children_list.remove(next_node_id)
            children_list.append(aging_node_id)

            dag_df.at[idx, 'CHILDREN'] = ', '.join(children_list)

            # 2. aging 노드 생성
            new_rows.append({
                'ID': aging_node_id,
                'DEPTH': row['DEPTH'] + 1,  # parent depth + 1
                'CHILDREN': next_node_id if next_node_id else ''
            })

    # 3. 새 노드 추가
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        dag_df = pd.concat([dag_df, new_df], ignore_index=True)
        dag_df = dag_df.sort_values(['DEPTH', 'ID']).reset_index(drop=True)

    return dag_df
```

**depth 처리**: parent.depth + 1 (depth 중복 허용, parent_node_count로 순서 결정)

**구현 위치**: `src/dag_management/dag_dataframe.py`

#### 2.3 create_complete_dag_system() 수정

**함수 시그니처 변경**:
```python
def create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info, aging_map=None):
```

**내부 로직 수정**:
```python
def create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info, aging_map=None):
    merged_df = make_process_table(sequence_seperated_order)
    hierarchy = sorted(...)

    # 기존 DAG 생성
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(...)

    # aging 노드 처리
    if aging_map:
        print("[42%] Aging 노드 DAG에 삽입 중...")

        # 1. dag_df에 aging 노드 추가
        dag_df = insert_aging_nodes_to_dag(dag_df, aging_map)

        # 2. machine_dict에 aging 노드 추가
        for parent_id, info in aging_map.items():
            aging_node_id = info['aging_node_id']
            aging_time = info['aging_time']
            machine_dict[aging_node_id] = {-1: aging_time}

        # 3. DAGGraphManager 재빌드 (aging 노드 포함)
        manager = DAGGraphManager(opnode_dict)
        manager.build_from_dataframe(dag_df)

        # 4. aging 노드에 is_aging 플래그 설정
        for parent_id, info in aging_map.items():
            aging_node_id = info['aging_node_id']
            if aging_node_id in manager.nodes:
                manager.nodes[aging_node_id].is_aging = True

    return dag_df, opnode_dict, manager, machine_dict, merged_df
```

**구현 위치**: `src/dag_management/__init__.py`

---

### 단계 3: Machine_Time_window 확장

**플래그 추가**:
```python
class Machine_Time_window:
    def __init__(self, Machine_index, allow_overlapping=False):
        ...
        self.allow_overlapping = allow_overlapping
```

**_Input() 메서드 수정**:
```python
def _Input(self, depth, node_id, M_Earliest, P_t, ...):
    if self.allow_overlapping:
        # overlapping: 빈 시간 체크 없이 바로 추가
        self.assigned_task.append([depth, node_id])
        self.O_start.append(M_Earliest)
        self.O_end.append(M_Earliest + P_t)
        self.O_start.sort()
        self.O_end.sort()
        self.End_time = max(self.End_time, M_Earliest + P_t)
    else:
        # 기존 로직
        ...
```

---

### 단계 4: Scheduler 수정 (Hybrid Approach)

#### 4.1 Machines 구조 수정

**핵심 전략**:
- ✅ `self.Machines` **리스트 유지** (기존 코드 호환성)
- ✅ `self.aging_machine` **별도 속성 추가** (aging 전용)
- ✅ `get_machine()` **통합 접근자 제공** (향후 확장성)

**4.1.1 Scheduler.__init__() 수정**:
```python
class Scheduler:
    def __init__(self, machine_dict, machine_numbers, delay_processor):
        self.machine_dict = machine_dict
        self.machine_numbers = machine_numbers
        self.delay_processor = delay_processor
        self.Machines = []  # 일반 기계들 (리스트 유지)
        self.aging_machine = None  # aging 전용 기계 (별도 속성)
```

**4.1.2 allocate_resources() 수정**:
```python
def allocate_resources(self):
    # 일반 기계 생성 (기존 방식 유지)
    self.Machines = [
        Machine_Time_window(i)
        for i in range(self.machine_numbers)
    ]

    # Aging 기계 생성 (별도 속성)
    self.aging_machine = Machine_Time_window(-1, allow_overlapping=True)
```

**4.1.3 get_machine() 통합 접근자 추가** (새로 추가):
```python
def get_machine(self, machine_index):
    """
    통합 기계 접근자

    Args:
        machine_index: 기계 인덱스 (0~n-1: 일반, -1: aging)

    Returns:
        Machine_Time_window 객체
    """
    if machine_index == -1:
        return self.aging_machine
    return self.Machines[machine_index]
```

**영향받는 코드**:
- ✅ 기존 `self.Machines[i]` 코드는 **수정 불필요** (리스트 유지)
- ✅ 기존 `for machine in self.Machines` 코드는 **수정 불필요** (리스트 순회)
- 기계 -1 접근 시: `self.aging_machine` 또는 `self.get_machine(-1)` 사용
- 동적 인덱스 접근: `self.get_machine(idx)` 사용 권장

**수정 필요 위치**:
- `assign_operation()`: aging 감지 및 aging_machine 사용
- `machine_earliest_start()`: machine_index == -1 체크
- `create_machine_schedule_dataframe()`: aging_machine 별도 처리
- `allocate_machine_downtime()`: 변경 불필요 (기계 -1 이미 제외됨)

#### 4.2 주요 메서드 수정

**4.2.1 assign_operation() - Aging 감지 및 할당**:

```python
def assign_operation(self, earliest_start, node_id, depth):
    machine_info = self.machine_dict[node_id]

    # ✅ Aging 노드 감지 (machine_dict 구조 기반)
    is_aging = set(machine_info.keys()) == {-1}

    if is_aging:
        # Aging 전용 할당
        processing_time = machine_info[-1]
        start_time = earliest_start  # 즉시 시작
        self.aging_machine._Input(depth, node_id, start_time, processing_time)
        return AssignmentResult(
            machine_index=-1,
            start_time=start_time,
            processing_time=processing_time
        )

    # 일반 기계 할당
    best_machine = None
    best_end_time = float('inf')

    # ✅ enumerate → items() 변경 (machine_dict가 딕셔너리이므로)
    for machine_index, machine_processing_time in machine_info.items():
        if machine_index == -1:  # Skip aging (이미 위에서 처리됨)
            continue
        if machine_processing_time >= 9999:
            continue

        # ✅ 리스트 접근 (변경 없음)
        machine = self.Machines[machine_index]
        earliest = self.machine_earliest_start(
            machine_index, earliest_start, node_id, depth
        )
        end_time = earliest + machine_processing_time

        if end_time < best_end_time:
            best_machine = machine_index
            best_end_time = end_time

    # 최적 기계에 할당
    ...
```

**4.2.2 machine_earliest_start() 수정**:

```python
def machine_earliest_start(self, machine_index, earliest_start, node_id, depth):
    # ✅ Aging 기계는 즉시 시작
    if machine_index == -1:
        return earliest_start

    # ✅ 일반 기계 로직 (리스트 접근, 변경 없음)
    machine = self.Machines[machine_index]
    # ... 기존 로직 (Empty_time_window 체크 등)
```

**4.2.3 allocate_machine_downtime() 수정**:

```python
def allocate_machine_downtime(self, downtime_df):
    # ✅ 일반 기계만 처리 (리스트 순회, 변경 없음)
    for machine in self.Machines:
        # ... 휴식 시간 할당
    # aging_machine은 가상 기계이므로 휴식 없음 (별도 처리 불필요)
```

**4.2.4 create_machine_schedule_dataframe() 수정**:

```python
def create_machine_schedule_dataframe(self):
    all_schedules = []

    # ✅ 일반 기계 (리스트 순회, 변경 없음)
    for machine in self.Machines:
        schedules = machine.get_schedule()
        all_schedules.extend(schedules)

    # ✅ Aging 기계 추가
    if self.aging_machine:
        aging_schedules = self.aging_machine.get_schedule()
        all_schedules.extend(aging_schedules)

    return pd.DataFrame(all_schedules)
```

---

### 단계 5: SchedulingCore 수정

**5.1 AgingMachineStrategy 생성**:

```python
class AgingMachineStrategy(MachineAssignmentStrategy):
    """Aging 전용 기계 할당 전략"""

    def assign(self, scheduler, node, earliest_start):
        node_id = node.id
        machine_info = scheduler.machine_dict[node_id]

        # ✅ Aging 노드 검증
        if set(machine_info.keys()) != {-1}:
            raise ValueError(f"Node {node_id} is not an aging node")

        processing_time = machine_info[-1]
        start_time = earliest_start  # 즉시 시작

        # Aging 기계에 할당
        scheduler.aging_machine._Input(
            node.depth,
            node_id,
            start_time,
            processing_time
        )

        return AssignmentResult(
            machine_index=-1,
            start_time=start_time,
            processing_time=processing_time
        )
```

**5.2 schedule_single_node() 수정**:

```python
def schedule_single_node(node, scheduler, machine_assignment_strategy):
    if node.parent_node_count != 0:
        return False

    earliest_start = max(node.parent_node_end)

    # ✅ Aging 노드 감지 (machine_dict 구조 기반)
    machine_info = scheduler.machine_dict[node.id]
    is_aging = set(machine_info.keys()) == {-1}

    if is_aging:
        # Aging 전용 전략 사용
        strategy = AgingMachineStrategy()
        assignment_result = strategy.assign(scheduler, node, earliest_start)
    else:
        # 일반 전략 사용
        assignment_result = machine_assignment_strategy.assign(
            scheduler, node, earliest_start
        )

    # 노드 상태 업데이트
    node.machine = assignment_result.machine_index
    node.node_start = assignment_result.start_time
    node.processing_time = assignment_result.processing_time
    node.node_end = assignment_result.start_time + assignment_result.processing_time

    # 후속 작업 업데이트
    for child in node.children:
        child.parent_node_count -= 1
        child.parent_node_end.append(node.node_end)

    return True
```

**5.3 SetupMinimizedStrategy.execute() 수정**:

```python
def execute(self, scheduler, nodes, ...):
    # ✅ Aging 노드 필터링 (배합액 선택 제외)
    non_aging_nodes = [
        node for node in nodes
        if set(scheduler.machine_dict[node.id].keys()) != {-1}
    ]

    # Setup 최소화는 일반 노드만 대상
    ...
```

**5.4 find_best_chemical() 수정**:

```python
def find_best_chemical(nodes, scheduler):
    # ✅ Aging 노드 제외
    non_aging_nodes = [
        node for node in nodes
        if set(scheduler.machine_dict[node.id].keys()) != {-1}
    ]

    # 배합액 선택 로직
    ...
```

---

### 단계 6: DelayProcessor 수정

- `delay_calc_whole_process()`에서 aging 노드는 딜레이 0

---

### 단계 7: 결과 처리

- 기계 인덱스 -1을 "AGING" 표시
- 결과 DataFrame에 aging 공정 포함

---

---

### 단계 8: main.py 실행 흐름

**수정 위치**: `main.py:182` (create_complete_dag_system 호출 직전)

**수정 전**:
```python
# === 4단계: DAG 생성 (내부에서 aging_map 자동 생성) ===
print("[40%] DAG 시스템 생성 중...")
dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
    sequence_seperated_order, linespeed, machine_master_info)
```

**수정 후**:
```python
# === 4단계: DAG 생성 ===
print("[40%] DAG 시스템 생성 중...")

# aging 요구사항 파싱
print("[38%] Aging 요구사항 파싱 중...")
aging_map = parse_aging_requirements(aging_df, sequence_seperated_order)
print(f"[INFO] {len(aging_map)}개의 aging 노드 생성 예정")

# DAG 생성 (aging_map 전달)
dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
    sequence_seperated_order, linespeed, machine_master_info, aging_map=aging_map)
```

**import 추가**:
```python
# main.py 상단
from src.dag_management import create_complete_dag_system
from src.dag_management.dag_dataframe import parse_aging_requirements  # 추가
```

---

## 3. 핵심 고려사항

### 3.1 Aging 노드 정의

| 항목 | 값 |
|------|-----|
| **ID 규칙** | `{parent_node_id}_AGING` |
| **depth** | parent.depth + 1 |
| **시간 단위** | 30분 단위 |
| **기계 인덱스** | -1 (고정) |

### 3.2 Aging 노드 감지 전략 (Hybrid Approach)

**이중 감지 메커니즘**:
1. **Primary**: `machine_dict` 구조 체크 (빠르고 간단)
2. **Secondary**: `DAGNode.is_aging` 속성 체크 (명시적, 선택적)

**구현**:
```python
def is_aging_node(node_id, machine_dict):
    """
    Aging 노드 감지

    Args:
        node_id: 노드 ID
        machine_dict: 기계 딕셔너리

    Returns:
        True if node is aging operation
    """
    if node_id not in machine_dict:
        return False

    # machine_dict가 {-1: time}만 가지면 aging
    return set(machine_dict[node_id].keys()) == {-1}
```

**Optional: DAGNode 속성 활용** (추가 검증용):
```python
def is_aging_node_with_attribute(node, machine_dict):
    """
    Combined detection using both methods
    """
    # Method 1: DAGNode attribute (if available)
    if hasattr(node, 'is_aging') and node.is_aging:
        return True

    # Method 2: machine_dict structure (fallback)
    return set(machine_dict[node.id].keys()) == {-1}
```

**사용 위치**:
- `Scheduler.assign_operation()`: 기계 할당 분기
- `SchedulingCore.schedule_single_node()`: 전략 선택
- `SetupMinimizedStrategy`: aging 노드 필터링 (배합액 선택 제외)
- `DelayProcessor`: aging 전후 딜레이 0 처리

### 3.3 DAG 삽입 로직

**aging_df 필요 정보**:
- 어떤 gitem의 어떤 공정 이후 aging?
- aging 시간 (30분 단위 변환 필요?)

**다중 aging**: 하나의 공정 → 하나의 aging → 하나의 다음 공정 (가정)

### 3.4 테스트 시나리오

1. **기본**: 공정A → Aging → 공정B
2. **Overlapping**: 아이템1 Aging(10~14), 아이템2 Aging(12~15) → 겹침 허용
3. **다중 부모**: 공정A,B 완료 → Aging (max 종료시간 기준)

---

## 4. 구현 체크리스트

### Phase 1: 데이터 구조 ✅ **완료 (100%)**
- [x] machine_dict 딕셔너리 구조로 변경
- [x] create_machine_dict() 수정 (aging_nodes_dict 파라미터)
- [x] DAGNode에 is_aging 속성 추가
- [x] is_aging_node() 헬퍼 함수 작성

### Phase 2: DAG 생성 ⚠️ **대부분 완료 (95%)**
- [x] `parse_aging_requirements()` 함수 작성 (`src/dag_management/dag_dataframe.py`)
  - [x] aging_df에서 gitemno, proccode, aging_time 읽기
  - [x] sequence_seperated_order와 매칭하여 parent_node_id 찾기
  - [x] 다음 노드(next_node_id) 찾기
  - [x] aging_map 딕셔너리 생성
  - ⚠️ P/O NO 매칭 로직에 경고 주석 추가됨 (Line 223-227)
- [x] `insert_aging_nodes_to_dag()` 함수 작성 (`src/dag_management/dag_dataframe.py`)
  - [x] dag_df의 CHILDREN 컬럼 수정
  - [x] aging 노드 행 생성 (ID, DEPTH, CHILDREN)
  - [x] dag_df에 새 행 추가 및 정렬
  - ⚠️⚠️⚠️ **CRITICAL**: Depth 중복 문제 주석 작성됨 (Line 287-303) - **미해결!**
- [x] `create_complete_dag_system()` 수정 (`src/dag_management/__init__.py`)
  - [x] 함수 시그니처에 aging_map 파라미터 추가
  - [x] insert_aging_nodes_to_dag() 호출
  - [x] machine_dict에 aging 노드 추가
  - [x] DAGGraphManager 재빌드
  - [x] aging 노드에 is_aging 플래그 설정
- [x] `main.py` 수정
  - [x] parse_aging_requirements import 추가
  - [x] aging_map 생성 코드 추가
  - [x] create_complete_dag_system()에 aging_map 전달

### Phase 3: Machine 클래스 ✅ **완료 (100%)**
- [x] Machine_Time_window에 allow_overlapping 플래그
- [x] _Input() overlapping 지원

### Phase 4: Scheduler (Hybrid Approach) ✅ **완료 (100%)**
- [x] **Machines 리스트 유지** (딕셔너리 변경 ❌)
- [x] **aging_machine 속성 추가** (별도 Machine_Time_window)
- [x] **get_machine() 메서드 추가** (통합 접근자)
- [x] allocate_resources()에 aging_machine 생성 코드 추가
- [x] assign_operation() 수정
  - [x] Aging 감지 로직 추가 (machine_dict 체크)
  - [x] aging_machine 사용 코드 추가
  - [x] enumerate→items 변경 (machine_dict 순회용)
- [x] machine_earliest_start() 수정 (get_machine() 사용)
- [x] create_machine_schedule_dataframe() 수정 (aging_machine 추가)
- [x] allocate_machine_downtime() 확인 (변경 불필요)

### Phase 5: SchedulingCore ✅ **완료 (100%)**
- [x] AgingMachineStrategy 클래스 작성
- [x] schedule_single_node() aging 감지 추가
- [x] SetupMinimizedStrategy aging 필터링 (opnode_dict 자동 필터링)
- [x] find_best_chemical() aging 필터링 (opnode_dict 자동 필터링)

### Phase 6: DelayProcessor ⏭️ **선택사항 - 구현 안 함**
- [ ] aging 딜레이 0 처리
  - **이유**: Aging 노드는 가상 기계이므로 딜레이 계산 자체가 무의미
  - **현재 상태**: assign_operation()에서 조기 리턴하므로 딜레이 계산 안 함

### Phase 7: 결과 처리 ⏭️ **선택사항 - 구현 안 함**
- [ ] create_results() 기계 -1 표시 개선
  - **이유**: 기계 인덱스 -1만으로 충분히 구분 가능
  - **향후**: 필요 시 추가 가능

### Phase 8: 테스트 ⏳ **대기 중**
- [ ] 기본/Overlapping/다중부모 시나리오 테스트
  - **선행 조건**: Depth 중복 문제 해결 필요

---

## 📊 구현 현황 요약

| Phase | 상태 | 진행률 | 비고 |
|-------|-----|-------|------|
| Phase 1 | ✅ 완료 | 100% | machine_dict 구조 변경, DAGNode.is_aging 추가 |
| Phase 2 | ⚠️ 대부분 완료 | 95% | **Depth 중복 문제 미해결** (Line 287-303) |
| Phase 3 | ✅ 완료 | 100% | Overlapping 지원 |
| Phase 4 | ✅ 완료 | 100% | Hybrid Approach 적용 |
| Phase 5 | ✅ 완료 | 100% | 전략 패턴 통합 |
| Phase 6 | ⏭️ 선택사항 | - | 구현 안 함 (불필요) |
| Phase 7 | ⏭️ 선택사항 | - | 구현 안 함 (우선순위 낮음) |
| Phase 8 | ✅ 부분 완료 | 80% | Dispatch Priority 문제 해결, Depth 문제 남음 |
| **전체** | **⚠️ 대부분 완료** | **97%** | **Depth 중복 문제만 해결하면 100%** |

---

## ⚠️ 미해결 이슈

### 🔥 CRITICAL #1: Aging 노드 Dispatch Priority 문제

**발견일**: 2025-11-10
**위치**: `src/scheduler/scheduling_core.py` DispatchPriorityStrategy.execute()

**문제**:
1. **Due Date 부재**: Aging 노드는 `sequence_seperated_order`에 없어서 due_date가 없음
2. **Priority Order 포함**: create_dispatch_rule()이 모든 노드(Aging 포함)를 priority_order에 포함
3. **스케줄링 누락**: due_date가 없는 Aging 노드는 `result` 리스트에서 제외됨
4. **IndexError 발생**: 모든 노드가 제외되면 window_result가 빈 리스트가 되어 `window_result[0]` 접근 시 에러

**로직적 문제**:
- Aging 노드를 dispatch priority에 포함시키는 것 자체가 논리적으로 맞지 않음
- Aging은 선행 공정 완료 즉시 자동으로 시작되어야 함 (due_date 우선순위 무관)

**영향**:
- 런타임 에러: `IndexError: list index out of range` (Line 549)
- Aging 노드가 스케줄링되지 않음

**해결 방안** (2025-11-10 확정 - Option 1 채택):

### 설계 원칙
- **단일 책임 원칙 (SRP)**: 각 메서드는 하나의 책임만 가짐
- **응집도 향상**: 스케줄링 로직을 SchedulingCore에 집중
- **결합도 감소**: update_dependencies()는 의존성 업데이트만 담당

### 구현 방법

**1. DispatchPriorityStrategy에서 Aging 제외**:
```python
# priority_order를 필터링하여 Aging 노드 제외
filtered_priority = [
    node_id for node_id in priority_order
    if not (scheduler.machine_dict.get(node_id) and
            set(scheduler.machine_dict[node_id].keys()) == {-1})
]
# 일반 노드만 dispatch 우선순위 기반 스케줄링
```

**2. schedule_ready_aging_children() 새 메서드 추가** (Option 1):
```python
@staticmethod
def schedule_ready_aging_children(node, scheduler):
    """
    완료된 노드의 자식 중 스케줄 가능한 Aging 노드를 자동 스케줄링

    책임: Aging 노드 자동 스케줄링
    호출 시점: schedule_single_node()에서 의존성 업데이트 직후

    Args:
        node: 완료된 DAGNode 인스턴스
        scheduler: Scheduler 인스턴스
    """
    for child in node.children:
        if child.parent_node_count == 0:  # 스케줄 가능
            machine_info = scheduler.machine_dict.get(child.id)
            is_aging = machine_info and set(machine_info.keys()) == {-1}

            if is_aging:
                print(f"[INFO] Aging 노드 {child.id} 자동 스케줄링")
                SchedulingCore.schedule_single_node(
                    child,
                    scheduler,
                    AgingMachineStrategy()
                )
```

**3. schedule_single_node() 수정**:
```python
# 5. 후속 작업 의존성 업데이트
SchedulingCore.update_dependencies(node)

# 6. Aging 자식 노드 자동 스케줄링
SchedulingCore.schedule_ready_aging_children(node, scheduler)
```

**4. 방어 코드 추가**:
```python
# DispatchPriorityStrategy.execute()에서
if not window_result:
    print(f"[WARNING] 윈도우가 비어있음")
    break  # 또는 result = result[1:]

if not used_ids:
    print(f"[WARNING] 노드가 스케줄링되지 않음")
    result = result[1:]  # 무한루프 방지
```

**구현 체크리스트**:
- [x] 문제 분석 완료
- [x] 설계 원칙 확정 (Option 1: 별도 메서드 분리)
- [x] `SchedulingCore.schedule_ready_aging_children()` 메서드 추가 (Line 104-127)
- [x] `SchedulingCore.schedule_single_node()` 수정 (Line 179-180, 6번 단계 추가)
- [x] `DispatchPriorityStrategy.execute()` 수정 (Line 540-552, Aging 필터링)
- [x] 무한루프 방지 코드 추가 (Line 598-601)
- [x] 테스트 실행 - **IndexError 완전 해결!**

**구현 결과 (2025-11-10 완료)**:
```
✅ Aging 노드 필터링 성공
[INFO] Priority order: 전체 4개 노드 중 일반 2개, Aging 2개

✅ Aging 자동 스케줄링 성공
[INFO] Aging 노드 32409_24000_1300_T01824_4_M10_AGING 자동 스케줄링 (parent ... 완료)
[INFO] Aging 노드 32409_23100_1300_T01862_4_M10_AGING 자동 스케줄링 (parent ... 완료)

✅ 스케줄링 완료
[LOG] DispatchPriorityStrategy: used_ids= 1 (정상 진행)
```

**상태**: ✅ **해결 완료**

---

### 🔥 CRITICAL #2: Depth 중복 문제

**발견일**: 2025-11-10
**위치**: `src/dag_management/dag_dataframe.py` Line 287-303

**문제**:
- 현재 구현: `aging_depth = parent_depth + 1`
- 예: Parent(depth=2) → Aging(depth=3) → Next(depth=3) ❌ DUPLICATE!

**근본 원인**:
```python
# insert_aging_nodes_to_dag()에서 Aging 노드 depth 할당
aging_depth = parent_depth + 1  # ← 문제 발생 지점

# 만약 다음 노드가 이미 depth=3을 가지고 있다면?
# → 중복 발생!
```

**실제 에러 사례**:
```
KeyError: '3_proccode'

merged_df.columns: Index(['pono', '1_proccode', '2_proccode'], dtype='object')
               ↑
         '3_proccode' 컬럼이 없음!
```

**에러 발생 경로**:
1. `insert_aging_nodes_to_dag()`: Aging(depth=3), Next(depth=3) 중복 생성
2. `make_process_table()`: Pivot table 생성 시 컬럼명 중복 → 덮어씀
   ```python
   # dag_dataframe.py Line 111-137
   pivot_df = df_exploded.pivot_table(
       columns='operation_col',  # "1공정", "2공정", "3공정" ...
       values=config.columns.ID,
       aggfunc='first'  # ← DUPLICATE시 하나만 선택됨!
   )
   ```
3. `late_processor.py` Line 32: "3_proccode" 컬럼 접근 시도 → KeyError!

**영향 범위 분석**:
- **Column Naming**: `late_processor.py:32` - depth 기반 컬럼명 생성
- **Node Ordering**: `dag_dataframe.py:138` - depth 기준 정렬
- **Machine Tasks**: `machine.py:26` - `[depth, node_id]` 튜플 사용
- **Visualization**: `draw_gantt.py:61` - depth 기반 색상 코딩
- **Entry Detection**: `dispatch_rules.py:30` - `depth==1` 노드 검색

**해결 방안**:

#### **Option 1: Depth Shift 방식** (✅ 채택)
- Aging 노드 삽입 후 모든 후속 노드(descendants)의 depth를 +1씩 shift
- 장점:
  - 컬럼명 체계 유지 (1공정, 2공정, 3공정, ...)
  - late_processor 수정 불필요
  - 기존 로직과 호환성 높음
- 단점:
  - DAG 전체 순회 필요 (성능 영향 미미)

**구현 알고리즘**:
```python
def shift_depths_after_aging(aging_node_id, aging_depth, df):
    """
    Aging 노드 삽입 후 후속 노드들의 depth +1 증가

    예시:
    Before: A(d=1) → B(d=2) → C(d=3) → D(d=4)
    Insert Aging after B
    After:  A(d=1) → B(d=2) → Aging(d=3) → C(d=4) → D(d=5)
    """
    # 1. Aging 노드의 모든 후손(descendants) 찾기
    descendants = []
    queue = [aging_node_id]
    visited = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        # 자식 노드들 찾기
        children_rows = df[df[config.columns.PARENT_ID] == current_id]
        for _, child_row in children_rows.iterrows():
            child_id = child_row[config.columns.ID]
            child_depth = child_row[config.columns.OPERATION_ORDER]

            # Aging depth 이상인 후손들만 shift 대상
            if child_depth >= aging_depth:
                descendants.append(child_id)
                queue.append(child_id)

    # 2. 후손 노드들의 depth +1 증가
    if descendants:
        print(f"[INFO] Depth Shift: {len(descendants)}개 노드 depth +1")
        mask = df[config.columns.ID].isin(descendants)
        df.loc[mask, config.columns.OPERATION_ORDER] += 1

    return df
```

**호출 위치**:
```python
# insert_aging_nodes_to_dag() 내부
# Aging 노드 추가 후
dag_df = pd.concat([dag_df, pd.DataFrame([new_aging_node])], ignore_index=True)

# 후손 노드들의 depth shift
dag_df = shift_depths_after_aging(
    aging_node_id=aging_node_id,
    aging_depth=aging_depth,
    df=dag_df
)
```

**테스트 케이스**:
1. **Single Aging**:
   ```
   Before: A(1) → B(2) → C(3)
   After:  A(1) → B(2) → Aging(3) → C(4)
   Columns: ['1_proccode', '2_proccode', '3_proccode', '4_proccode'] ✓
   ```

2. **Multiple Aging**:
   ```
   Before: A(1) → B(2) → C(3) → D(4)
   Insert Aging1 after A, Aging2 after B
   After:  A(1) → Aging1(2) → B(3) → Aging2(4) → C(5) → D(6)
   Columns: ['1_proccode', ..., '6_proccode'] ✓
   ```

3. **Branching DAG**:
   ```
   Before:      A(1)
               /    \
            B(2)    C(2)
               \    /
                D(3)

   Insert Aging after A
   After:       A(1)
                 |
            Aging(2)
               /    \
            B(3)    C(3)
               \    /
                D(4)
   ```

#### **Option 2: 소수점 Depth** (❌ 기각)
- Aging 노드에 소수점 depth 부여 (예: 2.5)
- 단점:
  - late_processor.py 수정 필요 (컬럼명 생성 로직)
  - int → float 타입 변경
  - 기존 depth 기반 로직 전면 수정

**구현 계획**:
- [ ] `shift_depths_after_aging()` 함수 추가
- [ ] `insert_aging_nodes_to_dag()`에서 depth shift 호출
- [ ] 모든 Aging 노드 삽입 후 재정렬
- [ ] 테스트 케이스 검증

**현재 상태**: ⚠️ **계획 수립 완료, 구현 대기 중**

---

## 5. 수정 파일 목록

| 파일 | 수정 내용 | 상태 | 우선순위 |
|------|----------|------|---------|
| **`src/dag_management/dag_dataframe.py`** | ✅ DAGNode.is_aging 속성 추가<br>✅ parse_aging_requirements() 함수 추가<br>✅ insert_aging_nodes_to_dag() 함수 추가<br>⚠️ **Depth 중복 문제 주석 작성** (Line 287-303) | ⚠️ 95% | Critical |
| **`src/dag_management/__init__.py`** | ✅ create_complete_dag_system() 시그니처 변경<br>✅ aging_map 처리 로직 추가 | ✅ 100% | Critical |
| **`main.py`** | ✅ parse_aging_requirements import<br>✅ aging_map 생성<br>✅ create_complete_dag_system()에 aging_map 전달 | ✅ 100% | Critical |
| **`src/dag_management/node_dict.py`** | ✅ create_machine_dict() 딕셔너리 구조 변경<br>✅ aging_nodes_dict 파라미터 추가 | ✅ 100% | Critical |
| **`src/scheduler/scheduler.py`** | ✅ **aging_machine 속성 추가** (별도 속성)<br>✅ **get_machine() 메서드 추가** (통합 접근자)<br>✅ allocate_resources()에 aging_machine 생성<br>✅ assign_operation() aging 감지 추가<br>✅ assign_operation() enumerate → items<br>✅ machine_earliest_start() get_machine() 사용<br>✅ create_machine_schedule_dataframe() aging_machine 포함<br>✅ **Machines는 리스트 유지** | ✅ 100% | High |
| **`src/scheduler/machine.py`** | ✅ Machine_Time_window에 allow_overlapping 플래그<br>✅ _Input() overlapping 지원 | ✅ 100% | High |
| **`src/scheduler/scheduling_core.py`** | ✅ AgingMachineStrategy 클래스 추가<br>✅ schedule_single_node() aging 감지<br>✅ SetupMinimizedStrategy aging 자동 필터링<br>✅ find_best_chemical() aging 자동 필터링 | ✅ 100% | Medium |
| **`src/dag_management/dag_manager.py`** | ✅ 수정 불필요 (opnode_dict 없는 노드 자동 처리) | ✅ N/A | Low |
| **`src/results.py`** | ⏭️ 선택사항 (기계 -1 표시 개선) | ⏭️ 미구현 | Low |

**수정 완료**: 7개 파일 ✅ (1개 파일은 Depth 중복 문제 미해결)
**선택사항 미구현**: 2개 파일 ⏭️

---

## 6. 구현 우선순위 (Hybrid Approach 기준)

### ✅ Critical (100% 완료)
- [x] machine_dict 딕셔너리 변경 (리스트→딕셔너리)
- [x] Scheduler.aging_machine 속성 추가 (Machines는 리스트 유지!)
- [x] DAGNode.is_aging 속성 추가

### ✅ High (100% 완료)
- [x] assign_operation() 수정 (aging 감지, enumerate→items)
- [x] get_machine() 통합 접근자 추가
- [x] aging 노드 생성 및 DAG 삽입

### ✅ Medium (100% 완료)
- [x] overlapping 지원
- [x] AgingMachineStrategy 구현

### ⏭️ Low (선택사항 - 미구현)
- [ ] 결과 표시 개선 (기계 -1 → "AGING")

---

## 7. 최종 요약

### 핵심 변경점 (모두 완료 ✅)
- ✅ `machine_dict`: 리스트 → 딕셔너리 (필수)
- ✅ `Scheduler.Machines`: 리스트 유지 (기존 코드 호환)
- ✅ `Scheduler.aging_machine`: 별도 속성 추가 (새로운 접근법)
- ✅ `get_machine()`: 통합 접근자 (향후 확장성)
- ✅ `AgingMachineStrategy`: 전략 패턴 통합
- ✅ `allow_overlapping`: Overlapping 지원

### 추가된 코드
- **새 함수**: 4개
  - `parse_aging_requirements()` - aging_map 생성
  - `insert_aging_nodes_to_dag()` - DAG 수정
  - `is_aging_node()` - 헬퍼 함수
  - `get_machine()` - 통합 접근자
- **새 클래스**: 1개
  - `AgingMachineStrategy` - Aging 전용 전략
- **새 메서드**: 여러 개 (overlapping 지원 등)
- **총 코드량**: ~200줄

### 현재 상태
- ✅ **Phase 1-5 완료**: 모든 핵심 기능 구현 완료
- ✅ **Dispatch Priority 문제 해결**: Aging 노드 자동 스케줄링 구현 (2025-11-10)
- ⚠️ **1개 CRITICAL 이슈**: Depth 중복 문제 미해결
- ⏭️ **선택사항**: DelayProcessor, Results 표시 개선 미구현
- **전체 진행률**: 97%

### 완료된 작업 (2025-11-10)
1. ✅ `schedule_ready_aging_children()` 메서드 추가
2. ✅ Aging 노드 필터링 로직 구현
3. ✅ 자동 스케줄링 트리거 구현
4. ✅ IndexError 완전 해결
5. ✅ 테스트 성공 확인

### 다음 단계
1. 🔥 **URGENT**: Depth 중복 문제 해결 (`'3_proccode'` 에러)
   - Option 1: Depth Shift 방식 (권장)
   - Option 2: 소수점 Depth
2. ✅ **최종 테스트**: Depth 문제 해결 후 완전한 통합 테스트 실행
