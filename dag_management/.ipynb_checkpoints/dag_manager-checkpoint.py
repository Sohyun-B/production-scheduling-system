import pandas as pd
import numpy as np
import ast
from collections import defaultdict, OrderedDict
import copy
import re
from .dag_dataframe import DAGNode

class DAGGraphManager:
    def __init__(self,opnode_dict):
        """ 
        
        """
        self.nodes = {}
        self.scheduler = None # GA용
        self.depth_groups = defaultdict(list)
        self.opnode_dict = opnode_dict
        self.max_length = 25000

    @staticmethod
    def parse_list(x):
        """리스트 형식 문자열 파싱 메소드

        Args:
            x (str): 파싱할 문자열 (예: "[a, b, c]")

        Returns:
            list: 파싱된 항목들의 리스트. 유효하지 않은 입력 시 빈 리스트 반환
        """
        if isinstance(x, list): # 
            # print(f"이미 리스트 형태")
            return x
        
        if pd.isna(x) or x.strip() in ['', '[]']:
            return []

        # 괄호 제거 및 문자열 정제
        cleaned = x.strip().lstrip('[').rstrip(']').replace("'", "").replace('"', '')
        if not cleaned:
            return []

        return [item.strip() for item in cleaned.split(',')]


    def build_from_dataframe(self, dag_df):
        # children이 리스트 형태가 아닌 경우 리스트 형태로 변환
        dag_df['CHILDREN'] = dag_df['CHILDREN'].apply(self.parse_list)
        # 노드 생성 (변경 없음)
        for idx, row in dag_df.iterrows():
            node = DAGNode(row['ID'], row['DEPTH'])
            self.nodes[row['ID']] = node

        # 관계 설정: CHILDREN 컬럼 기준
        for _, row in dag_df.iterrows():
            current = self.nodes[row['ID']]

            # CHILDREN 기반 연결
            for child_id in row['CHILDREN']:  # PARENT -> CHILDREN 변경
                # 핵심 수정 부분 시작
                if child_id not in self.nodes:  # 존재 여부 확인
                    continue  # 없는 경우 건너뜀
                child = self.nodes[child_id]

                # 자식 관계 설정
                if child not in current.children:
                    current.children.append(child)

                # 자식의 parent_node_count 증가
                child.parent_node_count += 1  # 직접 카운트 설정
                child.original_parent_count = child.parent_node_count 
        # 현제 초기화 상태의 노드 저장
        for node in self.nodes.values():
            node.save_initial_state()

        self._build_parents()
        self._build_all_descendants()

    def _build_parents(self):
        """
        ga의 crossover와 mutation의 위상정렬을 위해 부모노드 id 리스트 생성
        self.nodes의 모든 노드에 .parent_ids(혹은 .parents) 속성을 만들어줌.
        children 정보만을 활용해 한 번에 parent 정보를 구축.
        """
        for node in self.nodes.values():
            if not hasattr(node, 'parent_ids'):
                node.parent_ids = []
        for node in self.nodes.values():
            for child in node.children:
                if not hasattr(child, 'parent_ids'):
                    child.parent_ids = []
                child.parent_ids.append(node.id)

    
    def _build_all_descendants(self):
        """
        모든 노드에 all_descendants(set of node_id) 어트리뷰트를 추가합니다.
        all_descendants:
        """ 
        memo = {}

        def dfs(node):
            if node.id in memo:
                return memo[node.id]
            descendants = set()
            for child in getattr(node, 'children', []):
                descendants.add(child.id)
                descendants.update(dfs(child))
            memo[node.id] = descendants
            return descendants

        for node in self.nodes.values():
            node.all_descendants = dfs(node)


    def schedule_dfs(self, start_id, scheduler):
        """DFS 기반 스케줄링 수행"""
        stack = []
        visited = set()

        # start_node = self.nodes[start_id[1:6]+str(depth)]
        start_node = self.nodes[start_id]
        # 첫번째 공정이므로 이전 공정 존재 X
        start_node.earliest_start = 0

        if start_node.parent_node_count == 0:
            stack.append(start_node)
            
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)

            # 0. parent_node_count 체크
            if node.parent_node_count != 0:
                continue  # 조건 불충족 시 건너뜀

            node_id = node.id
            node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
            
            # 부모 노드의 개수
            parent_node_length = len(node.parent_node_end)     
            
            depth = node.depth

            ideal_machine_index, node_start, machine_processing_time= scheduler.assign_operation(node.earliest_start, node_id, depth, node.node_delay)

            node.machine = ideal_machine_index

            # 1. PROCESSING_TIME 값 설정
            node.processing_time = machine_processing_time

            # 2. NODE_START
            node.node_start = node_start

            # 3. NODE_END 계산
            node.node_end = node.node_start + node.processing_time

            # 자식 노드 처리 (부모 카운트 감소)
            for child in node.children:
                child.parent_node_count -= 1
                child.parent_node_end.append(node.node_end)
                if child.parent_node_count == 0:
                    stack.append(child)


    def to_dataframe(self):
        """모든 노드 정보를 데이터프레임으로 변환"""
        rows = []
        for node in self.nodes.values():
            row = {
                'id': node.id,
                'depth': node.depth,
                'children': [c.id for c in node.children],  # 자식 ID 리스트
                'parent_node_count': node.parent_node_count,
                'processing_time': node.processing_time,
                'node_start': node.node_start,
                'node_end': node.node_end,
                'parent_node_end': node.parent_node_end,  # 부모 종료 시간 리스트
                'earliest_start': node.earliest_start,
                'machine': node.machine,
            }
            rows.append(row)
        return pd.DataFrame(rows)


    
########################## GA용 추가 함수
    def allocate_scheduler(self, scheduler):
        """ GA를 위한 스케줄러 할당"""
        self.scheduler = scheduler

    def schedule_dfs_id(self, start_id, op3node=None):
        """
        스케줄링 할당. 첫번째 노드를 넣으면 전부 실행시키는 것이 아니라 해당 노드만 할당함.
        op3node: op3node가 쪼개지는 경우 해당 op3node중 이번에 사용된 일부에 대한 데이터만을 가져온다.
        
        """
    
        node = self.nodes[start_id]
        # 0. parent_node_count 체크
        if node.depth != 3 and node.parent_node_count != 0:
            return
    
        node_id = node.id
        node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
        
        # 부모 노드의 개수
        parent_node_length = len(node.parent_node_end)     
        
        depth = node.depth
    
        ideal_machine_index, node_start, machine_processing_time= self.scheduler.assign_operation(node.earliest_start, node_id, depth, op3node)
    
        node.machine = ideal_machine_index
    
        # 1. PROCESSING_TIME 값 설정
        node.processing_time = machine_processing_time
    
        # 2. NODE_START
        node.node_start = node_start
    
        # 3. NODE_END 계산
        node.node_end = node.node_start + node.processing_time
    
        # 자식 노드 처리 (부모 카운트 감소)
        for child in node.children:
            child.parent_node_count -= 1
            child.parent_node_end.append(node.node_end)
            """
            # 자식의 depth가 3일 때만 middlegroup으로 나눈다고 봐서 만든 코드. 이제 순서와 middlegroup이 언제나 일치하는 것이 아니기에 코드 수정 필요
            if child.depth == 3:
                # 자식 노드 확인
                
                op3node = self._check_middlegroup_operation(child, node.id)
                if op3node: # 3공정의 부분이 실행됨. 
                    self.schedule_dfs_id(child.id, op3node)
            """
            
    def reset_all_nodes(self):
        """GA를 위한 노드 초기화"""
        for node in self.nodes.values():
            node.restore_initial_state()

# =====================================

    def schedule_minimize_setup(self, start_id, window):
        """
        유사한 공정들을 묶으면서 할당
        start_id: 시작하는 id
        window: window_size = 5일때 첫번째 공정단위 마감일로부터 5일간의 마감 데이터
        """
    
        node = self.nodes[start_id]
        # 0. parent_node_count 체크
        if node.parent_node_count != 0:
            return
    
        node_id = node.id
        node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
        
        # 부모 노드의 개수
        parent_node_length = len(node.parent_node_end) 
        
        depth = node.depth
    
        ideal_machine_index, node_start, machine_processing_time = self.scheduler.assign_operation(node.earliest_start, node_id, depth)

    
        node.machine = ideal_machine_index
    
        # 1. PROCESSING_TIME 값 설정
        node.processing_time = machine_processing_time
    
        # 2. NODE_START
        node.node_start = node_start
    
        # 3. NODE_END 계산
        node.node_end = node.node_start + node.processing_time
    
        # 자식 노드 처리 (부모 카운트 감소)
        for child in node.children:
            child.parent_node_count -= 1
            child.parent_node_end.append(node.node_end)

        # 첫번째 공정이 사용하는 배합액과, 공정명, 원단너비
        mixture_name = self.opnode_dict.get(start_id)[4]
        operation_name = self.opnode_dict.get(start_id)[1]
        width = self.opnode_dict.get(start_id)[3] # 원단너비
        
        
        same_mixture_queue = []
        same_operation_queue = []
        for gene in window:
            if self.opnode_dict.get(gene)[4] == mixture_name: # 배합액이 동일한 경우
                same_mixture_queue.append(gene)
            elif self.opnode_dict.get(gene)[1] == operation_name: # 배합액은 달라도 공정이 동일한 경우
                same_operation_queue.append(gene)
        # print(f"배합액 이름: {mixture_name}")
        # print(f"공정 이름: {operation_name}")
        # print(f"window내 배합액 같은 경우: {same_mixture_queue}")
        # print(f"window내 공정이 같은 경우: {same_operation_queue}")

        # 같은 배합액 내에서 너비 기준 내림차순 정렬
        same_mixture_queue = sorted(
            same_mixture_queue,
            key=lambda gene: self.opnode_dict.get(gene)[3],
            reverse=True
        ) 

        # 같은 공정 내에서 특정 배합액의 등장순서대로 배합액 기준 정렬
        mixture_groups = OrderedDict()
        for gene in same_operation_queue:
            mixture_name = self.opnode_dict.get(gene)[4]  # 배합액 이름 추출
            if mixture_name not in mixture_groups:   # 처음 등장한 배합액이면
                mixture_groups[mixture_name] = []
            mixture_groups[mixture_name].append(gene)
        
        # 등장순서대로 그룹을 합침. 이때 그룹 내에서는 너비 기준으로 
        sorted_same_operation_queue = []
        for group in mixture_groups.values():
            group = sorted(group, key=lambda gene: self.opnode_dict.get(gene)[3], reverse=True)
            sorted_same_operation_queue.extend(group)
        
        # print(f"등장순 등장 배합액별 정렬: {sorted_same_operation_queue}")

        used_ids = [start_id]
        for queue in [same_mixture_queue, sorted_same_operation_queue]:
            for same_mixture_id in queue:
                # 확인용
                used_id = self.schedule_operation(same_mixture_id, ideal_machine_index)
                if used_id: used_ids.append(used_id)
                

        # 이번에 window 내에서 사용한 것들을 반환해야함
        return used_ids

    def schedule_operation(self, start_id, machine_idx):
        """
        앞에 수행된 공정과 배합액 혹은 공정이 동일한 공정을 해당 공정과 동일한 기계에 강제 배치해서 수행 후 수행된 node_id 리턴
        이때 해당 공정이 현재 parent_node_count가 0이 아니어서 수행 불가능하거나, 할당된 기계에서 해당 공정이 수행 불가능한 경우 제외
        """
        node = self.nodes[start_id]
        # 0. parent_node_count 체크
        if node.parent_node_count != 0:
            # print("dag.schedule_operation에서 parent_node_count가 0이 아닌게 들어옴")
            return 
    
        node_id = node.id
        node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
        
        # 부모 노드의 개수
        parent_node_length = len(node.parent_node_end) 
        
        depth = node.depth
        
        # flag: 만약 강제로 할당한 기계가 해당 공정을 수행하지 못하는 기계라면 flag == False
        flag, node_start, machine_processing_time = self.scheduler.force_assign_operation(machine_idx, node.earliest_start, node_id, depth)

        #

        if flag: 
            node.machine = machine_idx
        
            # 1. PROCESSING_TIME 값 설정
            node.processing_time = machine_processing_time
        
            # 2. NODE_START
            node.node_start = node_start
        
            # 3. NODE_END 계산
            node.node_end = node.node_start + node.processing_time
    
            # 자식 노드 처리 (부모 카운트 감소)
            for child in node.children:
                child.parent_node_count -= 1
                child.parent_node_end.append(node.node_end)

            return node_id
        else: # 공정이 강제로 할당된 기계에서 실행할 수 없는 경우
            return 
            