"""
results 모듈 - 스케줄링 결과 생성 통합 모듈

기존 results 모듈을 개선하여:
1. 호기_정보 (기존 유지)
2. 스케줄링_성과_지표 (신규)
3. 장비별_상세_성과 (신규)
4. 주문_지각_정보 (신규)
5. 간격_분석 (기존 detailed_gaps 개선)
"""

import pandas as pd
from config import config
from .data_cleaner import DataCleaner
from .merge_processor import MergeProcessor, create_process_detail_result
from .gantt_chart_generator import GanttChartGenerator
from .machine_info_builder import MachineInfoBuilder
from .performance_metrics import PerformanceMetricsCalculator
from .machine_detailed_analyzer import MachineDetailedAnalyzer
from .order_lateness_reporter import OrderLatenessReporter
from .simplified_gap_analyzer import SimplifiedGapAnalyzer


def create_results(
    raw_scheduling_result,
    merged_df,
    original_order,
    sequence_seperated_order,
    machine_mapper,
    base_date,
    scheduler
):
    """
    전체 결과 처리 파이프라인 (results 버전)

    Args:
        raw_scheduling_result (pd.DataFrame): 스케줄러 원본 결과
        merged_df (pd.DataFrame): 주문-공정 병합 데이터
        original_order (pd.DataFrame): 원본 주문 데이터
        sequence_seperated_order (pd.DataFrame): 공정별 분리 주문
        machine_mapper (MachineMapper): 기계 정보 매핑 관리 객체
        base_date (datetime): 기준 날짜
        scheduler: 스케줄러 인스턴스

    Returns:
        dict: 5개 테이블 + 메타 정보
            - machine_info: 호기_정보 (기존 형태)
            - performance_summary: 스케줄링_성과_지표
            - machine_detailed_performance: 장비별_상세_성과
            - order_lateness_report: 주문_지각_정보
            - gap_analysis: 간격_분석 (12개 컬럼)
            - actual_makespan: makespan (float)
            - gantt_filename: 간트차트 파일명
    """

    print("[85%] results 모듈로 결과 후처리 시작...")

    # ===================================================================
    # 1단계: 공통 전처리 (기존 DataCleaner 사용)
    # ===================================================================
    print("[86%] 공통 전처리 중...")
    cleaned_data = DataCleaner.clean_all_data(raw_scheduling_result, scheduler)

    result_cleaned = cleaned_data['result_cleaned']
    actual_makespan = cleaned_data['actual_makespan']
    total_makespan = cleaned_data['total_makespan']
    machine_schedule_df = cleaned_data['machine_schedule_df']

    print(f"[87%] 전처리 완료 - 실제 makespan: {actual_makespan:.1f}, 전체: {total_makespan:.1f}")

    # ===================================================================
    # 2단계: Aging 포함 상세 공정 결과 생성 (기존)
    # ===================================================================
    print("[87.5%] Aging 포함 상세 공정 결과 생성 중...")
    process_detail_df = create_process_detail_result(
        result_cleaned,
        sequence_seperated_order,
        scheduler
    )

    process_detail_df.to_csv("process_detail_df.csv", encoding = 'utf-8-sig')

    # ===================================================================
    # 3단계: 호기_정보 생성 (MachineInfoBuilder 사용)
    # ===================================================================
    print("[88%] 호기_정보 생성 중...")

    # MachineInfoBuilder로 호기 정보 생성 (원스톱)
    machine_builder = MachineInfoBuilder(machine_mapper, base_date)
    machine_info = machine_builder.create_complete_machine_info(
        machine_schedule_df,
        process_detail_df,
        original_order
    )

    machine_info.to_csv("machine_info.csv", encoding = 'utf-8-sig')
    print(f"[89%] 호기_정보 완료 - {len(machine_info)}행")

    # ===================================================================
    # 4단계: 신규 모듈 실행
    # ===================================================================

    # 4-1. 간격 분석 (SimplifiedGapAnalyzer)
    print("[90%] 간격 분석 중...")
    gap_analyzer = SimplifiedGapAnalyzer(
        scheduler,
        scheduler.delay_processor,
        machine_mapper,
        base_date
    )
    gap_analysis = gap_analyzer.analyze_all_gaps()
    print(f"[90%] 간격 분석 완료 - {len(gap_analysis)}개 간격")

    # 4-2. 성과 지표 (PerformanceMetricsCalculator)
    print("[91%] 스케줄링 성과 지표 계산 중...")
    metrics_calc = PerformanceMetricsCalculator(
        result_cleaned,
        original_order,
        scheduler,
        base_date,
        sequence_seperated_order  # ID-PO_NO 매핑용
    )
    performance_summary = metrics_calc.create_summary_table()
    print(f"[91%] 성과 지표 완료")

    # 4-3. 장비별 상세 분석 (MachineDetailedAnalyzer)
    print("[92%] 장비별 상세 성과 분석 중...")
    machine_analyzer = MachineDetailedAnalyzer(
        scheduler,
        gap_analyzer,
        machine_mapper
    )
    machine_detailed_performance = machine_analyzer.create_detailed_table()
    print(f"[92%] 장비별 상세 성과 완료 - {len(machine_detailed_performance)}개 기계")

    # 4-4. 주문 지각 정보 (OrderLatenessReporter)
    print("[93%] 주문 지각 정보 생성 중...")
    lateness_reporter = OrderLatenessReporter(
        result_cleaned,
        original_order,
        base_date,
        sequence_seperated_order  # ID-PO_NO 매핑용
    )
    order_lateness_report = lateness_reporter.create_lateness_table()
    print(f"[93%] 주문 지각 정보 완료 - {len(order_lateness_report)}개 주문")

    # ===================================================================
    # 5단계: 간트차트 생성
    # ===================================================================
    print("[95%] 간트차트 생성 중...")
    gantt_generator = GanttChartGenerator()
    gantt_filename = gantt_generator.generate(
        scheduler.Machines,
        gap_analyzer=None  # SimplifiedGapAnalyzer는 간트차트에서 사용 안 함
    )
    print(f"[95%] 간트차트 생성 완료 - {gantt_filename}")

    # ===================================================================
    # 6단계: 결과 검증 및 요약 출력
    # ===================================================================
    print("[97%] 결과 검증 중...")
    print(f"[검증] 원본 결과 행 수: {len(result_cleaned)}")
    print(f"[검증] 호기_정보 행 수: {len(machine_info)}")
    print(f"[검증] 성과 지표 행 수: {len(performance_summary)}")
    print(f"[검증] 장비 상세 행 수: {len(machine_detailed_performance)}")
    print(f"[검증] 지각 정보 행 수: {len(order_lateness_report)}")
    print(f"[검증] 간격 분석 행 수: {len(gap_analysis)}")

    # 성과 지표 출력
    metrics_dict = metrics_calc.get_metrics_dict()
    print(f"\n[성과] PO제품수: {metrics_dict['po_count']}개")
    print(f"[성과] 총 생산시간: {metrics_dict['makespan_hours']:.2f}시간")
    print(f"[성과] 납기준수율: {metrics_dict['ontime_delivery_rate']:.2f}%")
    print(f"[성과] 납기 지각 제품 개수: {metrics_dict['late_product_count']}개")

    # 지각 요약 출력
    lateness_summary = lateness_reporter.get_lateness_summary()
    print(f"\n[지각] 총 주문: {lateness_summary['total_orders']}개")
    print(f"[지각] 준수: {lateness_summary['ontime_orders']}개, 지각: {lateness_summary['late_orders']}개")
    print(f"[지각] 평균 지각일수 (지각 주문만): {lateness_summary['avg_lateness_days']:.2f}일")

    print("[98%] 모든 결과 처리 완료!")

    # ===================================================================
    # 7단계: 최종 결과 반환 (백엔드 API용 JSON 직렬화 가능 형태)
    # ===================================================================
    return {
        # 5개 테이블 (JSON 직렬화 가능한 dict 형태)
        'machine_info': machine_info.to_dict('records'),                          # 호기_정보
        'performance_summary': performance_summary.to_dict('records'),            # 스케줄링_성과_지표
        'machine_detailed_performance': machine_detailed_performance.to_dict('records'),  # 장비별_상세_성과
        'order_lateness_report': order_lateness_report.to_dict('records'),        # 주문_지각_정보
        'gap_analysis': gap_analysis.to_dict('records'),                          # 간격_분석

        # 메타 정보
        'metadata': {
            'actual_makespan': float(actual_makespan),
            'total_makespan': float(total_makespan),
            'gantt_filename': gantt_filename,
            'total_nodes': len(result_cleaned),
            'total_machines': len(machine_detailed_performance)
        },

        # 성과 지표 (요약)
        'performance_metrics': {
            'po_count': int(metrics_dict['po_count']),
            'makespan_hours': round(float(metrics_dict['makespan_hours']), 2),
            'ontime_delivery_rate': round(float(metrics_dict['ontime_delivery_rate']), 2),
            'late_product_count': int(metrics_dict['late_product_count'])
        },

        # 지각 요약
        'lateness_summary': {
            'total_orders': int(lateness_summary['total_orders']),
            'ontime_orders': int(lateness_summary['ontime_orders']),
            'late_orders': int(lateness_summary['late_orders']),
            'ontime_rate': round(float(lateness_summary['ontime_rate']), 2),
            'avg_lateness_days': round(float(lateness_summary['avg_lateness_days']), 2)
        }
    }
