import numpy as np
from config import config

def operation_machine_limit(linespeed, machine_limit):
    """
    해당 기계에서 해당 공정을 수행하지 않게 제한하는 경우 라인스피드를 사용하지 못하는 방식으로 변경
            
    linespeed:
        GITEM, 공정, 각 기계코드의 이름의 라인스피드 컬럼으로 생성
    
    machine_limit:
        필수 컬럼: 기계코드, 공정명 

    """
    m = linespeed[config.columns.OPERATION].isin(machine_limit[config.columns.OPERATION])
    
    sub_ml = machine_limit[[config.columns.OPERATION, config.columns.MACHINE_CODE]].dropna()
    sub_ml = sub_ml[sub_ml[config.columns.OPERATION].isin(linespeed.loc[m, config.columns.OPERATION])]
    valid_machine_codes = set(linespeed.columns)  # '공정' 포함 가능
    machine_code_set = valid_machine_codes - {config.columns.OPERATION, config.columns.GITEM}      # 안전하게 '공정' 제외
    machine_codes = [c for c in sub_ml[config.columns.MACHINE_CODE].unique() if c in machine_code_set]
    
    target_mask = linespeed[config.columns.OPERATION].isin(sub_ml[config.columns.OPERATION])
    if machine_codes: 
        print(linespeed.loc[target_mask])
        linespeed.loc[target_mask, machine_codes] = np.nan
        print(linespeed.loc[target_mask])
        unable_gitems = _check_unable_order(linespeed, list(machine_code_set))  # set을 list로 변환
    else:
        print("주문 데이터 중 해당 기계에서 해당 공정을 수행하는 경우가 없음")
        unable_gitems = []  # 빈 리스트 반환
    return linespeed, unable_gitems

def _check_unable_order(linespeed, all_machine_columns):
    # 각 행에서 모든 기계 코드가 NaN인지 확인
    mask_all_nan = linespeed[all_machine_columns].isna().all(axis=1)

    if mask_all_nan.any():
        print(f"전체 기계 컬럼: {all_machine_columns}")
        print("모든 기계에서 수행 불가능한 공정:")
        print(linespeed.loc[mask_all_nan])
        
        unable_gitems = (
            linespeed.loc[mask_all_nan, 'GITEM']
            .dropna()
            .astype(str)
            .tolist()
        )
        print(
            "생산 불가(GITEM): 모든 기계 컬럼이 NaN인 공정/주문. "
            f"대상 수={len(unable_gitems)} -> {unable_gitems}"
        )
    else: # 모든 아이템이 결과적으로 생산 가능
        unable_gitems = []
    return unable_gitems




def operation_machine_exclusive(linespeed, machine_allocate):
    """
    해당 기계에서만 해당 공정을 수행하도록 독점 할당
    독점 할당으로 생산 불가능해질 행들은 변경하지 않음
    ex) 안료점착을 c2260에서만 생산가능하다고 했지만 gitem 30000의 경우 c2260에서 안료점착을 수행하지 못하는 경우 원본 유지
    """
    # 유효한 기계코드 추출
    machine_codes = set(linespeed.columns) - {config.columns.OPERATION, config.columns.GITEM}
    allocated_machines = [m for m in machine_allocate[config.columns.MACHINE_CODE].dropna().unique() if m in machine_codes]
    
    if not allocated_machines:
        print("독점 할당할 기계가 없음")
        return linespeed
    
    # 대상 행 선택
    target_mask = linespeed[config.columns.OPERATION].isin(machine_allocate[config.columns.OPERATION].dropna())
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