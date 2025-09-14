"""
3단계: 수율 예측 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import YieldPredictionRequest, YieldPredictionResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager

router = APIRouter(prefix="/api/v1/yield-prediction", tags=["yield-prediction"])


@router.post("/", response_model=YieldPredictionResponse)
async def run_yield_prediction(request: YieldPredictionRequest):
    """
    3단계: 수율 예측
    
    과거 데이터를 기반으로 공정별 수율을 예측합니다.
    """
    try:
        logger.info(f"수율 예측 시작: {request.session_id}")
        
        # 이전 단계 데이터 조회
        preprocessing_data = redis_manager.get_stage_data(request.session_id, "preprocessing")
        if preprocessing_data is None:
            raise HTTPException(status_code=400, detail="먼저 전처리를 완료해주세요.")
        
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        # 필요한 데이터 추출 (Redis에서)
        sequence_seperated_order = preprocessing_data.get("sequence_seperated_order", [])
        loaded_data = validation_data.get("loaded_data", {})
        
        # 수율 예측 실행 (main.py와 동일한 함수 호출)
        yield_predictor, sequence_yield_df, adjusted_sequence_order = python_engine_service.run_yield_prediction(
            yield_data=loaded_data.get("yield_data", []),
            gitem_operation=loaded_data.get("gitem_operation", []),
            sequence_seperated_order=sequence_seperated_order
        )
        
        # 결과를 직렬화 가능한 형태로 변환
        sequence_yield_dict = sequence_yield_df.to_dict('records') if hasattr(sequence_yield_df, 'to_dict') else sequence_yield_df
        adjusted_sequence_dict = adjusted_sequence_order.to_dict('records') if hasattr(adjusted_sequence_order, 'to_dict') else adjusted_sequence_order
        
        # Redis에 수율 예측 결과 저장
        stage_data = {
            "stage": "yield_prediction",
            "session_id": request.session_id,
            "sequence_yield_df": sequence_yield_dict,
            "adjusted_sequence_order": adjusted_sequence_dict,
            "yield_prediction_completed": True
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="yield_prediction",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"수율 예측 완료: {request.session_id}")
        
        return YieldPredictionResponse(
            success=True,
            message="수율 예측이 완료되었습니다.",
            data={
                "yield_prediction_completed": True,
                "sequence_yield_count": len(sequence_yield_dict)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"수율 예측 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=YieldPredictionResponse)
async def get_yield_prediction_result(session_id: str):
    """
    수율 예측 결과 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "yield_prediction")
        
        if data is None:
            raise HTTPException(status_code=404, detail="수율 예측 결과를 찾을 수 없습니다.")
        
        return YieldPredictionResponse(
            success=True,
            message="수율 예측 결과를 조회했습니다.",
            data={
                "yield_prediction_completed": data.get("yield_prediction_completed", False),
                "sequence_yield_count": len(data.get("sequence_yield_df", []))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"수율 예측 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
