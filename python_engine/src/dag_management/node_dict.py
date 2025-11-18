import pandas as pd
import numpy as np
from config import config

def create_opnode_dict(sequence_seperated_order):
    opnode_dict = {}

    for _, row in sequence_seperated_order.iterrows():
        # CHEMICAL_LIST 문자열을 튜플로 변환
        chemical_str = str(row[config.columns.CHEMICAL_LIST])
        if chemical_str == "None" or chemical_str.strip() == "":
            chemical_tuple = ()
        else:
            # 'A|B' -> ('A','B'), 'A' -> ('A',)
            chemical_tuple = tuple(chemical_str.split("|"))
        
        opnode_dict[row[config.columns.PROCESS_ID]] = {
            "OPERATION_ORDER": row[config.columns.OPERATION_ORDER],
            "OPERATION_CODE": row[config.columns.OPERATION_CODE],
            "OPERATION_CLASSIFICATION": row[config.columns.OPERATION_CLASSIFICATION],
            "FABRIC_WIDTH": row[config.columns.FABRIC_WIDTH],
            "CHEMICAL_LIST": chemical_tuple,
            "PRODUCTION_LENGTH": row[config.columns.PRODUCTION_LENGTH],
            "SELECTED_CHEMICAL": None,  # 초기값
        }
    
    return opnode_dict



def create_machine_dict(sequence_seperated_order, linespeed, machine_mapper, aging_nodes_dict=None):
    """
    machine_dict 생성 (코드 기반)

    ⚠️ 리팩토링: 인덱스 기반 → 코드 기반 machine_dict

    Args:
        sequence_seperated_order: 주문 시퀀스 DataFrame
        linespeed: Long Format DataFrame [gitemno, proccode, machineno, linespeed]
        machine_mapper: MachineMapper 인스턴스
        aging_nodes_dict: Aging 노드 딕셔너리 (optional)

    Returns:
        machine_dict: {node_id: {machine_code: processing_time}}
    """
    # ⭐ Step 1: Linespeed 캐시 생성 (O(1) 조회용, vectorized 방식)
    print("[INFO] Linespeed 캐시 생성 중...")

    # Vectorized 방식으로 캐시 생성 (iterrows()보다 10~100배 빠름)
    linespeed_cache = dict(zip(
        zip(
            linespeed[config.columns.GITEM].astype(str),
            linespeed[config.columns.OPERATION_CODE].astype(str),
            linespeed[config.columns.MACHINE_CODE].astype(str)
        ),
        linespeed['linespeed'].astype(float)
    ))

    print(f"[INFO] Linespeed 캐시 생성 완료: {len(linespeed_cache)}개 항목")

    # ⭐ Step 2: machine_dict 생성 (코드 기반)
    machine_dict = {}
    all_machine_codes = machine_mapper.get_all_codes()

    for _, order_row in sequence_seperated_order.iterrows():
        node_id = order_row[config.columns.PROCESS_ID]
        gitem = str(order_row[config.columns.GITEM])
        proccode = str(order_row[config.columns.OPERATION_CODE])
        production_length = float(order_row[config.columns.PRODUCTION_LENGTH])

        machine_dict[node_id] = {}

        # 모든 기계에 대해 처리시간 계산
        for machine_code in all_machine_codes:
            # 캐시에서 linespeed 조회 (O(1))
            cache_key = (gitem, proccode, machine_code)
            linespeed_value = linespeed_cache.get(cache_key)

            if linespeed_value is None or linespeed_value == 0:
                # linespeed 없음 → 처리 불가
                processing_time = 9999
            else:
                # 처리시간 계산
                processing_time = np.ceil(
                    production_length /
                    linespeed_value /
                    config.constants.TIME_MULTIPLIER
                )

                # inf/NaN 안전 처리
                if not np.isfinite(processing_time):
                    processing_time = 9999

            # ⭐ 코드 기반 저장 (인덱스 변환 제거!)
            machine_dict[node_id][machine_code] = int(processing_time)

    print(f"[INFO] machine_dict 생성 완료: {len(machine_dict)}개 노드")

    # Aging 노드 추가
    if aging_nodes_dict:
        for aging_node_id, aging_time in aging_nodes_dict.items():
            machine_dict[aging_node_id] = {'AGING': int(aging_time)}
        print(f"[INFO] {len(aging_nodes_dict)}개 Aging 노드 추가")

    return machine_dict