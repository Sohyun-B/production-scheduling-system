import pandas as pd
from config import config

def _yield_prediction(yield_data):
    """
    yield_data: gitemno, proccode, procseq 별 수율 (단위: %)
    그룹으로 묶어 투입 비율 계산


    """
    #  (gitem, 공정순서) 순으로 정렬
    yield_data = yield_data.sort_values([config.columns.GITEM, config.columns.OPERATION_ORDER]).reset_index(drop=True)

    # gitem 별로 그룹화하여 투입비율 계산
    yield_data = yield_data.groupby(config.columns.GITEM, group_keys=False).apply(calculate_input_ratio)

    yield_data.to_csv('yield_data.csv', encoding = 'utf-8-sig')

    # 재공품 직접 읽음
    # gitemno, length, completed_procseq, completed_proccode로 구성
    work_in_progress = pd.read_excel("data/input/재공품.xlsx", dtype={config.columns.GITEM: str})
    
    # 재공품이 완성품일 때의 길이 계산
    work_in_progress = work_in_progress
    return yield_data

def handle_work_in_progress(work_in_progress, yield_data):
    wip = work_in_progress.merge(yield_data, left_on = 'completed_proccode', right_on = 'proccode', how = 'left')



def yield_prediction(yield_data, sequence_seperated_order):
    """
    """
    # 1. 수율 기준정보에서 각 공정별 가중 product_ratio 구함
    yield_product_ratio = _yield_prediction(yield_data)

    # 2. sequence_seperated_order에 product_ratio 곱하여 각 공정의 투입 길이 도출
    sequence_seperated_order = sequence_seperated_order.merge(yield_product_ratio, on = [config.columns.GITEM, config.columns.OPERATION_CODE], how = 'left')

    # 3. work-in-progress 공정별 분리 후 

    return sequence_seperated_order


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
