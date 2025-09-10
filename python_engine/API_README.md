# Production Scheduling API Server

제조업 공정 스케줄링 시스템을 위한 FastAPI 백엔드 서버입니다.

## 🚀 주요 기능

- **단계별 독립 API**: 각 스케줄링 단계를 독립적으로 실행할 수 있는 API 엔드포인트
- **외부 API 연동**: 외부 시스템에서 데이터를 가져와서 스케줄링에 활용
- **세션 관리**: 각 스케줄링 작업을 세션 단위로 관리
- **RESTful API**: 표준 HTTP 메서드를 사용한 RESTful API 설계
- **자동 문서화**: Swagger UI와 ReDoc을 통한 API 문서 자동 생성

## 📋 API 엔드포인트

### 기본 엔드포인트

- `GET /` - 루트 엔드포인트
- `GET /health` - 헬스 체크
- `GET /docs` - Swagger UI 문서
- `GET /redoc` - ReDoc 문서

### 1단계: 데이터 로딩

- `POST /api/v1/stage1/load-data` - 직접 데이터 로딩
- `POST /api/v1/stage1/load-external-data` - 외부 API에서 데이터 로딩

### 2단계: 전처리

- `POST /api/v1/stage2/preprocessing` - 주문 데이터 전처리

### 3단계: 수율 예측

- `POST /api/v1/stage3/yield-prediction` - 수율 예측

### 4단계: DAG 생성

- `POST /api/v1/stage4/dag-creation` - DAG 시스템 생성

### 5단계: 스케줄링

- `POST /api/v1/stage5/scheduling` - 스케줄링 실행

### 6단계: 결과 후처리

- `POST /api/v1/stage6/results` - 결과 후처리

### 전체 파이프라인

- `POST /api/v1/full-scheduling` - 전체 스케줄링 파이프라인 실행

### 세션 관리

- `GET /api/v1/session/{session_id}/status` - 세션 상태 조회
- `DELETE /api/v1/session/{session_id}` - 세션 데이터 삭제

## 🛠️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
# 개발 모드
python run_server.py

# 또는 직접 실행
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Docker 실행

```bash
# Docker 이미지 빌드
docker build -t scheduling-api .

# Docker 컨테이너 실행
docker run -p 8000:8000 scheduling-api

# 또는 Docker Compose 사용
docker-compose up -d
```

## 📖 사용 예시

### 1. 외부 API를 통한 데이터 로딩

```python
import httpx

# 1단계: 외부 API에서 데이터 로딩
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/stage1/load-external-data",
        json={
            "api_config": {
                "base_url": "https://your-external-api.com",
                "api_key": "your-api-key",
                "use_mock": False
            }
        }
    )
    
    session_id = response.json()["session_id"]
    print(f"세션 ID: {session_id}")
```

### 2. 단계별 스케줄링 실행

```python
# 2단계: 전처리
response = await client.post(
    "http://localhost:8000/api/v1/stage2/preprocessing",
    json={"session_id": session_id}
)

# 3단계: 수율 예측
response = await client.post(
    "http://localhost:8000/api/v1/stage3/yield-prediction",
    json={"session_id": session_id}
)

# 4단계: DAG 생성
response = await client.post(
    "http://localhost:8000/api/v1/stage4/dag-creation",
    json={"session_id": session_id}
)

# 5단계: 스케줄링
response = await client.post(
    "http://localhost:8000/api/v1/stage5/scheduling",
    json={
        "session_id": session_id,
        "window_days": 5
    }
)

# 6단계: 결과 후처리
response = await client.post(
    "http://localhost:8000/api/v1/stage6/results",
    json={"session_id": session_id}
)
```

### 3. 전체 파이프라인 실행

```python
# 전체 스케줄링 파이프라인 실행
response = await client.post(
    "http://localhost:8000/api/v1/full-scheduling",
    json={
        "data": {
            # Stage1DataRequest 데이터
        },
        "window_days": 5
    }
)
```

## 🧪 테스트

### API 테스트 실행

```bash
python test_api_client.py
```

### 개별 테스트

```python
from test_api_client import APITestClient

client = APITestClient("http://localhost:8000")
await client.test_full_pipeline()
```

## ⚙️ 설정

### 환경 변수

- `HOST`: 서버 호스트 (기본값: 0.0.0.0)
- `PORT`: 서버 포트 (기본값: 8000)
- `RELOAD`: 자동 재로드 (기본값: true)
- `LOG_LEVEL`: 로그 레벨 (기본값: info)
- `ENVIRONMENT`: 환경 (development/production/testing)
- `EXTERNAL_API_BASE_URL`: 외부 API 기본 URL
- `EXTERNAL_API_KEY`: 외부 API 키
- `USE_MOCK_API`: Mock API 사용 여부 (기본값: true)

### 설정 파일

`api_config.py`에서 환경별 설정을 관리할 수 있습니다.

## 📊 데이터 구조

### 입력 데이터 (Stage1DataRequest)

```json
{
  "linespeed": [...],
  "operation_sequence": [...],
  "machine_master_info": [...],
  "yield_data": [...],
  "gitem_operation": [...],
  "operation_types": [...],
  "operation_delay": [...],
  "width_change": [...],
  "machine_rest": [...],
  "machine_allocate": [...],
  "machine_limit": [...],
  "order_data": [...]
}
```

### 응답 데이터

각 단계별로 적절한 응답 데이터를 반환합니다:

- **Stage1Response**: 데이터 로딩 결과 및 세션 ID
- **Stage2Response**: 전처리 결과 및 처리된 작업 수
- **Stage3Response**: 수율 예측 완료 여부
- **Stage4Response**: DAG 생성 결과 및 노드/기계 수
- **Stage5Response**: 스케줄링 결과 및 Makespan 정보
- **Stage6Response**: 결과 후처리 및 지각 정보

## 🔧 개발

### 코드 구조

```
python_engine/
├── api_server.py          # FastAPI 메인 애플리케이션
├── run_server.py          # 서버 실행 스크립트
├── api_config.py          # 설정 관리
├── test_api_client.py     # API 테스트 클라이언트
├── src/
│   ├── external_api_client.py  # 외부 API 클라이언트
│   └── ...                # 기존 모듈들
└── requirements.txt       # 의존성 목록
```

### 새로운 엔드포인트 추가

1. `api_server.py`에 새로운 엔드포인트 함수 추가
2. Pydantic 모델 정의 (요청/응답)
3. 테스트 케이스 추가
4. 문서 업데이트

## 🚨 주의사항

- 현재 세션 데이터는 메모리에 저장되므로 서버 재시작 시 데이터가 손실됩니다
- 운영 환경에서는 Redis 등의 외부 저장소 사용을 권장합니다
- 대용량 데이터 처리 시 메모리 사용량을 모니터링하세요
- 외부 API 호출 시 타임아웃 설정을 적절히 조정하세요

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
