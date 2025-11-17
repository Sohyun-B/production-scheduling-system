# 버그 분석: machine_rest 사용 시 노드 스케줄링 실패 문제

## 문제 증상

`main.py` 실행 시 다음과 같은 WARNING 메시지가 반복적으로 출력됨:

```
[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 32571_1300_4_M3_23312_T01639 제거
[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 32571_1300_4_M3_23316_T01640 제거
[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 32571_1300_4_M3_20500_T01514 제거
...
```

### 발생 조건

- `machine_rest` (기계 다운타임) 데이터가 비어있지 않을 때만 발생
- `machine_rest`가 빈 DataFrame일 때는 정상 작동

## 근본 원인 분석

### 1. 버그 위치

**파일**: `python_engine/src/scheduler/scheduling_core.py`
**클래스**: `OptimalMachineStrategy`
**메서드**: `assign()` (Line 213-235)

```python
def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
    try:
        machine_idx, start_time, processing_time = scheduler.assign_operation(
            earliest_start, node.id, node.depth
        )
        return AssignmentResult(
            success=True,  # ← 버그! machine_idx가 None이어도 항상 True
            machine_index=machine_idx,
            start_time=start_time,
            processing_time=processing_time
        )
    except Exception as e:
        return AssignmentResult(
            success=False,
            machine_index=None,
            start_time=None,
            processing_time=None
        )
```

### 2. 버그 발생 메커니즘

#### Step 1: machine_rest로 인한 기계 차단

`machine_rest`가 설정되면 `Scheduler.allocate_machine_downtime()` 메서드가 호출됨:

```python
# scheduler.py:328-349
def allocate_machine_downtime(self, machine_rest, base_date):
    for idx, row in machine_rest.iterrows():
        machine_code = row[config.columns.MACHINE_CODE]
        start_time = row[config.columns.MACHINE_REST_START]
        end_time = row[config.columns.MACHINE_REST_END]
        # DOWNTIME 작업으로 기계 차단
        self.Machines[machine_code].force_Input(-1, "DOWNTIME 기계 사용 불가 시간", start_time, end_time)
```

#### Step 2: 사용 가능한 기계 없음

노드의 `machine_info`에 있는 모든 기계가 DOWNTIME으로 차단된 경우:

```python
# scheduler.py:176-232
def assign_operation(self, node_earliest_start, node_id, depth):
    machine_info = self.machine_dict.get(node_id)
    ideal_machine_code = None

    for machine_code, machine_processing_time in machine_info.items():
        if machine_processing_time != 9999:
            earliest_start = self.machine_earliest_start(
                machine_info, machine_code, node_earliest_start, node_id
            )[0]
            # 모든 기계가 DOWNTIME으로 차단되어 earliest_start가 매우 큰 값
            ...

    if ideal_machine_code is not None:
        self.Machines[ideal_machine_code]._Input(...)
    else:
        print(f"[경고] 노드 {node_id}: 사용 가능한 기계 없음")

    return ideal_machine_code, best_earliest_start, ideal_machine_processing_time
    # ← ideal_machine_code = None 반환!
```

#### Step 3: 잘못된 성공 반환

`OptimalMachineStrategy.assign()`이 `machine_idx=None`을 받았는데도 `success=True` 반환:

```python
machine_idx, start_time, processing_time = scheduler.assign_operation(...)
# machine_idx = None

return AssignmentResult(
    success=True,  # ← 버그! None인데도 True
    machine_index=None,
    start_time=inf,
    processing_time=inf
)
```

#### Step 4: "유령 노드" 생성

`schedule_single_node()`가 계속 진행됨:

```python
# scheduling_core.py:165-182
if not assignment_result.success:  # success=True이므로 통과
    return False

# 노드 상태 업데이트 - 잘못된 값으로 설정됨
SchedulingCore.update_node_state(
    node,
    assignment_result.machine_index,  # None
    assignment_result.start_time,     # inf
    assignment_result.processing_time  # inf
)
# node.machine = None, node.node_start = inf, node.node_end = inf

# Dependency 업데이트 - 자식의 parent_node_count 감소
SchedulingCore.update_dependencies(node)

return True  # 성공으로 반환!
```

#### Step 5: 결과

- **노드는 스케줄링되지 않았지만** (`machine=None`)
- **Dependency는 업데이트됨** (자식의 `parent_node_count -= 1`)
- 자식 노드들의 dependency가 해결되어 ready 상태가 됨
- 하지만 부모 노드가 실제로는 스케줄링되지 않았으므로 **논리적 오류**

### 3. 왜 WARNING이 발생하는가?

디버그 로그 분석:

```
[DEBUG] SetupMinimizedStrategy - loop_leader: 32571_1300_4_M3_23312_T01639, parent_node_count: 0
[LOG] SetupMinimizedStrategy: same_operation= 0  same_chemical= 0  remaining_op= 0
```

1. 첫 번째 노드는 `parent_count=0` (ready 상태)
2. 스케줄링 시도 → `machine=None`으로 설정되지만 `success=True` 반환
3. `used_ids = [start_id]` 반환
4. 다음 윈도우로 이동

```
[DEBUG] SetupMinimizedStrategy - loop_leader: 32571_1300_4_M3_23316_T01640, parent_node_count: 1
```

5. 두 번째 노드는 `parent_count=1` (not ready) - **dependency가 완전히 해결되지 않음**
6. 스케줄링 실패 → `used_ids = []` 반환
7. `DispatchPriorityStrategy.execute()`에서 WARNING 출력 (Line 592)

## 왜 parent_count가 여전히 1인가?

### 예상 시나리오: Aging 노드 존재

DAG 구조:
```
23312 (M3) → [AGING] → 23316 (M3) → 20500 → ...
```

1. `23312` 스케줄링 시도 → `machine=None`, `success=True` (버그)
2. `update_dependencies()` 호출 → Aging 노드의 `parent_count -= 1` (0이 됨)
3. `schedule_ready_aging_children()` 호출 → Aging 노드 스케줄링 시도
4. **Aging 노드도 실패** (기계 없음 or 다른 이유)
5. Aging 노드가 스케줄링되지 않았으므로 `23316`의 `parent_count`는 여전히 1

또는:

1. `23312`가 실제로는 여러 자식을 가짐 (parallel dependencies)
2. `23316`은 `23312` + 다른 노드의 완료가 필요
3. `23312`만 "유령 스케줄링"되어 `parent_count`가 2→1로 감소
4. 여전히 1이므로 ready 아님

## 해결 방안

### 1. 버그 수정 (권장)

`OptimalMachineStrategy.assign()`에서 `machine_idx`가 `None`일 때 `success=False` 반환:

```python
def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
    try:
        machine_idx, start_time, processing_time = scheduler.assign_operation(
            earliest_start, node.id, node.depth
        )
        return AssignmentResult(
            success=machine_idx is not None,  # ← 수정
            machine_index=machine_idx,
            start_time=start_time,
            processing_time=processing_time
        )
    except Exception as e:
        return AssignmentResult(
            success=False,
            machine_index=None,
            start_time=None,
            processing_time=None
        )
```

### 2. 효과

- `machine_idx=None`일 때 `success=False` 반환
- `schedule_single_node()`가 `False` 반환
- `SetupMinimizedStrategy.execute()`가 빈 리스트 반환
- **Dependency가 업데이트되지 않음** (정상)
- 노드가 priority queue에 남아있어 나중에 재시도 가능
- `machine_rest` 시간이 끝나면 다시 스케줄링 가능

### 3. 추가 개선 사항

#### 3.1 Aging 노드 스케줄링 실패 처리

현재는 Aging 노드 스케줄링이 실패해도 무시됨:

```python
# scheduling_core.py:121-127
if is_aging:
    print(f"[INFO] Aging 노드 {child.id} 자동 스케줄링 (parent {node.id} 완료)")
    SchedulingCore.schedule_single_node(
        child,
        scheduler,
        AgingMachineStrategy()
    )
    # ← 반환값을 체크하지 않음!
```

개선안:

```python
if is_aging:
    print(f"[INFO] Aging 노드 {child.id} 자동 스케줄링 (parent {node.id} 완료)")
    success = SchedulingCore.schedule_single_node(
        child,
        scheduler,
        AgingMachineStrategy()
    )
    if not success:
        print(f"[ERROR] Aging 노드 {child.id} 자동 스케줄링 실패")
        # 필요시 예외 발생 또는 부모 노드 스케줄링 롤백
```

#### 3.2 machine_rest 시간대 고려

스케줄러가 `machine_rest`로 차단된 시간대를 피해서 스케줄링하도록 개선:

- `earliest_start` 계산 시 DOWNTIME 종료 시간 고려
- 또는 DOWNTIME이 끝난 후 자동 재시도 메커니즘 추가

## 관련 코드 위치

- **버그 위치**: `python_engine/src/scheduler/scheduling_core.py:224`
- **영향받는 메서드**:
  - `OptimalMachineStrategy.assign()` (Line 213)
  - `SchedulingCore.schedule_single_node()` (Line 130)
  - `SetupMinimizedStrategy.execute()` (Line 352)
  - `DispatchPriorityStrategy.execute()` (Line 509)
- **관련 파일**:
  - `python_engine/src/scheduler/scheduler.py` (assign_operation, allocate_machine_downtime)
  - `python_engine/src/dag_management/dag_manager.py` (dependency 관리)

## 테스트 방법

### 재현 방법

1. `시나리오_공정제약조건.xlsx`의 `machine_rest` 시트에 데이터 추가
2. `main.py` 실행
3. WARNING 메시지 확인

### 버그 수정 후 확인 사항

1. WARNING 메시지가 사라짐
2. 모든 노드가 정상적으로 스케줄링됨
3. `[경고] 노드 {id}: 사용 가능한 기계 없음` 메시지 출력 시 스케줄링이 실패로 처리됨
4. Dependency가 올바르게 유지됨 (유령 노드 없음)

## 결론

`OptimalMachineStrategy.assign()`이 `machine_idx=None`일 때도 `success=True`를 반환하는 버그로 인해:

1. 실제로는 스케줄링되지 않은 "유령 노드"가 생성됨
2. Dependency는 업데이트되지만 실제 작업은 할당되지 않음
3. Priority queue에서 노드가 제거되어 재시도 기회가 없음
4. 최종적으로 일부 노드가 스케줄링되지 않은 채 프로그램이 종료됨

**수정 방법**: `success=machine_idx is not None`로 변경하여 실제 할당 여부를 정확히 반영
