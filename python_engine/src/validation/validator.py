"""
원본 데이터 유효성 검사 모듈

order_data를 기준으로 다른 테이블들의 데이터 존재 여부 및 일관성을 검증합니다.
"""

import pandas as pd
from typing import Dict, List, Tuple, Set
from config import config


class DataValidator:
    """데이터 유효성 검사 및 정제 클래스"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.gitem_proccode_pairs: Set[Tuple[str, str]] = set()
        self.cleaned_data = {}
        self.validation_issues = []  # JSON 형식의 검증 이슈 저장

    def validate_all(
        self,
        order_df: pd.DataFrame,
        gitem_sitem_df: pd.DataFrame,
        operation_df: pd.DataFrame,
        yield_df: pd.DataFrame,
        linespeed_df: pd.DataFrame,
        chemical_df: pd.DataFrame
    ) -> Dict:
        """
        전체 데이터 유효성 검사 실행

        Args:
            order_df: PO정보 테이블
            gitem_sitem_df: 제품군-GITEM-SITEM 테이블
            operation_df: GITEM-공정-순서 테이블
            yield_df: 수율-GITEM등 테이블
            linespeed_df: 라인스피드-GITEM등 테이블
            chemical_df: 배합액정보 테이블

        Returns:
            Dict: 검증 결과 딕셔너리
        """
        # order_df의 unique GitemNo 추출
        unique_gitems = order_df[config.columns.GITEM].unique()
        print("\n" + "="*80)
        print("데이터 유효성 검사 시작")
        print("="*80)
        print(f"검증 대상: PO정보의 제품코드 {len(unique_gitems)}개")

        # 1. 제품군-GITEM-SITEM 테이블 검증
        self._validate_gitem_sitem(order_df, gitem_sitem_df)

        # 2. GITEM-공정-순서 테이블 검증 (GitemNo, PROCCODE 쌍 저장)
        self._validate_operation_sequence(unique_gitems, operation_df)

        # 3. 수율-GITEM등 테이블 검증
        self._validate_yield_data(unique_gitems, yield_df)

        # 4. 라인스피드-GITEM등 테이블 검증
        self._validate_linespeed_data(linespeed_df)

        # 5. 배합액정보 테이블 검증
        self._validate_chemical_data(chemical_df)

        # 결과 요약
        result = {
            'is_valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'gitem_proccode_pairs': self.gitem_proccode_pairs,
            'validation_issues': self.validation_issues  # JSON 형식 이슈 추가
        }

        self._print_summary(result)

        return result

    def _validate_gitem_sitem(self, order_df: pd.DataFrame, gitem_sitem_df: pd.DataFrame):
        """1. 제품군-GITEM-SITEM 테이블 검증"""
        print("\n[검증 1/5] 제품군-GITEM-SITEM 테이블")
        print("-" * 80)

        # order_df의 (GItemNo, Spec) 조합 생성
        order_combinations = set(
            zip(order_df[config.columns.GITEM], order_df[config.columns.SPEC])
        )

        # gitem_sitem_df의 (GitemNo, Spec) 조합 생성 (소문자 i)
        gitem_sitem_combinations = set(
            zip(gitem_sitem_df[config.columns.GITEM], gitem_sitem_df[config.columns.SPEC])
        )

        # 존재하지 않는 조합 찾기
        missing_combinations = order_combinations - gitem_sitem_combinations

        if missing_combinations:
            print(f"⚠️  경고: PO정보에는 있지만 제품군-GITEM-SITEM 테이블에 없는 데이터 ({len(missing_combinations)}건)")
            for gitem, spec in missing_combinations:
                warning_msg = f"[제품군-GITEM-SITEM] PO정보의 (제품코드={gitem}, 규격={spec}) 조합이 제품군-GITEM-SITEM 테이블에 존재하지 않습니다."
                self.warnings.append(warning_msg)
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_itemspec",
                    "severity": "warning",
                    "columns": ["gitemno", "spec"],
                    "constraint": "existence",
                    "issue_type": "missing",
                    "values": {
                        "gitemno": str(gitem),
                        "spec": str(spec)
                    },
                    "action_taken": "none"
                })
                
                print(f"  - 제품코드: {gitem}, 규격: {spec}")
        else:
            print(f"✓ 검증 통과: PO정보의 모든 (제품코드, 규격) 조합이 존재합니다.")

    def _validate_operation_sequence(self, unique_gitems: List[str], operation_df: pd.DataFrame):
        """2. GITEM-공정-순서 테이블 검증"""
        print("\n[검증 2/5] GITEM-공정-순서 테이블")
        print("-" * 80)

        # operation_df에 존재하는 GitemNo들
        operation_gitems = set(operation_df[config.columns.GITEM].unique())

        # GitemNo 존재 여부 확인
        missing_gitems = set(unique_gitems) - operation_gitems
        if missing_gitems:
            print(f"❌ 오류: PO정보에는 있지만 GITEM-공정-순서 테이블에 없는 제품코드 ({len(missing_gitems)}건)")
            for gitem in missing_gitems:
                error_msg = f"[GITEM-공정-순서] PO정보의 제품코드={gitem}가 GITEM-공정-순서 테이블에 존재하지 않습니다."
                self.errors.append(error_msg)
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_itemproc",
                    "severity": "error",
                    "columns": ["gitemno"],
                    "constraint": "existence",
                    "issue_type": "missing",
                    "values": {
                        "gitemno": str(gitem)
                    },
                    "action_taken": "none"
                })
                
                print(f"  - 제품코드: {gitem}")

        # 각 GitemNo별 PROCSEQ 연속성 확인
        seq_errors = []
        for gitem in unique_gitems:
            if gitem not in operation_gitems:
                continue

            gitem_operations = operation_df[operation_df[config.columns.GITEM] == gitem].sort_values(config.columns.OPERATION_ORDER)
            procseq_values = gitem_operations[config.columns.OPERATION_ORDER].tolist()

            # PROCSEQ가 1부터 시작하고 연속적인지 확인
            expected_seq = list(range(1, len(procseq_values) + 1))
            if procseq_values != expected_seq:
                error_msg = f"[GITEM-공정-순서] 제품코드={gitem}의 공정순서(PROCSEQ)가 연속적이지 않습니다. 현재: {procseq_values}, 예상: {expected_seq}"
                self.errors.append(error_msg)
                seq_errors.append((gitem, procseq_values, expected_seq))
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_itemproc",
                    "severity": "error",
                    "columns": ["gitemno"],
                    "constraint": "sequence_continuity",
                    "issue_type": "invalid_sequence",
                    "values": {
                        "gitemno": str(gitem)
                    },
                    "action_taken": "none"
                })
            else:
                # 정상이면 (GitemNo, PROCCODE) 쌍 저장
                for _, row in gitem_operations.iterrows():
                    self.gitem_proccode_pairs.add((row[config.columns.GITEM], row[config.columns.OPERATION_CODE]))

        if seq_errors:
            print(f"❌ 오류: 공정순서(PROCSEQ)가 연속적이지 않은 제품코드 ({len(seq_errors)}건)")
            for gitem, current, expected in seq_errors:
                print(f"  - 제품코드: {gitem}")
                print(f"    현재 순서: {current}")
                print(f"    예상 순서: {expected}")

        if not missing_gitems and not seq_errors:
            print(f"✓ 검증 통과: 모든 제품코드의 공정순서가 정상입니다.")
            print(f"  저장된 (제품코드, 공정코드) 쌍: {len(self.gitem_proccode_pairs)}개")

    def _validate_yield_data(self, unique_gitems: List[str], yield_df: pd.DataFrame):
        """3. 수율-GITEM등 테이블 검증"""
        print("\n[검증 3/5] 수율-GITEM등 테이블")
        print("-" * 80)

        missing_gitems = []
        duplicate_gitems = []

        for gitem in unique_gitems:
            gitem_rows = yield_df[yield_df[config.columns.GITEM] == gitem]
            row_count = len(gitem_rows)

            if row_count == 0:
                error_msg = f"[수율-GITEM등] PO정보의 제품코드={gitem}가 수율-GITEM등 테이블에 존재하지 않습니다."
                self.errors.append(error_msg)
                missing_gitems.append(gitem)
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_productionyield",
                    "severity": "error",
                    "columns": ["gitemno"],
                    "constraint": "existence",
                    "issue_type": "missing",
                    "values": {
                        "gitemno": str(gitem)
                    },
                    "action_taken": "none"
                })
                
            elif row_count > 1:
                warning_msg = f"[수율-GITEM등] 제품코드={gitem}가 수율-GITEM등 테이블에 {row_count}개 행으로 중복 존재합니다. (전처리에서 첫 번째 행만 유지)"
                self.warnings.append(warning_msg)
                duplicate_gitems.append((gitem, row_count))
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_productionyield",
                    "severity": "warning",
                    "columns": ["gitemno"],
                    "constraint": "uniqueness",
                    "issue_type": "duplicate",
                    "duplicate_count": row_count,
                    "values": {
                        "gitemno": str(gitem)
                    },
                    "action_taken": "keep_first"
                })

        if missing_gitems:
            print(f"❌ 오류: 수율 데이터가 없는 제품코드 ({len(missing_gitems)}건)")
            for gitem in missing_gitems:
                print(f"  - 제품코드: {gitem}")

        if duplicate_gitems:
            print(f"⚠️  경고: 수율 데이터가 중복된 제품코드 ({len(duplicate_gitems)}건)")
            print(f"   → 전처리 단계에서 첫 번째 행만 자동으로 유지됩니다.")
            for gitem, count in duplicate_gitems:
                print(f"  - 제품코드: {gitem} (중복 {count}건)")

        if not missing_gitems and not duplicate_gitems:
            print(f"✓ 검증 통과: 모든 제품코드가 수율-GITEM등 테이블에 정확히 1개씩 존재합니다.")

    def _validate_linespeed_data(self, linespeed_df: pd.DataFrame):
        """4. 라인스피드-GITEM등 테이블 검증"""
        print("\n[검증 4/5] 라인스피드-GITEM등 테이블")
        print("-" * 80)

        if not self.gitem_proccode_pairs:
            warning_msg = "GITEM-공정-순서 검증 실패로 인해 라인스피드 검증을 건너뜁니다."
            self.warnings.append(warning_msg)
            print(f"⚠️  경고: {warning_msg}")
            return

        missing_pairs = []
        duplicate_pairs = []

        for gitem, proccode in self.gitem_proccode_pairs:
            linespeed_rows = linespeed_df[
                (linespeed_df[config.columns.GITEM] == gitem) &
                (linespeed_df[config.columns.OPERATION_CODE] == proccode)
            ]
            row_count = len(linespeed_rows)

            if row_count == 0:
                error_msg = f"[라인스피드-GITEM등] (제품코드={gitem}, 공정코드={proccode})가 라인스피드-GITEM등 테이블에 존재하지 않습니다."
                self.errors.append(error_msg)
                missing_pairs.append((gitem, proccode))
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_linespeed",
                    "severity": "error",
                    "columns": ["gitemno", "proccode"],
                    "constraint": "existence",
                    "issue_type": "missing",
                    "values": {
                        "gitemno": str(gitem),
                        "proccode": str(proccode)
                    },
                    "action_taken": "none"
                })
                
            elif row_count > 1:
                warning_msg = f"[라인스피드-GITEM등] (제품코드={gitem}, 공정코드={proccode})가 라인스피드-GITEM등 테이블에 {row_count}개 행으로 중복 존재합니다. (전처리에서 첫 번째 행만 유지)"
                self.warnings.append(warning_msg)
                duplicate_pairs.append((gitem, proccode, row_count))
                
                # JSON 이슈 추가
                self.validation_issues.append({
                    "table_name": "tb_linespeed",
                    "severity": "warning",
                    "columns": ["gitemno", "proccode"],
                    "constraint": "uniqueness",
                    "issue_type": "duplicate",
                    "duplicate_count": row_count,
                    "values": {
                        "gitemno": str(gitem),
                        "proccode": str(proccode)
                    },
                    "action_taken": "keep_first"
                })

        if missing_pairs:
            print(f"❌ 오류: 라인스피드 데이터가 없는 (제품코드, 공정코드) 쌍 ({len(missing_pairs)}건)")
            for gitem, proccode in missing_pairs:
                print(f"  - 제품코드: {gitem}, 공정코드: {proccode}")

        if duplicate_pairs:
            print(f"⚠️  경고: 라인스피드 데이터가 중복된 (제품코드, 공정코드) 쌍 ({len(duplicate_pairs)}건)")
            print(f"   → 전처리 단계에서 첫 번째 행만 자동으로 유지됩니다.")
            for gitem, proccode, count in duplicate_pairs:
                print(f"  - 제품코드: {gitem}, 공정코드: {proccode} (중복 {count}건)")

        if not missing_pairs and not duplicate_pairs:
            print(f"✓ 검증 통과: 모든 (제품코드, 공정코드) 쌍이 라인스피드-GITEM등 테이블에 정확히 1개씩 존재합니다.")

    def _validate_chemical_data(self, chemical_df: pd.DataFrame):
        """5. 배합액정보 테이블 검증"""
        print("\n[검증 5/5] 배합액정보 테이블")
        print("-" * 80)

        if not self.gitem_proccode_pairs:
            warning_msg = "GITEM-공정-순서 검증 실패로 인해 배합액정보 검증을 건너뜁니다."
            self.warnings.append(warning_msg)
            print(f"⚠️  경고: {warning_msg}")
            return

        missing_pairs = []
        duplicate_pairs = []

        for gitem, proccode in self.gitem_proccode_pairs:
            chemical_rows = chemical_df[
                (chemical_df[config.columns.GITEM] == gitem) &
                (chemical_df[config.columns.OPERATION_CODE] == proccode)
            ]
            row_count = len(chemical_rows)

            if row_count == 0:
                warning_msg = f"[배합액정보] (제품코드={gitem}, 공정코드={proccode})가 배합액정보 테이블에 존재하지 않습니다. (배합액이 필요 없는 공정일 수 있음)"
                self.warnings.append(warning_msg)
                missing_pairs.append((gitem, proccode))
                
                # JSON 이슈 추가 (누락은 경고)
                self.validation_issues.append({
                    "table_name": "tb_chemical",
                    "severity": "warning",
                    "columns": ["gitemno", "proccode"],
                    "constraint": "existence",
                    "issue_type": "missing",
                    "values": {
                        "gitemno": str(gitem),
                        "proccode": str(proccode)
                    },
                    "action_taken": "none"
                })
                
            elif row_count > 1:
                error_msg = f"[배합액정보] (제품코드={gitem}, 공정코드={proccode})가 배합액정보 테이블에 {row_count}개 행으로 중복 존재합니다."
                self.errors.append(error_msg)
                duplicate_pairs.append((gitem, proccode, row_count))
                
                # JSON 이슈 추가 (중복은 오류)
                self.validation_issues.append({
                    "table_name": "tb_chemical",
                    "severity": "error",
                    "columns": ["gitemno", "proccode"],
                    "constraint": "uniqueness",
                    "issue_type": "duplicate",
                    "duplicate_count": row_count,
                    "values": {
                        "gitemno": str(gitem),
                        "proccode": str(proccode)
                    },
                    "action_taken": "none"
                })

        if missing_pairs:
            print(f"⚠️  경고: 배합액 데이터가 없는 (제품코드, 공정코드) 쌍 ({len(missing_pairs)}건)")
            print(f"   (배합액이 필요 없는 공정일 수 있습니다)")
            for gitem, proccode in missing_pairs:
                print(f"  - 제품코드: {gitem}, 공정코드: {proccode}")

        if duplicate_pairs:
            print(f"❌ 오류: 배합액 데이터가 중복된 (제품코드, 공정코드) 쌍 ({len(duplicate_pairs)}건)")
            for gitem, proccode, count in duplicate_pairs:
                print(f"  - 제품코드: {gitem}, 공정코드: {proccode} (중복 {count}건)")

        if not missing_pairs and not duplicate_pairs:
            print(f"✓ 검증 통과: 모든 (제품코드, 공정코드) 쌍이 배합액정보 테이블에 정확히 1개씩 존재합니다.")

    def _print_summary(self, result: Dict):
        """검증 결과 요약 출력"""
        print("\n" + "="*80)
        print("데이터 유효성 검사 완료")
        print("="*80)

        if result['is_valid']:
            print("✅ 결과: 모든 검증 통과!")
        else:
            print(f"❌ 결과: 총 {len(self.errors)}개의 문제 발견")
            print(f"   - 오류: {len(self.errors)}개")

        if self.warnings:
            print(f"   - 경고: {len(self.warnings)}개")

        print("="*80)

    def clean_duplicates(
        self,
        linespeed_df: pd.DataFrame,
        yield_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        중복 데이터 제거

        Args:
            linespeed_df: 라인스피드 데이터프레임
            yield_df: 수율 데이터프레임

        Returns:
            tuple: (중복 제거된 라인스피드, 중복 제거된 수율)
        """
        print("\n" + "="*80)
        print("데이터 중복 제거")
        print("="*80)

        # 1. 라인스피드 중복 제거
        before_count = len(linespeed_df)
        linespeed_cleaned = linespeed_df.drop_duplicates(keep='first')
        duplicate_count = before_count - len(linespeed_cleaned)

        if duplicate_count > 0:
            duplicated_rows = linespeed_df[linespeed_df.duplicated(keep=False)]
            if config.columns.GITEM in duplicated_rows.columns and config.columns.OPERATION_CODE in duplicated_rows.columns:
                duplicated_pairs = duplicated_rows[[config.columns.GITEM, config.columns.OPERATION_CODE]].drop_duplicates()
                print(f"\n[1/2] 라인스피드 데이터")
                print(f"  중복 {duplicate_count}개 행 발견 → 첫 번째 행만 유지")
                print(f"  중복된 (제품코드, 공정코드) 쌍: {len(duplicated_pairs)}개")
                for _, row in duplicated_pairs.head(5).iterrows():
                    print(f"    - 제품코드: {row[config.columns.GITEM]}, 공정코드: {row[config.columns.OPERATION_CODE]}")
                if len(duplicated_pairs) > 5:
                    print(f"    ... 외 {len(duplicated_pairs) - 5}개")
            else:
                print(f"\n[1/2] 라인스피드 데이터")
                print(f"  중복 {duplicate_count}개 행 발견 → 첫 번째 행만 유지")
        else:
            print(f"\n[1/2] 라인스피드 데이터")
            print(f"  ✓ 중복 없음")

        # 2. 수율 중복 제거
        before_count = len(yield_df)
        # GItemName이 있으면 함께 사용, 없으면 GitemNo만 사용
        subset_cols = [config.columns.GITEM, config.columns.GITEM_NAME] if config.columns.GITEM_NAME in yield_df.columns else [config.columns.GITEM]
        yield_cleaned = yield_df.drop_duplicates(subset=subset_cols, keep='first')
        duplicate_count = before_count - len(yield_cleaned)

        if duplicate_count > 0:
            duplicated_gitems = yield_df[yield_df.duplicated(subset=subset_cols, keep=False)][config.columns.GITEM].unique()
            print(f"\n[2/2] 수율 데이터")
            print(f"  중복 {duplicate_count}개 행 발견 → 첫 번째 행만 유지")
            print(f"  중복된 제품코드: {', '.join(map(str, duplicated_gitems))}")
        else:
            print(f"\n[2/2] 수율 데이터")
            print(f"  ✓ 중복 없음")

        print("="*80 + "\n")

        return linespeed_cleaned, yield_cleaned

    def validate_and_clean(
        self,
        order_df: pd.DataFrame,
        gitem_sitem_df: pd.DataFrame,
        operation_df: pd.DataFrame,
        yield_df: pd.DataFrame,
        linespeed_df: pd.DataFrame,
        chemical_df: pd.DataFrame
    ) -> Tuple[Dict[str, pd.DataFrame], Dict]:
        """
        데이터 검증 및 정제 (통합 메서드)

        Args:
            order_df: PO정보
            gitem_sitem_df: 제품군-GITEM-SITEM
            operation_df: GITEM-공정-순서
            yield_df: 수율-GITEM등
            linespeed_df: 라인스피드-GITEM등
            chemical_df: 배합액정보

        Returns:
            tuple: (정제된 데이터 딕셔너리, 검증 결과)
        """
        # 1. 검증
        validation_result = self.validate_all(
            order_df=order_df,
            gitem_sitem_df=gitem_sitem_df,
            operation_df=operation_df,
            yield_df=yield_df,
            linespeed_df=linespeed_df,
            chemical_df=chemical_df
        )

        # 2. 중복 제거
        linespeed_cleaned, yield_cleaned = self.clean_duplicates(
            linespeed_df=linespeed_df,
            yield_df=yield_df
        )

        # 3. 정제된 데이터 저장
        self.cleaned_data = {
            'order_df': order_df,
            'linespeed_df': linespeed_cleaned,
            'yield_df': yield_cleaned,
            'operation_df': operation_df,
            'chemical_df': chemical_df
        }

        return self.cleaned_data, validation_result
