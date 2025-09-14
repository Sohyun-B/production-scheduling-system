"""
1단계: 데이터 검증 API (Node.js에서 데이터 전달)
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import ValidationRequest, ValidationResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager

router = APIRouter(prefix="/api/v1/validation-with-data", tags=["validation-with-data"])


@router.post("/", response_model=ValidationResponse)
async def validate_data_with_data(request: dict):
    """
    1단계: 데이터 검증 (Node.js에서 로드된 데이터 사용)
    
    Node.js에서 JSON 파일을 읽어서 전달받은 데이터를 검증합니다.
    """
    try:
        session_id = request.get("session_id")
        window_days = request.get("window_days", 5)
        base_date = request.get("base_date")
        yield_period = request.get("yield_period", 6)
        loaded_data = request.get("loaded_data", {})
        stats = request.get("stats", {})
        load_results = request.get("load_results", {})
        
        logger.info(f"데이터 검증 시작 (Node.js 데이터): {session_id}")
        
        # Node.js에서 로드된 데이터 검증 (python_engine_service 사용)
        validation_result = python_engine_service.validate_loaded_data(
            loaded_data=loaded_data,
            session_id=session_id,
            window_days=window_days,
            base_date=base_date,
            yield_period=yield_period
        )
        
        # 로드 결과 정보 추가
        validation_result["loaded_files"] = load_results
        
        # Redis에 검증 결과와 로드된 데이터 저장
        stage_data = {
            "stage": "validation",
            "session_id": session_id,
            "validation_result": validation_result,
            "loaded_data": loaded_data,
            "stats": stats
        }
        
        success = redis_manager.save_stage_data(
            session_id=session_id,
            stage="validation",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"데이터 검증 완료 (Node.js 데이터): {session_id}")
        
        return ValidationResponse(
            success=True,
            message="데이터 검증이 완료되었습니다.",
            data={
                "total_orders": stats.get("total_orders", 0),
                "total_linespeed": stats.get("total_linespeed", 0),
                "total_machines": stats.get("total_machines", 0),
                "total_operation_types": stats.get("total_operation_types", 0),
                "total_yield_data": stats.get("total_yield_data", 0),
                "total_gitem_operation": stats.get("total_gitem_operation", 0),
                "loaded_files": stats.get("success_files_count", 0),
                "total_files": stats.get("loaded_files_count", 0),
                "validation_status": validation_result["validation_status"]
            }
        )
        
    except HTTPException:
        raise
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
        
        stats = data.get("stats", {})
        
        return ValidationResponse(
            success=True,
            message="검증 결과를 조회했습니다.",
            data={
                "total_orders": stats.get("total_orders", 0),
                "total_linespeed": stats.get("total_linespeed", 0),
                "total_machines": stats.get("total_machines", 0),
                "total_operation_types": stats.get("total_operation_types", 0),
                "total_yield_data": stats.get("total_yield_data", 0),
                "total_gitem_operation": stats.get("total_gitem_operation", 0),
                "loaded_files": stats.get("success_files_count", 0),
                "total_files": stats.get("loaded_files_count", 0),
                "validation_status": data.get("validation_result", {}).get("validation_status", "unknown")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검증 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


