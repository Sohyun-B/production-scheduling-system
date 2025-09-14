"""
2단계: 전처리 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import PreprocessingRequest, PreprocessingResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager

router = APIRouter(prefix="/api/v1/preprocessing", tags=["preprocessing"])


@router.post("/", response_model=PreprocessingResponse)
async def run_preprocessing(request: PreprocessingRequest):
    """
    2단계: 데이터 전처리
    
    검증된 데이터를 스케줄링에 적합한 형태로 전처리합니다.
    """
    try:
        logger.info(f"전처리 시작: {request.session_id}")
        
        # 이전 단계 데이터 조회
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        # 검증 결과 확인
        validation_result = validation_data.get("validation_result", {})
        if validation_result.get("validation_status") == "error":
            raise HTTPException(status_code=400, detail="데이터 검증에 실패했습니다.")
        
        # 입력 데이터 추출 (validation에서 로드된 데이터)
        loaded_data = validation_data.get("loaded_data", {})
        if not loaded_data:
            raise HTTPException(status_code=400, detail="검증 단계에서 로드된 데이터를 찾을 수 없습니다.")
        
        # 데이터 로깅
        logger.info(f"로드된 데이터 키: {list(loaded_data.keys())}")
        logger.info(f"order_data 길이: {len(loaded_data.get('order', []))}")
        logger.info(f"operation_seperated_sequence 길이: {len(loaded_data.get('operation_seperated_sequence', []))}")
        logger.info(f"operation_types 길이: {len(loaded_data.get('operation_types', []))}")
        logger.info(f"machine_limit 길이: {len(loaded_data.get('machine_limit', []))}")
        logger.info(f"machine_allocate 길이: {len(loaded_data.get('machine_allocate', []))}")
        logger.info(f"linespeed 길이: {len(loaded_data.get('linespeed', []))}")
        
        # 전처리 실행 (main.py와 동일한 함수 호출)
        sequence_seperated_order, linespeed = python_engine_service.run_preprocessing(
            order_data=loaded_data["order"],  # main.py의 order 변수와 동일
            operation_data=loaded_data["operation_seperated_sequence"],
            operation_types=loaded_data["operation_types"],
            machine_limit=loaded_data["machine_limit"],
            machine_allocate=loaded_data["machine_allocate"],
            linespeed=loaded_data["linespeed"]
        )
        
        # 전처리 결과를 직렬화 가능한 형태로 변환
        sequence_seperated_order_dict = sequence_seperated_order.to_dict('records') if hasattr(sequence_seperated_order, 'to_dict') else sequence_seperated_order
        linespeed_dict = linespeed.to_dict('records') if hasattr(linespeed, 'to_dict') else linespeed
        
        # 원본 주문 데이터 통계
        original_orders = loaded_data.get("order", [])
        original_gitems = set()
        if original_orders:
            original_gitems = set([order.get('GITEM', '') for order in original_orders if order.get('GITEM')])
        
        # 처리된 작업 통계
        processed_jobs_count = len(sequence_seperated_order) if hasattr(sequence_seperated_order, '__len__') else 0
        processed_gitems = set()
        if hasattr(sequence_seperated_order, 'GITEM'):
            processed_gitems = set(sequence_seperated_order['GITEM'].unique())
        elif isinstance(sequence_seperated_order, list):
            processed_gitems = set([job.get('GITEM', '') for job in sequence_seperated_order if job.get('GITEM')])
        
        # 제외된 GITEM 계산
        excluded_gitems = original_gitems - processed_gitems
        excluded_count = len(excluded_gitems)
        
        # Redis에 전처리 결과 저장
        stage_data = {
            "stage": "preprocessing",
            "session_id": request.session_id,
            "window_days": request.window_days,
            "sequence_seperated_order": sequence_seperated_order_dict,
            "linespeed": linespeed_dict,
            "processed_jobs_count": processed_jobs_count,
            "original_orders_count": len(original_orders),
            "original_gitems_count": len(original_gitems),
            "processed_gitems_count": len(processed_gitems),
            "excluded_gitems_count": excluded_count,
            "excluded_gitems": list(excluded_gitems)
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="preprocessing",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"전처리 완료: {request.session_id}")
        
        return PreprocessingResponse(
            success=True,
            message="데이터 전처리가 완료되었습니다.",
            data={
                "processed_jobs_count": stage_data["processed_jobs_count"],
                "original_orders_count": stage_data["original_orders_count"],
                "original_gitems_count": stage_data["original_gitems_count"],
                "processed_gitems_count": stage_data["processed_gitems_count"],
                "excluded_gitems_count": stage_data["excluded_gitems_count"],
                "excluded_gitems": stage_data["excluded_gitems"],
                "window_days": request.window_days
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=PreprocessingResponse)
async def get_preprocessing_result(session_id: str):
    """
    전처리 결과 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "preprocessing")
        
        if data is None:
            raise HTTPException(status_code=404, detail="전처리 결과를 찾을 수 없습니다.")
        
        return PreprocessingResponse(
            success=True,
            message="전처리 결과를 조회했습니다.",
            data={
                "processed_jobs_count": data.get("processed_jobs_count", 0),
                "window_days": data.get("window_days", 5)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전처리 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
