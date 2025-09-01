import pandas as pd
import numpy as np

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
        id2end = dict(zip(self.final_result_df['id'], self.final_result_df['node_end']))

        # 공정ID 컬럼 순서
        unique_depth_values = self.final_result_df['depth'].unique()
        
        id_cols = [f"{val}공정ID" for val in unique_depth_values]
        
        def get_end_time(row):
            for col in id_cols:
                key = row.get(col, None)
                if pd.notna(key) and key in id2end:
                    return id2end[key]
            return np.nan

        
        self.merged_df['종료시각'] = self.merged_df.apply(get_end_time, axis=1)

        # 병합 후 납기일도 포함한 결과 생성
        self.calculated_df = pd.merge(
            self.merged_df,
            self.original_order[['P/O NO', 'GITEM', '납기일']],
            on='P/O NO',
            how='left'
        )
        return self.calculated_df

    def calc_late_days(self, df, base_date, end_col='종료시각', due_col='납기일'):
        if self.calculated_df is None:
            raise RuntimeError("calculate_late_order() 먼저 실행해야 합니다.")

        df = self.calculated_df.copy()
        df['종료날짜'] = base_date + pd.to_timedelta(df[end_col] * 30, unit='m')
        df[due_col] = pd.to_datetime(df[due_col])
        diff = (df['종료날짜'] - df[due_col]).dt.total_seconds()
        df['지각일수'] = (diff // (24*60*60)).clip(lower=0).astype(int)

        self.calculated_df = df
        self.late_days_sum = df['지각일수'].sum()
        return self.calculated_df, self.late_days_sum