# Node.js 백엔드 통합 가이드

## 🎯 개요

프론트엔드에서 요청을 받아 Python FastAPI의 각 단계별 API에 요청을 보내고 결과를 전달하는 Node.js 백엔드 서버입니다.

## 🏗️ 아키텍처

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
├── examples/                # 예제 파일
│   ├── index.html
│   └── frontend-integration.js
├── logs/                    # 로그 파일
├── package.json
├── env.example
├── start.bat               # Windows 실행 스크립트
├── start.sh                # Linux/Mac 실행 스크립트
└── README.md
```

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
cd nodejs-backend
npm install
```

### 2. 환경 설정
```bash
cp env.example .env
# .env 파일을 편집하여 설정 수정
```

### 3. 서버 실행
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# 또는 npm 스크립트 사용
npm run dev  # 개발 모드
npm start    # 프로덕션 모드
```

## 📚 API 사용법

### 기본 설정
```javascript
const api = new SchedulingAPI('http://localhost:3000');
```

### 1. 전체 스케줄링 프로세스
```javascript
const result = await api.runFullScheduling(data, windowDays);
```

### 2. 단계별 실행
```javascript
// 1단계: 데이터 검증
const validation = await api.validateData(data);

// 2단계: 전처리
const preprocessing = await api.runPreprocessing(sessionId, windowDays);

// 3단계: 수율 예측
const yieldPrediction = await api.runYieldPrediction(sessionId);

// 4단계: DAG 생성
const dagCreation = await api.runDAGCreation(sessionId);

// 5단계: 스케줄링
const scheduling = await api.runScheduling(sessionId, windowDays);

// 6단계: 결과 처리
const results = await api.runResultsProcessing(sessionId);
```

### 3. 세션 관리
```javascript
// 세션 상태 조회
const status = await api.getSessionStatus(sessionId);

// 헬스 체크
const health = await api.healthCheck();
```

## 🔧 설정 옵션

### 환경 변수
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

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
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

## 🔄 데이터 흐름

### 1. 프론트엔드 요청
```javascript
// 프론트엔드에서 데이터와 함께 요청
const data = {
  order_data: [...],
  linespeed: [...],
  // ... 기타 데이터
};

const result = await api.runFullScheduling(data, 5);
```

### 2. Node.js 백엔드 처리
```javascript
// 1. 요청 검증
const { error, value } = schema.validate(req.body);

// 2. Python API 호출
const pythonResult = await pythonApiService.validateData(sessionId, data);

// 3. 결과 반환
res.json({
  success: true,
  data: pythonResult
});
```

### 3. Python FastAPI 처리
```python
# 1. 데이터 검증
validation_result = python_engine_service.validate_data(...)

# 2. Redis에 저장
redis_manager.save_stage_data(session_id, "validation", stage_data)

# 3. 결과 반환
return {"success": True, "data": validation_result}
```

## 🚨 주의사항

### 1. 서버 실행 순서
1. **Redis 서버** 실행
2. **Python FastAPI 서버** 실행
3. **Node.js 백엔드 서버** 실행

### 2. 메모리 관리
- 대용량 데이터 처리 시 메모리 사용량 모니터링
- 적절한 타임아웃 설정

### 3. 에러 처리
- 각 단계별 실패 시 적절한 에러 메시지 제공
- 로그를 통한 디버깅 지원

## 📝 로그 예시

```
2025-01-01 12:00:00 [info]: 요청 시작: {"method":"POST","url":"/api/scheduling/full","ip":"127.0.0.1"}
2025-01-01 12:00:01 [info]: Python API 요청: POST http://localhost:8000/api/v1/validation/
2025-01-01 12:00:02 [info]: Python API 응답: 200 http://localhost:8000/api/v1/validation/
2025-01-01 12:00:03 [info]: 요청 완료: {"method":"POST","url":"/api/scheduling/full","statusCode":200,"duration":"3000ms"}
```

## 🎉 완성된 기능

### ✅ 백엔드 서버
- Express 기반 REST API 서버
- Python FastAPI 연동
- Redis 상태 관리
- 에러 처리 및 로깅

### ✅ 프론트엔드 연동
- JavaScript SDK
- HTML 예제 페이지
- 실시간 상태 표시
- 에러 처리

### ✅ 개발 도구
- 환경 설정 관리
- 로깅 시스템
- 데이터 검증
- Rate Limiting

## 🤝 사용 예제

### HTML에서 사용
```html
<!DOCTYPE html>
<html>
<head>
    <title>Production Scheduling</title>
</head>
<body>
    <button id="runScheduling">스케줄링 실행</button>
    <div id="result"></div>
    
    <script src="examples/frontend-integration.js"></script>
    <script>
        const api = new SchedulingAPI();
        
        document.getElementById('runScheduling').addEventListener('click', async function() {
            try {
                const result = await api.runFullScheduling(data, 5);
                document.getElementById('result').innerHTML = JSON.stringify(result, null, 2);
            } catch (error) {
                console.error('에러:', error);
            }
        });
    </script>
</body>
</html>
```

### Node.js에서 사용
```javascript
const SchedulingAPI = require('./examples/frontend-integration');

const api = new SchedulingAPI('http://localhost:3000');

async function main() {
    try {
        const result = await api.runFullScheduling(data, 5);
        console.log('결과:', result);
    } catch (error) {
        console.error('에러:', error);
    }
}

main();
```

이제 프론트엔드에서 Node.js 백엔드를 통해 Python FastAPI의 스케줄링 시스템을 사용할 수 있습니다!


