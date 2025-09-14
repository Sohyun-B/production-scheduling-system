"""
상태 조회 및 관리 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import StatusRequest, StatusResponse, HealthResponse
from app.core.redis_manager import redis_manager
from datetime import datetime

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    서비스 헬스 체크
    """
    try:
        redis_connected = redis_manager.health_check()
        
        return HealthResponse(
            status="healthy" if redis_connected else "unhealthy",
            timestamp=datetime.now(),
            redis_connected=redis_connected
        )
        
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            redis_connected=False
        )


@router.get("/{session_id}", response_model=StatusResponse)
async def get_session_status(session_id: str):
    """
    세션 상태 조회
    """
    try:
        # 모든 단계 데이터 조회
        all_stages = redis_manager.get_all_stages(session_id)
        
        # 단계별 완료 상태 확인
        stage_status = {}
        stages = ["validation", "preprocessing", "yield_prediction", 
                 "dag_creation", "scheduling", "results"]
        
        for stage in stages:
            if stage in all_stages:
                stage_data = all_stages[stage]
                stage_status[stage] = {
                    "completed": True,
                    "timestamp": stage_data.get("timestamp", None),
                    "data_available": True
                }
            else:
                stage_status[stage] = {
                    "completed": False,
                    "timestamp": None,
                    "data_available": False
                }
        
        # 전체 진행률 계산
        completed_stages = sum(1 for status in stage_status.values() if status["completed"])
        total_stages = len(stages)
        progress_percentage = (completed_stages / total_stages) * 100
        
        return StatusResponse(
            success=True,
            message="세션 상태를 조회했습니다.",
            data={
                "session_id": session_id,
                "progress_percentage": progress_percentage,
                "completed_stages": completed_stages,
                "total_stages": total_stages,
                "stage_status": stage_status,
                "all_stages_available": len(all_stages) > 0
            }
        )
        
    except Exception as e:
        logger.error(f"세션 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """
    세션 데이터 삭제
    """
    try:
        success = redis_manager.clear_session(session_id)
        
        if success:
            return {"success": True, "message": f"세션 {session_id}의 데이터가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="세션 데이터 삭제에 실패했습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 데이터 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

