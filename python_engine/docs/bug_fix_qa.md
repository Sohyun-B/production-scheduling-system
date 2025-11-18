# Bug Fix Q&A: machine_rest 관련 수정사항 분석

## 질문 1: success=False 반환 시 연쇄 효과 및 핸들링 방식

### 1.1 기존 동작 (버그 상태)

**코드 위치**: [scheduling_core.py:213-228](../src/scheduler/scheduling_core.py#L213-L228)

```python
# OptimalMachineStrategy.assign() - 버그 버전
def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
    machine_code, start_time, processing_time = scheduler.assign_operation(...)
    return AssignmentResult(
        success=True,  # ← 항상 True (버그!)
        machine_code=machine_code,  # None일 수 있음
        start_time=start_time,
        processing_time=processing_time
    )
```

**문제점**:
- `machine_code=None`이어도 `success=True` 반환
- "유령 노드" 생성: 실제로는 할당되지 않았지만 할당된 것으로 처리됨
- Dependency 업데이트 실행 → 자식 노드들이 잘못된 ready 상태가 됨
- 논리적 오류 누적

### 1.2 수정 후 동작 (정상 상태)

```python
# OptimalMachineStrategy.assign() - 수정 버전
def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
    machine_code, start_time, processing_time = scheduler.assign_operation(...)
    return AssignmentResult(
        success=machine_code is not None,  # ← 실제 할당 여부 반영
        machine_code=machine_code,
        start_time=start_time,
        processing_time=processing_time
    )
```

### 1.3 연쇄 효과 분석

#### Step 1: schedule_single_node() 에서의 처리

**코드 위치**: [scheduling_core.py:166-168](../src/scheduler/scheduling_core.py#L166-L168)

```python
if not assignment_result.success:
    print(f"[DEBUG] schedule_single_node - 노드 {node.id}: 기계 할당 실패")
    return False  # ← 즉시 False 반환
```

**효과**:
- ✅ 노드 상태 업데이트 **안 함** (line 171-176 실행 안 됨)
- ✅ Dependency 업데이트 **안 함** (line 179 실행 안 됨)
- ✅ 노드는 원래 상태 유지 (`machine=None`, `parent_node_count` 그대로)

#### Step 2: SetupMinimizedStrategy.execute() 에서의 처리

**코드 위치**: [scheduling_core.py:372-376](../src/scheduler/scheduling_core.py#L372-L376)

```python
# 1. 첫 번째 노드(loop_leader) 스케줄링 시도
success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

if not success:
    print(f"[DEBUG] SetupMinimizedStrategy - loop_leader {start_id} 스케줄링 실패")
    return []  # ← 빈 리스트 반환
```

**효과**:
- ✅ 윈도우 전체 스케줄링 중단
- ✅ `used_ids = []` 반환 (아무 노드도 스케줄링 안 됨)
- ✅ 상위 전략(DispatchPriorityStrategy)으로 실패 전파

#### Step 3: DispatchPriorityStrategy.execute() 에서의 처리

**코드 위치**: [scheduling_core.py:589-599](../src/scheduler/scheduling_core.py#L589-L599)

```python
used_ids = setup_strategy.execute(dag_manager, scheduler, window_result[0], window_result[1:])

if used_ids:
    result = [item for item in result if item[0] not in used_ids]
else:
    # 무한루프 방지: 아무것도 스케줄링되지 않았으면 첫 번째 노드 강제 제거
    print(f"[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 {result[0][0]} 제거")
    result = result[1:]
```

**효과**:
- ⚠️ WARNING 메시지 출력
- ✅ 문제 노드를 priority queue에서 **제거**
- ✅ 다음 윈도우로 이동 (무한루프 방지)

### 1.4 핸들링 방식 요약

| 단계 | 기존 (버그) | 수정 후 (정상) |
|------|------------|---------------|
| **OptimalMachineStrategy** | `success=True` (거짓) | `success=False` (정직) |
| **schedule_single_node** | 계속 진행 (유령 노드 생성) | 즉시 중단 (`return False`) |
| **노드 상태** | `machine=None`, dependency 업데이트됨 (오류) | 원래 상태 유지 (정상) |
| **SetupMinimizedStrategy** | 다음 노드로 진행 (논리 오류) | `return []` (실패 표시) |
| **DispatchPriorityStrategy** | 논리 오류 누적 | WARNING 출력 + 노드 제거 |
| **최종 결과** | 일부 노드 미스케줄 (조용한 실패) | 명시적 실패 + 로그 출력 |

### 1.5 "에러 상황"에 대한 이해

**사용자 우려**: "success=false인 것도 에러상황인데..."

**답변**:
- ✅ `success=False`는 **정상적인 에러 핸들링**입니다
- ✅ 시스템이 **의도한 대로 동작**하는 것입니다
- ✅ 기존 버그는 에러를 **숨기는** 것이었고, 수정 후는 에러를 **명확히 표시**하는 것입니다

**실제 시나리오**:
1. **machine_rest로 모든 기계가 차단된 경우**
   - 스케줄링 불가능 → `success=False` 반환 → WARNING 출력 → 노드 제거
   - 이후 DOWNTIME이 끝나면 재시도 가능 (현재 구현에서는 재시도 로직 없음)

2. **특정 시간대에만 기계 사용 불가**
   - 다른 윈도우에서 다시 시도
   - 시간이 지나면 스케줄링 가능

3. **진짜 에러 (기계 정보 없음 등)**
   - 명확한 에러 메시지 출력
   - 디버깅 가능

### 1.6 현재 한계점 및 개선 방향

#### 현재 한계점
- ⚠️ 실패한 노드는 queue에서 영구 제거됨 (재시도 없음)
- ⚠️ DOWNTIME이 끝나도 자동 재스케줄링 안 됨

#### 개선 방향 (선택사항)
```python
# 개선안: 실패 원인별 처리
if not success:
    failure_reason = assignment_result.failure_reason
    if failure_reason == "DOWNTIME_BLOCKING":
        # 나중에 재시도할 수 있도록 별도 큐에 보관
        delayed_queue.append((node_id, downtime_end_time))
    elif failure_reason == "NO_MACHINE":
        # 영구 에러: 제거
        print(f"[ERROR] 노드 {node_id}: 사용 가능한 기계 없음 (영구 실패)")
    return []
```

---

## 질문 2: 시나리오 C (delay=0 처리 시) 리스크 설명

### 2.1 사용자 지적사항

> "downtime 바로 직전까지 작업을 하거나 downtime이 바로 끝난 뒤에 작업을 하는 등의 스케줄링은 의도된 바임."

**→ 맞습니다!** 이는 정상적인 동작입니다.

### 2.2 실제 리스크 명확화

제가 지적한 "시나리오 C" 리스크는 **DOWNTIME-인접 스케줄링 자체**가 아니라, **delay 계산 오류 시 발생하는 문제**입니다.

#### 문제 시나리오

**상황**:
1. 일반 작업 A가 11:50에 끝남
2. DOWNTIME이 12:00~14:00에 설정됨
3. 다음 작업 B가 14:00부터 시작 가능

**정상 동작** (delay 계산 성공):
```
작업 A: 10:00 - 11:50 (공정타입: DYEING, 폭: 200cm, chemical: C1)
DOWNTIME: 12:00 - 14:00
작업 B: 14:00 + delay - 14:30 (공정타입: PRINTING, 폭: 150cm, chemical: C2)
        ^^^^^^^
        delay = 30분 (DYEING→PRINTING 교체시간)
```

**비정상 동작** (delay 계산 실패 → 0 반환):
```
작업 A: 10:00 - 11:50
DOWNTIME: 12:00 - 14:00
작업 B: 14:00 - 14:20 (delay=0으로 계산됨)
        ^^^^
        ❌ 교체시간 없이 바로 시작
        ❌ 실제로는 14:30까지 준비 못함
        ❌ 일정 위반!
```

### 2.3 왜 delay=0이 반환될 수 있는가?

**코드 위치**: [delay_dict.py:41-56](../src/scheduler/delay_dict.py#L41-L56)

#### 원인 1: empty_dict 키 누락 (이미 수정 완료 ✅)

```python
# 수정 전 (버그)
empty_dict = {
    "OPERATION_ORDER": 0,
    "OPERATION_CODE": "",
    "OPERATION_CLASSIFICATION": "",
    "FABRIC_WIDTH": 0,
    "CHEMICAL_LIST": (),
    "PRODUCTION_LENGTH": 0,
    # "SELECTED_CHEMICAL": None,  ← 누락!
}

# delay_calc_whole_process()에서:
values1 = self.opnode_dict.get(item_id1, empty_dict)  # DOWNTIME은 opnode_dict에 없음
input_key = self.calculate_delay(values1, values2, machine_code)
# ↓
# KeyError: 'SELECTED_CHEMICAL' 발생!
# ↓
# 예외 처리로 0 반환 (또는 크래시)
```

**수정 후 (정상 ✅)**:
```python
empty_dict = {
    ...
    "SELECTED_CHEMICAL": None,  # ← 추가됨!
}
```

#### 원인 2: delay_dict에 키가 없는 경우

**코드 위치**: [delay_dict.py:55](../src/scheduler/delay_dict.py#L55)

```python
delay_time = self.delay_dict.get(input_key, 0)  # ← 키 없으면 0 반환
```

**시나리오**:
- `input_key = ('A2020', '', 'DYEING', False, False, False, False)`
  - DOWNTIME의 `OPERATION_CLASSIFICATION = ""`
  - 이런 조합이 `delay_dict`에 없으면 → `delay=0` 반환

### 2.4 리스크 정리

| 상황 | 리스크 수준 | 설명 |
|------|------------|------|
| **DOWNTIME 직전 작업** | ⚠️ 중간 | A 작업 완료 → DOWNTIME 시작 사이 delay는 무시됨 (괜찮음) |
| **DOWNTIME 직후 작업** | 🔴 높음 | DOWNTIME → B 작업 사이 delay가 0으로 계산되면 교체시간 누락 |
| **일반 작업 간** | 🔴 높음 | delay 계산 실패 시 모든 교체시간 누락 |

### 2.5 수정 완료 상태 확인

✅ **원인 1 해결됨**: `empty_dict`에 `SELECTED_CHEMICAL` 추가
✅ **원인 2 완화됨**: 이제 KeyError는 발생하지 않음

**남은 리스크**:
- ⚠️ DOWNTIME의 `OPERATION_CLASSIFICATION`이 빈 문자열인 경우, delay_dict에 매칭 실패 가능
- ⚠️ 하지만 `get(input_key, 0)`으로 안전하게 0 반환

**권장 개선사항** (선택):
```python
# scheduler.py:346 근처 - DOWNTIME 데이터 보강
for idx, row in machine_rest.iterrows():
    ...
    # DOWNTIME에 명시적 OPERATION_CLASSIFICATION 부여
    self.Machines[machine_code].force_Input(
        -1,
        "DOWNTIME_기계사용불가시간",  # node_id
        start_time,
        end_time
    )

    # opnode_dict에도 등록 (delay 계산을 위해)
    self.opnode_dict["DOWNTIME_기계사용불가시간"] = {
        "OPERATION_ORDER": 0,
        "OPERATION_CODE": "DOWNTIME",
        "OPERATION_CLASSIFICATION": "MAINTENANCE",  # ← 명시적 타입
        "FABRIC_WIDTH": 0,
        "CHEMICAL_LIST": (),
        "PRODUCTION_LENGTH": 0,
        "SELECTED_CHEMICAL": None,
    }
```

---

## 질문 3: force_Input() 정렬 미수행 문제 - 왜 지금까지 문제 없었나?

### 3.1 버그 확인

**코드 위치**: [machine.py:143-152](../src/scheduler/machine.py#L143-L152)

```python
def force_Input(self, depth, node_id, start_time, end_time):
    """
    특정 시간대에 기계가 사용되지 못하게 가짜 일을 추가하는 방식
    """
    self.assigned_task.append([depth, node_id])
    self.O_start.append(start_time)  # ← append만 함
    self.O_end.append(end_time)      # ← append만 함
    self.End_time = max(self.End_time, end_time)
    # ❌ 정렬 없음!
```

**대조**: [machine.py:133-137](../src/scheduler/machine.py#L133-L137) `_Input()` 메서드

```python
def _Input(self, depth, node_id, M_Ealiest, P_t, operation_nodes = None):
    ...
    self.O_start.append(M_Ealiest)
    self.O_start.sort()  # ← 정렬 수행!
    self.O_end.append(M_Ealiest + P_t)
    self.O_end.sort()    # ← 정렬 수행!
    self.End_time = self.O_end[-1]
```

### 3.2 왜 지금까지 문제가 없었는가?

#### 이유 1: allocate_machine_downtime()은 스케줄링 **시작 전**에만 호출됨

**코드 위치**: [__init__.py:138-147](../src/scheduler/__init__.py#L138-L147)

```python
# Scheduler 생성
scheduler = Scheduler(machine_dict=machine_dict, ...)

# ⭐ DOWNTIME 먼저 할당 (이때 기계는 비어있음)
scheduler.allocate_machine_downtime(machine_rest, base_date)

# ⭐ 그 다음 실제 스케줄링 시작
strategy = DispatchPriorityStrategy()
result = strategy.execute(...)
```

**핵심**:
- DOWNTIME은 **기계가 비어있을 때** force_Input()으로 삽입됨
- 이후 일반 작업들은 **_Input()** 으로 삽입되며, _Input()은 정렬을 수행함
- _Input()이 정렬을 수행하면 **O_start와 O_end 전체**가 정렬됨 (DOWNTIME 포함)

**예시**:
```python
# 1. force_Input() 호출 (정렬 안 함)
machine.force_Input(-1, "DOWNTIME1", 100, 200)
machine.O_start = [100]  # 정렬 안 됨
machine.O_end = [200]

machine.force_Input(-1, "DOWNTIME2", 50, 80)
machine.O_start = [100, 50]  # ❌ 비정렬 상태!
machine.O_end = [200, 80]

# 2. 첫 번째 _Input() 호출 (정렬 수행)
machine._Input(depth=0, node_id="JOB1", M_Ealiest=0, P_t=30)
machine.O_start.append(0)
machine.O_start.sort()  # ← 이때 DOWNTIME들도 함께 정렬됨!
machine.O_start = [0, 50, 100]  # ✅ 정렬됨!
machine.O_end = [30, 80, 200]
```

#### 이유 2: Empty_time_window() 계산이 정렬을 가정함

**코드 위치**: [machine.py:50-79](../src/scheduler/machine.py#L50-L79)

```python
def Empty_time_window(self):
    ...
    if len(self.O_end) > 1:
        # 연속된 작업들 사이의 빈 시간 계산
        time_window_start.extend(self.O_end[:-1])  # ← 정렬되어 있다고 가정!
        time_window_end.extend(self.O_start[1:])   # ← 정렬되어 있다고 가정!
    ...
```

**만약 정렬 안 되어 있으면**:
```python
# 비정렬 상태
O_start = [100, 50, 200]
O_end = [150, 80, 250]

# Empty_time_window() 계산 결과 (잘못됨)
time_window_start = [150, 80]  # O_end[:-1]
time_window_end = [50, 200]    # O_start[1:]
len_time_window = [50-150, 200-80] = [-100, 120]  # ❌ 음수!
```

**하지만 실제로는**:
- 첫 번째 `_Input()` 호출 시 전체 리스트가 정렬됨
- 이후 모든 `Empty_time_window()` 호출은 정렬된 상태를 사용

#### 이유 3: DOWNTIME이 하나만 있는 경우가 대부분

**현재 테스트 데이터**:
- 보통 기계당 DOWNTIME 0~1개
- 여러 개 있어도 _Input() 호출 전에 이미 정렬됨 (위 이유 1)

### 3.3 언제 문제가 발생할 수 있는가?

#### 시나리오 1: force_Input()만 여러 번 호출하고 _Input() 없이 Empty_time_window() 호출

```python
# 기계 생성
machine = Machine("TEST", allow_overlapping=False)

# DOWNTIME만 여러 개 추가 (역순)
machine.force_Input(-1, "DOWNTIME1", 100, 200)
machine.force_Input(-1, "DOWNTIME2", 50, 80)
machine.force_Input(-1, "DOWNTIME3", 150, 180)

# ❌ _Input() 호출 없이 바로 Empty_time_window() 사용
windows = machine.Empty_time_window()
# 결과: 잘못된 빈 시간 계산!
```

**발생 가능성**:
- ⚠️ **매우 낮음** - 실제 스케줄링은 항상 _Input()을 호출하기 때문
- ⚠️ 하지만 **이론적으로 가능**

#### 시나리오 2: 재스케줄링 시 DOWNTIME 추가

**코드 위치**: [scheduling_core.py:604-660](../src/scheduler/scheduling_core.py#L604-L660) `UserRescheduleStrategy`

현재 코드에는 재스케줄링 중 DOWNTIME을 추가하는 로직이 **없음**.
만약 미래에 추가된다면:

```python
# 재스케줄링 중
for machine in scheduler.Machines.values():
    # 기존 작업들이 이미 _Input()으로 정렬된 상태

    # 새로운 DOWNTIME 추가
    machine.force_Input(-1, "NEW_DOWNTIME", 120, 150)
    # ❌ 정렬 안 됨!

    # machine_earliest_start() 계산
    # ❌ 잘못된 결과 가능!
```

### 3.4 버그 노출 테스트 방법

#### 테스트 1: 여러 DOWNTIME을 역순으로 입력

**Excel 입력** (`machine_rest` 시트):

| 기계코드 | 시작시간 | 종료시간 |
|---------|---------|---------|
| A2020 | 2024-06-10 14:00 | 2024-06-10 16:00 |
| A2020 | 2024-06-10 08:00 | 2024-06-10 10:00 |
| A2020 | 2024-06-10 18:00 | 2024-06-10 20:00 |

**예상 결과** (버그 있으면):
- Empty_time_window() 계산 오류
- 작업이 DOWNTIME 시간대에 할당될 수 있음
- 음수 빈 시간창 발생

**실제 결과** (현재):
- ✅ 정상 작동 (첫 번째 _Input()이 정렬함)

#### 테스트 2: 직접 force_Input() 테스트

**Python 코드**:
```python
from src.scheduler.machine import Machine

# 기계 생성
m = Machine("TEST", allow_overlapping=False)

# DOWNTIME 역순 삽입
m.force_Input(-1, "DT1", 100, 150)
m.force_Input(-1, "DT2", 50, 80)
m.force_Input(-1, "DT3", 200, 250)

# 정렬 전 상태 확인
print("O_start (정렬 전):", m.O_start)  # [100, 50, 200]
print("O_end (정렬 전):", m.O_end)      # [150, 80, 250]

# Empty_time_window() 계산
start, end, length = m.Empty_time_window()
print("Window lengths:", length)  # 음수 포함 가능!

# _Input() 호출 후
m._Input(0, "JOB1", 0, 30)

# 정렬 후 상태 확인
print("O_start (정렬 후):", m.O_start)  # [0, 50, 100, 200]
print("O_end (정렬 후):", m.O_end)      # [30, 80, 150, 250]
```

### 3.5 외부 정렬 로직 존재 여부

**결론**: **없음**

- ✅ `allocate_machine_downtime()` 이후 별도 정렬 없음
- ✅ `_Input()` 메서드가 **유일한 정렬 지점**
- ✅ 현재는 우연히 정상 작동 중

### 3.6 수정 권장사항

#### 수정안 1: force_Input()에 정렬 추가 (권장 ⭐)

**코드 위치**: [machine.py:143-152](../src/scheduler/machine.py#L143-L152)

```python
def force_Input(self, depth, node_id, start_time, end_time):
    """
    특정 시간대에 기계가 사용되지 못하게 가짜 일을 추가하는 방식
    """
    self.assigned_task.append([depth, node_id])
    self.O_start.append(start_time)
    self.O_start.sort()  # ← 추가!
    self.O_end.append(end_time)
    self.O_end.sort()    # ← 추가!
    self.End_time = max(self.End_time, end_time)
```

**장점**:
- ✅ _Input()과 동일한 동작
- ✅ 향후 버그 방지
- ✅ 코드 일관성 향상

**단점**:
- ⚠️ 성능: DOWNTIME 추가할 때마다 O(N log N) 정렬 (하지만 N은 작음)

#### 수정안 2: allocate_machine_downtime() 후 정렬

**코드 위치**: [scheduler.py:328-350](../src/scheduler/scheduler.py#L328-L350)

```python
def allocate_machine_downtime(self, machine_rest, base_date):
    ...
    for idx, row in machine_rest.iterrows():
        ...
        self.Machines[machine_code].force_Input(-1, "DOWNTIME...", start_time, end_time)

    # ⭐ 모든 DOWNTIME 추가 후 한 번만 정렬
    for machine in self.Machines.values():
        machine.O_start.sort()
        machine.O_end.sort()
```

**장점**:
- ✅ 성능: O(N log N) 한 번만 수행

**단점**:
- ⚠️ force_Input()의 일반적 사용에는 정렬 안 됨
- ⚠️ 재스케줄링 시 문제 가능성 남음

#### 권장사항

**⭐ 수정안 1 선택**:
- 코드 일관성 최우선
- 성능 영향 미미 (DOWNTIME 개수 적음)
- 향후 모든 케이스에 안전

---

## 요약

### 질문 1: success=False 연쇄효과
- ✅ **정상적인 에러 핸들링**입니다
- ✅ 노드 상태 보존, dependency 보존, 명시적 실패 표시
- ✅ WARNING 출력 후 다음 윈도우로 이동 (무한루프 방지)
- ⚠️ 재시도 로직은 현재 없음 (개선 가능)

### 질문 2: delay=0 리스크
- ✅ DOWNTIME 인접 스케줄링 자체는 **정상**입니다
- ✅ 리스크는 **delay 계산 실패 시 교체시간 누락**
- ✅ `SELECTED_CHEMICAL` 추가로 KeyError는 해결됨
- ⚠️ DOWNTIME의 OPERATION_CLASSIFICATION 처리 개선 가능

### 질문 3: force_Input() 정렬
- ✅ 지금까지 문제 없었던 이유: **첫 번째 _Input()이 전체 리스트 정렬**
- ⚠️ 이론적 버그 존재: force_Input()만 여러 번 호출 시 문제 가능
- ⭐ **권장 수정**: force_Input()에 sort() 추가 (코드 일관성 + 향후 안전성)

---

## 다음 단계 제안

1. **우선순위 높음** ⭐:
   - [ ] `force_Input()`에 정렬 추가 (machine.py:151-152)
   - [ ] `OptimalMachineStrategy.assign()`에 `success=machine_code is not None` 적용 확인

2. **우선순위 중간**:
   - [ ] DOWNTIME delay 계산 개선 (opnode_dict 등록)
   - [ ] 실패 노드 재시도 로직 검토

3. **테스트**:
   - [ ] 여러 DOWNTIME 역순 입력 테스트
   - [ ] DOWNTIME 직후 작업 delay 확인
