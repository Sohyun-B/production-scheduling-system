"""
주문-공정 병합 처리 통합 모듈 (results 전용)
merge_results + order_merge_processor 통합
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
            temp = self.sequence_seperated_order[[config.columns.PROCESS_ID] + merge_cols].copy()
            suffix = process.replace(config.columns.PROCESS_ID, '')  # 예: '1공정'
            rename_map = {col: f"{col}_{suffix}" for col in merge_cols}
            temp.rename(columns=rename_map, inplace=True)

            result = result.merge(temp, how='left', left_on=process, right_on=config.columns.PROCESS_ID)
            result.drop(columns=[config.columns.PROCESS_ID], inplace=True)

        self.merged_result = result
        return self.merged_result


def create_process_detail_result(final_result_df, sequence_seperated_order, scheduler):
    """
    final_result_df 기준으로 Aging 포함 상세 공정 결과 생성 (긴 형식)

    Args:
        final_result_df: 스케줄링 결과 DataFrame (Aging 포함)
        sequence_seperated_order: 원본 공정 데이터 (Aging 제외)
        scheduler: machine_dict 접근용

    Returns:
        pd.DataFrame: 긴 형식 결과
            - pono, gitem, depth, process_id, process_code, is_aging
            - machine, start_time, end_time, processing_time
            - fabric_width, production_length, chemical_list, duedate
    """
    results = []

    # sequence_seperated_order를 ID 기준으로 인덱싱 (중복 고려 - 첫 번째 것만 사용)
    seq_dict = {}
    for _, row in sequence_seperated_order.iterrows():
        node_id = row[config.columns.PROCESS_ID]
        if node_id not in seq_dict:  # 중복 시 첫 번째만 저장
            seq_dict[node_id] = row.to_dict()

    for _, row in final_result_df.iterrows():
        node_id = row['id']

        # Aging 여부 확인
        machine_info = scheduler.machine_dict.get(node_id)
        is_aging = machine_info and set(machine_info.keys()) == {-1}

        # sequence_seperated_order에서 추가 정보 가져오기
        if is_aging and '_AGING' in node_id:
            # Aging 노드는 부모 노드 ID에서 정보 상속
            parent_node_id = node_id.replace('_AGING', '')
            extra_info = seq_dict.get(parent_node_id, {})
        else:
            # 일반 노드는 직접 조회
            extra_info = seq_dict.get(node_id, {})

        # 컬럼명: node_start, node_end (lowercase)
        node_start = row.get('node_start', 0)
        node_end = row.get('node_end', 0)

        results.append({
            config.columns.PO_NO: extra_info.get(config.columns.PO_NO, ''),
            config.columns.GITEM: extra_info.get(config.columns.GITEM, ''),
            config.columns.DEPTH: row[config.columns.DEPTH],
            config.columns.PROCESS_ID: node_id,
            config.columns.OPERATION_CODE: extra_info.get(config.columns.OPERATION_CODE, ''),
            'is_aging': is_aging,
            config.columns.MACHINE_CODE: row.get(config.columns.MACHINE_CODE, row.get('machine', None)),  # ★ MACHINE_INDEX → MACHINE_CODE
            'node_start': node_start,
            config.columns.NODE_END: node_end,
            'processing_time': row.get('processing_time', node_end - node_start),
            config.columns.FABRIC_WIDTH: extra_info.get(config.columns.FABRIC_WIDTH, None),
            config.columns.PRODUCTION_LENGTH: extra_info.get(config.columns.PRODUCTION_LENGTH, None),
            config.columns.CHEMICAL_LIST: extra_info.get(config.columns.CHEMICAL_LIST, None),
            config.columns.DUE_DATE: extra_info.get(config.columns.DUE_DATE, None),
        })

    df = pd.DataFrame(results)

    # 정렬: PO번호 → 시작시간 순
    df = df.sort_values([config.columns.PO_NO, 'node_start']).reset_index(drop=True)

    print(f"[병합처리] 긴 형식 결과 생성 완료 - 총 {len(df)}행 (Aging 포함: {df['is_aging'].sum()}개)")
    print(f"[DEBUG] process_detail_df의 빈 PO_NO 개수: {(df[config.columns.PO_NO] == '').sum()}")
    print(f"[DEBUG] process_detail_df의 NaN PO_NO 개수: {df[config.columns.PO_NO].isna().sum()}")
    print(f"[DEBUG] process_detail_df의 unique PO_NO: {df[config.columns.PO_NO].nunique()}")
    print(f"[DEBUG] process_detail_df의 PO 목록: {sorted(df[config.columns.PO_NO].unique())}")

    return df


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