"""
5단계: 스케줄링 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from datetime import datetime
from app.models.schemas import SchedulingRequest, SchedulingResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager
from app.core.config import settings

router = APIRouter(prefix="/api/v1/scheduling", tags=["scheduling"])


@router.post("/full", response_model=SchedulingResponse)
async def run_full_scheduling(request: SchedulingRequest):
    """
    전체 스케줄링 프로세스 실행 (main.py와 동일한 방식)
    """
    try:
        logger.info(f"전체 스케줄링 시작: {request.session_id}")
        
        # validation 단계에서 로드된 원본 데이터 사용
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        loaded_data = validation_data.get("loaded_data", {})
        
        # 기본 날짜 설정 (main.py와 동일)
        base_date = datetime(settings.base_year, settings.base_month, settings.base_day)
        if base_date.tzinfo is not None:
            base_date = base_date.replace(tzinfo=None)
        
        # main.py와 동일한 방식으로 전체 프로세스 실행
        result, scheduler, machine_schedule_df = python_engine_service.run_full_scheduling(
            loaded_data=loaded_data,
            window_days=request.window_days,
            base_date=base_date
        )
        
        # 결과를 직렬화 가능한 형태로 변환
        result_dict = result.to_dict('records') if hasattr(result, 'to_dict') else result
        machine_schedule_dict = machine_schedule_df.to_dict('records') if hasattr(machine_schedule_df, 'to_dict') else machine_schedule_df
        
        # Makespan 계산
        actual_makespan = result['node_end'].max() if hasattr(result, 'node_end') else 0
        total_days = (actual_makespan * 0.5) / 24 if actual_makespan > 0 else 0
        
        logger.info(f"전체 스케줄링 완료: {request.session_id}")
        
        return SchedulingResponse(
            success=True,
            message="🎉 전체 스케줄링이 완료되었습니다!",
            data={
                "scheduling_completed": True,
                "total_jobs_scheduled": len(result) if hasattr(result, '__len__') else 0,
                "makespan": int(actual_makespan),
                "total_days": total_days,
                "late_jobs_count": 0,
                "late_days_sum": 0,
                "completion_message": "모든 단계가 성공적으로 완료되었습니다. 최적의 생산 스케줄이 생성되었습니다."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전체 스케줄링 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=SchedulingResponse)
async def run_scheduling(request: SchedulingRequest):
    """
    5단계: 스케줄링 실행
    
    DispatchPriorityStrategy를 사용하여 최적 생산 스케줄을 생성합니다.
    """
    try:
        logger.info(f"스케줄링 시작: {request.session_id}")
        
        # 이전 단계 데이터 조회
        dag_data = redis_manager.get_stage_data(request.session_id, "dag_creation")
        if dag_data is None:
            raise HTTPException(status_code=400, detail="먼저 DAG 생성을 완료해주세요.")
        
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        # 필요한 데이터 추출 (Redis에서)
        dag_df = dag_data.get("dag_df", [])
        merged_df = dag_data.get("merged_df", [])
        # DAG 생성에서 사용한 sequence_seperated_order 사용 (데이터 일관성 보장)
        sequence_seperated_order = dag_data.get("dag_sequence_seperated_order", dag_data.get("sequence_seperated_order", []))
        opnode_dict = dag_data.get("opnode_dict", {})
        machine_dict = dag_data.get("machine_dict", {})
        
        # manager 객체 역직렬화
        manager = None
        manager_serialized = dag_data.get("manager", None)
        if manager_serialized:
            try:
                import pickle
                import base64
                manager = pickle.loads(base64.b64decode(manager_serialized))
                logger.info("✅ DAG Manager 객체 역직렬화 성공")
            except Exception as e:
                logger.warning(f"DAG Manager 역직렬화 실패: {e}")
                manager = None
        
        # validation 단계에서 로드된 원본 데이터 사용 (Redis 저장/로딩 과정 우회)
        loaded_data = validation_data.get("loaded_data", {})
        
        # sequence_seperated_order가 비어있으면 전처리 데이터에서 가져오기
        if not sequence_seperated_order:
            preprocessing_data = redis_manager.get_stage_data(request.session_id, "preprocessing")
            if preprocessing_data:
                sequence_seperated_order = preprocessing_data.get("sequence_seperated_order", [])
        
        # 디버깅: 데이터 크기 확인
        logger.info(f"데이터 크기 확인:")
        logger.info(f"  - dag_df: {len(dag_df) if isinstance(dag_df, list) else 'DataFrame'}")
        logger.info(f"  - sequence_seperated_order: {len(sequence_seperated_order) if isinstance(sequence_seperated_order, list) else 'DataFrame'}")
        logger.info(f"  - loaded_data keys: {list(loaded_data.keys())}")
        logger.info(f"  - operation_delay_df: {len(loaded_data.get('operation_delay_df', []))}")
        logger.info(f"  - machine_rest: {len(loaded_data.get('machine_rest', []))}")
        
        # 기본 날짜 설정 (main.py와 동일, timezone-naive로 강제 설정)
        base_date = datetime(settings.base_year, settings.base_month, settings.base_day)
        # timezone 정보가 있다면 제거
        if base_date.tzinfo is not None:
            base_date = base_date.replace(tzinfo=None)
        
        # 스케줄링 실행 (main.py와 동일한 함수 호출)
        result, scheduler, machine_schedule_df = python_engine_service.run_scheduling(
            dag_manager=manager,  # DAG 매니저 객체 전달
            dag_df=dag_df,
            sequence_seperated_order=sequence_seperated_order,
            operation_delay_df=loaded_data.get("operation_delay_df", []),
            width_change_df=loaded_data.get("width_change_df", []),
            machine_rest=loaded_data.get("machine_rest", []),
            machine_dict=machine_dict,
            window_days=request.window_days,
            opnode_dict=opnode_dict,
            base_date=base_date  # base_date 명시적 전달
        )
        
        # 결과를 직렬화 가능한 형태로 변환
        result_dict = result.to_dict('records') if hasattr(result, 'to_dict') else result
        machine_schedule_dict = machine_schedule_df.to_dict('records') if hasattr(machine_schedule_df, 'to_dict') else machine_schedule_df
        
        # Makespan 계산
        actual_makespan = result['node_end'].max() if hasattr(result, 'node_end') else 0
        total_days = (actual_makespan * 0.5) / 24 if actual_makespan > 0 else 0
        
        # Redis에 스케줄링 결과 저장
        stage_data = {
            "stage": "scheduling",
            "session_id": request.session_id,
            "window_days_used": request.window_days,
            "makespan_slots": int(actual_makespan),
            "makespan_hours": actual_makespan * 0.5,
            "total_days": total_days,
            "processed_jobs_count": len(result) if hasattr(result, '__len__') else 0,
            "result": result_dict,
            "machine_schedule": machine_schedule_dict,
            "scheduling_completed": True
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="scheduling",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"스케줄링 완료: {request.session_id}")
        
        return SchedulingResponse(
            success=True,
            message="🎉 전체 스케줄링이 완료되었습니다!",
            data={
                "scheduling_completed": True,
                "total_jobs_scheduled": stage_data["processed_jobs_count"],
                "makespan": int(actual_makespan),
                "total_days": total_days,
                "late_jobs_count": 0,  # TODO: 실제 지각 작업 수 계산
                "late_days_sum": 0,    # TODO: 실제 지각 일수 계산
                "completion_message": "모든 단계가 성공적으로 완료되었습니다. 최적의 생산 스케줄이 생성되었습니다."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스케줄링 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SchedulingResponse)
async def get_scheduling_result(session_id: str):
    """
    스케줄링 결과 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "scheduling")
        
        if data is None:
            raise HTTPException(status_code=404, detail="스케줄링 결과를 찾을 수 없습니다.")
        
        return SchedulingResponse(
            success=True,
            message="스케줄링 결과를 조회했습니다.",
            data={
                "scheduling_completed": data.get("scheduling_completed", False),
                "makespan_slots": data.get("makespan_slots", 0),
                "total_days": data.get("total_days", 0),
                "processed_jobs_count": data.get("processed_jobs_count", 0)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스케줄링 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

