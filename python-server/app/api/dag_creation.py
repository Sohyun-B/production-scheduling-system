"""
4단계: DAG 생성 API
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
from app.models.schemas import DAGCreationRequest, DAGCreationResponse
from app.services.python_engine_service import python_engine_service
from app.core.redis_manager import redis_manager

router = APIRouter(prefix="/api/v1/dag-creation", tags=["dag-creation"])


@router.post("/", response_model=DAGCreationResponse)
async def run_dag_creation(request: DAGCreationRequest):
    """
    4단계: DAG 생성
    
    공정 간 의존성을 DAG(방향성 비순환 그래프)로 모델링합니다.
    """
    try:
        logger.info(f"DAG 생성 시작: {request.session_id}")
        
        # 이전 단계 데이터 조회
        preprocessing_data = redis_manager.get_stage_data(request.session_id, "preprocessing")
        if preprocessing_data is None:
            raise HTTPException(status_code=400, detail="먼저 전처리를 완료해주세요.")
        
        validation_data = redis_manager.get_stage_data(request.session_id, "validation")
        if validation_data is None:
            raise HTTPException(status_code=400, detail="먼저 데이터 검증을 완료해주세요.")
        
        # 필요한 데이터 추출 (Redis에서)
        sequence_seperated_order = preprocessing_data.get("sequence_seperated_order", [])
        linespeed = preprocessing_data.get("linespeed", [])
        loaded_data = validation_data.get("loaded_data", {})
        
        # sequence_seperated_order가 비어있으면 전처리 데이터에서 다시 가져오기
        if not sequence_seperated_order:
            sequence_seperated_order = preprocessing_data.get("processed_data", {}).get("sequence_seperated_order", [])
        
        # DAG 생성 실행 (main.py와 동일한 함수 호출)
        dag_df, opnode_dict, manager, machine_dict, merged_df = python_engine_service.run_dag_creation(
            sequence_seperated_order=sequence_seperated_order,
            linespeed=linespeed,
            machine_master_info=loaded_data.get("machine_master_info", [])
        )
        
        # 결과를 직렬화 가능한 형태로 변환
        dag_df_dict = dag_df.to_dict('records') if hasattr(dag_df, 'to_dict') else dag_df
        merged_df_dict = merged_df.to_dict('records') if hasattr(merged_df, 'to_dict') else merged_df
        
        # sequence_seperated_order를 직렬화 가능한 형태로 변환
        sequence_seperated_order_dict = sequence_seperated_order.to_dict('records') if hasattr(sequence_seperated_order, 'to_dict') else sequence_seperated_order
        
        # opnode_dict와 machine_dict를 직렬화 가능한 형태로 변환
        # opnode_dict는 딕셔너리이므로 그대로 저장
        opnode_dict_serializable = dict(opnode_dict) if opnode_dict else {}
        
        # machine_dict도 딕셔너리이므로 그대로 저장
        machine_dict_serializable = dict(machine_dict) if machine_dict else {}
        
        # manager 객체를 pickle로 직렬화하여 저장
        import pickle
        import base64
        manager_serializable = base64.b64encode(pickle.dumps(manager)).decode('utf-8') if manager else None
        
        # DAG 생성에서 사용한 sequence_seperated_order를 저장 (데이터 일관성 보장)
        dag_sequence_seperated_order_dict = sequence_seperated_order.to_dict('records') if hasattr(sequence_seperated_order, 'to_dict') else sequence_seperated_order
        
        # Redis에 DAG 생성 결과 저장
        stage_data = {
            "stage": "dag_creation",
            "session_id": request.session_id,
            "dag_df": dag_df_dict,
            "merged_df": merged_df_dict,
            "sequence_seperated_order": sequence_seperated_order_dict,  # 원본 데이터
            "dag_sequence_seperated_order": dag_sequence_seperated_order_dict,  # DAG 생성에서 사용한 데이터
            "opnode_dict": opnode_dict_serializable,
            "machine_dict": machine_dict_serializable,
            "manager": manager_serializable,
            "node_count": len(dag_df) if hasattr(dag_df, '__len__') else 0,
            "machine_count": len(machine_dict) if hasattr(machine_dict, '__len__') else 0,
            "dag_creation_completed": True
        }
        
        success = redis_manager.save_stage_data(
            session_id=request.session_id,
            stage="dag_creation",
            data=stage_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Redis 저장 실패")
        
        logger.info(f"DAG 생성 완료: {request.session_id}")
        
        return DAGCreationResponse(
            success=True,
            message="DAG 생성이 완료되었습니다.",
            data={
                "dag_creation_completed": True,
                "node_count": stage_data["node_count"],
                "machine_count": stage_data["machine_count"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DAG 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=DAGCreationResponse)
async def get_dag_creation_result(session_id: str):
    """
    DAG 생성 결과 조회
    """
    try:
        data = redis_manager.get_stage_data(session_id, "dag_creation")
        
        if data is None:
            raise HTTPException(status_code=404, detail="DAG 생성 결과를 찾을 수 없습니다.")
        
        return DAGCreationResponse(
            success=True,
            message="DAG 생성 결과를 조회했습니다.",
            data={
                "dag_creation_completed": data.get("dag_creation_completed", False),
                "node_count": data.get("node_count", 0),
                "machine_count": data.get("machine_count", 0)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DAG 생성 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

