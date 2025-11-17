import pandas as pd
from config import config


def yield_prediction(yield_data, sequence_seperated_order):
    """
    yield_data: gitemno, proccode 별 수율 (단위: %)
    
    수율에 따라 공정에 길이 추가하는 함수
    해당 공정이 수행된 뒤
        production_length: 수율을 고려하여 변경된 해당 공정에 '투입되어야 하는' 길이. 이때 2공정의 투입길이 == 1공정의 완료길이 
        original_production_length: 수율 고려 이전 주문한 아이템의 길이
    """
    # 수율 정보 추가
    sequence_seperated_order_yield = sequence_seperated_order.merge(yield_data, on = [config.columns.GITEM, config.columns.OPERATION_CODE], how = 'left')

    # item과 process_sequence로 정렬
    sequence_seperated_order_yield = sequence_seperated_order_yield.sort_values([config.columns.GITEM, config.columns.OPERATION_ORDER]).reset_index(drop=True)

    # item별로 그룹화하여 투입 비율 계산
    sequence_seperated_order_yield = sequence_seperated_order_yield.groupby(config.columns.GITEM, group_keys=False).apply(calculate_input_ratio)

    sequence_seperated_order_yield.rename(columns = { config.columns.PRODUCTION_LENGTH: config.columns.ORIGINAL_PRODUCTION_LENGTH}, inplace = True)
    sequence_seperated_order_yield[config.columns.PRODUCTION_LENGTH] = sequence_seperated_order_yield[config.columns.ORIGINAL_PRODUCTION_LENGTH] * sequence_seperated_order_yield[config.columns.PRODUCT_RATIO]
    sequence_seperated_order_yield.drop(columns = {config.columns.YIELD, config.columns.PRODUCT_RATIO}, inplace = True)

    # 결과 길이를 10의 자리에서 반올림
    sequence_seperated_order_yield[config.columns.PRODUCTION_LENGTH] = (sequence_seperated_order_yield[config.columns.PRODUCTION_LENGTH].round(-1).astype(int)
)

    return sequence_seperated_order_yield


def calculate_input_ratio(group):
    """
    공정별 수율을 고려한 투입 비율을 계산합니다.

    역순으로 누적 곱을 계산하여 각 공정에서 필요한 투입량 비율을 산출합니다.

    Args:
        group: 같은 item으로 그룹화된 DataFrame

    Returns:
        input_ratio 컬럼이 추가된 DataFrame
    """
    yields = group[config.columns.YIELD].values
    num_processes = len(yields)
    ratios = [1] * num_processes

    accumulator = 1

    # 역순으로 진행하며 누적 곱을 계산
    for i in range(num_processes - 1, -1, -1):
        accumulator *= 1 / yields[i] * 100
        ratios[i] = accumulator

    group[config.columns.PRODUCT_RATIO] = ratios
    return group
