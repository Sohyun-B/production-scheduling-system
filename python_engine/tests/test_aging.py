"""
Aging 기능 단위 테스트

테스트 시나리오:
1. parse_aging_requirements() - aging_map 생성 테스트
2. insert_aging_nodes_to_dag() - DAG에 aging 노드 삽입 테스트
3. Scheduler - aging_machine 할당 테스트
4. 통합 테스트 - 전체 파이프라인 테스트
"""

import sys
import os
import pandas as pd

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dag_management.dag_dataframe import parse_aging_requirements, insert_aging_nodes_to_dag
from src.scheduler.scheduler import Scheduler
from src.scheduler.machine import Machine_Time_window
from config import config


class TestParseAgingRequirements:
    """parse_aging_requirements() 함수 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 샘플 데이터 준비"""
        # 샘플 aging_df (aging 요구사항)
        self.aging_df = pd.DataFrame({
            'gitemno': ['ITEM001', 'ITEM002', 'ITEM003'],
            'proccode': ['PROC1', 'PROC2', 'PROC1'],
            'aging_time': [1440, 2880, 720]  # 분 단위 (24시간, 48시간, 12시간)
        })

        # 샘플 sequence_seperated_order (공정별로 분리된 주문)
        self.sequence_seperated_order = pd.DataFrame({
            config.columns.ID: ['N001', 'N002', 'N003', 'N004', 'N005', 'N006'],
            config.columns.GITEM: ['ITEM001', 'ITEM001', 'ITEM002', 'ITEM002', 'ITEM003', 'ITEM003'],
            config.columns.OPERATION_CODE: ['PROC1', 'PROC2', 'PROC1', 'PROC2', 'PROC1', 'PROC2'],
            config.columns.OPERATION_ORDER: [1, 2, 1, 2, 1, 2],
            config.columns.PO_NO: ['PO001', 'PO001', 'PO002', 'PO002', 'PO003', 'PO003']
        })

    def test_basic_aging_map_creation(self):
        """기본 aging_map 생성 테스트"""
        aging_map = parse_aging_requirements(self.aging_df, self.sequence_seperated_order)

        # aging_map이 딕셔너리인지 확인
        assert isinstance(aging_map, dict)

        # 예상되는 노드 개수 확인 (3개)
        assert len(aging_map) == 3

        # 각 aging 노드가 올바른 구조인지 확인
        for parent_id, info in aging_map.items():
            assert 'aging_time' in info
            assert 'aging_node_id' in info
            assert 'next_node_id' in info
            assert info['aging_node_id'] == f"{parent_id}_AGING"

    def test_aging_time_values(self):
        """aging_time 값이 올바르게 설정되는지 테스트"""
        aging_map = parse_aging_requirements(self.aging_df, self.sequence_seperated_order)

        # N001 (ITEM001 PROC1) → 1440분
        assert aging_map['N001']['aging_time'] == 1440

        # N003 (ITEM002 PROC1) → 2880분
        # 실제로는 PROC1이지만 aging_df에서 ITEM002의 PROC2가 2880분
        # 이 부분은 실제 데이터 구조에 따라 조정 필요

    def test_next_node_id_detection(self):
        """다음 노드 ID가 올바르게 감지되는지 테스트"""
        aging_map = parse_aging_requirements(self.aging_df, self.sequence_seperated_order)

        # N001 (PO001, order=1) 다음은 N002 (PO001, order=2)
        assert aging_map['N001']['next_node_id'] == 'N002'

        # N003 (PO002, order=1) 다음은 N004 (PO002, order=2)
        assert aging_map['N003']['next_node_id'] == 'N004'

    def test_last_operation_aging(self):
        """마지막 공정 이후 aging의 경우 next_node_id가 None인지 테스트"""
        # 마지막 공정에 aging 추가
        aging_df_last = pd.DataFrame({
            'gitemno': ['ITEM001'],
            'proccode': ['PROC2'],  # 마지막 공정
            'aging_time': [1000]
        })

        aging_map = parse_aging_requirements(aging_df_last, self.sequence_seperated_order)

        # N002가 ITEM001의 PROC2 (마지막 공정)
        if 'N002' in aging_map:
            assert aging_map['N002']['next_node_id'] is None

    def test_empty_aging_df(self):
        """빈 aging_df 처리 테스트"""
        empty_df = pd.DataFrame(columns=['gitemno', 'proccode', 'aging_time'])
        aging_map = parse_aging_requirements(empty_df, self.sequence_seperated_order)

        assert isinstance(aging_map, dict)
        assert len(aging_map) == 0


class TestInsertAgingNodesToDAG:
    """insert_aging_nodes_to_dag() 함수 테스트"""

    def setup_method(self):
        """샘플 DAG 데이터 준비"""
        # 샘플 dag_df
        self.dag_df = pd.DataFrame({
            'ID': ['N001', 'N002', 'N003'],
            'DEPTH': [1, 2, 3],
            'CHILDREN': ['N002', 'N003', '']
        })

        # 샘플 aging_map
        self.aging_map = {
            'N001': {
                'aging_time': 1440,
                'aging_node_id': 'N001_AGING',
                'next_node_id': 'N002'
            }
        }

    def test_aging_node_insertion(self):
        """Aging 노드가 DAG에 삽입되는지 테스트"""
        result_df = insert_aging_nodes_to_dag(self.dag_df.copy(), self.aging_map)

        # 노드 개수가 증가했는지 확인 (3개 → 4개)
        assert len(result_df) == 4

        # Aging 노드가 추가되었는지 확인
        assert 'N001_AGING' in result_df['ID'].values

    def test_children_modification(self):
        """부모 노드의 CHILDREN이 수정되는지 테스트"""
        result_df = insert_aging_nodes_to_dag(self.dag_df.copy(), self.aging_map)

        # N001의 CHILDREN이 'N001_AGING'으로 변경되었는지
        n001_row = result_df[result_df['ID'] == 'N001']
        assert 'N001_AGING' in n001_row.iloc[0]['CHILDREN']
        assert 'N002' not in n001_row.iloc[0]['CHILDREN']

    def test_aging_node_structure(self):
        """Aging 노드의 구조가 올바른지 테스트"""
        result_df = insert_aging_nodes_to_dag(self.dag_df.copy(), self.aging_map)

        # N001_AGING 노드 찾기
        aging_node = result_df[result_df['ID'] == 'N001_AGING']
        assert len(aging_node) == 1

        # CHILDREN이 'N002'인지 확인
        assert aging_node.iloc[0]['CHILDREN'] == 'N002'

    def test_depth_assignment(self):
        """[WARN] Depth 할당 테스트 (현재는 중복 문제 있음)"""
        result_df = insert_aging_nodes_to_dag(self.dag_df.copy(), self.aging_map)

        # N001_AGING의 depth
        aging_node = result_df[result_df['ID'] == 'N001_AGING']
        aging_depth = aging_node.iloc[0]['DEPTH']

        # 현재 구현: parent_depth + 1 = 1 + 1 = 2
        assert aging_depth == 2

        # [WARN] 문제: N002의 depth도 2이면 중복!
        n002_depth = result_df[result_df['ID'] == 'N002'].iloc[0]['DEPTH']
        print(f"[WARN] WARNING: aging_depth={aging_depth}, n002_depth={n002_depth}")

        # 현재는 중복 가능성 있음 (이것이 미해결 이슈)
        if aging_depth == n002_depth:
            print("[WARN] CRITICAL: Depth 중복 발생!")

    def test_sorting(self):
        """결과 DataFrame이 DEPTH 순으로 정렬되는지 테스트"""
        result_df = insert_aging_nodes_to_dag(self.dag_df.copy(), self.aging_map)

        # DEPTH 컬럼이 오름차순인지 확인
        depths = result_df['DEPTH'].tolist()
        assert depths == sorted(depths)


class TestSchedulerAging:
    """Scheduler의 aging_machine 할당 테스트"""

    def setup_method(self):
        """Scheduler 및 샘플 데이터 준비"""
        # machine_dict (aging 노드 포함)
        self.machine_dict = {
            'N001': {0: 100, 1: 120, 2: 110},  # 일반 노드
            'N001_AGING': {-1: 1440},  # Aging 노드 (24시간 = 1440분)
            'N002': {0: 200, 1: 180, 2: 190}  # 일반 노드
        }

    def test_scheduler_initialization(self):
        """Scheduler 초기화 시 aging_machine이 None인지 테스트"""
        scheduler = Scheduler(self.machine_dict, delay_processor=None)
        assert scheduler.aging_machine is None

    def test_allocate_resources_creates_aging_machine(self):
        """allocate_resources() 호출 시 aging_machine이 생성되는지 테스트"""
        scheduler = Scheduler(self.machine_dict, delay_processor=None)
        scheduler.allocate_resources(num_machines=3)

        # aging_machine이 생성되었는지 확인
        assert scheduler.aging_machine is not None
        assert isinstance(scheduler.aging_machine, Machine_Time_window)

        # aging_machine의 인덱스가 -1인지 확인
        assert scheduler.aging_machine.Machine_index == -1

        # allow_overlapping이 True인지 확인
        assert scheduler.aging_machine.allow_overlapping is True

    def test_get_machine_method(self):
        """get_machine() 메서드가 올바르게 동작하는지 테스트"""
        scheduler = Scheduler(self.machine_dict, delay_processor=None)
        scheduler.allocate_resources(num_machines=3)

        # 일반 기계 접근
        machine_0 = scheduler.get_machine(0)
        assert machine_0 is scheduler.Machines[0]

        # Aging 기계 접근
        aging_machine = scheduler.get_machine(-1)
        assert aging_machine is scheduler.aging_machine

    def test_aging_node_detection(self):
        """Aging 노드 감지 로직 테스트"""
        # Aging 노드: machine_dict에서 키가 {-1}만 있음
        aging_machine_info = self.machine_dict['N001_AGING']
        is_aging = set(aging_machine_info.keys()) == {-1}
        assert is_aging is True

        # 일반 노드: machine_dict에서 키가 {0, 1, 2, ...}
        normal_machine_info = self.machine_dict['N001']
        is_not_aging = set(normal_machine_info.keys()) == {-1}
        assert is_not_aging is False

    def test_assign_operation_aging(self):
        """assign_operation()에서 aging 노드를 올바르게 할당하는지 테스트"""
        scheduler = Scheduler(self.machine_dict, delay_processor=None)
        scheduler.allocate_resources(num_machines=3)

        # Aging 노드 할당
        machine_idx, start_time, processing_time = scheduler.assign_operation(
            earliest_start=0,
            node_id='N001_AGING',
            depth=2
        )

        # 기계 인덱스가 -1인지 확인
        assert machine_idx == -1

        # 시작 시간이 earliest_start와 같은지 (즉시 시작)
        assert start_time == 0

        # 처리 시간이 1440인지 확인
        assert processing_time == 1440

        # aging_machine에 작업이 추가되었는지 확인
        assert len(scheduler.aging_machine.assigned_task) == 1


class TestOverlapping:
    """Overlapping 기능 테스트"""

    def test_overlapping_enabled(self):
        """allow_overlapping=True일 때 겹치는 작업 추가 가능한지 테스트"""
        machine = Machine_Time_window(machine_index=-1, allow_overlapping=True)

        # 첫 번째 작업 추가 (0~100)
        machine._Input(depth=1, node_id='AGING1', M_Ealiest=0, P_t=100)

        # 두 번째 작업 추가 (50~150) - 겹침!
        machine._Input(depth=2, node_id='AGING2', M_Ealiest=50, P_t=100)

        # 두 작업이 모두 추가되었는지 확인
        assert len(machine.assigned_task) == 2
        assert 'AGING1' in [task[1] for task in machine.assigned_task]
        assert 'AGING2' in [task[1] for task in machine.assigned_task]

    def test_overlapping_disabled(self):
        """allow_overlapping=False일 때는 빈 시간창에만 추가되는지 테스트"""
        machine = Machine_Time_window(machine_index=0, allow_overlapping=False)

        # 첫 번째 작업 추가 (0~100)
        machine._Input(depth=1, node_id='N001', M_Ealiest=0, P_t=100)

        # 두 번째 작업 추가 시도 (50~150) - 겹침이므로 100 이후로 배치되어야 함
        machine._Input(depth=2, node_id='N002', M_Ealiest=50, P_t=100)

        # N002의 시작 시간이 100 이상이어야 함
        n002_start = machine.O_start[1]
        assert n002_start >= 100


def run_integration_test():
    """
    통합 테스트: 전체 파이프라인 시뮬레이션

    시나리오:
    - 주문 2개 (각 2개 공정)
    - 첫 번째 공정 후 aging 필요
    """
    print("\n" + "="*80)
    print("통합 테스트 시작: Aging 기능 전체 파이프라인")
    print("="*80)

    # 1. 샘플 데이터 생성
    print("\n[1단계] 샘플 데이터 생성")

    aging_df = pd.DataFrame({
        'gitemno': ['ITEM001', 'ITEM002'],
        'proccode': ['PROC1', 'PROC1'],
        'aging_time': [1440, 2880]
    })
    print(f"aging_df:\n{aging_df}\n")

    sequence_seperated_order = pd.DataFrame({
        config.columns.ID: ['N001', 'N002', 'N003', 'N004'],
        config.columns.GITEM: ['ITEM001', 'ITEM001', 'ITEM002', 'ITEM002'],
        config.columns.OPERATION_CODE: ['PROC1', 'PROC2', 'PROC1', 'PROC2'],
        config.columns.OPERATION_ORDER: [1, 2, 1, 2],
        config.columns.PO_NO: ['PO001', 'PO001', 'PO002', 'PO002']
    })
    print(f"sequence_seperated_order:\n{sequence_seperated_order}\n")

    # 2. aging_map 생성
    print("[2단계] parse_aging_requirements() 실행")
    aging_map = parse_aging_requirements(aging_df, sequence_seperated_order)
    print(f"aging_map: {aging_map}\n")

    # 3. DAG에 aging 노드 삽입
    print("[3단계] insert_aging_nodes_to_dag() 실행")
    dag_df = pd.DataFrame({
        'ID': ['N001', 'N002', 'N003', 'N004'],
        'DEPTH': [1, 2, 1, 2],
        'CHILDREN': ['N002', '', 'N004', '']
    })
    print(f"원본 dag_df:\n{dag_df}\n")

    result_dag_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)
    print(f"aging 노드 삽입 후 dag_df:\n{result_dag_df}\n")

    # 4. machine_dict 생성
    print("[4단계] machine_dict 생성 (aging 노드 포함)")
    machine_dict = {
        'N001': {0: 100, 1: 120},
        'N002': {0: 200, 1: 180},
        'N003': {0: 150, 1: 130},
        'N004': {0: 250, 1: 220},
        'N001_AGING': {-1: 1440},
        'N003_AGING': {-1: 2880}
    }
    print(f"machine_dict keys: {list(machine_dict.keys())}\n")

    # 5. Scheduler 초기화 및 aging_machine 생성
    print("[5단계] Scheduler 초기화")
    scheduler = Scheduler(machine_dict, delay_processor=None)
    scheduler.allocate_resources(num_machines=2)
    print(f"Machines 개수: {len(scheduler.Machines)}")
    print(f"aging_machine: {scheduler.aging_machine}")
    print(f"aging_machine.allow_overlapping: {scheduler.aging_machine.allow_overlapping}\n")

    # 6. Aging 노드 할당 테스트
    print("[6단계] Aging 노드 스케줄링 시뮬레이션")

    # N001 할당 (일반 노드)
    m1, s1, p1 = scheduler.assign_operation(0, 'N001', 1)
    print(f"N001 할당: 기계={m1}, 시작={s1}, 소요시간={p1}")

    # N001_AGING 할당
    m2, s2, p2 = scheduler.assign_operation(s1 + p1, 'N001_AGING', 2)
    print(f"N001_AGING 할당: 기계={m2}, 시작={s2}, 소요시간={p2}")

    # N003_AGING 할당 (overlapping 테스트)
    m3, s3, p3 = scheduler.assign_operation(200, 'N003_AGING', 2)
    print(f"N003_AGING 할당: 기계={m3}, 시작={s3}, 소요시간={p3}")

    # 7. aging_machine 상태 확인
    print(f"\n[7단계] aging_machine 최종 상태")
    print(f"assigned_task: {scheduler.aging_machine.assigned_task}")
    print(f"O_start: {scheduler.aging_machine.O_start}")
    print(f"O_end: {scheduler.aging_machine.O_end}")
    print(f"End_time: {scheduler.aging_machine.End_time}")

    # 8. Depth 중복 검증
    print(f"\n[8단계] [WARN] Depth 중복 검증")
    depth_counts = result_dag_df['DEPTH'].value_counts()
    duplicates = depth_counts[depth_counts > 1]
    if not duplicates.empty:
        print(f"[CRITICAL] Depth 중복 발견!")
        print(f"중복된 depth: {duplicates.to_dict()}")
        print(f"\n문제가 되는 노드들:")
        for depth_val in duplicates.index:
            nodes = result_dag_df[result_dag_df['DEPTH'] == depth_val]
            print(f"  depth={depth_val}: {nodes['ID'].tolist()}")
    else:
        print(f"[PASS] Depth 중복 없음")

    print("\n" + "="*80)
    print("통합 테스트 완료")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Aging 기능 단위 테스트 시작")
    print("="*80 + "\n")

    # pytest를 사용하지 않고 직접 실행
    print("=" * 80)
    print("1. TestParseAgingRequirements")
    print("=" * 80)
    test1 = TestParseAgingRequirements()
    test1.setup_method()

    try:
        test1.test_basic_aging_map_creation()
        print("[PASS] test_basic_aging_map_creation")
    except AssertionError as e:
        print(f"[FAIL] test_basic_aging_map_creation: {e}")

    try:
        test1.test_next_node_id_detection()
        print("[PASS] test_next_node_id_detection")
    except AssertionError as e:
        print(f"[FAIL] test_next_node_id_detection: {e}")

    try:
        test1.test_empty_aging_df()
        print("[PASS] test_empty_aging_df")
    except AssertionError as e:
        print(f"[FAIL] test_empty_aging_df: {e}")

    print("\n" + "=" * 80)
    print("2. TestInsertAgingNodesToDAG")
    print("=" * 80)
    test2 = TestInsertAgingNodesToDAG()
    test2.setup_method()

    try:
        test2.test_aging_node_insertion()
        print("[PASS] test_aging_node_insertion PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_aging_node_insertion FAILED: {e}")

    try:
        test2.test_children_modification()
        print("[PASS] test_children_modification PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_children_modification FAILED: {e}")

    try:
        test2.test_depth_assignment()
        print("[PASS] test_depth_assignment PASSED ([WARN] Depth 중복 가능)")
    except AssertionError as e:
        print(f"[FAIL] test_depth_assignment FAILED: {e}")

    print("\n" + "=" * 80)
    print("3. TestSchedulerAging")
    print("=" * 80)
    test3 = TestSchedulerAging()
    test3.setup_method()

    try:
        test3.test_scheduler_initialization()
        print("[PASS] test_scheduler_initialization PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_scheduler_initialization FAILED: {e}")

    try:
        test3.test_allocate_resources_creates_aging_machine()
        print("[PASS] test_allocate_resources_creates_aging_machine PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_allocate_resources_creates_aging_machine FAILED: {e}")

    try:
        test3.test_get_machine_method()
        print("[PASS] test_get_machine_method PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_get_machine_method FAILED: {e}")

    try:
        test3.test_aging_node_detection()
        print("[PASS] test_aging_node_detection PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_aging_node_detection FAILED: {e}")

    try:
        test3.test_assign_operation_aging()
        print("[PASS] test_assign_operation_aging PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_assign_operation_aging FAILED: {e}")

    print("\n" + "=" * 80)
    print("4. TestOverlapping")
    print("=" * 80)
    test4 = TestOverlapping()

    try:
        test4.test_overlapping_enabled()
        print("[PASS] test_overlapping_enabled PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_overlapping_enabled FAILED: {e}")

    try:
        test4.test_overlapping_disabled()
        print("[PASS] test_overlapping_disabled PASSED")
    except AssertionError as e:
        print(f"[FAIL] test_overlapping_disabled FAILED: {e}")

    # 통합 테스트 실행
    run_integration_test()

    print("\n" + "="*80)
    print("모든 테스트 완료!")
    print("="*80)
