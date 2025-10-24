from config import config
from .fabric_combiner import FabricRuleHandler, FabricCombiner
import pandas as pd

def process_operations_by_category(merged_df):
    """
    병합된 DataFrame(merged_df)을 받아서, 세부유형/공정/배합코드 기준으로 
    FabricCombiner를 적용하고 결과 리스트를 반환한다.
    """
    results = []

    for gitem in merged_df[config.columns.GITEM].dropna().unique():
        category_df = merged_df[merged_df[config.columns.GITEM] == gitem]

        for operation in category_df[config.columns.OPERATION_CODE].dropna().unique():
            opslice = category_df[category_df[config.columns.OPERATION_CODE] == operation]

            # 배합코드 유무에 따라 분리
            nan_bh = opslice[opslice[config.columns.CHEMICAL_LIST].isna()]
            notnan_bh = opslice[~opslice[config.columns.CHEMICAL_LIST].isna()]

            # 배합코드가 존재하는 경우
            if not notnan_bh.empty:
                groupby_col = [config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.CHEMICAL_LIST, config.columns.COMBINATION_CLASSIFICATION]
                combiner = FabricCombiner(groupby_col)
                
                
                paired_order = combiner.process(notnan_bh)
                
                if not paired_order.empty:
                    paired_order[config.columns.ID] = (
                        str(gitem) + "_" + 
                        paired_order[config.columns.OPERATION_CODE].round().astype(int).astype(str) + "_" +
                        paired_order[config.columns.FABRIC_WIDTH].round().astype(int).astype(str) + "_" + 
                        paired_order[config.columns.CHEMICAL_LIST].astype(str) + "_" +
                        paired_order[config.columns.COMBINATION_CLASSIFICATION].astype(str)
                    )
                    results.append(paired_order)

            if not nan_bh.empty:
                print(f"[{gitem}/{operation}] 배합코드 미존재 행 존재!!!!")

    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()
        
def create_sequence_seperated_order(order_list, operation_seperated_sequence):
    sequence_seperated_order_list = []
    
    for order_df in order_list:
        # 병합 및 전처리 (외부에서 처리)
        merged = pd.merge(order_df, operation_seperated_sequence, on=[config.columns.GITEM], how='left')
        merged = merged.rename(columns={config.columns.FABRIC_LENGTH: config.columns.PRODUCTION_LENGTH})
    
        # 처리 함수 적용 (공정별 분리 및 ID 생성 등)
        result_df = process_operations_by_category(merged)
    
        if not result_df.empty:
            sequence_seperated_order_list.append(result_df)
    
    # 결과를 하나의 DataFrame으로 병합
    sequence_seperated_order = pd.concat(sequence_seperated_order_list, ignore_index=True)
    
    # 해시 생성 후 ID에 추가
    sequence_seperated_order[config.columns.ID] = sequence_seperated_order[config.columns.ID].astype(str) + "_M" + sequence_seperated_order[config.columns.DUE_DATE].dt.month.astype(str)
    sequence_seperated_order[config.columns.OPERATION_ORDER] = sequence_seperated_order[config.columns.OPERATION_ORDER].astype(int)
    return sequence_seperated_order
    