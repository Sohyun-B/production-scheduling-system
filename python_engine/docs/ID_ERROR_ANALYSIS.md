# ID 리팩토링 에러 분석 및 해결 방안

## 🔴 에러 발생

### 에러 메시지

```
KeyError: 'PROCESS_ID'

File "src\scheduler\dispatch_rules.py", line 9, in create_dispatch_rule
    dag_df = pd.merge(dag_df, sequence_seperated_order[[config.columns.DUE_DATE,
                      config.columns.FABRIC_WIDTH, config.columns.PROCESS_ID]],
                      on=config.columns.PROCESS_ID, how='left')
```

### 에러 위치

- **파일:** `src/scheduler/dispatch_rules.py:9`
- **함수:** `create_dispatch_rule()`

---

## 🔍 원인 분석

### 근본 원인

**dag_df에 `PROCESS_ID` 컬럼이 없음**

### 상세 분석

#### 1. dag_df는 어디서 생성되는가?

**파일:** `src/dag_management/dag_dataframe.py:74-78`

```python
dag_data.append({
    'ID': node,           # ← 문제! 하드코딩된 'ID' 문자열
    config.columns.DEPTH: depth,
    'CHILDREN': ', '.join(children) if children else ''
})
```

**문제점:**

- `'ID'` 문자열을 하드코딩
- `config.columns.PROCESS_ID`를 사용해야 함

#### 2. dag_df의 실제 컬럼

```python
# 현재 (잘못됨)
dag_df.columns = ['ID', config.columns.DEPTH, 'CHILDREN']

# 기대 (올바름)
dag_df.columns = ['PROCESS_ID', config.columns.DEPTH, 'CHILDREN']
```

#### 3. 후속 코드의 영향

**파일:** `src/dag_management/dag_manager.py:49-62`

```python
for idx, row in dag_df.iterrows():
    node = DAGNode(row['ID'], row[config.columns.DEPTH])  # ← 'ID' 하드코딩
    node_id = row['ID']                      # ← 'ID' 하드코딩
    self.nodes[row['ID']] = node            # ← 'ID' 하드코딩
```

**문제점:**

- `row['ID']`를 여러 곳에서 사용
- 모두 `row[config.columns.PROCESS_ID]`로 변경 필요

---

## 🎯 해결 방안

### 전략

**하드코딩된 `'ID'` 문자열을 모두 `config.columns.PROCESS_ID`로 변경**

### 수정 대상 파일

| 파일               | 하드코딩 'ID' 개수 | 우선순위  |
| ------------------ | ------------------ | --------- |
| `dag_dataframe.py` | 13개               | 🔴 High   |
| `dag_manager.py`   | 4개                | 🔴 High   |
| 기타               | 검색 필요          | 🟡 Medium |

---

## 📝 상세 수정 계획

### 1. `dag_dataframe.py` 수정 (13곳)

#### Line 75: dag_data 생성

**변경 전:**

```python
dag_data.append({
    'ID': node,
    config.columns.DEPTH: depth,
    'CHILDREN': ', '.join(children) if children else ''
})
```

**변경 후:**

```python
dag_data.append({
    config.columns.PROCESS_ID: node,  # 'ID' → config.columns.PROCESS_ID
    config.columns.DEPTH: depth,
    'CHILDREN': ', '.join(children) if children else ''
})
```

#### Line 81: DataFrame 정렬

**변경 전:**

```python
return pd.DataFrame(dag_data).sort_values([config.columns.DEPTH, 'ID'])
```

**변경 후:**

```python
return pd.DataFrame(dag_data).sort_values([config.columns.DEPTH, config.columns.PROCESS_ID])
```

#### Line 247: normalize_depths_post_aging

**변경 전:**

```python
node_id = row['ID']
```

**변경 후:**

```python
node_id = row[config.columns.PROCESS_ID]
```

#### Line 289, 301, 309, 321, 352, 368, 378, 396, 442, 466, 485

**변경 전:**

```python
# 예시
result_df[result_df['ID'] == current_id]
mask = result_df['ID'] == node_id
df['ID'].values
```

**변경 후:**

```python
# 예시
result_df[result_df[config.columns.PROCESS_ID] == current_id]
mask = result_df[config.columns.PROCESS_ID] == node_id
df[config.columns.PROCESS_ID].values
```

---

### 2. `dag_manager.py` 수정 (4곳)

#### Line 49-50, 58, 62

**변경 전:**

```python
node = DAGNode(row['ID'], row[config.columns.DEPTH])
node_id = row['ID']
self.nodes[row['ID']] = node
current = self.nodes[row['ID']]
```

**변경 후:**

```python
node = DAGNode(row[config.columns.PROCESS_ID], row[config.columns.DEPTH])
node_id = row[config.columns.PROCESS_ID]
self.nodes[row[config.columns.PROCESS_ID]] = node
current = self.nodes[row[config.columns.PROCESS_ID]]
```

---

### 3. 기타 파일 검색 및 수정

**검색 명령:**

```bash
# 하드코딩된 'ID' 문자열 검색
grep -rn "['\"]\ID['\"]" src/ --include="*.py"

# 또는
grep -rn "row\['ID'\]" src/ --include="*.py"
grep -rn "\.columns\['ID'\]" src/ --include="*.py"
```

**예상 위치:**

- `src/results/*.py`
- `src/new_results/*.py`
- `src/scheduler/*.py`

---

## ⚠️ 주의사항

### 1. 'ID' vs PROCESS_ID 구분

**변경해야 하는 경우:**

```python
# DataFrame 컬럼명으로 사용
row['ID']                    → row[config.columns.PROCESS_ID]
df['ID']                     → df[config.columns.PROCESS_ID]
{'ID': node}                 → {config.columns.PROCESS_ID: node}
.sort_values([config.columns.DEPTH, 'ID']) → .sort_values([config.columns.DEPTH, config.columns.PROCESS_ID])
```

**변경하지 않는 경우:**

```python
# 일반 문자열 (노드 ID 값 자체)
node.id  # DAGNode 객체의 id 속성 (문제 없음)
node_id = "A001_1500_1_M5_OP1_CHEM1"  # 실제 ID 값 (문제 없음)
```

### 2. DEPTH, CHILDREN 컬럼

**변경 불필요:**

- `config.columns.DEPTH`, `'CHILDREN'`는 그대로 유지
- config에 정의되어 있지만 하드코딩해도 무방

---

## 🧪 검증 방법

### 1. 수정 후 dag_df 컬럼 확인

```python
# src/dag_management/__init__.py 또는 main.py에서
print("dag_df columns:", dag_df.columns.tolist())

# 예상 결과
# ['PROCESS_ID', config.columns.DEPTH, 'CHILDREN']
```

### 2. merge 테스트

```python
# dispatch_rules.py에서
dag_df = pd.merge(dag_df,
                  sequence_seperated_order[[config.columns.DUE_DATE,
                                           config.columns.FABRIC_WIDTH,
                                           config.columns.PROCESS_ID]],
                  on=config.columns.PROCESS_ID,
                  how='left')
# 에러 없이 실행되어야 함
```

### 3. 전체 파이프라인 테스트

```bash
python main.py
```

---

## 📋 수정 체크리스트

### dag_dataframe.py

- [ ] Line 75: `'ID': node` → `config.columns.PROCESS_ID: node`
- [ ] Line 81: `sort_values([config.columns.DEPTH, 'ID'])` → `sort_values([config.columns.DEPTH, config.columns.PROCESS_ID])`
- [ ] Line 247: `row['ID']` → `row[config.columns.PROCESS_ID]`
- [ ] Line 289: `result_df['ID']` → `result_df[config.columns.PROCESS_ID]`
- [ ] Line 301: `result_df['ID']` → `result_df[config.columns.PROCESS_ID]`
- [ ] Line 309: `sort_values([config.columns.DEPTH, 'ID'])` → `sort_values([config.columns.DEPTH, config.columns.PROCESS_ID])`
- [ ] Line 321: `duplicates[['ID', config.columns.DEPTH]]` → `duplicates[[config.columns.PROCESS_ID, config.columns.DEPTH]]`
- [ ] Line 352: `df['ID'].values` → `df[config.columns.PROCESS_ID].values`
- [ ] Line 368: `df['ID']` → `df[config.columns.PROCESS_ID]`
- [ ] Line 378: `df['ID']` → `df[config.columns.PROCESS_ID]`
- [ ] Line 396: `df['ID']` → `df[config.columns.PROCESS_ID]`
- [ ] Line 442: `result_df['ID']` → `result_df[config.columns.PROCESS_ID]`
- [ ] Line 466: `'ID': aging_node_id` → `config.columns.PROCESS_ID: aging_node_id`
- [ ] Line 485: `sort_values([config.columns.DEPTH, 'ID'])` → `sort_values([config.columns.DEPTH, config.columns.PROCESS_ID])`

### dag_manager.py

- [ ] Line 49: `row['ID']` → `row[config.columns.PROCESS_ID]`
- [ ] Line 50: `row['ID']` → `row[config.columns.PROCESS_ID]`
- [ ] Line 58: `row['ID']` → `row[config.columns.PROCESS_ID]`
- [ ] Line 62: `row['ID']` → `row[config.columns.PROCESS_ID]`

### 기타

- [ ] 전체 검색 수행: `grep -rn "['\"]\ID['\"]" src/`
- [ ] 추가 발견된 파일 수정
- [ ] 테스트 실행

---

## 🎯 우선 수정 순서

### 1단계: DAG 생성 핵심 파일 (필수)

1. ✅ `src/dag_management/dag_dataframe.py` (13곳)
2. ✅ `src/dag_management/dag_manager.py` (4곳)

### 2단계: 테스트

```bash
python main.py
```

### 3단계: 추가 에러 발생 시

- 에러 메시지 확인
- 해당 파일에서 하드코딩된 'ID' 검색 및 수정
- 재테스트

---

## 🚀 빠른 수정 스크립트 (선택)

**자동 치환 (주의: 백업 필수!)**

```bash
# 백업
cp src/dag_management/dag_dataframe.py src/dag_management/dag_dataframe.py.bak
cp src/dag_management/dag_manager.py src/dag_management/dag_manager.py.bak

# sed로 일괄 치환 (Linux/Mac)
sed -i "s/\['ID'\]/[config.columns.PROCESS_ID]/g" src/dag_management/dag_dataframe.py
sed -i "s/\['ID'\]/[config.columns.PROCESS_ID]/g" src/dag_management/dag_manager.py

# Windows는 수동 치환 권장 (에디터 찾기/바꾸기 기능 사용)
```

**수동 치환 (권장)**

- VSCode 또는 에디터의 "찾기 및 바꾸기" 기능 사용
- 정규식 검색: `\['ID'\]`
- 치환: `[config.columns.PROCESS_ID]`
- 파일별로 확인하며 치환

---

## 📊 예상 결과

### 수정 전 (에러)

```python
KeyError: 'PROCESS_ID'
```

### 수정 후 (정상)

```python
dag_df.columns = ['PROCESS_ID', config.columns.DEPTH, 'CHILDREN']
# merge 정상 동작
# 스케줄링 정상 실행
```

---

## 💡 교훈

### 문제점

1. **하드코딩의 위험성**

   - `'ID'` 문자열을 하드코딩하면 config 변경 시 오류 발생
   - 일관성 없는 코드

2. **전역 검색의 중요성**
   - config.columns.ID만 변경하고 하드코딩된 'ID' 간과

### 개선 방안

1. **항상 config 사용**

   ```python
   # Bad
   row['ID']

   # Good
   row[config.columns.PROCESS_ID]
   ```

2. **리팩토링 시 전역 검색**

   ```bash
   grep -rn "['\"]\ID['\"]" src/
   ```

3. **타입 안전성 강화**
   - 가능하면 문자열 리터럴 대신 상수 사용

---

## ✅ 완료 조건

1. ✅ dag_dataframe.py의 모든 'ID' → PROCESS_ID 변경
2. ✅ dag_manager.py의 모든 'ID' → PROCESS_ID 변경
3. ✅ 전역 검색으로 추가 하드코딩 확인
4. ✅ `python main.py` 정상 실행
5. ✅ 결과 파일 생성 확인
