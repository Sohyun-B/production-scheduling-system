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
            
        return max(valid_end_times)
    
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
            
            # 3. 기계 할당 (전략 패턴 적용)
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
        
        # 2. 첫번째 공정의 배합액과 공정명 추출 (셋업 시간 최소화를 위한 그룹화)
        mixture_name = dag_manager.opnode_dict.get(start_id)[4]
        operation_name = dag_manager.opnode_dict.get(start_id)[1]
        
        # 3. 윈도우 내에서 비슷한 노드들 그룹화
        same_mixture_queue = []
        same_operation_queue = []
        for gene in window:
            if dag_manager.opnode_dict.get(gene)[4] == mixture_name:  # 배합액이 동일한 경우
                same_mixture_queue.append(gene)
            elif dag_manager.opnode_dict.get(gene)[1] == operation_name:  # 배합액은 달라도 공정이 동일한 경우
                same_operation_queue.append(gene)
        
        # 4. 같은 배합액 내에서 너비 기준 내림차순 정렬
        same_mixture_queue = sorted(
            same_mixture_queue,
            key=lambda gene: dag_manager.opnode_dict.get(gene)[3],
            reverse=True
        )
        
        # 5. 같은 공정 내에서 특정 배합액의 등장순서대로 배합액 기준 정렬
        mixture_groups = OrderedDict()
        for gene in same_operation_queue:
            mixture_name = dag_manager.opnode_dict.get(gene)[4]  # 배합액 이름 추출
            if mixture_name not in mixture_groups:   # 처음 등장한 배합액이면
                mixture_groups[mixture_name] = []
            mixture_groups[mixture_name].append(gene)
        
        # 등장순서대로 그룹을 합침. 이때 그룹 내에서는 너비 기준으로 정렬
        sorted_same_operation_queue = []
        for group in mixture_groups.values():
            group = sorted(group, key=lambda gene: dag_manager.opnode_dict.get(gene)[3], reverse=True)
            sorted_same_operation_queue.extend(group)
        
        # 6. 동일 기계에 강제 할당
        used_ids = [start_id]
        for queue in [same_mixture_queue, sorted_same_operation_queue]:
            for same_mixture_id in queue:
                node = dag_manager.nodes[same_mixture_id]
                strategy = ForcedMachineStrategy(ideal_machine_index, use_machine_window=False)
                success = SchedulingCore.schedule_single_node(node, scheduler, strategy)
                if success:
                    used_ids.append(same_mixture_id)
        
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
        
        # priority_order와 납기일을 결합
        # DUE_DATE 컬럼이 없으면 sequence_seperated_order에서 가져오기
        if config.columns.DUE_DATE not in dag_df.columns:
            # sequence_seperated_order에서 ID별 납기일 매핑 생성
            sequence_seperated_order = kwargs.get('sequence_seperated_order', pd.DataFrame())
            if sequence_seperated_order.empty or config.columns.ID not in sequence_seperated_order.columns:
                raise ValueError(f"priority_order가 None이고 dag_df에 {config.columns.DUE_DATE} 컬럼이 없는 경우, sequence_seperated_order가 필요합니다")
            
            due_date_mapping = sequence_seperated_order.set_index(config.columns.ID)[config.columns.DUE_DATE].to_dict()
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
                due_date = dag_df.loc[dag_df['ID'] == node_id, config.columns.DUE_DATE].values[0]
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
        
        print("남은 큐 길이:", queue_lengths)
        print("전체 남은 노드 수:", total_remaining)
        print("각 큐의 맨 앞 노드 정보:", queue_front_info)
        
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

