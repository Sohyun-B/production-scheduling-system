import pandas as pd
import numpy as np
from config import config

class ResultMerger:
    def __init__(self, merged_df, original_order, sequence_seperated_order):
        """
        :param merged_df: 기본 주문 및 공정 데이터프레임
        :param original_order: 원본 주문 데이터프레임
        :param sequence_seperated_order: 공정별 분리 주문 데이터프레임
        """
        self.merged_df = merged_df
        self.original_order = original_order
        self.sequence_seperated_order = sequence_seperated_order
        self.merged_result = None

    def merge_everything(self):
        df = pd.merge(self.merged_df, self.original_order, on=config.columns.PO_NO, how='left')
        merge_cols = [config.columns.COMBINATION_CLASSIFICATION, config.columns.FABRIC_WIDTH, config.columns.PRODUCTION_LENGTH, config.columns.MIXTURE_CODE]
        process_list = [config.columns.PROCESS_1_ID, config.columns.PROCESS_2_ID, config.columns.PROCESS_3_ID, config.columns.PROCESS_4_ID]
        result = df.copy()
        

        for process in process_list:
            temp = self.sequence_seperated_order[[config.columns.ID] + merge_cols].copy()
            suffix = process.replace(config.columns.ID, '')  # 예: '1공정'
            rename_map = {col: f"{col}_{suffix}" for col in merge_cols}
            temp.rename(columns=rename_map, inplace=True)

            result = result.merge(temp, how='left', left_on=process, right_on=config.columns.ID)
            result.drop(columns=[config.columns.ID], inplace=True)

        self.merged_result = result
        return self.merged_result