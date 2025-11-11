"""
글로벌 기계 제약조건(블랙리스트) 기능 단위 테스트

테스트 시나리오:
1. preprocess_global_machine_limit() - 제품군별 제약을 GITEM별로 확장
2. operation_machine_global_limit() - 블랙리스트 적용하여 linespeed 제거
3. 안전성 보장 메커니즘 - 모든 기계가 제거되지 않도록 보장
4. 통합 테스트 - 전체 파이프라인 테스트
"""

import sys
import os
import pandas as pd
import numpy as np

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.validation.production_preprocessor import ProductionDataPreprocessor
from src.order_sequencing.operation_machine_limit import operation_machine_global_limit
from config import config


class TestPreprocessGlobalMachineLimit:
    """preprocess_global_machine_limit() 함수 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 샘플 데이터 준비"""
        self.preprocessor = ProductionDataPreprocessor()

        # 샘플 global_machine_limit_df (제품군별 기계 제약조건)
        self.global_machine_limit_df = pd.DataFrame({
            config.columns.GRP2_NAME: ['제품군A', '제품군B', '제품군A'],
            config.columns.OPERATION_CLASSIFICATION: ['염색', '코팅', '안료점착'],
            config.columns.MACHINE_CODE: ['C2210', 'C2220', 'C2230']
        })

        # 샘플 gitem_sitem_df (제품군-GITEM 매핑)
        self.gitem_sitem_df = pd.DataFrame({
            config.columns.GRP2_NAME: ['제품군A', '제품군A', '제품군B', '제품군B'],
            config.columns.GITEM: ['GITEM001', 'GITEM002', 'GITEM003', 'GITEM004']
        })

        # 샘플 operation_df (공정 정보)
        self.operation_df = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM001', 'GITEM002', 'GITEM002',
                                   'GITEM003', 'GITEM003', 'GITEM004', 'GITEM004'],
            config.columns.OPERATION_CODE: ['DYE01', 'COAT01', 'DYE02', 'COAT02',
                                            'DYE03', 'COAT03', 'DYE04', 'COAT04'],
            config.columns.OPERATION_CLASSIFICATION: ['염색', '코팅', '염색', '코팅',
                                                      '염색', '코팅', '염색', '코팅']
        })

    def test_basic_expansion(self):
        """제품군별 제약을 GITEM별로 확장하는지 테스트"""
        result = self.preprocessor.preprocess_global_machine_limit(
            self.global_machine_limit_df,
            self.gitem_sitem_df,
            self.operation_df
        )

        # 결과가 DataFrame인지 확인
        assert isinstance(result, pd.DataFrame)

        # 필수 컬럼이 있는지 확인
        required_cols = {config.columns.GITEM, config.columns.OPERATION_CODE,
                        config.columns.MACHINE_CODE}
        assert required_cols.issubset(set(result.columns))

        # 제품군A(GITEM001, GITEM002)에 대한 제약이 확장되었는지 확인
        gitem001_rows = result[result[config.columns.GITEM] == 'GITEM001']
        assert len(gitem001_rows) > 0

        print(f"\n[TEST PASS] 제품군별 제약 확장: {len(result)}개 행 생성")
        print(f"결과 샘플:\n{result.head()}")

    def test_operation_code_mapping(self):
        """공정구분이 공정코드로 올바르게 매핑되는지 테스트"""
        result = self.preprocessor.preprocess_global_machine_limit(
            self.global_machine_limit_df,
            self.gitem_sitem_df,
            self.operation_df
        )

        # 공정코드가 정상적으로 매핑되었는지 확인
        assert config.columns.OPERATION_CODE in result.columns

        # 염색 → DYE01, DYE02, DYE03, DYE04 중 하나로 매핑
        dye_rows = result[result[config.columns.OPERATION_CLASSIFICATION] == '염색']
        assert all(dye_rows[config.columns.OPERATION_CODE].str.startswith('DYE'))

        print(f"\n[TEST PASS] 공정코드 매핑 성공")

    def test_duplication_removal(self):
        """중복 제거가 올바르게 동작하는지 테스트"""
        result = self.preprocessor.preprocess_global_machine_limit(
            self.global_machine_limit_df,
            self.gitem_sitem_df,
            self.operation_df
        )

        # 중복이 제거되었는지 확인
        key_cols = [config.columns.GITEM, config.columns.OPERATION_CODE,
                   config.columns.MACHINE_CODE]
        duplicates = result[key_cols].duplicated()
        assert not duplicates.any()

        print(f"\n[TEST PASS] 중복 제거 완료: {len(result)}개 unique 행")


class TestOperationMachineGlobalLimit:
    """operation_machine_global_limit() 함수 테스트"""

    def setup_method(self):
        """샘플 linespeed 데이터 준비"""
        # 샘플 linespeed (GITEM, 공정, 기계별 속도)
        self.linespeed = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM001', 'GITEM002', 'GITEM002'],
            config.columns.OPERATION_CODE: ['DYE01', 'COAT01', 'DYE02', 'COAT02'],
            'C2210': [100.0, 120.0, 110.0, 130.0],
            'C2220': [105.0, 125.0, 115.0, 135.0],
            'C2230': [102.0, 122.0, 112.0, 132.0]
        })

        # 샘플 블랙리스트 (GITEM001-DYE01은 C2210에서 불가)
        self.global_machine_limit = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM002'],
            config.columns.OPERATION_CODE: ['DYE01', 'COAT02'],
            config.columns.MACHINE_CODE: ['C2210', 'C2230']
        })

    def test_basic_blacklist_application(self):
        """블랙리스트가 올바르게 적용되는지 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.global_machine_limit
        )

        # GITEM001-DYE01의 C2210이 NaN이어야 함
        row = result[(result[config.columns.GITEM] == 'GITEM001') &
                     (result[config.columns.OPERATION_CODE] == 'DYE01')]
        assert pd.isna(row['C2210'].iloc[0])

        # GITEM001-DYE01의 C2220, C2230은 유지되어야 함
        assert pd.notna(row['C2220'].iloc[0])
        assert pd.notna(row['C2230'].iloc[0])

        print(f"\n[TEST PASS] 블랙리스트 적용 성공")
        print(f"결과:\n{result}")

    def test_multiple_blacklist_entries(self):
        """여러 블랙리스트 항목이 올바르게 적용되는지 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.global_machine_limit
        )

        # GITEM002-COAT02의 C2230이 NaN이어야 함
        row = result[(result[config.columns.GITEM] == 'GITEM002') &
                     (result[config.columns.OPERATION_CODE] == 'COAT02')]
        assert pd.isna(row['C2230'].iloc[0])

        print(f"\n[TEST PASS] 복수 블랙리스트 적용 성공")

    def test_machine_column_preservation(self):
        """모든 기계 컬럼이 보존되는지 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.global_machine_limit
        )

        # 원본 기계 컬럼이 모두 존재하는지 확인
        machine_cols = ['C2210', 'C2220', 'C2230']
        assert all(col in result.columns for col in machine_cols)

        print(f"\n[TEST PASS] 기계 컬럼 보존 성공")


class TestSafetyMechanism:
    """안전성 보장 메커니즘 테스트"""

    def setup_method(self):
        """위험한 블랙리스트 시나리오 준비"""
        # 샘플 linespeed (GITEM001-DYE01은 C2210에서만 처리 가능)
        self.linespeed = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM002', 'GITEM003'],
            config.columns.OPERATION_CODE: ['DYE01', 'DYE02', 'DYE03'],
            'C2210': [100.0, 110.0, 120.0],
            'C2220': [np.nan, 115.0, 125.0],  # GITEM001-DYE01은 C2220 불가
            'C2230': [np.nan, 112.0, 122.0]   # GITEM001-DYE01은 C2230 불가
        })

        # 위험한 블랙리스트: GITEM001-DYE01의 유일한 가능 기계(C2210)를 제거 시도
        self.dangerous_blacklist = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM002'],
            config.columns.OPERATION_CODE: ['DYE01', 'DYE02'],
            config.columns.MACHINE_CODE: ['C2210', 'C2220']
        })

    def test_prevent_total_removal(self):
        """모든 기계가 제거되지 않도록 보장하는지 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.dangerous_blacklist
        )

        # GITEM001-DYE01 행 확인
        row = result[(result[config.columns.GITEM] == 'GITEM001') &
                     (result[config.columns.OPERATION_CODE] == 'DYE01')]

        # 모든 기계 컬럼
        machine_cols = ['C2210', 'C2220', 'C2230']

        # 최소 1개의 기계는 유효해야 함 (안전성 보장)
        valid_machines = row[machine_cols].notna().sum(axis=1).iloc[0]
        assert valid_machines >= 1, f"모든 기계가 제거됨! valid_machines={valid_machines}"

        print(f"\n[TEST PASS] 안전성 보장 성공: 유효 기계 {valid_machines}개 유지")
        print(f"GITEM001-DYE01 결과:\n{row[machine_cols]}")

    def test_safe_removal_allowed(self):
        """안전한 제거는 허용되는지 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.dangerous_blacklist
        )

        # GITEM002-DYE02는 C2210, C2230이 유효하므로 C2220 제거 가능
        row = result[(result[config.columns.GITEM] == 'GITEM002') &
                     (result[config.columns.OPERATION_CODE] == 'DYE02')]

        # C2220이 제거되었는지 확인
        assert pd.isna(row['C2220'].iloc[0])

        # C2210, C2230은 유지되어야 함
        assert pd.notna(row['C2210'].iloc[0])
        assert pd.notna(row['C2230'].iloc[0])

        print(f"\n[TEST PASS] 안전한 제거 허용됨")

    def test_risky_group_detection(self):
        """위험 그룹 감지 로직 테스트"""
        result = operation_machine_global_limit(
            self.linespeed.copy(),
            self.dangerous_blacklist
        )

        # GITEM001-DYE01 (위험 그룹)
        risky_row = result[(result[config.columns.GITEM] == 'GITEM001') &
                           (result[config.columns.OPERATION_CODE] == 'DYE01')]
        risky_valid = risky_row[['C2210', 'C2220', 'C2230']].notna().sum(axis=1).iloc[0]

        # GITEM002-DYE02 (안전 그룹)
        safe_row = result[(result[config.columns.GITEM] == 'GITEM002') &
                          (result[config.columns.OPERATION_CODE] == 'DYE02')]
        safe_valid = safe_row[['C2210', 'C2220', 'C2230']].notna().sum(axis=1).iloc[0]

        # 위험 그룹은 유효 기계가 보존되어야 함
        assert risky_valid >= 1

        # 안전 그룹은 제거가 적용되어야 함
        assert safe_valid >= 2  # C2210, C2230 유지

        print(f"\n[TEST PASS] 위험 그룹 감지 및 보호 성공")
        print(f"  위험 그룹(GITEM001-DYE01): {risky_valid}개 유효")
        print(f"  안전 그룹(GITEM002-DYE02): {safe_valid}개 유효")


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_blacklist(self):
        """빈 블랙리스트 처리 테스트"""
        linespeed = pd.DataFrame({
            config.columns.GITEM: ['GITEM001'],
            config.columns.OPERATION_CODE: ['DYE01'],
            'C2210': [100.0],
            'C2220': [105.0]
        })

        empty_blacklist = pd.DataFrame(columns=[
            config.columns.GITEM,
            config.columns.OPERATION_CODE,
            config.columns.MACHINE_CODE
        ])

        result = operation_machine_global_limit(linespeed.copy(), empty_blacklist)

        # 원본과 동일해야 함
        assert result.equals(linespeed)

        print(f"\n[TEST PASS] 빈 블랙리스트 처리 성공")

    def test_missing_required_columns(self):
        """필수 컬럼이 없는 경우 테스트"""
        linespeed = pd.DataFrame({
            config.columns.GITEM: ['GITEM001'],
            config.columns.OPERATION_CODE: ['DYE01'],
            'C2210': [100.0]
        })

        # 필수 컬럼 누락된 블랙리스트
        invalid_blacklist = pd.DataFrame({
            'WRONG_COLUMN': ['GITEM001']
        })

        result = operation_machine_global_limit(linespeed.copy(), invalid_blacklist)

        # 원본이 유지되어야 함
        assert result.equals(linespeed)

        print(f"\n[TEST PASS] 잘못된 블랙리스트 처리 성공 (원본 유지)")

    def test_all_nan_initially(self):
        """초기에 모든 기계가 NaN인 경우 테스트"""
        linespeed = pd.DataFrame({
            config.columns.GITEM: ['GITEM001', 'GITEM002'],
            config.columns.OPERATION_CODE: ['DYE01', 'DYE02'],
            'C2210': [np.nan, 100.0],  # GITEM001은 이미 모든 기계 불가
            'C2220': [np.nan, 105.0]
        })

        blacklist = pd.DataFrame({
            config.columns.GITEM: ['GITEM001'],
            config.columns.OPERATION_CODE: ['DYE01'],
            config.columns.MACHINE_CODE: ['C2210']
        })

        result = operation_machine_global_limit(linespeed.copy(), blacklist)

        # GITEM001-DYE01은 여전히 모든 기계 NaN이어야 함
        row = result[(result[config.columns.GITEM] == 'GITEM001') &
                     (result[config.columns.OPERATION_CODE] == 'DYE01')]
        assert row[['C2210', 'C2220']].isna().all().all()

        print(f"\n[TEST PASS] 초기 전체 NaN 처리 성공")


def run_integration_test():
    """
    통합 테스트: 전체 파이프라인 시뮬레이션

    시나리오:
    - 3개 제품군, 각 2개 GITEM
    - 제품군별 기계 제약조건 설정
    - 안전성 검증
    """
    print("\n" + "="*80)
    print("통합 테스트 시작: 글로벌 기계 제약조건 전체 파이프라인")
    print("="*80)

    # 1. 샘플 데이터 생성
    print("\n[1단계] 샘플 데이터 생성")

    # 제품군-GITEM 매핑
    gitem_sitem_df = pd.DataFrame({
        config.columns.GRP2_NAME: ['제품군A', '제품군A', '제품군B', '제품군B', '제품군C', '제품군C'],
        config.columns.GITEM: ['G001', 'G002', 'G003', 'G004', 'G005', 'G006']
    })
    print(f"제품군-GITEM 매핑:\n{gitem_sitem_df}\n")

    # 공정 정보
    operation_df = pd.DataFrame({
        config.columns.GITEM: ['G001', 'G001', 'G002', 'G002', 'G003', 'G003',
                               'G004', 'G004', 'G005', 'G005', 'G006', 'G006'],
        config.columns.OPERATION_CODE: ['DYE1', 'COAT1', 'DYE1', 'COAT1', 'DYE2', 'COAT2',
                                        'DYE2', 'COAT2', 'DYE3', 'COAT3', 'DYE3', 'COAT3'],
        config.columns.OPERATION_CLASSIFICATION: ['염색', '코팅', '염색', '코팅', '염색', '코팅',
                                                  '염색', '코팅', '염색', '코팅', '염색', '코팅']
    })
    print(f"공정 정보 (샘플):\n{operation_df.head()}\n")

    # 제품군별 기계 제약조건
    global_limit_raw = pd.DataFrame({
        config.columns.GRP2_NAME: ['제품군A', '제품군B'],
        config.columns.OPERATION_CLASSIFICATION: ['염색', '코팅'],
        config.columns.MACHINE_CODE: ['M01', 'M02']
    })
    print(f"제품군별 제약조건:\n{global_limit_raw}\n")

    # linespeed 초기 데이터
    linespeed = pd.DataFrame({
        config.columns.GITEM: ['G001', 'G002', 'G003', 'G004', 'G005', 'G006'],
        config.columns.OPERATION_CODE: ['DYE1', 'DYE1', 'DYE2', 'DYE2', 'DYE3', 'DYE3'],
        'M01': [100.0, 105.0, 110.0, 115.0, 120.0, 125.0],
        'M02': [102.0, 107.0, 112.0, 117.0, 122.0, 127.0],
        'M03': [101.0, 106.0, 111.0, 116.0, 121.0, 126.0]
    })
    print(f"초기 linespeed:\n{linespeed}\n")

    # 2. 전처리: 제품군별 제약을 GITEM별로 확장
    print("[2단계] 제품군별 제약 → GITEM별 제약 확장")
    preprocessor = ProductionDataPreprocessor()
    global_limit_expanded = preprocessor.preprocess_global_machine_limit(
        global_limit_raw, gitem_sitem_df, operation_df
    )
    print(f"확장된 글로벌 제약조건:\n{global_limit_expanded}\n")

    # 3. 블랙리스트 적용
    print("[3단계] 블랙리스트 적용")
    linespeed_filtered = operation_machine_global_limit(
        linespeed.copy(), global_limit_expanded
    )
    print(f"필터링 후 linespeed:\n{linespeed_filtered}\n")

    # 4. 안전성 검증
    print("[4단계] 안전성 검증")
    machine_cols = ['M01', 'M02', 'M03']
    for idx, row in linespeed_filtered.iterrows():
        gitem = row[config.columns.GITEM]
        op_code = row[config.columns.OPERATION_CODE]
        valid_count = row[machine_cols].notna().sum()

        if valid_count == 0:
            print(f"  [CRITICAL] {gitem}-{op_code}: 모든 기계 제거됨!")
        elif valid_count == 1:
            print(f"  [WARN] {gitem}-{op_code}: 유효 기계 1개만 남음")
        else:
            print(f"  [OK] {gitem}-{op_code}: 유효 기계 {valid_count}개")

    # 5. 변경 사항 비교
    print("\n[5단계] 변경 사항 요약")
    for idx, row in linespeed.iterrows():
        gitem = row[config.columns.GITEM]
        op_code = row[config.columns.OPERATION_CODE]

        original_valid = row[machine_cols].notna().sum()
        filtered_row = linespeed_filtered[
            (linespeed_filtered[config.columns.GITEM] == gitem) &
            (linespeed_filtered[config.columns.OPERATION_CODE] == op_code)
        ]

        if not filtered_row.empty:
            filtered_valid = filtered_row[machine_cols].notna().sum().iloc[0]
            removed = original_valid - filtered_valid

            if removed > 0:
                print(f"  {gitem}-{op_code}: {original_valid}개 → {filtered_valid}개 ({removed}개 제거)")

    print("\n" + "="*80)
    print("통합 테스트 완료")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("글로벌 기계 제약조건 단위 테스트 시작")
    print("="*80 + "\n")

    # 1. TestPreprocessGlobalMachineLimit
    print("=" * 80)
    print("1. TestPreprocessGlobalMachineLimit")
    print("=" * 80)
    test1 = TestPreprocessGlobalMachineLimit()
    test1.setup_method()

    try:
        test1.test_basic_expansion()
        print("[PASS] test_basic_expansion")
    except AssertionError as e:
        print(f"[FAIL] test_basic_expansion: {e}")

    try:
        test1.test_operation_code_mapping()
        print("[PASS] test_operation_code_mapping")
    except AssertionError as e:
        print(f"[FAIL] test_operation_code_mapping: {e}")

    try:
        test1.test_duplication_removal()
        print("[PASS] test_duplication_removal")
    except AssertionError as e:
        print(f"[FAIL] test_duplication_removal: {e}")

    # 2. TestOperationMachineGlobalLimit
    print("\n" + "=" * 80)
    print("2. TestOperationMachineGlobalLimit")
    print("=" * 80)
    test2 = TestOperationMachineGlobalLimit()
    test2.setup_method()

    try:
        test2.test_basic_blacklist_application()
        print("[PASS] test_basic_blacklist_application")
    except AssertionError as e:
        print(f"[FAIL] test_basic_blacklist_application: {e}")

    try:
        test2.test_multiple_blacklist_entries()
        print("[PASS] test_multiple_blacklist_entries")
    except AssertionError as e:
        print(f"[FAIL] test_multiple_blacklist_entries: {e}")

    try:
        test2.test_machine_column_preservation()
        print("[PASS] test_machine_column_preservation")
    except AssertionError as e:
        print(f"[FAIL] test_machine_column_preservation: {e}")

    # 3. TestSafetyMechanism
    print("\n" + "=" * 80)
    print("3. TestSafetyMechanism (핵심 테스트)")
    print("=" * 80)
    test3 = TestSafetyMechanism()
    test3.setup_method()

    try:
        test3.test_prevent_total_removal()
        print("[PASS] test_prevent_total_removal")
    except AssertionError as e:
        print(f"[FAIL] test_prevent_total_removal: {e}")

    try:
        test3.test_safe_removal_allowed()
        print("[PASS] test_safe_removal_allowed")
    except AssertionError as e:
        print(f"[FAIL] test_safe_removal_allowed: {e}")

    try:
        test3.test_risky_group_detection()
        print("[PASS] test_risky_group_detection")
    except AssertionError as e:
        print(f"[FAIL] test_risky_group_detection: {e}")

    # 4. TestEdgeCases
    print("\n" + "=" * 80)
    print("4. TestEdgeCases")
    print("=" * 80)
    test4 = TestEdgeCases()

    try:
        test4.test_empty_blacklist()
        print("[PASS] test_empty_blacklist")
    except AssertionError as e:
        print(f"[FAIL] test_empty_blacklist: {e}")

    try:
        test4.test_missing_required_columns()
        print("[PASS] test_missing_required_columns")
    except AssertionError as e:
        print(f"[FAIL] test_missing_required_columns: {e}")

    try:
        test4.test_all_nan_initially()
        print("[PASS] test_all_nan_initially")
    except AssertionError as e:
        print(f"[FAIL] test_all_nan_initially: {e}")

    # 통합 테스트
    run_integration_test()

    print("\n" + "="*80)
    print("모든 테스트 완료!")
    print("="*80)
