# Production Scheduling System API

제조업 생산 스케줄링 시스템의 FastAPI 서버입니다.

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
cd python-server
pip install -r requirements.txt
```

### 2. 환경 설정
```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집 (필요시)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# API_HOST=0.0.0.0
# API_PORT=8000
```

### 3. Redis 서버 실행
```bash
# Redis 서버가 실행 중인지 확인
redis-cli ping
```

### 4. 서버 실행
```bash
python run.py
```

### 5. API 문서 확인
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📋 API 엔드포인트

### 1단계: 데이터 검증
- `POST /api/v1/validation/` - 데이터 검증 실행
- `GET /api/v1/validation/{session_id}` - 검증 결과 조회

### 2단계: 전처리
- `POST /api/v1/preprocessing/` - 데이터 전처리 실행
- `GET /api/v1/preprocessing/{session_id}` - 전처리 결과 조회

### 3단계: 수율 예측
- `POST /api/v1/yield-prediction/` - 수율 예측 실행
- `GET /api/v1/yield-prediction/{session_id}` - 수율 예측 결과 조회

### 4단계: DAG 생성
- `POST /api/v1/dag-creation/` - DAG 생성 실행
- `GET /api/v1/dag-creation/{session_id}` - DAG 생성 결과 조회

### 5단계: 스케줄링
- `POST /api/v1/scheduling/` - 스케줄링 실행
- `GET /api/v1/scheduling/{session_id}` - 스케줄링 결과 조회

### 6단계: 결과 처리
- `POST /api/v1/results/` - 결과 처리 실행
- `GET /api/v1/results/{session_id}` - 결과 처리 데이터 조회

### 상태 관리
- `GET /api/v1/status/health` - 서비스 헬스 체크
- `GET /api/v1/status/{session_id}` - 세션 상태 조회
- `DELETE /api/v1/status/{session_id}` - 세션 데이터 삭제

## 🔧 사용 방법

### 1. 세션 생성 및 데이터 검증
```bash
curl -X POST "http://localhost:8000/api/v1/validation/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001",
    "order_data": [...],
    "machine_data": [...],
    "operation_data": [...],
    "constraint_data": [...]
  }'
```

### 2. 전처리 실행
```bash
curl -X POST "http://localhost:8000/api/v1/preprocessing/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001",
    "window_days": 5
  }'
```

### 3. 수율 예측 실행
```bash
curl -X POST "http://localhost:8000/api/v1/yield-prediction/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001"
  }'
```

### 4. DAG 생성 실행
```bash
curl -X POST "http://localhost:8000/api/v1/dag-creation/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001"
  }'
```

### 5. 스케줄링 실행
```bash
curl -X POST "http://localhost:8000/api/v1/scheduling/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001",
    "window_days": 5
  }'
```

### 6. 결과 처리 실행
```bash
curl -X POST "http://localhost:8000/api/v1/results/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001"
  }'
```

### 7. 세션 상태 조회
```bash
curl -X GET "http://localhost:8000/api/v1/status/test-session-001"
```

## 🏗️ 아키텍처

```
python-server/
├── app/
│   ├── api/                    # API 엔드포인트
│   │   ├── validation.py       # 1단계: 데이터 검증
│   │   ├── preprocessing.py    # 2단계: 전처리
│   │   ├── yield_prediction.py # 3단계: 수율 예측
│   │   ├── dag_creation.py     # 4단계: DAG 생성
│   │   ├── scheduling.py       # 5단계: 스케줄링
│   │   ├── results.py          # 6단계: 결과 처리
│   │   └── status.py           # 상태 관리
│   ├── core/                   # 핵심 설정
│   │   ├── config.py           # 설정 관리
│   │   └── redis_manager.py    # Redis 상태 관리
│   ├── models/                 # 데이터 모델
│   │   └── schemas.py          # Pydantic 스키마
│   ├── services/               # 비즈니스 로직
│   │   └── python_engine_service.py # Python Engine 연동
│   └── main.py                 # FastAPI 메인 앱
├── requirements.txt            # 의존성
├── env.example                 # 환경 변수 예시
├── run.py                      # 서버 실행 스크립트
└── README.md                   # 문서
```

## 🔄 데이터 흐름

1. **프론트엔드** → **Node.js** → **FastAPI** → **Python Engine** → **Redis**
2. 각 단계별로 독립적인 API 엔드포인트 제공
3. Redis를 통한 단계별 상태 관리 및 데이터 저장
4. 이전 단계 완료 후 다음 단계 실행 가능

## ⚙️ 설정

### 환경 변수
- `REDIS_HOST`: Redis 서버 호스트 (기본값: localhost)
- `REDIS_PORT`: Redis 서버 포트 (기본값: 6379)
- `REDIS_DB`: Redis 데이터베이스 번호 (기본값: 0)
- `API_HOST`: API 서버 호스트 (기본값: 0.0.0.0)
- `API_PORT`: API 서버 포트 (기본값: 8000)
- `API_DEBUG`: 디버그 모드 (기본값: True)
- `PYTHON_ENGINE_PATH`: Python Engine 경로 (기본값: ../python_engine)

## 🐛 문제 해결

### Redis 연결 실패
```bash
# Redis 서버 상태 확인
redis-cli ping

# Redis 서버 시작 (Ubuntu/Debian)
sudo systemctl start redis

# Redis 서버 시작 (macOS)
brew services start redis
```

### Python Engine 모듈 import 실패
- `PYTHON_ENGINE_PATH` 환경 변수가 올바른 경로를 가리키는지 확인
- Python Engine의 의존성이 설치되어 있는지 확인

### 포트 충돌
- `API_PORT` 환경 변수를 다른 포트로 변경
- 사용 중인 포트 확인: `netstat -tulpn | grep :8000`


