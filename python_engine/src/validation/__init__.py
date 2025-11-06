"""
생산계획 원본 데이터(Ver4) 전처리 모듈

Excel에서 읽은 데이터프레임들을 스케줄링에 필요한 형태로 전처리합니다.
"""

from .production_preprocessor import ProductionDataPreprocessor
from .validator import DataValidator
import pandas as pd
import json
from typing import Dict


def preprocess_production_data(
    order_df: pd.DataFrame,
    linespeed_df: pd.DataFrame,
    operation_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    chemical_df: pd.DataFrame,
    operation_delay_df: pd.DataFrame,
    width_change_df: pd.DataFrame,
    gitem_sitem_df: pd.DataFrame = None,
    linespeed_period: str = '6_months',
    yield_period: str = '6_months',
    validate: bool = True,
    save_output: bool = False,
    output_file: str = "data/input/python_input.xlsx"
) -> Dict[str, pd.DataFrame]:
    """
    Ver4 원본 데이터 전처리

    Args:
        order_df (pd.DataFrame): PO정보 시트
        linespeed_df (pd.DataFrame): 라인스피드-GITEM등 시트
        operation_df (pd.DataFrame): GITEM-공정-순서 시트
        yield_df (pd.DataFrame): 수율-GITEM등 시트
        chemical_df (pd.DataFrame): 배합액정보 시트
        operation_delay_df (pd.DataFrame): 공정교체시간 시트
        width_change_df (pd.DataFrame): 폭변경 시트
        gitem_sitem_df (pd.DataFrame): 제품군-GITEM-SITEM 시트 (검증용)
        linespeed_period (str): 라인스피드 기간 설정 ('6_months', '1_year', '3_months')
        yield_period (str): 수율 기간 설정 ('6_months', '1_year', '3_months')
        validate (bool): 데이터 유효성 검사 수행 여부
        save_output (bool): 중간 결과를 python_input.xlsx로 저장할지 여부
        output_file (str): 저장할 파일 경로 (save_output=True일 때만 사용)

    Returns:
        Dict[str, pd.DataFrame]: 전처리된 모든 데이터
            - 'order_data': 주문 데이터
            - 'linespeed': 라인스피드 피벗 테이블
            - 'operation_types': 공정 타입 정보
            - 'operation_sequence': 공정 순서 정보
            - 'yield_data': 수율 정보
            - 'machine_master_info': 설비 마스터 정보
            - 'chemical_data': 배합액 정보
            - 'operation_delay': 공정교체시간
            - 'width_change': 폭변경 정보
            - 'machine_limit': 기계 제한 정보
            - 'machine_allocate': 기계 할당 정보
            - 'machine_rest': 기계 중단시간 정보
            - 'validation_result': 검증 결과 (validate=True인 경우)
    """

    # === 1단계: 검증 및 중복 제거 (Validator) ===
    validation_result = None
    cleaned_data = {}

    if validate and gitem_sitem_df is not None:
        validator = DataValidator()
        cleaned_data, validation_result = validator.validate_and_clean(
            order_df=order_df,
            gitem_sitem_df=gitem_sitem_df,
            operation_df=operation_df,
            yield_df=yield_df,
            linespeed_df=linespeed_df,
            chemical_df=chemical_df
        )

        # 검증 결과 요약 출력
        if not validation_result['is_valid']:
            print("\n" + "!"*80)
            print(f"⚠️  데이터 검증에서 {len(validation_result['errors'])}개의 문제가 발견되었습니다.")
            print("⚠️  아래 문제들을 확인하고 필요시 원본 데이터를 수정하세요.")
            print("!"*80)
        else:
            print("\n" + "="*80)
            print("✅ 데이터 검증 완료: 모든 검증 통과!")
            print("="*80 + "\n")
        
        # JSON 검증 결과 저장 (테이블 단위 요약 구조)
        if validation_result and 'validation_issues' in validation_result:
            issues = validation_result['validation_issues']

            # 테이블별로 이슈 그룹화
            table_to_issues = {}
            for issue in issues:
                table_name = issue.get('table_name', 'unknown')
                # 개별 이슈 항목에서 table_name 제거 (상위 블록에서 제공)
                issue_entry = {k: v for k, v in issue.items() if k != 'table_name'}
                table_to_issues.setdefault(table_name, []).append(issue_entry)

            # 테이블별 summary 계산
            tables_output = []
            total_errors = 0
            total_warnings = 0
            tables_valid = 0

            for table_name, table_issues in table_to_issues.items():
                err_count = sum(1 for it in table_issues if it.get('severity') == 'error')
                warn_count = sum(1 for it in table_issues if it.get('severity') == 'warning')
                total_errors += err_count
                total_warnings += warn_count
                is_valid_table = err_count == 0
                if is_valid_table:
                    tables_valid += 1

                tables_output.append({
                    "table_name": table_name,
                    "validation_summary": {
                        "is_valid": is_valid_table,
                        "total_errors": err_count,
                        "total_warnings": warn_count
                    },
                    "issues": table_issues
                })

            json_output = {
                "overall_summary": {
                    "total_tables": len(tables_output),
                    "tables_valid": tables_valid,
                    "total_errors": total_errors,
                    "total_warnings": total_warnings
                },
                "tables": tables_output
            }

            json_file_path = "data/output/validation_result.json"
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_output, f, ensure_ascii=False, indent=2)
            print(f"[Validation] JSON 검증 결과 저장: {json_file_path}")
    else:
        # 검증 스킵 시 원본 데이터 사용
        cleaned_data = {
            'order_df': order_df,
            'linespeed_df': linespeed_df,
            'yield_df': yield_df,
            'operation_df': operation_df,
            'chemical_df': chemical_df
        }

    # === 2단계: 데이터 변환 (ProductionDataPreprocessor) ===
    print("[Validation] 데이터 변환 시작...")

    preprocessor = ProductionDataPreprocessor()

    # 각 데이터 전처리 (검증 및 정제된 데이터 사용)
    order_data = preprocessor.preprocess_order_data(cleaned_data['order_df'])
    linespeed, linespeed_pivot = preprocessor.preprocess_linespeed_data(cleaned_data['linespeed_df'], linespeed_period)
    operation_types, operation_sequence = preprocessor.preprocess_operation_data(cleaned_data['operation_df'])
    yield_info = preprocessor.preprocess_yield_data(cleaned_data['yield_df'], yield_period)
    machine_master_info = preprocessor.preprocess_machine_master_info(cleaned_data['linespeed_df'])
    chemical_data = preprocessor.preprocess_chemical_data(cleaned_data['chemical_df'])

    print("[Validation] 데이터 변환 완료. 결과 정리 중...")

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
        'validation_result': validation_result
    }

    # 옵션: Excel 파일로 저장
    if save_output:
        print(f"[Validation] 중간 결과를 {output_file}에 저장 중...")
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            for sheet_name, df in processed_data.items():
                if type(df) == pd.DataFrame: # 데이터프레임 타입만 저장. 이때 validation_result는 딕셔너리이므로 저장하지 않음  
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"[Validation] 저장 완료: {output_file}")

    print("[Validation] 전처리 완료!")

    return processed_data


__all__ = ['preprocess_production_data', 'ProductionDataPreprocessor', 'DataValidator']
