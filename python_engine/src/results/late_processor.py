"""
지각 작업 처리 통합 모듈 (late_order + late_order_processor 통합)
"""

import pandas as pd
import numpy as np
from config import config


class LateOrderCalculator:
    """지각 주문 계산 및 분석 (기존 late_order.py의 로직)"""
    
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
        """지각 주문 계산 (기존 로직 유지)"""
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
        """지각 일수 계산 (기존 로직 유지)"""
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


class LateProcessor:
    """지각 작업 처리 및 분석 통합 클래스"""
    
    def __init__(self, base_date):
        """
        Args:
            base_date (datetime): 기준 날짜
        """
        self.base_date = base_date
    
    def process(self, result_cleaned, merged_df, original_order):
        """
        지각 작업 처리 파이프라인 실행
        
        Args:
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과
            merged_df (pd.DataFrame): 병합된 주문 데이터
            original_order (pd.DataFrame): 원본 주문 데이터
            
        Returns:
            dict: {
                'new_output_final_result': pd.DataFrame,  # 지각 계산 완료된 결과
                'late_days_sum': int,                    # 총 지각 일수
                'late_products': pd.DataFrame,           # 지각한 제품 정보
                'late_po_numbers': list                  # 지각한 P/O 번호들
            }
        """
        print("[지각처리] 지각 작업 처리 시작...")
        
        # 지각 계산기 초기화
        late_calc = LateOrderCalculator(result_cleaned, merged_df, original_order)
        
        # 지각 계산 실행
        new_output_final_result = late_calc.calculate_late_order()
        new_output_final_result, late_days_sum = late_calc.calc_late_days(
            new_output_final_result, self.base_date
        )
        
        # 결과 정렬
        new_output_final_result = new_output_final_result.sort_values(by=config.columns.END_TIME)
        
        # 지각한 제품 정보 추출
        late_products = new_output_final_result[
            new_output_final_result['지각일수'] > 0
        ]
        late_po_numbers = late_products['P/O NO'].tolist() if len(late_products) > 0 else []
        
        print(f"[지각처리] 완료 - 총 지각 일수: {late_days_sum}일, 지각 제품: {len(late_products)}개")
        
        return {
            'new_output_final_result': new_output_final_result,
            'late_days_sum': late_days_sum,
            'late_products': late_products,
            'late_po_numbers': late_po_numbers
        }