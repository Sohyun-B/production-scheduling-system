"""
웹 인터페이스용 단계별 데이터 추출 및 포맷터
각 스케줄링 단계의 결과를 웹 UI에서 사용할 수 있는 형태로 변환
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from config import config


class StageDataExtractor:
    """json 형태의 직접 변경은 백엔드에서. 백엔드가 간단한 연산 (len,count 등)만으로 화면에 필요한 데이터 알 수 있게 포맷팅"""
    
    # @staticmethod
    # def extract_stage1_data(
    #     linespeed: pd.DataFrame,
    #     machine_master_info: pd.DataFrame,
    #     operation_types: pd.DataFrame,
    #     operation_delay_df: pd.DataFrame,
    #     order: pd.DataFrame
    # ) -> Dict[str, Any]:
    #     """1단계: 데이터 로딩 결과 추출"""
    #     return {
    #         "stage": "loading",
    #         "data": {
    #             "linespeed_count": len(linespeed),
    #             "machine_count": len(machine_master_info),
    #             "operation_types_count": len(operation_types),
    #             "operation_delay_count": len(operation_delay_df),
    #             "total_orders": len(order),
    #             "base_config": {
    #                 "base_year": config.constants.BASE_YEAR,
    #                 "base_month": config.constants.BASE_MONTH,
    #                 "base_day": config.constants.BASE_DAY,
    #                 "window_days": config.constants.WINDOW_DAYS
    #             }
    #         }
    #     }
    
    @staticmethod
    def _process_po_no_separation(unable_order: pd.DataFrame, unable_details: List[Dict] = None) -> pd.DataFrame:
        """P/O NO 쉼표 분리 및 불가능한공정 매핑 처리"""
        if len(unable_order) == 0:
            return pd.DataFrame()
            
        processed = unable_order.copy()
        
        # 중복 제거 (explode 전에)
        processed = processed.drop_duplicates()
        
        # 불가능한공정 매핑
        if unable_details:
            details_dict = {detail['gitem']: detail['operation'] for detail in unable_details}
            processed['불가능한공정'] = processed['GITEM'].astype(str).map(details_dict)
        
        # P/O NO 쉼표 분리
        if config.columns.PO_NO in processed.columns:
            comma_mask = processed[config.columns.PO_NO].astype(str).str.contains(', ', na=False)
            if comma_mask.any():
                normal_rows = processed[~comma_mask]
                comma_rows = processed[comma_mask].copy()
                comma_rows[config.columns.PO_NO] = comma_rows[config.columns.PO_NO].str.split(', ')
                comma_rows = comma_rows.explode(config.columns.PO_NO)
                comma_rows[config.columns.PO_NO] = comma_rows[config.columns.PO_NO].str.strip()
                processed = pd.concat([normal_rows, comma_rows], ignore_index=True)
        
        return processed

    @staticmethod
    def extract_stage2_data(
        order: pd.DataFrame,
        sequence_seperated_order: pd.DataFrame,
        unable_gitems: List[str],
        unable_order: pd.DataFrame,
        unable_details: List[Dict] = None
    ) -> Dict[str, Any]:
        """2단계: 전처리 결과 추출"""
        
        processed_unable_order = StageDataExtractor._process_po_no_separation(unable_order, unable_details)
        
        return {
            "stage": "preprocessing", 
            "data": {
                "input_orders": len(order),
                "used_orders": sequence_seperated_order[config.columns.PO_NO].unique().tolist(),
                "excluded_gitems_count": len(unable_gitems),
                "excluded_orders": processed_unable_order.to_dict(orient='records') if len(processed_unable_order) > 0 else [],
            }
        }
    
    @staticmethod
    def extract_stage3_data(
        yield_predictor,
        sequence_yield_df: pd.DataFrame,
        original_gitem_count: int
    ) -> Dict[str, Any]:
        """3단계: 수율 예측 결과 추출"""
        # 수율이 있는 GITEM 수 계산
        gitem_with_yield = len(sequence_yield_df[sequence_yield_df[config.columns.PREDICTED_YIELD].notna()])
        gitem_without_yield = len(sequence_yield_df) - gitem_with_yield
        
        # 평균 수율 계산
        mean_yield = sequence_yield_df[config.columns.PREDICTED_YIELD].mean() if gitem_with_yield > 0 else 0
        
        return {
            "stage": "yield_prediction", 
            "data": {
                "total_gitem_count": len(sequence_yield_df),
                "gitem_with_yield_count": gitem_with_yield,
                "gitem_without_yield_count": gitem_without_yield,
                "mean_predicted_yield": round(mean_yield, 4) if mean_yield > 0 else 0,
                "yield_coverage_rate": round(gitem_with_yield / len(sequence_yield_df), 4) if len(sequence_yield_df) > 0 else 0
            }
        }
    
    @staticmethod
    def extract_stage4_data(
        dag_df: pd.DataFrame,
        machine_dict: Dict,
        opnode_dict: Dict
    ) -> Dict[str, Any]:
        """4단계: DAG 시스템 생성 결과 추출"""
        return {
            "stage": "dag_creation",
            "data": {
                "total_nodes": len(dag_df),
                "machine_count": len(machine_dict),
                "opnode_count": len(opnode_dict),
                "dag_depth_levels": dag_df[config.columns.DEPTH].nunique() if config.columns.DEPTH in dag_df.columns else 0
            }
        }
    
    @staticmethod
    def extract_stage5_data(
        result: pd.DataFrame,
        machine_schedule_df: pd.DataFrame,
        window_days: int,
        actual_makespan: float
    ) -> Dict[str, Any]:
        """5단계: 스케줄링 실행 결과 추출"""
        # depth -1인 가짜 공정 제외한 실제 작업 수
        actual_jobs = result[~(result[config.columns.DEPTH] == -1)] if config.columns.DEPTH in result.columns else result
        
        # 기계 스케줄에서 가짜 공정 제외
        clean_machine_schedule = machine_schedule_df[
            ~machine_schedule_df[config.columns.ALLOCATED_WORK].astype(str).str.startswith('[-1', na=False)
        ] if config.columns.ALLOCATED_WORK in machine_schedule_df.columns else machine_schedule_df
        
        return {
            "stage": "scheduling",
            "data": {
                "window_days_used": window_days,
                "makespan_slots": int(actual_makespan),
                "makespan_hours": actual_makespan * 0.5,
                "total_days": (actual_makespan * 0.5) / 24,
                "processed_jobs_count": len(actual_jobs),
                "machine_info": clean_machine_schedule.to_dict('records')
            }
        }
    
    @staticmethod
    def extract_stage6_data(
        new_output_final_result: pd.DataFrame,
        late_days_sum: int
    ) -> Dict[str, Any]:
        """6단계: 결과 후처리 추출"""
        # 지각한 제품 정보
        late_products = new_output_final_result[new_output_final_result[config.columns.LATE_DAYS] > 0]
        late_po_numbers = late_products[config.columns.PO_NO].tolist() if len(late_products) > 0 else []
        
        return {
            "stage": "results",
            "data": {
                "late_days_sum": late_days_sum,
                "late_products_count": len(late_products),
                "late_po_numbers": late_po_numbers
            }
        }
    
    @staticmethod
    def extract_gitem_summary_data(
        order: pd.DataFrame, 
        sequence_seperated_order: pd.DataFrame
    ) -> Dict[str, Any]:
        """GITEM별 요약 정보 추출 (프론트엔드용)"""
        result = {}
        
        for gitem, group in sequence_seperated_order.groupby('GITEM'):
            # GITEM별 P/O 정보는 order에서 가져옴
            po_list = []
            order_filtered = order[order['GITEM'] == gitem]
            for _, po_row in order_filtered.iterrows():
                po_list.append({
                    'P/O NO': po_row['P/O NO'],
                    '길이': int(po_row['길이']),
                    '너비': int(po_row['너비']),
                    '납기일': po_row['납기일']
                })
            
            # 공정 목록은 sequence_seperated_order에서 가져옴 (공정순서대로 정렬)
            process_list = []
            for _, row in group.sort_values('공정순서').iterrows():
                process_list.append({
                    '공정명': row['공정명'],
                    'dag_node_id': row['ID']
                })
            
            result[gitem] = {
                '생산길이': int(order_filtered['길이'].sum()),  # P/O 길이들의 합계
                '원단너비': int(group['원단너비'].iloc[0]),
                '공정명': '→'.join(group.sort_values('공정순서')['공정명']),
                'p/o_list': po_list,
                '공정목록': process_list
            }
        
        return result


class WebTableFormatter:
    """웹 UI 테이블 표시용 데이터 포맷터"""
    
    @staticmethod
    def format_preprocessing_summary_table(
        sequence_seperated_order: pd.DataFrame,
        unable_order: pd.DataFrame
    ) -> Dict[str, Any]:
        """전처리 단계 요약 테이블"""
        
        # 사용된 주문 요약
        used_summary = (
            sequence_seperated_order
            .groupby([config.columns.PO_NO, config.columns.GITEM])
            .agg({
                config.columns.REQUEST_AMOUNT: 'first',
                config.columns.DUE_DATE: 'first'
            })
            .reset_index()
        )
        
        return {
            "used_orders_table": {
                "columns": [config.columns.PO_NO, config.columns.GITEM, config.columns.REQUEST_AMOUNT, config.columns.DUE_DATE],
                "data": used_summary.to_dict('records')
            },
            "excluded_orders_table": {
                "columns": [config.columns.PO_NO, config.columns.GITEM],
                "data": unable_order.to_dict('records') if len(unable_order) > 0 else []
            }
        }
    
    @staticmethod
    def format_yield_summary_table(sequence_yield_df: pd.DataFrame) -> Dict[str, Any]:
        """수율 예측 단계 요약 테이블"""
        
        # 수율 정보가 있는 데이터만 필터링
        yield_with_data = sequence_yield_df[sequence_yield_df[config.columns.PREDICTED_YIELD].notna()]
        
        if len(yield_with_data) == 0:
            return {
                "yield_summary_table": {
                    "columns": [],
                    "data": []
                }
            }
        
        # GITEM별 수율 요약
        yield_summary = (
            yield_with_data
            .groupby([config.columns.GITEM])
            .agg({
                config.columns.PREDICTED_YIELD: 'mean'
            })
            .round(4)
            .reset_index()
        )
        
        return {
            "yield_summary_table": {
                "columns": [config.columns.GITEM, config.columns.PREDICTED_YIELD],
                "data": yield_summary.to_dict('records')
            }
        }
    
    @staticmethod
    def format_scheduling_summary_table(
        result: pd.DataFrame,
        machine_schedule_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """스케줄링 결과 요약 테이블"""
        
        # 실제 작업만 필터링 (depth -1 제외)
        actual_jobs = result[~(result[config.columns.DEPTH] == -1)] if config.columns.DEPTH in result.columns else result
        
        # 기계별 작업 요약
        machine_summary = (
            machine_schedule_df
            .groupby([config.columns.MACHINE_CODE] if config.columns.MACHINE_CODE in machine_schedule_df.columns else [config.columns.MACHINE_INDEX])
            .agg({
                config.columns.WORK_START_TIME: 'count',  # 작업 개수
                config.columns.WORK_END_TIME: 'max'       # 최대 종료 시간
            })
            .rename(columns={
                config.columns.WORK_START_TIME: 'job_count',
                config.columns.WORK_END_TIME: 'max_end_time'
            })
            .reset_index()
        )
        
        return {
            "machine_summary_table": {
                "columns": list(machine_summary.columns),
                "data": machine_summary.to_dict('records')
            },
            "job_count": len(actual_jobs),
            "total_makespan": actual_jobs[config.columns.NODE_END].max() if config.columns.NODE_END in actual_jobs.columns else 0
        }