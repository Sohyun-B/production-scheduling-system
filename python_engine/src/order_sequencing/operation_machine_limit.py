import numpy as np
import pandas as pd
from config import config

def operation_machine_limit(linespeed, local_machine_limit, global_machine_limit):
    """
    해당 기계에서 해당 공정을 수행하지 않게 제한하는 경우 라인스피드를 사용하지 못하는 방식으로 변경
            
    linespeed:
        GITEM, 공정, 각 기계코드의 이름의 라인스피드 컬럼으로 생성
    
    local_machine_limit:
        필수 컬럼: 기계코드, 공정명 

    """

    m = linespeed[config.columns.OPERATION_CODE].isin(local_machine_limit[config.columns.OPERATION_CODE])
    
    sub_ml = local_machine_limit[[config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]].dropna()
    sub_ml = sub_ml[sub_ml[config.columns.OPERATION_CODE].isin(linespeed.loc[m, config.columns.OPERATION_CODE])]
    valid_machine_codes = set(linespeed.columns)
    machine_code_set = valid_machine_codes - {config.columns.OPERATION_CODE, config.columns.GITEM}
    machine_codes = [c for c in sub_ml[config.columns.MACHINE_CODE].unique() if c in machine_code_set]
    
    target_mask = linespeed[config.columns.OPERATION_CODE].isin(sub_ml[config.columns.OPERATION_CODE])
    if machine_codes: 
        linespeed.loc[target_mask, machine_codes] = np.nan

    linespeed = operation_machine_global_limit(linespeed, global_machine_limit)
    unable_gitems, unable_details = _check_unable_order(linespeed, list(machine_code_set))
    return linespeed, unable_gitems, unable_details

def operation_machine_global_limit(linespeed, global_machine_limit):
    """
    글로벌 제약조건(블랙리스트)을 적용하여 특정 (GITEM, OPERATION_CODE, MACHINE_CODE) 조합을 제거한다.

    동작 개요
    - linespeed를 long 형식으로 변환 (각 기계별 속도값을 행으로 펼침)
    - 글로벌 블랙리스트와 조인하여 삭제 후보를 표시
    - 각 (GITEM, OPERATION_CODE) 그룹에서 유효 속도가 최소 1개 이상 남는 범위에서만 실제 삭제
    - wide 형식으로 복원 후 반환 (원래 기계 컬럼을 모두 보존)

    안전성 보장
    - 삭제로 인해 어떤 (GITEM, OPERATION_CODE)도 전부 불가능(모든 기계 NaN)이 되지 않도록 함
    """

    # 1) 입력 유효성 검사: 필수 컬럼 존재 여부 확인
    required_cols = {config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE}
    if not hasattr(global_machine_limit, "columns"):
        return linespeed
    if not required_cols.issubset(set(global_machine_limit.columns)):
        return linespeed

    # 2) 글로벌 블랙리스트 정제: 결측/중복 제거
    global_df = (
        global_machine_limit[list(required_cols)]
        .dropna()
        .drop_duplicates()
    )
    if global_df.empty:
        return linespeed

    # 3) linespeed의 기계 컬럼 목록/ID 컬럼 정의
    id_cols = [config.columns.GITEM, config.columns.OPERATION_CODE]
    machine_cols = [c for c in linespeed.columns if c not in {config.columns.OPERATION_CODE, config.columns.GITEM}]

    # 4) long 형식으로 변환: (GITEM, OPERATION_CODE, MACHINE_CODE, __SPEED__)
    melted = linespeed.melt(
        id_vars=id_cols,
        value_vars=machine_cols,
        var_name=config.columns.MACHINE_CODE,
        value_name="__SPEED__",
    )

    # 5) 블랙리스트 후보 표시 (__CAND__ = True)
    blacklist = global_df.assign(__CAND__=True)
    merged = melted.merge(
        blacklist,
        on=[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE],
        how="left",
    )
    merged["__CAND__"] = merged["__CAND__"].fillna(False)

    # 6) 그룹별 현재 유효 속도 개수와 후보 유효 개수 계산
    merged["__NN__"] = merged["__SPEED__"].notna()
    group_cols = id_cols
    grp_nn_cnt = (
        merged.groupby(group_cols, as_index=False)["__NN__"]
        .sum()
        .rename(columns={"__NN__": "__NN_CNT__"})
    )
    merged["__CAND_NN__"] = merged["__CAND__"] & merged["__NN__"]
    grp_cand_nn_cnt = (
        merged.groupby(group_cols, as_index=False)["__CAND_NN__"]
        .sum()
        .rename(columns={"__CAND_NN__": "__CAND_NN_CNT__"})
    )
    grp_info = grp_nn_cnt.merge(grp_cand_nn_cnt, on=group_cols, how="left").fillna({"__CAND_NN_CNT__": 0})
    grp_info["__RISKY__"] = (grp_info["__NN_CNT__"] - grp_info["__CAND_NN_CNT__"]) <= 0

    # 7) 위험 그룹 플래그를 행에 부여하고 삭제 마스크 생성
    merged = merged.merge(grp_info, on=group_cols, how="left")
    # 위험 그룹에서는 유효 속도(__SPEED__ notna)는 삭제하지 않음 (NaN 후보만 삭제 허용)
    drop_mask = merged["__CAND__"] & ~(merged["__RISKY__"] & merged["__SPEED__"].notna())

    # 8) 삭제 적용: 안전한 후보만 제거
    filtered = merged.loc[~drop_mask]

    # 9) wide 복원 및 기계 컬럼 보존
    wide = pd.pivot_table(
        filtered,
        index=group_cols,
        columns=config.columns.MACHINE_CODE,
        values="__SPEED__",
        aggfunc="first",
    ).reset_index()
    for col in machine_cols:
        if col not in wide.columns:
            wide[col] = np.nan
    keep_cols = group_cols + machine_cols
    return wide[keep_cols]

def _check_unable_order(linespeed, all_machine_columns):
    # 각 행에서 모든 기계 코드가 NaN인지 확인
    mask_all_nan = linespeed[all_machine_columns].isna().all(axis=1)

    if mask_all_nan.any():
        # GITEM과 공정명을 함께 추출
        unable_items_df = linespeed.loc[mask_all_nan, [config.columns.GITEM, config.columns.OPERATION_CODE]].dropna()
        
        unable_gitems = unable_items_df[config.columns.GITEM].astype(str).tolist()
        unable_operations = unable_items_df[config.columns.OPERATION_CODE].tolist()
        
        # GITEM과 공정명을 매핑한 딕셔너리 생성
        unable_details = []
        for _, row in unable_items_df.iterrows():
            unable_details.append({
                'gitem': str(row[config.columns.GITEM]),
                'operation': row[config.columns.OPERATION_CODE]
            })
        
        print(f"생산 불가(GITEM): {len(unable_gitems)}개")
            
    else: # 모든 아이템이 결과적으로 생산 가능
        unable_gitems = []
        unable_details = []
        
    return unable_gitems, unable_details




def operation_machine_exclusive(linespeed, machine_allocate):
    """
    해당 기계에서만 해당 공정을 수행하도록 독점 할당
    독점 할당으로 생산 불가능해질 행들은 변경하지 않음
    ex) 안료점착을 c2260에서만 생산가능하다고 했지만 gitem 30000의 경우 c2260에서 안료점착을 수행하지 못하는 경우 원본 유지
    """
    # 유효한 기계코드 추출
    machine_codes = set(linespeed.columns) - {config.columns.OPERATION_CODE, config.columns.GITEM}
    allocated_machines = [m for m in machine_allocate[config.columns.MACHINE_CODE].dropna().unique() if m in machine_codes]
    
    if not allocated_machines:
        print("독점 할당할 기계가 없음")
        return linespeed
    
    # 대상 행 선택
    target_mask = linespeed[config.columns.OPERATION_CODE].isin(machine_allocate[config.columns.OPERATION_CODE].dropna())
    if not target_mask.any():
        print("독점 할당할 공정이 없음")
        return linespeed

    
    # 다른 기계들 (독점하지 않을 기계들)
    other_machines = [m for m in machine_codes if m not in allocated_machines]
    
    if other_machines:
        # 독점 할당해도 안전한 행들만 선택 (할당된 기계 중 하나라도 유효값 있는 행)
        safe_mask = target_mask & linespeed[allocated_machines].notna().any(axis=1)
        
        if safe_mask.any():
            linespeed.loc[safe_mask, other_machines] = np.nan
            print(f"독점 할당: {allocated_machines}, 비활성화: {other_machines}")
        else:
            print("독점 할당 가능한 행이 없음")
    
    return linespeed