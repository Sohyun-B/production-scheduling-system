from .dag_dataframe import make_process_table, Create_dag_dataframe, insert_aging_nodes_to_dag, parse_aging_requirements
from .node_dict import create_opnode_dict, create_machine_dict
from .dag_manager import DAGGraphManager
from config import config
import pandas as pd


def run_dag_pipeline(merged_df, hierarchy, sequence_seperated_order, linespeed, machine_mapper):
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
    machine_dict = create_machine_dict(sequence_seperated_order, linespeed, machine_mapper)

    return dag_df, opnode_dict, manager, machine_dict


def create_complete_dag_system(sequence_seperated_order, linespeed, machine_mapper, aging_df):
    """
    DAG 생성을 위한 전체 파이프라인을 한번에 처리하는 통합 함수

    Args:
        sequence_seperated_order: 전처리된 주문 데이터
        linespeed: 라인스피드 데이터
        machine_mapper: MachineMapper 객체 (기계 정보 매핑 관리)
        aging_map: parse_aging_requirements()의 결과 (선택 사항)

    Returns:
        tuple: (dag_df, opnode_dict, manager, machine_dict, merged_df)
    """

    print("[38%] Aging 요구사항 파싱 중...")
    aging_map = parse_aging_requirements(aging_df, sequence_seperated_order)
    print(f"[INFO] {len(aging_map)}개의 aging 노드 생성 예정")

    merged_df = make_process_table(sequence_seperated_order)
    hierarchy = sorted(
        [col for col in merged_df.columns if col.endswith(config.columns.PROCESS_ID_SUFFIX)],
        key=lambda x: int(x.replace(config.columns.PROCESS_ID_SUFFIX, ''))
    )
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        merged_df, hierarchy, sequence_seperated_order, linespeed,
        machine_mapper=machine_mapper
    )

    # NEW: aging 노드 처리
    if aging_map:
        print("[42%] Aging 노드 DAG에 삽입 중...")

        # 1. dag_df에 aging 노드 추가
        dag_df = insert_aging_nodes_to_dag(dag_df, aging_map)

        # 2. machine_dict에 aging 노드 추가
        aging_nodes_dict = {
            info['aging_node_id']: info['aging_time']
            for parent_id, info in aging_map.items()
        }
        for aging_node_id, aging_time in aging_nodes_dict.items():
            machine_dict[aging_node_id] = {'AGING': int(aging_time)}

        # 3. DAGGraphManager 재빌드 (aging 노드 포함)
        manager = DAGGraphManager(opnode_dict)
        manager.build_from_dataframe(dag_df)

        # 4. aging 노드에 is_aging 플래그 설정
        for parent_id, info in aging_map.items():
            aging_node_id = info['aging_node_id']
            if aging_node_id in manager.nodes:
                manager.nodes[aging_node_id].is_aging = True

        print(f"[44%] Aging 노드 DAG 삽입 완료 - {len(aging_map)}개 노드")

    return dag_df, opnode_dict, manager, machine_dict, merged_df