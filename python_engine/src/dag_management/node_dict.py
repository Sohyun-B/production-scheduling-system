import pandas as pd
import numpy as np
from config import config

# def create_opnode_dict(sequence_seperated_order):
#     return {
#         row[config.columns.ID]: [
#             row[config.columns.OPERATION_ORDER],
#             row[config.columns.OPERATION_CODE],
#             row[config.columns.OPERATION_CLASSIFICATION],
#             row[config.columns.FABRIC_WIDTH],
#             row[config.columns.MIXTURE_LIST],
#             row[config.columns.PRODUCTION_LENGTH]
#         ]
#         for _, row in sequence_seperated_order.iterrows()
#     }


def create_opnode_dict(sequence_seperated_order):
    opnode_dict = {}
    
    for _, row in sequence_seperated_order.iterrows():
        # MIXTURE_LIST 문자열을 튜플로 변환
        mixture_str = str(row[config.columns.MIXTURE_LIST])
        if mixture_str == "None" or mixture_str.strip() == "":
            mixture_tuple = ()
        else:
            # 'A|B' -> ('A','B'), 'A' -> ('A',)
            mixture_tuple = tuple(mixture_str.split("|"))
        
        opnode_dict[row[config.columns.ID]] = {
            "OPERATION_ORDER": row[config.columns.OPERATION_ORDER],
            "OPERATION_CODE": row[config.columns.OPERATION_CODE],
            "OPERATION_CLASSIFICATION": row[config.columns.OPERATION_CLASSIFICATION],
            "FABRIC_WIDTH": row[config.columns.FABRIC_WIDTH],
            "MIXTURE_LIST": mixture_tuple,
            "PRODUCTION_LENGTH": row[config.columns.PRODUCTION_LENGTH],
            "SELECTED_MIXTURE": None  # 초기값
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