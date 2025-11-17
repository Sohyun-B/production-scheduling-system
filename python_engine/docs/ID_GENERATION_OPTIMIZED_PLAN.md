# ID 생성 로직 최적화 계획

## 🎯 문제점 분석

### 기존 계획의 문제 (비효율적)
```python
# ❌ Line 31-37: 월 정보 없이 생성
paired_order[PRODUCT_ID] = f"{GITEM}_{WIDTH}_{COMB}"
paired_order[PROCESS_ID] = f"{PRODUCT_ID}_{OP}_{CHEM}"

# ❌ Line 66: 월 추가하면서 재생성
sequence_seperated_order[PRODUCT_ID] = f"{PRODUCT_ID}_M{MONTH}"
sequence_seperated_order[PROCESS_ID] = f"{PRODUCT_ID}_{OP}_{CHEM}"  # 다시 생성!
```

**문제점:**
1. ❌ **비효율적**: 같은 ID를 두 번 생성
2. ❌ **위험성**: 중간에 데이터 변경되면 불일치 가능
3. ❌ **유지보수**: 로직이 두 곳에 분산

---

## ✅ 최적화된 방법

### 핵심 아이디어
**`paired_order`에 이미 `DUE_DATE`가 있다 → 처음부터 월 포함해서 생성!**

### 데이터 흐름 확인
```python
# FabricCombiner._assign_fabric_quantity (Line 201)
return pd.DataFrame([{
    ...
    config.columns.DUE_DATE: sub_df[config.columns.DUE_DATE].min(),  # ← DUE_DATE 포함!
    ...
}])

# ↓ 이 결과가 paired_order로 반환됨

# process_operations_by_category (Line 28-30)
paired_order = combiner.process(notnan_bh)  # ← DUE_DATE 이미 있음!
```

---

## 📝 최적화된 코드

### 변경 위치 1: `process_operations_by_category()` (Line 30-37)

#### 변경 전 (기존)
```python
paired_order[config.columns.ID] = (
    str(gitem) + "_" +
    paired_order[config.columns.OPERATION_CODE].astype(str) + "_" +
    paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" +
    paired_order[config.columns.CHEMICAL_LIST].astype(str) + "_" +
    paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str)
)
```

#### 변경 후 (최적화) ✅
```python
# PRODUCT_ID 생성 (월 정보 포함!)
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
```

**결과:**
```
PRODUCT_ID: "A001_1500_1_M5"
PROCESS_ID: "A001_1500_1_M5_OP1_CHEM1"
```

---

### 변경 위치 2: `create_sequence_seperated_order()` (Line 66-67)

#### 변경 전 (기존)
```python
# 해시 생성 후 ID에 추가
sequence_seperated_order[config.columns.ID] = (
    sequence_seperated_order[config.columns.ID].astype(str) +
    "_M" +
    sequence_seperated_order[config.columns.DUE_DATE].dt.month.astype(str)
)
sequence_seperated_order[config.columns.OPERATION_ORDER] = (
    sequence_seperated_order[config.columns.OPERATION_ORDER].astype(int)
)
```

#### 변경 후 (최적화) ✅
```python
# 월 정보가 이미 PRODUCT_ID/PROCESS_ID에 포함되어 있으므로
# ID 생성 로직 완전 제거!

# OPERATION_ORDER 타입 변환만 유지
sequence_seperated_order[config.columns.OPERATION_ORDER] = (
    sequence_seperated_order[config.columns.OPERATION_ORDER].astype(int)
)
```

---

## 🔄 전체 데이터 흐름 (최적화 후)

```
1. order_df (월별 분리됨)
   ↓
2. merge(order_df, operation_seperated_sequence)
   → merged (DUE_DATE 포함)
   ↓
3. FabricCombiner.process(merged)
   → paired_order (DUE_DATE 포함)
   ↓
4. process_operations_by_category()
   → 🎯 여기서 PRODUCT_ID, PROCESS_ID 한 번만 생성 (월 포함!)
   ↓
5. concat(results)
   → sequence_seperated_order
   ↓
6. create_sequence_seperated_order()
   → ✅ 월 추가 로직 불필요 (이미 포함됨)
```

---

## 📊 비교표

| 항목 | 기존 계획 | 최적화 후 |
|------|----------|----------|
| **ID 생성 횟수** | 2회 | 1회 ✅ |
| **코드 복잡도** | 높음 | 낮음 ✅ |
| **데이터 일관성** | 위험 | 안전 ✅ |
| **유지보수성** | 분산 | 집중 ✅ |
| **성능** | 느림 | 빠름 ✅ |

---

## 🎯 장점

### 1. 단일 진실 공급원 (Single Source of Truth)
- ID 생성 로직이 **한 곳**에만 존재
- 수정 시 한 곳만 변경하면 됨

### 2. 데이터 일관성 보장
- PRODUCT_ID와 PROCESS_ID가 **동시에** 생성됨
- 중간에 데이터 변경으로 인한 불일치 불가능

### 3. 성능 향상
```python
# 기존: O(2N) - 두 번 생성
# 최적화: O(N) - 한 번 생성
# → 약 50% 성능 향상
```

### 4. 코드 간결화
```python
# Line 66: 5줄 → 2줄 (60% 감소)
```

### 5. 가독성 향상
- ID 생성 로직이 모두 `process_operations_by_category()`에 집중
- 명확한 책임 분리

---

## 🧪 검증

### Test Case 1: PRODUCT_ID 형식
```python
def test_product_id_includes_month():
    # Given
    paired_order = pd.DataFrame({
        'gitemno': ['A001'],
        'fabric_width': [1500],
        'comb_classification': [1],
        'duedate': [pd.Timestamp('2025-05-15')]
    })

    # When
    # ... (PRODUCT_ID 생성)

    # Then
    assert paired_order['PRODUCT_ID'].iloc[0] == "A001_1500_1_M5"
```

### Test Case 2: PROCESS_ID 형식
```python
def test_process_id_based_on_product_id():
    # Given
    product_id = "A001_1500_1_M5"
    operation_code = "OP1"
    chemical_list = "CHEM1"

    # When
    process_id = f"{product_id}_{operation_code}_{chemical_list}"

    # Then
    assert process_id == "A001_1500_1_M5_OP1_CHEM1"
```

### Test Case 3: ID 생성 횟수
```python
def test_id_generated_only_once():
    # Given
    call_count = 0

    # When
    # ... (전체 파이프라인 실행)

    # Then
    assert call_count == 1  # process_operations_by_category에서만 생성
```

---

## 📝 구현 순서

### Step 1: `process_operations_by_category()` 수정
**파일:** `src/order_sequencing/sequence_preprocessing.py:30-37`

```python
if not paired_order.empty:
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

    results.append(paired_order)
```

### Step 2: `create_sequence_seperated_order()` 수정
**파일:** `src/order_sequencing/sequence_preprocessing.py:65-67`

```python
# 결과를 하나의 DataFrame으로 병합
sequence_seperated_order = pd.concat(sequence_seperated_order_list, ignore_index=True)

# 월 정보가 이미 포함되어 있으므로 ID 추가 로직 제거!
# (기존 Line 66 삭제)

# OPERATION_ORDER 타입 변환만 유지
sequence_seperated_order[config.columns.OPERATION_ORDER] = (
    sequence_seperated_order[config.columns.OPERATION_ORDER].astype(int)
)

return sequence_seperated_order
```

### Step 3: 테스트
```bash
# 단위 테스트
python -m pytest tests/test_id_system.py -v

# 통합 테스트
python main.py
```

---

## ⚠️ 주의사항

### 1. DUE_DATE 컬럼 필수
**확인:**
- `FabricCombiner._assign_fabric_quantity()`가 `DUE_DATE`를 반환하는지 확인
- ✅ 확인 완료: Line 201에서 `DUE_DATE: sub_df[DUE_DATE].min()` 포함

### 2. 타입 변환
```python
# DUE_DATE가 Timestamp 타입인지 확인
assert isinstance(paired_order[config.columns.DUE_DATE].iloc[0], pd.Timestamp)

# .dt.month 접근 가능한지 확인
month = paired_order[config.columns.DUE_DATE].dt.month.astype(str)
```

### 3. NaN 처리
```python
# DUE_DATE가 NaN인 경우 처리
if paired_order[config.columns.DUE_DATE].isna().any():
    raise ValueError("DUE_DATE에 NaN이 존재합니다")
```

---

## 🎉 결론

### 최적화 효과

| 지표 | 개선 |
|------|------|
| **코드 라인** | -5줄 |
| **ID 생성 횟수** | 2회 → 1회 (50% 감소) |
| **연산 복잡도** | O(2N) → O(N) |
| **유지보수 포인트** | 2곳 → 1곳 |
| **데이터 일관성** | 위험 → 안전 |

### 핵심 변경
1. ✅ **Line 30-37**: PRODUCT_ID, PROCESS_ID 한 번에 생성 (월 포함)
2. ✅ **Line 66**: 월 추가 로직 완전 제거

### 최종 권장
**이 최적화된 방법을 사용하여 ID를 단 한 번만 생성할 것을 강력히 권장합니다!**

---

## 📋 체크리스트

### 구현 전
- [ ] `paired_order`에 `DUE_DATE` 포함 확인
- [ ] `DUE_DATE` 타입이 Timestamp인지 확인
- [ ] `.dt.month` 접근 가능한지 확인

### 구현 후
- [ ] PRODUCT_ID 형식: `{GITEM}_{WIDTH}_{COMB}_M{MONTH}`
- [ ] PROCESS_ID 형식: `{PRODUCT_ID}_{OP}_{CHEM}`
- [ ] Line 66의 월 추가 로직 제거됨
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 기존 결과와 동일한지 검증
