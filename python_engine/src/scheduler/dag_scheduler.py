# from collections import OrderedDict
# from .scheduling_core import SchedulingCore, ForcedMachineStrategy, OptimalMachineStrategy


# class DAGScheduler:
#     """
#     DAG 기반 스케줄링 로직을 담당하는 클래스
#     DAGGraphManager와 Scheduler를 조합하여 스케줄링 수행
#     """
    
#     def __init__(self, scheduler, dag_manager):
#         """
#         Args:
#             scheduler: 기계 자원 관리 담당 Scheduler 인스턴스
#             dag_manager: DAG 구조 관리 담당 DAGGraphManager 인스턴스
#         """
#         self.scheduler = scheduler
#         self.dag_manager = dag_manager
        
#     def schedule_minimize_setup(self, start_id, window):
#         """
#         유사한 공정들을 묶으면서 할당
#         start_id: 시작하는 id
#         window: window_size = 5일때 첫번째 공정단위 마감일로부터 5일간의 마감 데이터
#         """
    
#         node = self.dag_manager.nodes[start_id]
        
#         # 통합된 스케줄링 로직 사용 - 최적 기계 자동 선택
#         strategy = OptimalMachineStrategy()
#         success = SchedulingCore.schedule_single_node(node, self.scheduler, strategy)
        
#         if not success:
#             return
        
#         # 할당된 기계 인덱스 가져오기 (후속 작업에 필요)
#         ideal_machine_index = node.machine

#         # 첫번째 공정의 배합액과 공정명 추출 (셋업 시간 최소화를 위한 그룹화)
#         chemical_name = self.dag_manager.opnode_dict.get(start_id)[4]
#         operation_name = self.dag_manager.opnode_dict.get(start_id)[1]
        
#         same_chemical_queue = []
#         same_operation_queue = []
#         for gene in window:
#             if self.dag_manager.opnode_dict.get(gene)[4] == chemical_name: # 배합액이 동일한 경우
#                 same_chemical_queue.append(gene)
#             elif self.dag_manager.opnode_dict.get(gene)[1] == operation_name: # 배합액은 달라도 공정이 동일한 경우
#                 same_operation_queue.append(gene)

#         # 같은 배합액 내에서 너비 기준 내림차순 정렬
#         same_chemical_queue = sorted(
#             same_chemical_queue,
#             key=lambda gene: self.dag_manager.opnode_dict.get(gene)[3],
#             reverse=True
#         ) 

#         # 같은 공정 내에서 특정 배합액의 등장순서대로 배합액 기준 정렬
#         chemical_groups = OrderedDict()
#         for gene in same_operation_queue:
#             chemical_name = self.dag_manager.opnode_dict.get(gene)[4]  # 배합액 이름 추출
#             if chemical_name not in chemical_groups:   # 처음 등장한 배합액이면
#                 chemical_groups[chemical_name] = []
#             chemical_groups[chemical_name].append(gene)
        
#         # 등장순서대로 그룹을 합침. 이때 그룹 내에서는 너비 기준으로 
#         sorted_same_operation_queue = []
#         for group in chemical_groups.values():
#             group = sorted(group, key=lambda gene: self.dag_manager.opnode_dict.get(gene)[3], reverse=True)
#             sorted_same_operation_queue.extend(group)
        

#         used_ids = [start_id]
#         for queue in [same_chemical_queue, sorted_same_operation_queue]:
#             for same_chemical_id in queue:
#                 node = self.dag_manager.nodes[same_chemical_id]
#                 # 동일 기계에 강제 할당
#                 strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
#                 success = SchedulingCore.schedule_single_node(node, self.scheduler, strategy)
#                 if success: 
#                     used_ids.append(same_chemical_id)
                

#         # 이번에 window 내에서 사용한 것들을 반환해야함
#         return used_ids

#     def user_reschedule(self, machine_queues):
#         """
#         machine_queues: {machine_index: [node_id, ...]} 형태
#         - 각 리스트는 큐처럼 사용 (앞에서만 pop)
#         - 가능한 모든 노드를 한 번의 호출에서 처리
#         """
#         progress = True
#         while progress:
#             progress = False  # 이번 루프에서 실행이 있었는지 추적

#             for machine_idx, queue in machine_queues.items():
#                 if not queue:  # 큐가 비었으면 스킵
#                     continue

#                 node_id = queue[0]  # 큐 맨 앞
#                 node = self.dag_manager.nodes[node_id]
                
#                 # 통합된 스케줄링 로직 사용 - 재스케줄링 모드
#                 strategy = ForcedMachineStrategy(machine_idx, use_machine_window=True)
#                 success = SchedulingCore.schedule_single_node(node, self.scheduler, strategy)
                
#                 if success:
#                     # 큐에서 제거
#                     queue.pop(0)
#                     progress = True  # 실행이 있었음
                
#         # ===== while 문 탈출 후 통계 출력 =====
#         # 1. 각 큐의 남은 길이
#         queue_lengths = {mid: len(q) for mid, q in machine_queues.items()}

#         # 2. 길이들의 합
#         total_remaining = sum(queue_lengths.values())

#         # 3. 각 큐의 맨 앞 노드와 그 parent_node_count
#         queue_front_info = {}
#         for mid, q in machine_queues.items():
#             if q:  # 큐가 비어있지 않으면
#                 front_id = q[0]
#                 queue_front_info[mid] = {
#                     "node_id": front_id,
#                     "parent_node_count": getattr(self.dag_manager.nodes[front_id], "parent_node_count", None)
#                 }
#             else:
#                 queue_front_info[mid] = None

#         # 예시 출력
#         print("남은 큐 길이:", queue_lengths)
#         print("전체 남은 노드 수:", total_remaining)
#         print("각 큐의 맨 앞 노드 정보:", queue_front_info)