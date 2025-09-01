import pandas as pd
import numpy as np

def create_opnode_dict(sequence_seperated_order):

    print("sequence seperated order head")
    display(sequence_seperated_order.head(2))
    return {
        row['ID']: [
            row['공정순서'],
            row['공정'],
            row['공정분류'],
            row['원단너비'],
            row['배합코드'],
            row['생산길이']
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
    linespeed['GITEM'] = linespeed['GITEM'].astype(str)
    
    order_linespeed = sequence_seperated_order[['GITEM', '공정', '생산길이', 'ID']]
    order_linespeed = pd.merge(order_linespeed, linespeed, on =['GITEM', '공정'], how='left')

    order_linespeed = order_linespeed.fillna(np.inf) # 

    for col in machine_columns:
        order_linespeed[col] = np.ceil(order_linespeed['생산길이'] / order_linespeed[col] / 30).astype(int)
    
    for col in machine_columns:
        order_linespeed.loc[order_linespeed[col] == 0, col] = 9999
    
    machine_dict = {
        row['ID']: [row[col] for col in machine_columns]
        for _, row in order_linespeed.iterrows()
    }
    return machine_dict