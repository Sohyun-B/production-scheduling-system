"""
1단계: 데이터 검증 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import ValidationRequest, ValidationResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.post("/", response_model=ValidationResponse)
async def validate_data(request: ValidationRequest):
    """
    1단계: 데이터 검증
    
    JSON 파일에서 데이터를 로드하고 유효성을 검증합니다.
    """
    try:
        logger.info(f"데이터 검증 시작: {request.session_id}")
        
        # JSON 파일에서 데이터 로드 (main.py와 동일한 방식)
        validation_result = python_engine_service.load_and_validate_data(
            session_id=request.session_id,
            window_days=request.window_days,
            base_date=request.base_date,
            yield_period=request.yield_period
        )
        
        # Redis에 검증 결과 저장
        stage_data = {
            "stage": "validation",
            "session_id": request.session_id,
            "validation_result": validation_result,
            "loaded_data": validation_result.get("loaded_data", {})
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="validation",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"데이터 검증 완료: {request.session_id}")
        
        return ValidationResponse(
            success=True,
            message="데이터 검증이 완료되었습니다.",
            data=validation_result
        )
        
    except Exception as e:
        logger.error(f"데이터 검증 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=ValidationResponse)
async def get_validation_result(session_id: str):
    """
    검증 결과 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "validation")
        
        if data is None:
            raise HTTPException(status_code=404, detail="검증 결과를 찾을 수 없습니다.")
        
        return ValidationResponse(
            success=True,
            message="검증 결과를 조회했습니다.",
            data=data.get("validation_result", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검증 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
