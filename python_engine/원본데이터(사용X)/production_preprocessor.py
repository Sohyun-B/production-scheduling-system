
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
        # 필요한 컬럼만 선택
        order_data = order_df[[config.columns.PO_NO, config.columns.GITEM, config.columns.GITEM_NAME, config.columns.SITEM,
                              config.columns.SITEM_NAME, config.columns.SPEC, config.columns.REQUEST_AMOUNT, config.columns.DUE_DATE]]

        # Spec 컬럼을 분해 (Thickness, Width, Length)
        order_data[['Thickness', config.columns.WIDTH, config.columns.LENGTH]] = order_data[config.columns.SPEC].str.split("*", expand=True)

        # Fabric_Length 계산
        order_data[config.columns.FABRIC_LENGTH] = order_data[config.columns.LENGTH].astype(int) * order_data[config.columns.REQUEST_AMOUNT].astype(int)


        return order_data

    def _select_period_columns(self, df: pd.DataFrame, period: str, 
                              prefix: str, period_mapping: Dict[str, str]) -> Tuple[pd.DataFrame, list]:
        """
        기간별 컬럼 선택 헬퍼 함수

        Args:
            df: 데이터프레임
            period: 기간 ('6_months', '1_year', '3_months')
            prefix: 컬럼 접두사 ('L', 'S')
            period_mapping: 기간별 패턴 매핑

        Returns:
            tuple: (처리된 데이터프레임, 선택된 컬럼 리스트)
        """
        pattern = period_mapping.get(period, r"^{}.*1$".format(prefix))
        selected_cols = [col for col in df.columns if re.match(pattern, col)]
        print(f"{period} 기준 컬럼명: {selected_cols}")

        return df, selected_cols

    def preprocess_linespeed_data(self, linespeed_df: pd.DataFrame, 
                                 linespeed_period: str = '6_months') -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        라인스피드 데이터 전처리

        Args:
            linespeed_df (pd.DataFrame): 라인스피드 원본 데이터프레임
            linespeed_period (str): 기간 설정 ('6_months', '1_year', '3_months')

        Returns:
            tuple: (선택된 라인스피드 데이터, 피벗된 라인스피드 데이터)
        """
        # 복사본 생성
        linespeed = linespeed_df.copy()

        # 중복 제거
        linespeed = linespeed.drop_duplicates(keep='first')

        # 기간별 컬럼 선택
        period_mapping = {
            '6_months': r"^l.*1$",
            '1_year': r"^l.*0$",
            '3_months': r"^l.*2$"  # 원본 코드에서 3개월도 2로 끝나는 패턴 사용
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

        # 피벗 테이블 생성
        linespeed_pivot = linespeed.pivot(
            index=[config.columns.GITEM, config.columns.OPERATION_CODE],
            columns=config.columns.MACHINE_CODE,
            values='selected_linespeed'
        ).reset_index().rename_axis(None, axis=1)

        return linespeed, linespeed_pivot

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
        operation_types = gitem_operation_sequence[[config.columns.operation_code, config.columns.OPERATION, config.columns.operation_classification]].drop_duplicates(keep='first')

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

        # 컬럼명 변경
        yield_data = yield_data.rename(columns={"GItemName": "GitemName"})

        # 기간별 컬럼 선택
        period_mapping = {
            '6_months': r"^S.*1$",
            '1_year': r"^S.*2$",
            '3_months': r"^S.*2$"
        }

        yield_data, yield_cols = self._select_period_columns(
            yield_data, yield_period, 'S', period_mapping
        )

        # 0을 NaN으로 변경
        yield_data = yield_data.replace(0, np.nan)

        # NaN이 아닌 첫 번째 값으로 yield 컬럼 생성
        yield_data['yield'] = yield_data[yield_cols].bfill(axis=1).iloc[:, 0]

        # 수율이 없으면 100으로 설정
        yield_data['yield'] = yield_data['yield'].replace(np.nan, 100)

        # 선택된 컬럼명 저장
        yield_data['selected'] = yield_data[yield_cols].apply(
            lambda x: x.first_valid_index(), axis=1
        )

        # S로 시작하는 컬럼 제거
        yield_data = yield_data.drop(
            columns=yield_data.columns[yield_data.columns.str.startswith("S")]
        )

        # 중복 제거
        yield_info = yield_data.drop_duplicates(subset=['GitemNo', 'GitemName'], keep='first')

        return yield_info

    def preprocess_machine_master_info(self, linespeed_df: pd.DataFrame) -> pd.DataFrame:
        """
        설비 마스터 정보 전처리

        Args:
            linespeed_df (pd.DataFrame): 라인스피드 원본 데이터프레임

        Returns:
            pd.DataFrame: 설비 마스터 정보
        """
        machine_master_info = (
            linespeed_df[['MachineNo', 'MachineName']]
            .drop_duplicates()
            .sort_values(by='MachineNo')
            .reset_index(drop=True)
            .assign(MachineIndex=lambda df: range(len(df)))
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

    def create_empty_dataframes(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        빈 데이터프레임 생성

        Returns:
            tuple: (machine_limit, machine_allocate, machine_rest)
        """
        machine_limit = pd.DataFrame(columns=[config.columns.OPERATION_CODE, config.columns.MACHINE_CODE])
        machine_allocate = pd.DataFrame(columns=[config.columns.OPERATION_CODE, config.columns.MACHINE_CODE])
        machine_rest = pd.DataFrame(columns=[config.columns.MACHINE_CODE, 'dt_start', 'dt_end'])

        return machine_limit, machine_allocate, machine_rest


def main(excel_file_path: str = "생산계획 필요기준정보 내역-Ver4.xlsx", 
         output_file: str = "python_input.xlsx",
         linespeed_period: str = '6_months',
         yield_period: str = '6_months'):
    """
    메인 실행 함수 - 전체 전처리 및 저장

    Args:
        excel_file_path (str): 입력 Excel 파일 경로
        output_file (str): 출력 Excel 파일 경로
        linespeed_period (str): 라인스피드 기간 설정
        yield_period (str): 수율 기간 설정

    Returns:
        Dict[str, pd.DataFrame]: 전처리된 모든 데이터
    """
    # Excel 파일에서 데이터 읽기
    print("Excel 파일에서 데이터 읽는 중...")

    # 각 시트에서 데이터 읽기
    order_df = pd.read_excel(excel_file_path, sheet_name="PO정보", skiprows=1)
    linespeed_df = pd.read_excel(excel_file_path, sheet_name="라인스피드-GITEM등", skiprows=5)
    operation_df = pd.read_excel(excel_file_path, sheet_name="GITEM-공정-순서", skiprows=1)
    yield_df = pd.read_excel(excel_file_path, sheet_name="수율-GITEM등", skiprows=5)
    chemical_df = pd.read_excel(excel_file_path, sheet_name="배합액정보", skiprows=5)
    operation_delay_df = pd.read_excel(excel_file_path, sheet_name="공정교체시간", skiprows=1)
    width_change_df = pd.read_excel(excel_file_path, sheet_name="폭변경", skiprows=1)

    print("데이터 읽기 완료. 전처리 시작...")

    # 전처리기 초기화
    preprocessor = ProductionDataPreprocessor()

    # 각 데이터 전처리
    order_data = preprocessor.preprocess_order_data(order_df)
    linespeed, linespeed_pivot = preprocessor.preprocess_linespeed_data(linespeed_df, linespeed_period)
    operation_types, operation_sequence = preprocessor.preprocess_operation_data(operation_df)
    yield_info = preprocessor.preprocess_yield_data(yield_df, yield_period)
    machine_master_info = preprocessor.preprocess_machine_master_info(linespeed_df)
    chemical_data = preprocessor.preprocess_chemical_data(chemical_df)
    machine_limit, machine_allocate, machine_rest = preprocessor.create_empty_dataframes()

    print("전처리 완료. 결과 정리 중...")

    # 결과를 딕셔너리로 정리
    processed_data = {
        'order_data': order_data,
        'linespeed': linespeed_pivot,
        'operation_types': operation_types,
        'operation_sequence': operation_sequence,
        'yield_data': yield_info,
        'machine_master_info': machine_master_info,
        'chemical_data': chemical_data,
        'operation_delay': operation_delay_df,
        'width_change': width_change_df,
        'machine_limit': machine_limit,
        'machine_allocate': machine_allocate,
        'machine_rest': machine_rest
    }

    # Excel 파일로 저장
    print(f"결과를 {output_file}에 저장 중...")
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for sheet_name, df in processed_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"전처리 완료! 데이터가 {output_file}에 저장되었습니다.")

    return processed_data


if __name__ == "__main__":
    processed_data = main()
