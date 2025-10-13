# Mixture Selection Logic Documentation

## 개요
배합액(Mixture) 선택 로직은 스케줄링 과정에서 각 노드가 사용할 배합액을 결정하고, 이를 통해 공정 교체 시간을 최소화하는 메커니즘입니다.

## 현재 구조

### 1. 데이터 구조
- **MIXTURE_LIST** (튜플): 각 노드가 사용 가능한 배합액 목록
  - `()`: 배합액 사용 안함
  - `('A',)`: A만 사용 가능
  - `('A', 'B')`: A 우선, B 차선 (순서가 우선순위를 의미)

- **SELECTED_MIXTURE** (문자열 or None): 실제로 선택된 배합액
  - 초기값: `None`
  - 스케줄링 후: 실제 선택된 배합액 값 (예: 'A', 'B', None)

### 2. 현재 문제점
- SELECTED_MIXTURE가 활용되지 않음 (항상 None)
- DelayProcessor가 MIXTURE_LIST를 직접 비교하여 부정확한 지연시간 계산
- 배합액 선택 최적화가 이루어지지 않음

## 변경 계획

### Phase 1: 배합액 선택 헬퍼 함수 추가

#### 위치: `scheduling_core.py`

```python
def find_best_mixture(first_node_dict, window_nodes, dag_manager):
    """
    첫 노드의 MIXTURE_LIST에서 최적 배합액 선택

    로직:
    1. 첫 노드의 MIXTURE_LIST 확인
    2. 각 배합액에 대해 윈도우 내 사용 가능한 노드 수 카운트
    3. 가장 많이 사용 가능한 배합액 반환

    예시:
    첫 노드: ('A', 'B')
    윈도우 노드들의 MIXTURE_LIST:
    - 노드2: ('A', 'C') → A 가능
    - 노드3: ('B', 'C') → B 가능
    - 노드4: ('B', 'D') → B 가능

    결과: B 선택 (2개 노드에서 사용 가능)
    """
```

### Phase 2: SetupMinimizedStrategy 수정

#### 위치: `scheduling_core.py` - `SetupMinimizedStrategy.execute()`

#### 변경 로직:

1. **첫 노드 스케줄링 시**
   ```
   1. 윈도우 내 모든 노드의 MIXTURE_LIST 분석
   2. find_best_mixture()로 최적 배합액 결정
   3. 첫 노드의 SELECTED_MIXTURE 설정
   4. 첫 노드 스케줄링
   ```

2. **같은 배합액 그룹 생성**
   ```
   1. 선택된 배합액이 MIXTURE_LIST에 포함된 노드들 찾기
   2. 해당 노드들의 SELECTED_MIXTURE를 동일하게 설정
   3. 너비 기준 정렬 후 연속 스케줄링
   ```

3. **같은 공정, 다른 배합액 그룹 반복 처리**
   ```
   same_operation_queue에서 아직 처리 안 된 노드들 반복:

   while (남은 노드가 있는 동안):
      a. 남은 노드 중 첫 번째를 새로운 리더로 선정
      b. 해당 리더의 MIXTURE_LIST 기준으로 최적 배합액 선택
         (남은 노드들 중 가장 많이 사용 가능한 배합액)
      c. 남은 노드들 중 해당 배합액 사용 가능한 노드 그룹화
      d. 각 노드의 SELECTED_MIXTURE 설정
      e. 너비 기준 정렬 후 스케줄링
      f. 처리된 노드들을 남은 노드 리스트에서 제거

   4. 모든 same_operation 노드 처리 완료 후 return used_ids
   ```

### Phase 3: DelayProcessor 수정

#### 위치: `delay_dict.py` - `DelayProcessor.calculate_delay()`

#### 변경 사항:
```
이전: earlier["MIXTURE_LIST"] == later["MIXTURE_LIST"]
변경: earlier["SELECTED_MIXTURE"] == later["SELECTED_MIXTURE"]
```

#### None 처리:
```python
# 둘 다 None인 경우도 같은 것으로 처리
if earlier_mixture == later_mixture:  # None == None은 True
    same_mixture = True
```

## 실행 흐름 예시

### 시나리오
```
Node 1: 공정A, MIXTURE_LIST = ('X', 'Y')
Node 2: 공정A, MIXTURE_LIST = ('X', 'Z')
Node 3: 공정A, MIXTURE_LIST = ('Y', 'Z')
Node 4: 공정A, MIXTURE_LIST = ('Z')
Node 5: 공정B, MIXTURE_LIST = ('X')
```

### 스케줄링 과정

1. **윈도우 생성** (Node 1-5)

2. **첫 노드(Node 1) 처리**
   - Node 1의 선택지: X, Y
   - X 사용 가능: Node 2 (1개)
   - Y 사용 가능: Node 3 (1개)
   - **결과: X 선택** (동수일 경우 첫번째)
   - Node 1: SELECTED_MIXTURE = 'X', 스케줄링

3. **같은 배합액 그룹 처리 (X 그룹)**
   - Node 2: SELECTED_MIXTURE = 'X'
   - [Node 2] 스케줄링

4. **같은 공정, 다른 배합액 그룹 반복 처리**

   **첫 번째 반복 - 남은 same_operation_queue: [Node 3, Node 4]**
   - 리더: Node 3
   - Node 3의 선택지: Y, Z
   - Y 사용 가능: 0개
   - Z 사용 가능: Node 4 (1개)
   - **결과: Z 선택**
   - Node 3: SELECTED_MIXTURE = 'Z'
   - Node 4: SELECTED_MIXTURE = 'Z'
   - [Node 3, Node 4] 너비 정렬 후 스케줄링

   **두 번째 반복 - 남은 노드 없음, 종료**

5. **최종 스케줄링 순서**
   - Node 1 (X) → Node 2 (X) → Node 3 (Z) → Node 4 (Z)

6. **지연시간 계산 결과**
   - Node 1 → 2: 같은 배합액(X), 지연 최소
   - Node 2 → 3: 다른 배합액(X→Z), 교체 지연 발생
   - Node 3 → 4: 같은 배합액(Z), 지연 최소

## 효과

1. **Setup 시간 감소**: 같은 배합액 작업 연속 배치로 교체 횟수 최소화
2. **자동 최적화**: 각 그룹별로 가장 많이 사용되는 배합액 우선 선택
3. **정확한 지연시간**: 실제 선택된 배합액(SELECTED_MIXTURE) 기준 계산
4. **동적 그룹화**: 같은 공정 내에서도 배합액별 서브그룹 형성으로 효율 극대화

## 구현 우선순위

1. ✅ opnode_dict 구조 변경 (완료)
2. ⏳ 배합액 선택 헬퍼 함수 추가
3. ⏳ SetupMinimizedStrategy 수정
4. ⏳ DelayProcessor 수정
5. ⏳ 테스트 및 검증

## 주의사항

- MIXTURE_LIST는 읽기 전용 (가능한 옵션)
- SELECTED_MIXTURE만 수정 (실제 선택)
- 빈 튜플 `()` 처리 시 None 반환
- 스케줄링 전 모든 노드의 SELECTED_MIXTURE는 None