from config import config
from .late_order import LateOrderCalculator
from .merge_results import ResultMerger
from .machine_schedule import MachineScheduleProcessor

def create_results(
        output_final_result,
        merged_df,
        original_order,
        sequence_seperated_order,
        machine_mapping,
        machine_schedule_df,
        base_date,
        scheduler
    ):
    """
    전체 결과 처리 파이프라인 함수

    Args:
        output_final_result (pd.DataFrame): 스케줄러 최종 결과
        merged_df (pd.DataFrame): 주문 및 공정 병합 데이터
        original_order (pd.DataFrame): 원본 주문 데이터
        sequence_seperated_order (pd.DataFrame): 공정별 분리 주문 데이터
        machine_mapping (dict): 머신 인덱스 -> 이름 매핑
        machine_schedule_df (pd.DataFrame): 기계 스케줄 데이터
        base_date (datetime): 기준 시간
        scheduler: 스케줄러 인스턴스 (기계 스케줄 데이터 생성에 필요시)

    Returns:
        dict: {
            'new_output_final_result': pd.DataFrame,  # 지각 계산 및 정렬 완료된 데이터
            'late_days_sum': int,                    # 총 지각 일수
            'merged_result': pd.DataFrame,           # 병합 결과
            'machine_info': pd.DataFrame              # 기계별 가독성 좋은 결과
        }
    """
    # 1. 지각 작업 처리
    late_calc = LateOrderCalculator(output_final_result, merged_df, original_order)
    new_output_final_result = late_calc.calculate_late_order()
    new_output_final_result, late_days_sum = late_calc.calc_late_days(new_output_final_result, base_date)
    new_output_final_result = new_output_final_result.sort_values(by=config.columns.END_TIME)

    print(new_output_final_result.head())

    # 2. 주문-공정 병합 처리
    merger = ResultMerger(merged_df, original_order.copy(), sequence_seperated_order)
    merged_result = merger.merge_everything()

    # 3. 기계 스케줄 처리
    # 만약 scheduler로부터 기계 스케줄 dataframe을 얻는 구조가 다르다면, 인자 받아 조절 필요
    machine_proc = MachineScheduleProcessor(machine_mapping, machine_schedule_df, output_final_result, base_date)
    machine_info = machine_proc.make_readable_result_file()
    machine_info = machine_proc.machine_info_decorate(merged_result)

    return {
        'new_output_final_result': new_output_final_result,
        'late_days_sum': late_days_sum,
        'merged_result': merged_result,
        'machine_info': machine_info
    }


# from results import process_full_results

# results = process_full_results(
#     output_final_result=output_final_result,
#     merged_df=merged_df,
#     original_order=original_order,
#     sequence_seperated_order=sequence_seperated_order,
#     machine_mapping=machine_mapping,
#     machine_schedule_df=scheduler.create_machine_schedule_dataframe(),
#     base_date=base_date,
#     scheduler=scheduler
# )

# print(f"지각 총 일 수: {results['late_days_sum']}")
# print(f"총 소요시간: {results['new_output_final_result']['종료시각'].max()/48}일")
# print(f"총 makespan: {results['new_output_final_result']['종료시각'].max()}")

# # 필요에 따라 파일 저장, 뷰 전달 등 자유롭게 사용
