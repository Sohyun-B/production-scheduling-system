# 비결정성 디버깅 세션 요약

**날짜**: 2025-11-19
**목표**: 생산 스케줄링 알고리즘의 비결정성(Non-Deterministic) 원인 찾기
**현상**: 같은 입력 데이터로 main.py 실행 시 매번 다른 스케줄링 결과 발생

---

## 🎯 핵심 문제

**사용자 요구사항**:
- 같은 입력 → 항상 같은 출력 (재현성, Determinism)
- 현재는 실행할 때마다 최종 스케줄링 결과가 다름

---

## 📝 지금까지 수행한 작업

### 1. 초기 분석 (잘못된 방향)

**시도했던 것**:
- `src/scheduler/dispatch_rules.py:21`의 `set()` 순회를 비결정성 원인으로 지목
- Python hash randomization 때문에 set iteration 순서가 비결정적이라고 분석

**사용자 피드백**:
- heapq에 `(납기일, -원단너비, node_id)` 튜플을 넣는데, `node_id`가 unique하므로 완전한 tie-breaking 보장됨
- **set 순회 순서와 관계없이 heapq pop 순서는 결정적**
- → 이 분석은 **잘못됨**

### 2. 단위 테스트 접근 (현재 진행 중)

**목적**: 각 단계별로 결정성을 검증하여 비결정성이 **처음 발생하는 지점**을 특정

**테스트 스크립트**: `test_determinism.py`
- 전체 파이프라인을 **2번 실행**
- 각 단계마다 결과의 hash 비교
- 처음 다른 결과가 나오는 지점이 비결정성의 원인

**테스트 단계**:
1. ✅ **입력 데이터 로딩** - 결정적 (모두 SAME)
2. ✅ **Validation & Preprocessing** - 결정적 (모두 SAME)
3. ✅ **주문 시퀀스 생성** - 결정적 (SAME)
4. ✅ **수율 예측** - 결정적 (SAME)
5. ⏳ **DAG 생성** - 테스트 중 (aging_map까지 SAME 확인)
6. ⏳ **Dispatch Rule 생성** - **여기가 핵심 의심 지점**
7. ⏳ **스케줄링 실행** - 확인 필요

**현재 상태**:
- 테스트 스크립트 작성 완료
- 테스트 5까지 모두 결정적임을 확인
- 테스트 6, 7 실행 중 (시간이 오래 걸림)
- 코드 수정 필요: `create_complete_dag_system` 호출 방식 수정 완료

---

## 🔍 확인된 사실

### Python 환경
- **Python 버전**: 3.11.9
- **NumPy**: 2.3.2
- **Pandas**: 2.3.2
- Python 3.7+ → 딕셔너리 삽입 순서 보장됨

### 결정적인 부분 (검증 완료)
1. ✅ 입력 Excel 파일 로딩
2. ✅ Validation & Preprocessing (전처리)
3. ✅ 주문 시퀀스 생성 (폭 조합 등)
4. ✅ 수율 예측
5. ✅ aging_map 생성

### 의심 지점
- **Dispatch Rule 생성** (`src/scheduler/dispatch_rules.py`)
- **스케줄링 실행** (`src/scheduler/`)

---

## 🚧 다음 세션에서 해야 할 일

### 1단계: 단위 테스트 완료 및 분석

**즉시 실행**:
```bash
cd "C:\Users\kim\OneDrive\바탕 화면\생산계획\스케줄링-1112\python_engine"
python test_determinism.py > test_output.txt 2>&1
```

**확인 사항**:
```python
# test_output.txt 파일에서 다음 항목 확인
# [테스트 6] Dispatch Rule 생성 결정성 검증
# dispatch_rule          : [OK] SAME 또는 [DIFF] DIFFERENT?

# [테스트 7] 스케줄링 실행 결정성 검증
# scheduling_result      : [OK] SAME 또는 [DIFF] DIFFERENT?
```

**만약 [DIFF] DIFFERENT가 나온다면**:
- 그 지점이 비결정성의 **첫 발생 지점**
- 해당 코드를 집중 분석
- 테스트 스크립트는 차이나는 부분을 자동으로 출력함

### 2단계: 비결정성 원인 파악

**Dispatch Rule이 다르다면** (`src/scheduler/dispatch_rules.py` 분석):

**확인할 부분**:
1. **Line 21**: `all_ids = set(dag_df[config.columns.PROCESS_ID])`
   - set 생성 자체는 문제없지만, 다른 곳에서 순회하는지 확인

2. **Line 13-19**: `children_map`, `parents_map` 생성
   ```python
   children_map = defaultdict(list)
   parents_map = defaultdict(list)
   for idx, row in dag_df.iterrows():
       parent = row[config.columns.PROCESS_ID]
       for child in row[config.columns.CHILDREN]:
           children_map[parent].append(child)
           parents_map[child].append(parent)
   ```
   - `dag_df.iterrows()` 순서가 결정적인지 확인
   - `dag_df`가 정렬되어 있는지 확인

3. **Line 51-57**: children 순회
   ```python
   for child in children_map[current]:
       in_degree[child] -= 1
       if in_degree[child] == 0:
           heapq.heappush(ready, (due_dict[child], -width_dict[child], child))
   ```
   - `children_map[current]`의 순서가 결정적인지 확인

**스케줄링이 다르다면** (`src/scheduler/` 분석):

**확인할 부분**:
1. `src/scheduler/scheduling_core.py`:
   - `find_best_chemical()` 함수
   - `SetupMinimizedStrategy.execute()`
   - 윈도우 내 노드 순회 순서

2. `src/scheduler/scheduler.py`:
   - `assign_operation()` 메서드
   - 기계 선택 로직

### 3단계: 원인별 해결 방법

**딕셔너리/set 순회 문제라면**:
```python
# 나쁜 예
for item in my_dict.items():
    ...

# 좋은 예
for key in sorted(my_dict.keys()):
    value = my_dict[key]
    ...
```

**DataFrame 순회 순서 문제라면**:
```python
# DataFrame 정렬 확인
dag_df = dag_df.sort_values(['DEPTH', 'PROCESS_ID']).reset_index(drop=True)
```

**리스트 append 순서 문제라면**:
```python
# append 후 정렬
children_list.append(child)
children_list.sort()  # 명시적 정렬
```

### 4단계: 수정 및 검증

**수정 후**:
```bash
# 여러 번 실행하여 결과가 동일한지 확인
python main.py
cp data/output/result.xlsx result1.xlsx

python main.py
cp data/output/result.xlsx result2.xlsx

# Python으로 비교
python -c "
import pandas as pd
df1 = pd.read_excel('result1.xlsx')
df2 = pd.read_excel('result2.xlsx')
print('Identical:', df1.equals(df2))
if not df1.equals(df2):
    print('Differences:')
    print(df1.compare(df2))
"
```

### 5단계: 문서 작성

**수정 완료 후**:
- `docs/non_deterministic_analysis.md` 업데이트
- 실제 원인과 해결 방법 명확히 기술
- 재현 테스트 결과 포함

---

## 📂 관련 파일

### 작성한 파일
- **test_determinism.py**: 단위 테스트 스크립트 (루트 디렉토리)
- **docs/non_deterministic_analysis.md**: 초기 분석 문서 (잘못된 내용 포함, 재작성 필요)

### 주요 코드 파일
- **src/scheduler/dispatch_rules.py**: Dispatch rule 생성 (의심 지점 1)
- **src/scheduler/scheduling_core.py**: 스케줄링 핵심 로직 (의심 지점 2)
- **src/scheduler/scheduler.py**: 기계 할당 로직
- **src/dag_management/dag_dataframe.py**: DAG 생성
- **main.py**: 전체 파이프라인 실행

---

## 💡 중요한 교훈

### 사용자가 지적한 오류
1. **heapq의 동작 원리 오해**:
   - ❌ 잘못된 생각: set 순회 순서가 heapq 결과에 영향
   - ✅ 올바른 이해: `(납기일, -너비, node_id)`에서 node_id가 unique하므로 완전한 tie-breaking
   - → 같은 우선순위 항목이 없으므로 삽입 순서 무관

2. **원인 없다 ≠ 문제 없다**:
   - "이론적으로 결정적이어야 함" ≠ "실제로 결정적임"
   - 실제 비결정성이 발생하고 있으므로 어딘가에 원인이 있음
   - → **단위 테스트로 실증적으로 원인 찾기**

### 올바른 접근 방법
1. ✅ **단위 테스트**: 각 단계별로 실제 결과 비교
2. ✅ **실증적 분석**: 이론보다 실제 실행 결과 우선
3. ✅ **점진적 범위 좁히기**: 전체 → 각 단계 → 특정 함수

---

## 🔧 즉시 실행 가능한 명령어

### 테스트 실행
```bash
cd "C:\Users\kim\OneDrive\바탕 화면\생산계획\스케줄링-1112\python_engine"
python test_determinism.py 2>&1 | tee test_output.txt
```

### 결과 확인 (Python)
```python
# test_output.txt에서 핵심 결과만 추출
with open('test_output.txt', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
    for line in lines:
        if 'SAME' in line or 'DIFFERENT' in line or '테스트' in line:
            print(line.rstrip())
```

### 두 번 실행 후 비교
```bash
# Run 1
python main.py
copy "data\output\result.xlsx" result_run1.xlsx

# Run 2
python main.py
copy "data\output\result.xlsx" result_run2.xlsx

# Compare
python -c "import pandas as pd; df1=pd.read_excel('result_run1.xlsx'); df2=pd.read_excel('result_run2.xlsx'); print('Same:', df1.equals(df2))"
```

---

## 📌 다음 세션 시작 시 체크리스트

- [ ] `test_determinism.py` 실행 완료되었는지 확인
- [ ] 테스트 6, 7의 결과 확인 (SAME or DIFFERENT?)
- [ ] DIFFERENT가 나온 첫 번째 지점 특정
- [ ] 해당 코드 상세 분석
- [ ] 비결정성 원인 파악
- [ ] 수정 및 검증
- [ ] 문서 업데이트

---

**마지막 상태**:
- 테스트 스크립트 작성 완료
- 테스트 1-5 모두 결정적 확인
- 테스트 6-7 실행 필요 (시간 소요)
- 실제 원인은 아직 미확인
