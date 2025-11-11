"""
지각 작업 처리 통합 모듈 (late_order + late_order_processor 통합)
"""

import pandas as pd
import numpy as np
from config import config


class LateOrderCalculator:
    """지각 주문 계산 및 분석 (긴 형식 기반)"""

    def __init__(self, final_result_df, process_detail_df, original_order):
        """
        :param final_result_df: 전체 작업 완료 시간 결과 (id, node_end 등)
        :param process_detail_df: Aging 포함 긴 형식 DataFrame
        :param original_order: 원본 주문 데이터 (납기일 등 포함)
        """
        self.final_result_df = final_result_df
        self.process_detail_df = process_detail_df
        self.original_order = original_order
        self.calculated_df = None
        self.late_days_sum = None

    def calculate_late_order(self):
        """지각 주문 계산 (긴 형식 기반)"""
        # Aging 제외하고 각 주문의 마지막 공정 종료시간 찾기
        non_aging_df = self.process_detail_df[self.process_detail_df['is_aging'] == False].copy()

        # PO_NO가 쉼표로 연결된 문자열인지 확인 (예: "PO1, PO2")
        has_comma_po = non_aging_df[config.columns.PO_NO].astype(str).str.contains(',', na=False).any()

        if has_comma_po:
            print(f"[DEBUG] PO_NO 쉼표 분리 행 감지 - 문자열을 리스트로 변환 중...")
            # 쉼표로 연결된 문자열을 리스트로 변환
            non_aging_df[config.columns.PO_NO] = non_aging_df[config.columns.PO_NO].astype(str).apply(
                lambda x: [po.strip() for po in x.split(',') if po.strip()]
            )
            # 리스트 explode 실행
            non_aging_df = non_aging_df.explode(config.columns.PO_NO).reset_index(drop=True)
            print(f"[DEBUG] Explode 후 non_aging_df 행 수: {len(non_aging_df)}")
        else:
            # 리스트인 경우 직접 explode
            has_list_po = non_aging_df[config.columns.PO_NO].apply(
                lambda x: isinstance(x, list)
            ).any()

            if has_list_po:
                print(f"[DEBUG] PO_NO 리스트 행 감지 - explode 처리 중...")
                non_aging_df = non_aging_df.explode(config.columns.PO_NO).reset_index(drop=True)
                print(f"[DEBUG] Explode 후 non_aging_df 행 수: {len(non_aging_df)}")

        # 각 주문별 마지막 종료시간 찾기
        order_end_times = non_aging_df.groupby(config.columns.PO_NO)[config.columns.NODE_END].max().reset_index()
        order_end_times.columns = [config.columns.PO_NO, config.columns.END_TIME]

        print(f"[DEBUG] order_end_times의 행 수: {len(order_end_times)}")
        print(f"[DEBUG] order_end_times의 PO_NO: {order_end_times[config.columns.PO_NO].tolist()}")
        print(f"[DEBUG] original_order의 행 수: {len(self.original_order)}")
        print(f"[DEBUG] original_order의 PO_NO: {self.original_order[config.columns.PO_NO].tolist()}")
        print(f"[DEBUG] original_order의 DUE_DATE NaN 개수: {self.original_order[config.columns.DUE_DATE].isna().sum()}")

        # 원본 주문 정보와 병합
        self.calculated_df = pd.merge(
            order_end_times,
            self.original_order[[config.columns.PO_NO, config.columns.GITEM, config.columns.DUE_DATE]],
            on=config.columns.PO_NO,
            how='left'
        )

        print(f"[DEBUG] 병합 후 DUE_DATE NaN 개수: {self.calculated_df[config.columns.DUE_DATE].isna().sum()}")
        if self.calculated_df[config.columns.DUE_DATE].isna().sum() > 0:
            print(f"[DEBUG] NaN인 행들: {self.calculated_df[self.calculated_df[config.columns.DUE_DATE].isna()][[config.columns.PO_NO, config.columns.END_TIME]].to_string()}")

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
    
    def process(self, result_cleaned, process_detail_df, original_order):
        """
        지각 작업 처리 파이프라인 실행

        Args:
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과
            process_detail_df (pd.DataFrame): Aging 포함 긴 형식 결과
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

        # 지각 계산기 초기화 (긴 형식 사용)
        late_calc = LateOrderCalculator(result_cleaned, process_detail_df, original_order)

        # 지각 계산 실행
        new_output_final_result = late_calc.calculate_late_order()
        new_output_final_result, late_days_sum = late_calc.calc_late_days(
            new_output_final_result, self.base_date
        )
        
        # 결과 정렬
        new_output_final_result = new_output_final_result.sort_values(by=config.columns.END_TIME)
        
        # 지각한 제품 정보 추출
        late_products = new_output_final_result[
            new_output_final_result[config.columns.LATE_DAYS] > 0
        ]
        late_po_numbers = late_products[config.columns.PO_NO].tolist() if len(late_products) > 0 else []
        
        print(f"[지각처리] 완료 - 총 지각 일수: {late_days_sum}일, 지각 제품: {len(late_products)}개")
        
        return {
            'new_output_final_result': new_output_final_result,
            'late_days_sum': late_days_sum,
            'late_products': late_products,
            'late_po_numbers': late_po_numbers
        }