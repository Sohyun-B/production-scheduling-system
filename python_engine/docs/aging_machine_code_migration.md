# AGING machine_code 마이그레이션 분석: -1 → 'AGING'

## 목차
1. [현재 상태 분석](#현재-상태-분석)
2. [변경 범위](#변경-범위)
3. [영향받는 파일 및 코드](#영향받는-파일-및-코드)
4. [잠재적 오류 시나리오](#잠재적-오류-시나리오)
5. [마이그레이션 순서](#마이그레이션-순서)
6. [테스트 체크리스트](#테스트-체크리스트)

---

## 현재 상태 분석

### 1.1 AGING 시스템 개요

**비즈니스 로직**:
- Aging은 염색 후 건조/숙성 공정 (실제 기계 없이 시간만 소요)
- 부모 공정 완료 시 자동으로 스케줄링됨
- 작업들이 시간대 중첩 가능 (allow_overlapping=True)

**현재 구조**:
```python
# 1. machine_dict에 -1 키로 저장
machine_dict[aging_node_id] = {-1: aging_time}
# 예: {"N00001_AGING": {-1: 48}}

# 2. Scheduler에 별도 aging_machine 속성
self.aging_machine = Machine_Time_window(-1, allow_overlapping=True)

# 3. Aging 감지 패턴
is_aging = set(machine_info.keys()) == {-1}

# 4. 출력 시 'AGING' 문자열 사용 (scheduler.py:308)
config.columns.MACHINE_CODE: 'AGING'
```

**불일치 문제**:
- **내부**: -1 (정수)
- **출력**: 'AGING' (문자열)
- **목표**: 전체를 'AGING' 문자열로 통일

---

## 변경 범위

### 2.1 핵심 변경사항

| 항목 | 현재 (Before) | 변경 후 (After) |
|------|--------------|----------------|
| **machine_dict 키** | `{-1: time}` | `{'AGING': time}` |
| **Aging 감지 조건** | `set(keys()) == {-1}` | `set(keys()) == {'AGING'}` |
| **Machine 생성자** | `Machine_Time_window(-1, ...)` | `Machine_Time_window('AGING', ...)` |
| **get_machine() 조건** | `if machine_code == -1:` | `if machine_code == 'AGING':` |
| **assign_operation 반환** | `return -1, start, time` | `return 'AGING', start, time` |
| **AssignmentResult** | `machine_code=-1` | `machine_code='AGING'` |

---

## 영향받는 파일 및 코드

### 3.1 우선순위 높음 (필수 수정)

#### File 1: [node_dict.py:102](../src/dag_management/node_dict.py#L102)

**현재**:
```python
machine_dict[aging_node_id] = {-1: int(aging_time)}
```

**변경 후**:
```python
machine_dict[aging_node_id] = {'AGING': int(aging_time)}
```

**영향**: machine_dict 생성의 시작점 - 모든 하위 로직에 영향

---

#### File 2: [dag_dataframe.py:159](../src/dag_management/dag_dataframe.py#L159)

**현재**:
```python
def _is_aging_node(node_id, machine_dict):
    if node_id not in machine_dict:
        return False
    return set(machine_dict[node_id].keys()) == {-1}
```

**변경 후**:
```python
def _is_aging_node(node_id, machine_dict):
    if node_id not in machine_dict:
        return False
    return set(machine_dict[node_id].keys()) == {'AGING'}
```

**영향**: Aging 노드 감지 함수 - DAG 생성 시 사용

---

#### File 3: [scheduler.py](../src/scheduler/scheduler.py)

**위치 1**: Line 42 - Machine 생성
```python
# 현재
self.aging_machine = Machine_Time_window(-1, allow_overlapping=True)

# 변경 후
self.aging_machine = Machine_Time_window('AGING', allow_overlapping=True)
```

**위치 2**: Line 57-59 - get_machine()
```python
# 현재
if machine_code == -1:
    return self.aging_machine
return self.Machines[machine_code]

# 변경 후
if machine_code == 'AGING':
    return self.aging_machine
return self.Machines[machine_code]
```

**위치 3**: Line 196-201 - assign_operation()
```python
# 현재
is_aging = set(machine_info.keys()) == {-1}
if is_aging:
    aging_time = machine_info[-1]
    self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
    return -1, node_earliest_start, aging_time

# 변경 후
is_aging = set(machine_info.keys()) == {'AGING'}
if is_aging:
    aging_time = machine_info['AGING']
    self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
    return 'AGING', node_earliest_start, aging_time
```

**영향**: 스케줄링 핵심 로직

---

#### File 4: [scheduling_core.py](../src/scheduler/scheduling_core.py)

**위치 1**: Line 119 - schedule_ready_aging_children()
```python
# 현재
is_aging = machine_info and set(machine_info.keys()) == {-1}

# 변경 후
is_aging = machine_info and set(machine_info.keys()) == {'AGING'}
```

**위치 2**: Line 154 - schedule_single_node()
```python
# 현재
is_aging = machine_info and set(machine_info.keys()) == {-1}

# 변경 후
is_aging = machine_info and set(machine_info.keys()) == {'AGING'}
```

**위치 3**: Line 257 - AgingMachineStrategy.assign()
```python
# 현재
if not machine_info or set(machine_info.keys()) != {-1}:
    raise ValueError(f"Node {node.id} is not an aging node")

# 변경 후
if not machine_info or set(machine_info.keys()) != {'AGING'}:
    raise ValueError(f"Node {node.id} is not an aging node")
```

**위치 4**: Line 260-276 - AgingMachineStrategy.assign() 계속
```python
# 현재
aging_time = machine_info[-1]
...
return AssignmentResult(
    success=True,
    machine_code=-1,
    start_time=start_time,
    processing_time=processing_time
)

# 변경 후
aging_time = machine_info['AGING']
...
return AssignmentResult(
    success=True,
    machine_code='AGING',
    start_time=start_time,
    processing_time=processing_time
)
```

**위치 5**: Line 545 - DispatchPriorityStrategy.execute()
```python
# 현재
is_aging = machine_info and set(machine_info.keys()) == {-1}

# 변경 후
is_aging = machine_info and set(machine_info.keys()) == {'AGING'}
```

**영향**: 스케줄링 전략 전반

---

#### File 5: [__init__.py (dag_management)](../src/dag_management/__init__.py#L69)

**현재**:
```python
for aging_node_id, aging_time in aging_nodes_dict.items():
    machine_dict[aging_node_id] = {-1: int(aging_time)}
```

**변경 후**:
```python
for aging_node_id, aging_time in aging_nodes_dict.items():
    machine_dict[aging_node_id] = {'AGING': int(aging_time)}
```

**영향**: DAG 재빌드 시 사용

---

#### File 6: [merge_processor.py:77](../src/results/merge_processor.py#L77)

**현재**:
```python
machine_info = scheduler.machine_dict.get(node_id)
is_aging = machine_info and set(machine_info.keys()) == {-1}
```

**변경 후**:
```python
machine_info = scheduler.machine_dict.get(node_id)
is_aging = machine_info and set(machine_info.keys()) == {'AGING'}
```

**영향**: 결과 병합 처리

---

### 3.2 우선순위 중간 (간접 영향)

#### File 7: [machine.py](../src/scheduler/machine.py)

**현재 코드 확인 필요**:
```python
class Machine_Time_window:
    def __init__(self, machine_index, allow_overlapping=False):
        self.machine_index = machine_index  # -1 또는 실제 인덱스
        ...
```

**잠재적 이슈**:
- `machine_index` 변수명이 여전히 사용 중인지 확인
- -1과 문자열 'AGING'의 타입 차이로 인한 오류 가능성

**권장 수정**:
```python
class Machine_Time_window:
    def __init__(self, machine_code, allow_overlapping=False):
        self.machine_code = machine_code  # 'AGING' 또는 실제 코드
        ...
```

---

#### File 8: [machine_info_builder.py](../src/results/machine_info_builder.py)

**현재 동작** (Line 40-44):
```python
machine_mapping = {
    code: self.machine_mapper.code_to_name(code)
    for code in self.machine_mapper.get_all_codes()
}
df[config.columns.MACHINE_NAME] = df[config.columns.MACHINE_CODE].map(machine_mapping)
```

**잠재적 이슈**:
- 'AGING'이 `machine_mapper.get_all_codes()`에 포함되지 않을 수 있음
- `machine_mapping['AGING']` → KeyError 또는 NaN

**권장 수정**:
```python
machine_mapping = {
    code: self.machine_mapper.code_to_name(code)
    for code in self.machine_mapper.get_all_codes()
}
# AGING 특수 처리
machine_mapping['AGING'] = 'AGING'  # 또는 '숙성기' 등

df[config.columns.MACHINE_NAME] = df[config.columns.MACHINE_CODE].map(machine_mapping)
```

---

### 3.3 우선순위 낮음 (문서/주석)

#### File 9: [claude.md](../src/scheduler/claude.md)

여러 위치에서 `-1` 언급:
- Line 338: `if machine_info == {-1: 시간}:`
- Line 340: `return -1, node_earliest_start, 시간`
- 기타 예시 코드

**변경**: 모든 `-1`을 `'AGING'`으로 업데이트

---

## 잠재적 오류 시나리오

### 4.1 타입 불일치 오류 (TypeError)

**시나리오**:
```python
# 코드 A에서 -1 사용
machine_code = -1

# 코드 B에서 'AGING' 사용
if machine_code == 'AGING':  # False! (정수 vs 문자열)
    ...
```

**발생 위치**:
- ✅ **완전 마이그레이션 안 됨**: 일부 파일만 수정하고 다른 파일은 그대로인 경우
- ✅ **외부 의존성**: 다른 모듈이나 설정 파일에서 -1을 참조하는 경우

**방지책**:
- 한 번에 모든 파일 수정 (원자적 변경)
- 단위 테스트로 검증

---

### 4.2 딕셔너리 KeyError

**시나리오 1**: machine_info 조회
```python
# 현재
aging_time = machine_info[-1]  # -1이 키

# 변경 후 (기존 코드 남아있으면)
aging_time = machine_info[-1]  # KeyError! (키가 'AGING'임)
```

**발생 위치**:
- [scheduler.py:199](../src/scheduler/scheduler.py#L199)
- [scheduling_core.py:260](../src/scheduler/scheduling_core.py#L260)

**방지책**:
- 모든 `machine_info[-1]`을 `machine_info['AGING']`으로 변경
- grep으로 `[-1]` 패턴 검색

---

**시나리오 2**: machine_mapper 누락
```python
# machine_info_builder.py
machine_mapping = {...}  # 'AGING' 없음
df[MACHINE_NAME] = df[MACHINE_CODE].map(machine_mapping)
# 결과: AGING 행의 MACHINE_NAME이 NaN
```

**방지책**:
- `machine_mapping`에 'AGING' 명시적 추가
- fillna() 또는 기본값 처리

---

### 4.3 조건문 실패

**시나리오**:
```python
# 일부만 수정된 경우
# File A
is_aging = set(machine_info.keys()) == {'AGING'}  # True

# File B (수정 안 됨)
if machine_code == -1:  # False! ('AGING' != -1)
    return self.aging_machine
else:
    return self.Machines[machine_code]  # KeyError! ('AGING' not in Machines)
```

**발생 위치**:
- [scheduler.py:57](../src/scheduler/scheduler.py#L57) get_machine()

**방지책**:
- 모든 조건문 동시 수정
- E2E 테스트로 전체 플로우 검증

---

### 4.4 Results 모듈 오류

**시나리오**: machine_mapper.code_to_name('AGING') 실패
```python
# machine_info_builder.py
for code in df[MACHINE_CODE].unique():
    name = self.machine_mapper.code_to_name(code)  # 'AGING'에 대해 KeyError
```

**발생 위치**:
- [machine_info_builder.py:40-44](../src/results/machine_info_builder.py#L40-L44)

**방지책**:
- try-except 추가
- 'AGING' 특수 케이스 처리

---

### 4.5 Excel 출력 오류

**시나리오**: MACHINE_NAME이 NaN
```
MACHINE_CODE | MACHINE_NAME | WORK_START_TIME
-------------|--------------|----------------
A2020        | 염색기 1호    | 2024-06-10 10:00
AGING        | NaN          | 2024-06-10 12:00  ← 문제!
C2010        | 날염기 2호    | 2024-06-10 14:00
```

**발생 원인**:
- machine_mapper에 'AGING' 매핑 없음

**사용자 영향**:
- 결과 파일이 불완전함
- Aging 작업 식별 불가

**방지책**:
- machine_mapping에 'AGING' 추가
- 출력 검증 테스트

---

### 4.6 delay_dict 조회 오류

**시나리오**: DOWNTIME과 유사하게, AGING도 delay 계산 시 문제 가능

```python
# delay_dict.py:25-56
def delay_calc_whole_process(self, item_id1, item_id2, machine_code):
    # machine_code = 'AGING'

    if machine_code not in self.machine_code_list:  # 'AGING'이 리스트에 없으면
        return 0  # delay 0 반환
```

**잠재적 문제**:
- `machine_code_list`가 실제 기계 코드만 포함 (A2020, C2010, ...)
- 'AGING'은 포함되지 않을 수 있음
- 하지만 **Aging은 교체시간 개념이 없으므로 0이 정상**

**검증 필요**:
- Aging 작업 전후로 일반 작업이 있을 때 delay 계산 확인
- 현재 로직이 의도한 대로 작동하는지 검증

---

### 4.7 Scheduler.Machines 딕셔너리 접근 오류

**시나리오**:
```python
# scheduler.py:224 - assign_operation()
if ideal_machine_code is not None:
    self.Machines[ideal_machine_code]._Input(...)  # ideal_machine_code='AGING'인 경우
    # KeyError! (Machines에는 'AGING' 없음, aging_machine은 별도 속성)
```

**현재 안전 장치**:
- Aging은 assign_operation() 초반에 감지되어 early return
- Line 196-201에서 처리됨

**하지만 주의**:
- early return 조건이 변경되면 오류 가능
- 방어적 코드 추가 검토

---

## 마이그레이션 순서

### 5.1 Phase 1: 데이터 생성 수정 (machine_dict)

**순서**:
1. [node_dict.py:102](../src/dag_management/node_dict.py#L102)
   ```python
   machine_dict[aging_node_id] = {'AGING': int(aging_time)}
   ```

2. [__init__.py:69](../src/dag_management/__init__.py#L69)
   ```python
   machine_dict[aging_node_id] = {'AGING': int(aging_time)}
   ```

**검증**:
```python
# 테스트 코드
assert machine_dict['N00001_AGING'] == {'AGING': 48}
```

---

### 5.2 Phase 2: Aging 감지 로직 수정

**순서**:
3. [dag_dataframe.py:159](../src/dag_management/dag_dataframe.py#L159)
4. [scheduler.py:197](../src/scheduler/scheduler.py#L197)
5. [scheduling_core.py:119, 154, 257, 545](../src/scheduler/scheduling_core.py)
6. [merge_processor.py:77](../src/results/merge_processor.py#L77)

**패턴 변경**:
```python
# 모든 위치에서
set(machine_info.keys()) == {-1}  # Before
→
set(machine_info.keys()) == {'AGING'}  # After
```

**검증**:
```python
# 테스트 코드
is_aging = set({'AGING': 48}.keys()) == {'AGING'}
assert is_aging == True
```

---

### 5.3 Phase 3: machine_code 값 수정

**순서**:
7. [scheduler.py:42](../src/scheduler/scheduler.py#L42) - Machine 생성
8. [scheduler.py:57](../src/scheduler/scheduler.py#L57) - get_machine()
9. [scheduler.py:199-201](../src/scheduler/scheduler.py#L199-L201) - assign_operation()
10. [scheduling_core.py:260, 273](../src/scheduler/scheduling_core.py) - AgingMachineStrategy

**패턴 변경**:
```python
# 값 변경
-1  # Before
→
'AGING'  # After

# 조건문 변경
if machine_code == -1:  # Before
→
if machine_code == 'AGING':  # After

# 딕셔너리 키 변경
machine_info[-1]  # Before
→
machine_info['AGING']  # After
```

---

### 5.4 Phase 4: Results 모듈 수정

**순서**:
11. [machine_info_builder.py:40-44](../src/results/machine_info_builder.py#L40-L44)

**추가 코드**:
```python
# 기존 매핑 생성
machine_mapping = {
    code: self.machine_mapper.code_to_name(code)
    for code in self.machine_mapper.get_all_codes()
}

# ⭐ AGING 특수 처리 추가
if 'AGING' not in machine_mapping:
    machine_mapping['AGING'] = 'AGING'  # 또는 'Aging 공정', '숙성', 등

df[config.columns.MACHINE_NAME] = df[config.columns.MACHINE_CODE].map(machine_mapping)
```

---

### 5.5 Phase 5: 문서 업데이트

**순서**:
12. [claude.md](../src/scheduler/claude.md) - 모든 `-1` 언급 변경

**검색 패턴**:
```bash
grep -n "\-1" claude.md
# 모든 결과를 'AGING'으로 변경
```

---

### 5.6 Phase 6: Machine 클래스 리팩토링 (선택)

**순서**:
13. [machine.py](../src/scheduler/machine.py) - machine_index → machine_code

**변경**:
```python
# Before
class Machine_Time_window:
    def __init__(self, machine_index, allow_overlapping=False):
        self.machine_index = machine_index

# After
class Machine_Time_window:
    def __init__(self, machine_code, allow_overlapping=False):
        self.machine_code = machine_code
```

**영향**:
- 모든 `self.machine_index` 참조를 `self.machine_code`로 변경
- 하지만 현재 코드에서 `machine_index` 속성이 실제로 사용되는지 확인 필요

---

## 테스트 체크리스트

### 6.1 단위 테스트

#### Test 1: machine_dict 생성
```python
def test_aging_machine_dict():
    # Aging 노드 추가
    aging_nodes_dict = {'N00001_AGING': 48}
    machine_dict = {}

    for aging_node_id, aging_time in aging_nodes_dict.items():
        machine_dict[aging_node_id] = {'AGING': int(aging_time)}

    # 검증
    assert machine_dict['N00001_AGING'] == {'AGING': 48}
    assert set(machine_dict['N00001_AGING'].keys()) == {'AGING'}
```

#### Test 2: Aging 감지
```python
def test_is_aging_detection():
    machine_info_aging = {'AGING': 48}
    machine_info_normal = {'A2020': 120, 'C2010': 150}

    # Aging 노드
    is_aging = set(machine_info_aging.keys()) == {'AGING'}
    assert is_aging == True

    # 일반 노드
    is_aging = set(machine_info_normal.keys()) == {'AGING'}
    assert is_aging == False
```

#### Test 3: get_machine()
```python
def test_get_machine_aging():
    scheduler = Scheduler(...)

    # AGING 조회
    aging_machine = scheduler.get_machine('AGING')
    assert aging_machine is scheduler.aging_machine

    # 일반 기계 조회
    normal_machine = scheduler.get_machine('A2020')
    assert normal_machine is scheduler.Machines['A2020']
```

#### Test 4: assign_operation() - Aging 경로
```python
def test_assign_operation_aging():
    scheduler = Scheduler(...)
    scheduler.machine_dict['N00001_AGING'] = {'AGING': 48}

    machine_code, start_time, processing_time = scheduler.assign_operation(
        node_earliest_start=100,
        node_id='N00001_AGING',
        depth=1
    )

    # 검증
    assert machine_code == 'AGING'
    assert start_time == 100
    assert processing_time == 48
```

---

### 6.2 통합 테스트

#### Test 5: 전체 스케줄링 플로우
```python
def test_full_scheduling_with_aging():
    # Aging 포함 DAG 생성
    dag_df = create_test_dag_with_aging()

    # 스케줄링 실행
    result = run_scheduling(dag_df, ...)

    # 결과 검증
    aging_rows = result[result[MACHINE_CODE] == 'AGING']
    assert len(aging_rows) > 0
    assert aging_rows[MACHINE_NAME].notna().all()  # NaN 없음
```

#### Test 6: Results 모듈
```python
def test_machine_info_builder_aging():
    builder = MachineInfoBuilder(machine_mapper, base_date)
    machine_schedule_df = create_test_schedule_with_aging()

    # 호기 정보 생성
    machine_info = builder.build_machine_info(machine_schedule_df)

    # AGING 행 검증
    aging_rows = machine_info[machine_info[MACHINE_CODE] == 'AGING']
    assert len(aging_rows) > 0
    assert aging_rows[MACHINE_NAME].notna().all()
    assert (aging_rows[MACHINE_NAME] == 'AGING').all()
```

---

### 6.3 엣지 케이스 테스트

#### Test 7: 혼합 시나리오
```python
def test_mixed_aging_and_normal():
    """일반 작업 - Aging - 일반 작업 혼합"""
    # DAG 구조:
    # JOB_A (염색, A2020) → AGING → JOB_B (날염, C2010)

    result = run_scheduling(...)

    # 순서 검증
    assert result.iloc[0][MACHINE_CODE] == 'A2020'
    assert result.iloc[1][MACHINE_CODE] == 'AGING'
    assert result.iloc[2][MACHINE_CODE] == 'C2010'
```

#### Test 8: 여러 Aging 노드
```python
def test_multiple_aging_nodes():
    """여러 Aging 작업이 동시에 진행"""
    # allow_overlapping=True이므로 중첩 가능

    result = run_scheduling(...)
    aging_tasks = result[result[MACHINE_CODE] == 'AGING']

    # 중첩 확인
    for i in range(len(aging_tasks) - 1):
        task1_end = aging_tasks.iloc[i][WORK_END_TIME]
        task2_start = aging_tasks.iloc[i+1][WORK_START_TIME]
        # 중첩 가능하므로 task2_start < task1_end일 수 있음
```

---

### 6.4 회귀 테스트

#### Test 9: 기존 기능 정상 작동
```python
def test_non_aging_scheduling_unchanged():
    """Aging 없는 스케줄링은 영향 없음"""
    dag_df_no_aging = create_test_dag_without_aging()

    result_before = load_reference_result()  # 수정 전 결과
    result_after = run_scheduling(dag_df_no_aging, ...)

    # 결과 일치 확인 (Aging 관련 없는 부분)
    pd.testing.assert_frame_equal(result_before, result_after)
```

---

### 6.5 데이터 검증 테스트

#### Test 10: Excel 출력 검증
```python
def test_excel_output_format():
    """최종 Excel 출력 포맷 검증"""
    result_df = run_full_pipeline(...)

    # MACHINE_CODE 값 확인
    unique_codes = result_df[MACHINE_CODE].unique()
    assert 'AGING' in unique_codes
    assert -1 not in unique_codes  # -1 없어야 함

    # MACHINE_NAME 값 확인
    aging_names = result_df[result_df[MACHINE_CODE] == 'AGING'][MACHINE_NAME]
    assert aging_names.notna().all()
    assert (aging_names == 'AGING').all() or (aging_names == 'Aging 공정').all()
```

---

## 예상 변경 통계

| 카테고리 | 파일 수 | 변경 위치 수 |
|---------|--------|-------------|
| **필수** | 6 | 15 |
| **간접 영향** | 2 | 3 |
| **문서** | 1 | 5+ |
| **테스트** | 1 (신규) | 10 |
| **총계** | 10 | 33+ |

---

## 최종 권장사항

### 7.1 마이그레이션 전략

1. ✅ **한 번에 모든 파일 수정** (원자적 변경)
   - 부분 수정 시 타입 불일치 오류 발생

2. ✅ **Phase별 커밋**
   - Phase 1-2: 데이터 + 감지 로직
   - Phase 3: machine_code 값
   - Phase 4: Results 모듈
   - Phase 5-6: 문서 + 리팩토링

3. ✅ **각 Phase 후 테스트**
   - 단위 테스트 → 통합 테스트 → E2E 테스트

### 7.2 검증 도구

**grep 검색 패턴**:
```bash
# -1 사용 확인
grep -rn "\-1" src/ --include="*.py" | grep -v "# " | grep -v "\[-1\]"

# machine_info[-1] 패턴
grep -rn "machine_info\[-1\]" src/

# set(...) == {-1} 패턴
grep -rn "== {-1}" src/

# machine_code == -1 패턴
grep -rn "== -1" src/
```

### 7.3 위험도 평가

| 위험 요소 | 발생 확률 | 영향도 | 완화 방법 |
|----------|----------|--------|----------|
| 타입 불일치 | 높음 | 높음 | 전체 동시 수정 |
| KeyError | 중간 | 높음 | 단위 테스트 |
| machine_mapper 누락 | 중간 | 중간 | 특수 처리 추가 |
| 문서 불일치 | 낮음 | 낮음 | grep 검색 |

**종합 위험도**: ⚠️ **중간**
- 변경 범위는 크지만 패턴이 일관적
- 충분한 테스트로 안전하게 마이그레이션 가능

---

## 롤백 계획

만약 마이그레이션 후 문제 발생 시:

1. **즉시 롤백**: Git revert
2. **문제 분석**: 실패한 테스트 케이스 확인
3. **부분 수정**: 문제 위치만 수정 후 재시도
4. **재테스트**: 전체 테스트 스위트 재실행

---

## 요약

**변경 내용**:
- AGING machine_code를 -1 (정수)에서 'AGING' (문자열)로 통일

**주요 위험**:
- 타입 불일치 (정수 vs 문자열)
- KeyError (딕셔너리 키 변경)
- machine_mapper 누락

**완화 방안**:
- 원자적 변경 (모든 파일 동시 수정)
- 단계별 테스트
- machine_mapping에 'AGING' 특수 처리

**예상 효과**:
- ✅ 코드 일관성 향상
- ✅ 가독성 개선
- ✅ 타입 안정성 향상 (문자열로 통일)