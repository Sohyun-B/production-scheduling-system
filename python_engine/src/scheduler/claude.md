# Scheduler 모듈 - 비즈니스 로직 상세 설명서

## 목차
1. [Scheduler 모듈의 역할](#scheduler-모듈의-역할)
2. [모듈 구성과 책임 분담](#모듈-구성과-책임-분담)
3. [핵심 비즈니스 로직 상세 분석](#핵심-비즈니스-로직-상세-분석)
4. [실행 흐름과 의사결정 과정](#실행-흐름과-의사결정-과정)

---

## Scheduler 모듈의 역할

### 모듈이 받는 입력
main.py의 `run_scheduler_pipeline()` 호출 시점에 이미 다음이 준비되어 있음:

```python
# 입력 데이터
dag_df                    # DAG 구조 (노드 간 의존성 관계)
sequence_seperated_order  # 공정별 작업 목록 (납기일, 원단폭 등 포함)
opnode_dict              # 각 작업의 메타데이터 (배합액 목록, 공정코드 등)
machine_dict             # {작업ID: {기계코드: 처리시간}} 매핑
operation_delay_df       # 공정 교체 시간 테이블
width_change_df          # 원단 폭 변경 시간 테이블
machine_rest             # 기계 중단 시간 (점검/고장)
manager                  # DAGGraphManager (노드 객체 관리)
```

### 모듈이 해결하는 문제
> **"언제, 어떤 작업을, 어느 기계에 할당할 것인가?"**

이것은 단순한 배정 문제가 아니라, 다음을 동시에 고려하는 복잡한 최적화 문제:
- **의존성**: 부모 작업 완료 전에는 자식 작업 시작 불가
- **기계 선택**: 같은 작업도 기계마다 처리 시간이 다름
- **셋업 최소화**: 유사 작업을 묶어서 배합액/폭 교체 횟수 감소
- **납기 준수**: 가급적 납기일이 빠른 작업 우선 처리
- **자원 제약**: 기계는 한 번에 하나의 작업만 처리 가능

### 모듈의 출력
```python
result_df  # 스케줄링 결과 (각 작업의 할당 기계, 시작시간, 종료시간)
scheduler  # Scheduler 객체 (기계별 타임라인 정보 포함)
```

---

## 모듈 구성과 책임 분담

### 파일 구조 및 역할

```
scheduler/
├── __init__.py                  # 파이프라인 진입점
├── scheduling_core.py           # 핵심 스케줄링 로직 및 전략 패턴
├── scheduler.py                 # 기계 자원 관리 및 할당 실행
├── dispatch_rules.py            # 우선순위 규칙 생성
├── delay_dict.py                # 셋업 시간 계산
└── machine.py                   # 기계 타임라인 관리
```

---

### 1. `__init__.py` - 파이프라인 오케스트레이터

**핵심 함수**: `run_scheduler_pipeline()`

**역할**: 스케줄링 실행을 위한 사전 준비 및 전략 실행 호출

**수행 작업**:

#### Step 1: 디스패치 규칙 생성
```python
dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
```
- 모든 작업에 우선순위 부여
- 반환값: 우선순위 순서대로 정렬된 작업 ID 리스트

#### Step 2: DelayProcessor 초기화
```python
delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df, machine_code_list)
```
- 셋업 시간 계산을 담당할 객체 생성
- 공정 교체 시간 + 원단 폭 변경 시간 계산 준비

#### Step 3: Scheduler 객체 생성
```python
scheduler = Scheduler(machine_dict, delay_processor, machine_mapper)
scheduler.allocate_resources()
```
- 기계 자원 관리 객체 생성
- 각 기계를 `Machine_Time_window` 객체로 초기화

#### Step 4: 기계 중단 시간 설정
```python
scheduler.allocate_machine_downtime(machine_rest, base_date)
```
- 점검/고장 시간을 "DOWNTIME" 가짜 작업으로 차단
- 이후 스케줄링 시 자동으로 해당 시간 회피

#### Step 5: 스케줄링 전략 실행
```python
strategy = DispatchPriorityStrategy()
result = strategy.execute(
    dag_manager=manager,
    scheduler=scheduler,
    dag_df=dag_df,
    priority_order=dispatch_rule_ans,
    window_days=window_days
)
```
- 실제 스케줄링 알고리즘 실행
- 반환: 스케줄링 완료된 DataFrame

**비즈니스 의미**:
파이프라인은 "작업장 준비 → 작업 우선순위 정하기 → 실제 작업 배정"이라는 현실 프로세스를 반영합니다.

---

### 2. `dispatch_rules.py` - 우선순위 규칙 관리

**핵심 함수**: `create_dispatch_rule(dag_df, sequence_seperated_order)`

**비즈니스 문제**: "수백 개의 작업 중 무엇부터 처리할 것인가?"

#### 우선순위 결정 기준

```python
# 1순위: 납기일 (빠른 납기가 우선)
# 2순위: 원단 폭 (같은 납기면 넓은 폭 우선)
# 3순위: 노드 ID (동일 조건이면 ID 순)
```

#### 알고리즘: 위상 정렬 + 우선순위 큐

**Step 1: 진입차수(in-degree) 계산**
```python
각 노드에 대해:
  depth == 1 이면 in_degree = 0 (바로 실행 가능)
  depth > 1 이면 in_degree = 부모 노드 수
```

**Step 2: 초기 ready 큐 생성**
```python
in_degree == 0인 모든 노드를:
  (납기일, -원단폭, 노드ID) 형태로 heap에 추가

※ -원단폭: 넓은 폭이 먼저 나오도록 (heap은 최소값 우선)
```

**Step 3: 위상 정렬 실행**
```python
while ready 큐가 비지 않음:
    현재 = heap에서 pop() → 우선순위 가장 높은 작업
    answer에 추가

    현재의 모든 자식 노드에 대해:
        자식.in_degree -= 1

        if 자식.in_degree == 0:
            heap에 (자식.납기일, -자식.폭, 자식.ID) 추가
```

**결과**: `answer` - 위상 정렬 제약을 만족하면서 우선순위 순서로 정렬된 작업 리스트

#### 비즈니스 의미

**왜 위상 정렬인가?**
- 부모 작업이 자식보다 먼저 나오도록 보장
- DAG 구조 위반 방지 (코팅이 염색보다 먼저 스케줄되는 오류 차단)

**왜 납기일 우선인가?**
- 고객 만족도 직결
- 지각 패널티 최소화

**왜 원단 폭을 2순위로?**
- 같은 날짜 작업끼리는 폭 교체 횟수 최소화가 효율적
- 넓은 폭부터 처리 → 기계 조정 시간 감소

---

### 3. `delay_dict.py` - 셋업 시간 계산

**핵심 클래스**: `DelayProcessor`

**비즈니스 문제**: "두 작업을 연속 처리할 때 얼마나 준비 시간이 필요한가?"

#### 초기화
```python
def __init__(self, opnode_dict, operation_delay_df, width_change_df, machine_code_list):
    # 공정 교체 시간 딕셔너리 생성
    self.operation_delay_dict = {
        (이전공정, 다음공정): 교체시간
    }

    # 원단 폭 변경 시간 딕셔너리 생성
    self.width_change_dict = {
        기계코드: {
            (이전폭, 다음폭): 변경시간
        }
    }
```

#### 핵심 메서드: `delay_calc_whole_process()`

**입력**:
- `prev_id`: 이전 작업 ID
- `next_id`: 다음 작업 ID
- `machine_code`: 기계 코드

**계산 로직**:

```python
# 1. 이전/다음 작업 정보 추출
prev_operation = opnode_dict[prev_id]["OPERATION_CODE"]
next_operation = opnode_dict[next_id]["OPERATION_CODE"]
prev_width = opnode_dict[prev_id]["FABRIC_WIDTH"]
next_width = opnode_dict[next_id]["FABRIC_WIDTH"]

# 2. 공정 교체 시간 조회
operation_delay = operation_delay_dict.get((prev_operation, next_operation), 0)

# 3. 원단 폭 변경 시간 조회
width_delay = width_change_dict[machine_code].get((prev_width, next_width), 0)

# 4. 최종 지연 시간 = 둘 중 큰 값
delay = max(operation_delay, width_delay)
```

**왜 max()인가?**
- 공정이 바뀌면 기계를 완전히 재설정하므로 원단 폭도 초기화됨
- 공정 교체 시간 > 폭 변경 시간이면 폭 변경은 공정 교체에 포함됨
- 공정은 같은데 폭만 바뀌면 폭 변경 시간만 적용

#### 예시

**경우 1: 공정 변경 + 폭 변경**
```
이전: 염색 1524mm
다음: 코팅 1016mm

공정 교체: 염색→코팅 = 45분
폭 변경: 1524→1016 = 12분

delay = max(45, 12) = 45분
(공정 교체 시 폭도 새로 설정하므로)
```

**경우 2: 같은 공정, 폭만 변경**
```
이전: 염색 1524mm
다음: 염색 1016mm

공정 교체: 염색→염색 = 0분
폭 변경: 1524→1016 = 12분

delay = max(0, 12) = 12분
```

**비즈니스 가치**:
정확한 셋업 시간 계산으로 현실적인 스케줄 생성. 과소평가하면 실제 납기 못 맞춤, 과대평가하면 비효율 발생.

---

### 4. `scheduler.py` - 기계 자원 관리 및 할당 실행

**핵심 클래스**: `Scheduler`

**역할**: 기계 객체들을 관리하고, 실제 작업 할당 연산을 수행

#### 4.1 초기화 및 자원 할당

```python
def __init__(self, machine_dict, delay_processor, machine_mapper):
    self.machine_dict = machine_dict      # 작업별 기계 처리시간
    self.delay_processor = delay_processor # 셋업 시간 계산기
    self.machine_mapper = machine_mapper   # 기계 코드 관리
    self.Machines = {}                     # 기계 객체 딕셔너리
    self.aging_machine = None              # 에이징 전용 기계
```

**allocate_resources()**:
```python
# 일반 기계들 생성
for machine_code in machine_mapper.get_all_codes():
    self.Machines[machine_code] = Machine_Time_window(machine_code)

# 에이징 기계 생성 (중첩 허용)
self.aging_machine = Machine_Time_window(-1, allow_overlapping=True)
```

**비즈니스 의미**:
- 일반 기계: 동시에 1개 작업만 처리 (물리적 제약)
- 에이징 기계: 동시에 여러 작업 가능 (대기 시간이므로 물리적 공간 불필요)

---

#### 4.2 기계 중단 시간 할당

**allocate_machine_downtime(machine_rest, base_date)**

**비즈니스 문제**: "점검/고장으로 기계를 사용할 수 없는 시간을 어떻게 반영하나?"

**해결 방법**: 가짜 작업 "DOWNTIME" 사전 할당

```python
# 예: M1 기계가 6월 10일 10:00~14:00 점검
machine_rest DataFrame:
  기계코드  시작시간              종료시간
  M1      2024-06-10 10:00    2024-06-10 14:00

# base_date = 2024-06-01 00:00 기준으로 30분 단위 시간 변환
시작 = (10일 10시 - 1일 0시) = 9일 10시 = 228시간 = 456 (30분 단위)
종료 = (10일 14시 - 1일 0시) = 9일 14시 = 232시간 = 464 (30분 단위)

# M1 기계에 DOWNTIME 작업 강제 삽입
self.Machines["M1"].force_Input(-1, "DOWNTIME", 456, 464)
```

**결과**:
- 이후 assign_operation() 호출 시 DOWNTIME 구간은 자동으로 회피됨
- 기계는 "이미 작업이 할당된 시간"으로 인식

---

#### 4.3 최적 기계 선택 및 할당

**assign_operation(node_earliest_start, node_id, depth)**

**비즈니스 문제**: "이 작업을 어느 기계에 할당하면 가장 빨리 끝나는가?"

**알고리즘**:

```python
# 1. 작업이 수행 가능한 기계 목록 조회
machine_info = machine_dict[node_id]
# 예: {"M1": 120, "M2": 9999, "M3": 150}

# 2. 에이징 노드 특수 처리
if machine_info == {-1: 시간}:
    aging_machine에 즉시 할당
    return -1, node_earliest_start, 시간

# 3. 각 기계별 완료 시간 계산
for machine_code, processing_time in machine_info.items():
    if processing_time == 9999:
        continue  # 수행 불가 기계 제외

    # 해당 기계의 최조 시작 가능 시간 계산
    earliest_start = machine_earliest_start(machine_info, machine_code, ...)

    # 완료 시간 = 시작 + 처리시간
    completion_time = earliest_start + processing_time

    # 가장 빨리 끝나는 기계 추적
    if completion_time < best_completion_time:
        ideal_machine = machine_code
        best_completion_time = completion_time

# 4. 선택된 기계에 작업 할당
self.Machines[ideal_machine]._Input(depth, node_id, start, processing_time)
```

**machine_earliest_start() 상세**:

이 메서드가 **가장 복잡하고 중요한 비즈니스 로직**을 포함합니다.

**목표**: "이 기계에서 이 작업을 가장 빨리 시작할 수 있는 시점은?"

**고려사항**:
1. 작업의 최조 시작 가능 시간 (부모 작업 완료 시간)
2. 기계의 현재 종료 시간
3. 셋업 시간 (이전 작업과의 공정/폭 차이)
4. 기계의 빈 시간창 (중간에 빈 구간 활용 가능성)

**로직**:

```python
# 1. 기본 정보 추출
processing_time = machine_info[machine_code]
node_earliest = node_earliest_start  # 부모 작업 완료 시간
machine_end_time = Machines[machine_code].End_time  # 기계 현재 종료
assigned_tasks = Machines[machine_code].assigned_task  # 할당된 작업 리스트

# 2. 셋업 시간 계산
if assigned_tasks:
    last_task = assigned_tasks[-1][1]  # 마지막 작업 ID
    delay = delay_processor.delay_calc_whole_process(
        last_task, node_id, machine_code
    )
else:
    delay = 0  # 첫 작업이면 셋업 없음

# 3. 기본 시작 시간 = max(노드 준비 시간, 기계 종료+셋업)
machine_earliest = max(node_earliest, machine_end_time + delay)

# 4. 빈 시간창 탐색 (선택적 최적화)
empty_windows = Machines[machine_code].Empty_time_window()
# 반환: ([시작1, 시작2], [종료1, 종료2], [길이1, 길이2])

for i, window_length in enumerate(empty_windows[2]):
    window_start = empty_windows[0][i]
    window_end = empty_windows[1][i]

    # 경우 1: 빈 창이 충분히 크고, 노드 준비 후 사용 가능
    if (window_length >= processing_time and
        window_start >= node_earliest):

        # 앞 작업과의 셋업 시간 계산
        prev_task = assigned_tasks[i-1][1] if i > 0 else None
        if prev_task:
            earlier_delay = delay_processor.delay_calc_whole_process(
                prev_task, node_id, machine_code
            )
        else:
            earlier_delay = 0

        # 뒤 작업과의 셋업 시간 계산
        next_task = assigned_tasks[i][1]
        later_delay = delay_processor.delay_calc_whole_process(
            node_id, next_task, machine_code
        )

        # 실제 필요 공간 = 앞 셋업 + 처리시간 + 뒤 셋업
        if window_length >= earlier_delay + processing_time + later_delay:
            machine_earliest = window_start + earlier_delay
            break  # 첫 번째 적합한 창 사용

    # 경우 2: 노드 준비 시간이 창 중간에 있는 경우
    if (window_start < node_earliest and
        window_end - node_earliest >= processing_time):

        # 유사한 셋업 시간 계산...
        # 실제 시작 = max(창 시작+앞셋업, 노드준비)
        # ...

return machine_earliest, machine_code, processing_time, ...
```

**비즈니스 의미**:

**빈 시간창 활용의 가치**:
```
기계 타임라인:
0────100───150──────300───500
     작업1  (빈 창)   작업2

새 작업: 처리시간 120분, 준비 완료 시간 80분

빈 창 미활용: 500분 시작 → 620분 완료
빈 창 활용: 150분 시작 → 270분 완료 (350분 단축!)
```

이런 최적화가 수백 번 누적되면 전체 makespan이 크게 감소합니다.

---

#### 4.4 강제 기계 할당

**force_assign_operation(machine_code, node_earliest_start, node_id, depth, machine_window_flag)**

**언제 사용하는가?**
- 셋업 최소화 전략에서 리더와 같은 기계에 그룹 작업 할당
- 사용자가 수동으로 기계를 지정한 경우

**차이점**:
- `assign_operation()`: 모든 기계 비교 후 최적 선택
- `force_assign_operation()`: 지정된 기계만 사용

**machine_window_flag**:
- `False`: 빈 시간창 활용 시도 (기본값)
- `True`: 기계 맨 뒤에만 추가 (재스케줄링 시)

**로직**:
```python
# 지정 기계에서 수행 가능한지 확인
processing_time = machine_dict[node_id].get(machine_code, 9999)
if processing_time == 9999:
    return False, None, None  # 수행 불가

# 해당 기계의 최조 시작 시간만 계산
earliest_start = machine_earliest_start(
    machine_info, machine_code, node_earliest_start, node_id,
    machine_window_flag=machine_window_flag
)

# 해당 기계에 할당
self.Machines[machine_code]._Input(depth, node_id, earliest_start, processing_time)
return True, earliest_start, processing_time
```

---

### 5. `scheduling_core.py` - 핵심 스케줄링 로직 및 전략

이 파일이 **scheduler 모듈의 심장부**입니다.

#### 5.1 SchedulingCore - 기본 스케줄링 연산

**클래스 역할**: 노드 스케줄링의 원자적 연산 제공 (static methods)

##### validate_ready_node()
```python
def validate_ready_node(node) -> bool:
    return node.parent_node_count == 0
```
**의미**: "선행 작업이 모두 완료되었는가?"

##### calculate_start_time()
```python
def calculate_start_time(node) -> float:
    if not node.parent_node_end:
        return 0.0

    valid_times = [t for t in node.parent_node_end if t is not None]
    if not valid_times:
        return 0.0

    return max(valid_times)
```
**의미**: "부모 작업들 중 가장 늦게 끝나는 시점이 내 최조 시작 시점"

##### update_node_state()
```python
def update_node_state(node, machine_index, start_time, processing_time):
    node.machine = machine_index
    node.node_start = start_time
    node.processing_time = processing_time
    node.node_end = start_time + processing_time
```
**의미**: "작업 할당 결과를 노드에 기록"

##### update_dependencies()
```python
def update_dependencies(node):
    for child in node.children:
        child.parent_node_count -= 1  # 선행 작업 1개 완료
        child.parent_node_end.append(node.node_end)  # 종료 시간 전달
```
**의미**: "내가 끝났으니 자식 작업들에게 알림"

##### schedule_ready_aging_children()
```python
def schedule_ready_aging_children(node, scheduler):
    for child in node.children:
        if child.parent_node_count == 0:  # 스케줄 가능
            machine_info = scheduler.machine_dict.get(child.id)
            is_aging = machine_info and set(machine_info.keys()) == {-1}

            if is_aging:
                # 에이징 노드는 즉시 자동 스케줄링
                SchedulingCore.schedule_single_node(
                    child, scheduler, AgingMachineStrategy()
                )
```
**의미**: "내 작업이 끝나면서 자식 중 에이징 노드가 준비되었다면 즉시 처리"

##### schedule_single_node() - 가장 중요한 메서드

**역할**: 노드 하나를 완전히 스케줄링하는 통합 프로세스

```python
def schedule_single_node(node, scheduler, machine_assignment_strategy) -> bool:
    # 1. 선행 작업 완료 검증
    if not SchedulingCore.validate_ready_node(node):
        return False  # 아직 스케줄 불가

    # 2. 최조 시작 가능 시간 계산
    earliest_start = SchedulingCore.calculate_start_time(node)
    node.earliest_start = earliest_start

    # 3. 에이징 노드 자동 감지
    machine_info = scheduler.machine_dict.get(node.id)
    is_aging = machine_info and set(machine_info.keys()) == {-1}

    if is_aging:
        strategy = AgingMachineStrategy()  # 에이징 전용 전략
    else:
        strategy = machine_assignment_strategy  # 전달받은 전략

    # 4. 기계 할당 실행
    assignment_result = strategy.assign(scheduler, node, earliest_start)

    if not assignment_result.success:
        return False  # 할당 실패

    # 5. 노드 상태 업데이트
    SchedulingCore.update_node_state(
        node,
        assignment_result.machine_index,
        assignment_result.start_time,
        assignment_result.processing_time
    )

    # 6. 후속 작업 의존성 업데이트
    SchedulingCore.update_dependencies(node)

    # 7. 에이징 자식 노드 자동 스케줄링
    SchedulingCore.schedule_ready_aging_children(node, scheduler)

    return True
```

**이 메서드의 비즈니스 가치**:
- **일관성**: 모든 노드 스케줄링이 동일한 6단계 프로세스를 거침
- **안전성**: 의존성 검증 → 할당 → 상태 업데이트 → 전파 순서 보장
- **확장성**: 전략 패턴으로 다양한 할당 방식 지원

---

#### 5.2 기계 할당 전략 (MachineAssignmentStrategy)

**전략 패턴 적용 이유**:
- 같은 노드라도 상황에 따라 다른 할당 방식 필요
- 코드 중복 없이 다양한 전략 구현

##### OptimalMachineStrategy - 최적 기계 자동 선택

**언제**: 윈도우/그룹의 첫 작업 (리더)

**목표**: 가장 빨리 완료되는 기계 선택

```python
def assign(self, scheduler, node, earliest_start) -> AssignmentResult:
    machine_idx, start_time, processing_time = scheduler.assign_operation(
        earliest_start, node.id, node.depth
    )

    return AssignmentResult(
        success=True,
        machine_index=machine_idx,
        start_time=start_time,
        processing_time=processing_time
    )
```

##### ForcedMachineStrategy - 특정 기계 강제 할당

**언제**:
- 같은 배합액 그룹 작업 (리더와 같은 기계 사용)
- 사용자 재스케줄링

**목표**: 셋업 시간 최소화 (기계 전환 없음)

```python
def __init__(self, target_machine_idx, use_machine_window=False):
    self.target_machine_idx = target_machine_idx
    self.use_machine_window = use_machine_window

def assign(self, scheduler, node, earliest_start) -> AssignmentResult:
    flag, start_time, processing_time = scheduler.force_assign_operation(
        self.target_machine_idx,
        earliest_start,
        node.id,
        node.depth,
        machine_window_flag=self.use_machine_window
    )

    return AssignmentResult(
        success=flag,
        machine_index=self.target_machine_idx if flag else None,
        start_time=start_time if flag else None,
        processing_time=processing_time if flag else None
    )
```

##### AgingMachineStrategy - 에이징 전용 할당

**언제**: 에이징 노드 자동 스케줄링

**특징**: 중첩 허용 (여러 제품 동시 에이징 가능)

```python
def assign(self, scheduler, node, earliest_start) -> AssignmentResult:
    machine_info = scheduler.machine_dict.get(node.id)

    # 에이징 노드 검증
    if not machine_info or set(machine_info.keys()) != {-1}:
        raise ValueError(f"Node {node.id} is not an aging node")

    processing_time = machine_info[-1]
    start_time = earliest_start  # 즉시 시작

    # 에이징 기계에 할당 (중첩 허용)
    scheduler.aging_machine._Input(
        node.depth, node.id, start_time, processing_time
    )

    return AssignmentResult(
        success=True,
        machine_index=-1,
        start_time=start_time,
        processing_time=processing_time
    )
```

---

#### 5.3 고수준 스케줄링 전략 (HighLevelSchedulingStrategy)

##### DispatchPriorityStrategy - 우선순위 디스패치 전략

**전체 스케줄링의 최상위 제어 로직**

**핵심 아이디어**: "납기 유사 작업들을 윈도우로 묶어 집중 처리"

**execute() 메서드 흐름**:

```python
def execute(self, dag_manager, scheduler, dag_df, priority_order, window_days=5):
    # 1. 에이징 노드 필터링 (일반 노드만 처리)
    filtered_priority = [일반 노드만]
    aging_nodes = [에이징 노드들]
    # 에이징은 부모 완료 시 자동 스케줄되므로 제외

    # 2. 우선순위 + 납기일 결합
    result = [(node_id, due_date) for node_id in filtered_priority]

    # 3. 셋업 최소화 전략 객체 생성
    setup_strategy = SetupMinimizedStrategy()

    # 4. 윈도우별 반복 처리
    while result:
        # 4-1. 윈도우 생성
        base_date = result[0][1]  # 첫 번째 작업의 납기일
        window_result = [
            node_id for node_id, due_date in result
            if abs((due_date - base_date).days) <= window_days
        ]

        # 4-2. 윈도우 내 셋업 최소화 스케줄링
        used_ids = setup_strategy.execute(
            dag_manager, scheduler,
            window_result[0],      # 리더
            window_result[1:]      # 후보들
        )

        # 4-3. 처리된 작업 제거
        if used_ids:
            result = [item for item in result if item[0] not in used_ids]
        else:
            # 무한루프 방지: 아무것도 처리 안 되면 첫 작업 강제 제거
            result = result[1:]

    return dag_manager.to_dataframe()
```

**윈도우 크기의 비즈니스 의미**:

```
window_days = 5일 설정 시:

시나리오 A: 납기 6/15, 6/16, 6/17, 6/25, 6/26 작업들

윈도우 1: 6/15 기준 → 6/10~6/20 범위
  → 6/15, 6/16, 6/17 포함 (3개)
  → 이들을 묶어서 셋업 최소화 처리

윈도우 2: 6/25 기준 → 6/20~6/30 범위
  → 6/25, 6/26 포함 (2개)
  → 별도로 처리

결과: 납기 가까운 작업들끼리 그룹화되어 납기 준수율 향상
     + 그룹 내에서는 유사 작업 묶어 효율 확보
```

---

##### SetupMinimizedStrategy - 셋업 최소화 전략

**이것이 scheduler 모듈의 가장 핵심적인 비즈니스 로직입니다.**

**목표**: 유사 작업을 그룹화하여 배합액/폭 교체 최소화

**execute() 메서드 상세**:

**입력**:
- `start_id`: 윈도우의 첫 번째 작업 (리더)
- `window`: 윈도우 내 나머지 작업 ID 리스트

**출력**:
- `used_ids`: 이번에 스케줄링된 작업 ID 리스트

**알고리즘 단계**:

```python
def execute(self, dag_manager, scheduler, start_id, window):
    node = dag_manager.nodes[start_id]

    # ===== Step 1: 리더 노드 스케줄링 =====
    strategy = OptimalMachineStrategy()
    success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

    if not success:
        return []  # 리더 실패 시 중단

    ideal_machine_index = node.machine  # 리더가 선택한 기계

    # ===== Step 2: 리더의 최적 배합액 선택 =====
    first_node_dict = dag_manager.opnode_dict[start_id]
    operation_name = first_node_dict["OPERATION_CODE"]

    # 윈도우 내 같은 공정 작업들만 추출 (ready + aging 제외)
    same_operation_nodes = [
        gene for gene in window
        if dag_manager.opnode_dict.get(gene)  # aging은 opnode_dict에 없음
        and dag_manager.opnode_dict[gene]["OPERATION_CODE"] == operation_name
        and SchedulingCore.validate_ready_node(dag_manager.nodes[gene])
    ]

    # 리더의 최적 배합액 결정
    best_chemical = find_best_chemical(
        first_node_dict, same_operation_nodes, dag_manager
    )
    dag_manager.opnode_dict[start_id]["SELECTED_CHEMICAL"] = best_chemical

    # ===== Step 3: 같은 배합액 그룹 생성 =====
    same_chemical_queue = []
    remaining_operation_queue = []

    for gene in same_operation_nodes:
        gene_dict = dag_manager.opnode_dict[gene]

        if (best_chemical and
            best_chemical in gene_dict["CHEMICAL_LIST"] and
            SchedulingCore.validate_ready_node(dag_manager.nodes[gene])):
            same_chemical_queue.append(gene)
            gene_dict["SELECTED_CHEMICAL"] = best_chemical
        else:
            remaining_operation_queue.append(gene)

    # ===== Step 4: 같은 배합액 그룹 너비 정렬 =====
    same_chemical_queue = sorted(
        same_chemical_queue,
        key=lambda gene: dag_manager.opnode_dict[gene]["FABRIC_WIDTH"],
        reverse=True  # 넓은 폭부터
    )

    # ===== Step 5: 같은 배합액 그룹 스케줄링 =====
    used_ids = [start_id]
    for same_chemical_id in same_chemical_queue:
        node = dag_manager.nodes[same_chemical_id]
        strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
        success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

        if success:
            used_ids.append(same_chemical_id)
        else:
            remaining_operation_queue.append(same_chemical_id)

    # ===== Step 6: 남은 작업들 반복 처리 =====
    iter_count = 0
    while remaining_operation_queue:
        iter_count += 1
        if iter_count > 50:
            break  # 무한루프 방지

        # 6-1. ready 아닌 노드 제거
        remaining_operation_queue = [
            g for g in remaining_operation_queue
            if SchedulingCore.validate_ready_node(dag_manager.nodes[g])
        ]

        if not remaining_operation_queue:
            break

        # 6-2. 새 리더 선정
        leader_id = remaining_operation_queue[0]
        leader_dict = dag_manager.opnode_dict[leader_id]

        # 6-3. 새 리더의 최적 배합액 선택
        leader_best_chemical = find_best_chemical(
            leader_dict, remaining_operation_queue, dag_manager
        )
        leader_dict["SELECTED_CHEMICAL"] = leader_best_chemical

        # 6-4. 현재 배합액 그룹 생성
        current_chemical_group = [leader_id]
        next_remaining = []

        for gene in remaining_operation_queue[1:]:
            gene_dict = dag_manager.opnode_dict[gene]

            if (leader_best_chemical and
                leader_best_chemical in gene_dict["CHEMICAL_LIST"] and
                SchedulingCore.validate_ready_node(dag_manager.nodes[gene])):
                current_chemical_group.append(gene)
                gene_dict["SELECTED_CHEMICAL"] = leader_best_chemical
            else:
                next_remaining.append(gene)

        # 6-5. 현재 그룹 너비 정렬
        current_chemical_group = sorted(
            current_chemical_group,
            key=lambda gene: dag_manager.opnode_dict[gene]["FABRIC_WIDTH"],
            reverse=True
        )

        # 6-6. 현재 그룹 스케줄링
        for chemical_id in current_chemical_group:
            node = dag_manager.nodes[chemical_id]

            if not SchedulingCore.validate_ready_node(node):
                next_remaining.append(chemical_id)
                continue

            strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
            success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

            if success:
                used_ids.append(chemical_id)
            else:
                next_remaining.append(chemical_id)

        # 6-7. 진행 없으면 중단
        if len(next_remaining) == len(remaining_operation_queue):
            break

        remaining_operation_queue = next_remaining

    return used_ids
```

**find_best_chemical() 헬퍼 함수**:

```python
def find_best_chemical(first_node_dict, window_nodes, dag_manager):
    """
    리더 노드의 배합액 선택지 중 윈도우 내 가장 많은 작업에 적용 가능한 배합액 선택
    """
    chemical_list = first_node_dict["CHEMICAL_LIST"]

    if not chemical_list or chemical_list == ():
        return None

    # 각 배합액별 사용 가능 작업 수 카운트
    chemical_counts = {}
    for chemical in chemical_list:
        count = 0
        for node_id in window_nodes:
            node_dict = dag_manager.opnode_dict.get(node_id)
            if node_dict and chemical in node_dict["CHEMICAL_LIST"]:
                count += 1
        chemical_counts[chemical] = count

    if not chemical_counts:
        return None

    # 가장 많이 사용 가능한 배합액 반환
    best_chemical = max(chemical_counts, key=chemical_counts.get)
    return best_chemical
```

**실제 동작 예시**:

```
윈도우: 염색 공정 작업 10개

리더: 작업#1
  - 가능 배합액: [A, B, C]
  - 윈도우 내 배합액별 사용 가능 수:
    A: 6개, B: 2개, C: 4개
  → 배합액 A 선택
  → M1 기계 할당 (OptimalMachineStrategy)

같은 배합액 A 그룹:
  - 작업#3 (1524mm), 작업#5 (1524mm), 작업#7 (1016mm), 작업#9 (914mm), 작업#2 (508mm)
  → 너비 정렬: [#3, #5, #7, #9, #2]
  → 모두 M1에 강제 할당 (ForcedMachineStrategy)
  → 배합액 교체 없음, 폭 교체만 5회

남은 작업: 4개
  - 새 리더: 작업#4
  - 가능 배합액: [B, C]
  - 남은 작업 중 B: 2개, C: 2개
  → 배합액 B 선택 (동수면 첫 번째)
  → M1에 계속 할당

  같은 배합액 B 그룹:
    - 작업#6 (1016mm), 작업#8 (914mm)
    → M1에 연속 할당
    → 배합액 A→B 교체 1회

남은 작업: 2개 (배합액 C만 가능)
  - 새 리더: 작업#10
  → 배합액 C 선택
  → 작업#10, #11 M1에 할당
  → 배합액 B→C 교체 1회

결과:
  M1 기계에 10개 작업 모두 할당
  배합액 교체: 2회 (A→B→C)
  원단 폭 교체: 약 7-8회

vs. 단순 우선순위만 따를 경우:
  배합액 교체: 6-8회 발생 가능
  → 셋업 시간 절약: 2-4시간
```

**비즈니스 가치**:

1. **배합액 교체 최소화**
   - 한 번 교체에 30-60분 소요
   - 같은 배합액 그룹화로 교체 횟수 크게 감소

2. **원단 폭 교체 최소화**
   - 넓은 폭 → 좁은 폭 순서로 처리
   - 기계 조정 시간 단축 (좁→넓보다 넓→좁이 빠름)

3. **기계 전환 최소화**
   - 같은 기계에 그룹 작업 모두 할당
   - 기계 간 이동 없이 연속 처리

4. **동적 그룹 재구성**
   - 첫 그룹 처리 후 남은 작업으로 새 그룹 생성
   - 의존성 해소로 새로 ready된 작업 즉시 반영

---

##### UserRescheduleStrategy - 사용자 재스케줄링 전략

**언제 사용**: 사용자가 수동으로 기계별 작업 순서 조정 시

**입력**: `machine_queues = {기계코드: [작업ID 리스트]}`

**로직**:
```python
def execute(self, dag_manager, scheduler, machine_queues):
    progress = True

    while progress:
        progress = False

        for machine_idx, queue in machine_queues.items():
            if not queue:
                continue

            node_id = queue[0]  # 큐 맨 앞 작업
            node = dag_manager.nodes[node_id]

            # 강제 기계 할당 (빈 시간창 사용 안 함)
            strategy = ForcedMachineStrategy(
                machine_idx, use_machine_window=True
            )
            success = SchedulingCore.schedule_single_node(
                node, scheduler, strategy
            )

            if success:
                queue.pop(0)  # 성공 시 큐에서 제거
                progress = True

    return dag_manager.to_dataframe()
```

**use_machine_window=True의 의미**:
- 기계 맨 뒤에만 추가
- 빈 시간창 삽입 시도 안 함
- 사용자가 지정한 순서 그대로 유지

---

### 6. `machine.py` - 기계 타임라인 관리

**핵심 클래스**: `Machine_Time_window`

**역할**: 개별 기계의 작업 타임라인 관리

**주요 속성**:
```python
self.Machine_code = machine_code      # 기계 코드 (예: "M1")
self.assigned_task = []               # [(depth, node_id), ...]
self.O_start = []                     # 각 작업 시작 시간
self.O_end = []                       # 각 작업 종료 시간
self.End_time = 0                     # 현재 마지막 작업 종료 시간
self.allow_overlapping = False        # 작업 중첩 허용 여부 (aging만 True)
```

**핵심 메서드**:

##### _Input() - 작업 할당
```python
def _Input(self, depth, operation, start_time, processing_time):
    end_time = start_time + processing_time

    # 작업 삽입 위치 찾기 (시간 순 정렬 유지)
    insert_pos = 0
    for i, existing_start in enumerate(self.O_start):
        if start_time < existing_start:
            break
        insert_pos = i + 1

    # 삽입
    self.assigned_task.insert(insert_pos, (depth, operation))
    self.O_start.insert(insert_pos, start_time)
    self.O_end.insert(insert_pos, end_time)

    # 마지막 종료 시간 업데이트
    self.End_time = max(self.End_time, end_time)
```

##### Empty_time_window() - 빈 시간창 계산
```python
def Empty_time_window(self):
    """
    작업 간 빈 시간 구간 찾기

    반환: (시작시간 리스트, 종료시간 리스트, 길이 리스트)
    """
    if not self.assigned_task:
        return ([], [], [])

    starts, ends, lengths = [], [], []

    for i in range(len(self.assigned_task) - 1):
        gap_start = self.O_end[i]
        gap_end = self.O_start[i+1]
        gap_length = gap_end - gap_start

        if gap_length > 0:  # 실제 빈 시간이 있으면
            starts.append(gap_start)
            ends.append(gap_end)
            lengths.append(gap_length)

    return (starts, ends, lengths)
```

**비즈니스 의미**:
```
기계 타임라인:
0────100───150──────300───500
     작업1  (빈창)   작업2

Empty_time_window() 반환:
  starts = [100]
  ends = [150]
  lengths = [50]

→ scheduler가 이 50분 구간에 작업 삽입 가능 여부 판단
```

---

## 실행 흐름과 의사결정 과정

### 전체 실행 순서

```
1. run_scheduler_pipeline() 호출
   ├─ create_dispatch_rule() → 우선순위 정렬
   ├─ Scheduler 객체 생성 및 자원 할당
   ├─ allocate_machine_downtime() → DOWNTIME 차단
   └─ DispatchPriorityStrategy.execute() 호출

2. DispatchPriorityStrategy.execute()
   └─ while 작업 남음:
       ├─ 윈도우 생성 (납기 ±5일)
       └─ SetupMinimizedStrategy.execute(리더, 윈도우)

3. SetupMinimizedStrategy.execute()
   ├─ 리더 스케줄링 (OptimalMachineStrategy)
   ├─ 최적 배합액 선택
   ├─ 같은 배합액 그룹 스케줄링 (ForcedMachineStrategy)
   └─ while 남은 작업:
       └─ 새 리더로 반복

4. SchedulingCore.schedule_single_node()
   ├─ validate_ready_node() → 선행 작업 확인
   ├─ calculate_start_time() → 최조 시작 시간
   ├─ strategy.assign() → 기계 할당
   ├─ update_node_state() → 노드 상태 기록
   ├─ update_dependencies() → 자식에게 전파
   └─ schedule_ready_aging_children() → 에이징 자동 처리

5. MachineAssignmentStrategy.assign()
   ├─ OptimalMachineStrategy:
   │   └─ scheduler.assign_operation() → 모든 기계 비교
   ├─ ForcedMachineStrategy:
   │   └─ scheduler.force_assign_operation() → 지정 기계만
   └─ AgingMachineStrategy:
       └─ aging_machine._Input() → 즉시 할당

6. Scheduler.assign_operation() / force_assign_operation()
   └─ machine_earliest_start()
       ├─ 기계 종료 시간 조회
       ├─ 셋업 시간 계산 (DelayProcessor)
       ├─ 빈 시간창 탐색
       └─ 최적 시작 시간 반환
```

### 의사결정 트리

#### 레벨 1: 어떤 작업부터 처리할 것인가?
```
create_dispatch_rule()
├─ 납기일 빠른 순
├─ 같은 날이면 원단 폭 넓은 순
└─ 같은 폭이면 ID 순
```

#### 레벨 2: 윈도우를 어떻게 구성할 것인가?
```
DispatchPriorityStrategy
├─ 첫 작업의 납기일 ± window_days
└─ 해당 범위 내 모든 작업 포함
```

#### 레벨 3: 윈도우 내에서 어떤 순서로 처리할 것인가?
```
SetupMinimizedStrategy
├─ 리더 작업 먼저
├─ 리더와 같은 공정 중
│   ├─ 같은 배합액 사용 가능한 작업들
│   │   └─ 원단 폭 넓은 순
│   └─ 배합액 다른 작업들 → 다음 그룹으로
└─ 남은 작업으로 새 리더 선정 반복
```

#### 레벨 4: 어떤 기계에 할당할 것인가?
```
OptimalMachineStrategy (리더)
├─ 수행 가능한 모든 기계 비교
├─ 각 기계의 완료 시간 계산
└─ 가장 빨리 끝나는 기계 선택

ForcedMachineStrategy (그룹)
└─ 리더와 같은 기계에 강제 할당
```

#### 레벨 5: 언제 시작할 것인가?
```
machine_earliest_start()
├─ 작업 준비 시간 (부모 완료)
├─ 기계 종료 시간
├─ 셋업 시간
└─ max(작업준비, 기계종료+셋업)
    └─ 빈 시간창 있으면 거기에 삽입 시도
```

---

## 알고리즘의 시간 복잡도 및 성능

### 복잡도 분석

**전체 스케줄링**:
- N: 작업 수
- M: 기계 수
- W: 윈도우 크기

```
create_dispatch_rule: O(N log N)  # heap 기반 위상 정렬

DispatchPriorityStrategy:
  윈도우 수: O(N/W)
  윈도우당 처리: O(W²)
  → 총합: O(N × W)

SetupMinimizedStrategy (윈도우당):
  같은 공정 필터링: O(W)
  배합액 선택: O(W × C) (C: 배합액 종류)
  그룹 정렬: O(G log G) (G: 그룹 크기)
  그룹 스케줄링: O(G × M) (기계 할당)
  → 윈도우당: O(W²)

assign_operation (작업당):
  기계 비교: O(M)
  빈 시간창 탐색: O(K) (K: 해당 기계 작업 수)
  → 작업당: O(M × K)

전체: O(N log N + N × W + N × M × K)
```

### 실용적 성능

**일반적 케이스**:
- N = 500 작업
- M = 20 기계
- W = 50 (윈도우 크기)
- K = 25 (기계당 평균 작업 수)

→ 예상 시간: 수초 ~ 수십초

**최악 케이스**:
- N = 5000 작업
- M = 100 기계
- W = 500

→ 예상 시간: 수분

**성능 최적화 요소**:
1. 윈도우 크기 제한으로 전역 탐색 회피
2. 딕셔너리 기반 O(1) 조회
3. 빈 시간창은 첫 번째 적합한 곳 사용 (완전 탐색 안 함)

---

## 시스템의 강점과 한계

### 강점

**1. 현실적 제약 반영**
- 공정 순서, 셋업 시간, 기계 중단, 에이징 등 실제 생산 환경 고려
- 9999 값, DOWNTIME 작업 등 우아한 제약 표현

**2. 계층적 최적화**
- 윈도우 레벨: 납기 준수
- 그룹 레벨: 셋업 최소화
- 작업 레벨: 기계 완료 시간 최소화

**3. 확장 가능한 설계**
- 전략 패턴으로 새로운 할당 방식 추가 용이
- static method로 재사용 가능한 연산 제공

**4. 동적 대응**
- 의존성 해소 시 즉시 작업 추가
- 에이징 자동 스케줄링
- 빈 시간창 활용

### 한계

**1. 로컬 최적해**
- 윈도우 내에서만 최적화
- 윈도우 경계에서 비효율 발생 가능

**2. 탐욕적 결정**
- 리더 선택이 전체 결과에 큰 영향
- 다른 리더 선택 시 더 나은 결과 가능성

**3. 결정론적**
- 같은 입력에 같은 출력
- 확률적 방법(유전 알고리즘 등) 대비 다양성 부족

**4. 불확실성 미고려**
- 실제 처리 시간 변동성 무시
- 돌발 상황 대응 어려움

### 개선 방향

**1. 메타휴리스틱 결합**
- 현재 알고리즘으로 초기해 생성
- 유전 알고리즘/시뮬레이티드 어닐링으로 개선

**2. 룩어헤드 (Look-ahead)**
- 윈도우 경계 너머 작업 미리 고려
- 더 나은 배합액 선택 가능

**3. 동적 윈도우 크기**
- 작업 밀집도에 따라 윈도우 크기 조정
- 유연한 납기-효율 균형

**4. 불확실성 반영**
- 처리 시간에 안전 마진 추가
- 로버스트 스케줄링 기법 적용

---

## 요약

scheduler 모듈은 **계층적 그룹화 + 탐욕적 로컬 최적화**를 핵심으로 하는 실용적 스케줄링 시스템입니다.

**핵심 의사결정**:
1. **우선순위 정렬**: 납기 → 원단 폭 순
2. **윈도우 구성**: 납기 유사 작업 묶음
3. **셋업 최소화**: 같은 배합액 그룹화 + 폭 정렬
4. **기계 선택**: 리더는 최적, 그룹은 강제
5. **시간 할당**: 빈 시간창 활용

**비즈니스 가치**:
- 납기 준수율 향상 (윈도우 기반 처리)
- 생산 효율 개선 (셋업 시간 최소화)
- 현실 반영 (제약조건 정확한 모델링)
- 실행 속도 (다항 시간 알고리즘)

이 모듈은 "완벽한 최적해"보다는 "빠르게 얻을 수 있는 좋은 해"를 지향하며, 실제 생산 환경에서 충분히 실용적인 스케줄을 생성합니다.
