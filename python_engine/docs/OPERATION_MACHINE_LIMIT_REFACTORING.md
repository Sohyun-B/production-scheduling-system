# operation_machine_limit 함수 리팩토링 계획

## 📋 현재 문제점

### 1. Linespeed 형태 불일치

#### 전처리 후 실제 형태 (Long Format)
```python
# 컬럼: ['gitemno', 'proccode', 'machineno', 'linespeed', ...]
   gitemno  proccode  machineno  linespeed
0    32265     20500      C2270       27.0
1    32265     20500      C2250        0.0
2    32267     20500      C2270       26.5
```

#### operation_machine_limit()가 예상하는 형태 (Wide Format)
```python
# 컬럼: ['gitemno', 'proccode', 'C2270', 'C2250', 'A2020', ...]
   gitemno  proccode  C2270  C2250  A2020
0    32265     20500   27.0    0.0   99.0
1    32267     20500   26.5    NaN   99.0
```

### 2. 문제 발생 지점

#### operation_machine_limit.py:21-22
```python
valid_machine_codes = set(linespeed.columns)
machine_code_set = valid_machine_codes - {config.columns.OPERATION_CODE, config.columns.GITEM}
```
**문제:** Long Format에서는 `machine_code_set`에 `['gitemname', 'procname', 'machineno', 'machinename', 'linespeed', 'selected']`가 포함됨

#### operation_machine_limit.py:64-73 (operation_machine_global_limit)
```python
machine_cols = [c for c in linespeed.columns if c not in {config.columns.OPERATION_CODE, config.columns.GITEM}]

melted = linespeed.melt(
    id_vars=id_cols,
    value_vars=machine_cols,  # ← 여기서 잘못된 컬럼들을 melt
    var_name=config.columns.MACHINE_CODE,
    value_name="__SPEED__",
)
```
**문제:** 이미 Long Format인데 다시 melt()를 시도하여 데이터 구조가 완전히 깨짐

#### 결과
- C2270 등의 실제 기계 정보가 손실됨
- 최종적으로 machine_dict에서 모든 기계가 9999(사용 불가)로 설정됨

---

## 🎯 수정 방식

### 전략: Long Format 기반 로직으로 전면 재작성

#### 핵심 원칙
1. **Wide Format 변환 금지**: 이미 Long Format이므로 melt() 제거
2. **직접 필터링**: Long Format에서 직접 행을 삭제하는 방식 사용
3. **안전성 유지**: 모든 기계가 제거되어 생산 불가능해지는 상황 방지

---

## 📝 함수별 수정 계획

### 1. operation_machine_limit() - 메인 함수

#### 현재 로직 (Wide Format 기반)
```python
def operation_machine_limit(linespeed, local_machine_limit, global_machine_limit):
    # 1. local_machine_limit에서 제약조건 추출
    # 2. machine_codes를 컬럼명으로 인식
    # 3. linespeed.loc[mask, machine_codes] = np.nan  # Wide 방식
    # 4. operation_machine_global_limit() 호출
    # 5. _check_unable_order() 호출
```

#### 수정 로직 (Long Format 기반)
```python
def operation_machine_limit(linespeed, local_machine_limit, global_machine_limit):
    """
    Long Format 기반 기계 제약조건 적용

    Args:
        linespeed: DataFrame [gitemno, proccode, machineno, linespeed, ...]
        local_machine_limit: DataFrame [proccode, machineno]
        global_machine_limit: DataFrame [gitemno, proccode, machineno]

    Returns:
        filtered_linespeed: 제약조건 적용 후 DataFrame
        unable_gitems: 생산 불가능한 GITEM 리스트
        unable_details: 생산 불가능한 (GITEM, 공정) 상세 정보
    """

    # 1. Local 제약조건 적용 (공정별 기계 제외)
    if not local_machine_limit.empty:
        # Long Format에서는 (proccode, machineno) 조합을 직접 제거
        # 단, 안전성 검사: 제거 후에도 최소 1개 기계가 남는지 확인
        linespeed = apply_local_machine_limit(linespeed, local_machine_limit)

    # 2. Global 제약조건 적용 (GITEM+공정별 기계 제외)
    if global_machine_limit is not None and not global_machine_limit.empty:
        linespeed = apply_global_machine_limit(linespeed, global_machine_limit)

    # 3. 생산 불가능한 항목 확인
    unable_gitems, unable_details = check_unable_items(linespeed)

    return linespeed, unable_gitems, unable_details
```

---

### 2. apply_local_machine_limit() - 신규 함수

#### 목적
Local 제약조건 (공정별 기계 제외)을 Long Format에 맞게 적용

#### 로직
```python
def apply_local_machine_limit(linespeed, local_machine_limit):
    """
    Local 제약조건 적용: 특정 공정에서 특정 기계 제외

    예시:
        local_machine_limit:
            proccode  machineno
            20500     C2010
            20906     A2020

        → 20500 공정에서 C2010 제거, 20906 공정에서 A2020 제거

    안전성:
        - 제거 후 해당 (gitemno, proccode)가 모든 기계 불가능이 되면 제거 취소
    """

    # 1. 제약조건 정제
    constraints = local_machine_limit[
        [config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]
    ].dropna().drop_duplicates()

    if constraints.empty:
        return linespeed

    # 2. 각 제약조건별로 처리
    for _, row in constraints.iterrows():
        proccode = row[config.columns.OPERATION_CODE]
        machineno = row[config.columns.MACHINE_CODE]

        # 제거 후보 마스크
        drop_mask = (
            (linespeed[config.columns.OPERATION_CODE] == proccode) &
            (linespeed[config.columns.MACHINE_CODE] == machineno)
        )

        # 안전성 검사: 이 제약조건을 적용했을 때 생산 불가능해지는 GITEM이 있는지
        if drop_mask.any():
            affected_gitems = linespeed.loc[drop_mask, config.columns.GITEM].unique()

            # 각 affected_gitem에 대해 다른 기계가 남아있는지 확인
            safe_to_drop = []
            for gitem in affected_gitems:
                # 해당 gitem + proccode의 모든 행
                gitem_proc_mask = (
                    (linespeed[config.columns.GITEM] == gitem) &
                    (linespeed[config.columns.OPERATION_CODE] == proccode)
                )

                # 제거 후 남는 행 (유효한 linespeed > 0)
                remaining_after_drop = linespeed.loc[
                    gitem_proc_mask & ~drop_mask &
                    (linespeed['linespeed'] > 0)
                ]

                # 최소 1개 기계가 남으면 안전
                if len(remaining_after_drop) > 0:
                    safe_to_drop.append(gitem)

            # 안전한 gitem에 대해서만 제거
            if safe_to_drop:
                final_drop_mask = drop_mask & linespeed[config.columns.GITEM].isin(safe_to_drop)
                linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
                print(f"[Local 제약] 공정 {proccode}, 기계 {machineno} 제거: {len(safe_to_drop)}개 GITEM")
            else:
                print(f"[Local 제약] 공정 {proccode}, 기계 {machineno} 제거 불가 (생산 불가능 위험)")

    return linespeed
```

---

### 3. apply_global_machine_limit() - 기존 함수 재작성

#### 현재 문제
- Wide Format 기반으로 melt()를 시도함
- 이미 Long Format인데 또 melt()를 해서 데이터 손실

#### 수정 로직
```python
def apply_global_machine_limit(linespeed, global_machine_limit):
    """
    Global 제약조건 적용: 특정 (GITEM, 공정, 기계) 조합 제외

    예시:
        global_machine_limit:
            gitemno  proccode  machineno
            32265    20500     C2010
            32267    20906     A2020

        → GITEM 32265 + 공정 20500에서 C2010 제거
        → GITEM 32267 + 공정 20906에서 A2020 제거

    안전성:
        - 제거 후 해당 (gitemno, proccode)가 모든 기계 불가능이 되면 제거 취소
    """

    # 1. 필수 컬럼 확인
    required_cols = {config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE}
    if not required_cols.issubset(set(global_machine_limit.columns)):
        return linespeed

    # 2. 제약조건 정제
    constraints = global_machine_limit[list(required_cols)].dropna().drop_duplicates()

    if constraints.empty:
        return linespeed

    # 3. Long Format에서 직접 매칭 및 제거
    # (gitemno, proccode, machineno) 조합 생성
    linespeed['__KEY__'] = (
        linespeed[config.columns.GITEM].astype(str) + '|' +
        linespeed[config.columns.OPERATION_CODE].astype(str) + '|' +
        linespeed[config.columns.MACHINE_CODE].astype(str)
    )

    constraints['__KEY__'] = (
        constraints[config.columns.GITEM].astype(str) + '|' +
        constraints[config.columns.OPERATION_CODE].astype(str) + '|' +
        constraints[config.columns.MACHINE_CODE].astype(str)
    )

    blacklist_keys = set(constraints['__KEY__'].unique())

    # 제거 후보 마스크
    drop_mask = linespeed['__KEY__'].isin(blacklist_keys)

    # 4. 안전성 검사: 제거 후 생산 불가능해지는 (gitemno, proccode) 조합 확인
    if drop_mask.any():
        affected_keys = linespeed.loc[drop_mask, [config.columns.GITEM, config.columns.OPERATION_CODE]].drop_duplicates()

        safe_to_drop = []
        for _, row in affected_keys.iterrows():
            gitem = row[config.columns.GITEM]
            proccode = row[config.columns.OPERATION_CODE]

            # 해당 (gitem, proccode)의 모든 행
            gitem_proc_mask = (
                (linespeed[config.columns.GITEM] == gitem) &
                (linespeed[config.columns.OPERATION_CODE] == proccode)
            )

            # 제거 후 남는 유효한 행 (linespeed > 0)
            remaining_after_drop = linespeed.loc[
                gitem_proc_mask & ~drop_mask &
                (linespeed['linespeed'] > 0)
            ]

            # 최소 1개 기계가 남으면 안전
            if len(remaining_after_drop) > 0:
                safe_to_drop.append((gitem, proccode))

        # 안전한 항목에 대해서만 제거
        if safe_to_drop:
            safe_gitem_proccode = set(safe_to_drop)
            final_drop_mask = drop_mask & linespeed.apply(
                lambda row: (row[config.columns.GITEM], row[config.columns.OPERATION_CODE]) in safe_gitem_proccode,
                axis=1
            )
            linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
            print(f"[Global 제약] {len(blacklist_keys)}개 조합 제거, {len(safe_to_drop)}개 (gitem, 공정) 영향")
        else:
            print(f"[Global 제약] 제거 불가 (모든 항목이 생산 불가능 위험)")

    # 5. 임시 컬럼 제거
    linespeed = linespeed.drop(columns=['__KEY__'])

    return linespeed
```

---

### 4. check_unable_items() - 기존 _check_unable_order() 재작성

#### 현재 문제
- Wide Format 기반으로 `all_machine_columns`를 받아서 `.isna().all(axis=1)` 체크
- Long Format에서는 작동하지 않음

#### 수정 로직
```python
def check_unable_items(linespeed):
    """
    생산 불가능한 (GITEM, 공정) 조합 확인

    Long Format에서는:
    - 각 (gitemno, proccode) 그룹에 유효한 linespeed (> 0)가 하나도 없으면 생산 불가능
    """

    # 유효한 linespeed만 추출 (> 0)
    valid_linespeed = linespeed[linespeed['linespeed'] > 0]

    # (gitemno, proccode) 그룹별 카운트
    group_counts = valid_linespeed.groupby(
        [config.columns.GITEM, config.columns.OPERATION_CODE]
    ).size().reset_index(name='valid_count')

    # 원본 linespeed의 모든 (gitemno, proccode) 조합
    all_combinations = linespeed[
        [config.columns.GITEM, config.columns.OPERATION_CODE]
    ].drop_duplicates()

    # Left join으로 카운트가 없는 조합 찾기
    merged = all_combinations.merge(
        group_counts,
        on=[config.columns.GITEM, config.columns.OPERATION_CODE],
        how='left'
    )
    merged['valid_count'] = merged['valid_count'].fillna(0)

    # 유효한 기계가 없는 조합
    unable_items = merged[merged['valid_count'] == 0]

    if not unable_items.empty:
        unable_gitems = unable_items[config.columns.GITEM].astype(str).unique().tolist()
        unable_details = unable_items.to_dict('records')

        print(f"[경고] 생산 불가능한 항목: {len(unable_items)}개 (gitemno, proccode) 조합")
        print(f"[경고] 생산 불가능한 GITEM: {len(unable_gitems)}개")

        return unable_gitems, unable_details
    else:
        return [], []
```

---

### 5. operation_machine_exclusive() - 독점 할당 함수

#### 현재 문제
- Wide Format 기반 (기계를 컬럼으로 인식)

#### 수정 로직
```python
def operation_machine_exclusive(linespeed, machine_allocate):
    """
    특정 공정을 특정 기계에서만 수행하도록 독점 할당

    예시:
        machine_allocate:
            proccode  machineno
            20500     C2270

        → 20500 공정은 C2270에서만 수행 (다른 기계 제거)

    안전성:
        - 독점 할당으로 생산 불가능해지는 GITEM은 원본 유지
    """

    # 1. 제약조건 정제
    constraints = machine_allocate[
        [config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]
    ].dropna().drop_duplicates()

    if constraints.empty:
        print("독점 할당할 기계가 없음")
        return linespeed

    # 2. 각 제약조건별로 처리
    for _, row in constraints.iterrows():
        proccode = row[config.columns.OPERATION_CODE]
        allocated_machine = row[config.columns.MACHINE_CODE]

        # 해당 공정의 모든 행
        proc_mask = linespeed[config.columns.OPERATION_CODE] == proccode

        if not proc_mask.any():
            continue

        # 제거 대상: 같은 공정이지만 다른 기계
        drop_mask = proc_mask & (linespeed[config.columns.MACHINE_CODE] != allocated_machine)

        # 안전성 검사: 독점 할당 후 생산 불가능해지는 GITEM 확인
        if drop_mask.any():
            affected_gitems = linespeed.loc[proc_mask, config.columns.GITEM].unique()

            safe_to_drop = []
            for gitem in affected_gitems:
                # 해당 gitem + proccode + allocated_machine 조합이 존재하고 유효한지
                allocated_row = linespeed.loc[
                    (linespeed[config.columns.GITEM] == gitem) &
                    (linespeed[config.columns.OPERATION_CODE] == proccode) &
                    (linespeed[config.columns.MACHINE_CODE] == allocated_machine) &
                    (linespeed['linespeed'] > 0)
                ]

                # 할당된 기계에서 처리 가능하면 안전
                if len(allocated_row) > 0:
                    safe_to_drop.append(gitem)

            # 안전한 gitem에 대해서만 제거
            if safe_to_drop:
                final_drop_mask = drop_mask & linespeed[config.columns.GITEM].isin(safe_to_drop)
                removed_count = final_drop_mask.sum()
                linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
                print(f"[독점 할당] 공정 {proccode} → 기계 {allocated_machine}: {removed_count}개 행 제거")
            else:
                print(f"[독점 할당] 공정 {proccode} → 기계 {allocated_machine}: 제거 불가 (모든 GITEM이 위험)")

    return linespeed
```

---

## ✅ 수정 후 기대 효과

### 1. 데이터 손실 방지
- Long Format에서 직접 행을 제거하므로 C2270 등의 기계 정보 보존
- 잘못된 melt() 제거로 데이터 구조 유지

### 2. 성능 향상
- Wide ↔ Long 변환 제거로 불필요한 연산 감소
- 직접 필터링으로 더 빠른 처리

### 3. 코드 가독성 향상
- Long Format 기반으로 일관된 로직
- Wide Format 가정 제거로 혼란 감소

### 4. 안전성 유지
- 모든 함수에서 "생산 불가능" 상황 사전 검사
- 제약조건 적용 후에도 최소 1개 기계는 남도록 보장

---

## 🧪 테스트 계획

### 1. 단위 테스트

#### Test 1: Local 제약조건 적용
```python
# Input:
linespeed = [
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2270', 'linespeed': 27.0},
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2010', 'linespeed': 25.0},
]
local_machine_limit = [
    {'proccode': '20500', 'machineno': 'C2010'}
]

# Expected Output:
# C2010 행 제거, C2270 행 유지
```

#### Test 2: Global 제약조건 적용 + 안전성 검사
```python
# Input:
linespeed = [
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2270', 'linespeed': 27.0},
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2010', 'linespeed': 0.0},  # 유효하지 않음
]
global_machine_limit = [
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2270'}
]

# Expected Output:
# C2270 제거하면 생산 불가능하므로 제거하지 않음
```

#### Test 3: 독점 할당
```python
# Input:
linespeed = [
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2270', 'linespeed': 27.0},
    {'gitemno': '32265', 'proccode': '20500', 'machineno': 'C2250', 'linespeed': 20.0},
]
machine_allocate = [
    {'proccode': '20500', 'machineno': 'C2270'}
]

# Expected Output:
# C2250 행 제거, C2270만 유지
```

### 2. 통합 테스트

main.py 실행 후:
1. 32265, 32263, 32267 + 20500 + C2270 조합이 machine_dict에 정상 값으로 존재하는지 확인
2. 스케줄링이 정상적으로 완료되는지 확인
3. 생산 불가능한 GITEM이 0개인지 확인

---

## 📌 주의사항

### 1. 컬럼명 통일
- `config.columns.GITEM` = "gitemno"
- `config.columns.OPERATION_CODE` = "proccode"
- `config.columns.MACHINE_CODE` = "machineno"

### 2. Linespeed 유효성 판단
- `linespeed > 0`: 유효한 속도
- `linespeed == 0 or linespeed == NaN`: 해당 기계 사용 불가

### 3. 안전성 우선
- 제약조건을 적용할 때 항상 "적용 후 생산 가능한가?" 먼저 검사
- 불가능하면 제약조건 적용 취소 (경고 메시지 출력)

### 4. 성능 최적화
- `apply()` 대신 벡터 연산 사용
- 불필요한 복사 방지 (`inplace=True` 지양, 필터링 마스크 사용)

---

## 📅 구현 순서

1. ✅ 문제 원인 파악 (완료)
2. 📝 이 문서 작성 (완료)
3. 🔧 새 함수 구현
   - `apply_local_machine_limit()`
   - `apply_global_machine_limit()` (재작성)
   - `check_unable_items()` (재작성)
   - `operation_machine_exclusive()` (재작성)
4. 🧪 단위 테스트 작성 및 실행
5. 🔄 `operation_machine_limit()` 메인 로직 수정
6. ✅ 통합 테스트 (main.py 실행)
7. 📊 결과 검증

---

## 🎯 최종 목표

**"32265, 32263, 32267의 20500 공정이 C2270에서 정상적으로 스케줄링되는 것"**

- machine_dict에 `{'C2270': 27}` 등으로 정상 값 저장
- 스케줄링 시 C2270 기계 선택 가능
- "사용 가능한 기계 없음" 경고 발생하지 않음
