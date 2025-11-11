# Aging Depth 중복 문제 - 수정 계획서

**작성일**: 2025-11-11
**상태**: 🔥 **CRITICAL - 즉시 수정 필요**
**영향도**: HIGH
**난이도**: MEDIUM

---

## 1️⃣ 문제 분석 (현재 에이징 상태.txt 기반)

### 근본 원인

#### 문제 1: 원본 dag_df 순회로 인한 depth 미반영
```python
# src/dag_management/dag_dataframe.py:312-325
for idx, row in dag_df.iterrows():  # ← 원본 dag_df를 순회!
    parent_node_id = row['ID']
    if parent_node_id in aging_map:
        aging_depth = row['DEPTH'] + 1  # ← row['DEPTH']는 shift 전 상태
```

**시나리오**:
```
원본:  N001(d=1) → N002(d=2) → N003(d=3)

Step 1: N001 after aging 추가
  - N001_AGING의 depth = 1 + 1 = 2
  - shift_depths 호출 → N002 shift: d=2→3, N003 shift: d=3→4
  - 결과: N001(1) → N001_A(2) → N002(3) → N003(4) ✓

Step 2: N003 after aging 추가 (문제!)
  - dag_df는 이미 shift된 상태인데...
  - row['DEPTH']는 원본 기준 depth=3을 사용!
  - N003_AGING의 depth = 3 + 1 = 4 (실제로는 4+1=5여야 함)
  - 결과: N003(4) → N003_A(4) ← 중복! ❌
```

#### 문제 2: 마지막 공정의 aging shift 실패
```python
# src/dag_management/dag_dataframe.py:254-309
# shift_depths_after_aging()에서:
descendants = []  # ← 마지막 공정은 children이 없음!
# 빈 descendants이면 shift가 아무것도 안 됨
```

---

## 2️⃣ 수정해야 하는 작업 (WHAT TO FIX)

### FIX-1: Sequential Aging Insertion ⭐ (권장)
**파일**: `src/dag_management/dag_dataframe.py`
**함수**: `insert_aging_nodes_to_dag()`
**라인**: 312-425
**난이도**: MEDIUM

**현재 방식**: 모든 aging을 한 번에 for 루프로 처리
**개선 방식**: aging 하나씩 삽입 후 즉시 shift → 다음 aging 처리

**의사코드**:
```python
def insert_aging_nodes_to_dag(dag_df, aging_map):
    result_df = dag_df.copy()

    # ✅ KEY: aging 하나씩 순차 처리
    for parent_node_id in sorted(aging_map.keys()):  # 깊이순 정렬 중요!
        info = aging_map[parent_node_id]

        # 1. 현재 dag_df 상태에서 parent의 depth 읽기
        parent_row = result_df[result_df['ID'] == parent_node_id]
        current_parent_depth = parent_row.iloc[0]['DEPTH']  # ← 최신 상태!

        # 2. Aging 노드 생성
        aging_depth = current_parent_depth + 1
        aging_node = create_aging_row(info, aging_depth)

        # 3. 즉시 DAG에 삽입
        result_df = add_aging_node_to_df(result_df, parent_node_id, aging_node, info)

        # 4. 즉시 shift (다음 aging에 반영됨)
        result_df = shift_depths_after_aging(info['aging_node_id'], aging_depth, result_df)

    return result_df.sort_values('DEPTH').reset_index(drop=True)
```

---

### FIX-2: Last Process Aging Shift
**파일**: `src/dag_management/dag_dataframe.py`
**함수**: `shift_depths_after_aging()`
**라인**: 254-309
**난이도**: LOW

**문제**: 마지막 공정의 aging은 children이 없어서 shift 안 됨
**해결**: Aging 노드도 shift 대상에 포함

**의사코드**:
```python
def shift_depths_after_aging(aging_node_id, aging_depth, df):
    """
    Shift descendants when aging node inserted

    ⚠️ Important: Aging node 다음의 노드도 포함!
    """
    # BFS로 descendants 찾기
    descendants = []
    queue = [aging_node_id]
    visited = set()

    while queue:
        current_id = queue.pop(0)
        # ... BFS 로직 ...

        # ✅ KEY: next_node_id도 확인 (children이 없어도!)
        # aging_map에서 next_node_id를 알았으니 직접 shift

    return df
```

---

### FIX-3: Depth Normalization Post-Processing ⭐⭐ (추가 안전장치)
**파일**: `src/dag_management/dag_dataframe.py` (새 함수)
**함수**: `normalize_depths_after_all_aging_insertions()`
**라인**: NEW
**난이도**: MEDIUM

**목적**: 모든 aging 삽입 후 전체 depth를 BFS로 재정규화
**장점**: FIX-1,2의 버그가 있어도 최종적으로 correct depths 보장

**의사코드**:
```python
def normalize_depths_post_aging(dag_df):
    """
    BFS로 source node부터 시작해서 각 노드의 depth를 재할당

    이 함수 실행 후에는 depth가 반드시 unique + topological order 보장
    """
    # 1. Source node 찾기 (parent_node_count == 0인 노드)
    # 2. BFS로 traversal
    # 3. 방문 순서대로 depth 재할당

    return dag_df  # depth가 정규화된 상태
```

---

## 3️⃣ 구체적인 해야할 일 (ACTION ITEMS)

### Phase 1: 코드 수정 (2-3시간)

#### Task 1-1: insert_aging_nodes_to_dag() 리팩토링
- [ ] **파일**: `src/dag_management/dag_dataframe.py:312-425`
- [ ] **작업**:
  1. 기존 for 루프 삭제
  2. `insert_aging_nodes_sequentially()` 함수 생성
  3. Aging을 하나씩 처리하는 루프 작성
  4. 각 iteratio에서 현재 dag_df 상태를 읽도록 수정
  5. 각 aging 삽입 후 즉시 shift 호출
- [ ] **테스트**: 단일 aging, 다중 aging, 마지막 aging 케이스

**코드 스니펫**:
```python
def insert_aging_nodes_sequentially(dag_df, aging_map):
    """새로운 함수: Sequential insertion"""
    result_df = dag_df.copy()

    # aging_map의 키를 parent_depth 순으로 정렬
    sorted_parents = sorted(
        aging_map.keys(),
        key=lambda x: result_df[result_df['ID']==x].iloc[0]['DEPTH']
    )

    for parent_id in sorted_parents:
        # ... sequential 처리 ...

    return result_df
```

---

#### Task 1-2: shift_depths_after_aging() 개선
- [ ] **파일**: `src/dag_management/dag_dataframe.py:254-309`
- [ ] **작업**:
  1. 마지막 공정의 aging 케이스 처리 추가
  2. BFS 로직에서 next_node_id도 포함
  3. Edge case (depth < aging_depth인 노드) 처리
- [ ] **테스트**: 마지막 공정, 중간 공정, 여러 자식 케이스

---

#### Task 1-3: normalize_depths_post_aging() 함수 추가
- [ ] **파일**: `src/dag_management/dag_dataframe.py` (새 함수)
- [ ] **작업**:
  1. `normalize_depths_post_aging()` 함수 작성
  2. BFS 기반 depth 재할당 로직
  3. 불변성 검증 (모든 depth unique 확인)
- [ ] **사용처**: `insert_aging_nodes_to_dag()` 끝에서 호출
- [ ] **테스트**: 모든 aging 케이스의 최종 depth 검증

---

### Phase 2: 통합 테스트 (1-2시간)

#### Task 2-1: 단위 테스트 작성
- [ ] **파일**: `tests/test_aging_depth_fix.py` (새 파일)
- [ ] **테스트 케이스**:
  1. ✅ `test_single_aging_depth` - 하나의 aging만
  2. ✅ `test_two_aging_depth` - 두 개 aging (현재 버그 케이스)
  3. ✅ `test_three_aging_depth` - 세 개 이상
  4. ✅ `test_last_process_aging` - 마지막 공정의 aging
  5. ✅ `test_depth_uniqueness` - 모든 depth가 unique한지
  6. ✅ `test_topological_order` - depth가 topological order 따르는지

**테스트 예시**:
```python
def test_two_aging_depth():
    """현재 버그를 재현하는 테스트"""
    aging_map = {
        'N001': {'aging_node_id': 'N001_A', 'aging_time': 48, 'next_node_id': 'N002'},
        'N003': {'aging_node_id': 'N003_A', 'aging_time': 48, 'next_node_id': None}
    }
    dag_df = ... # Create test DAG

    result_df = insert_aging_nodes_to_dag(dag_df, aging_map)

    # ✅ Assert: 모든 depth가 unique해야 함
    assert len(result_df['DEPTH'].unique()) == len(result_df), "Depth duplication!"

    # ✅ Assert: 마지막 aging의 depth도 정확해야 함
    n003_a = result_df[result_df['ID'] == 'N003_A']
    n003 = result_df[result_df['ID'] == 'N003']
    assert n003_a.iloc[0]['DEPTH'] > n003.iloc[0]['DEPTH'], "Aging should be after parent"
```

---

#### Task 2-2: 엔드-투-엔드 테스트
- [ ] **파일**: `tests/test_aging_e2e.py` (수정)
- [ ] **작업**:
  1. 실제 aging_df로 full pipeline 실행
  2. Scheduling 결과에서 aging 노드 확인
  3. Depth와 scheduling order 일치 확인
- [ ] **테스트 시나리오**:
  - 3개 공정 + 2개 aging
  - 5개 공정 + 3개 aging
  - 마지막 공정에만 aging

---

### Phase 3: 문서화 및 배포 (1시간)

#### Task 3-1: 수정 내용 문서화
- [ ] `docs/aging_depth_fix_summary.md` 작성
  - 문제 설명
  - 해결 방법
  - 변경사항 요약
  - Breaking changes 없음 확인

#### Task 3-2: CLAUDE.md 업데이트
- [ ] Aging 섹션에 "Depth 정규화됨" 추가

#### Task 3-3: 변경사항 테스트
- [ ] 기존 모든 테스트 통과 확인
- [ ] 새로운 테스트 통과 확인
- [ ] Backward compatibility 확인

---

## 4️⃣ 타임라인 및 우선순위

| Task | 시간 | 우선순위 | 담당 |
|------|------|---------|------|
| 1-1: insert_aging_nodes_to_dag() 리팩토링 | 1.5h | 🔥 CRITICAL | Claude |
| 1-2: shift_depths_after_aging() 개선 | 0.5h | 🔥 CRITICAL | Claude |
| 1-3: normalize_depths_post_aging() 추가 | 1h | 🔥 CRITICAL | Claude |
| 2-1: 단위 테스트 작성 | 1h | 🟡 HIGH | Claude |
| 2-2: E2E 테스트 | 0.5h | 🟡 HIGH | Claude |
| 3-1: 문서화 | 0.5h | 🟢 MEDIUM | Claude |
| 3-2: CLAUDE.md 업데이트 | 0.2h | 🟢 LOW | Claude |
| **총소요시간** | **~5.2h** | - | - |

---

## 5️⃣ 검증 기준 (DONE CRITERIA)

### ✅ 수정 완료 기준
1. **Depth 중복 없음**
   - `len(df['DEPTH'].unique()) == len(df)` ✓

2. **Topological 순서 유지**
   - Parent depth < Child depth 항상 만족 ✓

3. **Parent-child 관계 정확**
   - CHILDREN 컬럼이 정확한 자식 노드 가리킴 ✓

4. **모든 테스트 통과**
   - 기존 테스트: 100% PASS ✓
   - 새 테스트: 100% PASS ✓

5. **Scheduling 정상 작동**
   - Aging 노드들이 올바른 순서로 스케줄됨 ✓
   - Overlapping 정상 작동 ✓

---

## 6️⃣ 예상 영향도

### 변경 범위
- **수정 파일**: 1개 (`src/dag_management/dag_dataframe.py`)
- **신규 함수**: 2개 (`insert_aging_nodes_sequentially`, `normalize_depths_post_aging`)
- **수정 함수**: 1개 (`shift_depths_after_aging`)
- **Breaking change**: ❌ 없음 (같은 입출력 인터페이스)

### 영향받는 컴포넌트
- ✅ DAG 생성 (`create_complete_dag_system`)
- ✅ Scheduler (depth 정규화로 더 안정적)
- ✅ Results processing (depth 기반 컬럼명)

---

## 7️⃣ Rollback 계획

만약 문제 발생 시:
```bash
git revert <commit_hash>  # 이전 버전으로 복구
```

기존 코드도 작동하지만 depth 중복 문제 있음을 문서에 명시

---

## 다음 단계

**지금 바로 할 것**:
1. 이 계획서 검토 및 확인 ✓ (지금)
2. Phase 1 코드 수정 시작
3. Phase 2 테스트 작성
4. Phase 3 배포

**확인 필요**:
- [ ] 이 계획이 맞는가?
- [ ] 다른 접근 방식이 있는가?
- [ ] 우선순위 조정 필요한가?

