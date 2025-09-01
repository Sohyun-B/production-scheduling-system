import pandas as pd
import numpy as np
from collections import defaultdict
from config import config

class YieldPredictor:
    def __init__(self, df):
        """
        공정 개수 동적으로 계산 안됨 지금 6공정 까지 있는 걸로 컬럼명 fixed
        df: melted_machine_linespeed: 필요 컬럼 GITEM, 공정명, 수율
        operation_sequence: 필요 컬럼 GITEM, 공정명, 공정명.1, 공정명.2, 공정명.3, 공정명.4, 공정명.5, 공정명.6 
                            predict_sequence_yield에서 입력받는 데이터
        """
        self.df = df
        self.model = None
        self.grid_df = None
        self.operation_sequence_yield = None
        self.gitem_yield_dict = defaultdict(float)
        
    def preprocessing(self):
        """ 데이터클렌징 """
        pass
    def calculate_predicted_yield(self):
        df = self.df.copy()

        
        group_cols = [config.columns.GITEM, config.columns.OPERATION]
        target_col = config.columns.YIELD

        result_rows = []
        grouped = df.groupby(group_cols)

        for group_keys, group_df in grouped:
            valid_yields = group_df[group_df[target_col] >= 0.9][target_col]

            if not valid_yields.empty:
                mean_yield = valid_yields.mean()
            else:
                mean_yield = 0.9

            result_rows.append(list(group_keys) + [mean_yield])

        grid_df = pd.DataFrame(result_rows, columns=group_cols + [config.columns.PREDICTED_YIELD])
        self.grid_df = grid_df


    def predict_sequence_yield(self, operation_sequence):
        """
        operation_sequence: 공정 시퀀스 DataFrame (ex: GITEM, 1공정, 2공정, ... 동적으로)
        예측수율 결과 및 생산비율 컬럼 추가
        """
        grid_df = self.grid_df.copy()
        operation_sequence[config.columns.GITEM] = operation_sequence[config.columns.GITEM].astype(str)
        grid_df[config.columns.GITEM] = grid_df[config.columns.GITEM].astype(str)
        grid_df[config.columns.OPERATION] = grid_df[config.columns.OPERATION].astype(str)
    
        process_cols = [col for col in operation_sequence.columns if col != config.columns.GITEM]
        # 모든 공정 컬럼 문자열 변환
        for col in process_cols:
            operation_sequence[col] = operation_sequence[col].astype(str)
    
        # 공정별 예측 수율 merge 및 컬럼명 지정 (접두사 '예측_수율.' + 공정명)
        for col in process_cols:
            operation_sequence = pd.merge(
                operation_sequence,
                grid_df,
                left_on=[config.columns.GITEM, col],
                right_on=[config.columns.GITEM, config.columns.OPERATION],
                how='left',
                suffixes=('', '_drop')
            )
            operation_sequence.drop(columns=[config.columns.OPERATION], inplace=True)
            operation_sequence.rename(columns={config.columns.PREDICTED_YIELD: f'{config.columns.PREDICTED_YIELD}.{col}'}, inplace=True)
    
        yield_cols = [col for col in operation_sequence.columns if col.startswith(f'{config.columns.PREDICTED_YIELD}.')]
    
        print(f"예측수율 컬럼 리스트: {yield_cols}")
    
        # 전체 예측 수율 계산 (곱)
        operation_sequence[config.columns.TOTAL_PREDICTED_YIELD] = operation_sequence[yield_cols].apply(lambda row: np.nanprod(row), axis=1)
        operation_sequence[config.columns.TOTAL_PREDICTED_YIELD] = operation_sequence[config.columns.TOTAL_PREDICTED_YIELD].round(4)
        operation_sequence[config.columns.YIELD_PRODUCTION_RATIO] = 100 / operation_sequence[config.columns.TOTAL_PREDICTED_YIELD]
    
        self.operation_sequence_yield = operation_sequence
        self._get_gitem_yield_dict()


    def _get_gitem_yield_dict(self):
        """
        self.operation_sequence_yield 가 있어야 작동함 (predict_sequence_yield 수행 후)
        GITEM별 평균 전체_예측_수율 딕셔너리 리턴
        """
        if self.operation_sequence_yield is None:
            raise ValueError("predict_sequence_yield 메서드를 먼저 호출하여 데이터를 생성하세요.")
        
        grouped = self.operation_sequence_yield.groupby(config.columns.GITEM)[config.columns.YIELD_PRODUCTION_RATIO].mean()
        self.gitem_yield_dict = grouped.to_dict()
        

    def adjust_production_length(self, sequence_seperated_order):
        """
        sequence_seperated_order: pd.DataFrame, 'GITEM'과 '생산길이' 컬럼 포함된 데이터

        gitem_yield_dict에 기반해 '생산길이'에 수율 값(%) 반영 후 수정하고,
        수정 전 원본은 '원본생산길이' 컬럼에 백업함.

        반환: 수율이 반영된 pd.DataFrame
        """
        yield_map = sequence_seperated_order[config.columns.GITEM].map(self.gitem_yield_dict).fillna(100)
        sequence_seperated_order = sequence_seperated_order.copy()
        sequence_seperated_order[config.columns.ORIGINAL_PRODUCTION_LENGTH] = sequence_seperated_order[config.columns.PRODUCTION_LENGTH]
        sequence_seperated_order[config.columns.PRODUCTION_LENGTH] = (sequence_seperated_order[config.columns.PRODUCTION_LENGTH] * yield_map / 100).round().astype(int)
        return sequence_seperated_order