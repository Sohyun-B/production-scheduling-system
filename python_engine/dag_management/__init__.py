from .dag_dataframe import make_process_table, Create_dag_dataframe
from .node_dict import create_opnode_dict, create_machine_dict
from .dag_manager import DAGGraphManager
from .dag_visualizer import DAGVisualizer

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


# from dag_management import run_dag_pipeline

# def main():
#     dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
#         merged_df, hierarchy, sequence_seperated_order, linespeed, machine_columns
#     )
#     # 이후 manager 등으로 후속 스케줄링 작업 수행
