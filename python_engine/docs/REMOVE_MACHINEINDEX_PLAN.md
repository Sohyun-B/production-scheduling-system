# machineindex 완전 제거 계획서

## 📋 문서 정보
- **작성일**: 2025-11-13
- **목적**: machineindex 컬럼 및 관련 코드 완전 제거
- **예상 소요**: 1~2시간
- **난이도**: ⭐⭐ (중간) - 리팩토링 이후라 비교적 간단

---

## 🎯 1. 현재 상황 분석

### 1.1 machine_master_info.xlsx 구조

**현재**:
```
Columns: ['machineno', 'machinename', 'machineindex']

  machineno machinename  machineindex
0     A2020     AgNW2호기             0
1     C2010   코팅1호기_WIN             1
2     C2250  코팅25호기_WIN             2
...
```

**목표**:
```
Columns: ['machineno', 'machinename']

  machineno machinename
0     A2020     AgNW2호기
1     C2010   코팅1호기_WIN
2     C2250  코팅25호기_WIN
...
```

### 1.2 machineindex 사용 현황

#### MachineMapper 내부 (machine_mapper.py)

**Index 관련 속성**:
```python
# 제거 대상
self._idx_to_code: Dict[int, str]      # machineindex → machineno
self._idx_to_name: Dict[int, str]      # machineindex → machinename
self._code_to_idx: Dict[str, int]      # machineno → machineindex
self._name_to_idx: Dict[str, int]      # machinename → machineindex
```

**Index 관련 메서드** (총 8개):
```python
# 제거 대상
1. index_to_code(idx: int) → str        # idx → code
2. index_to_name(idx: int) → str        # idx → name
3. index_to_info(idx: int) → Dict       # idx → {code, name}
4. code_to_index(code: str) → int       # code → idx
5. name_to_index(name: str) → int       # name → idx
6. code_to_info(code: str) → Dict       # code → {index, name}  ⚠️ index 포함
7. get_all_indices() → List[int]        # 모든 idx 반환
8. format_machine_info(idx: int) → str  # 포맷팅 (idx 필요)
```

**Index 관련 검증 로직**:
```python
# __init__() (Lines 40-59)
- machineindex 필수 컬럼 검증
- machineindex 중복 검증
- machineindex로 정렬
```

#### 외부 사용처 (단 1곳!)

**src/new_results/__init__.py** (Lines 92-93):
```python
machine_mapping = {
    idx: machine_mapper.index_to_code(idx)  # ← index_to_code 사용
    for idx in machine_mapper.get_all_indices()  # ← get_all_indices 사용
}
```

**목적**: MachineScheduleProcessor에 전달하기 위한 매핑 생성
**현재 문제**: 이 매핑이 실제로 사용되는지 확인 필요

---

## 🔍 2. 제거 가능성 분석

### 2.1 Index가 필요 없는 이유

이미 코드 기반 리팩토링 완료:
- ✅ **Scheduler.Machines**: 딕셔너리 `{"A2020": Machine, ...}`
- ✅ **machine_dict**: `{node_id: {"A2020": 120, ...}}`
- ✅ **DelayProcessor**: machine_code 기반
- ✅ **Results 모듈**: machine_code 기반

**Index는 더 이상 필요 없습니다!**

### 2.2 순서 관리 방법

**Before**: machineindex로 순서 관리
```python
self._machine_master_info.sort_values('machineindex')
```

**After**: 자연 순서 또는 machineno로 정렬
```python
# Option 1: 파일 순서 그대로 사용
self._machine_master_info = machine_master_info.copy()

# Option 2: machineno로 정렬 (알파벳 순)
self._machine_master_info = machine_master_info.sort_values('machineno').reset_index(drop=True)
```

### 2.3 영향 받는 메서드

#### 완전 제거 대상 (8개)
1. `index_to_code()` ❌
2. `index_to_name()` ❌
3. `index_to_info()` ❌
4. `code_to_index()` ❌
5. `name_to_index()` ❌
6. `get_all_indices()` ❌
7. `format_machine_info(idx)` ❌

#### 수정 필요 (1개)
8. `code_to_info()` - index 제거, name만 반환

---

## 📝 3. 제거 계획

### Phase 1: 영향도 분석 및 사전 준비 (10분)

**작업 내용**:
1. ✅ 현재 상황 파악 (완료)
2. machine_mapping 사용처 상세 분석
   - `src/new_results/__init__.py:92-93`
   - `src/results/machine_processor.py` 내부에서 사용 여부 확인
3. 백업 생성 (git stash 또는 branch)

**체크포인트**:
- [ ] machine_mapping 실제 사용처 파악
- [ ] 백업 생성 확인

---

### Phase 2: 외부 사용처 수정 (20분)

**파일**: `src/new_results/__init__.py`

#### 2.1 machine_mapping 제거 또는 변경

**현재 코드** (Lines 90-107):
```python
# MachineMapper를 사용한 기계 매핑
machine_mapping = {
    idx: machine_mapper.index_to_code(idx)
    for idx in machine_mapper.get_all_indices()
}

# 기계 정보 처리 (기존 MachineProcessor 사용)
from src.results.machine_processor import MachineScheduleProcessor

machine_proc = MachineScheduleProcessor(
    machine_mapping,  # ← 여기서 사용
    machine_schedule_df,
    result_cleaned,
    base_date,
    gap_analyzer=None
)
```

**Option A: machine_mapping 완전 제거** (권장)
```python
# ❌ 제거: machine_mapping 생성 로직

# ✅ 변경: MachineScheduleProcessor가 machine_mapper 직접 받도록 수정
machine_proc = MachineScheduleProcessor(
    machine_mapper,  # ← machine_mapper 직접 전달
    machine_schedule_df,
    result_cleaned,
    base_date,
    gap_analyzer=None
)
```

**Option B: code → code 매핑으로 변경** (임시 방안)
```python
# 🔄 변경: code → code 매핑 (실질적으로 의미 없음)
machine_mapping = {
    code: code
    for code in machine_mapper.get_all_codes()
}
```

#### 2.2 MachineScheduleProcessor 수정 필요 여부 확인

- `src/results/machine_processor.py:MachineScheduleProcessor.__init__()` 확인
- machine_mapping을 어떻게 사용하는지 확인
- 필요시 machine_mapper를 직접 받도록 수정

**작업 내용**:
1. MachineScheduleProcessor 사용처 분석
2. machine_mapping → machine_mapper 변경
3. 내부 로직 수정 (필요시)

**체크포인트**:
- [ ] new_results/__init__.py 수정 완료
- [ ] MachineScheduleProcessor 수정 완료 (필요시)

---

### Phase 3: MachineMapper 클래스 수정 (30분)

**파일**: `src/utils/machine_mapper.py`

#### 3.1 __init__() 수정

**현재** (Lines 40-62):
```python
# 필수 컬럼 검증
required_columns = ['machineindex', config.columns.MACHINE_CODE, config.columns.MACHINE_NAME]
missing_columns = [col for col in required_columns if col not in machine_master_info.columns]
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# 중복 검증
if machine_master_info['machineindex'].duplicated().any():
    duplicates = machine_master_info[machine_master_info['machineindex'].duplicated()]['machineindex'].tolist()
    raise ValueError(f"Duplicate machineindex found: {duplicates}")

# 원본 데이터 저장 (복사본)
self._machine_master_info = machine_master_info.copy()

# machineindex 순서로 정렬 (순서 보장)
self._machine_master_info = self._machine_master_info.sort_values('machineindex').reset_index(drop=True)
```

**변경** (Lines 40-58):
```python
# 필수 컬럼 검증
required_columns = [config.columns.MACHINE_CODE, config.columns.MACHINE_NAME]  # ✅ machineindex 제거
missing_columns = [col for col in required_columns if col not in machine_master_info.columns]
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# ❌ 제거: machineindex 중복 검증

# 중복 검증: machineno만 체크
if machine_master_info[config.columns.MACHINE_CODE].duplicated().any():
    duplicates = machine_master_info[machine_master_info[config.columns.MACHINE_CODE].duplicated()][config.columns.MACHINE_CODE].tolist()
    raise ValueError(f"Duplicate machineno found: {duplicates}")

# 원본 데이터 저장 (복사본)
self._machine_master_info = machine_master_info.copy()

# ✅ 변경: machineno로 정렬 (일관된 순서 보장)
self._machine_master_info = self._machine_master_info.sort_values(config.columns.MACHINE_CODE).reset_index(drop=True)
```

#### 3.2 _build_mapping_dicts() 수정

**현재** (Lines 64-78):
```python
def _build_mapping_dicts(self):
    """매핑 딕셔너리 생성 (캐싱)"""
    df = self._machine_master_info

    # Index → Code/Name
    self._idx_to_code = dict(zip(df['machineindex'], df[config.columns.MACHINE_CODE]))
    self._idx_to_name = dict(zip(df['machineindex'], df[config.columns.MACHINE_NAME]))

    # Code → Index/Name
    self._code_to_idx = dict(zip(df[config.columns.MACHINE_CODE], df['machineindex']))
    self._code_to_name = dict(zip(df[config.columns.MACHINE_CODE], df[config.columns.MACHINE_NAME]))

    # Name → Index/Code
    self._name_to_idx = dict(zip(df[config.columns.MACHINE_NAME], df['machineindex']))
    self._name_to_code = dict(zip(df[config.columns.MACHINE_NAME], df[config.columns.MACHINE_CODE]))
```

**변경** (Lines 64-71):
```python
def _build_mapping_dicts(self):
    """매핑 딕셔너리 생성 (캐싱)"""
    df = self._machine_master_info

    # ❌ 제거: Index 관련 딕셔너리

    # Code → Name
    self._code_to_name = dict(zip(df[config.columns.MACHINE_CODE], df[config.columns.MACHINE_NAME]))

    # Name → Code
    self._name_to_code = dict(zip(df[config.columns.MACHINE_NAME], df[config.columns.MACHINE_CODE]))
```

#### 3.3 Index 관련 메서드 제거 (Lines 80-221)

**제거할 메서드**:
```python
# ❌ 완전 제거 (Lines 82-132)
def index_to_code(self, idx: int) -> Optional[str]:
def index_to_name(self, idx: int) -> Optional[str]:
def index_to_info(self, idx: int) -> Optional[Dict]:

# ❌ 완전 제거 (Lines 136-150)
def code_to_index(self, code: str) -> Optional[int]:

# ❌ 완전 제거 (Lines 190-204)
def name_to_index(self, name: str) -> Optional[int]:
```

#### 3.4 code_to_info() 수정

**현재** (Lines 168-186):
```python
def code_to_info(self, code: str) -> Optional[Dict]:
    """
    machineno → {index, name} 변환

    Returns:
        Optional[Dict]: {'index': machineindex, 'name': machinename} (없으면 None)
    """
    idx = self._code_to_idx.get(code)
    name = self._code_to_name.get(code)
    if idx is None or name is None:
        return None
    return {'index': idx, 'name': name}
```

**변경**:
```python
def code_to_info(self, code: str) -> Optional[Dict]:
    """
    machineno → {name} 변환

    Returns:
        Optional[Dict]: {'name': machinename} (없으면 None)
    """
    name = self._code_to_name.get(code)
    if name is None:
        return None
    return {'name': name}
```

#### 3.5 get_all_indices() 제거

**현재** (Lines 250-261):
```python
def get_all_indices(self) -> List[int]:
    """
    모든 machineindex 리스트 반환
    """
    return self._machine_master_info['machineindex'].tolist()
```

**제거**:
```python
# ❌ 완전 제거
```

#### 3.6 format_machine_info() 수정

**현재** (Lines 348-365):
```python
def format_machine_info(self, idx: int) -> str:
    """
    기계 정보를 사람이 읽기 쉬운 형태로 포맷팅

    Example:
        >>> mapper.format_machine_info(0)
        '염색1호기_WIN (C2010) [idx=0]'
    """
    info = self.index_to_info(idx)
    if info is None:
        return f"Unknown machine [idx={idx}]"
    return f"{info['name']} ({info['code']}) [idx={idx}]"
```

**변경**:
```python
def format_machine_info(self, code: str) -> str:
    """
    기계 정보를 사람이 읽기 쉬운 형태로 포맷팅

    Args:
        code (str): 기계 코드

    Example:
        >>> mapper.format_machine_info('C2010')
        '염색1호기_WIN (C2010)'
    """
    name = self.code_to_name(code)
    if name is None:
        return f"Unknown machine [{code}]"
    return f"{name} ({code})"
```

#### 3.7 __str__() 수정

**현재** (Lines 376-386):
```python
def __str__(self) -> str:
    """MachineMapper 객체의 상세 문자열 표현"""
    lines = [f"MachineMapper: {self.get_machine_count()} machines"]
    for idx in self.get_all_indices():
        lines.append(f"  [{idx}] {self.index_to_code(idx)} - {self.index_to_name(idx)}")
    return "\n".join(lines)
```

**변경**:
```python
def __str__(self) -> str:
    """MachineMapper 객체의 상세 문자열 표현"""
    lines = [f"MachineMapper: {self.get_machine_count()} machines"]
    for code in self.get_all_codes():
        lines.append(f"  {code} - {self.code_to_name(code)}")
    return "\n".join(lines)
```

**작업 내용**:
1. __init__() 수정 (machineindex 검증 제거, machineno 정렬)
2. _build_mapping_dicts() 수정 (index 딕셔너리 제거)
3. index 관련 메서드 8개 제거
4. code_to_info() 수정 (index 제거)
5. format_machine_info() 수정 (code 기반)
6. __str__() 수정 (get_all_codes 사용)
7. docstring 업데이트

**체크포인트**:
- [ ] 모든 index 관련 메서드 제거 확인
- [ ] 남은 메서드들이 정상 동작하는지 확인

---

### Phase 4: machine_master_info.xlsx 수정 (5분)

**파일**: `data/input/machine_master_info.xlsx`

#### 방법 1: Excel에서 직접 수정
1. Excel 파일 열기
2. machineindex 컬럼 삭제
3. 저장

#### 방법 2: Python으로 수정
```python
import pandas as pd

# 읽기
df = pd.read_excel('data/input/machine_master_info.xlsx')

# machineindex 컬럼 제거
df = df[['machineno', 'machinename']]

# 저장
df.to_excel('data/input/machine_master_info.xlsx', index=False)
```

**작업 내용**:
1. machine_master_info.xlsx에서 machineindex 컬럼 제거
2. 파일 저장 확인

**체크포인트**:
- [ ] Excel 파일에서 machineindex 컬럼 제거 확인

---

### Phase 5: 통합 테스트 (20분)

**작업 내용**:
1. main.py 전체 실행
   ```bash
   python main.py
   ```

2. 에러 발생 시 확인 및 수정
   - machineindex 관련 에러 체크
   - 누락된 수정 사항 찾기

3. 결과 확인
   - 성과 지표 정상 출력
   - Excel 파일 정상 생성
   - 간트차트 정상 생성

**체크포인트**:
- [ ] main.py 실행 성공
- [ ] 모든 결과 파일 정상 생성
- [ ] 성과 지표 일치 확인

---

### Phase 6: 문서화 및 정리 (10분)

**작업 내용**:
1. 이번 작업 내용 문서화
   - `REMOVE_MACHINEINDEX_PROGRESS.md` 생성
   - 변경 파일 목록
   - 제거된 메서드 목록

2. 주석 업데이트
   - MachineMapper docstring 업데이트
   - machineindex 언급 제거

3. Git commit
   ```bash
   git add .
   git commit -m "Remove machineindex column and related code

   - Remove machineindex from machine_master_info.xlsx
   - Remove all index-related methods from MachineMapper
   - Update machine_mapping usage in new_results/__init__.py
   - Simplify MachineMapper to code/name only
   "
   ```

**체크포인트**:
- [ ] 문서 작성 완료
- [ ] Git commit 완료

---

## 📊 4. 예상 효과

### 4.1 코드 단순화

**Before**:
- MachineMapper: 3가지 키 (index, code, name)
- 매핑 딕셔너리: 6개
- 공개 메서드: 13개

**After**:
- MachineMapper: 2가지 키 (code, name)
- 매핑 딕셔너리: 2개 (-67%)
- 공개 메서드: 5개 (-62%)

### 4.2 유지보수성 향상

```
Before:
- machineindex 순서 관리 필요
- index ↔ code 변환 필요
- 3가지 식별자 관리

After:
- machineno 또는 자연 순서
- 직접 code 사용
- 2가지 식별자만 관리 (단순!)
```

### 4.3 파일 크기 감소

**machine_mapper.py**:
- Before: 387 lines
- After: ~250 lines (예상) (-35%)

---

## 🚨 5. 리스크 및 완화 방안

### 리스크 1: 순서 변경 영향

**문제**: machineindex로 정렬하던 것을 machineno로 정렬 시 순서가 바뀔 수 있음
- machineindex: [0, 1, 2, 3, ...]
- machineno 정렬: [A2020, C2010, C2250, ...]

**완화 방안**:
- 이미 코드 기반으로 전환 완료 → 순서 의존성 없음
- 순서가 바뀌어도 결과에 영향 없음 ✅

### 리스크 2: 미발견 사용처

**문제**: index 관련 메서드를 사용하는 곳이 더 있을 수 있음

**완화 방안**:
- Phase 1에서 철저한 분석
- 통합 테스트로 검증
- 에러 발생 시 즉시 수정

### 리스크 3: 외부 의존성

**문제**: 외부 코드나 다른 팀에서 machineindex 사용 가능성

**완화 방안**:
- 현재 프로젝트는 독립적임 (외부 의존성 없음)
- Excel 파일은 내부 데이터 → 안전

---

## ✅ 6. 체크리스트

### Phase 1: 영향도 분석 (10분)
- [ ] machine_mapping 사용처 상세 분석
- [ ] MachineScheduleProcessor 내부 확인
- [ ] 백업 생성

### Phase 2: 외부 사용처 수정 (20분)
- [ ] new_results/__init__.py 수정
- [ ] MachineScheduleProcessor 수정 (필요시)

### Phase 3: MachineMapper 수정 (30분)
- [ ] __init__() 수정
- [ ] _build_mapping_dicts() 수정
- [ ] index 관련 메서드 8개 제거
- [ ] code_to_info() 수정
- [ ] format_machine_info() 수정
- [ ] __str__() 수정
- [ ] docstring 업데이트

### Phase 4: Excel 파일 수정 (5분)
- [ ] machineindex 컬럼 제거
- [ ] 파일 저장 확인

### Phase 5: 통합 테스트 (20분)
- [ ] main.py 실행 성공
- [ ] 결과 파일 정상 생성
- [ ] 성과 지표 일치

### Phase 6: 문서화 (10분)
- [ ] 진행 문서 작성
- [ ] Git commit

---

## 🎯 7. 최종 목표

**machineindex 완전 제거 후**:

1. ✅ machine_master_info.xlsx: 2개 컬럼만 (machineno, machinename)
2. ✅ MachineMapper: 간결한 2-way 매핑 (code ↔ name)
3. ✅ 코드 단순화: 메서드 62% 감소
4. ✅ 유지보수성 향상: 식별자 1개 감소
5. ✅ 순서 독립성: machineno 기준 정렬 (일관성)

**최종 결과**: 더 간결하고 명확한 기계 정보 관리 시스템!

---

**작성 완료** ✅
**준비되면 Phase 1부터 시작하시겠습니까?**
