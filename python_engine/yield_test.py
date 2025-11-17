"""
수율(yield) 적용 전후 비교 및 생산비율 계산 테스트 스크립트

이 스크립트는 다음을 수행합니다:
1. 수율 적용 전후의 CSV 파일을 비교
2. 샘플 데이터로 공정별 수율을 고려한 생산비율 계산
"""

import pandas as pd


def compare_csv_columns():
    """수율 적용 전후 CSV 파일의 컬럼 차이를 비교합니다."""
    before_dag = pd.read_csv("sequence_seperated_order_수율이전.csv")
    after_dag = pd.read_csv("sequence_seperated_order_수율이후.csv")

    before_col_list = before_dag.columns.tolist()
    print("수율 적용 전 컬럼:")
    print(before_col_list)

    after_col_list = after_dag.columns.tolist()
    print("\n수율 적용 후 컬럼:")
    print(after_col_list)

    col_subtracted = set(before_col_list) - set(after_col_list)
    col_added = set(after_col_list) - set(before_col_list)

    print(f"\n제거된 컬럼: {col_subtracted}")
    print(f"추가된 컬럼: {col_added}")

    # 결과 해석:
    # - gitemname 컬럼 추가
    # - 기존 production_length가 수율 적용된 값으로 교체
    # - 수율 적용 이전 길이는 original_production_length에 저장


def calculate_input_ratio(group):
    """
    공정별 수율을 고려한 투입 비율을 계산합니다.

    역순으로 누적 곱을 계산하여 각 공정에서 필요한 투입량 비율을 산출합니다.

    Args:
        group: 같은 item으로 그룹화된 DataFrame

    Returns:
        input_ratio 컬럼이 추가된 DataFrame
    """
    yields = group['yield'].values
    num_processes = len(yields)
    ratios = [1] * num_processes

    accumulator = 1

    # 역순으로 진행하며 누적 곱을 계산
    for i in range(num_processes - 1, -1, -1):
        accumulator *= 1 / yields[i] * 100
        ratios[i] = accumulator

    print("ratios")
    print(ratios)

    group['input_ratio'] = ratios
    print("group")
    print(group)
    return group


def test_yield_calculation():
    """샘플 데이터로 수율 기반 생산비율 계산을 테스트합니다."""

    df = pd.read_csv("sequence_seperated_order_수율이전.csv")
    yield_data = pd.read_excel("data/input/python_input.xlsx", sheet_name="yield_data")
    
    print("\n원본 데이터:")
    print(df.head())

    print("\n수율 데이터")
    print(yield_data.head())

    df = df.merge(yield_data, on = ['gitemno', 'proccode'], how = 'left')

    # item과 process_sequence로 정렬
    df = df.sort_values(['gitemno', 'procseq']).reset_index(drop=True)

    df.to_csv("yield_attached.csv", encoding='utf-8-sig')

    # item별로 그룹화하여 투입 비율 계산
    df = df.groupby('gitemno', group_keys=False).apply(calculate_input_ratio)

    print("\n수율을 고려한 생산비율:")
    print(df)
    df.to_csv("yield_calculated.csv", encoding='utf-8-sig')


if __name__ == "__main__":
    # CSV 비교 실행
    compare_csv_columns()

    # 수율 계산 테스트 실행
    test_yield_calculation()
