
"""
생산계획 데이터 전처리 모듈
데이터프레임을 파라미터로 받아 전처리하는 함수들을 제공합니다.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, Tuple, Union
from config import config


class ProductionDataPreprocessor:
    """
    생산계획 데이터 전처리 클래스
    """

    def __init__(self):
        """
        전처리기 초기화
        """
        pass

    def preprocess_order_data(self, order_df: pd.DataFrame) -> pd.DataFrame:
        """
        주문 데이터 전처리

        Args:
            order_df (pd.DataFrame): PO정보 원본 데이터프레임

        Returns:
            pd.DataFrame: 전처리된 주문 데이터
        """
        # 필요한 컬럼만 선택하고 복사본 생성
        order_data = order_df[[config.columns.PO_NO, config.columns.GITEM, config.columns.GITEM_NAME, config.columns.SITEM,
                              config.columns.SITEM_NAME, config.columns.SPEC, config.columns.REQUEST_AMOUNT, config.columns.DUE_DATE]].copy()

        # Spec 컬럼을 분해 (Thickness, Width, Length)
        order_data[['Thickness', config.columns.WIDTH, config.columns.LENGTH]] = order_data[config.columns.SPEC].str.split("*", expand=True)

        # Fabric_Length 계산
        order_data[config.columns.FABRIC_LENGTH] = order_data[config.columns.LENGTH].astype(int) * order_data[config.columns.REQUEST_AMOUNT].astype(int)

        # # 납기일 처리: 원본 백업 및 조정된 납기일로 덮어쓰기 
        # 납기일 조정 기능 삭제
        # order_data[config.columns.ORIGINAL_DUE_DATE] = order_data['DUEDATE']
        # order_data['DUEDATE'] = pd.to_datetime(order_data['DUEDATE']) - pd.Timedelta(days=buffer_days)

        return order_data

    def _select_period_columns(self, df: pd.DataFrame, period: str, 
                              prefix: str, period_mapping: Dict[str, str]) -> Tuple[pd.DataFrame, list]:
        """
        기간별 컬럼 선택 헬퍼 함수

        Args:
            df: 데이터프레임
            period: 기간 ('6_months', '1_year', '3_months')
            prefix: 컬럼 접두사 ('l', 's')
            period_mapping: 기간별 패턴 매핑

        Returns:
            tuple: (처리된 데이터프레임, 선택된 컬럼 리스트)
        """
        pattern = period_mapping.get(period, r"^{}.*1$".format(prefix))
        selected_cols = [col for col in df.columns if re.match(pattern, col)]
        print(f"{period} 기준 컬럼명: {selected_cols}")

        return df, selected_cols

    def preprocess_linespeed_data(self, linespeed_df: pd.DataFrame,
                                 linespeed_period: str = '6_months') -> pd.DataFrame:
        """
        라인스피드 데이터 전처리 (Long Format 유지)

        ⚠️ 리팩토링: Pivot 제거 - 원본 Long Format 유지
        전처리만 수행 (검증은 validation 단계에서 이미 완료됨)

        Args:
            linespeed_df (pd.DataFrame): 라인스피드 원본 데이터프레임
            linespeed_period (str): 기간 설정 ('6_months', '1_year', '3_months')

        Returns:
            pd.DataFrame: Long Format 라인스피드 데이터
                         컬럼: [gitemno, proccode, machineno, linespeed, ...]
        """
        # 복사본 생성
        linespeed = linespeed_df.copy()

        # 기간별 컬럼 선택
        period_mapping = {
            '6_months': r"^l.*1$",
            '1_year': r"^l.*0$",
            '3_months': r"^l.*2$"
        }

        linespeed, linespeed_cols = self._select_period_columns(
            linespeed, linespeed_period, 'l', period_mapping
        )

        # NaN이 아닌 첫 번째 값으로 linespeed 컬럼 생성
        linespeed['selected_linespeed'] = linespeed[linespeed_cols].bfill(axis=1).iloc[:, 0]

        # 선택된 컬럼명 저장
        linespeed['selected'] = linespeed[linespeed_cols].apply(
            lambda x: x.first_valid_index(), axis=1
        )

        # L로 시작하는 컬럼 제거
        linespeed = linespeed.drop(
            columns=linespeed.columns[linespeed.columns.str.startswith("l")]
        )

        # ⭐ 리팩토링: Pivot 제거!
        # selected_linespeed를 linespeed로 이름 변경
        linespeed = linespeed.rename(columns={'selected_linespeed': 'linespeed'})

        # 중복 제거 (동일한 gitem, proccode, machineno 조합)
        linespeed = linespeed.drop_duplicates(
            subset=[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE],
            keep='first'
        )

        # NaN 제거
        linespeed = linespeed.dropna(subset=['linespeed'])

        print(f"[INFO] Linespeed 전처리 완료 (Long Format): {len(linespeed)}개 레코드")

        # ⭐ Long Format 그대로 반환 (Pivot 제거!)
        return linespeed

    def preprocess_operation_data(self, operation_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        공정 관련 데이터 전처리

        Args:
            operation_df (pd.DataFrame): GITEM-공정-순서 원본 데이터프레임

        Returns:
            tuple: (공정 타입 데이터, 공정 순서 데이터)
        """
        # 복사본 생성
        gitem_operation_sequence = operation_df.copy()

        # 공정 타입 데이터 추출
        operation_types = gitem_operation_sequence[[config.columns.OPERATION_CODE, config.columns.OPERATION, config.columns.OPERATION_CLASSIFICATION]].drop_duplicates(keep='first')

        return operation_types, gitem_operation_sequence

    def preprocess_yield_data(self, yield_df: pd.DataFrame, 
                             yield_period: str = '6_months') -> pd.DataFrame:
        """
        수율 데이터 전처리

        Args:
            yield_df (pd.DataFrame): 수율 원본 데이터프레임
            yield_period (str): 기간 설정 ('6_months', '1_year', '3_months')

        Returns:
            pd.DataFrame: 전처리된 수율 데이터
        """
        # 복사본 생성
        yield_data = yield_df.copy()

        # 기간별 컬럼 선택
        period_mapping = {
            '6_months': r"^s.*1$",
            '1_year': r"^s.*0$",
            '3_months': r"^s.*2$"
        }

        yield_data, yield_cols = self._select_period_columns(
            yield_data, yield_period, 's', period_mapping
        )

        # 0을 NaN으로 변경
        yield_data = yield_data.replace(0, np.nan)

        # NaN이 아닌 첫 번째 값으로 yield 컬럼 생성
        yield_data[config.columns.YIELD] = yield_data[yield_cols].bfill(axis=1).iloc[:, 0]

        # 수율이 없으면 100으로 설정
        yield_data[config.columns.YIELD] = yield_data[config.columns.YIELD].replace(np.nan, 100)

        # 선택된 컬럼명 저장
        yield_data['selected'] = yield_data[yield_cols].apply(
            lambda x: x.first_valid_index(), axis=1
        )

        # S로 시작하는 컬럼 제거
        yield_data = yield_data.drop(
            columns=yield_data.columns[yield_data.columns.str.startswith("s")]
        )

        return yield_data

    def preprocess_machine_master_info(self, linespeed_df: pd.DataFrame) -> pd.DataFrame:
        """
        설비 마스터 정보 전처리

        Args:
            linespeed_df (pd.DataFrame): 라인스피드 원본 데이터프레임

        Returns:
            pd.DataFrame: 설비 마스터 정보
        """
        machine_master_info = (
            linespeed_df[[config.columns.MACHINE_CODE, config.columns.MACHINE_NAME]]
            .drop_duplicates()
            .sort_values(by=config.columns.MACHINE_CODE)
            .reset_index(drop=True)
            .assign(**{config.columns.MACHINE_INDEX: lambda df: range(len(df))})
        )

        return machine_master_info

    def preprocess_chemical_data(self, chemical_df: pd.DataFrame) -> pd.DataFrame:
        """
        배합액 정보 전처리

        Args:
            chemical_df (pd.DataFrame): 배합액정보 원본 데이터프레임

        Returns:
            pd.DataFrame: 전처리된 배합액 데이터
        """
        # 필요한 컬럼만 선택
        chemical_data = chemical_df[[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.CHEMICAL_1, config.columns.CHEMICAL_2]]

        return chemical_data

    def preprocess_aging_data(self, aging_gitem_df: pd.DataFrame, aging_gbn_df: pd.DataFrame,
                             gitem_sitem_df: pd.DataFrame, operation_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aging 데이터 전처리: GITEM별 + 제품군별 aging을 병합하고 공정정보와 결합

        Args:
            aging_gitem_df (pd.DataFrame): GITEM별 에이징 시간 데이터
            aging_gbn_df (pd.DataFrame): 제품군별 에이징 시간 데이터
            gitem_sitem_df (pd.DataFrame): 제품군-GITEM-SITEM 매핑 데이터
            operation_df (pd.DataFrame): 공정 정보 데이터

        Returns:
            pd.DataFrame: 전처리된 에이징 데이터 (gitemno, proccode, aging_time)
        """
        return (
            pd.concat([
                aging_gitem_df,
                gitem_sitem_df[[config.columns.GRP2_NAME, config.columns.GITEM]]
                .merge(aging_gbn_df, on=config.columns.GRP2_NAME, how="inner")
                .drop(columns=[config.columns.GRP2_NAME])
            ], ignore_index=True)
            .merge(
                operation_df[[config.columns.GITEM, config.columns.OPERATION_CLASSIFICATION, config.columns.OPERATION_CODE]],
                how='inner',
                left_on=[config.columns.GITEM, 'prev_procgbn'],
                right_on=[config.columns.GITEM, config.columns.OPERATION_CLASSIFICATION]
            )
            .drop(columns=[config.columns.OPERATION_CLASSIFICATION])
            .drop_duplicates(keep='first')
            [[config.columns.GITEM, config.columns.OPERATION_CODE, 'aging_time']]
            .astype({config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
        )

    def preprocess_global_machine_limit(self, global_machine_limit_df: pd.DataFrame,
                                       gitem_sitem_df: pd.DataFrame,
                                       operation_df: pd.DataFrame) -> pd.DataFrame:
        """
        Global 기계 제약조건 전처리: 제품군별 제약을 GITEM별로 확장하고 공정정보와 결합

        Args:
            global_machine_limit_df (pd.DataFrame): 제품군별 기계 제외 조건
            gitem_sitem_df (pd.DataFrame): 제품군-GITEM-SITEM 매핑 데이터
            operation_df (pd.DataFrame): 공정 정보 데이터

        Returns:
            pd.DataFrame: 전처리된 글로벌 기계 제약조건
        """
        return (
            global_machine_limit_df
            .merge(
                gitem_sitem_df[[config.columns.GRP2_NAME, config.columns.GITEM]],
                on=[config.columns.GRP2_NAME],
                how="inner"
            )
            .drop_duplicates(keep='first')
            .merge(
                operation_df[[config.columns.GITEM, config.columns.OPERATION_CLASSIFICATION, config.columns.OPERATION_CODE]],
                on=[config.columns.GITEM, config.columns.OPERATION_CLASSIFICATION],
                how="left"
            )
            .drop_duplicates(keep='first')
        )
