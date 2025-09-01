from .yield_predictor import YieldPredictor

def yield_prediction(yield_data, operation_sequence):
    """
    yield 계산 전 과정을 한 번에 수행하는 편리 함수.
    - 전처리
    - 공정별 예측 수율 계산
    - 시퀀스별 수율 예측 및 결과 반환
    """
    yp = YieldPredictor(yield_data)
    yp.preprocessing()
    yp.calculate_predicted_yield()
    result_df = yp.predict_sequence_yield(operation_sequence)
    return yp, result_df


# 메인 코드
# from yield_management import run_full_yield_prediction
# yp, sequence_yield_df = run_full_yield_prediction(yield_data, operation_sequence)
# yield_map = sequence_seperated_order['GITEM'].map(yp.gitem_yield_dict).fillna(100)
