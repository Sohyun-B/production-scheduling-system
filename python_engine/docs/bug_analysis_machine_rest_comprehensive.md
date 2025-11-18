# Machine Rest 버그 종합 분석 보고서

## 목차
1. [문제 요약](#문제-요약)
2. [두 가지 독립적 버그](#두-가지-독립적-버그)
3. [버그 A: OptimalMachineStrategy success 판정 오류](#버그-a-optimalmachinestrategy-success-판정-오류)
4. [버그 B: DOWNTIME delay 계산 KeyError](#버그-b-downtime-delay-계산-keyerror)
5. [두 버그의 상호작용](#두-버그의-상호작용)
6. [추가 발견 문제점](#추가-발견-문제점)
7. [종합 해결 방안](#종합-해결-방안)

---

## 문제 요약

**증상**: `machine_rest` (기계 중단 시간) 데이터를 입력하면 해당 기계에 작업이 아예 할당되지 않고 에러 발생

**근본 원인**: **2개의 독립적인 버그가 동시에 작용**
1. **버그 A**: `OptimalMachineStrategy`가 `machine_idx=None`일 때도 `success=True` 반환
2. **버그 B**: DOWNTIME 작업과 delay 계산 시 `KeyError: 'SELECTED_CHEMICAL'` 발생

---

## 두 가지 독립적 버그

### 버그의 독립성

이 두 버그는 **서로 다른 경로**에서 발생하며, **각각 독립적으로 시스템을 망가뜨림**:

| 측면 | 버그 A (success 판정) | 버그 B (KeyError) |
|------|----------------------|-------------------|
| 발생 위치 | `scheduling_core.py:OptimalMachineStrategy` | `delay_dict.py:calculate_delay()` |
| 발생 시점 | 기계 할당 결과 반환 시 | Delay 계산 시 |
| 직접 원인 | 논리 오류 (None 체크 누락) | 데이터 오류 (키 누락) |
| 영향 | 유령 노드 생성, Dependency 오염 | 프로그램 크래시 또는 잘못된 delay=0 |
| 단독 영향 | machine_rest 없어도 발생 가능 | machine_rest 있어야 발생 |

---

## 버그 A: OptimalMachineStrategy success 판정 오류

### A-1. 버그 위치

**파일**: `scheduling_core.py`
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

### A-2. 왜 machine_idx가 None인가?

**`scheduler.assign_operation()` 반환값 분석**:

```python
# scheduler.py:176-233
def assign_operation(self, node_earliest_start, node_id, depth):
    machine_info = self.machine_dict.get(node_id)
    ideal_machine_code = None  # ← 초기값 None
    ideal_machine_processing_time = float('inf')
    best_earliest_start = float('inf')

    for machine_code, machine_processing_time in machine_info.items():
        if machine_processing_time != 9999:  # 수행 가능한 기계만
            earliest_start = self.machine_earliest_start(...)[0]

            # 최소 완료시간 기준 선택
            if (earliest_start + machine_processing_time) < \
               (best_earliest_start + ideal_machine_processing_time):
                ideal_machine_code = machine_code  # ← 여기서 설정됨
                ideal_machine_processing_time = machine_processing_time
                best_earliest_start = earliest_start

    # ⭐ 선택된 기계에 작업 할당
    if ideal_machine_code is not None:
        self.Machines[ideal_machine_code]._Input(...)
    else:
        print(f"[경고] 노드 {node_id}: 사용 가능한 기계 없음")

    return ideal_machine_code, best_earliest_start, ideal_machine_processing_time
    # ← ideal_machine_code = None 반환 가능!
```

**None이 반환되는 경우**:
1. `machine_info`의 모든 기계가 `9999` (수행 불가)
2. 모든 기계가 DOWNTIME으로 차단됨 (접근 불가)
3. delay 계산 실패로 기계 선택 안 됨

### A-3. 버그의 영향

**"유령 노드" 생성 메커니즘**:

```python
# 1. schedule_single_node() 호출
assignment_result = strategy.assign(scheduler, node, earliest_start)
# AssignmentResult(success=True, machine_index=None, start_time=inf, processing_time=inf)

# 2. success 체크 (통과!)
if not assignment_result.success:  # success=True이므로 False
    return False
# ← 여기서 걸러져야 하는데 통과함!

# 3. 노드 상태 업데이트 (잘못된 값으로!)
SchedulingCore.update_node_state(
    node,
    assignment_result.machine_index,  # None
    assignment_result.start_time,     # inf
    assignment_result.processing_time  # inf
)
# 결과: node.machine = None, node.node_start = inf, node.node_end = inf

# 4. Dependency 업데이트 (치명적!)
SchedulingCore.update_dependencies(node)
for child in node.children:
    child.parent_node_count -= 1  # ← 부모가 실제론 스케줄 안 됐는데 감소!
    child.parent_node_end.append(node.node_end)  # ← inf 추가!

# 5. 성공으로 반환
return True  # ← 거짓 성공!
```

**결과**:
- 노드는 기계에 할당되지 않음 (`machine=None`)
- 하지만 스케줄링 완료로 간주됨 (`success=True`)
- 자식 노드의 `parent_node_count` 감소 → Dependency 오염
- 자식 노드의 `earliest_start = max([inf, ...]) = inf` → 실행 불가

### A-4. WARNING 메시지 발생 원인

```
[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 32571_1300_4_M3_23312_T01639 제거
```

**발생 경로**:

```python
# DispatchPriorityStrategy.execute() (Line 580-599)
while result:
    base_date = result[0][1]
    window_result = [윈도우 내 노드들]

    # SetupMinimizedStrategy 호출
    used_ids = setup_strategy.execute(
        dag_manager, scheduler,
        window_result[0],  # 리더
        window_result[1:]  # 후보들
    )

    if used_ids:
        result = [item for item in result if item[0] not in used_ids]
    else:
        # ⭐ 무한루프 방지: 아무것도 스케줄링 안 되면 첫 노드 강제 제거
        print(f"[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 {result[0][0]} 제거")
        result = result[1:]
```

**왜 `used_ids`가 비었는가?**

```python
# SetupMinimizedStrategy.execute()
node = dag_manager.nodes[start_id]

# 1. 리더 스케줄링 시도
strategy = OptimalMachineStrategy()
success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
# success = True (버그 A), 하지만 실제로는 machine=None

if not success:  # success=True이므로 통과 안 됨
    return []

# 2. 리더가 성공했다고 가정하고 진행
ideal_machine_index = node.machine  # ← None!
# ...

# 3. ForcedMachineStrategy로 그룹 스케줄링
for same_chemical_id in same_chemical_queue:
    node = dag_manager.nodes[same_chemical_id]
    strategy = ForcedMachineStrategy(ideal_machine_index, ...)  # machine=None
    success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
    # force_assign_operation(machine_code=None, ...) 호출
    # → 당연히 실패
    # success = False

    if success:
        used_ids.append(same_chemical_id)
    else:
        remaining_operation_queue.append(same_chemical_id)

# 결과: used_ids = [start_id]만 (리더만, 그룹은 실패)
```

**하지만 다음 노드도 실패**:
- 리더의 Dependency가 업데이트되어 다음 노드의 `parent_node_count` 감소
- 하지만 `parent_node_end`에 `inf`가 추가됨
- 다음 노드의 `earliest_start = inf` → 스케줄 불가
- 무한루프 → WARNING 출력

---

## 버그 B: DOWNTIME delay 계산 KeyError

### B-1. 버그 발생 경로

#### Step 1: DOWNTIME 삽입

```python
# scheduler.py:allocate_machine_downtime() (328-350)
for idx, row in machine_rest.iterrows():
    machine_code = row["기계코드"]  # "M1"
    start_time = row["시작시간"]    # 452 (30분 단위)
    end_time = row["종료시간"]      # 460

    self.Machines[machine_code].force_Input(-1, "DOWNTIME 기계 사용 불가 시간", start_time, end_time)
```

**결과 상태**:
```python
Machines["M1"].assigned_task = [[-1, "DOWNTIME 기계 사용 불가 시간"]]
Machines["M1"].O_start = [452]
Machines["M1"].O_end = [460]
Machines["M1"].End_time = 460
```

#### Step 2: 실제 작업 할당 시도

```python
# scheduler.py:machine_earliest_start() (91-98)
target_machine_task = target_machine.assigned_task
# [[-1, "DOWNTIME 기계 사용 불가 시간"]]

if target_machine_task:  # True
    normal_delay = self.delay_processor.delay_calc_whole_process(
        target_machine_task[-1][1],  # "DOWNTIME 기계 사용 불가 시간"
        node_id,                      # "PROC_001"
        Selected_Machine              # "M1"
    )
```

#### Step 3: Delay 계산 시도

```python
# delay_dict.py:delay_calc_whole_process() (25-55)
def delay_calc_whole_process(self, item_id1, item_id2, machine_code):
    # item_id1 = "DOWNTIME 기계 사용 불가 시간"
    # item_id2 = "PROC_001"

    empty_dict = {
        "OPERATION_ORDER": 0,
        "OPERATION_CODE": "",
        "OPERATION_CLASSIFICATION": "",
        "FABRIC_WIDTH": 0,
        "CHEMICAL_LIST": (),
        "PRODUCTION_LENGTH": 0
        # ❌ "SELECTED_CHEMICAL" 키 없음!
    }

    values1 = self.opnode_dict.get(item_id1, empty_dict)
    # item_id1 = "DOWNTIME 기계 사용 불가 시간"
    # opnode_dict에 없음 → empty_dict 반환

    values2 = self.opnode_dict.get(item_id2, empty_dict)
    # item_id2 = "PROC_001"
    # opnode_dict에 있음 → 실제 값 반환

    input_key = self.calculate_delay(values1, values2, machine_code)
```

#### Step 4: KeyError 발생

```python
# delay_dict.py:calculate_delay() (169-214)
@staticmethod
def calculate_delay(earlier: list, later: list, machine_code: str) -> Tuple:
    # earlier = empty_dict (DOWNTIME)
    # later = 실제 작업 정보

    earlier_operation_type = earlier["OPERATION_CLASSIFICATION"]  # "" (OK)
    later_operation_type = later["OPERATION_CLASSIFICATION"]      # "DY" (OK)
    earlier_width = earlier["FABRIC_WIDTH"]                        # 0 (OK)
    later_width = later["FABRIC_WIDTH"]                            # 1524 (OK)

    # ⭐ 여기서 KeyError!
    earlier_chemical = earlier["SELECTED_CHEMICAL"]
    # KeyError: 'SELECTED_CHEMICAL'
```

### B-2. 빈 시간창에서도 발생

```python
# scheduler.py:machine_earliest_start() - 빈 시간창 탐색 (115-162)
for le_i in range(len(M_Tlen)):
    if M_Tlen[le_i] >= P_t and M_Tstart[le_i] >= last_O_end:
        # 앞 작업과의 delay
        if le_i != 0:
            earlier_delay = self.delay_processor.delay_calc_whole_process(
                target_machine_task[le_i-1][1],  # 이전 작업
                node_id,
                Selected_Machine
            )

        # 뒤 작업과의 delay
        later_delay = self.delay_processor.delay_calc_whole_process(
            node_id,
            target_machine_task[le_i][1],  # ← DOWNTIME일 수 있음!
            Selected_Machine
        )
        # ⬇️ KeyError 발생!
```

### B-3. 버그의 영향

**시나리오 A: 프로그램 크래시**
```python
KeyError: 'SELECTED_CHEMICAL'
  File "delay_dict.py", line 194, in calculate_delay
    earlier_chemical = earlier["SELECTED_CHEMICAL"]
```
→ 스케줄링 완전 중단

**시나리오 B: 예외 처리 시**
```python
# ForcedMachineStrategy.assign() (670-697)
try:
    flag, start_time, processing_time = scheduler.force_assign_operation(...)
except Exception as e:
    return AssignmentResult(success=False, ...)
```
→ delay 계산 실패 → 기계 할당 실패 → `success=False` 반환

**시나리오 C: delay=0 처리 시**
```python
# delay_processor에 try-except 추가되었다면:
try:
    earlier_chemical = earlier["SELECTED_CHEMICAL"]
except KeyError:
    earlier_chemical = None

# same_chemical = (None == None) = True
# → delay가 0으로 계산됨
```
→ DOWNTIME 직전/직후에 작업 배치 → 시간 중첩 위험!

---

## 두 버그의 상호작용

### 시나리오 1: 버그 B가 먼저 발생

```
1. DOWNTIME 삽입
   ↓
2. 작업 X를 M1에 할당 시도
   ↓
3. machine_earliest_start() 호출
   ↓
4. delay_calc_whole_process("DOWNTIME", "PROC_001", "M1") 호출
   ↓
5. KeyError 발생!
   ↓
6a. 예외 처리 없음 → 프로그램 크래시 (END)

6b. 예외 처리 있음 → assign_operation() 실패
   ↓
7. assign_operation()이 (None, inf, inf) 반환
   ↓
8. OptimalMachineStrategy가 success=True 반환 (버그 A)
   ↓
9. 유령 노드 생성
```

### 시나리오 2: 버그 A가 주된 원인

```
1. machine_rest가 모든 기계를 장시간 차단
   ↓
2. assign_operation()이 기계 찾지 못함
   (KeyError 없이도 ideal_machine_code=None)
   ↓
3. OptimalMachineStrategy가 success=True 반환 (버그 A)
   ↓
4. 유령 노드 생성
   ↓
5. Dependency 오염
   ↓
6. 후속 노드들도 earliest_start=inf
   ↓
7. 전체 스케줄링 실패
```

### 시나리오 3: 두 버그 모두 작용

```
1. DOWNTIME 삽입 (짧은 시간대)
   ↓
2. 첫 작업: delay_calc KeyError → 실패
   ↓
3. 버그 A로 success=True → 유령 노드
   ↓
4. Dependency 업데이트 → 자식 earliest_start=inf
   ↓
5. 자식 작업: earliest_start=inf이지만 시도
   ↓
6. delay_calc 다시 KeyError → 실패
   ↓
7. 버그 A로 또 success=True → 또 유령 노드
   ↓
8. 연쇄 실패
```

---

## 추가 발견 문제점

### 문제 1: fillna inplace 미적용

**위치**: `scheduler.py:338`

```python
# 현재 코드:
machine_rest[config.columns.MACHINE_REST_START].fillna(base_date)
```

**문제**:
- 반환값을 재할당하지 않아 실제 DataFrame 수정 안 됨
- 시작시간이 None인 행은 그대로 유지

**영향**:
```python
# machine_rest:
  기계코드  시작시간  종료시간
  M1      None    2024-06-10 14:00

# fillna 호출 후에도:
  시작시간 = None

# pd.to_datetime(None) → NaT
# (NaT - base_date).dt.total_seconds() → NaN
# NaN // 1800 → NaN
# .astype(int) → 0 or 에러

# 결과: DOWNTIME이 0부터 시작 → 스케줄 전체 차단!
```

### 문제 2: force_Input() 정렬 미수행

**위치**: `machine.py:force_Input()` (143-153)

```python
def force_Input(self, depth, node_id, start_time, end_time):
    self.assigned_task.append([depth, node_id])
    self.O_start.append(start_time)
    self.O_end.append(end_time)
    self.End_time = max(self.End_time, end_time)
    # ❌ sort() 없음!
```

**영향**:
```python
# 1. 작업 A (100~200)
O_start = [100], O_end = [200]

# 2. DOWNTIME (50~80) - 더 이른 시간!
force_Input(-1, "DOWNTIME", 50, 80)
O_start = [100, 50]  # ❌ 미정렬
O_end = [200, 80]    # ❌ 미정렬

# 3. Empty_time_window():
time_window_start = O_end[:-1] = [200]
time_window_end = O_start[1:] = [50]
len_time_window = [-150]  # ❌ 음수!
```

### 문제 3: DOWNTIME 중첩 검증 미수행

```python
# 작업 A: 100~300
# DOWNTIME: 200~250 삽입
# → 중첩됨!
```

---

## 종합 해결 방안

### 긴급 패치 (즉시 적용)

#### 1. 버그 A 수정

```python
# scheduling_core.py:OptimalMachineStrategy.assign()
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
        return AssignmentResult(success=False, ...)
```

#### 2. 버그 B 수정 (최소)

```python
# delay_dict.py:delay_calc_whole_process()
empty_dict = {
    "OPERATION_ORDER": 0,
    "OPERATION_CODE": "",
    "OPERATION_CLASSIFICATION": "",
    "FABRIC_WIDTH": 0,
    "CHEMICAL_LIST": (),
    "PRODUCTION_LENGTH": 0,
    "SELECTED_CHEMICAL": None  # ← 추가
}
```

#### 3. fillna 수정

```python
# scheduler.py:338
machine_rest[config.columns.MACHINE_REST_START] = \
    machine_rest[config.columns.MACHINE_REST_START].fillna(base_date)
```

**예상 효과**:
- KeyError 해결 (프로그램 크래시 방지)
- 유령 노드 생성 방지
- Dependency 오염 방지
- WARNING 메시지 감소

---

### 단기 개선 (1주 이내)

#### 4. DOWNTIME 감지 로직

```python
# scheduler.py:machine_earliest_start()
if target_machine_task:
    last_task = target_machine_task[-1]
    last_task_depth = last_task[0]
    last_task_id = last_task[1]

    # DOWNTIME 감지
    if last_task_depth == -1 or "DOWNTIME" in str(last_task_id):
        normal_delay = 0
    else:
        normal_delay = self.delay_processor.delay_calc_whole_process(...)
else:
    normal_delay = 0
```

**적용 위치**: 3곳 (91행, 124행, 145행)

#### 5. force_Input() 정렬 추가

```python
# machine.py:force_Input()
def force_Input(self, depth, node_id, start_time, end_time):
    self.assigned_task.append([depth, node_id])
    self.O_start.append(start_time)
    self.O_end.append(end_time)

    # 정렬 추가
    sorted_indices = sorted(range(len(self.O_start)),
                           key=lambda i: self.O_start[i])
    self.assigned_task = [self.assigned_task[i] for i in sorted_indices]
    self.O_start = [self.O_start[i] for i in sorted_indices]
    self.O_end = [self.O_end[i] for i in sorted_indices]

    self.End_time = max(self.End_time, end_time)
```

---

### 중기 개선 (1개월 이내)

#### 6. DOWNTIME 별도 관리 (근본 해결)

```python
class Machine_Time_window:
    def __init__(self, ...):
        self.assigned_task = []      # 일반 작업만
        self.downtime_periods = []   # DOWNTIME 전용
        self.O_start = []
        self.O_end = []

    def add_downtime(self, start_time, end_time):
        """DOWNTIME 전용 메서드"""
        self.downtime_periods.append((start_time, end_time))
        self.downtime_periods.sort()

    def is_time_available(self, start, end):
        """시간대 사용 가능 여부 (DOWNTIME 체크)"""
        for dt_start, dt_end in self.downtime_periods:
            if not (end <= dt_start or start >= dt_end):
                return False
        return True
```

---

## 테스트 체크리스트

### 버그 A 수정 검증

- [ ] machine_rest 없이도 작동
- [ ] `machine_idx=None` 시 `success=False` 반환
- [ ] 유령 노드 생성 안 됨
- [ ] Dependency 올바르게 유지
- [ ] WARNING 메시지 감소

### 버그 B 수정 검증

- [ ] KeyError 발생하지 않음
- [ ] DOWNTIME과의 delay=0 처리
- [ ] 빈 시간창 삽입 시 에러 없음
- [ ] DOWNTIME 시간대 침범 안 함

### 통합 테스트

- [ ] machine_rest 비어있을 때 정상 작동
- [ ] machine_rest 1개 있을 때 정상 작동
- [ ] machine_rest 여러 개 있을 때 정렬 정상
- [ ] 짧은 DOWNTIME 시 작업 할당 정상
- [ ] 긴 DOWNTIME 시 작업이 이후로 밀림
- [ ] 모든 노드 스케줄링 완료

---

## 결론

### 핵심 문제

**2개의 독립적 버그가 상호작용하여 시스템 마비**:

1. **버그 A (success 판정 오류)**:
   - `machine_idx=None`일 때도 `success=True` 반환
   - 유령 노드 생성 → Dependency 오염
   - machine_rest 없어도 발생 가능 (다른 원인으로 기계 없을 때)

2. **버그 B (KeyError)**:
   - DOWNTIME과 delay 계산 시 `SELECTED_CHEMICAL` 키 누락
   - 프로그램 크래시 or 잘못된 delay=0
   - machine_rest 있어야 발생

### 권장 조치

**우선순위 1 (긴급)**:
- 버그 A 수정 (success 판정)
- 버그 B 수정 (empty_dict에 키 추가)
- fillna inplace 수정

**우선순위 2 (단기)**:
- DOWNTIME 감지 로직
- force_Input() 정렬

**우선순위 3 (중기)**:
- DOWNTIME 별도 관리 구조

### 예상 효과

**긴급 패치 적용 후**:
- ✅ 프로그램 크래시 방지
- ✅ 유령 노드 생성 차단
- ✅ machine_rest 기본 기능 작동
- ⚠️ 여전히 논리적 개선 필요

**전체 개선 완료 후**:
- ✅ 안정적인 DOWNTIME 처리
- ✅ 명확한 책임 분리
- ✅ 향후 확장 용이
- ✅ 테스트 가능성 향상

---

**작성일**: 2025-01-17
**분석자**: Claude (Sonnet 4.5)
**영향 범위**: scheduler 모듈 전체, 특히 machine_rest 처리 및 기계 할당 로직
