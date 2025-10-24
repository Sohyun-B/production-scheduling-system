"""
주문-공정 병합 처리 통합 모듈 (merge_results + order_merge_processor 통합)
"""

import pandas as pd
import numpy as np
from config import config


class ResultMerger:
    """주문-공정 병합 처리 (기존 merge_results.py의 클래스)"""
    
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
        """모든 데이터 병합 실행"""
        df = pd.merge(self.merged_df, self.original_order, on=config.columns.PO_NO, how='left')
        merge_cols = [config.columns.COMBINATION_CLASSIFICATION, config.columns.FABRIC_WIDTH, config.columns.PRODUCTION_LENGTH, config.columns.CHEMICAL_LIST]
        # 동적으로 공정ID 컬럼들을 찾아서 순서대로 정렬
        process_columns = [col for col in df.columns if col.endswith(config.columns.PROCESS_ID_SUFFIX)]
        process_list = sorted(process_columns, key=lambda x: int(x.replace(config.columns.PROCESS_ID_SUFFIX, '')))
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


class MergeProcessor:
    """주문-공정 병합 처리 통합 클래스"""
    
    def process(self, merged_df, original_order, sequence_seperated_order):
        """
        주문-공정 병합 처리 파이프라인 실행
        
        Args:
            merged_df (pd.DataFrame): 기본 주문 및 공정 데이터
            original_order (pd.DataFrame): 원본 주문 데이터  
            sequence_seperated_order (pd.DataFrame): 공정별 분리 주문 데이터
            
        Returns:
            dict: {
                'merged_result': pd.DataFrame,  # 병합 결과
                'order_info': pd.DataFrame     # 조합분류 컬럼 제거된 주문 정보
            }
        """
        print("[병합처리] 주문-공정 병합 처리 시작...")
        
        # 병합 처리기 초기화 및 실행
        merger = ResultMerger(merged_df, original_order.copy(), sequence_seperated_order)
        merged_result = merger.merge_everything()
        
        # 주문 생산 정보 생성 (조합분류 컬럼 제거)
        order_info = merged_result.copy()
        order_info = order_info.loc[:, ~order_info.columns.str.startswith("조합분류")]
        
        print(f"[병합처리] 완료 - 병합 결과: {len(merged_result)}행")
        
        return {
            'merged_result': merged_result,
            'order_info': order_info
        }