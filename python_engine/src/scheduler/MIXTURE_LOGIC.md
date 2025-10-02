# Mixture Selection Logic Documentation

## 개요
배합액(Mixture) 선택 로직은 스케줄링 과정에서 각 노드가 사용할 배합액을 결정하고, 이를 통해 공정 교체 시간을 최소화하는 메커니즘입니다.

## 데이터 구조

### 1. MIXTURE_LIST (튜플)
각 노드가 사용 가능한 배합액 목록 (읽기 전용)
- `()`: 배합액 사용 안함
- `('A',)`: A만 사용 가능
- `('A', 'B')`: A 또는 B 사용 가능 (순서는 우선순위가 아님)

### 2. SELECTED_MIXTURE (문자열 or None)
실제로 선택된 배합액 (스케줄링 중 설정됨)
- 초기값: `None`
- 스케줄링 후: 실제 선택된 배합액 값 (예: 'A', 'B', None)

## 구현된 로직

### Phase 1: 배합액 선택 헬퍼 함수

#### 위치: `scheduling_core.py:214-252`

```python
def find_best_mixture(first_node_dict, window_nodes, dag_manager):
```

**기능**: 첫 노드의 MIXTURE_LIST에서 최적 배합액 선택

**로직**:
1. 첫 노드의 MIXTURE_LIST 확인
2. 각 배합액에 대해 window_nodes 내 사용 가능한 노드 수 카운트
3. 가장 많이 사용 가능한 배합액 반환 (동수일 경우 max 기준)
4. 배합액이 없으면 None 반환

**예시**:
```
첫 노드: ('A', 'B')
window_nodes의 MIXTURE_LIST:
- 노드2: ('A', 'C') → A 가능
- 노드3: ('B', 'C') → B 가능
- 노드4: ('B', 'D') → B 가능

결과: B 선택 (2개 노드에서 사용 가능)
```

### Phase 2: SetupMinimizedStrategy 수정

#### 위치: `scheduling_core.py:258-369`

#### 전체 실행 흐름:

**1. 첫 노드 스케줄링 (271-279행)**
```
- OptimalMachineStrategy로 첫 노드 스케줄링
- 할당된 기계 인덱스 저장
```

**2. 같은 공정 노드 추출 (281-287행)**
```
- 첫 노드의 OPERATION_CODE 추출
- 윈도우 내에서 같은 공정 노드들만 필터링 → same_operation_nodes
```

**3. 첫 노드 배합액 선택 (289-291행)**
```
- find_best_mixture(first_node_dict, same_operation_nodes, dag_manager) 호출
- 첫 노드의 SELECTED_MIXTURE 설정
```

**4. 같은 배합액 그룹 분리 (293-302행)**
```
- same_operation_nodes를 순회하며:
  - best_mixture를 사용 가능한 노드 → same_mixture_queue
  - 사용 불가능한 노드 → remaining_operation_queue
```

**5. 같은 배합액 그룹 처리 (304-324행)**
```
- same_mixture_queue를 너비 기준 내림차순 정렬
- 각 노드의 SELECTED_MIXTURE를 best_mixture로 설정
- 순차 스케줄링 (ForcedMachineStrategy 사용)
- 성공 시 used_ids에 추가
- 실패 시 remaining_operation_queue로 이동
```

**6. 남은 노드 반복 처리 (326-367행)**
```
while remaining_operation_queue가 비어있지 않은 동안:

    6-1. 리더 선정 (328-330행)
        - remaining_operation_queue[0]을 리더로 선정

    6-2. 리더의 최적 배합액 선택 (332-334행)
        - find_best_mixture(leader_dict, remaining_operation_queue, dag_manager)
        - 리더의 SELECTED_MIXTURE 설정

    6-3. 현재 배합액 그룹 생성 (336-346행)
        - current_mixture_group = [leader_id]
        - remaining_operation_queue[1:]을 순회하며:
          - leader_best_mixture 사용 가능 → current_mixture_group에 추가, SELECTED_MIXTURE 설정
          - 사용 불가능 → next_remaining에 추가

    6-4. 현재 그룹 정렬 (348-353행)
        - current_mixture_group을 너비 기준 내림차순 정렬

    6-5. 현재 그룹 스케줄링 (355-364행)
        - current_mixture_group을 순회하며 스케줄링
        - 성공 시 used_ids에 추가
        - 실패 시 next_remaining에 추가

    6-6. 다음 반복 준비 (366-367행)
        - remaining_operation_queue = next_remaining
```

**7. 반환 (369행)**
```
- used_ids 반환 (성공적으로 스케줄링된 모든 노드 ID 리스트)
```

### Phase 3: DelayProcessor 수정

#### 위치: `delay_dict.py:161-204`

#### 변경 사항:
```python
# 이전 (185-186행)
earlier_mixture = earlier["MIXTURE_LIST"]
later_mixture = later["MIXTURE_LIST"]

# 변경 후 (185-186행)
earlier_mixture = earlier["SELECTED_MIXTURE"]
later_mixture = later["SELECTED_MIXTURE"]
```

#### None 처리 (198-201행):
```python
# 3. mixture 동일 여부 확인 (SELECTED_MIXTURE 기준)
# 둘 다 None인 경우도 같은 것으로 처리
if earlier_mixture == later_mixture:
    same_mixture = True
```

## 실행 흐름 예시

### 시나리오
```
윈도우: Node 1-5
Node 1: 공정A, MIXTURE_LIST = ('X', 'Y'), 너비 100
Node 2: 공정A, MIXTURE_LIST = ('X', 'Z'), 너비 150
Node 3: 공정A, MIXTURE_LIST = ('Y', 'Z'), 너비 120
Node 4: 공정A, MIXTURE_LIST = ('Z',), 너비 90
Node 5: 공정B, MIXTURE_LIST = ('X',)
```

### 스케줄링 과정

**1. 윈도우 생성**
- window = [Node 1, Node 2, Node 3, Node 4, Node 5]

**2. 첫 노드(Node 1) 스케줄링**
- OptimalMachineStrategy로 Node 1 스케줄링
- 할당된 기계: 0번 기계

**3. 같은 공정 추출**
- same_operation_nodes = [Node 2, Node 3, Node 4] (공정A만)
- Node 5는 공정B이므로 제외

**4. 첫 노드 배합액 선택**
- Node 1의 선택지: ('X', 'Y')
- X 사용 가능: Node 2 (1개)
- Y 사용 가능: Node 3 (1개)
- **결과: X 선택** (동수, max 함수 기준)
- Node 1: SELECTED_MIXTURE = 'X'

**5. 같은 배합액 그룹 분리**
- same_mixture_queue = [Node 2] (X 사용 가능)
- remaining_operation_queue = [Node 3, Node 4] (X 사용 불가)

**6. 같은 배합액 그룹 처리**
- same_mixture_queue 정렬: [Node 2] (너비 150)
- Node 2: SELECTED_MIXTURE = 'X'
- Node 2 스케줄링 성공
- used_ids = [Node 1, Node 2]

**7. 남은 노드 반복 처리**

**첫 번째 반복 - remaining_operation_queue: [Node 3, Node 4]**
```
7-1. 리더: Node 3
7-2. Node 3의 선택지: ('Y', 'Z')
     - Y 사용 가능: 0개
     - Z 사용 가능: Node 4 (1개)
     - 결과: Z 선택
     - Node 3: SELECTED_MIXTURE = 'Z'
7-3. current_mixture_group = [Node 3]
     - Node 4: ('Z',) → Z 사용 가능 → current_mixture_group에 추가
     - Node 4: SELECTED_MIXTURE = 'Z'
     - current_mixture_group = [Node 3, Node 4]
     - next_remaining = []
7-4. 너비 정렬: [Node 3(너비 120), Node 4(너비 90)]
7-5. Node 3 스케줄링 성공, used_ids에 추가
     Node 4 스케줄링 성공, used_ids에 추가
7-6. remaining_operation_queue = []
```

**두 번째 반복**
- remaining_operation_queue가 비어있으므로 종료

**8. 최종 스케줄링 순서**
- Node 1 (공정A, X) → Node 2 (공정A, X) → Node 3 (공정A, Z) → Node 4 (공정A, Z)
- used_ids = [Node 1, Node 2, Node 3, Node 4]

**9. 지연시간 계산 결과**
- Node 1 → 2: SELECTED_MIXTURE 둘 다 'X', same_mixture = True
- Node 2 → 3: SELECTED_MIXTURE 'X' → 'Z', same_mixture = False (교체 지연 발생)
- Node 3 → 4: SELECTED_MIXTURE 둘 다 'Z', same_mixture = True

## 핵심 특징

### 1. 동적 배합액 선택
- MIXTURE_LIST의 순서는 우선순위가 아님
- 윈도우 내 사용 빈도를 기준으로 동적 선택

### 2. 스케줄링 실패 처리
- 같은 배합액 그룹에서 스케줄링 실패 시 remaining_operation_queue로 이동
- 다음 배합액 그룹에서 재시도 가능

### 3. 배합액별 서브그룹화
- 같은 공정 내에서도 배합액이 다르면 별도 그룹으로 처리
- 각 그룹은 너비 기준 내림차순 정렬

### 4. None 처리
- 배합액이 없는 공정: MIXTURE_LIST = (), SELECTED_MIXTURE = None
- None == None도 같은 배합액으로 처리

## 효과

1. **Setup 시간 감소**: 같은 배합액 작업 연속 배치로 교체 횟수 최소화
2. **자동 최적화**: 각 그룹별로 가장 많이 사용되는 배합액 우선 선택
3. **정확한 지연시간**: 실제 선택된 배합액(SELECTED_MIXTURE) 기준 계산
4. **동적 그룹화**: 같은 공정 내에서도 배합액별 서브그룹 형성으로 효율 극대화
5. **유연한 실패 처리**: 스케줄링 실패 시 다른 배합액 그룹에서 재시도

## 구현 상태

1. ✅ opnode_dict 구조 변경 (완료)
2. ✅ 배합액 선택 헬퍼 함수 추가 (완료)
3. ✅ SetupMinimizedStrategy 수정 (완료)
4. ✅ DelayProcessor 수정 (완료)
5. ⏳ 테스트 및 검증

## 주의사항

- MIXTURE_LIST는 읽기 전용 (가능한 옵션)
- SELECTED_MIXTURE만 수정 (실제 선택)
- 빈 튜플 `()` 처리 시 None 반환
- 스케줄링 전 모든 노드의 SELECTED_MIXTURE는 None
- MIXTURE_LIST의 순서는 우선순위가 아님 (사용 빈도 기반 선택)
