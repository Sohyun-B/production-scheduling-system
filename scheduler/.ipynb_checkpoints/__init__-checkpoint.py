from .scheduler import Scheduler
from .delay_dict import DelayProcessor
from .machine import Machine_Time_window  # 필요에 따라 변경, 혹은 제외 가능
from .chart import DrawChart
from .dispatch_rules import create_dispatch_rule, allocating_schedule_by_dispatching_priority, reallocating_schedule_by_user
from dag_management.dag_manager import DAGGraphManager


# 이후 클래스로 변환 필요??? 


def run_schedule(dag_df, sequence_seperated_order, machine_dict, manager, window_days, opnode_dict, machine_limit, base_date, operation_delay_df, width_change_df):
    """
    스케줄링 전체 파이프라인 처리 함수
    
    파라미터:
    - dag_df: DAG 데이터프레임
    - sequence_seperated_order: 시퀀스별 분리 주문 데이터프레임
    - machine_dict: 기계별 소요시간 정보 딕셔너리
    - window_days: dispatching window 크기 (예: 5)
    - opnode_dict: 노드 정보 딕셔너리
    - machine_limit: 기계가 사용 불가능한 시간 데이터프레임
    - base_date: 스케줄링이 시작하는 날짜

    반환:
    - output_final_result: 스케줄링 결과 데이터프레임
    - manager: DAGGraphManager 인스턴스 (추가 스케줄링 제어 등 용)
    - scheduler: Scheduler 인스턴스
    """

    # 1. 딜레이 처리기 생성
    delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)

    # 2. 디스패칭 룰 생성
    dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)

    # 3. 스케줄러 초기화 및 자원 할당
    scheduler = Scheduler(machine_dict, delay_processor)
    scheduler.allocate_resources()

    # 4. DAG 그래프 매니저 생성 및 스케줄러 할당
    manager.allocate_scheduler(scheduler)
    manager.reset_all_nodes()

    scheduler.allocate_unable_machine_info(machine_limit, base_date)

    # 5. 디스패치 우선순위 기반 스케줄링 수행
    output_final_result = allocating_schedule_by_dispatching_priority(
        dag_df, dispatch_rule_ans, window_days, manager=manager
    )

    # 6. 간트 파일 저장
    gantt = DrawChart(scheduler.Machines)

    # 7. 결과 저장
    return output_final_result, manager, scheduler


def run_reschedule(scheduler, machine_queues, manager, machine_limit, base_date):
    scheduler.allocate_resources()
    
    # 4. DAG 그래프 매니저 생성 및 스케줄러 할당
    manager.allocate_scheduler(scheduler)
    manager.reset_all_nodes()
    
    scheduler.allocate_unable_machine_info(machine_limit, base_date)
    
    new_output_final_result = reallocating_schedule_by_user(machine_queues, manager)
    return new_output_final_result
