# Aging 공정 구현 계획서

## 1. 개요

Aging 공정은 실제 공정순서(tb_itemproc)에 없는 특별한 공정으로, 별도 테이블에서 관리되며 **overlapping이 가능한 가상 기계(기계 인덱스 -1)**에서 수행됩니다.

### 핵심 특징
- **Overlapping 가능**: 동시에 여러 aging 작업 수행 가능
- **가상 기계**: 기계 인덱스 -1 전용
- **즉시 시작**: earliest_start 기준으로 바로 시작 (기계 대기 시간 없음)
- **별도 테이블 관리**: tb_agingtime_gitem, tb_agingtime_gbn에서 관리

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

### 단계 4: Scheduler 수정

#### 4.1 Machines 구조 변경 (리스트 → 딕셔너리)

**이유**: 기계 인덱스 -1 지원 (리스트는 음수 인덱스 불가)

```python
# 기존
self.Machines = [Machine_Time_window(i) for i in range(n)]

# 변경
self.Machines = {}
for i in range(self.machine_numbers):
    self.Machines[i] = Machine_Time_window(i)
self.Machines[-1] = Machine_Time_window(-1, allow_overlapping=True)
```

**영향받는 코드 수정**:
- `for machine in self.Machines` → `for idx, machine in self.Machines.items()`
- 모든 `self.Machines[i]` 접근은 그대로 (딕셔너리 키 접근)

**수정 필요 위치**:
- `machine_earliest_start()`, `assign_operation()`, `force_assign_operation()`
- `create_machine_schedule_dataframe()`, `allocate_machine_downtime()`

#### 4.2 주요 메서드 수정

**assign_operation()**:
- Aging 노드 감지: `set(machine_info.keys()) == {-1}`
- `enumerate` → `items()` 사용
- aging 기계(-1) 일반 할당에서 제외

**machine_earliest_start()**:
- 기계 -1일 때: earliest_start 그대로 반환 (대기 없음)

**allocate_machine_downtime()**:
- 기계 -1은 제외 (가상 기계는 휴식 없음)

---

### 단계 5: SchedulingCore 수정

**AgingMachineStrategy 생성**:
```python
class AgingMachineStrategy(MachineAssignmentStrategy):
    def assign(self, scheduler, node, earliest_start):
        # 기계 -1에 강제 할당
        ...
```

**schedule_single_node() 수정**:
- aging 노드 감지 시 `AgingMachineStrategy` 사용

**SetupMinimizedStrategy/find_best_chemical 수정**:
- aging 노드 필터링

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

### 3.2 DAG 삽입 로직

**aging_df 필요 정보**:
- 어떤 gitem의 어떤 공정 이후 aging?
- aging 시간 (30분 단위 변환 필요?)

**다중 aging**: 하나의 공정 → 하나의 aging → 하나의 다음 공정 (가정)

### 3.3 테스트 시나리오

1. **기본**: 공정A → Aging → 공정B
2. **Overlapping**: 아이템1 Aging(10~14), 아이템2 Aging(12~15) → 겹침 허용
3. **다중 부모**: 공정A,B 완료 → Aging (max 종료시간 기준)

---

## 4. 구현 체크리스트

### Phase 1: 데이터 구조
- [ ] machine_dict 딕셔너리 구조로 변경
- [ ] create_machine_dict() 수정 (aging_nodes_dict 파라미터)
- [ ] DAGNode에 is_aging 속성 추가
- [ ] is_aging_node() 헬퍼 함수 작성

### Phase 2: DAG 생성
- [ ] `parse_aging_requirements()` 함수 작성 (`src/dag_management/dag_dataframe.py`)
  - aging_df에서 gitemno, proccode, aging_time 읽기
  - sequence_seperated_order와 매칭하여 parent_node_id 찾기
  - 다음 노드(next_node_id) 찾기
  - aging_map 딕셔너리 생성
- [ ] `insert_aging_nodes_to_dag()` 함수 작성 (`src/dag_management/dag_dataframe.py`)
  - dag_df의 CHILDREN 컬럼 수정
  - aging 노드 행 생성 (ID, DEPTH, CHILDREN)
  - dag_df에 새 행 추가 및 정렬
- [ ] `create_complete_dag_system()` 수정 (`src/dag_management/__init__.py`)
  - 함수 시그니처에 aging_map 파라미터 추가
  - insert_aging_nodes_to_dag() 호출
  - machine_dict에 aging 노드 추가
  - DAGGraphManager 재빌드
  - aging 노드에 is_aging 플래그 설정
- [ ] `main.py` 수정
  - parse_aging_requirements import 추가
  - aging_map 생성 코드 추가 (182번 줄 직전)
  - create_complete_dag_system()에 aging_map 전달

### Phase 3: Machine 클래스
- [ ] Machine_Time_window에 allow_overlapping 플래그
- [ ] _Input() overlapping 지원

### Phase 4: Scheduler
- [ ] Machines 딕셔너리로 변경
- [ ] allocate_resources()에 기계 -1 추가
- [ ] assign_operation() 수정 (aging 감지, enumerate→items)
- [ ] machine_earliest_start() 수정 (기계 -1 처리)
- [ ] create_machine_schedule_dataframe() 수정
- [ ] allocate_machine_downtime() 수정 (기계 -1 제외)

### Phase 5: SchedulingCore
- [ ] AgingMachineStrategy 클래스
- [ ] schedule_single_node() aging 감지
- [ ] SetupMinimizedStrategy/find_best_chemical aging 제외

### Phase 6: DelayProcessor
- [ ] aging 딜레이 0 처리

### Phase 7: 결과 처리
- [ ] create_results() 기계 -1 표시

### Phase 8: 테스트
- [ ] 기본/Overlapping/다중부모 시나리오 테스트

---

## 5. 수정 파일 목록

| 파일 | 수정 내용 | 우선순위 |
|------|----------|---------|
| **`src/dag_management/dag_dataframe.py`** | DAGNode.is_aging 속성 추가<br>parse_aging_requirements() 함수 추가<br>insert_aging_nodes_to_dag() 함수 추가 | Critical |
| **`src/dag_management/__init__.py`** | create_complete_dag_system() 시그니처 변경<br>aging_map 처리 로직 추가 | Critical |
| **`main.py`** | parse_aging_requirements import<br>aging_map 생성 (182번 줄 직전)<br>create_complete_dag_system()에 aging_map 전달 | Critical |
| **`src/dag_management/node_dict.py`** | create_machine_dict() 딕셔너리 구조 변경<br>enumerate → items 사용 | Critical |
| **`src/scheduler/scheduler.py`** | Machines 딕셔너리 변경<br>assign_operation() enumerate → items<br>machine_earliest_start() 기계 -1 처리<br>allocate_machine_downtime() 기계 -1 제외 | High |
| **`src/scheduler/machine.py`** | Machine_Time_window에 allow_overlapping 플래그<br>_Input() overlapping 지원 | High |
| **`src/scheduler/scheduling_core.py`** | AgingMachineStrategy 클래스 추가<br>schedule_single_node() aging 감지<br>SetupMinimizedStrategy aging 제외 | Medium |
| **`src/dag_management/dag_manager.py`** | build_from_dataframe()에서 opnode_dict 없는 노드 처리 | Low |
| **`src/results.py`** | 기계 -1 표시 | Low |

---

## 6. 구현 우선순위

1. **Critical**: machine_dict 딕셔너리 변경, Machines 딕셔너리 변경
2. **High**: assign_operation() 수정 (enumerate→items)
3. **High**: aging 노드 생성 및 DAG 삽입
4. **Medium**: overlapping 지원
5. **Low**: 결과 표시 개선
