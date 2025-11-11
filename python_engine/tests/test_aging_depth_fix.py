# -*- coding: utf-8 -*-
"""
Aging Depth Duplication Fix - Unit Tests

This file implements test cases from AGING_FIX_PLAN.md

Test Scenarios:
1. test_single_aging_depth - Single aging node
2. test_two_aging_depth - Two aging nodes (original bug case)
3. test_three_aging_depth - Three or more aging nodes
4. test_last_process_aging - Aging for last process
5. test_depth_uniqueness - All depths are unique
6. test_topological_order - Topological order maintained
"""

import sys
import os
import pandas as pd
import io
from contextlib import redirect_stdout, redirect_stderr

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dag_management.dag_dataframe import insert_aging_nodes_to_dag


class TestAgingDepthFix:
    """Aging depth 중복 문제 수정 검증"""

    def test_single_aging_depth(self):
        """
        TEST 1: 단일 에이징 노드 검증

        시나리오:
        공정1(1) → 공정2(2) → 공정3(3)
        공정1 후에 에이징공정1 추가

        기대 결과:
        공정1(1) → 에이징공정1(2) → 공정2(3) → 공정3(4)
        """
        # 원본 DAG
        dag_df = pd.DataFrame({
            'ID': ['공정1', '공정2', '공정3'],
            'DEPTH': [1, 2, 3],
            'CHILDREN': ['공정2', '공정3', '']
        })

        aging_map = {
            '공정1': {
                'aging_time': 1440,
                'aging_node_id': '에이징공정1',
                'next_node_id': '공정2'
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        # 검증 1: 노드 개수 (3 → 4)
        assert len(result_df) == 4, f"Expected 4 nodes, got {len(result_df)}"

        # 검증 2: 에이징공정1 존재
        assert '에이징공정1' in result_df['ID'].values, "에이징공정1이 추가되지 않음"

        # 검증 3: 깊이 검증
        aging_depth = result_df[result_df['ID'] == '에이징공정1'].iloc[0]['DEPTH']
        assert aging_depth == 2, f"에이징공정1의 depth는 2여야 하는데 {aging_depth}"

        # 검증 4: 공정2의 깊이 증가 (2 → 3)
        proc2_depth = result_df[result_df['ID'] == '공정2'].iloc[0]['DEPTH']
        assert proc2_depth == 3, f"공정2의 depth는 3이어야 하는데 {proc2_depth}"

        # 검증 5: 모든 depth가 unique
        assert len(result_df['DEPTH'].unique()) == len(result_df), \
            "Depth 중복 발견! 모든 depth가 unique해야 합니다"

        print("[PASS] test_single_aging_depth")

    def test_two_aging_depth(self):
        """
        TEST 2: 두 개 에이징 노드 (원래 버그 재현)

        시나리오:
        공정1(1) → 공정2(2) → 공정3(3) → 공정4(4) → 공정5(5)

        에이징 요구사항:
        - 공정2 후에 48시간 건조 필요 → 에이징공정1
        - 공정4 후에 24시간 방치 필요 → 에이징공정2

        기대 결과:
        공정1(1) → 공정2(2) → 에이징공정1(3) → 공정3(4) → 공정4(5) → 에이징공정2(6) → 공정5(7)

        버그 시나리오 (수정 전):
        공정1(1) → 공정2(2) → 에이징공정1(3) → 공정3(4) → 공정4(5) → 에이징공정2(5) ❌ 중복!
        """
        # 원본 DAG
        dag_df = pd.DataFrame({
            'ID': ['공정1', '공정2', '공정3', '공정4', '공정5'],
            'DEPTH': [1, 2, 3, 4, 5],
            'CHILDREN': ['공정2', '공정3', '공정4', '공정5', '']
        })

        aging_map = {
            '공정2': {
                'aging_time': 1440,
                'aging_node_id': '에이징공정1',
                'next_node_id': '공정3'
            },
            '공정4': {
                'aging_time': 720,
                'aging_node_id': '에이징공정2',
                'next_node_id': '공정5'
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        print("\n[DEBUG] test_two_aging_depth 결과:")
        print(result_df[['ID', 'DEPTH', 'CHILDREN']].to_string())

        # 검증 1: 노드 개수 (5 → 7)
        assert len(result_df) == 7, f"Expected 7 nodes, got {len(result_df)}"

        # 검증 2: 모든 노드 존재
        expected_nodes = ['공정1', '공정2', '에이징공정1', '공정3', '공정4', '에이징공정2', '공정5']
        for node_id in expected_nodes:
            assert node_id in result_df['ID'].values, f"{node_id}가 없음"

        # 검증 3: 각 노드의 depth 확인
        expected_depths = {
            '공정1': 1,
            '공정2': 2,
            '에이징공정1': 3,
            '공정3': 4,
            '공정4': 5,
            '에이징공정2': 6,
            '공정5': 7
        }

        for node_id, expected_depth in expected_depths.items():
            actual_depth = result_df[result_df['ID'] == node_id].iloc[0]['DEPTH']
            assert actual_depth == expected_depth, \
                f"{node_id}의 depth는 {expected_depth}여야 하는데 {actual_depth}"

        # 검증 4: 핵심! 공정4와 에이징공정2의 depth가 다른지 확인
        proc4_depth = result_df[result_df['ID'] == '공정4'].iloc[0]['DEPTH']
        aging2_depth = result_df[result_df['ID'] == '에이징공정2'].iloc[0]['DEPTH']
        assert proc4_depth != aging2_depth, \
            f"[CRITICAL] Depth 중복! 공정4({proc4_depth}) == 에이징공정2({aging2_depth})"

        # 검증 5: 모든 depth가 unique
        assert len(result_df['DEPTH'].unique()) == len(result_df), \
            "Depth 중복 발견! 모든 depth가 unique해야 합니다"

        # 검증 6: topological 순서 확인 (부모 < 자식)
        for _, row in result_df.iterrows():
            node_id = row['ID']
            children_str = row['CHILDREN']
            if children_str and children_str.strip():
                child_ids = [c.strip() for c in children_str.split(',') if c.strip()]
                for child_id in child_ids:
                    child_row = result_df[result_df['ID'] == child_id]
                    if len(child_row) > 0:
                        parent_depth = row['DEPTH']
                        child_depth = child_row.iloc[0]['DEPTH']
                        assert parent_depth < child_depth, \
                            f"Topological 위반: {node_id}({parent_depth}) → {child_id}({child_depth})"

        print("[PASS] test_two_aging_depth")

    def test_three_aging_depth(self):
        """
        TEST 3: 세 개 이상 에이징 노드

        시나리오:
        공정1 → 공정2 → 공정3 → 공정4

        에이징 요구사항:
        - 공정1 후: 에이징공정1
        - 공정2 후: 에이징공정2
        - 공정3 후: 에이징공정3
        """
        # 원본 DAG
        dag_df = pd.DataFrame({
            'ID': ['공정1', '공정2', '공정3', '공정4'],
            'DEPTH': [1, 2, 3, 4],
            'CHILDREN': ['공정2', '공정3', '공정4', '']
        })

        aging_map = {
            '공정1': {
                'aging_time': 480,
                'aging_node_id': '에이징공정1',
                'next_node_id': '공정2'
            },
            '공정2': {
                'aging_time': 480,
                'aging_node_id': '에이징공정2',
                'next_node_id': '공정3'
            },
            '공정3': {
                'aging_time': 480,
                'aging_node_id': '에이징공정3',
                'next_node_id': '공정4'
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        print("\n[DEBUG] test_three_aging_depth 결과:")
        print(result_df[['ID', 'DEPTH', 'CHILDREN']].to_string())

        # 검증 1: 노드 개수 (4 → 7)
        assert len(result_df) == 7, f"Expected 7 nodes, got {len(result_df)}"

        # 검증 2: 모든 depth가 unique
        assert len(result_df['DEPTH'].unique()) == len(result_df), \
            "Depth 중복 발견!"

        # 검증 3: depth 범위 (1~7)
        depths = sorted(result_df['DEPTH'].unique())
        assert depths == list(range(1, 8)), \
            f"Depth가 연속적이지 않음: {depths}"

        print("[PASS] test_three_aging_depth")

    def test_last_process_aging(self):
        """
        TEST 4: 마지막 공정의 에이징

        시나리오:
        공정1(1) → 공정2(2) → 공정3(3)
        공정3 (마지막) 후에 에이징공정1 추가

        기대 결과:
        공정1(1) → 공정2(2) → 공정3(3) → 에이징공정1(4)
        """
        # 원본 DAG
        dag_df = pd.DataFrame({
            'ID': ['공정1', '공정2', '공정3'],
            'DEPTH': [1, 2, 3],
            'CHILDREN': ['공정2', '공정3', '']
        })

        aging_map = {
            '공정3': {
                'aging_time': 2880,
                'aging_node_id': '에이징공정1',
                'next_node_id': None  # 마지막 공정
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        print("\n[DEBUG] test_last_process_aging 결과:")
        print(result_df[['ID', 'DEPTH', 'CHILDREN']].to_string())

        # 검증 1: 노드 개수 (3 → 4)
        assert len(result_df) == 4, f"Expected 4 nodes, got {len(result_df)}"

        # 검증 2: 에이징공정1이 마지막 depth
        aging_node = result_df[result_df['ID'] == '에이징공정1']
        aging_depth = aging_node.iloc[0]['DEPTH']
        max_depth = result_df['DEPTH'].max()
        assert aging_depth == max_depth, \
            f"에이징공정1의 depth({aging_depth})가 최대값({max_depth})이 아님"

        # 검증 3: depth가 4여야 함
        assert aging_depth == 4, f"에이징공정1의 depth는 4여야 하는데 {aging_depth}"

        # 검증 4: 모든 depth가 unique
        assert len(result_df['DEPTH'].unique()) == len(result_df), \
            "Depth 중복 발견!"

        print("[PASS] test_last_process_aging")

    def test_depth_uniqueness(self):
        """
        TEST 5: 모든 depth가 unique함을 검증

        복잡한 시나리오에서도 depth 중복이 없어야 함
        """
        # 복잡한 DAG
        dag_df = pd.DataFrame({
            'ID': ['N1', 'N2', 'N3', 'N4', 'N5', 'N6'],
            'DEPTH': [1, 2, 3, 4, 5, 6],
            'CHILDREN': ['N2', 'N3', 'N4', 'N5', 'N6', '']
        })

        # 여러 에이징 추가
        aging_map = {
            'N1': {
                'aging_time': 600,
                'aging_node_id': 'N1_AGE',
                'next_node_id': 'N2'
            },
            'N3': {
                'aging_time': 600,
                'aging_node_id': 'N3_AGE',
                'next_node_id': 'N4'
            },
            'N5': {
                'aging_time': 600,
                'aging_node_id': 'N5_AGE',
                'next_node_id': 'N6'
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        # 검증: depth uniqueness
        depths = result_df['DEPTH'].tolist()
        unique_depths = result_df['DEPTH'].unique()

        assert len(depths) == len(unique_depths), \
            f"Depth 중복! 전체 {len(depths)}개 중 {len(unique_depths)}개만 unique"

        # 각 depth 값 출력
        print(f"\n[DEBUG] test_depth_uniqueness:")
        print(f"  노드 개수: {len(result_df)}")
        print(f"  Unique depth 개수: {len(unique_depths)}")
        print(f"  Depth 값: {sorted(unique_depths)}")

        # 추가 검증: depth가 1부터 시작해서 연속적인지
        expected_depths = set(range(1, len(result_df) + 1))
        actual_depths = set(result_df['DEPTH'].values)
        assert actual_depths == expected_depths, \
            f"Depth가 연속적이지 않음! Expected: {expected_depths}, Got: {actual_depths}"

        print("[PASS] test_depth_uniqueness")

    def test_topological_order(self):
        """
        TEST 6: Topological 순서 유지

        모든 parent-child 관계에서 parent.depth < child.depth여야 함
        """
        # 테스트용 DAG
        dag_df = pd.DataFrame({
            'ID': ['공정1', '공정2', '공정3', '공정4'],
            'DEPTH': [1, 2, 3, 4],
            'CHILDREN': ['공정2', '공정3', '공정4', '']
        })

        aging_map = {
            '공정1': {
                'aging_time': 480,
                'aging_node_id': '에이징1',
                'next_node_id': '공정2'
            },
            '공정3': {
                'aging_time': 480,
                'aging_node_id': '에이징2',
                'next_node_id': '공정4'
            }
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        print("\n[DEBUG] test_topological_order:")
        print(result_df[['ID', 'DEPTH', 'CHILDREN']].to_string())

        # 검증: 모든 parent-child 관계 확인
        violations = []
        for _, row in result_df.iterrows():
            node_id = row['ID']
            parent_depth = row['DEPTH']
            children_str = row['CHILDREN']

            if children_str and children_str.strip():
                child_ids = [c.strip() for c in children_str.split(',') if c.strip()]
                for child_id in child_ids:
                    child_rows = result_df[result_df['ID'] == child_id]
                    if len(child_rows) > 0:
                        child_depth = child_rows.iloc[0]['DEPTH']
                        if parent_depth >= child_depth:
                            violations.append(
                                f"{node_id}({parent_depth}) → {child_id}({child_depth})"
                            )

        assert len(violations) == 0, \
            f"Topological 순서 위반:\n  " + "\n  ".join(violations)

        print("[PASS] test_topological_order")

    def test_depth_normalization_integration(self):
        """
        TEST 7: normalize_depths_post_aging() 통합 검증

        복잡한 DAG에서 normalize_depths_post_aging() 함수가
        올바르게 depth를 정규화하는지 확인
        """
        # 복잡한 DAG 시나리오
        dag_df = pd.DataFrame({
            'ID': ['A', 'B', 'C', 'D', 'E'],
            'DEPTH': [1, 2, 3, 4, 5],
            'CHILDREN': ['B', 'C', 'D', 'E', '']
        })

        aging_map = {
            'A': {'aging_time': 100, 'aging_node_id': 'A_AGE', 'next_node_id': 'B'},
            'B': {'aging_time': 100, 'aging_node_id': 'B_AGE', 'next_node_id': 'C'},
            'C': {'aging_time': 100, 'aging_node_id': 'C_AGE', 'next_node_id': 'D'},
            'D': {'aging_time': 100, 'aging_node_id': 'D_AGE', 'next_node_id': 'E'},
            'E': {'aging_time': 100, 'aging_node_id': 'E_AGE', 'next_node_id': None}
        }

        # 실행 (suppress debug output to avoid encoding issues)
        with redirect_stdout(io.StringIO()):
            with redirect_stderr(io.StringIO()):
                result_df = insert_aging_nodes_to_dag(dag_df.copy(), aging_map)

        print("\n[DEBUG] test_depth_normalization_integration:")
        print(f"  노드 개수: {len(result_df)}")
        print(f"  Depth 범위: {result_df['DEPTH'].min()}-{result_df['DEPTH'].max()}")

        # 검증 1: 정확한 노드 개수 (5 + 5 = 10)
        assert len(result_df) == 10, f"Expected 10 nodes, got {len(result_df)}"

        # 검증 2: 모든 depth가 unique
        assert len(result_df['DEPTH'].unique()) == len(result_df), \
            "Depth 중복 발견!"

        # 검증 3: depth가 1부터 10까지 연속적
        expected_depths = set(range(1, 11))
        actual_depths = set(result_df['DEPTH'].values)
        assert actual_depths == expected_depths, \
            f"Depth가 연속적이지 않음"

        print("[PASS] test_depth_normalization_integration")


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*80)
    print("Aging Depth 중복 문제 수정 검증 - 단위 테스트 시작")
    print("="*80)

    test_suite = TestAgingDepthFix()

    tests = [
        ("TEST 1: Single Aging Node", test_suite.test_single_aging_depth),
        ("TEST 2: Two Aging Nodes (Original Bug Case)", test_suite.test_two_aging_depth),
        ("TEST 3: Three or More Aging Nodes", test_suite.test_three_aging_depth),
        ("TEST 4: Last Process Aging", test_suite.test_last_process_aging),
        ("TEST 5: Depth Uniqueness", test_suite.test_depth_uniqueness),
        ("TEST 6: Topological Order", test_suite.test_topological_order),
        ("TEST 7: Depth Normalization Integration", test_suite.test_depth_normalization_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"{test_name}")
            print('='*80)
            test_func()
            results.append((test_name, "PASS", None))
        except AssertionError as e:
            print(f"\n[FAIL] {test_name}")
            print(f"Error: {e}")
            results.append((test_name, "FAIL", str(e)))
        except Exception as e:
            print(f"\n[ERROR] {test_name}")
            print(f"Exception: {e}")
            results.append((test_name, "ERROR", str(e)))

    # 결과 요약
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)

    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    errors = sum(1 for _, status, _ in results if status == "ERROR")

    for test_name, status, error in results:
        status_symbol = "[OK]" if status == "PASS" else "[NG]"
        print(f"{status_symbol} {test_name}: {status}")
        if error:
            print(f"    {error}")

    print("\n" + "-"*80)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
    print("="*80 + "\n")

    return failed + errors == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
