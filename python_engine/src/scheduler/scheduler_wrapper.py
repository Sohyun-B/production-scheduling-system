"""
Scheduler wrapper

스케줄링 준비 및 실행 파이프라인 통합 함수
"""

from config import config
import pandas as pd
from .delay_dict import DelayProcessor
from .scheduler import Scheduler
from .dispatch_rules import create_dispatch_rule
from .scheduling_core import DispatchPriorityStrategy


def run_scheduler_pipeline(
    dag_df,
    sequence_seperated_order,
    width_change_df,
    machine_mapper,
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
    machine_mapper : MachineMapper
        기계 정보 매핑 관리 객체
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

    # ⭐ Phase 2 Day 2: machine_code_list 기반으로 변경
    machine_code_list = width_change_df[config.columns.MACHINE_CODE].unique().tolist()

    # DelayProcessor 생성 (코드 기반)
    delay_processor = DelayProcessor(
        opnode_dict, operation_delay_df, width_change_df, machine_code_list
    )

    # ★ Scheduler 생성 시 machine_mapper 추가
    scheduler = Scheduler(machine_dict, delay_processor, machine_mapper)
    scheduler.allocate_resources()

    # ⭐ Phase 2 Day 2: machine_code 직접 사용 (machine_index 변환 불필요)
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
