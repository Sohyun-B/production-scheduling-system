# Production Scheduling Backend

Node.js 백엔드 서버로 프론트엔드에서 요청을 받아 Python FastAPI의 각 단계별 API에 요청을 보내고 결과를 전달하는 서버입니다.

## 🚀 주요 기능

- **전체 스케줄링 프로세스**: 6단계를 한 번에 실행
- **단계별 실행**: 각 단계를 개별적으로 실행
- **세션 관리**: Redis를 통한 상태 관리
- **에러 처리**: 상세한 에러 메시지와 로깅
- **데이터 검증**: Joi를 통한 요청 데이터 검증
- **Rate Limiting**: API 호출 제한
- **로깅**: Winston을 통한 구조화된 로깅

## 📁 프로젝트 구조

```
nodejs-backend/
├── src/
│   ├── controllers/          # 컨트롤러
│   │   └── schedulingController.js
│   ├── middleware/           # 미들웨어
│   │   ├── errorHandler.js
│   │   ├── requestLogger.js
│   │   └── validation.js
│   ├── routes/              # 라우터
│   │   └── schedulingRoutes.js
│   ├── services/            # 서비스
│   │   └── pythonApiService.js
│   ├── utils/               # 유틸리티
│   │   └── logger.js
│   ├── app.js              # Express 앱 설정
│   └── server.js           # 서버 시작 파일
├── config/                  # 설정 파일
│   └── index.js
├── logs/                    # 로그 파일
├── package.json
├── env.example
└── README.md
```

## 🔧 설치 및 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 환경 설정

```bash
cp env.example .env
```

`.env` 파일을 편집하여 설정을 수정합니다:

```env
# 서버 설정
NODE_ENV=development
PORT=3000
HOST=localhost

# Python FastAPI 서버 설정
PYTHON_API_BASE_URL=http://localhost:8000
PYTHON_API_TIMEOUT=300000

# 로깅 설정
LOG_LEVEL=info
LOG_FILE=logs/app.log

# CORS 설정
CORS_ORIGIN=http://localhost:3000
```

### 3. 서버 실행

```bash
# 개발 모드
npm run dev

# 프로덕션 모드
npm start
```

## 📚 API 엔드포인트

### 기본 정보
- **Base URL**: `http://localhost:3000`
- **Content-Type**: `application/json`

### 엔드포인트 목록

#### 1. 전체 스케줄링 프로세스
```http
POST /api/scheduling/full
```

**요청 본문:**
```json
{
  "windowDays": 5,
  "data": {
    "order_data": [...],
    "linespeed": [...],
    "operation_seperated_sequence": [...],
    "machine_master_info": [...],
    "yield_data": [...],
    "gitem_operation": [...],
    "operation_types": [...],
    "operation_delay_df": [...],
    "width_change_df": [...],
    "machine_rest": [...],
    "machine_allocate": [...],
    "machine_limit": [...]
  }
}
```

#### 2. 단계별 실행

##### 데이터 검증
```http
POST /api/scheduling/validate
```

##### 전처리
```http
POST /api/scheduling/preprocessing
```

##### 수율 예측
```http
POST /api/scheduling/yield-prediction
```

##### DAG 생성
```http
POST /api/scheduling/dag-creation
```

##### 스케줄링
```http
POST /api/scheduling/scheduling
```

##### 결과 처리
```http
POST /api/scheduling/results
```

#### 3. 세션 관리

##### 세션 상태 조회
```http
GET /api/scheduling/status/:sessionId
```

##### 헬스 체크
```http
GET /api/scheduling/health
```

## 🔄 데이터 흐름

```
프론트엔드 → Node.js Backend → Python FastAPI → Redis
     ↓
1. 요청 수신 및 검증
     ↓
2. Python API 호출
     ↓
3. 결과 처리 및 반환
     ↓
4. 로깅 및 에러 처리
```

## 📊 응답 형식

### 성공 응답
```json
{
  "success": true,
  "message": "작업이 성공적으로 완료되었습니다",
  "data": {
    "sessionId": "session-uuid",
    "result": {...}
  }
}
```

### 에러 응답
```json
{
  "success": false,
  "error": {
    "message": "에러 메시지",
    "statusCode": 400,
    "timestamp": "2025-01-01T00:00:00.000Z",
    "path": "/api/scheduling/validate",
    "method": "POST"
  }
}
```

## 🛠️ 개발 도구

### 로깅
- **Winston**을 사용한 구조화된 로깅
- **파일 로그**: `logs/combined.log`, `logs/error.log`
- **콘솔 로그**: 개발 환경에서만 출력

### 에러 처리
- **중앙집중식 에러 처리**
- **상세한 에러 메시지**
- **HTTP 상태 코드**

### 데이터 검증
- **Joi**를 사용한 요청 데이터 검증
- **자동 에러 응답**
- **타입 안전성**

## 🔧 설정 옵션

### 서버 설정
- `PORT`: 서버 포트 (기본: 3000)
- `HOST`: 서버 호스트 (기본: localhost)
- `NODE_ENV`: 환경 (development/production)

### Python API 설정
- `PYTHON_API_BASE_URL`: Python FastAPI 서버 URL
- `PYTHON_API_TIMEOUT`: API 호출 타임아웃 (밀리초)

### 로깅 설정
- `LOG_LEVEL`: 로그 레벨 (error/warn/info/debug)
- `LOG_FILE`: 로그 파일 경로

### Rate Limiting
- `RATE_LIMIT_WINDOW_MS`: 시간 윈도우 (밀리초)
- `RATE_LIMIT_MAX_REQUESTS`: 최대 요청 수

## 🚨 주의사항

1. **Python FastAPI 서버**: 백엔드 실행 전 Python 서버가 실행 중이어야 합니다
2. **Redis 서버**: Python 서버에서 Redis를 사용하므로 Redis 서버가 실행 중이어야 합니다
3. **메모리 사용량**: 대용량 데이터 처리 시 메모리 사용량을 모니터링하세요
4. **타임아웃**: 스케줄링 프로세스는 시간이 오래 걸릴 수 있으므로 적절한 타임아웃을 설정하세요

## 📝 로그 예시

```
2025-01-01 12:00:00 [info]: 요청 시작: {"method":"POST","url":"/api/scheduling/full","ip":"127.0.0.1"}
2025-01-01 12:00:01 [info]: Python API 요청: POST http://localhost:8000/api/v1/validation/
2025-01-01 12:00:02 [info]: Python API 응답: 200 http://localhost:8000/api/v1/validation/
2025-01-01 12:00:03 [info]: 요청 완료: {"method":"POST","url":"/api/scheduling/full","statusCode":200,"duration":"3000ms"}
```

## 🤝 기여하기

1. 이슈를 생성하거나 기존 이슈를 확인하세요
2. 기능 브랜치를 생성하세요
3. 변경사항을 커밋하세요
4. Pull Request를 생성하세요

## 📄 라이선스

MIT License


