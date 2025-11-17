# results 모듈 독립화 및 results 제거 계획서

## 📋 목표

**`results` 모듈을 완전히 제거**하고 `results`만 사용하도록 리팩토링

---

## 🔍 현재 상황 분석

### results가 results에서 참조 중인 모듈 (4개)

| 모듈                                              | 위치                                   | 역할                                            | 라인 수 | 복잡도      |
| ------------------------------------------------- | -------------------------------------- | ----------------------------------------------- | ------- | ----------- |
| **DataCleaner**                                   | `src/results/data_cleaner.py`          | 가짜 작업(depth -1) 제거 및 makespan 계산       | ~90     | ⭐ 낮음     |
| **MachineProcessor**                              | `src/results/machine_processor.py`     | 호기 정보 생성 (기계 스케줄 → 가독성 있는 결과) | ~230    | ⭐⭐ 중간   |
| **MergeProcessor + create_process_detail_result** | `src/results/merge_processor.py`       | 주문-공정 병합, Aging 포함 상세 공정 결과 생성  | ~155    | ⭐⭐ 중간   |
| **GanttChartGenerator**                           | `src/results/gantt_chart_generator.py` | 간트차트 PNG 생성                               | ~130    | ⭐⭐⭐ 높음 |

**총 라인 수: ~605줄**

---

## 🎯 해결 전략: results로 완전 통합 ✅

### 전략: 필요한 모듈을 results로 복사하고 results 제거

**장점:**

- `results` 모듈 완전 제거 가능
- `results` 완전 독립
- 의존성 명확화 (외부 참조 없음)
- 불필요한 레거시 코드 제거

**단점:**

- 코드 복사 필요 (~605줄)
- 하지만 results를 어차피 안 쓸 거라면 중복이 아님

**최종 구조:**

```
src/
├── results/                   # 최종 결과 모듈 (독립 완료)
│   ├── __init__.py               # 메인 파이프라인
│   ├── data_cleaner.py           # results에서 복사 ✅
│   ├── merge_processor.py        # results에서 복사 ✅
│   ├── machine_info_builder.py   # results의 MachineProcessor 기능 복사 후 수정 ✅
│   ├── gantt_chart_generator.py  # results에서 복사 ✅
│   ├── performance_metrics.py    # 기존 (유지)
│   ├── machine_detailed_analyzer.py  # 기존 (유지)
│   ├── order_lateness_reporter.py    # 기존 (유지)
│   └── simplified_gap_analyzer.py    # 기존 (유지)
│
├── results/                       # ❌ 삭제 예정
│   └── (모든 파일 삭제)
│
├── validation/                    # 유지
├── order_sequencing/             # 유지
├── dag_management/               # 유지
└── scheduler/                    # 유지
```

---

## 🚀 실행 계획 (3단계)

### Phase 1: results 모듈을 results로 복사 (4개 파일)

**작업 항목:**

#### 1-1. DataCleaner 복사

```bash
# 파일 복사
cp src/results/data_cleaner.py src/results/data_cleaner.py
```

**수정 사항:**

- 임포트 경로 확인 (config만 사용하므로 수정 불필요)
- 파일 상단 docstring 업데이트

---

#### 1-2. MergeProcessor 복사

```bash
# 파일 복사
cp src/results/merge_processor.py src/results/merge_processor.py
```

**수정 사항:**

- 임포트 경로 확인 (config만 사용하므로 수정 불필요)
- 파일 상단 docstring 업데이트

---

#### 1-3. GanttChartGenerator 복사

```bash
# 파일 복사
cp src/results/gantt_chart_generator.py src/results/gantt_chart_generator.py
```

**수정 사항:**

- 임포트 경로 확인 (matplotlib, numpy만 사용)
- `gap_analyzer` 파라미터 처리:
  - `results`는 `SimplifiedGapAnalyzer` 사용
  - `results`의 `ScheduleGapAnalyzer`와 인터페이스 호환성 확인

---

#### 1-4. MachineInfoBuilder 생성 (MachineProcessor 기반)

**작업:**

- `src/results/machine_processor.py` 참고하여 `src/results/machine_info_builder.py` 생성
- `MachineScheduleProcessor` 로직 복사 후 단순화

**클래스 구조:**

```python
class MachineInfoBuilder:
    """호기 정보 생성 전용 클래스 (results용)"""

    def __init__(self, machine_mapper, base_date):
        self.machine_mapper = machine_mapper
        self.base_date = base_date

    def build_machine_info(self, machine_schedule_df):
        """
        기본 호기 정보 생성

        ⭐ 로직: MachineScheduleProcessor.make_readable_result_file() 복사
        """
        pass

    def decorate_with_process_details(self, machine_info, process_detail_df):
        """
        공정 상세 정보로 호기 정보 장식

        ⭐ 로직: MachineScheduleProcessor.machine_info_decorate() 복사
        """
        pass

    def add_gitem_names(self, machine_info, original_order):
        """
        GITEM명 매핑 및 추가 컬럼 생성

        ⭐ 로직: results/__init__.py:118-129 복사
        """
        pass

    def create_complete_machine_info(
        self,
        machine_schedule_df,
        process_detail_df,
        original_order
    ):
        """호기 정보 전체 파이프라인 (원스톱)"""
        machine_info = self.build_machine_info(machine_schedule_df)
        machine_info = self.decorate_with_process_details(machine_info, process_detail_df)
        machine_info = self.add_gitem_names(machine_info, original_order)
        return machine_info
```

**주의사항:**

- `gap_analyzer` 의존성 제거 (SimplifiedGapAnalyzer는 별도 사용)
- `MachineProcessor` 클래스는 복사 안 함 (불필요 - 단순 wrapper)

---

### Phase 2: results/**init**.py 임포트 수정

**작업 항목:**

1. 임포트 경로 변경:

   ```python
   # ❌ 기존 (results 참조)
   from src.results.data_cleaner import DataCleaner
   from src.results.machine_processor import MachineProcessor
   from src.results.merge_processor import MergeProcessor, create_process_detail_result
   from src.results.gantt_chart_generator import GanttChartGenerator

   # ✅ 신규 (results 내부 모듈 참조)
   from .data_cleaner import DataCleaner
   from .merge_processor import MergeProcessor, create_process_detail_result
   from .gantt_chart_generator import GanttChartGenerator
   from .machine_info_builder import MachineInfoBuilder
   ```

2. `create_results()` 함수 로직 수정:

   ```python
   # ❌ 기존 (87-108행)
   from src.results.machine_processor import MachineScheduleProcessor
   machine_proc = MachineScheduleProcessor(
       machine_mapping,
       machine_schedule_df,
       result_cleaned,
       base_date,
       gap_analyzer=None
   )
   machine_info = machine_proc.make_readable_result_file()
   machine_info = machine_proc.machine_info_decorate(process_detail_df)

   # ✅ 신규
   machine_builder = MachineInfoBuilder(machine_mapper, base_date)
   machine_info = machine_builder.create_complete_machine_info(
       machine_schedule_df,
       process_detail_df,
       original_order  # 이미 있는 변수
   )
   ```

3. GITEM명 매핑 로직 제거:

   ```python
   # ❌ 기존 (110-129행) - 중복 로직 제거
   order_with_names = original_order[[...]]
   machine_info = pd.merge(machine_info, order_with_names, ...)
   machine_info[config.columns.OPERATION] = ...
   machine_info[config.columns.WORK_TIME] = ...

   # ✅ 신규 - 이미 MachineInfoBuilder.add_gitem_names()에서 처리됨
   # 위 코드 블록 삭제
   ```

---

### Phase 3: results 모듈 완전 제거 및 정리

**작업 항목:**

#### 3-1. results 모듈 사용처 확인

```bash
# results 모듈을 참조하는 곳이 있는지 확인
grep -r "from src.results" src/ --exclude-dir=results
grep -r "import src.results" src/ --exclude-dir=results
```

**예상 결과:**

- `main.py`에서 `create_results` 사용 가능성 확인
- 다른 모듈에서 사용 여부 확인

---

#### 3-2. main.py 수정 (results → results)

**확인 사항:**

- `main.py`가 `results.create_results()` 사용 중인지 확인
- `results.create_results()` 사용 중이면 수정 불필요

**수정 (필요 시):**

```python
# ❌ 기존
from src.results import create_results
results = create_results(...)

# ✅ 신규
from src.results import create_results
results = create_results(...)
```

---

#### 3-3. results 디렉토리 삭제

**작업:**

```bash
# Git으로 관리 중이므로 git rm 사용
git rm -r src/results/

# 또는 수동 삭제 후
rm -rf src/results/
```

**삭제할 파일 목록:**

- `src/results/__init__.py`
- `src/results/data_cleaner.py`
- `src/results/machine_processor.py`
- `src/results/merge_processor.py`
- `src/results/gantt_chart_generator.py`
- `src/results/gap_analyzer.py`
- `src/results/late_processor.py`

**주의:**

- `gap_analyzer.py`, `late_processor.py`는 `results`에서 사용 안 함
- 삭제 전 내용 확인 (혹시 필요한 로직 있는지)

---

#### 3-4. 최종 검증

```bash
# 1. results 참조 완전 제거 확인
grep -r "src.results" src/
# 결과: 아무것도 안 나와야 함 ✅

# 2. results 임포트 확인
grep -r "from \.data_cleaner" src/results/
grep -r "from \.merge_processor" src/results/
grep -r "from \.gantt_chart_generator" src/results/
grep -r "from \.machine_info_builder" src/results/
# 결과: __init__.py에서만 나와야 함 ✅

# 3. main.py 실행 테스트
python main.py
# 결과: 정상 실행 및 Excel 파일 생성 확인 ✅
```

---

## 📊 변경 사항 요약

### 파일 변경 사항

| 작업     | 파일                                                                            | 상태                            |
| -------- | ------------------------------------------------------------------------------- | ------------------------------- |
| **복사** | `src/results/data_cleaner.py` → `src/results/data_cleaner.py`                   | ✅ 신규                         |
| **복사** | `src/results/merge_processor.py` → `src/results/merge_processor.py`             | ✅ 신규                         |
| **복사** | `src/results/gantt_chart_generator.py` → `src/results/gantt_chart_generator.py` | ✅ 신규                         |
| **생성** | `src/results/machine_info_builder.py`                                           | ✅ 신규 (MachineProcessor 기반) |
| **수정** | `src/results/__init__.py`                                                       | 🔧 임포트 경로 변경             |
| **삭제** | `src/results/` (전체 디렉토리)                                                  | ❌ 제거                         |

---

### 코드 라인 변경 요약

| 항목                | Before   | After    | 차이          |
| ------------------- | -------- | -------- | ------------- |
| **results 라인 수** | ~600줄   | ~1200줄  | +600줄 (복사) |
| **results 라인 수** | ~700줄   | 0줄      | -700줄 (삭제) |
| **전체 코드베이스** | ~15000줄 | ~14900줄 | -100줄 (순감) |

**순감 이유:**

- `results`의 일부 모듈 (`gap_analyzer.py`, `late_processor.py`)은 `results`에서 사용 안 함
- 중복 로직 정리

---

## 🧪 테스트 계획

### Phase 1 테스트 (파일 복사 후)

```python
# 각 모듈 임포트 테스트
from src.results.data_cleaner import DataCleaner
from src.results.merge_processor import MergeProcessor, create_process_detail_result
from src.results.gantt_chart_generator import GanttChartGenerator
from src.results.machine_info_builder import MachineInfoBuilder

print("✅ 모든 모듈 임포트 성공")
```

### Phase 2 테스트 (임포트 수정 후)

```python
# results 전체 파이프라인 테스트
from src.results import create_results

# main.py에서 호출하는 것과 동일하게 테스트
results = create_results(
    raw_scheduling_result,
    merged_df,
    original_order,
    sequence_seperated_order,
    machine_mapper,
    base_date,
    scheduler
)

# 5개 시트 데이터 확인
assert 'machine_info' in results
assert 'performance_summary' in results
assert 'machine_detailed_performance' in results
assert 'order_lateness_report' in results
assert 'gap_analysis' in results

print("✅ results 파이프라인 정상 작동")
```

### Phase 3 테스트 (results 삭제 후)

```bash
# 1. results 임포트 시도 (실패해야 정상)
python -c "from src.results import create_results"
# 예상 결과: ModuleNotFoundError ✅

# 2. main.py 전체 실행
python main.py
# 예상 결과: 정상 실행 + Excel 파일 생성 ✅

# 3. 생성된 Excel 파일 검증
ls -lh "data/output/0829 스케줄링결과.xlsx"
# 예상 결과: 파일 존재 + 5개 시트 확인 ✅
```

---

## 📋 상세 구현 가이드

### 1. machine_info_builder.py 구현 세부사항

**목표:**

- `MachineScheduleProcessor`의 핵심 로직만 추출
- `gap_analyzer` 의존성 제거 (SimplifiedGapAnalyzer는 별도 사용)

**구현 방법:**

#### Step 1: build_machine_info() 구현

```python
def build_machine_info(self, machine_schedule_df):
    """
    ⭐ 참고: src/results/machine_processor.py:31-45
    """
    df = machine_schedule_df.copy()

    # 1. MACHINE_NAME 추가 (code → name 매핑)
    machine_mapping = {
        code: self.machine_mapper.code_to_name(code)
        for code in self.machine_mapper.get_all_codes()
    }
    df[config.columns.MACHINE_NAME] = df[config.columns.MACHINE_CODE].map(machine_mapping)

    # 2. 할당 작업 분리 (tuple → 별도 컬럼)
    df[[config.columns.OPERATION_ORDER, config.columns.PROCESS_ID]] = pd.DataFrame(
        df[config.columns.ALLOCATED_WORK].tolist(),
        index=df.index
    )

    # 3. 필요한 컬럼만 선택
    machine_info = df[[
        config.columns.MACHINE_CODE,
        config.columns.MACHINE_NAME,
        config.columns.WORK_START_TIME,
        config.columns.WORK_END_TIME,
        config.columns.OPERATION_ORDER,
        config.columns.PROCESS_ID
    ]].copy()

    # 4. 시간 변환 (30분 단위 → datetime)
    machine_info[config.columns.WORK_START_TIME] = (
        self.base_date +
        pd.to_timedelta(machine_info[config.columns.WORK_START_TIME] * config.constants.TIME_MULTIPLIER, unit='m')
    )
    machine_info[config.columns.WORK_END_TIME] = (
        self.base_date +
        pd.to_timedelta(machine_info[config.columns.WORK_END_TIME] * config.constants.TIME_MULTIPLIER, unit='m')
    )

    return machine_info
```

#### Step 2: decorate_with_process_details() 구현

```python
def decorate_with_process_details(self, machine_info, process_detail_df):
    """
    ⭐ 참고: src/results/machine_processor.py:47-122
    """
    machine_info = machine_info.copy()

    # 각 작업(PROCESS_ID)에 대해 상세 정보 조회
    po_no_list = []
    gitem_list = []
    width_list = []
    length_list = []
    chemical_list = []
    duedate_list = []

    for idx, row in machine_info.iterrows():
        process_id = row[config.columns.PROCESS_ID]

        # process_detail_df에서 해당 작업 필터링
        filtered = process_detail_df[
            process_detail_df[config.columns.PROCESS_ID] == process_id
        ]

        if filtered.empty:
            # Aging 노드이거나 매칭 실패
            po_no_list.append([])
            gitem_list.append([])
            width_list.append([])
            length_list.append([])
            chemical_list.append([])
            duedate_list.append([])
            continue

        # 각 컬럼별로 리스트 추출
        po_no_list.append(filtered[config.columns.PO_NO].tolist())
        gitem_list.append(filtered[config.columns.GITEM].tolist())
        width_list.append(filtered[config.columns.FABRIC_WIDTH].tolist())
        length_list.append(filtered[config.columns.PRODUCTION_LENGTH].tolist())
        chemical_list.append(filtered[config.columns.CHEMICAL_LIST].tolist())
        duedate_list.append(filtered[config.columns.DUE_DATE].tolist())

    # 리스트 정리 함수 (헬퍼)
    def unique_or_single(lst):
        if not lst:
            return None
        unique_vals = list(dict.fromkeys([x for x in lst if pd.notna(x)]))
        return unique_vals[0] if len(unique_vals) == 1 else (unique_vals or None)

    def timestamps_to_dates(lst):
        if not lst:
            return []
        return [
            ts.strftime('%Y-%m-%d') if isinstance(ts, pd.Timestamp) else str(ts)
            for ts in lst if pd.notna(ts)
        ]

    # 컬럼 추가
    machine_info[config.columns.PO_NO] = po_no_list
    machine_info[config.columns.GITEM] = [unique_or_single(x) for x in gitem_list]
    machine_info[config.columns.FABRIC_WIDTH] = [unique_or_single(x) for x in width_list]
    machine_info[config.columns.PRODUCTION_LENGTH] = [unique_or_single(x) for x in length_list]
    machine_info[config.columns.CHEMICAL_LIST] = [unique_or_single(x) for x in chemical_list]
    machine_info[config.columns.DUE_DATE] = [timestamps_to_dates(sublist) for sublist in duedate_list]

    return machine_info
```

#### Step 3: add_gitem_names() 구현

```python
def add_gitem_names(self, machine_info, original_order):
    """
    ⭐ 참고: src/results/__init__.py:111-129
    """
    # GITEM명 매핑
    order_with_names = original_order[[
        config.columns.GITEM,
        config.columns.GITEM_NAME
    ]].drop_duplicates()

    machine_info = pd.merge(
        machine_info,
        order_with_names,
        on=config.columns.GITEM,
        how='left'
    )

    # 추가 컬럼 생성
    machine_info[config.columns.OPERATION] = (
        machine_info[config.columns.PROCESS_ID].str.split('_').str[1]
    )
    machine_info[config.columns.WORK_TIME] = (
        machine_info[config.columns.WORK_END_TIME] -
        machine_info[config.columns.WORK_START_TIME]
    )

    return machine_info
```

---

## ⚠️ 리스크 및 대응 방안

### 리스크 1: 복사 시 임포트 경로 누락

**대응:**

- 각 파일 복사 후 즉시 임포트 테스트
- `python -c "from src.results.xxx import yyy"` 실행 확인

### 리스크 2: results 삭제 후 main.py에서 오류

**대응:**

- `main.py`가 `create_results` 사용 중인지 사전 확인
- 사용 중이면 Phase 2에서 `create_results`로 변경

### 리스크 3: gap_analyzer 인터페이스 불일치

**대응:**

- `GanttChartGenerator`가 `SimplifiedGapAnalyzer`와 호환되는지 확인
- 필요 시 `GanttChartGenerator` 수정 (gap_analyzer 타입 체크 추가)

### 리스크 4: 기존 로직 누락

**대응:**

- 복사 전 각 파일의 다른 모듈 의존성 확인
- `grep -r "from \." src/results/` 실행하여 내부 참조 확인

---

## 📅 예상 소요 시간

| Phase         | 작업 내용                           | 예상 시간      |
| ------------- | ----------------------------------- | -------------- |
| Phase 1-1     | DataCleaner 복사                    | 10분           |
| Phase 1-2     | MergeProcessor 복사                 | 10분           |
| Phase 1-3     | GanttChartGenerator 복사            | 15분           |
| Phase 1-4     | MachineInfoBuilder 구현             | 45분           |
| Phase 2       | results 임포트 수정                 | 20분           |
| Phase 3-1~3-2 | results 사용처 확인 및 main.py 수정 | 15분           |
| Phase 3-3     | results 디렉토리 삭제               | 5분            |
| Phase 3-4     | 최종 검증                           | 15분           |
| 테스트        | 전체 통합 테스트                    | 30분           |
| **합계**      |                                     | **약 2.5시간** |

---

## ✅ 완료 체크리스트

### Phase 1: 파일 복사 및 생성

- [ ] `src/results/data_cleaner.py` 복사
- [ ] `src/results/merge_processor.py` 복사
- [ ] `src/results/gantt_chart_generator.py` 복사
- [ ] `src/results/machine_info_builder.py` 생성
  - [ ] `MachineInfoBuilder` 클래스 정의
  - [ ] `build_machine_info()` 구현
  - [ ] `decorate_with_process_details()` 구현
  - [ ] `add_gitem_names()` 구현
  - [ ] `create_complete_machine_info()` 구현
- [ ] 각 파일 임포트 테스트

### Phase 2: results 수정

- [ ] `__init__.py` 임포트 경로 수정
- [ ] `create_results()` 로직 업데이트
  - [ ] `MachineScheduleProcessor` 제거
  - [ ] `MachineInfoBuilder` 사용
  - [ ] 중복 로직 제거 (GITEM명 매핑)
- [ ] Phase 2 테스트 (파이프라인 정상 작동)

### Phase 3: results 제거

- [ ] results 사용처 확인 (`grep` 실행)
- [ ] `main.py` 확인 및 수정 (필요 시)
- [ ] `src/results/` 디렉토리 삭제
- [ ] 최종 검증
  - [ ] results 임포트 실패 확인
  - [ ] main.py 실행 성공 확인
  - [ ] Excel 파일 생성 확인

### 문서 업데이트

- [ ] `CLAUDE.md` 업데이트 (results 제거 명시)
- [ ] `README.md` 업데이트 (필요 시)

---

## 🎯 최종 목표 검증

**독립성 검증:**

```bash
# results 참조 완전 제거 확인
grep -r "from src.results" src/
grep -r "import src.results" src/

# 결과: 아무것도 안 나와야 성공 ✅
```

**동작 검증:**

```bash
# main.py 실행 → 5개 시트 Excel 생성 확인
python main.py

# 생성된 파일 확인
ls -lh "data/output/0829 스케줄링결과.xlsx"
```

**결과 비교:**

- 기존 `results` 사용 시 결과 (백업)
- 신규 `results` 사용 시 결과
- 두 Excel 파일 비교 (데이터 일치 여부)

---

## 🔄 롤백 계획 (문제 발생 시)

```bash
# Git으로 관리 중이므로 Phase별 커밋 후 롤백 가능

# Phase 1 롤백
git reset --hard HEAD~1  # Phase 1 커밋 취소

# Phase 2 롤백
git reset --hard HEAD~1  # Phase 2 커밋 취소

# Phase 3 롤백
git reset --hard HEAD~1  # Phase 3 커밋 취소

# 특정 커밋으로 롤백
git log --oneline  # 커밋 해시 확인
git reset --hard <commit-hash>
```

**권장 커밋 메시지:**

- Phase 1: `refactor: copy results modules to results`
- Phase 2: `refactor: update results imports and remove results dependency`
- Phase 3: `refactor: remove results module completely`

---

## 📚 참고 자료

- `src/results/machine_processor.py`: MachineInfoBuilder 구현 참고
- `src/results/__init__.py`: 기존 호기 정보 생성 로직
- `CLAUDE.md`: 프로젝트 전체 구조 문서

---

## 📝 변경 이력

| 날짜       | 버전 | 작성자 | 변경 내용                             |
| ---------- | ---- | ------ | ------------------------------------- |
| 2025-11-17 | v2.0 | Claude | **results 완전 제거 전략**으로 재작성 |
| 2025-11-17 | v1.0 | Claude | 초안 (공통 모듈 분리 전략 - 폐기)     |

---

**문서 종료**
