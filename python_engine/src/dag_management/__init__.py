from .dag_dataframe import make_process_table, Create_dag_dataframe
from .node_dict import create_opnode_dict, create_machine_dict
from .dag_manager import DAGGraphManager
from .dag_visualizer import DAGVisualizer
from config import config
import pandas as pd


def create_aging_map(aging_df):
    """
    AGING 데이터프레임에서 aging_map 딕셔너리 생성
    
    Args:
        aging_df (pd.DataFrame): AGING내역.xlsx에서 읽은 데이터프레임
            필수 컬럼: GitemNo, next_ProcGbn, aging_time
    
    Returns:
        dict: {(GitemNo, next_ProcGbn): aging_time * 2} 형태의 딕셔너리
            - aging_time이 없거나 NaN인 경우 제외
            - aging_time은 2배로 변환되어 저장
    
    Example:
        >>> aging_df = pd.read_excel("AGING내역.xlsx", sheet_name="DB AGING 테이블", skiprows=1)
        >>> aging_map = create_aging_map(aging_df)
        >>> # {('32528', '투명'): 96.0, ('32409', '투명'): 96.0, ...}
    """
    # 빈 DataFrame이면 빈 딕셔너리 반환
    if aging_df.empty:
        return {}
    
    # aging_time 컬럼을 숫자로 변환 (에러 발생 시 NaN)
    aging_df = aging_df.copy()
    if 'aging_time' in aging_df.columns:
        aging_df['aging_time'] = pd.to_numeric(aging_df['aging_time'], errors='coerce')
    
    # aging_map 생성: {(GitemNo, next_ProcGbn): aging_time * 2}
    aging_map = {
        (str(row['GitemNo']), str(row['next_ProcGbn'])): float(row['aging_time']) * 2
        for _, row in aging_df.iterrows()
        if ('GitemNo' in aging_df.columns and 
            'next_ProcGbn' in aging_df.columns and 
            'aging_time' in aging_df.columns)
           and pd.notna(row['GitemNo']) 
           and pd.notna(row['next_ProcGbn']) 
           and pd.notna(row['aging_time'])
    }
    
    return aging_map


def run_dag_pipeline(merged_df, hierarchy, sequence_seperated_order, linespeed, machine_columns, aging_map=None):
    """
    dag_management 모듈 내 주요 함수들을 종합 호출하여
    DAG 생성부터 노드-기계 사전 생성까지 한 번에 처리하는 편리 함수
    """

    # 1. DAG 데이터프레임 생성
    mnc = Create_dag_dataframe()
    
    dag_df = mnc.create_full_dag(merged_df, hierarchy)

    # 2. 노드 사전 생성
    opnode_dict = create_opnode_dict(sequence_seperated_order, aging_map)

    # 3. DAG 그래프 매니저 생성 및 빌드
    manager = DAGGraphManager(opnode_dict)
    manager.build_from_dataframe(dag_df)

    # 4. 기계 딕셔너리 생성
    machine_dict = create_machine_dict(sequence_seperated_order, linespeed, machine_columns)

    return dag_df, opnode_dict, manager, machine_dict


def create_complete_dag_system(sequence_seperated_order, linespeed, machine_master_info, aging_df=None):
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
    # aging_df가 제공되면 aging_map 생성
    if aging_df is not None:
        aging_map = create_aging_map(aging_df)
    else:
        aging_map = {}
    
    merged_df = make_process_table(sequence_seperated_order)

    print("merged_df")
    print(merged_df.columns)
    hierarchy = sorted(
        [col for col in merged_df.columns if col.endswith(config.columns.PROCESS_ID_SUFFIX)],
        key=lambda x: int(x.replace(config.columns.PROCESS_ID_SUFFIX, ''))
    )
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        merged_df, hierarchy, sequence_seperated_order, linespeed,
        machine_columns=machine_master_info[config.columns.MACHINE_CODE].values.tolist(),
        aging_map=aging_map
    )
    
    return dag_df, opnode_dict, manager, machine_dict, merged_df