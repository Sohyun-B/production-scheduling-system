import pandas as pd
import numpy as np
from config import config

def create_opnode_dict(sequence_seperated_order):
    return {
        row[config.columns.ID]: [
            row[config.columns.OPERATION_ORDER],
            row[config.columns.OPERATION],
            row[config.columns.OPERATION_CLASSIFICATION],
            row[config.columns.FABRIC_WIDTH],
            row[config.columns.MIXTURE_CODE],
            row[config.columns.PRODUCTION_LENGTH]
        ]
        for _, row in sequence_seperated_order.iterrows()
    }


def create_machine_dict(sequence_seperated_order, linespeed, machine_columns):
    """
    인풋 데이터프레임 컬럼 조건
    sequence_seperated_order: [ GITEM, 공정, 생산길이, ID]
    linespeed: [ GITEM, 공정, 기계명(왼쪽부터 기계인덱스 0으로 지정) ]
    machine_columns: linespeed의 컬럼명 중 기계이름의 컬럼으로 인식해야하는 컬럼명 리스트
    """
    linespeed[config.columns.GITEM] = linespeed[config.columns.GITEM].astype(str)
    
    order_linespeed = sequence_seperated_order[[config.columns.GITEM, config.columns.OPERATION, config.columns.PRODUCTION_LENGTH, config.columns.ID]]
    order_linespeed = pd.merge(order_linespeed, linespeed, on=[config.columns.GITEM, config.columns.OPERATION], how='left')

    order_linespeed = order_linespeed.fillna(np.inf) # 

    for col in machine_columns:
        # 0으로 나누기 방지: 0인 경우 inf로 설정
        order_linespeed[col] = order_linespeed[col].replace(0, np.inf)
        order_linespeed[col] = np.ceil(order_linespeed[config.columns.PRODUCTION_LENGTH] / order_linespeed[col] / config.constants.TIME_MULTIPLIER)
        # inf 값을 9999로 변경 후 정수 변환
        order_linespeed[col] = order_linespeed[col].replace(np.inf, 9999).astype(int)
    
    for col in machine_columns:
        order_linespeed.loc[order_linespeed[col] == 0, col] = 9999
    
    machine_dict = {
        row[config.columns.ID]: [row[col] for col in machine_columns]
        for _, row in order_linespeed.iterrows()
    }
    return machine_dict