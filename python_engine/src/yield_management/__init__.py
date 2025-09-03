from .yield_predictor import YieldPredictor

def yield_prediction(yield_data, operation_sequence, sequence_seperated_order):
    """
    yield 계산 전 과정을 한 번에 수행하는 편리 함수.
    - 전처리
    - 공정별 예측 수율 계산
    - 시퀀스별 수율 예측
    - 수율 매핑에 따른 생산길이 조정 반환
    """
    yp = YieldPredictor(yield_data)
    yp.preprocessing()
    yp.calculate_predicted_yield()
    result_df = yp.predict_sequence_yield(operation_sequence)

    # 수율 매핑 및 생산길이 조정
    adjusted_sequence_order = yp.adjust_production_length(sequence_seperated_order)

    return yp, result_df, adjusted_sequence_order

