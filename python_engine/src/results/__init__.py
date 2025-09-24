import pandas as pd
import os
from config import config

# 통합된 모듈들 import
from .data_cleaner import DataCleaner
from .late_processor import LateProcessor
from .merge_processor import MergeProcessor
from .machine_processor import MachineProcessor
from .gap_analyzer import GapAnalysisProcessor
from .gantt_chart_generator import GanttChartGenerator


def create_results(
        raw_scheduling_result,
        merged_df,
        original_order,
        sequence_seperated_order,
        machine_master_info,
        base_date,
        scheduler
    ):
    """
    전체 결과 처리 파이프라인 함수 (모듈화된 버전)
    
    각 기능을 독립적인 모듈로 분리하여 처리:
    1. 공통 전처리 (가짜 작업 삭제)
    2-4. 병렬 처리 가능한 독립 모듈들
    5. Gap 분석 (독립)
    6. 간트차트 생성

    Args:
        raw_scheduling_result (pd.DataFrame): 스케줄러 원본 결과 (depth -1 포함)
        merged_df (pd.DataFrame): 주문 및 공정 병합 데이터
        original_order (pd.DataFrame): 원본 주문 데이터
        sequence_seperated_order (pd.DataFrame): 공정별 분리 주문 데이터
        machine_master_info (pd.DataFrame): 기계 마스터 정보
        base_date (datetime): 기준 시간
        scheduler: 스케줄러 인스턴스

    Returns:
        dict: 모든 처리 결과가 포함된 딕셔너리
    """
    
    print("[85%] 결과 후처리 시작...")
    
    # === 1단계: 공통 전처리 (가짜 작업 삭제 및 makespan 계산) ===
    print("[86%] 공통 전처리 중...")
    cleaned_data = DataCleaner.clean_all_data(raw_scheduling_result, scheduler)
    
    result_cleaned = cleaned_data['result_cleaned']
    actual_makespan = cleaned_data['actual_makespan']
    total_makespan = cleaned_data['total_makespan']
    machine_schedule_df = cleaned_data['machine_schedule_df']
    
    print(f"[87%] 전처리 완료 - 실제 makespan: {actual_makespan:.1f}, 전체: {total_makespan:.1f}")
    
    # === 2-4단계: 독립적 처리들 (병렬 가능) ===
    # 2. 지각 작업 처리
    print("[88%] 지각 작업 처리 중...")
    late_processor = LateProcessor(base_date)
    late_results = late_processor.process(result_cleaned, merged_df, original_order)

    # 추후 삭제 예정
    late_results['new_output_final_result'].to_csv("지각작업처리결과.csv", encoding = 'utf-8-sig')
    
    # 3. 주문-공정 병합 처리
    print("[89%] 주문-공정 병합 처리 중...")
    merge_processor = MergeProcessor()
    merge_results = merge_processor.process(merged_df, original_order, sequence_seperated_order)

    # 추후 삭제 예정
    merge_results['merged_result'].to_csv("merged_result.csv", encoding = 'utf-8-sig')
    merge_results['order_info'].to_csv("order_info.csv", encoding = 'utf-8-sig')

    
    # 4. 기계 기준 정보 처리 (gap_analyzer 없이 먼저)
    print("[90%] 기계 기준 정보 처리 중...")
    machine_processor = MachineProcessor(base_date)
    
    # === 5단계: Gap 분석 (독립) ===
    print("[91%] 간격 분석 중...")
    gap_processor = GapAnalysisProcessor(base_date)
    gap_results = gap_processor.process(scheduler, machine_schedule_df, result_cleaned, machine_master_info)
    
    # 4단계 완료: 기계 기준 정보 (gap_analyzer 포함)
    machine_results = machine_processor.process(
        machine_schedule_df, 
        result_cleaned, 
        machine_master_info, 
        merge_results['merged_result'],
        original_order,
        gap_results['gap_analyzer']
    )
    
    # === 6단계: 간트차트 생성 ===
    print("[95%] 간트차트 생성 중...")
    gantt_generator = GanttChartGenerator()
    gantt_filename = gantt_generator.generate(
        scheduler.Machines, 
        gap_results['gap_analyzer']
    )
    
    # === 7단계: 주문 생산 요약본 생성 ===
    print("[96%] 주문 생산 요약본 생성 중...")
    order_summary = late_results['new_output_final_result'].copy()
    if config.columns.END_TIME in order_summary.columns:
        order_summary = order_summary[[config.columns.PO_NO, '1_PROCCODE', '2_PROCCODE', '3_PROCCODE', '4_PROCCODE', config.columns.GITEM, config.columns.DUE_DATE, config.columns.END_DATE, config.columns.LATE_DAYS]]
    
    # === 8단계: 데이터 검증 및 최종 정리 ===
    print("[97%] 데이터 검증 중...")
    print(f"[검증] 원본 결과 행 수: {len(result_cleaned)}")
    print(f"[검증] 처리된 결과 행 수: {len(late_results['new_output_final_result'])}")
    print(f"[검증] 원본 최대 node_end: {result_cleaned['node_end'].max()}")
    print(f"[분석] 총 소요시간: {late_results['new_output_final_result'][config.columns.END_TIME].max() / 48:.2f}일")
    print(f"[분석] 총 makespan: {late_results['new_output_final_result'][config.columns.END_TIME].max()}")
    
    print("[98%] 모든 결과 처리 완료!")
    
    # === 최종 결과 반환 ===
    return {
        # makespan 정보
        'actual_makespan': actual_makespan,
        'total_makespan': total_makespan,
        
        # 지각 처리 결과
        'new_output_final_result': late_results['new_output_final_result'],
        'late_days_sum': late_results['late_days_sum'],
        'late_products': late_results['late_products'],
        'late_po_numbers': late_results['late_po_numbers'],
        
        # 병합 처리 결과
        'merged_result': merge_results['merged_result'],
        'order_info': merge_results['order_info'],
        
        # 기계 정보 결과
        'machine_info': machine_results['machine_info'],
        
        # 주문 요약
        'order_summary': order_summary,
        
        # 분석 결과
        'gap_analyzer': gap_results['gap_analyzer'],
        'detailed_gaps': gap_results['detailed_gaps'],
        'machine_summary': gap_results['machine_summary'],
        'gantt_filename': gantt_filename
    }