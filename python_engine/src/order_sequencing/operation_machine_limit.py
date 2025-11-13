"""
기계 제약조건 적용 모듈 (Long Format 기반)

리팩토링 히스토리:
- 이전: Wide Format 기반 (각 기계가 컬럼)
- 현재: Long Format 기반 (gitemno, proccode, machineno, linespeed)
"""

import numpy as np
import pandas as pd
from config import config


def operation_machine_limit(linespeed, local_machine_limit, global_machine_limit):
    """
    기계 제약조건 적용 (Long Format 기반)

    Args:
        linespeed: DataFrame [gitemno, proccode, machineno, linespeed, ...]
        local_machine_limit: DataFrame [proccode, machineno] - 공정별 기계 제외
        global_machine_limit: DataFrame [gitemno, proccode, machineno] - GITEM+공정별 기계 제외

    Returns:
        filtered_linespeed: 제약조건 적용 후 DataFrame
        unable_gitems: 생산 불가능한 GITEM 리스트
        unable_details: 생산 불가능한 (GITEM, 공정) 상세 정보
    """

    # 1. Local 제약조건 적용 (공정별 기계 제외)
    if local_machine_limit is not None and not local_machine_limit.empty:
        linespeed = apply_local_machine_limit(linespeed, local_machine_limit)

    # 2. Global 제약조건 적용 (GITEM+공정별 기계 제외)
    if global_machine_limit is not None and not global_machine_limit.empty:
        linespeed = apply_global_machine_limit(linespeed, global_machine_limit)

    # 3. 생산 불가능한 항목 확인
    unable_gitems, unable_details = check_unable_items(linespeed)

    return linespeed, unable_gitems, unable_details


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
    required_cols = {config.columns.OPERATION_CODE, config.columns.MACHINE_CODE}
    if not required_cols.issubset(set(local_machine_limit.columns)):
        print("[Local 제약] 필수 컬럼 없음, 스킵")
        return linespeed

    constraints = local_machine_limit[
        [config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]
    ].dropna().drop_duplicates()

    if constraints.empty:
        print("[Local 제약] 제약조건 없음")
        return linespeed

    print(f"[Local 제약] {len(constraints)}개 제약조건 처리 중...")

    # 2. 각 제약조건별로 처리
    total_removed = 0
    for _, row in constraints.iterrows():
        proccode = row[config.columns.OPERATION_CODE]
        machineno = row[config.columns.MACHINE_CODE]

        # 제거 후보 마스크
        drop_mask = (
            (linespeed[config.columns.OPERATION_CODE] == proccode) &
            (linespeed[config.columns.MACHINE_CODE] == machineno)
        )

        if not drop_mask.any():
            continue

        # 안전성 검사: 이 제약조건을 적용했을 때 생산 불가능해지는 GITEM이 있는지
        affected_gitems = linespeed.loc[drop_mask, config.columns.GITEM].unique()

        safe_to_drop = []
        for gitem in affected_gitems:
            # 해당 gitem + proccode의 모든 행
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
                safe_to_drop.append(gitem)

        # 안전한 gitem에 대해서만 제거
        if safe_to_drop:
            final_drop_mask = drop_mask & linespeed[config.columns.GITEM].isin(safe_to_drop)
            removed_count = final_drop_mask.sum()
            linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
            total_removed += removed_count
            print(f"[Local 제약] 공정 {proccode}, 기계 {machineno}: {removed_count}개 행 제거")
        else:
            print(f"[Local 제약] 공정 {proccode}, 기계 {machineno}: 제거 불가 (생산 불가능 위험)")

    print(f"[Local 제약] 완료: 총 {total_removed}개 행 제거")
    return linespeed


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
        print("[Global 제약] 필수 컬럼 없음, 스킵")
        return linespeed

    # 2. 제약조건 정제
    constraints = global_machine_limit[list(required_cols)].dropna().drop_duplicates()

    if constraints.empty:
        print("[Global 제약] 제약조건 없음")
        return linespeed

    print(f"[Global 제약] {len(constraints)}개 제약조건 처리 중...")

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
    total_removed = 0
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
            total_removed = final_drop_mask.sum()
            linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
            print(f"[Global 제약] {len(blacklist_keys)}개 조합 중 {total_removed}개 행 제거, {len(safe_to_drop)}개 (gitem, 공정) 영향")
        else:
            print(f"[Global 제약] 제거 불가 (모든 항목이 생산 불가능 위험)")

    # 5. 임시 컬럼 제거
    linespeed = linespeed.drop(columns=['__KEY__'])

    print(f"[Global 제약] 완료: 총 {total_removed}개 행 제거")
    return linespeed


def check_unable_items(linespeed):
    """
    생산 불가능한 (GITEM, 공정) 조합 확인

    Long Format에서는:
    - 각 (gitemno, proccode) 그룹에 유효한 linespeed (> 0)가 하나도 없으면 생산 불가능

    Returns:
        unable_gitems: 생산 불가능한 GITEM 리스트 (unique)
        unable_details: 생산 불가능한 (gitemno, proccode) 상세 정보
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
        unable_details = [
            {
                'gitem': str(row[config.columns.GITEM]),
                'operation': row[config.columns.OPERATION_CODE]
            }
            for _, row in unable_items.iterrows()
        ]

        print(f"\n[경고] 생산 불가능한 항목: {len(unable_items)}개 (gitemno, proccode) 조합")
        print(f"[경고] 생산 불가능한 GITEM: {len(unable_gitems)}개")

        return unable_gitems, unable_details
    else:
        return [], []


def operation_machine_exclusive(linespeed, machine_allocate):
    """
    특정 공정을 특정 기계에서만 수행하도록 독점 할당 (Long Format 기반)

    예시:
        machine_allocate:
            proccode  machineno
            20500     C2270

        → 20500 공정은 C2270에서만 수행 (다른 기계 제거)

    안전성:
        - 독점 할당으로 생산 불가능해지는 GITEM은 원본 유지
    """

    # 1. 제약조건 정제
    required_cols = {config.columns.OPERATION_CODE, config.columns.MACHINE_CODE}
    if not required_cols.issubset(set(machine_allocate.columns)):
        print("[독점 할당] 필수 컬럼 없음, 스킵")
        return linespeed

    constraints = machine_allocate[
        [config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]
    ].dropna().drop_duplicates()

    if constraints.empty:
        print("독점 할당할 기계가 없음")
        return linespeed

    print(f"[독점 할당] {len(constraints)}개 제약조건 처리 중...")

    # 2. 각 제약조건별로 처리
    total_removed = 0
    for _, row in constraints.iterrows():
        proccode = row[config.columns.OPERATION_CODE]
        allocated_machine = row[config.columns.MACHINE_CODE]

        # 해당 공정의 모든 행
        proc_mask = linespeed[config.columns.OPERATION_CODE] == proccode

        if not proc_mask.any():
            print(f"[독점 할당] 공정 {proccode}: 데이터 없음, 스킵")
            continue

        # 제거 대상: 같은 공정이지만 다른 기계
        drop_mask = proc_mask & (linespeed[config.columns.MACHINE_CODE] != allocated_machine)

        if not drop_mask.any():
            print(f"[독점 할당] 공정 {proccode} → 기계 {allocated_machine}: 이미 독점 상태")
            continue

        # 안전성 검사: 독점 할당 후 생산 불가능해지는 GITEM 확인
        affected_gitems = linespeed.loc[proc_mask, config.columns.GITEM].unique()

        safe_to_drop = []
        unsafe_gitems = []
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
            else:
                unsafe_gitems.append(gitem)

        # 안전한 gitem에 대해서만 제거
        if safe_to_drop:
            final_drop_mask = drop_mask & linespeed[config.columns.GITEM].isin(safe_to_drop)
            removed_count = final_drop_mask.sum()
            linespeed = linespeed[~final_drop_mask].reset_index(drop=True)
            total_removed += removed_count
            print(f"[독점 할당] 공정 {proccode} → 기계 {allocated_machine}: {removed_count}개 행 제거 ({len(safe_to_drop)}개 GITEM)")

            if unsafe_gitems:
                print(f"[독점 할당] 공정 {proccode}: {len(unsafe_gitems)}개 GITEM은 원본 유지 (안전성)")
        else:
            print(f"[독점 할당] 공정 {proccode} → 기계 {allocated_machine}: 제거 불가 (모든 GITEM이 위험)")

    print(f"[독점 할당] 완료: 총 {total_removed}개 행 제거")
    return linespeed
