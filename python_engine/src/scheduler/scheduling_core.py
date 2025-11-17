"""
통합 스케줄링 핵심 로직

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from collections import OrderedDict
import numpy as np
import pandas as pd
from config import config


@dataclass
class AssignmentResult:
    """기계 할당 결과"""
    success: bool                    # 할당 성공 여부
    machine_index: Optional[int]     # 할당된 기계 인덱스
    start_time: Optional[float]      # 시작 시간
    processing_time: Optional[float] # 처리 시간
    
    @property
    def end_time(self) -> Optional[float]:
        """종료 시간 자동 계산"""
        if self.start_time is not None and self.processing_time is not None:
            return self.start_time + self.processing_time
        return None


class SchedulingCore:
    """핵심 스케줄링 로직 통합 클래스"""
    
    @staticmethod
    def validate_ready_node(node) -> bool:
        """
        선행 작업 완료 확인
        
        Args:
            node: DAGNode 인스턴스
            
        Returns:
            bool: 스케줄링 실행 가능 여부 (parent_node_count == 0)
        """
        return node.parent_node_count == 0
    
    @staticmethod  
    def calculate_start_time(node) -> float:
        """
        최조 시작 가능 시간 계산
        
        Args:
            node: DAGNode 인스턴스
            
        Returns:
            float: 최조 시작 가능 시간 (부모 노드들의 최대 종료 시간)
        """
        # 어트리뷰트나 값이 존재하지 않으면 0(바로 시작 가능)
        if not hasattr(node, 'parent_node_end') or not node.parent_node_end:
            return 0.0
        
        # None 값 필터링
        valid_end_times = [t for t in node.parent_node_end if t is not None]
        if not valid_end_times:
            return 0.0
        
        # 부모 노드들의 최대 종료 시간
        base_earliest_start = max(valid_end_times)
        
        # # aging_time이 0보다 크면 추가 (0이면 대기 시간 없음)
        # if hasattr(node, 'aging_time') and node.aging_time > 0:
        #     return base_earliest_start + node.aging_time
        
        return base_earliest_start
    
    @staticmethod
    def update_node_state(node, machine_index: int, start_time: float, processing_time: float):
        """
        노드 스케줄링 상태 업데이트
        
        Args:
            node: DAGNode 인스턴스
            machine_index: 할당된 기계 인덱스
            start_time: 시작 시간
            processing_time: 처리 시간
        """
        node.machine = machine_index
        node.node_start = start_time
        node.processing_time = processing_time
        node.node_end = start_time + processing_time
    
    @staticmethod
    def update_dependencies(node):
        """
        후속 작업 의존성 업데이트

        Args:
            node: 완료된 DAGNode 인스턴스
        """
        for child in node.children:
            child.parent_node_count -= 1
            child.parent_node_end.append(node.node_end)

    @staticmethod
    def schedule_ready_aging_children(node, scheduler):
        """
        완료된 노드의 자식 중 스케줄 가능한 Aging 노드를 자동 스케줄링

        책임: Aging 노드 자동 스케줄링
        호출 시점: schedule_single_node()에서 의존성 업데이트 직후

        Args:
            node: 완료된 DAGNode 인스턴스
            scheduler: Scheduler 인스턴스
        """
        for child in node.children:
            if child.parent_node_count == 0:  # 스케줄 가능
                machine_info = scheduler.machine_dict.get(child.id)
                is_aging = machine_info and set(machine_info.keys()) == {-1}

                if is_aging:
                    print(f"[INFO] Aging 노드 {child.id} 자동 스케줄링 (parent {node.id} 완료)")
                    SchedulingCore.schedule_single_node(
                        child,
                        scheduler,
                        AgingMachineStrategy()
                    )

    @staticmethod
    def schedule_single_node(node, scheduler, machine_assignment_strategy) -> bool:
        """
        단일 노드 완전 스케줄링 - 모든 패턴 통합

        Args:
            node: 스케줄링할 DAGNode 인스턴스
            scheduler: Scheduler 인스턴스
            machine_assignment_strategy: 기계 할당 전략

        Returns:
            bool: 스케줄링 성공 여부
        """
        try:
            # 1. 선행 작업 완료 검증
            if not SchedulingCore.validate_ready_node(node):
                return False

            # 2. 최초 시작 가능 시간 계산
            earliest_start = SchedulingCore.calculate_start_time(node)
            node.earliest_start = earliest_start

            # NEW: 3. Aging 노드 감지 및 전략 선택
            machine_info = scheduler.machine_dict.get(node.id)
            is_aging = machine_info and set(machine_info.keys()) == {-1}

            if is_aging:
                # Aging 노드는 AgingMachineStrategy 사용
                strategy = AgingMachineStrategy()
                assignment_result = strategy.assign(scheduler, node, earliest_start)
            else:
                # 일반 노드는 전달받은 전략 사용
                assignment_result = machine_assignment_strategy.assign(
                    scheduler, node, earliest_start
                )

            if not assignment_result.success:
                return False

            # 4. 노드 상태 업데이트
            SchedulingCore.update_node_state(
                node,
                assignment_result.machine_index,
                assignment_result.start_time,
                assignment_result.processing_time
            )

            # 5. 후속 작업 의존성 업데이트
            SchedulingCore.update_dependencies(node)

            # 6. Aging 자식 노드 자동 스케줄링
            SchedulingCore.schedule_ready_aging_children(node, scheduler)

            return True

        except Exception as e:
            print(f"Error in schedule_single_node for node {getattr(node, 'id', 'unknown')}: {e}")
            return False


class MachineAssignmentStrategy(ABC):
    """기계 할당 전략 추상 클래스"""
    
    @abstractmethod
    def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
        """
        기계 할당 실행
        
        Args:
            scheduler: Scheduler 인스턴스
            node: 할당할 DAGNode 인스턴스
            earliest_start: 최초 시작 가능 시간
            
        Returns:
            AssignmentResult: 할당 결과
        """
        pass


class OptimalMachineStrategy(MachineAssignmentStrategy):
    """최적 기계 자동 선택 전략"""

    def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
        """
        스케줄러가 최적 기계를 자동 선택하여 할당

        기존 코드: scheduler.assign_operation(earliest_start, node_id, depth)
        """
        try:
            machine_idx, start_time, processing_time = scheduler.assign_operation(
                earliest_start, node.id, node.depth
            )
            return AssignmentResult(
                success=True,
                machine_index=machine_idx,
                start_time=start_time,
                processing_time=processing_time
            )
        except Exception as e:
            return AssignmentResult(
                success=False,
                machine_index=None,
                start_time=None,
                processing_time=None
            )


class AgingMachineStrategy(MachineAssignmentStrategy):
    """Aging 전용 기계 할당 전략 (NEW)"""

    def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
        """
        Aging 노드를 aging_machine에 즉시 할당

        Args:
            scheduler: Scheduler 인스턴스
            node: Aging DAGNode 인스턴스
            earliest_start: 최초 시작 가능 시간

        Returns:
            AssignmentResult: 할당 결과 (machine_index=-1)
        """
        try:
            machine_info = scheduler.machine_dict.get(node.id)

            # Aging 노드 검증
            if not machine_info or set(machine_info.keys()) != {-1}:
                raise ValueError(f"Node {node.id} is not an aging node")

            processing_time = machine_info[-1]
            start_time = earliest_start  # 즉시 시작

            # Aging 기계에 할당
            scheduler.aging_machine._Input(
                node.depth,
                node.id,
                start_time,
                processing_time
            )

            return AssignmentResult(
                success=True,
                machine_index=-1,
                start_time=start_time,
                processing_time=processing_time
            )
        except Exception as e:
            print(f"[ERROR] AgingMachineStrategy.assign for node {node.id}: {e}")
            return AssignmentResult(
                success=False,
                machine_index=None,
                start_time=None,
                processing_time=None
            )


# ========================================================================================
# Level 4: High-Level Scheduling Strategies
# ========================================================================================

class HighLevelSchedulingStrategy(ABC):
    """최상위 스케줄링 전략 추상 클래스"""
    
    @abstractmethod
    def execute(self, dag_manager, scheduler, **kwargs):
        """전략 실행
        
        Args:
            dag_manager: DAG 구조 관리자
            scheduler: 기계 자원 관리자
            **kwargs: 전략별 추가 파라미터
            
        Returns:
            전략에 따른 결과 (리스트, DataFrame 등)
        """
        pass


def find_best_chemical(first_node_dict, window_nodes, dag_manager):
    """
    첫 노드의 CHEMICAL_LIST에서 최적 배합액 선택

    Args:
        first_node_dict: 첫 노드의 opnode_dict 정보
        window_nodes: 윈도우 내 노드 ID 리스트
        dag_manager: DAG 관리자

    Returns:
        str or None: 가장 많이 사용 가능한 배합액 (없으면 None)

    로직:
        1. 첫 노드의 CHEMICAL_LIST 확인
        2. 각 배합액에 대해 윈도우 내 사용 가능한 노드 수 카운트
        3. 가장 많이 사용 가능한 배합액 반환
    """
    chemical_list = first_node_dict["CHEMICAL_LIST"]

    # 배합액이 없는 경우
    if not chemical_list or chemical_list == ():
        return None

    # 각 배합액별 사용 가능한 노드 수 카운트
    chemical_counts = {}
    for chemical in chemical_list:
        count = 0
        for node_id in window_nodes:
            node_dict = dag_manager.opnode_dict.get(node_id)
            # NEW: Aging 노드는 opnode_dict에 없으므로 자동 제외됨 (추가 체크)
            if node_dict and chemical in node_dict["CHEMICAL_LIST"]:
                count += 1
        chemical_counts[chemical] = count

    # 가장 많이 사용 가능한 배합액 반환 (동수일 경우 첫 번째)
    if not chemical_counts:
        return None

    best_chemical = max(chemical_counts, key=chemical_counts.get)
    return best_chemical


class SetupMinimizedStrategy(HighLevelSchedulingStrategy):
    """셋업 시간 최소화 전략 (dag_scheduler.schedule_minimize_setup 통합)"""

    def execute(self, dag_manager, scheduler, start_id, window):
        """
        유사한 공정들을 묶어서 셋업 시간 최소화 스케줄링
        
        Args:
            start_id: 시작 노드 ID
            window: 윈도우 내 후보 노드 ID 리스트
            
        Returns:
            list: 이번에 사용된 노드 ID 리스트
        """
        node = dag_manager.nodes[start_id]

        # 1. 첫 번째 노드는 최적 기계 자동 선택
        strategy = OptimalMachineStrategy()
        success = SchedulingCore.schedule_single_node(node, scheduler, strategy)

        if not success:
            return []

        # 할당된 기계 인덱스 가져오기
        ideal_machine_index = node.machine

        # 2. 첫 노드의 최적 배합액 선택
        first_node_dict = dag_manager.opnode_dict.get(start_id)
        operation_name = first_node_dict["OPERATION_CODE"]

        # NEW: 윈도우 내 같은 공정 노드들만 추출 (ready 필터 + aging 제외)
        same_operation_nodes = [
            gene for gene in window
            if dag_manager.opnode_dict.get(gene)  # Aging 노드는 opnode_dict에 없으므로 제외됨
            and dag_manager.opnode_dict.get(gene)["OPERATION_CODE"] == operation_name
            and SchedulingCore.validate_ready_node(dag_manager.nodes[gene])
        ]

        # 첫 노드의 최적 배합액 결정
        best_chemical = find_best_chemical(first_node_dict, same_operation_nodes, dag_manager)
        dag_manager.opnode_dict[start_id]["SELECTED_CHEMICAL"] = best_chemical

        # 3. 같은 배합액 사용 가능한 노드들 그룹화
        same_chemical_queue = []
        remaining_operation_queue = []

        for gene in same_operation_nodes:
            gene_dict = dag_manager.opnode_dict.get(gene)
            if (best_chemical
                and best_chemical in gene_dict["CHEMICAL_LIST"]
                and SchedulingCore.validate_ready_node(dag_manager.nodes[gene])):
                same_chemical_queue.append(gene)
            else:
                remaining_operation_queue.append(gene)

        # 4. 같은 배합액 그룹 너비 정렬 및 SELECTED_CHEMICAL 설정
        same_chemical_queue = sorted(
            same_chemical_queue,
            key=lambda gene: dag_manager.opnode_dict.get(gene)["FABRIC_WIDTH"],
            reverse=True
        )

        for gene in same_chemical_queue:
            dag_manager.opnode_dict[gene]["SELECTED_CHEMICAL"] = best_chemical

        # 5. 같은 배합액 그룹 스케줄링
        print(
            "[LOG] SetupMinimizedStrategy: same_operation=", len(same_operation_nodes),
            " same_chemical=", len(same_chemical_queue),
            " remaining_op=", len(remaining_operation_queue)
        )
        used_ids = [start_id]
        for same_chemical_id in same_chemical_queue:
            node = dag_manager.nodes[same_chemical_id]
            strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
            success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
            if success:
                used_ids.append(same_chemical_id)
            else:
                # 스케줄링 실패 시 remaining으로 이동
                remaining_operation_queue.append(same_chemical_id)

        # 6. 남은 노드들을 배합액별로 반복 처리
        iter_count = 0
        while remaining_operation_queue:
            iter_count += 1
            if iter_count > 50:
                print("[LOG][WARN] SetupMinimizedStrategy: iteration cap reached (50); breaking loop")
                break
            # 매 반복마다 ready가 아닌 노드는 제거
            remaining_operation_queue = [
                g for g in remaining_operation_queue
                if SchedulingCore.validate_ready_node(dag_manager.nodes[g])
            ]
            if not remaining_operation_queue:
                break
            # 6-1. 남은 노드 중 첫 번째를 리더로 선정
            leader_id = remaining_operation_queue[0]
            leader_dict = dag_manager.opnode_dict.get(leader_id)

            # 6-2. 리더의 최적 배합액 선택
            leader_best_chemical = find_best_chemical(leader_dict, remaining_operation_queue, dag_manager)
            dag_manager.opnode_dict[leader_id]["SELECTED_CHEMICAL"] = leader_best_chemical

            # 6-3. 같은 배합액 사용 가능한 노드들 그룹화
            current_chemical_group = [leader_id]
            next_remaining = []

            for gene in remaining_operation_queue[1:]:
                gene_dict = dag_manager.opnode_dict.get(gene)
                if (leader_best_chemical
                    and leader_best_chemical in gene_dict["CHEMICAL_LIST"]
                    and SchedulingCore.validate_ready_node(dag_manager.nodes[gene])):
                    current_chemical_group.append(gene)
                    dag_manager.opnode_dict[gene]["SELECTED_CHEMICAL"] = leader_best_chemical
                else:
                    next_remaining.append(gene)

            # 6-4. 현재 그룹 너비 정렬
            current_chemical_group = sorted(
                current_chemical_group,
                key=lambda gene: dag_manager.opnode_dict.get(gene)["FABRIC_WIDTH"],
                reverse=True
            )

            # 6-5. 현재 그룹 스케줄링
            leader_parent_cnt = getattr(dag_manager.nodes[leader_id], "parent_node_count", None)
            print(
                "[LOG] SetupMinimizedStrategy: loop leader=", leader_id,
                " parent_node_count=", leader_parent_cnt,
                " best_chemical=", leader_best_chemical,
                " group_size=", len(current_chemical_group)
            )
            for chemical_id in current_chemical_group:
                node = dag_manager.nodes[chemical_id]
                # 안전망: 직전 단계에서 ready였어도 바로 전 노드 스케줄링으로 상태가 변할 수 있음
                if not SchedulingCore.validate_ready_node(node):
                    next_remaining.append(chemical_id)
                    continue
                strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
                success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
                if success:
                    used_ids.append(chemical_id)
                else:
                    # 스케줄링 실패 시 next_remaining에 추가
                    next_remaining.append(chemical_id)

            # 6-6. 다음 반복을 위해 remaining 업데이트
            if len(next_remaining) == len(remaining_operation_queue):
                print("[LOG][WARN] SetupMinimizedStrategy: no progress in iteration; remaining=", len(remaining_operation_queue))
                # 진행 없음이면 상위로 반환하여 상태 전환 기회를 제공
                break
            remaining_operation_queue = next_remaining

        return used_ids


class DispatchPriorityStrategy(HighLevelSchedulingStrategy):
    """우선순위 디스패치 전략 (dispatch_rules.allocating_schedule_by_dispatching_priority 통합)"""
    
    def execute(self, dag_manager, scheduler, dag_df=None, priority_order=None, window_days=5, **kwargs):
        """
        우선순위 순서대로 윈도우를 만들어 스케줄링 실행
        
        Args:
            dag_manager: DAG 구조 관리자  
            scheduler: 준비된 Scheduler 인스턴스 (필수)
            dag_df: DAG 데이터프레임
            priority_order: 우선순위 정렬된 작업 순서 리스트 (None이면 내부에서 생성)
            window_days: 윈도우 크기 (일 단위)
            **kwargs: 추가 파라미터들
            
        Returns:
            DataFrame: 최종 스케줄링 결과
        """
        # 필요한 경우에만 파라미터 추출
        sequence_seperated_order = kwargs.get('sequence_seperated_order')
        
        # 디스패치 룰 생성 (priority_order가 없으면 생성)
        if priority_order is None:
            from .dispatch_rules import create_dispatch_rule
            if sequence_seperated_order is None:
                raise ValueError("priority_order가 None인 경우 sequence_seperated_order가 필요합니다")
            priority_order, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)

        # Aging 노드 필터링 (Aging은 parent 완료 시 자동 스케줄링됨)
        filtered_priority = []
        aging_nodes = []
        for node_id in priority_order:
            machine_info = scheduler.machine_dict.get(node_id)
            is_aging = machine_info and set(machine_info.keys()) == {-1}
            if is_aging:
                aging_nodes.append(node_id)
            else:
                filtered_priority.append(node_id)

        print(f"[INFO] Priority order: 전체 {len(priority_order)}개 노드 중 일반 {len(filtered_priority)}개, Aging {len(aging_nodes)}개")
        priority_order = filtered_priority  # 일반 노드만 처리

        # priority_order와 납기일을 결합
        # DUE_DATE 컬럼이 없으면 sequence_seperated_order에서 가져오기
        if config.columns.DUE_DATE not in dag_df.columns:
            # sequence_seperated_order에서 ID별 납기일 매핑 생성
            sequence_seperated_order = kwargs.get('sequence_seperated_order', pd.DataFrame())
            if sequence_seperated_order.empty or config.columns.PROCESS_ID not in sequence_seperated_order.columns:
                raise ValueError(f"priority_order가 None이고 dag_df에 {config.columns.DUE_DATE} 컬럼이 없는 경우, sequence_seperated_order가 필요합니다")
            
            due_date_mapping = sequence_seperated_order.set_index(config.columns.PROCESS_ID)[config.columns.DUE_DATE].to_dict()
            result = []
            for node_id in priority_order:
                due_date = due_date_mapping.get(node_id)
                if due_date is not None:  # None이 아닌 경우에만 추가
                    result.append((node_id, due_date))
                else:
                    print(f"Warning: node_id {node_id}의 납기일을 찾을 수 없습니다")
        else:
            result = []
            for node_id in priority_order:
                due_date = dag_df.loc[dag_df[config.columns.PROCESS_ID] == node_id, config.columns.DUE_DATE].values[0]
                result.append((node_id, due_date))
        
        
        # 윈도우별로 셋업 최소화 스케줄링 실행
        setup_strategy = SetupMinimizedStrategy()
        
        while result:
            base_date = result[0][1]
            # 윈도우 내 노드들 추출 (첫 번째 노드 기준 ±window_days 이내)
            window_result = [
                item[0] for item in result
                if np.abs((item[1] - base_date) / np.timedelta64(1, 'D')) <= window_days
            ]

            # 셋업 최소화 전략으로 윈도우 내 노드들 스케줄링
            used_ids = setup_strategy.execute(
                dag_manager, scheduler, window_result[0], window_result[1:]
            )
            
            # 사용된 노드들을 제거
            if used_ids:
                result = [item for item in result if item[0] not in used_ids]
            else:
                # 무한루프 방지: 아무것도 스케줄링되지 않았으면 첫 번째 노드 강제 제거
                print(f"[WARNING] 노드가 스케줄링되지 않음. 첫 번째 노드 {result[0][0]} 제거")
                result = result[1:]

        return dag_manager.to_dataframe()


class UserRescheduleStrategy(HighLevelSchedulingStrategy):
    """사용자 재스케줄링 전략 (dag_scheduler.user_reschedule 통합)"""
    
    def execute(self, dag_manager, scheduler, machine_queues):
        """
        사용자가 지정한 기계별 큐 순서로 강제 재스케줄링
        
        Args:
            machine_queues: {machine_index: [node_id, ...]} 형태 딕셔너리
            
        Returns:
            DataFrame: 재스케줄링 결과
        """
        progress = True
        while progress:
            progress = False  # 이번 루프에서 실행이 있었는지 추적
            
            for machine_idx, queue in machine_queues.items():
                if not queue:  # 큐가 비었으면 스킵
                    continue
                
                node_id = queue[0]  # 큐 맨 앞
                node = dag_manager.nodes[node_id]
                
                # 강제 기계 할당 전략 사용 (재스케줄링 모드)
                strategy = ForcedMachineStrategy(machine_idx, use_machine_window=True)
                success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
                
                if success:
                    queue.pop(0)  # 큐에서 제거
                    progress = True  # 실행이 있었음
        
        # 통계 출력
        queue_lengths = {mid: len(q) for mid, q in machine_queues.items()}
        total_remaining = sum(queue_lengths.values())
        
        queue_front_info = {}
        for mid, q in machine_queues.items():
            if q:  # 큐가 비어있지 않으면
                front_id = q[0]
                queue_front_info[mid] = {
                    "node_id": front_id,
                    "parent_node_count": getattr(dag_manager.nodes[front_id], "parent_node_count", None)
                }
            else:
                queue_front_info[mid] = None
        
        # print("남은 큐 길이:", queue_lengths)
        # print("전체 남은 노드 수:", total_remaining)
        # print("각 큐의 맨 앞 노드 정보:", queue_front_info)
        
        return dag_manager.to_dataframe()


class ForcedMachineStrategy(MachineAssignmentStrategy):
    """특정 기계 강제 할당 전략"""
    
    def __init__(self, target_machine_idx: int, use_machine_window: bool = False):
        """
        Args:
            target_machine_idx: 강제 할당할 기계 인덱스
            use_machine_window: machine_window_flag 사용 여부 (재스케줄링용)
        """
        self.target_machine_idx = target_machine_idx
        self.use_machine_window = use_machine_window
        
    def assign(self, scheduler, node, earliest_start: float) -> AssignmentResult:
        """
        지정된 기계에 강제 할당
        
        기존 코드: scheduler.force_assign_operation(machine_idx, earliest_start, node_id, depth, ...)
        """
        try:
            flag, start_time, processing_time = scheduler.force_assign_operation(
                self.target_machine_idx, 
                earliest_start, 
                node.id, 
                node.depth,
                machine_window_flag=self.use_machine_window
            )
            
            return AssignmentResult(
                success=flag,
                machine_index=self.target_machine_idx if flag else None,
                start_time=start_time if flag else None,
                processing_time=processing_time if flag else None
            )
        except Exception as e:
            return AssignmentResult(
                success=False,
                machine_index=None,
                start_time=None,
                processing_time=None
            )

