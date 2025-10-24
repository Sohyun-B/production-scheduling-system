import pandas as pd
import numpy as np
from config import config

def create_opnode_dict(sequence_seperated_order, aging_map=None):
    opnode_dict = {}

    print("========================OPNODE 생성 시작======================== ")

    # aging_map이 None이거나 빈 딕셔너리면 모든 aging_time을 0으로 설정
    if aging_map is None or not aging_map:
        sequence_seperated_order['aging_time'] = 0
    else:
        # 각 노드에 에이징 시간 추가. 해당 aging 시간은 해당 공정이 시작되기 '전'에 수행되어야함
        # aging_map에 없는 경우는 0으로 설정
        sequence_seperated_order['aging_time'] = list(map(lambda t: aging_map.get(t, 0), 
            zip(sequence_seperated_order[config.columns.GITEM], sequence_seperated_order[config.columns.OPERATION_CLASSIFICATION])))
    
    print("sequence_seperated_order")
    sequence_seperated_order.to_csv("data/output/sequence_seperated_order.csv", encoding='utf-8-sig', index=False)
    print(sequence_seperated_order)

    print("=============================================================== ")
    
    for _, row in sequence_seperated_order.iterrows():
        # CHEMICAL_LIST 문자열을 튜플로 변환
        chemical_str = str(row[config.columns.CHEMICAL_LIST])
        if chemical_str == "None" or chemical_str.strip() == "":
            chemical_tuple = ()
        else:
            # 'A|B' -> ('A','B'), 'A' -> ('A',)
            chemical_tuple = tuple(chemical_str.split("|"))
        
        # aging_time 처리: pandas nan을 0으로 변환 (aging이 없으면 대기 시간 0)
        aging_time_value = row['aging_time']
        if pd.isna(aging_time_value):
            aging_time_value = 0
        
        opnode_dict[row[config.columns.ID]] = {
            "OPERATION_ORDER": row[config.columns.OPERATION_ORDER],
            "OPERATION_CODE": row[config.columns.OPERATION_CODE],
            "OPERATION_CLASSIFICATION": row[config.columns.OPERATION_CLASSIFICATION],
            "FABRIC_WIDTH": row[config.columns.FABRIC_WIDTH],
            "CHEMICAL_LIST": chemical_tuple,
            "PRODUCTION_LENGTH": row[config.columns.PRODUCTION_LENGTH],
            "SELECTED_CHEMICAL": None,  # 초기값
            "AGING_TIME": aging_time_value
            
        }
    
    return opnode_dict



def create_machine_dict(sequence_seperated_order, linespeed, machine_columns):
    """
    인풋 데이터프레임 컬럼 조건
    sequence_seperated_order: [ GITEM, 공정, 생산길이, ID]
    linespeed: [ GITEM, 공정, 기계명(왼쪽부터 기계인덱스 0으로 지정) ]
    machine_columns: linespeed의 컬럼명 중 기계이름의 컬럼으로 인식해야하는 컬럼명 리스트
    """
    linespeed[config.columns.GITEM] = linespeed[config.columns.GITEM].astype(str)
    
    order_linespeed = sequence_seperated_order[[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.PRODUCTION_LENGTH, config.columns.ID]]
    order_linespeed = pd.merge(order_linespeed, linespeed, on=[config.columns.GITEM, config.columns.OPERATION_CODE], how='left')


    for col in machine_columns:
        temp = order_linespeed[col].copy()

        # NaN이면 바로 9999
        temp[temp.isna()] = 9999

        # 숫자인 경우 계산
        numeric_mask = temp != 9999
        temp.loc[numeric_mask] = np.ceil(
            order_linespeed.loc[numeric_mask, config.columns.PRODUCTION_LENGTH] /
            order_linespeed.loc[numeric_mask, col] /
            config.constants.TIME_MULTIPLIER
        )

        # 계산 후 inf 또는 NaN도 안전하게 9999 처리
        temp[~np.isfinite(temp)] = 9999

        # 정수 변환
        order_linespeed[col] = temp.astype(int)

    machine_dict = {
        row[config.columns.ID]: [row[col] for col in machine_columns]
        for _, row in order_linespeed.iterrows()
    }
    return machine_dict