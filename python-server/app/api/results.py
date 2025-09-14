"""
6단계: 결과 처리 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from datetime import datetime
from app.models.schemas import ResultsRequest, ResultsResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager
from app.core.config import settings

router = APIRouter(prefix="/api/v1/results", tags=["results"])


@router.post("/", response_model=ResultsResponse)
async def run_results_processing(request: ResultsRequest):
    """
    6단계: 결과 처리
    
    스케줄링 결과를 분석하고 가독성 있는 형태로 변환합니다.
    """
    try:
        logger.info(f"결과 처리 시작: {request.session_id}")
        
        # 이전 단계 데이터 조회
        scheduling_data = redis_manager.get_stage_data(request.session_id, "scheduling")
        if scheduling_data is None:
            raise HTTPException(status_code=400, detail="먼저 스케줄링을 완료해주세요.")
        
        dag_data = redis_manager.get_stage_data(request.session_id, "dag_creation")
        if dag_data is None:
            raise HTTPException(status_code=400, detail="먼저 DAG 생성을 완료해주세요.")
        
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        # 필요한 데이터 추출 (Redis에서)
        result = scheduling_data.get("result", [])
        merged_df = dag_data.get("merged_df", [])
        loaded_data = validation_data.get("loaded_data", {})
        
        # 기본 날짜 설정 (main.py와 동일)
        base_date = datetime(settings.base_year, settings.base_month, settings.base_day)
        
        # 결과 처리 실행 (main.py와 동일한 함수 호출)
        results = python_engine_service.run_results_processing(
            output_final_result=result,
            merged_df=merged_df,
            original_order=loaded_data.get("order", []),
            sequence_seperated_order=dag_data.get("sequence_seperated_order", []),
            machine_mapping={},  # 실제 구현에서는 machine_mapping 필요
            machine_schedule_df=scheduling_data.get("machine_schedule", []),
            base_date=base_date,
            scheduler=None  # 실제 구현에서는 scheduler 객체 필요
        )
        
        # 결과를 직렬화 가능한 형태로 변환
        results_dict = {}
        for key, value in results.items():
            if hasattr(value, 'to_dict'):
                results_dict[key] = value.to_dict('records')
            else:
                results_dict[key] = value
        
        # Redis에 결과 처리 데이터 저장
        stage_data = {
            "stage": "results",
            "session_id": request.session_id,
            "late_days_sum": results_dict.get("late_days_sum", 0),
            "late_products_count": len(results_dict.get("late_products", [])),
            "late_po_numbers": results_dict.get("late_po_numbers", []),
            "results": results_dict,
            "results_processing_completed": True
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="results",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"결과 처리 완료: {request.session_id}")
        
        return ResultsResponse(
            success=True,
            message="결과 처리가 완료되었습니다.",
            data={
                "results_processing_completed": True,
                "late_days_sum": stage_data["late_days_sum"],
                "late_products_count": stage_data["late_products_count"],
                "late_po_numbers": stage_data["late_po_numbers"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str):
    """
    결과 처리 데이터 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "results")
        
        if data is None:
            raise HTTPException(status_code=404, detail="결과 처리 데이터를 찾을 수 없습니다.")
        
        return ResultsResponse(
            success=True,
            message="결과 처리 데이터를 조회했습니다.",
            data={
                "results_processing_completed": data.get("results_processing_completed", False),
                "late_days_sum": data.get("late_days_sum", 0),
                "late_products_count": data.get("late_products_count", 0),
                "late_po_numbers": data.get("late_po_numbers", [])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 처리 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

