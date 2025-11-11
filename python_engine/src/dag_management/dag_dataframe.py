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

    aging_map = {}

    for _, row in aging_df.iterrows():
        gitemno = str(row[config.columns.GITEM])
        proccode = str(row[config.columns.OPERATION_CODE])  # aging 이전 공정
        aging_time = int(row[config.columns.AGING_TIME])

        sequence_seperated_order[config.columns.OPERATION_CODE] = sequence_seperated_order[config.columns.OPERATION_CODE].astype(str)
        # sequence_seperated_order에서 해당 gitem + proccode 노드 찾기
        matches = sequence_seperated_order[
            (sequence_seperated_order[config.columns.GITEM] == gitemno) &
            (sequence_seperated_order[config.columns.OPERATION_CODE] == proccode)
        ]

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


def normalize_depths_post_aging(dag_df):
    """
    ✅ FIX-3: 최종 안전장치 - 모든 aging 삽입 후 BFS로 depth 재정규화

    이 함수는 insert_aging_nodes_to_dag() 후에 호출되어
    모든 depth가 strict topological order를 따르도록 보장합니다.

    Args:
        dag_df: Aging 노드가 모두 삽입된 DAG DataFrame

    Returns:
        정규화된 dag_df (모든 depth가 unique하고 topological order 유지)

    예시:
        Before (중복 가능): 공정1(1) → 에이징1(3) → 공정3(4) → 에이징2(5) → 공정5(5)
        After (정규화):     공정1(1) → 에이징1(2) → 공정3(3) → 에이징2(4) → 공정5(5)
    """
    result_df = dag_df.copy()

    # 1. Source 노드 찾기 (parent가 없는 노드)
    source_nodes = []
    for idx, row in result_df.iterrows():
        node_id = row['ID']
        is_source = True

        # 다른 노드가 이 노드를 children으로 가지는지 확인
        for idx2, row2 in result_df.iterrows():
            children_str = row2['CHILDREN']
            if isinstance(children_str, str) and children_str.strip():
                children_list = [c.strip() for c in children_str.split(',') if c.strip()]
                if node_id in children_list:
                    is_source = False
                    break

        if is_source:
            source_nodes.append(node_id)

    if not source_nodes:
        print(f"[WARN] No source nodes found, returning original DataFrame")
        return result_df

    print(f"[INFO] Normalize Depths: Source 노드 {source_nodes}에서 BFS 시작")

    # 2. BFS로 각 노드의 depth를 재할당
    depth_map = {}  # {node_id: new_depth}
    queue = [(node_id, 1) for node_id in source_nodes]  # (node_id, depth)
    visited = set()

    while queue:
        current_id, current_depth = queue.pop(0)

        if current_id in visited:
            continue
        visited.add(current_id)

        # 기존 depth와 새 depth 비교 (max 사용 - 안전성)
        if current_id in depth_map:
            new_depth = max(depth_map[current_id], current_depth)
        else:
            new_depth = current_depth

        depth_map[current_id] = new_depth

        # 현재 노드의 자식 찾기
        current_row = result_df[result_df['ID'] == current_id]
        if not current_row.empty:
            children_str = current_row.iloc[0]['CHILDREN']
            if isinstance(children_str, str) and children_str.strip():
                children_list = [c.strip() for c in children_str.split(',') if c.strip()]

                for child_id in children_list:
                    if child_id not in visited:
                        queue.append((child_id, new_depth + 1))

    # 3. depth_map을 DataFrame에 적용
    for node_id, new_depth in depth_map.items():
        mask = result_df['ID'] == node_id
        old_depth = result_df.loc[mask, 'DEPTH'].values[0] if mask.any() else None
        result_df.loc[mask, 'DEPTH'] = new_depth

        if old_depth != new_depth:
            print(f"[INFO] Normalize: {node_id} depth {old_depth} → {new_depth}")

    # 4. 최종 정렬
    result_df = result_df.sort_values(['DEPTH', 'ID']).reset_index(drop=True)

    # 5. 검증: 모든 depth가 unique한지 확인
    unique_depths = result_df['DEPTH'].nunique()
    total_rows = len(result_df)

    if unique_depths == total_rows:
        print(f"[INFO] [OK] Depth 정규화 검증 완료: 모든 {total_rows}개 노드의 depth가 unique")
    else:
        print(f"[WARN] [NG] Depth 중복 여전히 존재: {total_rows}개 노드 중 {unique_depths}개만 unique")
        # 중복된 depth 출력
        duplicates = result_df[result_df.duplicated(subset=['DEPTH'], keep=False)]
        print(f"[WARN] 중복된 depth: {duplicates[['ID', 'DEPTH']].values.tolist()}")

    print(f"[INFO] Normalize 완료: depth 범위 {result_df['DEPTH'].min()}-{result_df['DEPTH'].max()}")

    return result_df


def shift_depths_after_aging(aging_node_id, aging_depth, df):
    """
    Aging 노드 삽입 후 후속 노드들의 depth를 +1 증가시켜 중복 방지

    FIX: 더 견고한 에러 처리 및 검증 추가

    Args:
        aging_node_id: 삽입된 Aging 노드 ID
        aging_depth: Aging 노드의 depth
        df: DAG DataFrame

    Returns:
        depth가 조정된 DataFrame

    예시:
        Before: 공정1(d=1) → 공정2(d=2) → 공정3(d=3) → 공정4(d=4)
        Insert Aging after 공정2 (depth=3)
        After:  공정1(d=1) → 공정2(d=2) → 에이징1(d=3) → 공정3(d=4) → 공정4(d=5)
    """
    # 0. 입력 검증
    if not isinstance(df, pd.DataFrame):
        print(f"[ERROR] df is not a DataFrame")
        return df

    if aging_node_id not in df['ID'].values:
        print(f"[WARN] Aging node {aging_node_id} not found in DataFrame, skipping shift")
        return df

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

                    # ✅ FIX: 더 명확한 조건
                    # Aging depth 이상인 후손들만 shift 대상
                    if child_depth >= aging_depth:
                        descendants.append(child_id)
                        queue.append(child_id)
                else:
                    print(f"[WARN] Child node {child_id} not found in DataFrame")

    # 2. 후손 노드들의 depth +1 증가
    if descendants:
        print(f"[INFO] Depth Shift: 에이징 노드 '{aging_node_id}'(d={aging_depth}) 삽입으로 인해 "
              f"{len(descendants)}개 후손 노드의 depth +1 증가")

        # ✅ FIX: 더 명확한 로깅
        mask = df['ID'].isin(descendants)
        before_depths = df.loc[mask, 'DEPTH'].copy()
        df.loc[mask, 'DEPTH'] = df.loc[mask, 'DEPTH'] + 1
        after_depths = df.loc[mask, 'DEPTH'].copy()

        # 검증: depth가 실제로 증가했는지 확인
        if (after_depths == before_depths + 1).all():
            print(f"[INFO] [OK] Depth shift 검증 완료: {list(zip(descendants, before_depths.values, after_depths.values))[:3]}...")
        else:
            print(f"[WARN] [NG] Depth shift 검증 실패")
    else:
        print(f"[INFO] Depth Shift: 에이징 노드 '{aging_node_id}'(d={aging_depth})의 후손 노드 없음 (마지막 공정)")

    return df


def insert_aging_nodes_to_dag(dag_df, aging_map):
    """
    dag_df에 aging 노드 추가 및 부모-자식 관계 재설정

    FIX: Sequential insertion으로 변경
    - 각 aging을 하나씩 처리하면서 최신 dag_df에서 parent depth 읽기
    - 각 aging 삽입 후 즉시 shift → 다음 aging에 반영

    Args:
        dag_df: DataFrame with columns [ID, DEPTH, CHILDREN]
        aging_map: parse_aging_requirements() 결과

    Returns:
        수정된 dag_df
    """
    if not aging_map:
        return dag_df

    print(f"[INFO] insert_aging_nodes_to_dag: {len(aging_map)}개의 aging 관계 처리 시작")

    result_df = dag_df.copy()
    aging_count = 0

    # ✅ FIX: aging_map의 parent_node_id를 순회 (원본이 아닌 현재 dag_df 기반)
    for parent_node_id in aging_map.keys():
        aging_info = aging_map[parent_node_id]
        aging_node_id = aging_info['aging_node_id']
        next_node_id = aging_info['next_node_id']

        # 1. 현재 dag_df에서 parent의 최신 depth 읽기 ✅ (KEY FIX)
        parent_row = result_df[result_df['ID'] == parent_node_id]
        if parent_row.empty:
            print(f"[WARN] Parent node {parent_node_id} not found in DAG, skipping")
            continue

        parent_depth = parent_row.iloc[0]['DEPTH']
        aging_depth = parent_depth + 1  # ← 최신 depth 사용!

        # 2. Parent의 CHILDREN 수정
        idx = parent_row.index[0]
        children = result_df.at[idx, 'CHILDREN']
        if isinstance(children, str):
            children_list = [c.strip() for c in children.split(',') if c.strip()]
        else:
            children_list = []

        # next_node_id 제거, aging_node_id 추가
        if next_node_id and next_node_id in children_list:
            children_list.remove(next_node_id)
        children_list.append(aging_node_id)
        result_df.at[idx, 'CHILDREN'] = ', '.join(children_list)

        # 3. Aging 노드 생성
        aging_row = {
            'ID': aging_node_id,
            'DEPTH': aging_depth,
            'CHILDREN': next_node_id if next_node_id else ''
        }

        # 4. Aging 노드를 dag_df에 추가
        result_df = pd.concat([result_df, pd.DataFrame([aging_row])], ignore_index=True)

        # 5. 즉시 shift 수행 (다음 aging에 반영됨!) ✅ (KEY FIX)
        result_df = shift_depths_after_aging(
            aging_node_id=aging_node_id,
            aging_depth=aging_depth,
            df=result_df
        )

        aging_count += 1
        print(f"[INFO] [{aging_count}/{len(aging_map)}] Aging 노드 '{aging_node_id}' (depth={aging_depth}) 삽입 및 shift 완료")

    # 6. 최종 정렬 및 정리
    result_df = result_df.sort_values(['DEPTH', 'ID']).reset_index(drop=True)

    print(f"[INFO] insert_aging_nodes_to_dag: {aging_count}개의 aging 노드 추가 완료")
    print(f"[INFO] 최종 depth 범위: {result_df['DEPTH'].min()}-{result_df['DEPTH'].max()}")
    print(f"[INFO] 최종 노드 개수: {len(result_df)} (원본: {len(dag_df)}, 추가: {aging_count})")

    # 7. ⚠️ normalize_depths_post_aging() 제거
    # shift_depths_after_aging()에서 이미 depth를 제대로 설정했으므로 추가 정규화는 불필요
    # normalize_depths_post_aging()는 source nodes 판별 로직 오류로 depth를 리셋하는 문제 발생

    return result_df