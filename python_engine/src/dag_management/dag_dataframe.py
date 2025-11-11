import pandas as pd
import numpy as np
import ast
from collections import defaultdict, OrderedDict
import copy
import re
from config import config

class Create_dag_dataframe:
    """
    최적화된 DAG(방향성 비순환 그래프) 생성 클래스
    주요 기능:
    1. NaN 값과 'nan' 문자열을 완전히 제거
    2. 실제 데이터 흐름 기반 계층 구조 자동 연결
    3. 대규모 데이터 처리에 최적화된 벡터 연산 사용 
    """
    
    def __init__(self):
        """초기화 함수: 노드 연결 정보 저장을 위한 레지스트리 생성"""
        self.node_registry = defaultdict(set)  # {부모노드: {자식노드들}} 구조
    
    def _is_valid_node(self, value):
        """
        [헬퍼 함수] 유효한 노드인지 3단계 검증
        1. pd.isna(): 실제 NaN 값 체크
        2. 문자열 변환 후 공백 제거
        3. 'nan' 문자열 여부 확인
        """
        if pd.isna(value):  # 1차 필터링: 실제 NaN 값
            return False
        cleaned = str(value).strip().lower()  # 2차 처리: 문자열 정규화
        return cleaned != 'nan'  # 3차 필터링: 문자열 'nan' 차단

    def create_full_dag(self, df, hierarchy):
        """
        [메인 함수] DAG 생성 파이프라인
        프로세스:
        1단계: 유효 노드 추출 → 2단계: 계층 연결 → 3단계: DAG 생성
        """
        # 1단계: 계층별 유효 노드 추출 및 깊이 매핑 -------------------------------------------------
        node_depth_map = {}  # {노드명: 깊이} 저장 딕셔너리
        
        # 각 계층 컬럼 순회 (enumerate 시작값 1로 설정해 깊이 1부터 시작)
        for depth, col in enumerate(hierarchy, 1):
            # NaN 제거 → 문자열 변환 → 공백 제거 → 'nan' 필터링
            valid_nodes = df[col].dropna().astype(str).str.strip()
            valid_nodes = valid_nodes[~valid_nodes.str.lower().eq('nan')]
            
            # 고유 노드 추출 및 깊이 정보 저장
            node_depth_map.update({node: depth for node in valid_nodes.unique()})
    
        # 2단계: 실제 데이터 흐름 기반 계층 연결 ----------------------------------------------------
        for _, row in df.iterrows():
            valid_chain = []
            
            # 위치(계층 정보 포함) 함께 수집
            for idx, col in enumerate(hierarchy):
                val = row[col]
                if self._is_valid_node(val):
                    node = str(val).strip()
                    valid_chain.append((idx, node))  # (계층 위치, 노드명)
            
            if len(valid_chain) >= 2:
                for (prev_idx, parent), (curr_idx, child) in zip(valid_chain[:-1], valid_chain[1:]):
                    # 연속된 계층이거나, 중간 계층이 NaN일 때만 연결 허용
                    if curr_idx - prev_idx >= 1:
                        self.node_registry[parent].add(child)
    
    
        # 3단계: 최종 DAG 데이터프레임 생성 --------------------------------------------------------
        dag_data = []
        for node, depth in node_depth_map.items():
            children = sorted(self.node_registry.get(node, set()))  # 자식 노드 정렬
            dag_data.append({
                'ID': node,
                'DEPTH': depth,  # 원본 계층 깊이 유지
                'CHILDREN': ', '.join(children) if children else ''  # 자식 목록 문자열화
            })
    
        # 깊이 → 노드ID 순으로 정렬 후 반환
        return pd.DataFrame(dag_data).sort_values(['DEPTH', 'ID'])

class DAGNode:
    def __init__(self, node_id, depth, is_aging=False):
        # === 그래프 구조 관련 속성 (불변) ===
        self.id = node_id
        self.depth = depth
        self.is_aging = is_aging             # NEW: Aging 노드 플래그
        self.children = []                   # 후속 작업 노드들
        self.all_descendants = []            # 모든 후손 노드들 (그래프 분석용)

        # === 스케줄링 실행 관련 속성 (가변) ===
        self.earliest_start = None           # 최조 시작 가능 시간
        self.parent_node_count = 0           # 현재 대기 중인 부모 개수
        self.processing_time = None          # 가공 소요 시간
        self.machine = None                  # 할당된 기계
        self.node_start = None               # 실제 시작 시간
        self.node_end = None                 # 실제 종료 시간 (주의: node_start + processing_time과 일치해야 함)
        self.parent_node_end = [0]           # 부모들의 종료 시간 리스트


    def save_initial_state(self):
        """GA용 초기 상태 저장 (현재 미사용)"""
        pass

    def restore_initial_state(self):
        """GA용 초기 상태 복원 (현재 미사용)"""
        pass


def make_process_table(df):
    """
    각 P/O NO에 대해 해당 주문의 경로 만들기
    """
    # 1. 'P/O NO' 쉼표로 분리 후 행 폭발
    df = df.copy()
    df[config.columns.PO_NO] = df[config.columns.PO_NO].str.split(',')
    df_exploded = df.explode(config.columns.PO_NO).reset_index(drop=True)
    df_exploded[config.columns.PO_NO] = df_exploded[config.columns.PO_NO].str.strip()  # 공백 제거

    

    # 2. 공정순서별로 'n공정' 컬럼명 생성
    df_exploded['operation_col'] = df_exploded[config.columns.OPERATION_ORDER].astype(str) + config.columns.PROCESS_ID_SUFFIX

    # 3. 피벗: P/O NO, GITEM별로 공정순서별 공정명을 컬럼으로
    pivot_df = df_exploded.pivot_table(
        index=[config.columns.PO_NO],
        columns='operation_col',
        values=config.columns.ID,
        aggfunc='first'
    ).reset_index()

    # 4. 컬럼명 정리 (MultiIndex 해제)
    pivot_df.columns.name = None

    return pivot_df


# ============================================================================
# Aging 관련 함수들
# ============================================================================

def is_aging_node(node_id, machine_dict):
    """
    Aging 노드 감지 - machine_dict 구조 기반

    Args:
        node_id: 노드 ID
        machine_dict: 기계 딕셔너리

    Returns:
        True if node is aging operation
    """
    if node_id not in machine_dict:
        return False

    # machine_dict가 {-1: time}만 가지면 aging
    return set(machine_dict[node_id].keys()) == {-1}


def parse_aging_requirements(aging_df, sequence_seperated_order):
    """
    aging_df를 파싱하여 어떤 노드 이후에 aging을 삽입할지 결정

    Args:
        aging_df: aging 요구사항 데이터프레임
            필수 컬럼: gitemno, proccode, aging_time
        sequence_seperated_order: 전처리된 주문 시퀀스

    Returns:
        aging_map: {
            parent_node_id: {
                "aging_time": 48,
                "aging_node_id": "N00001_AGING",
                "next_node_id": "N00002"
            }
        }
    """

    print(f"parse_aging_requirements: {sequence_seperated_order.columns}")
    print(sequence_seperated_order[config.columns.GITEM].dtype)
    print(sequence_seperated_order[config.columns.OPERATION_CODE].dtype)
    print(aging_df[config.columns.GITEM].dtype)
    print(aging_df[config.columns.OPERATION_CODE].dtype)

    aging_map = {}

    print(f"[INFO] parse_aging_requirements: aging_df에 {len(aging_df)}개 행 존재")

    for _, row in aging_df.iterrows():
        gitemno = str(row[config.columns.GITEM])
        proccode = str(row[config.columns.OPERATION_CODE])  # aging 이전 공정
        aging_time = int(row[config.columns.AGING_TIME])

        
        
        sequence_seperated_order.to_csv("sequence_seperated_order.csv", encoding='utf-8-sig', index=False)

        sequence_seperated_order[config.columns.OPERATION_CODE] = sequence_seperated_order[config.columns.OPERATION_CODE].astype(str)
        # sequence_seperated_order에서 해당 gitem + proccode 노드 찾기
        matches = sequence_seperated_order[
            (sequence_seperated_order[config.columns.GITEM] == gitemno) &
            (sequence_seperated_order[config.columns.OPERATION_CODE] == proccode)
        ]

        if gitemno == '32409':
            # 컬럼 타입 확인
            print(sequence_seperated_order[config.columns.GITEM].dtype)
            print(sequence_seperated_order[config.columns.OPERATION_CODE].dtype)
            # 값 확인
            print(repr(sequence_seperated_order[config.columns.GITEM].iloc[0]))
            print(repr(sequence_seperated_order[config.columns.OPERATION_CODE].iloc[0]))
            print(repr(gitemno), repr(proccode))

            print(f'gitemno {gitemno}')
            print(f'proccode {proccode}')

            print(f'sequence_seperated_order: {sequence_seperated_order[sequence_seperated_order[config.columns.GITEM]==gitemno]}')
            print(f'sequence_seperated_order gitem + proccode \n {sequence_seperated_order[(sequence_seperated_order[config.columns.GITEM] == gitemno) & (sequence_seperated_order[config.columns.OPERATION_CODE] == proccode)]}')
            print("matches")
            print(matches)

        for _, match_row in matches.iterrows():
            parent_node_id = match_row[config.columns.ID]
            aging_node_id = f"{parent_node_id}_AGING"

            # 다음 노드 찾기 (같은 P/O NO, operation_order + 1)
            # ⚠️ WARNING: P/O NO 매칭 로직 주의사항
            # 1. P/O NO가 쉼표로 구분된 여러 개인 경우 (예: "PO001,PO002,PO003") 매칭 실패 가능
            #    → sequence_seperated_order에서 P/O NO가 이미 explode되어 분리된 상태여야 정상 작동
            # 2. 마지막 공정 이후 aging인 경우 next_node_id는 None으로 설정됨 (정상 동작)
            #    → aging_node의 CHILDREN이 빈 문자열로 처리됨
            next_op_order = match_row[config.columns.OPERATION_ORDER] + 1
            po_no = match_row[config.columns.PO_NO]

            next_node = sequence_seperated_order[
                (sequence_seperated_order[config.columns.PO_NO] == po_no) &
                (sequence_seperated_order[config.columns.OPERATION_ORDER] == next_op_order)
            ]

            next_node_id = next_node.iloc[0][config.columns.ID] if len(next_node) > 0 else None

            aging_map[parent_node_id] = {
                "aging_time": aging_time,
                "aging_node_id": aging_node_id,
                "next_node_id": next_node_id
            }

    print(f"[INFO] parse_aging_requirements: {len(aging_map)}개의 aging 노드 생성 예정")
    return aging_map


def shift_depths_after_aging(aging_node_id, aging_depth, df):
    """
    Aging 노드 삽입 후 후속 노드들의 depth를 +1 증가시켜 중복 방지

    Args:
        aging_node_id: 삽입된 Aging 노드 ID
        aging_depth: Aging 노드의 depth
        df: DAG DataFrame

    Returns:
        depth가 조정된 DataFrame

    예시:
        Before: A(d=1) → B(d=2) → C(d=3) → D(d=4)
        Insert Aging after B (depth=3)
        After:  A(d=1) → B(d=2) → Aging(d=3) → C(d=4) → D(d=5)
    """
    # 1. Aging 노드의 모든 후손(descendants) 찾기
    descendants = []
    queue = [aging_node_id]
    visited = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        # 현재 노드의 자식들 찾기 (CHILDREN 컬럼 사용)
        current_row = df[df['ID'] == current_id]
        if current_row.empty:
            continue

        children_str = current_row.iloc[0]['CHILDREN']
        if isinstance(children_str, str) and children_str.strip():
            children_list = [c.strip() for c in children_str.split(',') if c.strip()]

            for child_id in children_list:
                # 자식 노드의 depth 확인
                child_row = df[df['ID'] == child_id]
                if not child_row.empty:
                    child_depth = child_row.iloc[0]['DEPTH']

                    # Aging depth 이상인 후손들만 shift 대상
                    if child_depth >= aging_depth:
                        descendants.append(child_id)
                        queue.append(child_id)

    # 2. 후손 노드들의 depth +1 증가
    if descendants:
        print(f"[INFO] Depth Shift: Aging 노드 {aging_node_id}(d={aging_depth}) 삽입으로 인해 "
              f"{len(descendants)}개 후손 노드의 depth +1 증가")
        mask = df['ID'].isin(descendants)
        df.loc[mask, 'DEPTH'] = df.loc[mask, 'DEPTH'] + 1

    return df


def insert_aging_nodes_to_dag(dag_df, aging_map):
    """
    dag_df에 aging 노드 추가 및 부모-자식 관계 재설정

    Args:
        dag_df: DataFrame with columns [ID, DEPTH, CHILDREN]
        aging_map: parse_aging_requirements() 결과

    Returns:
        수정된 dag_df
    """
    new_rows = []

    print(f"[INFO] insert_aging_nodes_to_dag: {len(aging_map)}개의 aging 관계 처리 시작")

    # 1. 기존 노드의 CHILDREN 수정
    for idx, row in dag_df.iterrows():
        parent_node_id = row['ID']

        if parent_node_id in aging_map:
            aging_info = aging_map[parent_node_id]
            aging_node_id = aging_info['aging_node_id']
            next_node_id = aging_info['next_node_id']

            # CHILDREN 파싱
            children = row['CHILDREN']
            if isinstance(children, str):
                children_list = [c.strip() for c in children.split(',') if c.strip()]
            else:
                children_list = []

            # next_node_id 제거, aging_node_id 추가
            if next_node_id and next_node_id in children_list:
                children_list.remove(next_node_id)
            children_list.append(aging_node_id)

            dag_df.at[idx, 'CHILDREN'] = ', '.join(children_list)

            # 2. aging 노드 생성
            aging_depth = row['DEPTH'] + 1
            new_rows.append({
                'ID': aging_node_id,
                'DEPTH': aging_depth,
                'CHILDREN': next_node_id if next_node_id else '',
                '_parent_node_id': parent_node_id  # depth shift 시 필요
            })

    # 3. 새 노드 추가 및 Depth Shift
    if new_rows:
        # 각 Aging 노드 추가 후 즉시 depth shift 수행
        for aging_row in new_rows:
            aging_node_id = aging_row['ID']
            aging_depth = aging_row['DEPTH']

            # Aging 노드를 dag_df에 추가
            dag_df = pd.concat([dag_df, pd.DataFrame([aging_row])], ignore_index=True)

            # 후손 노드들의 depth shift
            dag_df = shift_depths_after_aging(
                aging_node_id=aging_node_id,
                aging_depth=aging_depth,
                df=dag_df
            )

        # 최종 정렬
        dag_df = dag_df.sort_values(['DEPTH', 'ID']).reset_index(drop=True)

        # 임시 컬럼 제거
        if '_parent_node_id' in dag_df.columns:
            dag_df = dag_df.drop(columns=['_parent_node_id'])

        print(f"[INFO] insert_aging_nodes_to_dag: {len(new_rows)}개의 aging 노드 추가 완료")
        print(f"[INFO] 최종 depth 범위: {dag_df['DEPTH'].min()}-{dag_df['DEPTH'].max()}")

    return dag_df