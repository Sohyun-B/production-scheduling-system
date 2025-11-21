# reallocating_by_user Aging 처리 문제 분석 및 해결방안

## 문제 상황

### 현재 구조
`reallocating_by_user` 로직은 사용자가 지정한 기계별 큐 순서대로 작업을 강제 재스케줄링하는 기능입니다.

**호출 흐름:**
```
reallocating_schedule_by_user()
  → UserRescheduleStrategy.execute()
  → ForcedMachineStrategy.assign()
  → scheduler.force_assign_operation()
```

### 핵심 문제

**`force_assign_operation` 메서드가 aging 노드를 처리하지 못합니다.**

#### 1. Aging 체크 로직 부재

**일반 할당 (`assign_operation`):**
```python
def assign_operation(self, node_earliest_start, node_id, depth):
    machine_info = self.machine_dict.get(node_id)

    # ★ Aging 노드 감지 및 처리
    is_aging = set(machine_info.keys()) == {'AGING'}
    if is_aging:
        aging_time = machine_info['AGING']
        self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
        return 'AGING', node_earliest_start, aging_time

    # 일반 기계 할당 로직...
```

**강제 할당 (`force_assign_operation`):**
```python
def force_assign_operation(self, machine_code, node_earliest_start, node_id, depth, machine_window_flag=False):
    machine_info = self.machine_dict.get(node_id)

    # ❌ Aging 체크 없음!
    machine_processing_time = machine_info.get(machine_code, 9999)

    if machine_processing_time == 9999:
        return False, None, None  # 실패

    # 바로 기계에 할당
    self.Machines[machine_code]._Input(depth, node_id, earliest_start, processing_time)
```

#### 2. 발생 가능한 문제들

1. **Aging 노드 스케줄링 실패**
   - Aging 노드의 `machine_info`는 `{'AGING': 300}` 형태
   - 사용자가 지정한 `machine_code` (예: 'A2020')로 조회하면 → `9999` 반환
   - 결과: `False` 반환하며 스케줄링 실패

2. **무한 루프 가능성**
   - `UserRescheduleStrategy.execute()`는 `progress` 플래그로 진행 여부 확인
   - Aging 노드가 계속 실패하면 큐에서 제거되지 않음
   - 잠재적 무한 루프 위험

3. **스케줄링 불완전**
   - Aging이 필요한 공정이 건너뛰어짐
   - 최종 결과에 일부 작업이 누락됨

## 해결 방안

### 방안 1: `force_assign_operation`에 Aging 체크 추가 (권장)

**장점:**
- 기존 구조 유지
- 최소한의 코드 변경
- 모든 강제 할당 케이스에서 aging 처리 보장

**구현:**

```python
def force_assign_operation(self, machine_code, node_earliest_start, node_id, depth, machine_window_flag=False):
    """
    특정 기계에 강제 할당 (코드 기반)
    """
    machine_info = self.machine_dict.get(node_id)

    if not machine_info:
        print(f"[오류] 노드 {node_id}의 machine_info 없음")
        return False, None, None

    # ★ Aging 노드 감지 및 처리 추가
    is_aging = set(machine_info.keys()) == {'AGING'}
    if is_aging:
        aging_time = machine_info['AGING']
        self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
        # Aging은 성공으로 간주 (특정 기계 할당은 무시)
        return True, node_earliest_start, aging_time

    # 기존 로직...
    machine_processing_time = machine_info.get(machine_code, 9999)

    if machine_processing_time == 9999:
        print(f"[경고] 기계 {machine_code}에서 노드 {node_id} 처리 불가 (9999)")
        return False, None, None

    # 최적 시작시간 계산
    if machine_window_flag:
        earliest_start, _, processing_time = self.machine_earliest_start(
            machine_info, machine_code, node_earliest_start, node_id, machine_window_flag=True
        )[0:3]
    else:
        earliest_start, _, processing_time = self.machine_earliest_start(
            machine_info, machine_code, node_earliest_start, node_id
        )[0:3]

    self.Machines[machine_code]._Input(depth, node_id, earliest_start, processing_time)

    return True, earliest_start, processing_time
```

**파일 위치:** `python_engine/src/scheduler/scheduler.py:235`

---

### 방안 2: `UserRescheduleStrategy`에서 Aging 노드 필터링

**장점:**
- 상위 레벨에서 처리
- Aging 노드를 사용자 재스케줄링 대상에서 제외

**단점:**
- 사용자가 의도적으로 aging 노드를 재배치하고 싶을 경우 대응 불가
- 로직이 분산됨

**구현:**

```python
class UserRescheduleStrategy(HighLevelSchedulingStrategy):
    """사용자 재스케줄링 전략"""

    def execute(self, dag_manager, scheduler, machine_queues):
        progress = True
        while progress:
            progress = False

            for machine_code, queue in machine_queues.items():
                if not queue:
                    continue

                node_id = queue[0]
                node = dag_manager.nodes[node_id]

                # ★ Aging 노드 체크
                machine_info = scheduler.machine_dict.get(node_id)
                is_aging = machine_info and set(machine_info.keys()) == {'AGING'}

                if is_aging:
                    # Aging 노드는 일반 할당 로직 사용
                    aging_time = machine_info['AGING']
                    earliest_start = SchedulingCore.calculate_earliest_start(node, dag_manager)
                    scheduler.aging_machine._Input(node.depth, node_id, earliest_start, aging_time)
                    queue.pop(0)
                    progress = True
                    continue

                # 강제 기계 할당 전략 사용 (일반 노드)
                strategy = ForcedMachineStrategy(machine_code, use_machine_window=True)
                success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

                if success:
                    queue.pop(0)
                    progress = True

        return dag_manager.to_dataframe()
```

**파일 위치:** `python_engine/src/scheduler/scheduling_core.py:604`

---

### 방안 3: 하이브리드 - Aging 노드는 자동 할당

**장점:**
- 가장 안전한 방식
- Aging 노드는 시스템이 자동으로 최적 처리
- 일반 노드는 사용자 지정대로 처리

**단점:**
- 사용자에게 aging 노드가 자동 처리됨을 명확히 안내 필요

**구현:**

방안 1 + 로깅 강화:

```python
def force_assign_operation(self, machine_code, node_earliest_start, node_id, depth, machine_window_flag=False):
    machine_info = self.machine_dict.get(node_id)

    if not machine_info:
        print(f"[오류] 노드 {node_id}의 machine_info 없음")
        return False, None, None

    # Aging 노드 감지 및 자동 처리
    is_aging = set(machine_info.keys()) == {'AGING'}
    if is_aging:
        aging_time = machine_info['AGING']
        self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
        print(f"[INFO] Aging 노드 {node_id}는 자동으로 AGING 기계에 할당됩니다 (사용자 지정 기계 {machine_code} 무시)")
        return True, node_earliest_start, aging_time

    # 기존 로직...
```

---

## 권장 해결 방안

### **방안 1 채택 권장**

**이유:**
1. **안정성**: 모든 `force_assign_operation` 호출에서 aging 처리 보장
2. **일관성**: `assign_operation`과 동일한 로직 적용
3. **최소 변경**: 한 곳만 수정하면 됨
4. **확장성**: 향후 다른 강제 할당 케이스에서도 동작

### 구현 우선순위

1. **1단계**: `force_assign_operation`에 aging 체크 로직 추가
2. **2단계**: 단위 테스트 작성
   - Aging 노드가 포함된 `machine_queues` 테스트
   - 일반 노드와 혼합된 케이스 테스트
3. **3단계**: 통합 테스트
   - 실제 데이터로 `reallocating_by_user` 실행
   - Aging 노드 스케줄링 결과 확인

### 테스트 케이스

```python
# 테스트 케이스 1: Aging 노드만 있는 큐
machine_queues = {
    'A2020': ['aging_node_1', 'aging_node_2']
}

# 테스트 케이스 2: 일반 노드와 Aging 노드 혼합
machine_queues = {
    'A2020': ['normal_node_1', 'aging_node_1', 'normal_node_2']
}

# 테스트 케이스 3: 여러 기계에 분산
machine_queues = {
    'A2020': ['aging_node_1', 'normal_node_1'],
    'C2010': ['normal_node_2', 'aging_node_2']
}
```

---

## 추가 고려사항

### 1. 사용자 인터페이스 개선

Aging 노드를 사용자가 재스케줄링하려 할 때 경고 메시지:

```
[WARNING] 노드 {node_id}는 AGING 공정입니다.
사용자 지정 기계 {machine_code} 대신 자동으로 AGING에 할당됩니다.
```

### 2. 문서화

사용자 매뉴얼에 다음 내용 추가:
- Aging 노드는 사용자 재스케줄링 대상에서 제외됨
- Aging 공정은 시스템이 자동으로 최적 처리
- 재스케줄링 결과에서 aging 노드 확인 방법

### 3. 로깅 강화

디버깅을 위한 상세 로그:

```python
if is_aging:
    print(f"[AGING] 노드 {node_id}: 사용자 지정 기계 {machine_code} → AGING 자동 할당")
    print(f"  - Aging 시간: {aging_time}")
    print(f"  - 시작 시간: {node_earliest_start}")
```

---

## 관련 파일

- `python_engine/src/scheduler/scheduler.py:235` - `force_assign_operation` 메서드
- `python_engine/src/scheduler/scheduling_core.py:604` - `UserRescheduleStrategy` 클래스
- `python_engine/src/scheduler/dispatch_rules.py:88` - `reallocating_schedule_by_user` 함수

---

## 변경 이력

| 날짜 | 작성자 | 내용 |
|------|--------|------|
| 2025-11-18 | Claude | 초안 작성 - Aging 처리 문제 분석 및 해결방안 제시 |
