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
        # self.scheduler = None # GA용
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
        for idx, row in dag_df.iterrows():
            node = DAGNode(row['ID'], row['DEPTH'])
            node_id = row['ID']
            if node_id in self.opnode_dict:
                node_info = self.opnode_dict[node_id]
                # aging_time = node_info.get('AGING_TIME', 0) if isinstance(node_info, dict) else 0
                # node.aging_time = aging_time if aging_time is not None else 0
            else:
                # opnode_dict에 없는 노드는 aging_time을 0으로 유지
                pass
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
        # 현제 초기화 상태의 노드 저장
        for node in self.nodes.values():
            node.save_initial_state()

        self._build_parents()
        self._build_all_descendants()

    def _build_parents(self):
        """
        부모-자식 관계 검증 및 추가 그래프 분석용 정보 구축
        """
        # 현재는 _build_all_descendants()만 필요하므로 빈 메서드로 유지
        pass

    
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


#     def schedule_dfs(self, start_id, scheduler):
#         """DFS 기반 스케줄링 수행"""
#         stack = []
#         visited = set()

#         # start_node = self.nodes[start_id[1:6]+str(depth)]
#         start_node = self.nodes[start_id]
#         # 첫번째 공정이므로 이전 공정 존재 X
#         start_node.earliest_start = 0

#         if start_node.parent_node_count == 0:
#             stack.append(start_node)
            
#         while stack:
#             node = stack.pop()
#             if node in visited:
#                 continue
#             visited.add(node)

#             # 0. parent_node_count 체크
#             if node.parent_node_count != 0:
#                 continue  # 조건 불충족 시 건너뜀

#             node_id = node.id
#             node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
            
#             # 부모 노드의 개수
#             parent_node_length = len(node.parent_node_end)     
            
#             depth = node.depth

#             ideal_machine_index, node_start, machine_processing_time = assign_operation(node.earliest_start, node_id, depth, node.node_delay)

#             node.machine = ideal_machine_index

#             # 1. PROCESSING_TIME 값 설정
#             node.processing_time = machine_processing_time

#             # 2. NODE_START
#             node.node_start = node_start

#             # 3. NODE_END 계산
#             node.node_end = node.node_start + node.processing_time

#             # 자식 노드 처리 (부모 카운트 감소)
#             for child in node.children:
#                 child.parent_node_count -= 1
#                 child.parent_node_end.append(node.node_end)
#                 if child.parent_node_count == 0:
#                     stack.append(child)


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
    # def allocate_scheduler(self, scheduler):
    #     """ GA를 위한 스케줄러 할당"""
    #     self.scheduler = scheduler

    # def schedule_dfs_id(self, start_id, op3node=None):
    #     """
    #     스케줄링 할당. 첫번째 노드를 넣으면 전부 실행시키는 것이 아니라 해당 노드만 할당함.
    #     op3node: op3node가 쪼개지는 경우 해당 op3node중 이번에 사용된 일부에 대한 데이터만을 가져온다.
        
    #     """
    
    #     node = self.nodes[start_id]
    #     # 0. parent_node_count 체크
    #     if node.depth != 3 and node.parent_node_count != 0:
    #         return
    
    #     node_id = node.id
    #     node.earliest_start = max(node.parent_node_end) # 부모 노드의 가장 늦게 끝나는 시간
        
    #     # 부모 노드의 개수
    #     parent_node_length = len(node.parent_node_end)     
        
    #     depth = node.depth
    
    #     ideal_machine_index, node_start, machine_processing_time= self.scheduler.assign_operation(node.earliest_start, node_id, depth, op3node)
    
    #     node.machine = ideal_machine_index
    
    #     # 1. PROCESSING_TIME 값 설정
    #     node.processing_time = machine_processing_time
    
    #     # 2. NODE_START
    #     node.node_start = node_start
    
    #     # 3. NODE_END 계산
    #     node.node_end = node.node_start + node.processing_time
    
    #     # 자식 노드 처리 (부모 카운트 감소)
    #     for child in node.children:
    #         child.parent_node_count -= 1
    #         child.parent_node_end.append(node.node_end)
    #         """
    #         # 자식의 depth가 3일 때만 middlegroup으로 나눈다고 봐서 만든 코드. 이제 순서와 middlegroup이 언제나 일치하는 것이 아니기에 코드 수정 필요
    #         if child.depth == 3:
    #             # 자식 노드 확인
                
    #             op3node = self._check_middlegroup_operation(child, node.id)
    #             if op3node: # 3공정의 부분이 실행됨. 
    #                 self.schedule_dfs_id(child.id, op3node)
    #         """
            
    # def reset_all_nodes(self):
    #     """GA를 위한 노드 초기화"""
    #     for node in self.nodes.values():
    #         node.restore_initial_state()

# =====================================


            
            
            
            
