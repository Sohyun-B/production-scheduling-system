"""
Production Scheduling API Server
FastAPI 기반 제조업 공정 스케줄링 시스템 API 서버
"""

import pandas as pd
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 기존 모듈들 import
from src.preprocessing import preprocessing
from src.yield_management import yield_prediction
from src.dag_management import create_complete_dag_system
from src.scheduler.scheduling_core import DispatchPriorityStrategy
from src.results import create_results
from src.external_api_client import ExternalAPIClient, MockExternalAPIClient, load_data_from_external_api
from src.redis_session_manager import get_session_manager, init_session_manager
from api_config import get_config

# 설정 로드
config_settings = get_config()

app = FastAPI(
    title="Production Scheduling API",
    description="""
    제조업 공정 스케줄링을 위한 FastAPI 서버입니다.
    
    ## 주요 기능
    - 6단계 스케줄링 파이프라인
    - Redis 기반 세션 관리
    - 외부 API 연동
    - 실시간 진행 상황 추적
    
    ## 스케줄링 단계
    1. **데이터 로딩**: JSON 데이터를 DataFrame으로 변환
    2. **전처리**: 주문 데이터를 공정별로 분리
    3. **수율 예측**: 생산 수율을 예측하고 조정
    4. **DAG 생성**: 공정 간 의존성 관계 구축
    5. **스케줄링 실행**: 최적의 생산 일정 생성
    6. **결과 후처리**: 스케줄링 결과 분석 및 정리
    """,
    version="1.0.0",
    contact={
        "name": "Production Scheduling Team",
        "email": "scheduling@company.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "서버 상태 확인 및 헬스 체크"
        },
        {
            "name": "stage1",
            "description": "1단계: 데이터 로딩 (JSON → DataFrame 변환)"
        },
        {
            "name": "stage2", 
            "description": "2단계: 전처리 (주문 데이터 공정별 분리)"
        },
        {
            "name": "stage3",
            "description": "3단계: 수율 예측 (생산 수율 계산 및 조정)"
        },
        {
            "name": "stage4",
            "description": "4단계: DAG 생성 (공정 간 의존성 관계 구축)"
        },
        {
            "name": "stage5",
            "description": "5단계: 스케줄링 실행 (최적 일정 생성)"
        },
        {
            "name": "stage6",
            "description": "6단계: 결과 후처리 (분석 및 정리)"
        },
        {
            "name": "session",
            "description": "세션 관리 (Redis 기반 상태 저장)"
        }
    ]
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=config_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis 세션 매니저 초기화 (Redis 없이 테스트용)
try:
    session_manager = init_session_manager(
        redis_url=config_settings.REDIS_URL or "redis://localhost:6379/0",
        session_timeout=config_settings.SESSION_TIMEOUT
    )
    print("✅ Redis 세션 매니저 초기화 완료")
except Exception as e:
    print(f"⚠️ Redis 연결 실패, 메모리 기반 세션 관리 사용: {e}")
    # 메모리 기반 세션 관리 (임시)
    session_manager = None

# 전역 executor 변수
executor = ThreadPoolExecutor(max_workers=2)  # 스케줄링 전용 스레드 풀

# =============================================================================
# Pydantic 모델 정의
# =============================================================================

class Stage1DataRequest(BaseModel):
    """
    1단계: 외부 API에서 받을 데이터 구조
    """
    linespeed: List[Dict[str, Any]] = Field(..., description="품목별 라인스피드 데이터")
    operation_sequence: List[Dict[str, Any]] = Field(..., description="공정 순서 데이터")
    machine_master_info: List[Dict[str, Any]] = Field(..., description="기계 마스터 정보")
    yield_data: List[Dict[str, Any]] = Field(..., description="수율 데이터")
    gitem_operation: List[Dict[str, Any]] = Field(..., description="GITEM별 공정 데이터")
    operation_types: List[Dict[str, Any]] = Field(..., description="공정 분류 데이터")
    operation_delay: List[Dict[str, Any]] = Field(..., description="공정 지연 데이터")
    width_change: List[Dict[str, Any]] = Field(..., description="폭 변경 데이터")
    machine_rest: List[Dict[str, Any]] = Field(..., description="기계 휴식 데이터")
    machine_allocate: List[Dict[str, Any]] = Field(..., description="기계 할당 데이터")
    machine_limit: List[Dict[str, Any]] = Field(..., description="기계 제한 데이터")
    order_data: List[Dict[str, Any]] = Field(..., description="주문 데이터")

class Stage1Response(BaseModel):
    """
    1단계 응답 데이터
    """
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="처리 결과 메시지")
    data_summary: Dict[str, Any] = Field(..., description="데이터 요약 정보")

class ExternalAPIConfig(BaseModel):
    """
    외부 API 설정
    """
    base_url: str = Field(..., description="외부 API 기본 URL")
    api_key: Optional[str] = Field(None, description="API 키 (선택사항)")
    use_mock: bool = Field(False, description="Mock API 사용 여부")

class Stage2Request(BaseModel):
    """
    2단계 요청 데이터
    """
    session_id: str = Field(..., description="세션 ID")

class Stage2Response(BaseModel):
    """
    2단계 응답 데이터
    """
    message: str = Field(..., description="처리 결과 메시지")
    processed_jobs: int = Field(..., description="처리된 작업 수")
    machine_constraints: Dict[str, Any] = Field(..., description="기계 제약사항")

class Stage3Request(BaseModel):
    """
    3단계 요청 데이터
    """
    session_id: str = Field(..., description="세션 ID")

class Stage3Response(BaseModel):
    """
    3단계 응답 데이터
    """
    message: str = Field(..., description="처리 결과 메시지")
    yield_predictions: int = Field(..., description="수율 예측 수")

class Stage4Request(BaseModel):
    """
    4단계 요청 데이터
    """
    session_id: str = Field(..., description="세션 ID")

class Stage4Response(BaseModel):
    """
    4단계 응답 데이터
    """
    message: str = Field(..., description="처리 결과 메시지")
    dag_nodes: int = Field(..., description="DAG 노드 수")
    machines: int = Field(..., description="기계 수")

class Stage5Request(BaseModel):
    """
    5단계 요청 데이터
    """
    session_id: str = Field(..., description="세션 ID")
    window_days: int = Field(5, description="스케줄링 윈도우 일수")

class Stage5Response(BaseModel):
    """
    5단계 응답 데이터
    """
    message: str = Field(..., description="처리 결과 메시지")
    scheduled_jobs: int = Field(..., description="스케줄링된 작업 수")
    makespan: float = Field(..., description="Makespan (시간)")

class Stage6Request(BaseModel):
    """
    6단계 요청 데이터
    """
    session_id: str = Field(..., description="세션 ID")

class Stage6Response(BaseModel):
    """
    6단계 응답 데이터
    """
    message: str = Field(..., description="처리 결과 메시지")
    late_orders: int = Field(..., description="지각 주문 수")
    results_summary: Dict[str, Any] = Field(..., description="결과 요약")

class FullSchedulingRequest(BaseModel):
    """
    전체 스케줄링 요청 데이터
    """
    data: Stage1DataRequest = Field(..., description="스케줄링 데이터")
    window_days: int = Field(5, description="스케줄링 윈도우 일수")

class FullSchedulingResponse(BaseModel):
    """
    전체 스케줄링 응답 데이터
    """
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="처리 결과 메시지")
    results: Dict[str, Any] = Field(..., description="전체 결과")

# =============================================================================
# 유틸리티 함수
# =============================================================================

def save_stage_data(session_id: str, stage: str, data: Dict[str, Any]):
    """단계별 데이터 저장 (Redis)"""
    if session_manager:
        success = session_manager.save_stage_data(session_id, stage, data)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to save stage {stage} data")
    else:
        # 메모리 기반 저장 (임시)
        if not hasattr(save_stage_data, '_memory_store'):
            save_stage_data._memory_store = {}
        if session_id not in save_stage_data._memory_store:
            save_stage_data._memory_store[session_id] = {}
        save_stage_data._memory_store[session_id][stage] = data

def run_scheduling_sync(session_id: str, window_days: int) -> Dict[str, Any]:
    """동기적으로 스케줄링을 실행하는 함수 (스레드에서 실행)"""
    try:
        print(f"🔄 동기 스케줄링 시작 - 세션 ID: {session_id}")
        
        # 1단계 데이터 로드
        stage1_data = load_stage_data(session_id, "stage1")
        dataframes = stage1_data["dataframes"]
        
        # 2단계 데이터 로드
        stage2_data = load_stage_data(session_id, "stage2")
        sequence_seperated_order = stage2_data["sequence_seperated_order"]
        
        # 4단계 데이터 로드
        stage4_data = load_stage_data(session_id, "stage4")
        dag_df = stage4_data["dag_df"]
        opnode_dict = stage4_data["opnode_dict"]
        manager = stage4_data["manager"]
        machine_dict = stage4_data["machine_dict"]
        
        # 스케줄링 실행
        from src.scheduler.delay_dict import DelayProcessor
        from src.scheduler.scheduler import Scheduler
        from src.scheduler.dispatch_rules import create_dispatch_rule
        from src.scheduler.scheduling_core import DispatchPriorityStrategy
        
        # 디스패치 룰 생성
        dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
        
        # 지연 처리기 초기화
        delay_processor = DelayProcessor(
            opnode_dict,
            dataframes['operation_delay'],
            dataframes['width_change']
        )
        
        # 스케줄러 초기화
        scheduler = Scheduler(machine_dict, delay_processor)
        
        # 스케줄링 전략 설정
        strategy = DispatchPriorityStrategy()
        
        # 스케줄링 실행
        result = strategy.execute(
            dag_manager=manager,
            scheduler=scheduler,
            dag_df=dag_df,
            priority_order=dispatch_rule_ans,
            window_days=window_days,
            sequence_seperated_order=sequence_seperated_order
        )
        
        # 5단계 데이터 저장
        stage5_data = {
            "result": result,
            "scheduler": scheduler,
            "delay_processor": delay_processor,
            "dispatch_rule": dispatch_rule_ans,
            "completed_at": datetime.now().isoformat()
        }
        
        save_stage_data(session_id, "stage5", stage5_data)
        
        print(f"✅ 동기 스케줄링 완료 - 세션 ID: {session_id}")
        return {
            "success": True,
            "scheduled_jobs": len(result) if hasattr(result, '__len__') else 0,
            "makespan": result.max() if hasattr(result, 'max') else 0
        }
        
    except Exception as e:
        print(f"❌ 동기 스케줄링 실패 - 세션 ID: {session_id}, 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def load_stage_data(session_id: str, stage: str) -> Dict[str, Any]:
    """단계별 데이터 로드 (Redis)"""
    if session_manager:
        try:
            return session_manager.load_stage_data(session_id, stage)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
    else:
        # 메모리 기반 로드 (임시)
        if not hasattr(load_stage_data, '_memory_store'):
            load_stage_data._memory_store = {}
        if session_id not in load_stage_data._memory_store:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        if stage not in load_stage_data._memory_store[session_id]:
            raise HTTPException(status_code=404, detail=f"Stage {stage} not found for session {session_id}")
        return load_stage_data._memory_store[session_id][stage]

def convert_json_to_dataframes(data: Stage1DataRequest) -> Dict[str, pd.DataFrame]:
    """JSON 데이터를 DataFrame으로 변환"""
    dataframes = {}
    
    # 각 데이터를 DataFrame으로 변환
    dataframes['linespeed'] = pd.DataFrame(data.linespeed)
    dataframes['operation_sequence'] = pd.DataFrame(data.operation_sequence)
    dataframes['machine_master_info'] = pd.DataFrame(data.machine_master_info)
    dataframes['yield_data'] = pd.DataFrame(data.yield_data)
    dataframes['gitem_operation'] = pd.DataFrame(data.gitem_operation)
    dataframes['operation_types'] = pd.DataFrame(data.operation_types)
    dataframes['operation_delay'] = pd.DataFrame(data.operation_delay)
    dataframes['width_change'] = pd.DataFrame(data.width_change)
    dataframes['machine_rest'] = pd.DataFrame(data.machine_rest)
    dataframes['machine_allocate'] = pd.DataFrame(data.machine_allocate)
    dataframes['machine_limit'] = pd.DataFrame(data.machine_limit)
    dataframes['order_data'] = pd.DataFrame(data.order_data)
    
    # 날짜 컬럼 변환 (더 강화된 변환)
    print("🔄 날짜 컬럼 변환 시작...")
    
    # order_data의 날짜 컬럼들
    if '납기일' in dataframes['order_data'].columns:
        print(f"📅 납기일 컬럼 변환: {dataframes['order_data']['납기일'].dtype}")
        dataframes['order_data']['납기일'] = pd.to_datetime(dataframes['order_data']['납기일'], errors='coerce')
        print(f"✅ 납기일 변환 완료: {dataframes['order_data']['납기일'].dtype}")
    
    # machine_rest의 날짜 컬럼들
    if '시작시간' in dataframes['machine_rest'].columns:
        print(f"📅 시작시간 컬럼 변환: {dataframes['machine_rest']['시작시간'].dtype}")
        dataframes['machine_rest']['시작시간'] = pd.to_datetime(dataframes['machine_rest']['시작시간'], errors='coerce')
        print(f"✅ 시작시간 변환 완료: {dataframes['machine_rest']['시작시간'].dtype}")
        
    if '종료시간' in dataframes['machine_rest'].columns:
        print(f"📅 종료시간 컬럼 변환: {dataframes['machine_rest']['종료시간'].dtype}")
        dataframes['machine_rest']['종료시간'] = pd.to_datetime(dataframes['machine_rest']['종료시간'], errors='coerce')
        print(f"✅ 종료시간 변환 완료: {dataframes['machine_rest']['종료시간'].dtype}")
    
    print("✅ 모든 날짜 컬럼 변환 완료")
    
    return dataframes

def check_stage_completion(session_id: str, required_stages: List[str]) -> bool:
    """필요한 단계들이 완료되었는지 확인"""
    if session_manager:
        try:
            status = session_manager.get_session_status(session_id)
            completed = status.get('completed_stages', [])
            return all(stage in completed for stage in required_stages)
        except:
            return False
    else:
        # 메모리 기반 확인 (임시)
        if not hasattr(check_stage_completion, '_memory_store'):
            check_stage_completion._memory_store = {}
        if session_id not in check_stage_completion._memory_store:
            return False
        completed = list(check_stage_completion._memory_store[session_id].keys())
        return all(stage in completed for stage in required_stages)

# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/", tags=["health"])
async def root():
    """
    ## 루트 엔드포인트
    
    API 서버의 기본 정보를 반환합니다.
    
    ### 응답
    - **message**: API 서버 상태 메시지
    - **version**: API 버전
    - **docs**: API 문서 URL
    """
    return {
        "message": "Production Scheduling API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running"
    }

@app.get("/health", tags=["health"])
async def health_check():
    """
    ## 헬스 체크
    
    서버의 현재 상태를 확인합니다.
    
    ### 응답
    - **status**: 서버 상태
    - **timestamp**: 현재 시간
    - **redis**: Redis 연결 상태
    """
    redis_status = "connected" if session_manager and session_manager.health_check() else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis": redis_status,
        "version": "1.0.0"
    }

@app.post("/api/v1/stage1/load-data", response_model=Stage1Response, tags=["stage1"])
async def load_data(request: Stage1DataRequest):
    """
    ## 1단계: 직접 데이터 로딩
    
    JSON 형태의 스케줄링 데이터를 받아서 DataFrame으로 변환하고 저장합니다.
    
    ### 요청 데이터
    - **linespeed**: 품목별 라인스피드 데이터
    - **operation_sequence**: 공정 순서 데이터
    - **machine_master_info**: 기계 마스터 정보
    - **yield_data**: 수율 데이터
    - **gitem_operation**: GITEM별 공정 데이터
    - **operation_types**: 공정 분류 데이터
    - **operation_delay**: 공정 지연 데이터
    - **width_change**: 폭 변경 데이터
    - **machine_rest**: 기계 휴식 데이터
    - **machine_allocate**: 기계 할당 데이터
    - **machine_limit**: 기계 제한 데이터
    - **order_data**: 주문 데이터
    
    ### 응답
    - **session_id**: 생성된 세션 ID
    - **message**: 처리 결과 메시지
    - **data_summary**: 데이터 요약 정보
    
    ### 사용 예시
    ```python
    import httpx
    
    data = {
        "linespeed": [...],
        "operation_sequence": [...],
        # ... 기타 데이터
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage1/load-data",
            json=data
        )
        result = response.json()
        print(f"세션 ID: {result['session_id']}")
    ```
    """
    try:
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        
        # JSON 데이터를 DataFrame으로 변환
        dataframes = convert_json_to_dataframes(request)
        
        # 데이터 요약 정보 생성
        data_summary = {
            "linespeed_count": len(dataframes['linespeed']),
            "machine_count": len(dataframes['machine_master_info']),
            "total_orders": len(dataframes['order_data']),
            "operation_count": len(dataframes['operation_sequence']),
            "yield_data_count": len(dataframes['yield_data'])
        }
        
        # 1단계 데이터 저장
        stage1_data = {
            "dataframes": dataframes,
            "data_summary": data_summary,
            "timestamp": datetime.now().isoformat()
        }
        
        save_stage_data(session_id, "stage1", stage1_data)
        
        return Stage1Response(
            session_id=session_id,
            message="데이터 로딩 완료",
            data_summary=data_summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 로딩 실패: {str(e)}")

@app.post("/api/v1/stage1/load-external-data", response_model=Stage1Response, tags=["stage1"])
async def load_external_data(api_config: ExternalAPIConfig):
    """
    ## 1단계: 외부 API에서 데이터 로딩
    
    외부 API에서 스케줄링 데이터를 가져와서 처리합니다.
    
    ### 요청 데이터
    - **base_url**: 외부 API 기본 URL
    - **api_key**: API 키 (선택사항)
    - **use_mock**: Mock API 사용 여부
    
    ### 응답
    - **session_id**: 생성된 세션 ID
    - **message**: 처리 결과 메시지
    - **data_summary**: 데이터 요약 정보
    
    ### 사용 예시
    ```python
    import httpx
    
    config = {
        "base_url": "http://api.example.com",
        "api_key": "your-api-key",
        "use_mock": False
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage1/load-external-data",
            json=config
        )
        result = response.json()
        print(f"세션 ID: {result['session_id']}")
    ```
    """
    try:
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        
        # 외부 API에서 데이터 로딩
        if api_config.use_mock:
            client = MockExternalAPIClient()
        else:
            client = ExternalAPIClient(api_config.base_url, api_config.api_key)
        
        data = await load_data_from_external_api(client)
        
        # JSON 데이터를 DataFrame으로 변환
        dataframes = convert_json_to_dataframes(Stage1DataRequest(**data))
        
        # 데이터 요약 정보 생성
        data_summary = {
            "linespeed_count": len(dataframes['linespeed']),
            "machine_count": len(dataframes['machine_master_info']),
            "total_orders": len(dataframes['order_data']),
            "operation_count": len(dataframes['operation_sequence']),
            "yield_data_count": len(dataframes['yield_data']),
            "source": "external_api"
        }
        
        # 1단계 데이터 저장
        stage1_data = {
            "dataframes": dataframes,
            "data_summary": data_summary,
            "timestamp": datetime.now().isoformat(),
            "api_config": api_config.dict()
        }
        
        save_stage_data(session_id, "stage1", stage1_data)
        
        return Stage1Response(
            session_id=session_id,
            message="외부 데이터 로딩 완료",
            data_summary=data_summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"외부 데이터 로딩 실패: {str(e)}")

@app.post("/api/v1/stage2/preprocessing", response_model=Stage2Response, tags=["stage2"])
async def preprocessing_stage(request: Stage2Request):
    """
    ## 2단계: 전처리
    
    주문 데이터를 공정별로 분리하고 기계 제약사항을 적용합니다.
    
    ### 요청 데이터
    - **session_id**: 세션 ID
    
    ### 응답
    - **message**: 처리 결과 메시지
    - **processed_jobs**: 처리된 작업 수
    - **machine_constraints**: 기계 제약사항
    
    ### 처리 과정
    1. 주문 데이터를 공정별로 분리
    2. 기계 제약사항 적용
    3. 작업 순서 생성
    4. 결과 저장
    
    ### 사용 예시
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage2/preprocessing",
            json={"session_id": "your-session-id"}
        )
        result = response.json()
        print(f"처리된 작업: {result['processed_jobs']}개")
    ```
    """
    try:
        print(f"🔍 2단계 전처리 시작 - 세션 ID: {request.session_id}")
        
        # 1단계 데이터 로드
        stage1_data = load_stage_data(request.session_id, "stage1")
        dataframes = stage1_data["dataframes"]
        print(f"✅ 1단계 데이터 로드 완료 - 데이터프레임 키: {list(dataframes.keys())}")
        
        # 데이터프레임 정보 출력
        for key, df in dataframes.items():
            print(f"📊 {key}: {df.shape} - 컬럼: {list(df.columns)}")
        
        # 날짜 컬럼 변환 (2단계에서 추가)
        print("🔄 날짜 컬럼 변환 시작...")
        
        # order_data의 날짜 컬럼들
        if '납기일' in dataframes['order_data'].columns:
            print(f"📅 납기일 컬럼 변환: {dataframes['order_data']['납기일'].dtype}")
            dataframes['order_data']['납기일'] = pd.to_datetime(dataframes['order_data']['납기일'], errors='coerce')
            print(f"✅ 납기일 변환 완료: {dataframes['order_data']['납기일'].dtype}")
        
        # machine_rest의 날짜 컬럼들
        if '시작시간' in dataframes['machine_rest'].columns:
            print(f"📅 machine_rest 시작시간 컬럼 변환: {dataframes['machine_rest']['시작시간'].dtype}")
            dataframes['machine_rest']['시작시간'] = pd.to_datetime(dataframes['machine_rest']['시작시간'], errors='coerce')
            print(f"✅ machine_rest 시작시간 변환 완료: {dataframes['machine_rest']['시작시간'].dtype}")
            
        if '종료시간' in dataframes['machine_rest'].columns:
            print(f"📅 machine_rest 종료시간 컬럼 변환: {dataframes['machine_rest']['종료시간'].dtype}")
            dataframes['machine_rest']['종료시간'] = pd.to_datetime(dataframes['machine_rest']['종료시간'], errors='coerce')
            print(f"✅ machine_rest 종료시간 변환 완료: {dataframes['machine_rest']['종료시간'].dtype}")
        
        # machine_limit의 날짜 컬럼들
        if '시작시간' in dataframes['machine_limit'].columns:
            print(f"📅 machine_limit 시작시간 컬럼 변환: {dataframes['machine_limit']['시작시간'].dtype}")
            dataframes['machine_limit']['시작시간'] = pd.to_datetime(dataframes['machine_limit']['시작시간'], errors='coerce')
            print(f"✅ machine_limit 시작시간 변환 완료: {dataframes['machine_limit']['시작시간'].dtype}")
            
        if '종료시간' in dataframes['machine_limit'].columns:
            print(f"📅 machine_limit 종료시간 컬럼 변환: {dataframes['machine_limit']['종료시간'].dtype}")
            dataframes['machine_limit']['종료시간'] = pd.to_datetime(dataframes['machine_limit']['종료시간'], errors='coerce')
            print(f"✅ machine_limit 종료시간 변환 완료: {dataframes['machine_limit']['종료시간'].dtype}")
        
        print("✅ 모든 날짜 컬럼 변환 완료")
        
        # 전처리 실행
        print("🔄 전처리 함수 호출 시작...")
        
        # gitem_operation과 operation_sequence 병합 (공정순서 컬럼 추가)
        print("🔄 gitem_operation과 operation_sequence 병합 중...")
        merged_operation = dataframes['gitem_operation'].merge(
            dataframes['operation_sequence'][['공정명', '공정순서']], 
            on='공정명', 
            how='left'
        )
        print(f"✅ 병합 완료 - 컬럼: {list(merged_operation.columns)}")
        
        # machine_limit에 기계코드 컬럼 추가
        print("🔄 machine_limit에 기계코드 컬럼 추가 중...")
        machine_limit_with_code = dataframes['machine_limit'].merge(
            dataframes['machine_master_info'][['기계인덱스', '기계코드']], 
            on='기계인덱스', 
            how='left'
        )
        print(f"✅ machine_limit 병합 완료 - 컬럼: {list(machine_limit_with_code.columns)}")
        
        # machine_allocate에 기계코드 컬럼 추가
        print("🔄 machine_allocate에 기계코드 컬럼 추가 중...")
        machine_allocate_with_code = dataframes['machine_allocate'].merge(
            dataframes['machine_master_info'][['기계인덱스', '기계코드']], 
            on='기계인덱스', 
            how='left'
        )
        print(f"✅ machine_allocate 병합 완료 - 컬럼: {list(machine_allocate_with_code.columns)}")
        
        # 전처리 함수에 전달할 데이터 확인
        print(f"📊 order_data 컬럼: {list(dataframes['order_data'].columns)}")
        print(f"📊 merged_operation 컬럼: {list(merged_operation.columns)}")
        print(f"📊 operation_types 컬럼: {list(dataframes['operation_types'].columns)}")
        print(f"📊 machine_limit_with_code 컬럼: {list(machine_limit_with_code.columns)}")
        print(f"📊 machine_allocate_with_code 컬럼: {list(machine_allocate_with_code.columns)}")
        print(f"📊 linespeed 컬럼: {list(dataframes['linespeed'].columns)}")
        
        try:
            sequence_seperated_order, linespeed = preprocessing(
                dataframes['order_data'],
                merged_operation,  # 병합된 operation 데이터 사용
                dataframes['operation_types'],
                machine_limit_with_code,  # 기계코드가 추가된 machine_limit 사용
                machine_allocate_with_code,  # 기계코드가 추가된 machine_allocate 사용
                dataframes['linespeed']
            )
            print(f"✅ 전처리 완료 - 결과: {len(sequence_seperated_order)}개 작업")
        except Exception as e:
            print(f"❌ 전처리 함수 내부 오류: {str(e)}")
            print(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            raise e
        
        # 2단계 데이터 저장
        stage2_data = {
            "sequence_seperated_order": sequence_seperated_order,
            "linespeed": linespeed,
            "machine_constraints": {
                "machine_rest": dataframes['machine_rest'].to_dict('records'),
                "machine_allocate": dataframes['machine_allocate'].to_dict('records'),
                "machine_limit": dataframes['machine_limit'].to_dict('records')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        save_stage_data(request.session_id, "stage2", stage2_data)
        
        return Stage2Response(
            message="전처리 완료",
            processed_jobs=len(sequence_seperated_order),
            machine_constraints=stage2_data["machine_constraints"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전처리 실패: {str(e)}")

@app.post("/api/v1/stage3/yield-prediction", response_model=Stage3Response, tags=["stage3"])
async def yield_prediction_stage(request: Stage3Request):
    """
    ## 3단계: 수율 예측
    
    생산 수율을 예측하고 작업 데이터에 적용합니다.
    
    ### 요청 데이터
    - **session_id**: 세션 ID
    
    ### 응답
    - **message**: 처리 결과 메시지
    - **yield_predictions**: 수율 예측 수
    
    ### 처리 과정
    1. 수율 데이터 분석
    2. GITEM별 공정별 수율 예측
    3. 작업 데이터에 수율 적용
    4. 결과 저장
    
    ### 사용 예시
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage3/yield-prediction",
            json={"session_id": "your-session-id"}
        )
        result = response.json()
        print(f"수율 예측: {result['yield_predictions']}개")
    ```
    """
    try:
        # 1단계 데이터 로드
        stage1_data = load_stage_data(request.session_id, "stage1")
        dataframes = stage1_data["dataframes"]
        
        # 2단계 데이터 로드
        stage2_data = load_stage_data(request.session_id, "stage2")
        sequence_seperated_order = stage2_data["sequence_seperated_order"]
        
        # 수율 예측 실행
        print("🔄 수율 예측 함수 호출 시작...")
        print(f"📊 yield_data 컬럼: {list(dataframes['yield_data'].columns)}")
        print(f"📊 gitem_operation 컬럼: {list(dataframes['gitem_operation'].columns)}")
        print(f"📊 sequence_seperated_order 컬럼: {list(sequence_seperated_order.columns)}")
        
        try:
            yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(
                dataframes['yield_data'],
                dataframes['gitem_operation'],
                sequence_seperated_order
            )
            print(f"✅ 수율 예측 완료 - sequence_yield_df: {type(sequence_yield_df)}")
            if sequence_yield_df is not None:
                print(f"📊 sequence_yield_df 길이: {len(sequence_yield_df)}")
            else:
                print("❌ sequence_yield_df가 None입니다!")
        except Exception as e:
            print(f"❌ 수율 예측 함수 내부 오류: {str(e)}")
            print(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            raise e
        
        # 3단계 데이터 저장
        stage3_data = {
            "yield_predictor": yield_predictor,
            "sequence_yield_df": sequence_yield_df,
            "sequence_seperated_order": sequence_seperated_order,
            "timestamp": datetime.now().isoformat()
        }
        
        save_stage_data(request.session_id, "stage3", stage3_data)
        
        return Stage3Response(
            message="수율 예측 완료",
            yield_predictions=len(sequence_yield_df)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수율 예측 실패: {str(e)}")

@app.post("/api/v1/stage4/dag-creation", response_model=Stage4Response, tags=["stage4"])
async def dag_creation_stage(request: Stage4Request):
    """
    ## 4단계: DAG 생성
    
    공정 간 의존성 관계를 구축하고 DAG 시스템을 생성합니다.
    
    ### 요청 데이터
    - **session_id**: 세션 ID
    
    ### 응답
    - **message**: 처리 결과 메시지
    - **dag_nodes**: DAG 노드 수
    - **machines**: 기계 수
    
    ### 처리 과정
    1. DAG 데이터프레임 생성
    2. 노드 딕셔너리 구축
    3. DAG 관리자 초기화
    4. 기계 딕셔너리 생성
    5. 결과 저장
    
    ### 사용 예시
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage4/dag-creation",
            json={"session_id": "your-session-id"}
        )
        result = response.json()
        print(f"DAG 노드: {result['dag_nodes']}개, 기계: {result['machines']}개")
    ```
    """
    try:
        # 1단계 데이터 로드
        stage1_data = load_stage_data(request.session_id, "stage1")
        dataframes = stage1_data["dataframes"]
        
        # 3단계 데이터 로드
        stage3_data = load_stage_data(request.session_id, "stage3")
        sequence_seperated_order = stage3_data["sequence_seperated_order"]
        
        # DAG 생성 실행
        print("🔄 DAG 생성 함수 호출 시작...")
        print(f"📊 sequence_seperated_order 컬럼: {list(sequence_seperated_order.columns)}")
        print(f"📊 sequence_seperated_order 샘플:")
        print(sequence_seperated_order.head())
        
        from config import Config
        config = Config()
        
        try:
            dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
                sequence_seperated_order,
                dataframes['linespeed'],
                dataframes['machine_master_info'],
                config
            )
            print(f"✅ DAG 생성 완료 - dag_df: {type(dag_df)}")
            if dag_df is not None:
                print(f"📊 dag_df 길이: {len(dag_df)}")
            else:
                print("❌ dag_df가 None입니다!")
        except Exception as e:
            print(f"❌ DAG 생성 함수 내부 오류: {str(e)}")
            print(f"❌ 오류 타입: {type(e).__name__}")
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            raise e
        
        # 4단계 데이터 저장
        stage4_data = {
            "dag_df": dag_df,
            "opnode_dict": opnode_dict,
            "manager": manager,
            "machine_dict": machine_dict,
            "merged_df": merged_df,
            "timestamp": datetime.now().isoformat()
        }
        
        save_stage_data(request.session_id, "stage4", stage4_data)
        
        return Stage4Response(
            message="DAG 생성 완료",
            dag_nodes=len(dag_df),
            machines=len(machine_dict)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DAG 생성 실패: {str(e)}")

@app.post("/api/v1/stage5/scheduling", response_model=Stage5Response, tags=["stage5"])
async def scheduling_stage(request: Stage5Request):
    """
    ## 5단계: 스케줄링 실행
    
    최적의 생산 일정을 생성합니다.
    
    ### 요청 데이터
    - **session_id**: 세션 ID
    - **window_days**: 스케줄링 윈도우 일수 (기본값: 5)
    
    ### 응답
    - **message**: 처리 결과 메시지
    - **scheduled_jobs**: 스케줄링된 작업 수
    - **makespan**: Makespan (시간)
    
    ### 처리 과정
    1. 디스패치 규칙 생성
    2. 스케줄러 초기화
    3. 스케줄링 실행
    4. 결과 저장
    
    ### 사용 예시
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage5/scheduling",
            json={
                "session_id": "your-session-id",
                "window_days": 7
            }
        )
        result = response.json()
        print(f"스케줄링된 작업: {result['scheduled_jobs']}개")
    ```
    """
    try:
        print(f"🔍 5단계 스케줄링 시작 (비동기) - 세션 ID: {request.session_id}")
        
        # 백그라운드에서 스케줄링 실행
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            executor, 
            run_scheduling_sync, 
            request.session_id, 
            request.window_days
        )
        
        # 즉시 응답 반환
        return Stage5Response(
            message="스케줄링이 백그라운드에서 시작되었습니다. 완료 후 세션에서 결과를 확인하세요.",
            scheduled_jobs=0,
            makespan=0
        )
        
    except Exception as e:
        print(f"❌ 스케줄링 시작 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스케줄링 시작 실패: {str(e)}"
        )

@app.get("/api/v1/stage5/status/{session_id}", tags=["stage5"])
async def get_scheduling_status(session_id: str):
    """
    ## 5단계: 스케줄링 상태 확인
    
    현재 스케줄링 진행 상태를 확인합니다.
    
    ### 응답
    - **status**: 스케줄링 상태 (running, completed, failed)
    - **message**: 상태 메시지
    - **scheduled_jobs**: 스케줄링된 작업 수 (완료 시)
    - **makespan**: Makespan (완료 시)
    """
    try:
        # 5단계 데이터 확인
        try:
            stage5_data = load_stage_data(session_id, "stage5")
            return {
                "status": "completed",
                "message": "스케줄링이 완료되었습니다.",
                "scheduled_jobs": len(stage5_data.get("result", [])),
                "makespan": stage5_data.get("actual_makespan", 0),
                "completed_at": stage5_data.get("completed_at")
            }
        except KeyError:
            return {
                "status": "running",
                "message": "스케줄링이 진행 중입니다.",
                "scheduled_jobs": 0,
                "makespan": 0
            }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"상태 확인 실패: {str(e)}",
            "scheduled_jobs": 0,
            "makespan": 0
        }

@app.post("/api/v1/stage6/results", response_model=Stage6Response, tags=["stage6"])
async def results_stage(request: Stage6Request):
    """
    ## 6단계: 결과 후처리
    
    스케줄링 결과를 분석하고 정리합니다.
    
    ### 요청 데이터
    - **session_id**: 세션 ID
    
    ### 응답
    - **message**: 처리 결과 메시지
    - **late_orders**: 지각 주문 수
    - **results_summary**: 결과 요약
    
    ### 처리 과정
    1. 지각 주문 계산
    2. 결과 병합
    3. 기계 스케줄 생성
    4. 간격 분석
    5. 최종 결과 저장
    
    ### 사용 예시
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/stage6/results",
            json={"session_id": "your-session-id"}
        )
        result = response.json()
        print(f"지각 주문: {result['late_orders']}개")
    ```
    """
    try:
        # 1단계 데이터 로드
        stage1_data = load_stage_data(request.session_id, "stage1")
        dataframes = stage1_data["dataframes"]
        
        # 2단계 데이터 로드
        stage2_data = load_stage_data(request.session_id, "stage2")
        sequence_seperated_order = stage2_data["sequence_seperated_order"]
        
        # 4단계 데이터 로드
        stage4_data = load_stage_data(request.session_id, "stage4")
        merged_df = stage4_data["merged_df"]
        
        # 5단계 데이터 로드
        stage5_data = load_stage_data(request.session_id, "stage5")
        result = stage5_data["result"]
        scheduler = stage5_data["scheduler"]
        
        # 결과 후처리 실행
        # 기계 스케줄 데이터프레임 생성 (스케줄러에서)
        machine_schedule_df = scheduler.create_machine_schedule_dataframe() if hasattr(scheduler, 'create_machine_schedule_dataframe') else pd.DataFrame()
        
        # 기계 매핑 생성
        machine_mapping = {i: f"기계{i}" for i in range(len(scheduler.machine_dict))}
        
        # 기준 날짜 설정 (현재 시간)
        base_date = datetime.now()
        
        results = create_results(
            result,
            merged_df,
            dataframes['order_data'],
            sequence_seperated_order,
            machine_mapping,
            machine_schedule_df,
            base_date,
            scheduler
        )
        
        # 6단계 데이터 저장
        stage6_data = {
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        save_stage_data(request.session_id, "stage6", stage6_data)
        
        return Stage6Response(
            message="결과 후처리 완료",
            late_orders=results.get('late_days_sum', 0),
            results_summary={
                "total_jobs": len(results.get('new_output_final_result', [])),
                "late_orders": results.get('late_days_sum', 0),
                "machine_count": len(results.get('machine_info', []))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 후처리 실패: {str(e)}")

@app.post("/api/v1/full-scheduling", response_model=FullSchedulingResponse, tags=["stage1"])
async def full_scheduling(request: FullSchedulingRequest):
    """
    ## 전체 스케줄링 파이프라인
    
    모든 단계를 순차적으로 실행합니다.
    
    ### 요청 데이터
    - **data**: 스케줄링 데이터
    - **window_days**: 스케줄링 윈도우 일수 (기본값: 5)
    
    ### 응답
    - **session_id**: 생성된 세션 ID
    - **message**: 처리 결과 메시지
    - **results**: 전체 결과
    
    ### 처리 과정
    1. 1단계: 데이터 로딩
    2. 2단계: 전처리
    3. 3단계: 수율 예측
    4. 4단계: DAG 생성
    5. 5단계: 스케줄링 실행
    6. 6단계: 결과 후처리
    
    ### 사용 예시
    ```python
    import httpx
    
    data = {
        "data": {
            "linespeed": [...],
            "operation_sequence": [...],
            # ... 기타 데이터
        },
        "window_days": 7
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/full-scheduling",
            json=data
        )
        result = response.json()
        print(f"세션 ID: {result['session_id']}")
    ```
    """
    try:
        # 1단계: 데이터 로딩
        stage1_response = await load_data(request.data)
        session_id = stage1_response.session_id
        
        # 2단계: 전처리
        stage2_response = await preprocessing_stage(Stage2Request(session_id=session_id))
        
        # 3단계: 수율 예측
        stage3_response = await yield_prediction_stage(Stage3Request(session_id=session_id))
        
        # 4단계: DAG 생성
        stage4_response = await dag_creation_stage(Stage4Request(session_id=session_id))
        
        # 5단계: 스케줄링 실행
        stage5_response = await scheduling_stage(Stage5Request(session_id=session_id, window_days=request.window_days))
        
        # 6단계: 결과 후처리
        stage6_response = await results_stage(Stage6Request(session_id=session_id))
        
        # 전체 결과 수집
        results = {
            "stage1": stage1_response.dict(),
            "stage2": stage2_response.dict(),
            "stage3": stage3_response.dict(),
            "stage4": stage4_response.dict(),
            "stage5": stage5_response.dict(),
            "stage6": stage6_response.dict()
        }
        
        return FullSchedulingResponse(
            session_id=session_id,
            message="전체 스케줄링 완료",
            results=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 스케줄링 실패: {str(e)}")

@app.get("/api/v1/session/{session_id}/status", tags=["session"])
async def get_session_status(session_id: str):
    """
    ## 세션 상태 조회
    
    특정 세션의 현재 상태와 완료된 단계를 확인합니다.
    
    ### 경로 매개변수
    - **session_id**: 조회할 세션 ID
    
    ### 응답
    - **session_id**: 세션 ID
    - **completed_stages**: 완료된 단계 목록
    - **total_stages**: 전체 단계 수 (6)
    - **created_at**: 세션 생성 시간
    - **last_updated**: 마지막 업데이트 시간
    
    ### 사용 예시
    ```python
    import httpx
    
    session_id = "your-session-id"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/session/{session_id}/status"
        )
        result = response.json()
        print(f"완료된 단계: {result['completed_stages']}")
        print(f"전체 단계: {result['total_stages']}")
    ```
    """
    try:
        if session_manager:
            return session_manager.get_session_status(session_id)
        else:
            # 메모리 기반 상태 조회 (임시)
            if not hasattr(get_session_status, '_memory_store'):
                get_session_status._memory_store = {}
            if session_id not in get_session_status._memory_store:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
            completed_stages = list(get_session_status._memory_store[session_id].keys())
            return {
                "session_id": session_id,
                "completed_stages": completed_stages,
                "total_stages": 6,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/v1/session/{session_id}", tags=["session"])
async def clear_session(session_id: str):
    """
    ## 세션 데이터 삭제
    
    특정 세션의 모든 데이터를 삭제합니다.
    
    ### 경로 매개변수
    - **session_id**: 삭제할 세션 ID
    
    ### 응답
    - **message**: 삭제 결과 메시지
    
    ### 사용 예시
    ```python
    import httpx
    
    session_id = "your-session-id"
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:8000/api/v1/session/{session_id}"
        )
        result = response.json()
        print(result["message"])
    ```
    
    ### 주의사항
    - 삭제된 세션의 데이터는 복구할 수 없습니다
    - 해당 세션 ID로는 더 이상 API를 호출할 수 없습니다
    """
    if session_manager:
        success = session_manager.clear_session(session_id)
        if success:
            return {"message": f"Session {session_id} cleared"}
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    else:
        # 메모리 기반 삭제 (임시)
        if not hasattr(clear_session, '_memory_store'):
            clear_session._memory_store = {}
        if session_id in clear_session._memory_store:
            del clear_session._memory_store[session_id]
            return {"message": f"Session {session_id} cleared"}
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
