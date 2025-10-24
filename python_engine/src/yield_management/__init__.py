import pandas as pd
from config import config

def yield_prediction(yield_data, sequence_seperated_order):
    """
    yield 계산 전 과정을 한 번에 수행하는 편리 함수.
    - 전처리
    - 공정별 예측 수율 계산
    - 시퀀스별 수율 예측
    - 수율 매핑에 따른 생산길이 조정 반환
    """
    sequence_seperated_order[config.columns.GITEM] = sequence_seperated_order[config.columns.GITEM].astype(int).astype(str)
    yield_data[config.columns.GITEM] = yield_data[config.columns.GITEM].astype(int).astype(str)
    
    
    sequence_seperated_order_yield = pd.merge(sequence_seperated_order, yield_data, on = config.columns.GITEM, how = 'left')
    sequence_seperated_order_yield['product_ratio'] = 100 / sequence_seperated_order_yield['yield']
    sequence_seperated_order_yield.rename(columns = {"production_length" : "original_production_length"}, inplace = True)
    sequence_seperated_order_yield['production_length'] = sequence_seperated_order_yield['original_production_length'] * sequence_seperated_order_yield['product_ratio']
    sequence_seperated_order_yield.drop(columns = {'yield', 'product_ratio'}, inplace = True)
    sequence_seperated_order_yield
    
    return sequence_seperated_order_yield

    # yp = YieldPredictor(yield_data)
    # yp.preprocessing()
    # yp.calculate_predicted_yield()
    # result_df = yp.predict_sequence_yield(operation_sequence)

    # # 수율 매핑 및 생산길이 조정
    # adjusted_sequence_order = yp.adjust_production_length(sequence_seperated_order)

    # return yp, result_df, adjusted_sequence_order
