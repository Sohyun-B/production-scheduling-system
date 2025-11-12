# 기계 정보 중앙 집중식 관리 구현 계획서

## 📋 문서 정보
- **작성일**: 2025-11-12
- **최종 수정일**: 2025-11-12
- **버전**: v1.4
- **목적**: 기계 정보 관리 방식을 명시적 마스터 테이블 + 중앙 집중식으로 개선
- **상태**: ✅ **Phase 0, 1, 2 핵심 수정 완료** (2025-11-12)

**v1.4 주요 변경사항** (2025-11-12):
- ✅ Phase 0 완료: machine_master_info.xlsx 생성, validation 모듈 수정
- ✅ Phase 1 완료: MachineMapper 클래스 구현 및 테스트 완료
- ✅ Phase 2 완료: 주요 6개 파일 수정 완료 (main.py, DAG, Scheduler, Results)
- ⚠️ Phase 3: 통합 테스트는 향후 진행

**v1.3 주요 변경사항**:
- ✅ machine_master_info는 validation 대상에서 제외
- ✅ main.py에서 Validation 완료 후 독립적으로 로딩
- ✅ validation 모듈 수정 범위 축소

## 🎯 핵심 변경사항 요약

### Before (현재 방식)
```python
# 1. Validation에서 linespeed_df로부터 자동 추출
# src/validation/production_preprocessor.py
machine_master_info = linespeed_df[['machineno', 'machinename']]\
    .drop_duplicates()\
    .sort_values(by='machineno')\  # ← 사전순 정렬 강제
    .assign(machineindex=range(len(df)))  # ← 자동 부여

# 2. 매핑 로직 6개 파일에 중복
```

**문제점**:
- ❌ 암묵적 생성 (linespeed 의존)
- ❌ 순서 제어 불가
- ❌ machineindex 자동 부여
- ❌ 매핑 로직 중복

### After (개선 방식)
```python
# 1. Validation 완료 후, 별도 Excel 파일에서 독립적으로 로딩
# main.py (Validation 이후)
machine_master_info_df = pd.read_excel(
    "data/input/machine_master_info.xlsx",
    sheet_name="machine_master"
)

# 2. MachineMapper 클래스로 중앙 관리
machine_mapper = MachineMapper(machine_master_info_df)

# 3. 모든 매핑을 mapper 통해 수행
machine_code = machine_mapper.index_to_code(0)  # 'A2020'
machine_name = machine_mapper.index_to_name(0)  # 'AgNW2호기'
```

**개선 효과**:
- ✅ 사용자가 기계 목록 명시적 관리
- ✅ 순서(machineindex) 직접 제어
- ✅ 매핑 로직 중앙 집중 (6개 → 1개)
- ✅ 디버깅 용이 (기계명 자동 표시)
- ✅ **machine_master_info는 validation 대상이 아님** (독립적 관리)

---

## 1. 현재 문제점 분석

### 1.1 기계 정보 생성 방식의 문제

**현재 방식**: `linespeed_df`에서 기계 정보를 추출하여 자동 생성

```python
# src/validation/production_preprocessor.py:185-203
machine_master_info = (
    linespeed_df[[MACHINE_CODE, MACHINE_NAME]]
    .drop_duplicates()
    .sort_values(by=MACHINE_CODE)  # ← machineno 사전순 정렬
    .reset_index(drop=True)
    .assign(machineindex=range(len(df)))  # ← 0, 1, 2, ... 자동 부여
)
```

**문제점**:
1. ❌ **암묵적 생성**: linespeed에 있는 기계만 자동으로 추출
2. ❌ **순서 제어 불가**: machineno 사전순 정렬로 고정 (변경 불가)
3. ❌ **machineindex 자동 부여**: 사용자가 명시적으로 관리할 수 없음
4. ❌ **linespeed 의존성**: linespeed에 없는 기계는 등록 불가
5. ❌ **데이터 정합성**: 기계 정보가 여러 곳에 흩어져 있음

### 1.2 매핑 로직 중복 (6개 파일에 분산)

| 파일 | 라인 | 내용 | 문제점 |
|------|------|------|--------|
| `src/validation/production_preprocessor.py` | 185-203 | machine_master_info 생성 | 암묵적 생성 |
| `src/dag_management/node_dict.py` | 73-75 | `enumerate(machine_columns)` | 순서 의존 |
| `src/scheduler/__init__.py` | 133-138 | `code_to_index` dict 생성 | 중복 매핑 |
| `src/new_results/__init__.py` | 91-93, 117-124 | `machine_mapping`, `code_to_name_mapping` | 중복 매핑 |
| `src/new_results/machine_detailed_analyzer.py` | 25-32 | `machine_idx_to_code/name` | 중복 매핑 |
| `src/results/machine_processor.py` | 187 | `machine_mapping` | 중복 매핑 |

**총 6개 파일에서 동일한 매핑 로직을 중복 작성**

### 1.2 순서 의존성 문제

```python
# 1. Validation 단계에서 machineindex 생성
machine_master_info = linespeed_df[[MACHINE_CODE, MACHINE_NAME]]\
    .drop_duplicates()\
    .sort_values(by=MACHINE_CODE)\  # ← machineno 정렬
    .reset_index(drop=True)\
    .assign(machineindex=range(len(df)))  # ← 0, 1, 2, ... 부여

# 2. DAG Creation 단계에서 암묵적으로 재생성
machine_columns = machine_master_info[MACHINE_CODE].tolist()
for idx, col in enumerate(machine_columns):  # ← 순서 의존
    machine_dict[node_id][idx] = processing_time
```

**위험**: `machine_columns`의 순서가 바뀌면 전체 시스템 오작동

### 1.3 디버깅 어려움

```python
# 현재 로그
print(f"기계 0에 할당")  # ← 어떤 기계인지 알 수 없음

# Scheduler에서 machine_index만 사용
self.Machines[ideal_machine_index]._Input(...)  # ← 0, 1, 2, ...
```

**문제**: machine_index만으로는 어떤 기계인지 식별 불가

### 1.4 기계명 활용 부족

- `machinename`은 최종 출력 시에만 사용
- 중간 과정에서는 전혀 사용되지 않음
- 디버깅/로깅 시 사람이 읽기 어려움

### 1.5 검증 로직 부재

- `machine_master_info` 순서와 `machine_columns` 순서 불일치 검증 없음
- 순서가 틀어져도 오류 감지 불가

---

## 2. 개선 목표

### 2.1 핵심 목표

1. ✅ **명시적 마스터 테이블**: Excel에 기계기준정보 시트 추가 (tb_machinemaster)
2. ✅ **사용자 제어 가능**: machineindex를 사용자가 직접 관리
3. ✅ **중앙 집중식 관리**: 모든 기계 매핑을 하나의 클래스에서 관리
4. ✅ **일관성 보장**: machine_master_info를 단일 진실 공급원(Single Source of Truth)으로 사용
5. ✅ **추적 가능성 향상**: 디버깅 시 기계명 즉시 확인 가능
6. ✅ **코드 중복 제거**: 6개 파일의 중복 매핑 로직 제거
7. ✅ **검증 강화**: 순서 일치성 및 무결성 검증 내장

### 2.2 개선 방안: 별도 Excel 파일로 기계 마스터 테이블 관리

#### 2.2.1 새로운 입력 파일 생성

**파일**: `data/input/machine_master_info.xlsx` (별도 파일)
**시트명**: `machine_master` (기계 기준 정보)

**파일 구조**:

| machineindex | machineno | machinename |
|-------------|-----------|-------------|
| 0           | A2020     | AgNW2호기 |
| 1           | C2010     | 염색1호기_WIN |
| 2           | C2250     | 염색25호기_WIN |
| 3           | C2260     | 염색26호기_WIN |
| 4           | C2270     | 염색27호기_WIN |
| 5           | D2280     | 염색28호기_DSP |
| ...         | ...       | ...         |

**필수 컬럼**:
- `machineindex` (int): 기계 인덱스 (0부터 시작, 중복 불가, 연속적일 필요 없음)
- `machineno` (str): 기계 코드 (A2020, C2010, C2250, ... - 유니크)
- `machinename` (str): 기계명 (AgNW2호기, 염색1호기_WIN, ... - 사람이 읽는 이름)

**선택 컬럼** (확장 가능):
- `비고` (str): 기계 설명
- `machine_type` (str): 기계 유형 (염색기, 수세기, ...)
- `is_active` (bool): 사용 여부 (True/False)

**파일 생성**:
- `create_machine_master.py` 스크립트로 자동 생성
- linespeed에서 기계 목록 추출 → 별도 Excel 파일로 저장

#### 2.2.2 장점

**현재 방식 (자동 생성)**:
```python
machine_master_info = linespeed_df[['machineno', 'machinename']]\
    .drop_duplicates()\
    .sort_values(by='machineno')\
    .assign(machineindex=range(len(df)))
```
- ❌ linespeed에 있는 기계만 자동 추출
- ❌ 정렬 순서 변경 불가
- ❌ machineindex 제어 불가

**개선 방식 (별도 파일 명시적 관리)**:
```python
machine_master_info = pd.read_excel(
    "data/input/machine_master_info.xlsx",
    sheet_name="machine_master",
    dtype={'machineindex': int, 'machineno': str}
)
```
- ✅ 사용자가 기계 목록 명시적 관리
- ✅ 순서(machineindex) 직접 제어 가능
- ✅ linespeed에 없는 기계도 등록 가능
- ✅ 기계 정보가 별도 파일로 독립적 관리
- ✅ 마스터 데이터로서 역할 명확
- ✅ 입력 파일과 분리되어 버전 관리 용이

### 2.2 비기능 요구사항

- **성능**: 매핑 딕셔너리는 초기화 시 한 번만 생성 (캐싱)
- **확장성**: 새로운 매핑 메서드 추가 용이
- **호환성**: 기존 코드와 최대한 호환되도록 설계
- **테스트**: 단위 테스트 작성 필수

---

## 3. 설계 방안

### 3.1 MachineMapper 클래스 설계

#### 3.1.1 클래스 구조

```python
# src/utils/machine_mapper.py

from typing import Dict, List, Optional
import pandas as pd
from config import config

class MachineMapper:
    """
    기계 정보 중앙 집중식 관리 클래스

    machine_master_info를 기반으로 다음 매핑을 제공:
    - machineindex (0, 1, 2, ...) ↔ machineno (C2010, C2250, ...)
    - machineindex ↔ machinename (1호기, 25호기, ...)
    - machineno ↔ machinename

    Attributes:
        machine_master_info (pd.DataFrame): 기계 마스터 정보
            - machineindex: 0, 1, 2, ... (int)
            - machineno: C2010, C2250, ... (str)
            - machinename: 1호기, 25호기, ... (str)
    """

    def __init__(self, machine_master_info: pd.DataFrame):
        """
        Args:
            machine_master_info: 기계 마스터 정보 DataFrame
                필수 컬럼: machineindex, machineno, machinename

        Raises:
            ValueError: 필수 컬럼 누락 시
            ValueError: machineindex 중복 시
            ValueError: machineno 중복 시
        """
        self._validate_input(machine_master_info)
        self._master = machine_master_info.copy()
        self._build_mappings()

    # === Validation ===
    def _validate_input(self, df: pd.DataFrame) -> None:
        """입력 DataFrame 검증"""
        pass

    # === Mapping Construction ===
    def _build_mappings(self) -> None:
        """모든 매핑 딕셔너리 생성 (캐싱)"""
        pass

    # === Public API: Index → Code/Name ===
    def index_to_code(self, idx: int) -> Optional[str]:
        """machineindex → machineno"""
        pass

    def index_to_name(self, idx: int) -> Optional[str]:
        """machineindex → machinename"""
        pass

    def index_to_info(self, idx: int) -> Optional[Dict[str, str]]:
        """machineindex → {code, name}"""
        pass

    # === Public API: Code → Index/Name ===
    def code_to_index(self, code: str) -> Optional[int]:
        """machineno → machineindex"""
        pass

    def code_to_name(self, code: str) -> Optional[str]:
        """machineno → machinename"""
        pass

    def code_to_info(self, code: str) -> Optional[Dict]:
        """machineno → {index, name}"""
        pass

    # === Public API: Name → Index/Code ===
    def name_to_index(self, name: str) -> Optional[int]:
        """machinename → machineindex"""
        pass

    def name_to_code(self, name: str) -> Optional[str]:
        """machinename → machineno"""
        pass

    # === Public API: Bulk Operations ===
    def get_all_codes(self) -> List[str]:
        """모든 machineno 리스트 (machineindex 순서)"""
        pass

    def get_all_names(self) -> List[str]:
        """모든 machinename 리스트 (machineindex 순서)"""
        pass

    def get_all_indices(self) -> List[int]:
        """모든 machineindex 리스트"""
        pass

    def get_machine_count(self) -> int:
        """기계 개수"""
        pass

    def get_master_info(self) -> pd.DataFrame:
        """원본 machine_master_info 반환 (복사본)"""
        pass

    # === Validation Helpers ===
    def validate_machine_order(self, machine_columns: List[str]) -> bool:
        """machine_columns 순서가 machine_master_info와 일치하는지 검증"""
        pass

    # === String Representation ===
    def format_machine_info(self, idx: int) -> str:
        """
        기계 정보를 사람이 읽기 쉬운 형태로 포맷팅
        예: "1호기 (C2010) [idx=0]"
        """
        pass

    def __repr__(self) -> str:
        return f"MachineMapper(machines={self.get_machine_count()})"
```

#### 3.1.2 내부 데이터 구조

```python
# 캐싱된 매핑 딕셔너리 (초기화 시 한 번만 생성)
self._idx_to_code: Dict[int, str]      # {0: 'C2010', 1: 'C2250', ...}
self._idx_to_name: Dict[int, str]      # {0: '1호기', 1: '25호기', ...}
self._code_to_idx: Dict[str, int]      # {'C2010': 0, 'C2250': 1, ...}
self._code_to_name: Dict[str, str]     # {'C2010': '1호기', 'C2250': '25호기', ...}
self._name_to_idx: Dict[str, int]      # {'1호기': 0, '25호기': 1, ...}
self._name_to_code: Dict[str, str]     # {'1호기': 'C2010', '25호기': 'C2250', ...}
```

### 3.2 전달 방식 변경

#### 3.2.1 현재 방식

```python
# main.py
machine_master_info = processed_data['machine_master_info']

# DAG Creation
machine_columns = machine_master_info[MACHINE_CODE].tolist()
create_complete_dag_system(..., machine_columns=machine_columns)

# Scheduler
code_to_index = dict(zip(machine_master_info[MACHINE_CODE],
                         machine_master_info[MACHINE_INDEX]))
delay_processor = DelayProcessor(..., machine_index_list)

# Results
machine_mapping = machine_master_info.set_index(MACHINE_INDEX)[MACHINE_CODE].to_dict()
```

**문제**: 각 단계마다 매핑 로직 중복

#### 3.2.2 개선 방식

```python
# main.py
machine_master_info = processed_data['machine_master_info']
machine_mapper = MachineMapper(machine_master_info)  # ← 한 번만 생성

# DAG Creation
create_complete_dag_system(..., machine_mapper=machine_mapper)  # ← mapper 전달

# Scheduler
run_scheduler_pipeline(..., machine_mapper=machine_mapper)  # ← mapper 전달

# Results
create_new_results(..., machine_mapper=machine_mapper)  # ← mapper 전달
```

**장점**: 매핑 로직 중복 제거, 일관성 보장

### 3.3 machine_dict 생성 방식 변경

#### 3.3.1 현재 방식

```python
# src/dag_management/node_dict.py:73-75
for idx, col in enumerate(machine_columns):  # ← 순서 의존
    processing_time = row[col]
    machine_dict[node_id][idx] = int(processing_time)
```

**문제**:
- `enumerate()`로 암묵적 index 생성
- `machine_columns` 순서가 바뀌면 오류

#### 3.3.2 개선 방식 (Option 1: mapper 사용)

```python
# src/dag_management/node_dict.py
def create_machine_dict(sequence_seperated_order, linespeed, machine_mapper, ...):
    machine_codes = machine_mapper.get_all_codes()  # ← 순서 보장된 리스트

    for col in machine_codes:
        idx = machine_mapper.code_to_index(col)  # ← 명시적 매핑
        processing_time = row[col]
        machine_dict[node_id][idx] = int(processing_time)

    # 순서 검증
    if not machine_mapper.validate_machine_order(machine_codes):
        raise ValueError("Machine order mismatch!")
```

**장점**:
- 명시적 매핑
- 순서 검증 내장
- 디버깅 용이

#### 3.3.3 개선 방식 (Option 2: 기계코드를 키로 사용)

```python
# machine_dict 구조 변경
machine_dict = {
    node_id: {
        'C2010': 120,
        'C2250': 150,
        'C2260': 9999,
        ...
    }
}

# Scheduler에서 사용 시
for machine_code, processing_time in machine_info.items():
    machine_index = machine_mapper.code_to_index(machine_code)
    if processing_time != 9999:
        ...
```

**장점**:
- 더 명확한 의미
- 순서 독립적

**단점**:
- 기존 코드 대대적 수정 필요
- 성능 영향 (str vs int 키)

**결정**: Option 1 채택 (호환성 우선)

### 3.4 로깅 개선

#### 3.4.1 현재 방식

```python
print(f"기계 {machine_index}에 할당")  # ← "기계 0에 할당"
```

#### 3.4.2 개선 방식

```python
machine_info_str = machine_mapper.format_machine_info(machine_index)
print(f"{machine_info_str}에 할당")  # ← "1호기 (C2010) [idx=0]에 할당"
```

---

## 4. 구현 단계

### Phase 0: 기계 마스터 파일 생성 (0.5일)

#### Step 0.1: machine_master_info.xlsx 파일 생성
- [x] `create_machine_master.py` 스크립트 작성 완료
- [x] 별도 Excel 파일 생성: `data/input/machine_master_info.xlsx`
- [x] 시트명: `machine_master`
- [x] 필수 컬럼 생성: `machineindex`, `machineno`, `machinename`
- [x] 기존 linespeed_df에서 기계 목록 추출하여 초기 데이터 입력

**생성 완료** (2025-11-12):
```bash
python create_machine_master.py
# → data/input/machine_master_info.xlsx 생성 완료 (12대 기계)
```

**파일 내용**:
```
machineindex | machineno | machinename
0            | A2020     | AgNW2호기
1            | C2010     | 염색1호기_WIN
...          | ...       | ...
11           | O2590     | 염색59호기_DSP
```

#### Step 0.2: main.py 로딩 로직 수정
- [x] `main.py`에서 **Validation 이후**에 별도 파일 로딩 추가 ✅ (2025-11-12)
- [x] `src/validation/production_preprocessor.py`의 `preprocess_machine_master_info()` 함수 제거 ✅

**중요**: machine_master_info는 validation 대상이 아님!

**수정 코드**:
```python
# main.py (라인 32-105 수정)

# === Excel 파일 로딩 ===
linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", ...)
# ... 기타 시트 로딩

# === Validation (machine_master_info 없이 진행) ===
print("[10%] 데이터 유효성 검사 및 전처리 (Validation) 시작...")
processed_data = preprocess_production_data(
    order_df=order_df,
    linespeed_df=linespeed_df,
    # machine_master_info_df 전달 안 함!
    ...
)

linespeed = processed_data['linespeed']
# processed_data에서 machine_master_info 제거됨

print("[30%] Validation 완료!")

# === Validation 이후에 기계 마스터 정보 로딩 ===
print("[30%] 기계 마스터 정보 로딩 중...")
machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(
    machine_master_file,
    sheet_name="machine_master",
    dtype={'machineindex': int, 'machineno': str}
)
print(f"[INFO] 기계 마스터 정보 로딩: {len(machine_master_info_df)}대")
```

#### Step 0.3: validation 모듈 수정
- [x] `preprocess_production_data()` 함수에서 `machine_master_info` 관련 모든 로직 제거 ✅ (2025-11-12)
- [x] `preprocess_machine_master_info()` 함수 완전 삭제 ✅
- [x] 반환 딕셔너리에서 `machine_master_info` 키 제거 ✅

**이유**:
- ✅ machine_master_info는 원본 입력 데이터가 아닌 메타데이터
- ✅ validation은 생산계획 입력 데이터만 검증
- ✅ 기계 마스터는 독립적으로 관리

**수정 코드**:
```python
# src/validation/__init__.py

def preprocess_production_data(
    order_df,
    linespeed_df,
    # machine_master_info_df 파라미터 제거!
    ...
):
    # machine_master_info 관련 로직 전부 제거

    # 기존 로직 유지
    ...

    return {
        # 'machine_master_info': ... ← 제거!
        'linespeed': linespeed_pivot,
        'operation_types': operation_types,
        ...
    }
```

### Phase 1: 기반 구축 (1일) ✅ **완료** (2025-11-12)

#### Step 1.1: MachineMapper 클래스 생성
- [x] `src/utils/machine_mapper.py` 파일 생성 ✅
- [x] 클래스 기본 구조 작성 ✅
- [x] 검증 로직 구현 ✅
- [x] 매핑 딕셔너리 생성 로직 구현 ✅
- [x] 단위 테스트 작성 (`test_machine_mapper.py`) ✅

#### Step 1.2: 통합 테스트
- [x] 실제 `machine_master_info` 데이터로 테스트 ✅
- [x] 모든 매핑 메서드 정상 동작 확인 ✅
- [x] 순서 검증 로직 테스트 ✅

### Phase 2: 기존 코드 수정 (2일) ✅ **핵심 수정 완료** (2025-11-12)

#### Step 2.1: main.py 수정
- [x] `MachineMapper` 생성 로직 추가 (Validation 직후) ✅
- [x] 전체 파이프라인에 `machine_mapper` 전달 ✅

#### Step 2.2: DAG Creation 수정
- [x] `src/dag_management/__init__.py` - `create_complete_dag_system()` 파라미터 변경 ✅
- [x] `src/dag_management/node_dict.py` - `create_machine_dict()` 수정 ✅
  - `machine_columns` → `machine_mapper` 변경 ✅
  - enumerate() 제거, 명시적 매핑 사용 ✅
  - ⚠️ 순서 검증 로직: 보류 (MACHINE_ORDER_VALIDATION_ISSUE.md 참조)

#### Step 2.3: Scheduler 수정
- [x] `src/scheduler/__init__.py` - `run_scheduler_pipeline()` 파라미터 변경 ✅
- [x] `code_to_index` 딕셔너리 생성 제거 → `machine_mapper` 사용 ✅
- [x] `machine_index_list` 생성 로직 수정 ✅

#### Step 2.4: Results 수정
- [x] `src/new_results/__init__.py` - `create_new_results()` 파라미터 변경 ✅
- [x] `machine_mapping`, `code_to_name_mapping` 딕셔너리 생성 제거 → `machine_mapper` 사용 ✅
- [x] `SimplifiedGapAnalyzer` 생성자 파라미터 변경 ✅
- [x] `MachineDetailedAnalyzer` 생성자 파라미터 변경 ✅
- ⚠️ `src/results/machine_processor.py` - 추후 필요시 수정

#### Step 2.5: 로깅 개선
- ⚠️ `src/scheduler/scheduler.py` - 추후 필요시 수정
- ⚠️ `src/scheduler/scheduling_core.py` - 추후 필요시 수정

### Phase 3: 테스트 및 검증 (1일)

#### Step 3.1: 통합 테스트
- [ ] `main.py` 전체 실행
- [ ] 결과 파일 생성 확인
- [ ] 기존 결과와 비교 (동일한지 확인)

#### Step 3.2: 성능 테스트
- [ ] 실행 시간 측정
- [ ] 메모리 사용량 확인

#### Step 3.3: 로그 분석
- [ ] 기계명이 제대로 출력되는지 확인
- [ ] 순서 검증 로그 확인

### Phase 4: 문서화 및 정리 (0.5일)

#### Step 4.1: 코드 문서화
- [ ] MachineMapper 클래스 docstring 완성
- [ ] 각 메서드 docstring 추가
- [ ] 사용 예시 추가

#### Step 4.2: README 업데이트
- [ ] `readme.md` - MachineMapper 사용법 추가
- [ ] `CLAUDE.md` - 아키텍처 설명 업데이트

#### Step 4.3: 레거시 코드 정리
- [ ] 사용하지 않는 매핑 로직 제거 확인
- [ ] 주석 처리된 코드 제거

---

## 5. 영향 받는 파일 목록

### 5.1 신규 생성 파일

| 파일 경로 | 내용 | 상태 |
|----------|------|------|
| `create_machine_master.py` | 기계 마스터 파일 생성 스크립트 | ✅ 완료 |
| `data/input/machine_master_info.xlsx` | 기계 마스터 정보 (별도 파일) | ✅ 완료 |
| `src/utils/machine_mapper.py` | MachineMapper 클래스 | ⏳ 예정 |
| `tests/test_machine_mapper.py` | 단위 테스트 | ⏳ 예정 |

### 5.2 수정 필요 파일 (우선순위 순)

| 우선순위 | 파일 경로 | 수정 범위 | 상태 |
|---------|----------|----------|------|
| 0 | `create_machine_master.py` | 별도 파일 생성 스크립트 | ✅ 완료 |
| 1 | `main.py` | Validation 이후 machine_master_info.xlsx 로딩 + MachineMapper 생성 | ⏳ 예정 |
| 2 | `src/validation/production_preprocessor.py` | preprocess_machine_master_info() 함수 삭제 | ⏳ 예정 |
| 3 | `src/dag_management/__init__.py` | 함수 시그니처 변경 | ⏳ 예정 |
| 4 | `src/dag_management/node_dict.py` | create_machine_dict() 로직 변경 | ⏳ 예정 |
| 5 | `src/scheduler/__init__.py` | run_scheduler_pipeline() 변경 | ⏳ 예정 |
| 6 | `src/new_results/__init__.py` | create_new_results() 변경 | ⏳ 예정 |
| 7 | `src/new_results/machine_detailed_analyzer.py` | 생성자 변경 | ⏳ 예정 |
| 8 | `src/results/machine_processor.py` | 매핑 전달 방식 변경 | ⏳ 예정 |
| 9 | `src/scheduler/scheduler.py` | 로깅 개선 (선택사항) | ⏳ 예정 |
| 10 | `src/scheduler/scheduling_core.py` | 로깅 개선 (선택사항) | ⏳ 예정 |

**총 10개 파일 수정 예상**

**주요 변경점**:
- ❌ `src/validation/__init__.py` 수정 제거 (validation은 machine_master_info 관여 안 함)
- ✅ machine_master_info는 main.py에서 Validation 이후 독립적으로 로딩

### 5.3 수정 불필요 파일

다음 파일들은 수정이 불필요합니다 (하위 레벨에서 동작):
- `src/scheduler/machine.py` (Machine_Time_window)
- `src/scheduler/delay_dict.py` (DelayProcessor)
- `src/dag_management/dag_dataframe.py` (DAGNode)
- `src/dag_management/dag_manager.py` (DAGGraphManager)

---

## 6. 파일별 상세 수정 사항

### 6.1 main.py

#### 현재 코드 (라인 32-105)
```python
# === Excel 파일 로딩 ===
try:
    print("Excel 파일 로딩 중...")
    input_file = "data/input/생산계획 입력정보.xlsx"

    order_df = pd.read_excel(input_file, sheet_name="tb_polist", ...)
    linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", ...)
    # ... 기타 시트 로딩

    print("Excel 파일 로딩 완료!")

except FileNotFoundError as e:
    print(f"오류: 파일을 찾을 수 없습니다 - {e}")
    return

# === Validation ===
print("[10%] 데이터 유효성 검사 및 전처리 (Validation) 시작...")
processed_data = preprocess_production_data(
    order_df=order_df,
    linespeed_df=linespeed_df,
    # ... 기타 파라미터
)

linespeed = processed_data['linespeed']
machine_master_info = processed_data['machine_master_info']  # ← 자동 생성됨
```

#### 수정 후 코드
```python
from src.utils.machine_mapper import MachineMapper

# === Excel 파일 로딩 ===
try:
    print("Excel 파일 로딩 중...")
    input_file = "data/input/생산계획 입력정보.xlsx"

    order_df = pd.read_excel(input_file, sheet_name="tb_polist", ...)
    linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", ...)
    # ... 기타 시트 로딩

    print("Excel 파일 로딩 완료!")

except FileNotFoundError as e:
    print(f"오류: 파일을 찾을 수 없습니다 - {e}")
    return

# === Validation (machine_master_info 없이 진행!) ===
print("[10%] 데이터 유효성 검사 및 전처리 (Validation) 시작...")
processed_data = preprocess_production_data(
    order_df=order_df,
    linespeed_df=linespeed_df,
    # machine_master_info_df 전달 안 함!
    # ... 기타 파라미터
)

linespeed = processed_data['linespeed']
# processed_data에서 machine_master_info 제거됨

print("[30%] Validation 완료!")

# === ★ Validation 이후에 기계 마스터 정보 로딩 (독립적) ===
print("[30%] 기계 마스터 정보 로딩 중...")
machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(
    machine_master_file,
    sheet_name="machine_master",
    dtype={
        config.columns.MACHINE_INDEX: int,
        config.columns.MACHINE_CODE: str
    }
)
print(f"[INFO] 기계 마스터 정보 로딩: {len(machine_master_info_df)}대")

# ★ MachineMapper 생성 (한 번만)
machine_mapper = MachineMapper(machine_master_info_df)
print(f"[INFO] {machine_mapper}")  # "MachineMapper(machines=12)"
```

#### 추가 수정 (라인 138, 157)
```python
# Before
result, scheduler = run_scheduler_pipeline(
    dag_df=dag_df,
    ...,
    machine_master_info=machine_master_info,
    ...
)

# After
result, scheduler = run_scheduler_pipeline(
    dag_df=dag_df,
    ...,
    machine_mapper=machine_mapper,  # ← 변경
    ...
)
```

```python
# Before
final_results = create_new_results(
    ...,
    machine_master_info=machine_master_info,
    ...
)

# After
final_results = create_new_results(
    ...,
    machine_mapper=machine_mapper,  # ← 변경
    ...
)
```

### 6.2 src/dag_management/__init__.py

#### 현재 코드 (라인 10-83)
```python
def create_complete_dag_system(
    sequence_seperated_order,
    linespeed,
    machine_master_info,
    aging_map=None
):
    machine_columns = machine_master_info[config.columns.MACHINE_CODE].values.tolist()

    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        ...,
        machine_columns=machine_columns
    )
```

#### 수정 후 코드
```python
def create_complete_dag_system(
    sequence_seperated_order,
    linespeed,
    machine_mapper,  # ← 변경: machine_master_info → machine_mapper
    aging_map=None
):
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        ...,
        machine_mapper=machine_mapper  # ← 변경
    )
```

### 6.3 src/dag_management/node_dict.py

#### 현재 코드 (라인 31-83)
```python
def create_machine_dict(sequence_seperated_order, linespeed, machine_columns, aging_nodes_dict=None):
    # ...
    for col in machine_columns:
        # ...

    machine_dict = {}
    for _, row in order_linespeed.iterrows():
        node_id = row[ID]
        machine_dict[node_id] = {}
        for idx, col in enumerate(machine_columns):  # ← 순서 의존
            processing_time = row[col]
            machine_dict[node_id][idx] = int(processing_time)
```

#### 수정 후 코드
```python
def create_machine_dict(sequence_seperated_order, linespeed, machine_mapper, aging_nodes_dict=None):
    # machine_mapper에서 순서 보장된 기계코드 리스트 추출
    machine_codes = machine_mapper.get_all_codes()

    # 순서 검증 (linespeed의 컬럼 순서와 일치하는지)
    linespeed_machine_cols = [col for col in linespeed.columns
                              if col not in [GITEM, OPERATION_CODE]]
    if not machine_mapper.validate_machine_order(linespeed_machine_cols):
        print("[WARNING] Machine column order mismatch detected!")

    # 처리시간 계산
    for col in machine_codes:
        # ... (기존 로직)

    # machine_dict 생성 (명시적 매핑)
    machine_dict = {}
    for _, row in order_linespeed.iterrows():
        node_id = row[ID]
        machine_dict[node_id] = {}

        for machine_code in machine_codes:
            machine_index = machine_mapper.code_to_index(machine_code)  # ← 명시적 매핑
            processing_time = row[machine_code]
            machine_dict[node_id][machine_index] = int(processing_time)
```

### 6.4 src/scheduler/__init__.py

#### 현재 코드 (라인 89-170)
```python
def run_scheduler_pipeline(
    dag_df,
    ...,
    machine_master_info,
    ...
):
    # code_to_index dict 생성
    code_to_index = dict(
        zip(
            machine_master_info[config.columns.MACHINE_CODE],
            machine_master_info[config.columns.MACHINE_INDEX],
        )
    )

    # machine_index_list 생성
    machine_index_list = (
        width_change_df[config.columns.MACHINE_CODE].map(code_to_index).tolist()
    )

    # merge
    width_change_df = pd.merge(
        width_change_df, machine_master_info,
        on=config.columns.MACHINE_CODE,
        how="left"
    )
```

#### 수정 후 코드
```python
def run_scheduler_pipeline(
    dag_df,
    ...,
    machine_mapper,  # ← 변경: machine_master_info → machine_mapper
    ...
):
    # machine_index_list 생성 (mapper 사용)
    machine_index_list = [
        machine_mapper.code_to_index(code)
        for code in width_change_df[config.columns.MACHINE_CODE]
    ]

    # merge (machine_master_info 사용)
    width_change_df = pd.merge(
        width_change_df,
        machine_mapper.get_master_info(),  # ← mapper에서 추출
        on=config.columns.MACHINE_CODE,
        how="left"
    )
```

### 6.5 src/new_results/__init__.py

#### 현재 코드 (라인 28-262)
```python
def create_new_results(
    raw_scheduling_result,
    merged_df,
    original_order,
    sequence_seperated_order,
    machine_master_info,
    base_date,
    scheduler
):
    # machine_mapping 생성
    machine_mapping = machine_master_info.set_index(
        config.columns.MACHINE_INDEX
    )[config.columns.MACHINE_CODE].to_dict()

    # code_to_name_mapping 생성
    code_to_name_mapping = machine_master_info.set_index(
        config.columns.MACHINE_CODE
    )[config.columns.MACHINE_NAME].to_dict()
```

#### 수정 후 코드
```python
def create_new_results(
    raw_scheduling_result,
    merged_df,
    original_order,
    sequence_seperated_order,
    machine_mapper,  # ← 변경: machine_master_info → machine_mapper
    base_date,
    scheduler
):
    # 매핑 딕셔너리 생성 제거 (mapper 사용)
    # machine_mapping, code_to_name_mapping 제거

    # MachineScheduleProcessor에 mapper 전달
    machine_proc = MachineScheduleProcessor(
        machine_mapper,  # ← 변경
        machine_schedule_df,
        result_cleaned,
        base_date,
        gap_analyzer=None
    )

    # 기계명 추가 (mapper 사용)
    machine_info[config.columns.MACHINE_NAME] = machine_info[
        config.columns.MACHINE_CODE
    ].map(machine_mapper.code_to_name)  # ← 변경
```

### 6.6 src/new_results/machine_detailed_analyzer.py

#### 현재 코드 (라인 11-187)
```python
class MachineDetailedAnalyzer:
    def __init__(self, scheduler, gap_analyzer, machine_master_info):
        self.machine_idx_to_code = machine_master_info.set_index(
            config.columns.MACHINE_INDEX
        )[config.columns.MACHINE_CODE].to_dict()

        self.machine_idx_to_name = machine_master_info.set_index(
            config.columns.MACHINE_INDEX
        )[config.columns.MACHINE_NAME].to_dict()
```

#### 수정 후 코드
```python
class MachineDetailedAnalyzer:
    def __init__(self, scheduler, gap_analyzer, machine_mapper):
        self.machine_mapper = machine_mapper  # ← 변경
        # 매핑 딕셔너리 생성 제거

    def analyze(self):
        for machine in self.scheduler.Machines:
            machine_idx = machine.Machine_index
            machine_code = self.machine_mapper.index_to_code(machine_idx)  # ← 변경
            machine_name = self.machine_mapper.index_to_name(machine_idx)  # ← 변경
```

### 6.7 src/results/machine_processor.py

#### 현재 코드 (라인 10-41)
```python
class MachineScheduleProcessor:
    def __init__(self, machine_mapping, machine_schedule_df, ...):
        self.machine_mapping = machine_mapping  # {0: 'C2010', 1: 'C2250', ...}

    def make_readable_result_file(self):
        self.machine_schedule_df[config.columns.MACHINE_INDEX] = \
            self.machine_schedule_df[config.columns.MACHINE_INDEX].map(self.machine_mapping)
```

#### 수정 후 코드
```python
class MachineScheduleProcessor:
    def __init__(self, machine_mapper, machine_schedule_df, ...):
        self.machine_mapper = machine_mapper  # ← 변경: mapping dict → mapper

    def make_readable_result_file(self):
        self.machine_schedule_df[config.columns.MACHINE_INDEX] = \
            self.machine_schedule_df[config.columns.MACHINE_INDEX].apply(
                self.machine_mapper.index_to_code  # ← 변경
            )
```

### 6.8 src/scheduler/scheduler.py (로깅 개선)

#### 현재 코드 (라인 141-206)
```python
def assign_operation(self, node_earliest_start, node_id, depth):
    # ...
    print(f"[LOG] 노드 {node_id}: 기계 {ideal_machine_index}에 할당")
```

#### 수정 후 코드
```python
def assign_operation(self, node_earliest_start, node_id, depth, machine_mapper=None):
    # ...
    if machine_mapper:
        machine_info_str = machine_mapper.format_machine_info(ideal_machine_index)
        print(f"[LOG] 노드 {node_id}: {machine_info_str}에 할당")
    else:
        print(f"[LOG] 노드 {node_id}: 기계 {ideal_machine_index}에 할당")
```

**참고**: `machine_mapper`를 Scheduler 초기화 시 저장하거나, 메서드 파라미터로 전달

---

## 7. 테스트 계획

### 7.1 단위 테스트 (MachineMapper)

#### 테스트 케이스

| 테스트명 | 내용 | 예상 결과 |
|---------|------|----------|
| `test_init_success` | 정상 초기화 | 성공 |
| `test_init_missing_columns` | 필수 컬럼 누락 | ValueError |
| `test_init_duplicate_index` | machineindex 중복 | ValueError |
| `test_init_duplicate_code` | machineno 중복 | ValueError |
| `test_index_to_code` | 0 → 'C2010' | 성공 |
| `test_index_to_name` | 0 → '1호기' | 성공 |
| `test_code_to_index` | 'C2010' → 0 | 성공 |
| `test_code_to_name` | 'C2010' → '1호기' | 성공 |
| `test_name_to_index` | '1호기' → 0 | 성공 |
| `test_get_all_codes` | ['C2010', 'C2250', ...] | 성공 |
| `test_validate_machine_order_success` | 순서 일치 | True |
| `test_validate_machine_order_fail` | 순서 불일치 | False |
| `test_format_machine_info` | "1호기 (C2010) [idx=0]" | 성공 |

#### 테스트 데이터

```python
# tests/test_machine_mapper.py
import pandas as pd
from src.utils.machine_mapper import MachineMapper

@pytest.fixture
def sample_machine_master_info():
    return pd.DataFrame({
        'machineindex': [0, 1, 2, 3, 4],
        'machineno': ['C2010', 'C2250', 'C2260', 'C2280', 'C2320'],
        'machinename': ['1호기', '25호기', '26호기', '28호기', '32호기']
    })

def test_init_success(sample_machine_master_info):
    mapper = MachineMapper(sample_machine_master_info)
    assert mapper.get_machine_count() == 5
    assert mapper.index_to_code(0) == 'C2010'
    assert mapper.index_to_name(0) == '1호기'
```

### 7.2 통합 테스트

#### 테스트 시나리오

1. **전체 파이프라인 실행**
   - 입력: `data/input/생산계획 입력정보.xlsx`
   - 기대: 오류 없이 완료
   - 검증: `data/output/result.xlsx` 생성 확인

2. **결과 일치성 검증**
   - 기존 코드 실행 결과와 신규 코드 실행 결과 비교
   - 검증 항목:
     - makespan 동일
     - 각 노드의 할당 기계 동일
     - 시작/종료 시간 동일
     - 지각 일수 동일

3. **로그 출력 검증**
   - 기계명이 포함된 로그 출력 확인
   - 예: "1호기 (C2010) [idx=0]에 할당"

### 7.3 성능 테스트

#### 측정 지표

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| 초기화 시간 | - | < 10ms | `time.time()` |
| 매핑 조회 시간 | - | < 1μs | `timeit` |
| 전체 실행 시간 | - | ± 5% 이내 | `time.time()` |
| 메모리 사용량 | - | ± 10% 이내 | `memory_profiler` |

#### 성능 테스트 코드

```python
import timeit
from src.utils.machine_mapper import MachineMapper

def test_mapping_performance():
    mapper = MachineMapper(sample_machine_master_info)

    # 매핑 조회 시간 측정
    time_index_to_code = timeit.timeit(lambda: mapper.index_to_code(0), number=100000)
    assert time_index_to_code < 0.1  # 100k 조회 < 100ms

    time_code_to_index = timeit.timeit(lambda: mapper.code_to_index('C2010'), number=100000)
    assert time_code_to_index < 0.1
```

---

## 8. 롤백 계획

### 8.1 버전 관리

#### Git 브랜치 전략

```bash
# 현재 브랜치
main

# 작업 브랜치 생성
git checkout -b feature/machine-mapper

# 개발 진행
git add .
git commit -m "Phase 1: MachineMapper 클래스 구현"
git commit -m "Phase 2: DAG Creation 수정"
git commit -m "Phase 3: Scheduler 수정"
git commit -m "Phase 4: Results 수정"

# 테스트 통과 후 병합
git checkout main
git merge feature/machine-mapper
```

#### 롤백 시나리오

**시나리오 1: 통합 테스트 실패**
```bash
# 작업 브랜치로 이동
git checkout feature/machine-mapper

# 문제 수정 후 재테스트
git add .
git commit -m "Fix: 통합 테스트 오류 수정"
```

**시나리오 2: 성능 저하 발견**
```bash
# 작업 브랜치 삭제 및 main으로 복귀
git checkout main
git branch -D feature/machine-mapper
```

**시나리오 3: 프로덕션 배포 후 문제 발견**
```bash
# 이전 커밋으로 되돌리기
git revert <commit-hash>

# 또는 강제 롤백
git reset --hard <previous-commit-hash>
```

### 8.2 백업 계획

#### 작업 전 백업

```bash
# 현재 상태 태그 생성
git tag -a v3.0-before-machine-mapper -m "Backup before MachineMapper refactoring"

# 코드 복사본 생성
cp -r python_engine python_engine_backup_20251112
```

#### 복구 절차

1. Git 태그로 복구:
   ```bash
   git checkout v3.0-before-machine-mapper
   ```

2. 파일 복사본으로 복구:
   ```bash
   cp -r python_engine_backup_20251112/* python_engine/
   ```

---

## 9. 리스크 관리

### 9.1 예상 리스크

| 리스크 | 발생 확률 | 영향도 | 대응 방안 |
|--------|----------|--------|----------|
| 순서 불일치 오류 | 중 | 높음 | 순서 검증 로직 내장 |
| 성능 저하 | 낮음 | 중간 | 매핑 딕셔너리 캐싱 |
| 기존 코드 호환성 문제 | 중 | 높음 | 단계별 테스트 |
| 디버깅 어려움 | 낮음 | 낮음 | 로깅 강화 |
| 테스트 커버리지 부족 | 중 | 중간 | 단위 테스트 작성 |

### 9.2 위험 완화 전략

1. **순서 불일치 오류**
   - `validate_machine_order()` 메서드로 자동 검증
   - 불일치 시 명확한 에러 메시지 출력

2. **성능 저하**
   - 매핑 딕셔너리는 초기화 시 한 번만 생성 (캐싱)
   - `timeit`으로 성능 측정 후 최적화

3. **호환성 문제**
   - 단계별 테스트 (Phase 2 각 단계마다 실행)
   - 기존 결과와 비교 검증

4. **디버깅 어려움**
   - `format_machine_info()` 메서드로 가독성 있는 로그
   - 각 단계마다 로그 출력

5. **테스트 커버리지**
   - 단위 테스트 13개 이상 작성
   - 통합 테스트 3개 시나리오 작성

---

## 10. 성공 기준

### 10.1 기능 요구사항

- [ ] MachineMapper 클래스가 모든 매핑 기능 제공
- [ ] 6개 파일의 중복 매핑 로직 제거 완료
- [ ] 순서 검증 로직 정상 동작
- [ ] 기존 코드와 동일한 스케줄링 결과 생성

### 10.2 비기능 요구사항

- [ ] 전체 실행 시간 5% 이내 증가
- [ ] 메모리 사용량 10% 이내 증가
- [ ] 단위 테스트 커버리지 90% 이상
- [ ] 통합 테스트 3개 시나리오 모두 통과

### 10.3 품질 요구사항

- [ ] 코드 중복도 20% 이상 감소
- [ ] 로그 가독성 향상 (기계명 포함)
- [ ] 문서화 완료 (docstring, README)
- [ ] 코드 리뷰 통과

---

## 11. 일정 계획

### 11.1 상세 일정

| Phase | 작업 내용 | 소요 시간 | 담당자 | 마감일 |
|-------|----------|----------|--------|--------|
| Phase 0 | Excel 입력 파일 및 validation 수정 | 0.5일 | - | D+0.5 |
| Phase 1 | MachineMapper 클래스 구현 | 1일 | - | D+1.5 |
| Phase 2.1 | main.py, DAG Creation 수정 | 0.5일 | - | D+2 |
| Phase 2.2 | Scheduler 수정 | 0.5일 | - | D+2.5 |
| Phase 2.3 | Results 수정 | 0.5일 | - | D+3 |
| Phase 2.4 | 로깅 개선 | 0.5일 | - | D+3.5 |
| Phase 3 | 통합 테스트 및 검증 | 1일 | - | D+4.5 |
| Phase 4 | 문서화 및 정리 | 0.5일 | - | D+5 |

**총 소요 시간**: 약 5일 (작업일 기준)

### 11.2 마일스톤

- **M0 (D+0.5)**: ✅ machine_master_info.xlsx 파일 생성 완료 (2025-11-12)
- **M1 (D+1.5)**: MachineMapper 클래스 완성 및 단위 테스트 통과
- **M2 (D+3.5)**: 모든 파일 수정 완료
- **M3 (D+4.5)**: 통합 테스트 통과 및 성능 검증
- **M4 (D+5)**: 문서화 완료 및 배포 준비

---

## 12. 참고 자료

### 12.1 관련 파일

- `config.py:38-41` - 기계 식별자 정의
- `src/validation/production_preprocessor.py:185-203` - machine_master_info 생성
- `src/dag_management/node_dict.py:31-83` - machine_dict 생성
- `src/scheduler/__init__.py:89-170` - 스케줄러 초기화
- `src/new_results/__init__.py:28-262` - 결과 처리

### 12.2 참고 문서

- `CLAUDE.md` - 프로젝트 아키텍처 설명
- `readme.md` - 시스템 개요 및 실행 방법
- `입출력정보.md` - 데이터 구조 설명 (삭제됨, 필요 시 복구)

### 12.3 디자인 패턴

- **Singleton Pattern** (선택사항): MachineMapper를 전역 싱글톤으로 관리
- **Factory Pattern**: machine_mapper 생성을 팩토리 함수로 관리
- **Facade Pattern**: 복잡한 매핑 로직을 단순한 인터페이스로 제공

---

## 13. 승인 체크리스트

### 13.1 기술 검토

- [ ] 아키텍처 설계 검토 완료
- [ ] 성능 영향 분석 완료
- [ ] 보안 영향 분석 완료 (해당 없음)
- [ ] 테스트 계획 검토 완료

### 13.2 비즈니스 검토

- [ ] 비용 분석 완료 (개발 시간 4.5일)
- [ ] 일정 검토 완료
- [ ] 리스크 평가 완료
- [ ] ROI 분석 완료 (유지보수성 향상)

### 13.3 최종 승인

- [ ] 프로젝트 오너 승인
- [ ] 기술 리더 승인
- [ ] 개발 시작 승인

---

## 부록 A: Excel 파일 생성 예시

### A.1 machine_master_info.xlsx 파일 생성 (✅ 완료)

**실행**:
```bash
python create_machine_master.py
```

**생성 결과**:
```
[완료] 기계 마스터 정보가 별도 파일로 저장되었습니다:
        → data/input/machine_master_info.xlsx

[최종 결과]
    machineindex machineno  machinename
0              0     A2020      AgNW2호기
1              1     C2010    염색1호기_WIN
2              2     C2250   염색25호기_WIN
3              3     C2260   염색26호기_WIN
4              4     C2270   염색27호기_WIN
5              5     D2280   염색28호기_DSP
6              6     O2310   염색31호기_DSP
7              7     O2320   염색32호기_DSP
8              8     O2340   염색34호기_DSP
9              9     O2360   염색36호기_DSP
10            10     O2510  염색51호기(이상혁)
11            11     O2590   염색59호기_DSP

[통계]
- 총 기계 수: 12대
- machineindex 범위: 0 ~ 11
- machineno 중복: 0개
- machineindex 중복: 0개
```

### A.2 기계 순서 커스터마이징 예시

**시나리오**: 특정 기계를 우선순위로 배치하고 싶은 경우

```python
import pandas as pd

# 1. 기존 파일 로드
machine_file = "data/input/machine_master_info.xlsx"
machine_master_info = pd.read_excel(machine_file, sheet_name="machine_master")

# 2. 원하는 순서로 machineindex 재할당
priority_machines = ['C2010', 'C2250', 'C2260']  # 우선순위 기계
other_machines = [m for m in machine_master_info['machineno'] if m not in priority_machines]

# 3. 순서 재정렬
ordered_machines = priority_machines + other_machines
machine_master_info['machineindex'] = machine_master_info['machineno'].map(
    {code: idx for idx, code in enumerate(ordered_machines)}
)
machine_master_info = machine_master_info.sort_values(by='machineindex').reset_index(drop=True)

# 4. 별도 파일로 저장
with pd.ExcelWriter(machine_file, engine='openpyxl') as writer:
    machine_master_info.to_excel(writer, sheet_name='machine_master', index=False)

print(f"[완료] 기계 순서 재배치 완료")
print(machine_master_info.head())
```

## 부록 B: 코드 예시

### B.1 MachineMapper 사용 예시

```python
# 초기화
from src.utils.machine_mapper import MachineMapper

machine_mapper = MachineMapper(machine_master_info)

# 매핑 사용
machine_code = machine_mapper.index_to_code(0)  # 'C2010'
machine_name = machine_mapper.index_to_name(0)  # '1호기'
machine_index = machine_mapper.code_to_index('C2010')  # 0

# 포맷팅
info_str = machine_mapper.format_machine_info(0)  # "1호기 (C2010) [idx=0]"
print(f"작업을 {info_str}에 할당했습니다.")

# 순서 검증
machine_codes = ['C2010', 'C2250', 'C2260']
if not machine_mapper.validate_machine_order(machine_codes):
    print("[ERROR] 기계 순서 불일치!")
```

### A.2 기존 코드 vs 신규 코드 비교

#### 기존 코드
```python
# main.py
machine_master_info = processed_data['machine_master_info']
machine_columns = machine_master_info['machineno'].tolist()

# dag_management/node_dict.py
for idx, col in enumerate(machine_columns):
    machine_dict[node_id][idx] = processing_time

# scheduler/__init__.py
code_to_index = dict(zip(machine_master_info['machineno'],
                         machine_master_info['machineindex']))

# new_results/__init__.py
machine_mapping = machine_master_info.set_index('machineindex')['machineno'].to_dict()
```

#### 신규 코드
```python
# main.py
machine_mapper = MachineMapper(machine_master_info)

# dag_management/node_dict.py
for machine_code in machine_mapper.get_all_codes():
    machine_index = machine_mapper.code_to_index(machine_code)
    machine_dict[node_id][machine_index] = processing_time

# scheduler/__init__.py
machine_index = machine_mapper.code_to_index(machine_code)

# new_results/__init__.py
machine_code = machine_mapper.index_to_code(machine_index)
```

**개선점**:
- 중복 제거
- 명시적 매핑
- 일관된 인터페이스

---

## 부록 C: 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| v1.0 | 2025-11-12 | Claude | 초안 작성 (Excel 시트 추가 방식) |
| v1.1 | 2025-11-12 | Claude | 별도 Excel 파일 방식으로 변경 (machine_master_info.xlsx) |
| v1.2 | 2025-11-12 | Claude | Phase 0 완료 반영 (파일 생성 완료) |
| v1.3 | 2025-11-12 | Claude | **중요 수정**: machine_master_info는 validation 대상에서 제외 |

---

## 📌 체크리스트 (구현 시작 전)

### Phase 0 시작 전 확인사항
- [x] 기존 Excel 파일 백업 완료
- [x] linespeed_df에서 기계 목록 추출 스크립트 작성 완료 (create_machine_master.py)
- [x] machine_master_info.xlsx 파일 생성 완료 (12대 기계)

### Phase 1 시작 전 확인사항
- [x] machine_master_info.xlsx 파일 생성 완료
- [ ] main.py에서 별도 파일 로딩 성공 확인
- [ ] MachineMapper 클래스 설계 검토 완료

### Phase 2 시작 전 확인사항
- [ ] MachineMapper 단위 테스트 통과
- [ ] Git 브랜치 생성 완료
- [ ] 롤백 계획 숙지

### Phase 3 시작 전 확인사항
- [ ] 모든 코드 수정 완료
- [ ] 컴파일 오류 없음
- [ ] 통합 테스트 시나리오 준비

### Phase 4 시작 전 확인사항
- [ ] 통합 테스트 통과
- [ ] 성능 기준 충족
- [ ] 문서화 완료

---

**문서 작성 완료** ✅
