from config import config
import pandas as pd
from .delay_dict import DelayProcessor
from .scheduler import Scheduler
from .dispatch_rules import create_dispatch_rule
from .scheduling_core import DispatchPriorityStrategy

# def run_schedule(dag_df, sequence_seperated_order, machine_dict, manager, window_days, opnode_dict, machine_limit, base_date, operation_delay_df, width_change_df, use_level4=False):
#     """
#     스케줄링 전체 파이프라인 처리 함수
    
#     파라미터:
#     - dag_df: DAG 데이터프레임
#     - sequence_seperated_order: 시퀀스별 분리 주문 데이터프레임
#     - machine_dict: 기계별 소요시간 정보 딕셔너리
#     - window_days: dispatching window 크기 (예: 5)
#     - opnode_dict: 노드 정보 딕셔너리
#     - machine_limit: 기계가 사용 불가능한 시간 데이터프레임
#     - base_date: 스케줄링이 시작하는 날짜
#     - use_level4: Level 4 전략 사용 여부 (기본값: False, 기존 방식 사용)

#     반환:
#     - output_final_result: 스케줄링 결과 데이터프레임
#     - manager: DAGGraphManager 인스턴스 (추가 스케줄링 제어 등 용)
#     - scheduler: Scheduler 인스턴스
#     """
    

#     # 1. 딜레이 처리기 생성
#     delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)

#     # 2. 디스패칭 룰 생성
#     dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)

#     # 3. 스케줄러 초기화 및 자원 할당
#     scheduler = Scheduler(machine_dict, delay_processor)
#     scheduler.allocate_resources()


#     # 특정 기계를 특정 시간/혹은 전체 시간동안 사용 못하는 경우 할당
#     scheduler.allocate_unable_machine_info(machine_limit, base_date)



#     # 5. 스케줄링 실행 (Level 4 전략 또는 기존 방식)
#     if use_level4:
#         # Level 4 전략 사용
#         strategy = DispatchPriorityStrategy()
#         output_final_result_df = strategy.execute(
#             dag_manager=manager,
#             scheduler=scheduler,
#             dag_df=dag_df,
#             priority_order=dispatch_rule_ans,
#             window_days=window_days
#         )
#         output_final_result = output_final_result_df
#     else:
#         # 기존 방식 사용
#         dag_scheduler = DAGScheduler(scheduler, manager)
#         output_final_result = allocating_schedule_by_dispatching_priority(
#             dag_df, dispatch_rule_ans, window_days, dag_scheduler=dag_scheduler
#         )

#     # 6. 간트 파일 저장
#     gantt = DrawChart(scheduler.Machines)

#     # 7. 결과 저장
#     return output_final_result, manager, scheduler


# def run_reschedule(scheduler, machine_queues, manager, machine_limit, base_date, use_level4=False):
#     scheduler.allocate_resources()
    
    
#     scheduler.allocate_unable_machine_info(machine_limit, base_date)
    
#     # 재스케줄링 실행 (Level 4 전략 또는 기존 방식)
#     if use_level4:
#         # Level 4 전략 사용
#         strategy = UserRescheduleStrategy()
#         new_output_final_result = strategy.execute(manager, scheduler, machine_queues)
#     else:
#         # 기존 방식 사용
#         dag_scheduler = DAGScheduler(scheduler, manager)
#         new_output_final_result = reallocating_schedule_by_user(machine_queues, dag_scheduler)
    
#     return new_output_final_result

def run_scheduler_pipeline(
    dag_df,
    sequence_seperated_order,
    width_change_df,
    machine_master_info,
    opnode_dict,
    operation_delay_df,
    machine_dict,
    machine_rest,
    base_date,
    manager,
    window_days,
):
    """스케줄링 준비 및 실행 파이프라인을 수행하고 결과와 스케줄러를 반환합니다.

    Parameters
    ----------
    dag_df : pd.DataFrame
    sequence_seperated_order : pd.DataFrame
    width_change_df : pd.DataFrame
    machine_master_info : pd.DataFrame
    opnode_dict : dict
    operation_delay_df : pd.DataFrame
    machine_dict : dict
    machine_rest : pd.DataFrame
    base_date : datetime
    manager : object
    window_days : int

    Returns
    -------
    (result_df, scheduler)
    """

    # 디스패치 룰 생성
    print("[65%] 디스패치 규칙 생성 중...")
    dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)



    # 스케줄러 초기화
    print("[70%] 스케줄러 초기화 및 자원 할당 중...")

    # MACHINE_CODE → MACHINE_INDEX dict 생성 후 공정교체시간 존재하는 기계인덱스만 가져옴
    code_to_index = dict(
        zip(
            machine_master_info[config.columns.MACHINE_CODE],
            machine_master_info[config.columns.MACHINE_INDEX],
        )
    )
    machine_index_list = (
        width_change_df[config.columns.MACHINE_CODE].map(code_to_index).tolist()
    )

    width_change_df = pd.merge(
        width_change_df, machine_master_info, on=config.columns.MACHINE_CODE, how="left"
    )
    delay_processor = DelayProcessor(
        opnode_dict, operation_delay_df, width_change_df, machine_index_list
    )

    scheduler = Scheduler(machine_dict, delay_processor)
    scheduler.allocate_resources()

    machine_rest = pd.merge(
        machine_rest, machine_master_info, on=config.columns.MACHINE_CODE, how="left"
    )
    scheduler.allocate_machine_downtime(machine_rest, base_date)
    print("[스케줄러] 기계 자원 할당 완료, 기계 중단시간 설정 완료")

    # 전략 실행 (가장 시간이 오래 걸리는 단계)
    print("[75%] 스케줄링 알고리즘 실행 중...")
    strategy = DispatchPriorityStrategy()
    result = strategy.execute(
        dag_manager=manager,
        scheduler=scheduler,
        dag_df=dag_df,
        priority_order=dispatch_rule_ans,
        window_days=window_days,
    )

    return result, scheduler
