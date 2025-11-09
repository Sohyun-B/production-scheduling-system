from .dag_dataframe import make_process_table, Create_dag_dataframe
from .node_dict import create_opnode_dict, create_machine_dict
from .dag_manager import DAGGraphManager
from .dag_visualizer import DAGVisualizer
from config import config
import pandas as pd


def run_dag_pipeline(merged_df, hierarchy, sequence_seperated_order, linespeed, machine_columns):
    """
    dag_management 모듈 내 주요 함수들을 종합 호출하여
    DAG 생성부터 노드-기계 사전 생성까지 한 번에 처리하는 편리 함수
    """

    # 1. DAG 데이터프레임 생성
    mnc = Create_dag_dataframe()
    
    dag_df = mnc.create_full_dag(merged_df, hierarchy)

    # 2. 노드 사전 생성
    opnode_dict = create_opnode_dict(sequence_seperated_order)

    # 3. DAG 그래프 매니저 생성 및 빌드
    manager = DAGGraphManager(opnode_dict)
    manager.build_from_dataframe(dag_df)

    # 4. 기계 딕셔너리 생성
    machine_dict = create_machine_dict(sequence_seperated_order, linespeed, machine_columns)

    return dag_df, opnode_dict, manager, machine_dict


def create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info):
    """
    DAG 생성을 위한 전체 파이프라인을 한번에 처리하는 통합 함수
    
    Args:
        sequence_seperated_order: 전처리된 주문 데이터
        linespeed: 라인스피드 데이터
        machine_master_info: 기계 마스터 정보
        aging_df: AGING내역.xlsx에서 읽은 DataFrame (선택 사항)
        
    Returns:
        tuple: (dag_df, opnode_dict, manager, machine_dict, merged_df)
    """
    sequence_seperated_order.to_csv("sequence_seperated_order.csv", encoding='utf-8-sig', index=False)

    merged_df = make_process_table(sequence_seperated_order)
    merged_df.to_csv("merged_df.csv", encoding='utf-8-sig', index=False)
    print("merged_df")
    print(merged_df.columns)
    hierarchy = sorted(
        [col for col in merged_df.columns if col.endswith(config.columns.PROCESS_ID_SUFFIX)],
        key=lambda x: int(x.replace(config.columns.PROCESS_ID_SUFFIX, ''))
    )
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        merged_df, hierarchy, sequence_seperated_order, linespeed,
        machine_columns=machine_master_info[config.columns.MACHINE_CODE].values.tolist()
    )
    
    return dag_df, opnode_dict, manager, machine_dict, merged_df