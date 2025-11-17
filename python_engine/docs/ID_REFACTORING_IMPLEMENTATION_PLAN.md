# ID 리팩토링 구현 계획서

## 📋 변경 요약

### 리스크 답변 반영 결과

✅ **모든 Critical 리스크 해소됨**

- 하위 호환성 유지 불필요 → ID를 PROCESS_ID로 완전 대체
- ID 파싱 로직 없음 → 안전하게 순서 변경 가능
- 테스트 데이터 자동 생성 → 문제 없음

✅ **구현 전략 단순화**

- 3단계 Phase → **2단계 Phase**로 축소
- 하위 호환 로직 제거 → 코드 간결화
- 예상 작업 기간: **9-13일 → 6-8일**로 단축

---

## 🎯 변경 목표

### AS-IS (현재)

```python
ID = "{GITEM}_{OPERATION_CODE}_{FABRIC_WIDTH}_{CHEMICAL_LIST}_{COMBINATION_CLASSIFICATION}_M{MONTH}"

예시: "A001_OP1_1500_CHEM1_1_M5"
```

### TO-BE (변경 후)

```python
PRODUCT_ID = "{GITEM}_{FABRIC_WIDTH}_{COMBINATION_CLASSIFICATION}_M{MONTH}"
PROCESS_ID = "{PRODUCT_ID}_{OPERATION_CODE}_{CHEMICAL_LIST}"

예시:
  PRODUCT_ID = "A001_1500_1_M5"
  PROCESS_ID = "A001_1500_1_M5_OP1_CHEM1"
```

**핵심 변경:**

- ID 컬럼 완전 제거 (PROCESS_ID로 대체)
- PRODUCT_ID 신규 추가 (제품 레벨 그룹화용)

---

## 📂 수정 파일 목록

### Phase 1: 핵심 ID 생성 로직 (4개 파일)

#### 1. `config.py`

**변경 내용:** 컬럼명 정의 수정

```python
@dataclass
class ColumnNames:
    # === ID System v2.0 ===
    PRODUCT_ID: str = "PRODUCT_ID"   # 제품 레벨 식별자 (NEW)
    PROCESS_ID: str = "PROCESS_ID"   # 공정 레벨 식별자 (ID 대체)

    # Legacy (제거됨)
    # ID: str = "ID"  # DEPRECATED: PROCESS_ID로 대체
```

#### 2. `src/order_sequencing/sequence_preprocessing.py`

**변경 내용:** ID 생성 로직 변경 (31-37줄, 66줄)

**⚠️ 최적화 적용:** ID를 **한 번만** 생성 (자세한 내용은 `ID_GENERATION_OPTIMIZED_PLAN.md` 참조)

**변경 전:**

```python
# Line 31-37: 월 정보 없이 ID 생성
paired_order[config.columns.ID] = (
    str(gitem) + "_" +
    paired_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" +
    paired_order[config.columns.CHEMICAL_LIST].astype(str) + "_" +
    paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str)
)

# Line 66: 월 정보 추가하면서 ID 재생성
sequence_seperated_order[config.columns.ID] = (
    sequence_seperated_order[config.columns.ID].astype(str) +
    "_M" +
    sequence_seperated_order[config.columns.DUE_DATE].dt.month.astype(str)
)
```

**변경 후 (최적화):**

```python
# Line 31-37: PRODUCT_ID, PROCESS_ID 한 번에 생성 (월 포함!) ✅
# paired_order에 이미 DUE_DATE가 있으므로 처음부터 월 포함

# PRODUCT_ID 생성 (월 포함)
paired_order[config.columns.PRODUCT_ID] = (
    str(gitem) + "_" +
    paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" +
    paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str) + "_M" +
    paired_order[config.columns.DUE_DATE].dt.month.astype(str)
)

# PROCESS_ID 생성 (PRODUCT_ID 기반)
paired_order[config.columns.PROCESS_ID] = (
    paired_order[config.columns.PRODUCT_ID] + "_" +
    paired_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    paired_order[config.columns.CHEMICAL_LIST].astype(str)
)

# Line 66: 월 정보가 이미 포함되어 있으므로 로직 제거! ✅
# (기존 월 추가 코드 삭제)

# OPERATION_ORDER 타입 변환만 유지
sequence_seperated_order[config.columns.OPERATION_ORDER] = (
    sequence_seperated_order[config.columns.OPERATION_ORDER].astype(int)
)
```

**최적화 효과:**

- ✅ ID 생성 횟수: 2회 → 1회 (50% 감소)
- ✅ 코드 라인: -5줄
- ✅ 데이터 일관성: 안전
- ✅ 유지보수성: 향상

#### 3. `src/dag_management/dag_dataframe.py`

**변경 내용:** DAG 생성 로직 수정

**Line 75 변경:**

```python
# 변경 전
dag_data.append({
    'ID': node,
    config.columns.DEPTH: depth,
    'CHILDREN': ', '.join(children) if children else ''
})

# 변경 후
dag_data.append({
    config.columns.PROCESS_ID: node,  # ID → PROCESS_ID
    config.columns.DEPTH: depth,
    'CHILDREN': ', '.join(children) if children else ''
})
```

**Line 124-132 변경 (make_process_table):**

```python
# 변경 전
df_exploded['operation_col'] = df_exploded[config.columns.OPERATION_ORDER].astype(str) + config.columns.PROCESS_ID_SUFFIX

pivot_df = df_exploded.pivot_table(
    index=[config.columns.PO_NO],
    columns='operation_col',
    values=config.columns.ID,  # ← ID 사용
    aggfunc='first'
).reset_index()

# 변경 후
df_exploded['operation_col'] = df_exploded[config.columns.OPERATION_ORDER].astype(str) + config.columns.PROCESS_ID_SUFFIX

pivot_df = df_exploded.pivot_table(
    index=[config.columns.PO_NO],
    columns='operation_col',
    values=config.columns.PROCESS_ID,  # ← PROCESS_ID 사용
    aggfunc='first'
).reset_index()
```

#### 4. `src/dag_management/node_dict.py`

**변경 내용:** 노드 딕셔너리에 PRODUCT_ID 추가

**Line 17-26 변경:**

```python
# 변경 전
def create_opnode_dict(sequence_seperated_order):
    opnode_dict = {}
    for _, row in sequence_seperated_order.iterrows():
        opnode_dict[row[config.columns.ID]] = {
            "OPERATION_ORDER": row[config.columns.OPERATION_ORDER],
            "OPERATION_CODE": row[config.columns.OPERATION_CODE],
            ...
        }
    return opnode_dict

# 변경 후
def create_opnode_dict(sequence_seperated_order):
    opnode_dict = {}
    for _, row in sequence_seperated_order.iterrows():
        process_id = row[config.columns.PROCESS_ID]

        opnode_dict[process_id] = {
            "PRODUCT_ID": row[config.columns.PRODUCT_ID],  # ← 신규 추가
            "OPERATION_ORDER": row[config.columns.OPERATION_ORDER],
            "OPERATION_CODE": row[config.columns.OPERATION_CODE],
            "OPERATION_CLASSIFICATION": row[config.columns.OPERATION_CLASSIFICATION],
            "FABRIC_WIDTH": row[config.columns.FABRIC_WIDTH],
            "CHEMICAL_LIST": chemical_tuple,
            "PRODUCTION_LENGTH": row[config.columns.PRODUCTION_LENGTH],
            "SELECTED_CHEMICAL": None,
        }
    return opnode_dict
```

---

### Phase 2: DAG 및 결과 처리 (7개 파일)

#### 5. `src/dag_management/dag_manager.py`

**변경 내용:** DAG DataFrame 컬럼명 변경

**Line 47-49 변경:**

```python
# 변경 전
dag_df['CHILDREN'] = dag_df['CHILDREN'].apply(self.parse_list)
for idx, row in dag_df.iterrows():
    node = DAGNode(row['ID'], row[config.columns.DEPTH])

# 변경 후
dag_df['CHILDREN'] = dag_df['CHILDREN'].apply(self.parse_list)
for idx, row in dag_df.iterrows():
    node = DAGNode(row[config.columns.PROCESS_ID], row[config.columns.DEPTH])  # ID → PROCESS_ID
```

**Line 58 변경:**

```python
# 변경 전
self.nodes[row['ID']] = node

# 변경 후
self.nodes[row[config.columns.PROCESS_ID]] = node
```

**Line 62 변경:**

```python
# 변경 전
current = self.nodes[row['ID']]

# 변경 후
current = self.nodes[row[config.columns.PROCESS_ID]]
```

**Line 169 변경 (to_dataframe):**

```python
# 변경 전
row = {
    'id': node.id,
    ...
}

# 변경 후
row = {
    config.columns.PROCESS_ID: node.id,  # 'id' → PROCESS_ID
    ...
}
```

#### 6. `src/results/merge_processor.py`

**변경 내용:** 병합 로직에 PRODUCT_ID 활용

**Line 35-40 변경:**

```python
# 변경 전
for process in process_list:
    temp = self.sequence_seperated_order[[config.columns.ID] + merge_cols].copy()
    result = result.merge(temp, how='left', left_on=process, right_on=config.columns.ID)
    result.drop(columns=[config.columns.ID], inplace=True)

# 변경 후
for process in process_list:
    temp = self.sequence_seperated_order[
        [config.columns.PROCESS_ID, config.columns.PRODUCT_ID] + merge_cols
    ].copy()
    result = result.merge(temp, how='left', left_on=process, right_on=config.columns.PROCESS_ID)
    result.drop(columns=[config.columns.PROCESS_ID], inplace=True)
```

**Line 64-69 변경 (create_process_detail_result):**

```python
# 변경 전
seq_dict = {}
for _, row in sequence_seperated_order.iterrows():
    node_id = row[config.columns.ID]
    if node_id not in seq_dict:
        seq_dict[node_id] = row.to_dict()

# 변경 후
seq_dict = {}
for _, row in sequence_seperated_order.iterrows():
    process_id = row[config.columns.PROCESS_ID]
    if process_id not in seq_dict:
        seq_dict[process_id] = row.to_dict()
```

**Line 71-95 변경:**

```python
# 변경 전
for _, row in final_result_df.iterrows():
    node_id = row['id']
    ...

# 변경 후
for _, row in final_result_df.iterrows():
    process_id = row[config.columns.PROCESS_ID]

    # Aging 여부 확인
    machine_info = scheduler.machine_dict.get(process_id)
    is_aging = machine_info and set(machine_info.keys()) == {-1}

    # sequence_seperated_order에서 추가 정보 가져오기
    if is_aging and '_AGING' in process_id:
        parent_process_id = process_id.replace('_AGING', '')
        extra_info = seq_dict.get(parent_process_id, {})
    else:
        extra_info = seq_dict.get(process_id, {})

    results.append({
        config.columns.PO_NO: extra_info.get(config.columns.PO_NO, ''),
        config.columns.PRODUCT_ID: extra_info.get(config.columns.PRODUCT_ID, ''),  # ← 신규
        config.columns.GITEM: extra_info.get(config.columns.GITEM, ''),
        config.columns.DEPTH: row[config.columns.DEPTH],
        config.columns.PROCESS_ID: process_id,  # ← ID → PROCESS_ID
        config.columns.OPERATION_CODE: extra_info.get(config.columns.OPERATION_CODE, ''),
        'is_aging': is_aging,
        ...
    })
```

#### 7. `src/results/machine_processor.py`

**변경 내용:** PROCESS_ID 사용

```python
# ID 컬럼을 PROCESS_ID로 변경하는 패턴 전체 적용
# 예: df['ID'] → df[config.columns.PROCESS_ID]
```

#### 8. `src/new_results/performance_metrics.py`

**변경 내용:** PRODUCT_ID 기반 주문별 집계 추가

**신규 함수 추가:**

```python
def calculate_product_level_metrics(process_detail_df):
    """
    PRODUCT_ID 기준 주문별 성과 지표 계산

    Returns:
        dict: {
            'product_makespan': 주문별 총 생산시간
            'product_lateness': 주문별 지각 일수
            'product_count': 총 주문 수
        }
    """
    product_metrics = process_detail_df.groupby(config.columns.PRODUCT_ID).agg({
        'node_end': 'max',  # 주문의 마지막 공정 종료시간 = makespan
        config.columns.DUE_DATE: 'first',
        config.columns.PO_NO: 'first'
    }).reset_index()

    product_metrics['makespan'] = product_metrics['node_end']
    product_metrics['lateness_days'] = (
        (product_metrics['node_end'] - product_metrics[config.columns.DUE_DATE].dt.timestamp()) / 86400
    ).clip(lower=0)

    return {
        'product_makespan': product_metrics[['PRODUCT_ID', 'makespan']].to_dict('records'),
        'product_lateness': product_metrics[['PRODUCT_ID', 'lateness_days']].to_dict('records'),
        'product_count': len(product_metrics)
    }
```

#### 9. `src/new_results/order_lateness_reporter.py`

**변경 내용:** PRODUCT_ID 기반 지각 분석

```python
# PRODUCT_ID로 그룹화하여 주문별 지각 분석
lateness_by_product = df.groupby(config.columns.PRODUCT_ID).agg({
    'node_end': 'max',
    config.columns.DUE_DATE: 'first'
}).reset_index()
```

#### 10. `src/new_results/__init__.py`

**변경 내용:** PROCESS_ID 사용, PRODUCT_ID 기반 집계 추가

```python
# create_new_results 함수 내부에서 PRODUCT_ID 기반 성과 지표 추가
product_metrics = calculate_product_level_metrics(process_detail_df)
final_results['product_metrics'] = product_metrics
```

#### 11. `docs/CLAUDE.md`

**변경 내용:** ID 체계 설명 업데이트

```markdown
## 🔑 ID 체계 (v2.0)

### PRODUCT_ID (제품 레벨 식별자)

- 형식: `{GITEM}_{FABRIC_WIDTH}_{COMBINATION_CLASSIFICATION}_M{MONTH}`
- 예시: `"A001_1500_1_M5"`
- 용도: 주문/제품 레벨 그룹화 및 집계

### PROCESS_ID (공정 레벨 식별자)

- 형식: `{PRODUCT_ID}_{OPERATION_CODE}_{CHEMICAL_LIST}`
- 예시: `"A001_1500_1_M5_OP1_CHEM1"`
- 용도: 각 공정 노드의 유일 식별자 (기존 ID 역할)

### 관계
```

PRODUCT_ID (1) ─── (N) PROCESS_ID

```

### 생성 위치
- `src/order_sequencing/sequence_preprocessing.py:31-66`
```

---

## 🧪 테스트 계획

### 단위 테스트 추가

**파일:** `tests/test_id_system.py` (신규 생성)

```python
import pytest
import pandas as pd
from config import config
from src.order_sequencing.sequence_preprocessing import process_operations_by_category

class TestIDSystem:
    """ID 시스템 v2.0 테스트"""

    def test_product_id_format(self):
        """PRODUCT_ID 형식 검증"""
        # Given: 샘플 데이터
        sample_data = pd.DataFrame({
            config.columns.GITEM: ['A001'],
            config.columns.FABRIC_WIDTH: [1500],
            config.columns.COMBINATION_CLASSIFICATION: [1],
            config.columns.DUE_DATE: [pd.Timestamp('2025-05-15')]
        })

        # When: PRODUCT_ID 생성 (함수 호출)
        # ... (실제 함수 호출 로직)

        # Then: 형식 검증
        expected = "A001_1500_1_M5"
        assert product_id == expected

    def test_process_id_format(self):
        """PROCESS_ID 형식 검증"""
        # Given
        product_id = "A001_1500_1_M5"
        operation_code = "OP1"
        chemical_list = "CHEM1"

        # When
        process_id = f"{product_id}_{operation_code}_{chemical_list}"

        # Then
        expected = "A001_1500_1_M5_OP1_CHEM1"
        assert process_id == expected

    def test_process_id_uniqueness(self):
        """PROCESS_ID 유일성 검증"""
        # Given: sequence_seperated_order 생성
        # ...

        # Then: 중복 없음 확인
        assert df[config.columns.PROCESS_ID].nunique() == len(df)

    def test_product_to_process_mapping(self):
        """PRODUCT_ID → PROCESS_ID 관계 검증"""
        # Given
        product_id = "A001_1500_1_M5"

        # When: 해당 제품의 모든 공정 조회
        processes = df[df[config.columns.PRODUCT_ID] == product_id]

        # Then: 모든 PROCESS_ID가 PRODUCT_ID로 시작
        for process_id in processes[config.columns.PROCESS_ID]:
            assert process_id.startswith(product_id + "_")

    def test_aging_node_naming(self):
        """Aging 노드 명명 규칙 검증"""
        # Given
        parent_process_id = "A001_1500_1_M5_OP1_CHEM1"

        # When
        aging_node_id = f"{parent_process_id}_AGING"

        # Then
        expected = "A001_1500_1_M5_OP1_CHEM1_AGING"
        assert aging_node_id == expected
```

### 통합 테스트

**파일:** `tests/test_integration_id_refactoring.py` (신규 생성)

```python
def test_full_pipeline_with_new_id_system():
    """전체 파이프라인 실행 - 신규 ID 시스템"""

    # 1. 데이터 로딩 및 전처리
    # 2. 주문 시퀀스 생성 → PRODUCT_ID, PROCESS_ID 생성 확인
    # 3. DAG 생성 → PROCESS_ID 사용 확인
    # 4. 스케줄링 실행 → 정상 동작 확인
    # 5. 결과 후처리 → PRODUCT_ID 집계 확인

    # 검증 사항:
    assert 'PRODUCT_ID' in sequence_seperated_order.columns
    assert 'PROCESS_ID' in sequence_seperated_order.columns
    assert 'ID' not in sequence_seperated_order.columns  # ID 제거 확인
    assert dag_df.columns.tolist() == ['PROCESS_ID', config.columns.DEPTH, 'CHILDREN']
```

---

## 📅 구현 일정

### Phase 1: 핵심 ID 생성 (3-4일)

**Day 1:**

- ✅ `config.py` 수정
- ✅ `sequence_preprocessing.py` 수정
- ✅ 단위 테스트 작성 및 실행

**Day 2:**

- ✅ `dag_dataframe.py` 수정
- ✅ `node_dict.py` 수정
- ✅ 통합 테스트 (DAG 생성까지)

**Day 3-4:**

- ✅ 버그 수정 및 검증
- ✅ Phase 1 완료 확인

### Phase 2: DAG 및 결과 처리 (3-4일)

**Day 5:**

- ✅ `dag_manager.py` 수정
- ✅ `merge_processor.py` 수정

**Day 6:**

- ✅ `machine_processor.py` 수정
- ✅ `performance_metrics.py` 수정 (PRODUCT_ID 집계 추가)

**Day 7:**

- ✅ `order_lateness_reporter.py` 수정
- ✅ `new_results/__init__.py` 수정

**Day 8:**

- ✅ 전체 통합 테스트
- ✅ 문서 업데이트 (`CLAUDE.md`)
- ✅ 최종 검증 및 배포

---

## ✅ 검증 체크리스트

### Phase 1 완료 조건

- [ ] `config.py`에 PRODUCT_ID, PROCESS_ID 추가됨
- [ ] sequence_seperated_order에 PRODUCT_ID, PROCESS_ID 컬럼 존재
- [ ] PRODUCT*ID 형식: `{GITEM}*{WIDTH}\_{COMB}\_M{MONTH}`
- [ ] PROCESS*ID 형식: `{PRODUCT_ID}*{OP}\_{CHEM}`
- [ ] PROCESS_ID 유일성 보장됨
- [ ] DAG DataFrame에 PROCESS_ID 컬럼 사용
- [ ] opnode_dict에 PRODUCT_ID 필드 추가

### Phase 2 완료 조건

- [ ] DAGGraphManager가 PROCESS_ID 사용
- [ ] merge_processor가 PRODUCT_ID, PROCESS_ID 사용
- [ ] PRODUCT_ID 기반 주문별 집계 함수 추가
- [ ] Aging 노드 명명: `{PROCESS_ID}_AGING`
- [ ] 전체 파이프라인 정상 실행
- [ ] 결과 Excel 파일 정상 생성
- [ ] `CLAUDE.md` 업데이트 완료

### 최종 검증

- [ ] ID 컬럼 완전 제거 확인 (grep으로 검색)
- [ ] 모든 테스트 통과
- [ ] 성능 저하 없음 확인
- [ ] git commit 및 push

---

## 🚀 즉시 시작 가능한 명령어

### 1. 백업 생성

```bash
git checkout -b feature/id-refactoring-v2
git add .
git commit -m "Backup before ID refactoring"
```

### 2. Phase 1 시작

```bash
# config.py 수정 (수동)
# sequence_preprocessing.py 수정 (수동)

# 테스트 실행
python -m pytest tests/test_id_system.py -v
```

### 3. 진행 상황 확인

```bash
# ID 컬럼 사용 여부 확인
grep -r "config.columns.ID\]" src/
grep -r "\"ID\"" src/ | grep -v "PRODUCT_ID\|PROCESS_ID"
```

### 4. 최종 검증

```bash
# 전체 파이프라인 실행
python main.py

# 결과 확인
ls -lh data/output/
```

---

## 📊 예상 결과

### 변경 전

```python
sequence_seperated_order.columns:
['pono', 'gitemno', 'proccode', 'ID', 'fabric_width', ...]

ID 예시: "A001_OP1_1500_CHEM1_1_M5"
```

### 변경 후

```python
sequence_seperated_order.columns:
['pono', 'gitemno', 'proccode', 'PRODUCT_ID', 'PROCESS_ID', 'fabric_width', ...]

PRODUCT_ID 예시: "A001_1500_1_M5"
PROCESS_ID 예시: "A001_1500_1_M5_OP1_CHEM1"
```

### 새로운 집계 기능

```python
# 주문별 makespan
df.groupby('PRODUCT_ID')['node_end'].max()

# 주문별 지각 분석
df.groupby('PRODUCT_ID').agg({
    'node_end': 'max',
    'duedate': 'first'
})
```

---

## 🎯 최종 목표

**구현 완료 시 달성되는 것:**

1. ✅ **명확한 계층 구조**

   - PRODUCT_ID (제품) → PROCESS_ID (공정)

2. ✅ **확장 가능한 집계**

   - 주문별 성과 지표 자동 계산

3. ✅ **깔끔한 코드베이스**

   - 하위 호환 로직 없음
   - ID 컬럼 완전 제거

4. ✅ **유지보수성 향상**
   - 명확한 명명 규칙
   - 의미 있는 구조

**예상 작업 기간:** 6-8일
**리스크:** Low (모든 Critical 리스크 해소됨)
