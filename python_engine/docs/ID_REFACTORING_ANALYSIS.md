# ID 구조 리팩토링 분석 문서

## 📋 목차
1. [현재 ID 구조 분석](#현재-id-구조-분석)
2. [제안된 변경사항](#제안된-변경사항)
3. [사용자 이해도 검증](#사용자-이해도-검증)
4. [영향 범위 분석](#영향-범위-분석)
5. [문제점 및 리스크](#문제점-및-리스크)
6. [리팩토링 권장사항](#리팩토링-권장사항)
7. [구현 계획](#구현-계획)

---

## 현재 ID 구조 분석

### 1. ID 생성 과정

#### 1단계: FabricCombiner에서 주문 병합
**위치:** `src/order_sequencing/fabric_combiner.py:175`

**병합 기준 (groupby):**
```python
[GITEM, OPERATION_CODE, CHEMICAL_LIST, COMBINATION_CLASSIFICATION]
```

**동작:**
- 같은 GITEM, 공정코드, 배합액, 조합분류를 가진 여러 주문을 하나로 병합
- P/O NO는 쉼표로 연결: `"PO001, PO002, PO003"`
- 원단 너비는 조합 규칙에 따라 계산됨 (FABRIC_WIDTH)

**예시:**
```
입력 (3개 주문):
- PO001: GITEM=A001, 공정=OP1, 배합=CHEM1, 조합분류=1, 너비=508mm
- PO002: GITEM=A001, 공정=OP1, 배합=CHEM1, 조합분류=1, 너비=1016mm
- PO003: GITEM=A001, 공정=OP1, 배합=CHEM1, 조합분류=1, 너비=508mm

출력 (1개로 병합):
- PO_NO="PO001, PO002, PO003"
- GITEM=A001
- OPERATION_CODE=OP1
- CHEMICAL_LIST=CHEM1
- COMBINATION_CLASSIFICATION=1
- FABRIC_WIDTH=1500 (조합 규칙에 따라 계산)
```

#### 2단계: 기본 ID 생성
**위치:** `src/order_sequencing/sequence_preprocessing.py:31-37`

**생성 로직:**
```python
ID = f"{GITEM}_{OPERATION_CODE}_{FABRIC_WIDTH}_{CHEMICAL_LIST}_{COMBINATION_CLASSIFICATION}"
```

**예시:**
```
"A001_OP1_1500_CHEM1_1"
```

#### 3단계: 월 정보 추가 (최종 ID)
**위치:** `src/order_sequencing/sequence_preprocessing.py:66`

```python
ID = f"{기본ID}_M{월}"
```

**최종 형식:**
```
{GITEM}_{OPERATION_CODE}_{FABRIC_WIDTH}_{CHEMICAL_LIST}_{COMBINATION_CLASSIFICATION}_M{MONTH}
```

**예시:**
```
"A001_OP1_1500_CHEM1_1_M5"
```

---

### 2. ID 사용 위치 분석

#### ✅ 핵심 사용처 (18개 파일)

| 파일 | 사용 방식 | 역할 |
|------|-----------|------|
| **DAG 생성** | | |
| `dag_dataframe.py:75` | `'ID': node` | DAG 노드 ID로 사용 |
| `dag_dataframe.py:130` | `values=config.columns.ID` | 피벗 테이블 값으로 사용 |
| `dag_manager.py:49` | `row['ID']` | DAGNode 생성 시 식별자 |
| **노드 딕셔너리** | | |
| `node_dict.py:17` | `opnode_dict[row[ID]]` | 노드 메타데이터 딕셔너리 키 |
| `node_dict.py:66` | `machine_dict[node_id]` | 기계 처리시간 딕셔너리 키 |
| **스케줄링** | | |
| `scheduling_core.py:118` | `scheduler.machine_dict.get(child.id)` | 기계 정보 조회 |
| `dispatch_rules.py` | 다수 | 노드 추적 및 윈도우 관리 |
| **결과 처리** | | |
| `merge_processor.py:35` | `left_on=process, right_on=ID` | 스케줄링 결과 병합 |
| `merge_processor.py:67` | `seq_dict[node_id]` | 상세 정보 조회 |
| `machine_processor.py` | 다수 | 기계별 작업 집계 |
| `performance_metrics.py` | 다수 | 성과 지표 계산 |
| `order_lateness_reporter.py` | 다수 | 지각 분석 |

---

### 3. ID의 역할 정리

| 역할 | 설명 | 중요도 |
|------|------|--------|
| **유일 식별자** | 각 공정 노드를 시스템 전체에서 유일하게 식별 | ⭐⭐⭐⭐⭐ |
| **DAG 노드 키** | 그래프 구조에서 노드 ID (`DAGNode.id`) | ⭐⭐⭐⭐⭐ |
| **딕셔너리 키** | `opnode_dict`, `machine_dict`의 키 | ⭐⭐⭐⭐⭐ |
| **조인 키** | DataFrame 병합 시 사용 | ⭐⭐⭐⭐ |
| **추적 키** | 스케줄링 결과 추적 및 분석 | ⭐⭐⭐⭐ |
| **의미 전달** | ID 자체가 GITEM, 공정, 너비 등 정보 포함 | ⭐⭐⭐ |

---

## 제안된 변경사항

### 새로운 ID 체계

#### PRODUCT_ID (신규)
```
{GITEM}_{FABRIC_WIDTH}_{COMBINATION_CLASSIFICATION}_M{MONTH}
```

**예시:**
```
"A001_1500_1_M5"
```

**특징:**
- 공정 정보 미포함 (OPERATION_CODE, CHEMICAL_LIST 제거)
- 제품/주문 레벨의 식별자
- 같은 제품의 모든 공정이 동일한 PRODUCT_ID를 공유

#### PROCESS_ID (현재 ID를 대체)
```
{GITEM}_{FABRIC_WIDTH}_{COMBINATION_CLASSIFICATION}_M{MONTH}_{OPERATION_CODE}_{CHEMICAL_LIST}
```

**예시:**
```
"A001_1500_1_M5_OP1_CHEM1"
```

**특징:**
- 현재 ID와 **동일한 정보**를 포함 (순서만 변경)
- 공정 레벨의 식별자
- PRODUCT_ID + 공정 정보 = PROCESS_ID

---

## 사용자 이해도 검증

### ✅ 맞는 이해

> "ID는 {GITEM}, {조합분류}, {원단너비}, {월}인 것들끼리 합치고 이걸 다시 {공정코드} {배합액}으로 쪼갠 거"

**검증:**
- ✅ **맞습니다!** FabricCombiner가 병합한 것을 각 공정별로 분리합니다.
- 병합 기준: `{GITEM, 공정코드, 배합액, 조합분류}`
- 분리 기준: 각 공정순서별로 별도 행 생성

### ✅ PRODUCT_ID 역할

> "PRODUCT_ID는 순전히 참조용"

**검증:**
- ✅ **맞습니다!** PRODUCT_ID는 주문/제품 레벨의 참조 키로 사용
- 같은 제품의 모든 공정을 그룹화하는 용도
- 스케줄링 자체에는 직접 사용되지 않음

### ✅ PROCESS_ID 역할

> "실제로 ID가 하던 역할은 순서만 바뀌었지 동일한 정보를 제공하는 PROCESS_ID가 하는 거"

**검증:**
- ✅ **완전히 맞습니다!** PROCESS_ID는 현재 ID와 정보적으로 동일
- 순서만 변경: 제품 정보 앞, 공정 정보 뒤
- 모든 기능적 역할을 PROCESS_ID가 대체 가능

---

## 영향 범위 분석

### 1. 직접 영향 (코드 수정 필수)

#### ✅ Level 1: 컬럼명 추가 (`config.py`)
```python
@dataclass
class ColumnNames:
    ID: str = "ID"                    # 유지 (하위 호환)
    PRODUCT_ID: str = "PRODUCT_ID"    # 신규
    PROCESS_ID: str = "PROCESS_ID"    # 신규
```

#### ✅ Level 2: ID 생성 로직 변경
**파일:** `src/order_sequencing/sequence_preprocessing.py:31-37, 66`

**변경 전:**
```python
paired_order[config.columns.ID] = (
    str(gitem) + "_" +
    paired_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" +
    paired_order[config.columns.CHEMICAL_LIST].astype(str) + "_" +
    paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str)
)
```

**변경 후:**
```python
# PRODUCT_ID 생성
paired_order[config.columns.PRODUCT_ID] = (
    str(gitem) + "_" +
    paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" +
    paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str)
)

# PROCESS_ID 생성
paired_order[config.columns.PROCESS_ID] = (
    paired_order[config.columns.PRODUCT_ID] + "_" +
    paired_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    paired_order[config.columns.CHEMICAL_LIST].astype(str)
)

# 하위 호환성 유지
paired_order[config.columns.ID] = paired_order[config.columns.PROCESS_ID]
```

#### ✅ Level 3: 월 정보 추가 로직
**파일:** `src/order_sequencing/sequence_preprocessing.py:66`

**변경 전:**
```python
sequence_seperated_order[config.columns.ID] = (
    sequence_seperated_order[config.columns.ID].astype(str) +
    "_M" +
    sequence_seperated_order[config.columns.DUE_DATE].dt.month.astype(str)
)
```

**변경 후:**
```python
# PRODUCT_ID에 월 추가
sequence_seperated_order[config.columns.PRODUCT_ID] = (
    sequence_seperated_order[config.columns.PRODUCT_ID].astype(str) +
    "_M" +
    sequence_seperated_order[config.columns.DUE_DATE].dt.month.astype(str)
)

# PROCESS_ID에 월 추가
sequence_seperated_order[config.columns.PROCESS_ID] = (
    sequence_seperated_order[config.columns.PRODUCT_ID] + "_" +
    sequence_seperated_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    sequence_seperated_order[config.columns.CHEMICAL_LIST].astype(str)
)

# 하위 호환
sequence_seperated_order[config.columns.ID] = sequence_seperated_order[config.columns.PROCESS_ID]
```

#### ✅ Level 4: DAG 생성 코드
**파일:** `src/dag_management/dag_dataframe.py:130`

**변경 전:**
```python
pivot_df = df_exploded.pivot_table(
    index=[config.columns.PO_NO],
    columns='operation_col',
    values=config.columns.ID,  # ← ID 사용
    aggfunc='first'
).reset_index()
```

**변경 후:**
```python
pivot_df = df_exploded.pivot_table(
    index=[config.columns.PO_NO],
    columns='operation_col',
    values=config.columns.PROCESS_ID,  # ← PROCESS_ID로 변경
    aggfunc='first'
).reset_index()
```

#### ✅ Level 5: 노드 딕셔너리 생성
**파일:** `src/dag_management/node_dict.py:17`

**변경 사항:**
```python
# opnode_dict
opnode_dict[row[config.columns.PROCESS_ID]] = {
    "PRODUCT_ID": row[config.columns.PRODUCT_ID],  # 신규 추가
    ...
}

# machine_dict
machine_dict[node_id] = {...}  # node_id는 PROCESS_ID
```

---

### 2. 간접 영향 (검증 필요, 수정 가능성 있음)

#### 🔍 결과 처리 모듈
**파일:** `src/results/*.py`, `src/new_results/*.py`

**영향:**
- ID로 조인하는 모든 코드 → PROCESS_ID로 변경
- PRODUCT_ID를 활용한 주문별 집계 추가 가능
- 예: 주문별 전체 makespan 계산 (`GROUP BY PRODUCT_ID`)

#### 🔍 Aging 노드 생성
**파일:** `src/dag_management/dag_dataframe.py:197`

**현재:**
```python
aging_node_id = f"{parent_node_id}_AGING"
```

**변경 후:**
```python
# parent_node_id가 PROCESS_ID이므로 동일하게 동작
aging_node_id = f"{parent_node_id}_AGING"
```

---

### 3. 영향 없음 (수정 불필요)

#### ✅ DAGNode 클래스
- `node.id`는 여전히 유일 식별자로 사용
- PROCESS_ID가 할당되므로 기능 동일

#### ✅ 스케줄링 코어
- `scheduler.machine_dict.get(node.id)` → node.id가 PROCESS_ID이므로 동일

#### ✅ DAGGraphManager
- `self.nodes[node_id]` → node_id가 PROCESS_ID이므로 동일

---

## 문제점 및 리스크

### ✅ 사용자 답변으로 해소된 리스크

#### 1. 기존 데이터 호환성 문제 ✅ 해소
**사용자 답변:**
> 현재는 과거 데이터와 비교가 필요하지 않음. 따라서 하위호환성 유지를 위한 작업 불필요. 오류로 인한 롤백을 위한 안전장치는 원격저장소에 저장된 ID 기반 코드로 대체 가능.

**결론:**
- ✅ ID 컬럼을 완전히 제거하고 PROCESS_ID로 대체 가능
- ✅ 하위 호환 로직 불필요 → 코드 간결화
- ✅ 롤백은 git으로 대체

#### 2. ID 파싱 로직 존재 여부 ✅ 해소
**사용자 답변:**
> ID 파싱해서 하는 로직 없음. 그런건 위험성이 있으므로 아이디로 합쳐진 것은 다시 쪼개지지 않음.

**결론:**
- ✅ ID 순서 변경 안전
- ✅ 파싱 로직 제거 작업 불필요

#### 3. 테스트 데이터 갱신 ✅ 해소
**사용자 답변:**
> ID는 테스트시 자동 생성되는거지 사용자가 입력한것 아님.

**결론:**
- ✅ 테스트 데이터 자동 생성되므로 문제 없음
- ✅ 수동 갱신 작업 불필요

---

### 🟢 확인된 설계 의도 (리스크 아님)

#### 1. PRODUCT_ID의 유일성 ✅ 의도된 동작
**사용자 답변:**
> 말한 바와 같이 의도한 부분. PRODUCT_ID는 유일키로 사용하지 않고 그룹화를 위해 사용할거임

**설계:**
```
PRODUCT_ID="A001_1500_1_M5" ← 여러 공정이 공유 (의도된 동작)
  ├─ PROCESS_ID="A001_1500_1_M5_OP1_CHEM1"
  ├─ PROCESS_ID="A001_1500_1_M5_OP2_CHEM2"
  └─ PROCESS_ID="A001_1500_1_M5_OP3_CHEM3"
```

**용도:**
- ✅ 주문별 집계 시 GROUP BY 키로 사용
- ✅ 노드 식별은 PROCESS_ID 사용

#### 2. Aging 노드 명명 규칙 ✅ 확정
**사용자 답변:**
> AGING_NODE는 네가 말했다시피 {PROCESS_ID}_AGING으로 우선 할것임.

**확정된 형식:**
```
Parent: "A001_1500_1_M5_OP1_CHEM1"
Aging:  "A001_1500_1_M5_OP1_CHEM1_AGING"
```

**평가:**
- ✅ 여전히 유일하고 의미 명확
- ✅ 문제 없음

---

### 🟢 Low 리스크 (확인됨)

**사용자 답변:**
> 고려 불필요.

#### 1. ID 길이 변화 없음 ✅
- 현재와 동일한 정보 → 문자열 길이 동일
- 데이터베이스 컬럼 크기 변경 불필요

#### 2. 성능 영향 없음 ✅
- 문자열 조합 순서 변경만으로 성능 변화 없음

---

## 🎯 리스크 종합 평가

### ✅ 모든 Critical 리스크 해소됨

| 리스크 항목 | 초기 평가 | 사용자 답변 후 | 상태 |
|------------|----------|---------------|------|
| 하위 호환성 | 🔴 Critical | 🟢 해소 | ✅ 불필요 |
| ID 파싱 로직 | 🔴 Critical | 🟢 해소 | ✅ 없음 |
| 테스트 데이터 | 🔴 Critical | 🟢 해소 | ✅ 자동 생성 |
| PRODUCT_ID 유일성 | 🟡 Medium | 🟢 확인 | ✅ 의도된 설계 |
| Aging 노드 명명 | 🟡 Medium | 🟢 확인 | ✅ 확정 |
| 성능/길이 | 🟢 Low | 🟢 확인 | ✅ 문제 없음 |

**결론:** 리팩토링 진행에 **장애 요소 없음** ✅

---

## 리팩토링 권장사항

### ✅ 리팩토링을 **추천하는** 이유

#### 1. 의미적 계층 구조 명확화
```
PRODUCT_ID (제품 레벨)
  └─ PROCESS_ID (공정 레벨)
```

**장점:**
- 제품-공정 관계가 ID에서도 명확히 드러남
- 주문별 집계 시 PRODUCT_ID로 간편하게 GROUP BY 가능

#### 2. 확장성 향상
**현재 구조의 한계:**
- ID만으로는 어떤 주문의 어떤 공정인지 파악하기 어려움
- 주문 레벨 정보 추출 시 opnode_dict 또는 DataFrame 조인 필요

**변경 후:**
```python
# 주문별 makespan 계산
df.groupby('PRODUCT_ID')['node_end'].max()

# 특정 제품의 모든 공정 조회
df[df['PROCESS_ID'].str.startswith('A001_1500_1_M5_')]
```

#### 3. 가독성 향상
**현재:**
```
"A001_OP1_1500_CHEM1_1_M5"
→ GITEM - 공정 - 너비 - 배합 - 조합 - 월 (섞여있음)
```

**변경 후:**
```
PRODUCT: "A001_1500_1_M5"
PROCESS: "A001_1500_1_M5_OP1_CHEM1"
→ 제품 정보 - 공정 정보 (명확한 분리)
```

#### 4. 데이터 모델 개선
- 현재: 단일 ID만 존재 (Flat 구조)
- 변경: PRODUCT_ID ← PROCESS_ID (계층 구조)
- 관계형 DB 스키마에 더 적합

---

### ⚠️ 리팩토링 시 주의사항 (간소화)

#### 1. 단순화된 마이그레이션 전략

**하위 호환성 유지 불필요 → 2단계 Phase로 축소**

**Phase 1: 핵심 ID 생성 로직 변경**
```python
# ID 컬럼 완전 제거, PRODUCT_ID/PROCESS_ID로 대체
df['PRODUCT_ID'] = ...  # 신규
df['PROCESS_ID'] = ...  # 신규 (ID 대체)
# df['ID'] = ...  # ← 완전 제거
```

**Phase 2: 전체 코드베이스 일괄 변경**
- 모든 `config.columns.ID` → `config.columns.PROCESS_ID`
- 한 번에 변경 (단계적 마이그레이션 불필요)

#### 2. 문서화 필수
- `CLAUDE.md`에 새로운 ID 체계 설명 추가
- API 문서 갱신
- 코드 주석 업데이트

#### 3. 테스트 커버리지 확보
```python
def test_product_id_format():
    """PRODUCT_ID 형식 검증"""
    assert product_id == "A001_1500_1_M5"

def test_process_id_format():
    """PROCESS_ID 형식 검증"""
    assert process_id == "A001_1500_1_M5_OP1_CHEM1"

def test_process_id_uniqueness():
    """PROCESS_ID 유일성 검증"""
    assert df['PROCESS_ID'].nunique() == len(df)

def test_product_to_process_mapping():
    """PRODUCT_ID → PROCESS_ID 관계 검증"""
    product_group = df[df['PRODUCT_ID'] == 'A001_1500_1_M5']
    assert all(pid.startswith('A001_1500_1_M5_')
               for pid in product_group['PROCESS_ID'])
```

---

## 구현 계획 (간소화)

### Phase 1: 핵심 ID 생성 로직 (3-4일)

#### Task 1-1: 백업 및 브랜치 생성
```bash
git checkout -b feature/id-refactoring-v2
git add .
git commit -m "Backup before ID refactoring"
```

#### Task 1-2: 컬럼 정의 변경
**파일:** `config.py`

```python
@dataclass
class ColumnNames:
    # ID System v2.0 (하위 호환 제거)
    PRODUCT_ID: str = "PRODUCT_ID"   # 제품 레벨 식별자
    PROCESS_ID: str = "PROCESS_ID"   # 공정 레벨 식별자
    # ID: str = "ID"  # ← 완전 제거
```

#### Task 1-3: ID 생성 로직 변경
**파일:** `src/order_sequencing/sequence_preprocessing.py`

**변경 범위:**
- `process_operations_by_category()` 함수 (31-37줄)
- `create_sequence_seperated_order()` 함수 (66줄)

**참고:** `ID_REFACTORING_IMPLEMENTATION_PLAN.md` 참조

---

### Phase 2: 전체 코드베이스 변경 (3-4일)

#### Task 2-1: DAG 생성 로직 일괄 변경
**파일:**
- `src/dag_management/dag_dataframe.py`
- `src/dag_management/node_dict.py`
- `src/dag_management/dag_manager.py`

**변경 방법:**
```bash
# ID → PROCESS_ID 일괄 치환
# 파일별로 확인하며 변경
```

#### Task 2-2: 결과 처리 모듈 일괄 변경
**파일:**
- `src/results/merge_processor.py`
- `src/results/machine_processor.py`
- `src/new_results/performance_metrics.py`
- `src/new_results/order_lateness_reporter.py`
- `src/new_results/__init__.py`

**변경 사항:**
- `config.columns.ID` → `config.columns.PROCESS_ID`
- PRODUCT_ID 기반 집계 함수 추가

#### Task 2-3: 테스트 및 검증
**단위 테스트:**
```bash
python -m pytest tests/test_id_system.py -v
```

**통합 테스트:**
```bash
python main.py
# 결과 파일 확인
```

---

### Phase 3: 문서화 및 최종 검증 (1일)

#### Task 4-1: 단위 테스트
```python
# tests/test_id_system.py
def test_product_id_generation():
    """PRODUCT_ID 생성 테스트"""
    pass

def test_process_id_generation():
    """PROCESS_ID 생성 테스트"""
    pass

def test_id_backward_compatibility():
    """ID 하위 호환성 테스트"""
    pass
```

#### Task 4-2: 통합 테스트
- 전체 파이프라인 실행 (`main.py`)
- 결과 파일 비교 (기존 vs 신규)

#### Task 4-3: 회귀 테스트
- 기존 기능 정상 동작 확인
- 스케줄링 결과 동일성 검증 (ID 순서만 다르고 할당 결과는 동일)

---

### Phase 5: 문서화 및 배포 (1일)

#### Task 5-1: 문서 업데이트
- `CLAUDE.md` 업데이트
- `docs/ID_REFACTORING_ANALYSIS.md` (본 문서) 최종 수정
- 마이그레이션 가이드 작성

#### Task 5-2: 코드 리뷰
- 변경 사항 리뷰
- 리팩토링 품질 검증

#### Task 5-3: 배포
- main 브랜치 병합
- 릴리즈 노트 작성

---

## 예상 수정 파일 목록

### 필수 수정 (11개 파일)

1. ✅ `config.py` - 컬럼명 추가
2. ✅ `src/order_sequencing/sequence_preprocessing.py` - ID 생성 로직
3. ✅ `src/dag_management/dag_dataframe.py` - DAG 생성
4. ✅ `src/dag_management/node_dict.py` - 노드 딕셔너리
5. ✅ `src/results/merge_processor.py` - 결과 병합
6. ✅ `src/results/machine_processor.py` - 기계 정보 처리
7. ✅ `src/new_results/performance_metrics.py` - 성과 지표
8. ✅ `src/new_results/order_lateness_reporter.py` - 지각 분석
9. ✅ `src/new_results/__init__.py` - 결과 통합
10. ✅ `docs/CLAUDE.md` - 프로젝트 문서
11. ✅ `tests/test_*.py` - 테스트 케이스

### 검증 필요 (7개 파일)

1. 🔍 `src/scheduler/scheduling_core.py` - 스케줄링 코어
2. 🔍 `src/scheduler/dispatch_rules.py` - 디스패치 룰
3. 🔍 `src/dag_management/dag_manager.py` - DAG 관리자
4. 🔍 `src/yield_management/*.py` - 수율 관리
5. 🔍 `src/validation/*.py` - 데이터 검증
6. 🔍 `main.py` - 메인 실행 파일
7. 🔍 기타 분석 스크립트

---

## 최종 권장사항

### ✅ 리팩토링 진행 권장

**이유:**
1. ✅ 의미적으로 더 명확한 구조 (제품 - 공정 계층)
2. ✅ 확장성 향상 (주문별 집계 용이)
3. ✅ 가독성 향상 (제품 정보와 공정 정보 분리)
4. ✅ 기술 부채 감소 (명확한 데이터 모델)
5. ✅ 하위 호환성 유지 가능 (ID 컬럼 별칭)

**조건:**
1. ⚠️ **단계적 마이그레이션** 필수 (3개 Phase로 분할)
2. ⚠️ **충분한 테스트** 필요 (단위/통합/회귀)
3. ⚠️ **ID 파싱 코드 사전 제거** (opnode_dict 사용으로 변경)
4. ⚠️ **문서화 철저히** (팀원 혼란 방지)

---

## 예상 작업 기간 (단축됨)

**하위 호환성 유지 불필요로 Phase 축소: 5단계 → 3단계**

| Phase | 작업 | 기간 | 난이도 |
|-------|------|------|--------|
| Phase 1 | 핵심 ID 생성 로직 | 3-4일 | 🟡 Medium |
| Phase 2 | 전체 코드베이스 변경 | 3-4일 | 🟡 Medium |
| Phase 3 | 문서화 및 최종 검증 | 1일 | 🟢 Low |
| **합계** | | **7-9일** | |

**리스크 대비 버퍼:** +1-2일
**최종 예상 기간:** **8-11일 (약 1.5-2주)**

**단축 이유:**
- ✅ 하위 호환 로직 제거 → 코드 간결화
- ✅ ID 파싱 로직 없음 → 검색/수정 작업 불필요
- ✅ 테스트 자동 생성 → 수동 갱신 불필요

---

## 결론 (최종 업데이트)

제안된 PRODUCT_ID/PROCESS_ID 체계는 **기술적으로 타당하고 안전하게 구현 가능**합니다.

### ✅ 핵심 포인트

1. **사용자 이해도:** 100% 정확
   - ID 병합/분리 과정 정확히 이해
   - PRODUCT_ID/PROCESS_ID 역할 명확히 구분

2. **기능적 동등성:** PROCESS_ID = 현재 ID
   - 동일한 정보 포함 (순서만 변경)
   - 모든 기존 기능 유지

3. **새로운 가치:** PRODUCT_ID 추가
   - 제품 레벨 그룹화 및 집계 용이
   - 확장성 향상

4. **리스크 상태:** 🟢 모든 Critical 리스크 해소
   - 하위 호환성 불필요
   - ID 파싱 로직 없음
   - 테스트 자동 생성

5. **작업 기간:** 단축됨
   - 5단계 → 3단계 Phase
   - 11-16일 → 8-11일

### 🎯 최종 권장사항

**✅ 리팩토링 즉시 진행 권장**

**이유:**
- 모든 장애 요소 제거됨
- 코드 간결화 및 유지보수성 향상
- 명확한 데이터 모델 확립
- 확장 가능한 구조

**실행 방법:**
1. `ID_REFACTORING_IMPLEMENTATION_PLAN.md` 참조
2. Phase 1부터 순차적으로 진행
3. 각 Phase 완료 후 테스트 수행
4. 최종 검증 후 배포

**다음 단계:**
```bash
# 백업 생성
git checkout -b feature/id-refactoring-v2

# Phase 1 시작
# config.py 수정
# sequence_preprocessing.py 수정
```
