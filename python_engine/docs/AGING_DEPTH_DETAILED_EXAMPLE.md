# Aging Depth 중복 문제 - 상세 예시 설명

**목표**: 실제 데이터로 현재 버그를 이해하기

---

## 📌 시나리오 설정

### 초기 상태: 5개 공정의 DAG

```
생산 흐름:
공정1 → 공정2 → 공정3 → 공정4 → 공정5

초기 DAG:
ID   | depth | CHILDREN | 설명
-----|-------|----------|------
N001 | 1     | N002     | 공정1
N002 | 2     | N003     | 공정2
N003 | 3     | N004     | 공정3
N004 | 4     | N005     | 공정4
N005 | 5     | (없음)   | 공정5
```

### Aging 요구사항

```
Aging Map:
{
  'N002': {  # 공정2 다음에 48시간 건조 필요 → 에이징공정1
    'aging_node_id': 'N002_AGING',
    'aging_time': 1440,  # 48시간
    'next_node_id': 'N003'
  },
  'N004': {  # 공정4 다음에 24시간 방치 필요 → 에이징공정2
    'aging_node_id': 'N004_AGING',
    'aging_time': 720,   # 24시간
    'next_node_id': 'N005'
  }
}
```

---

## 🔴 현재 코드의 버그 재현

### 현재 코드 구조

```python
# src/dag_management/dag_dataframe.py:312-325
def insert_aging_nodes_to_dag(dag_df, aging_map):
    for idx, row in dag_df.iterrows():  # ← 원본 dag_df 순회!
        parent_node_id = row['ID']
        if parent_node_id in aging_map:
            aging_depth = row['DEPTH'] + 1  # ← row는 아직 shift 전!
            # ... aging 노드 생성 ...
```

**문제**: 이 루프는 **원본 dag_df를 기준**으로 모든 에이징을 생성합니다.
따라서 첫 번째 에이징이 shift한 결과가 두 번째 에이징 생성 시 반영되지 않습니다!

---

## 🔍 Step-by-Step 버그 재현

### **STEP 1: 첫 번째 에이징 (에이징공정1) 삽입**

#### 1-1) 에이징공정1 노드 생성

```python
# 코드 실행:
for idx, row in dag_df.iterrows():
    if row['ID'] == 'N002':  # ← 원본 dag_df에서
        aging_depth = row['DEPTH'] + 1
        # row['DEPTH'] = 2 (원본 상태)
        # aging_depth = 2 + 1 = 3

# 결과: 에이징공정1의 depth = 3
```

**현재 DAG 상태**:
```
ID           | depth | CHILDREN     | 설명
-------------|-------|--------------|--------
공정1(N001)  | 1     | N002         | 공정1
공정2(N002)  | 2     | 에이징1      | 공정2 ← 자식이 변경됨
에이징1      | 3     | N003         | 에이징공정1
공정3(N003)  | 3     | N004         | 공정3 ← 중복!
공정4(N004)  | 4     | N005         | 공정4
공정5(N005)  | 5     | (없음)       | 공정5
```

⚠️ **이 시점에서 이미 depth 중복 발생**: 에이징1(3)과 공정3(3)

#### 1-2) shift_depths_after_aging() 호출

```python
# 에이징공정1의 children을 BFS로 찾음
aging_node_id = 'N002_AGING'
# CHILDREN = 'N003' 찾음

# 공정3의 depth = 3
# aging_depth = 3
# 공정3.depth >= aging_depth? → 3 >= 3? → YES!
# → 공정3를 descendants에 추가
# → 공정3.depth += 1

# 공정3 → 공정4를 따라 가기 (BFS)
# 공정4의 depth = 4
# 공정4.depth >= aging_depth? → 4 >= 3? → YES!
# → 공정4를 descendants에 추가
# → 공정4.depth += 1

# 공정4 → 공정5를 따라 가기 (BFS)
# 공정5의 depth = 5
# 공정5.depth >= aging_depth? → 5 >= 3? → YES!
# → 공정5를 descendants에 추가
# → 공정5.depth += 1
```

**Shift 완료 후 DAG 상태** ✅

```
ID           | depth | CHILDREN     | 설명
-------------|-------|--------------|--------
공정1(N001)  | 1     | N002         | 공정1
공정2(N002)  | 2     | 에이징1      | 공정2
에이징1      | 3     | N003         | 에이징공정1
공정3(N003)  | 4     | N004         | 공정3 ← 증가!
공정4(N004)  | 5     | N005         | 공정4 ← 증가!
공정5(N005)  | 6     | (없음)       | 공정5 ← 증가!
```

✅ 첫 번째 에이징은 성공했습니다!

---

### **STEP 2: 두 번째 에이징 (에이징공정2) 삽입** 🔴 버그 발생!

#### 2-1) 에이징공정2 노드 생성 (버그!)

```python
# 코드 실행:
for idx, row in dag_df.iterrows():  # ← 여전히 원본 dag_df를 순회!
    if row['ID'] == 'N004':  # ← 원본 dag_df에서
        aging_depth = row['DEPTH'] + 1
        # row['DEPTH'] = 4 (원본 상태!)
        # BUT 공정4의 현재 depth는 5 (shift 후)
        # aging_depth = 4 + 1 = 5 ← 잘못된 값!

# 결과: 에이징공정2의 depth = 5 (정확해야 할 값: 6)
```

**현재 DAG 상태** (버그!)
```
ID           | depth | CHILDREN     | 설명
-------------|-------|--------------|--------
공정1(N001)  | 1     | N002         | 공정1
공정2(N002)  | 2     | 에이징1      | 공정2
에이징1      | 3     | N003         | 에이징공정1
공정3(N003)  | 4     | N004         | 공정3
공정4(N004)  | 5     | 에이징2      | 공정4 ← 자식이 변경됨
에이징2      | 5     | N005         | 에이징공정2 ← 중복!
공정5(N005)  | 6     | (없음)       | 공정5
```

⚠️ **심각한 depth 중복**: 공정4(5)와 에이징2(5)

#### 2-2) shift_depths_after_aging() 호출 (실패!)

```python
# 에이징공정2의 children을 BFS로 찾음
aging_node_id = 'N004_AGING'
# CHILDREN = 'N005' 찾음

# 공정5의 depth = 6
# aging_depth = 5 (잘못된 값)
# 공정5.depth >= aging_depth? → 6 >= 5? → YES!
# → 공정5를 descendants에 추가
# → 공정5.depth += 1

# 공정5는 마지막 공정이므로 CHILDREN이 없음
# BFS 종료
```

**Shift 완료 후 DAG 상태** (여전히 버그!)
```
ID           | depth | CHILDREN     | 설명
-------------|-------|--------------|--------
공정1(N001)  | 1     | N002         | 공정1
공정2(N002)  | 2     | 에이징1      | 공정2
에이징1      | 3     | N003         | 에이징공정1
공정3(N003)  | 4     | N004         | 공정3
공정4(N004)  | 5     | 에이징2      | 공정4
에이징2      | 5     | N005         | 에이징공정2 ❌ 중복!
공정5(N005)  | 7     | (없음)       | 공정5
```

❌ **최종 결과: Depth 중복 발생!** 공정4(5) = 에이징2(5)

---

## 📊 비교: 현재 vs 예상 vs 수정 후

```
┌─────────────────────────────────────────────────────────────────┐
│                        현재 (버그)                                │
├─────────────────────────────────────────────────────────────────┤
│ 공정1(1) → 공정2(2) → 에이징1(3) → 공정3(4)                     │
│                                    ↓                             │
│                              공정4(5) → 에이징2(5) ❌ 중복!       │
│                                         ↓                        │
│                                    공정5(7)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        예상 (정상)                                │
├─────────────────────────────────────────────────────────────────┤
│ 공정1(1) → 공정2(2) → 에이징1(3) → 공정3(4)                     │
│                                    ↓                             │
│                              공정4(5) → 에이징2(6) ✅ 정상!       │
│                                         ↓                        │
│                                    공정5(7)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 문제의 원인 - 두 가지!

### 문제 1️⃣: 원본 dag_df 순회

```python
# ❌ 현재 코드:
for idx, row in dag_df.iterrows():  # 원본 dag_df 순회
    aging_depth = row['DEPTH'] + 1  # 원본 depth 사용

# ✅ 수정해야 할 방식:
for parent_id in aging_nodes:
    current_row = dag_df[dag_df['ID'] == parent_id]  # 최신 상태 읽기
    aging_depth = current_row['DEPTH'] + 1  # 최신 depth 사용
```

**영향**: 첫 번째 에이징의 shift가 두 번째 에이징에 반영 안 됨

### 문제 2️⃣: shift_depths_after_aging()의 불완전한 로직

```python
# 현재 문제:
descendants = []  # 비어있을 수 있음!

# 마지막 공정의 에이징:
# 공정5_AGING은 children이 없음
# → descendants = []
# → shift 안 됨!
```

**영향**: 마지막 공정 다음의 에이징이 shift되지 않음

---

## 🔧 수정 방법

### 방법 1: Sequential Insertion (권장) ⭐

```python
# ✅ Sequential 방식
def insert_aging_nodes_to_dag_fixed(dag_df, aging_map):
    result_df = dag_df.copy()

    # Key: 에이징을 하나씩 처리
    for parent_id in sorted_by_depth(aging_map.keys()):
        # 1. 현재 상태의 parent depth 읽기
        parent_row = result_df[result_df['ID'] == parent_id]
        current_parent_depth = parent_row.iloc[0]['DEPTH']  # ← 최신!

        # 2. 에이징 노드 생성
        aging_node = {
            'ID': aging_map[parent_id]['aging_node_id'],
            'DEPTH': current_parent_depth + 1,  # ← 최신 depth 사용
            'CHILDREN': aging_map[parent_id]['next_node_id']
        }

        # 3. DAG에 추가
        result_df = add_row_to_df(result_df, aging_node)

        # 4. 즉시 shift (다음 에이징에 반영됨!)
        result_df = shift_depths_after_aging(
            aging_node['ID'],
            aging_node['DEPTH'],
            result_df
        )

    return result_df
```

**이렇게 하면**:
```
STEP 1: 에이징공정1 삽입 + 즉시 shift
  결과: 공정1(1) → 공정2(2) → 에이징1(3) → 공정3(4) → 공정4(5) → 공정5(6)

STEP 2: 에이징공정2 삽입 (현재 공정4는 depth=5!)
  aging_depth = 5 + 1 = 6 ✅
  결과: ... → 공정4(5) → 에이징2(6) → 공정5(7) ✅ 정상!
```

---

## 💡 이제 이해되셨나요?

### 핵심 포인트

1. **원본 vs 현재 상태의 차이**
   - 첫 번째 에이징이 shift를 하면 DAG가 변함
   - 하지만 코드는 여전히 "원본"을 기준으로 다음 에이징을 생성함

2. **Sequential 처리의 중요성**
   - 에이징 하나씩 처리하고
   - 각각 즉시 shift해야 다음 에이징이 정확한 depth를 사용 가능

3. **마지막 공정의 특수성**
   - 마지막 공정은 children이 없음
   - 따라서 shift_depths_after_aging()의 BFS가 아무도 못 찾음
   - next_node_id를 명시적으로 처리해야 함

---

## 📋 정리

| 항목 | 설명 |
|------|------|
| **버그의 원인** | 원본 dag_df를 순회하며 shift 결과를 반영 안 함 |
| **증상** | Depth 중복 (공정4(5) = 에이징2(5)) |
| **영향** | Scheduling 정상이지만 depth 기반 로직에 문제 가능 |
| **해결책** | Sequential insertion + 즉시 shift |
| **소요시간** | 약 3시간 |

이제 명확하신가요? 😊
