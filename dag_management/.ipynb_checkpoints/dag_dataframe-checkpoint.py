import pandas as pd
import numpy as np
import ast
from collections import defaultdict, OrderedDict
import copy
import re

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
    def __init__(self, node_id, depth):
        self.id = node_id
        self.depth = depth
        self.children = []

        # 초기화 필드 추가
        self.earliest_start = None  #
        self.parent_node_count = 0  # 부모 개수로 설정 예정
        self.processing_time = None
        self.machine = None
        self.node_start = None
        self.node_end = None
        self.parent_node_end = [0]  # 자식 노드의 PARENT_NODE_END
        self.parent_ids = [] # ga의 mutation, crossover의 위상정렬을 위해 부모 id 필요
        
        self.original_parent_count = 0

        self.all_descendants = [] # 직접 연결된 children 포함 자신보다 뒤에 와야하는 전체의 후손 노드들


    def save_initial_state(self):
        # 현재 상태를 깊은 복사로 저장
        self._initial_state = {
            'earliest_start': self.earliest_start,
            'parent_node_count': self.parent_node_count,
            'processing_time': self.processing_time,
            'machine': self.machine,
            'node_start': self.node_start,
            'node_end': self.node_end,
            'parent_node_end': copy.deepcopy(self.parent_node_end),
        }

    def restore_initial_state(self):
        # 저장된 초기 상태로 복원
        if hasattr(self, '_initial_state'):
            state = self._initial_state
            self.earliest_start = state['earliest_start']
            self.parent_node_count = state['parent_node_count']
            self.processing_time = state['processing_time']
            self.machine = state['machine']
            self.node_start = state['node_start']
            self.node_end = state['node_end']
            self.parent_node_end = copy.deepcopy(state['parent_node_end'])


def make_process_table(df):
    """
    각 P/O NO에 대해 해당 주문의 경로 만들기
    """
    # 1. 'P/O NO' 쉼표로 분리 후 행 폭발
    df = df.copy()
    df['P/O NO'] = df['P/O NO'].str.split(',')
    df_exploded = df.explode('P/O NO').reset_index(drop=True)
    df_exploded['P/O NO'] = df_exploded['P/O NO'].str.strip()  # 공백 제거

    # 2. 공정순서별로 'n공정' 컬럼명 생성
    df_exploded['공정컬럼'] = df_exploded['공정순서'].astype(str) + '공정ID'

    # 3. 피벗: P/O NO, GITEM별로 공정순서별 공정명을 컬럼으로
    pivot_df = df_exploded.pivot_table(
        index=['P/O NO'],
        columns='공정컬럼',
        values='ID',
        aggfunc='first'
    ).reset_index()

    # 4. 컬럼명 정리 (MultiIndex 해제)
    pivot_df.columns.name = None

    return pivot_df