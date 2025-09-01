import pandas as pd
import numpy as np
from config import config

class LateOrderCalculator:
    def __init__(self, final_result_df, merged_df, original_order):
        """
        :param final_result_df: 전체 작업 완료 시간 결과 (id, node_end 등)
        :param merged_df: 공정별 정보가 포함된 병합된 주문 데이터프레임
        :param original_order: 원본 주문 데이터 (납기일 등 포함)
        """
        self.final_result_df = final_result_df
        self.merged_df = merged_df.copy()
        self.original_order = original_order
        self.calculated_df = None
        self.late_days_sum = None

    def calculate_late_order(self):
        id2end = dict(zip(self.final_result_df['id'], self.final_result_df[config.columns.NODE_END]))

        # 공정ID 컬럼 순서
        unique_depth_values = self.final_result_df[config.columns.DEPTH].unique()
        
        id_cols = [f"{val}공정{config.columns.ID}" for val in unique_depth_values]
        
        def get_end_time(row):
            # 마지막 공정의 종료시간을 반환해야 함 (역순으로 탐색)
            max_end_time = np.nan
            for col in reversed(id_cols):  # 역순으로 탐색하여 마지막 공정 우선
                key = row.get(col, None)
                if pd.notna(key) and key in id2end:
                    current_end_time = id2end[key]
                    if np.isnan(max_end_time) or current_end_time > max_end_time:
                        max_end_time = current_end_time
            return max_end_time

        
        self.merged_df[config.columns.END_TIME] = self.merged_df.apply(get_end_time, axis=1)

        # 병합 후 납기일도 포함한 결과 생성
        self.calculated_df = pd.merge(
            self.merged_df,
            self.original_order[[config.columns.PO_NO, config.columns.GITEM, config.columns.DUE_DATE]],
            on=config.columns.PO_NO,
            how='left'
        )
        return self.calculated_df

    def calc_late_days(self, df, base_date, end_col=None, due_col=None):
        if end_col is None:
            end_col = config.columns.END_TIME
        if due_col is None:
            due_col = config.columns.DUE_DATE
            
        if self.calculated_df is None:
            raise RuntimeError("calculate_late_order() 먼저 실행해야 합니다.")

        df = self.calculated_df.copy()
        df[config.columns.END_DATE] = base_date + pd.to_timedelta(df[end_col] * config.constants.TIME_MULTIPLIER, unit='m')
        df[due_col] = pd.to_datetime(df[due_col])
        diff = (df[config.columns.END_DATE] - df[due_col]).dt.total_seconds()
        df[config.columns.LATE_DAYS] = (diff // (24*60*60)).clip(lower=0).astype(int)

        self.calculated_df = df
        self.late_days_sum = df[config.columns.LATE_DAYS].sum()
        return self.calculated_df, self.late_days_sum