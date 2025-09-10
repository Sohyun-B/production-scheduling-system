# 🏗️ Production Scheduling System Architecture

## 📋 시스템 개요

3-tier 아키텍처로 구성된 생산 스케줄링 시스템으로, React 프론트엔드, Node.js 백엔드, Python FastAPI 서버가 연동되어 단계별 스케줄링을 수행합니다.

## 🏛️ 시스템 아키텍처

```
┌─────────────────┐    HTTP/API    ┌─────────────────┐    HTTP/API    ┌─────────────────┐
│   React Frontend │ ──────────────▶│  Node.js Backend│ ──────────────▶│ Python FastAPI  │
│   (Port 3000)    │                │   (Port 3001)   │                │   (Port 8000)   │
└─────────────────┘                └─────────────────┘                └─────────────────┘
         │                                   │                                   │
         │                                   │                                   │
         ▼                                   ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐                ┌─────────────────┐
│   사용자 인터페이스  │                │   API 오케스트레이션  │                │   스케줄링 엔진   │
│   - 단계별 실행     │                │   - 요청 라우팅      │                │   - 데이터 처리   │
│   - 결과 표시      │                │   - 세션 관리       │                │   - 알고리즘 실행 │
│   - 로딩 애니메이션  │                │   - 에러 처리       │                │   - Redis 저장   │
└─────────────────┘                └─────────────────┘                └─────────────────┘
```

## 🔄 전체 데이터 흐름

### 1. 사용자 액션 → 프론트엔드
```
사용자가 "1단계 실행" 버튼 클릭
    ↓
React 컴포넌트에서 executeStep() 함수 호출
    ↓
API 서비스에서 Node.js 백엔드로 HTTP 요청
```

### 2. 프론트엔드 → Node.js 백엔드
```
POST /api/stages/stage1/load-data
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

### 3. Node.js 백엔드 → Python FastAPI
```
POST http://localhost:8000/api/v1/stage1/load-data
{
  "linespeed": [...],
  "operation_sequence": [...],
  // ... 동일한 데이터
}
```

### 4. Python FastAPI 처리
```
1. JSON 데이터를 DataFrame으로 변환
2. Redis에 세션 ID와 함께 저장
3. 데이터 요약 정보 생성
4. 응답 반환
```

### 5. 응답 역순 전달
```
Python FastAPI → Node.js 백엔드 → React 프론트엔드 → 사용자
```

## 📊 단계별 상세 처리 과정

### 1단계: 데이터 로딩
**프론트엔드:**
- 사용자가 샘플 데이터와 함께 "1단계 실행" 클릭
- `executeStep()` 함수가 Node.js 백엔드로 POST 요청

**Node.js 백엔드:**
- `/api/stages/stage1/load-data` 엔드포인트에서 요청 수신
- Python FastAPI로 동일한 데이터 전달
- 응답을 프론트엔드로 전달

**Python FastAPI:**
- `POST /api/v1/stage1/load-data` 엔드포인트에서 요청 수신
- JSON 데이터를 DataFrame으로 변환
- Redis에 세션 ID와 함께 저장
- 세션 ID와 데이터 요약 정보 반환

**결과:**
```json
{
  "success": true,
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "message": "데이터 로딩 완료",
  "data": {
    "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
    "message": "데이터 로딩 완료",
    "data_summary": {...}
  }
}
```

### 2단계: 전처리
**프론트엔드:**
- 1단계 완료 후 "2단계 실행" 버튼 활성화
- 세션 ID와 함께 Node.js 백엔드로 요청

**Node.js 백엔드:**
- `/api/stages/stage2/preprocessing` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 ID 전달

**Python FastAPI:**
- `POST /api/v1/stage2/preprocessing` 엔드포인트에서 요청 수신
- Redis에서 1단계 데이터 로드
- `preprocessing` 함수 실행
- 전처리된 데이터를 Redis에 저장

**결과:**
```json
{
  "success": true,
  "message": "전처리 완료",
  "data": {
    "message": "전처리 완료",
    "processed_jobs": 2,
    "machine_constraints": {...}
  }
}
```

### 3단계: 수율 예측
**프론트엔드:**
- 2단계 완료 후 "3단계 실행" 버튼 활성화
- 세션 ID와 함께 Node.js 백엔드로 요청

**Node.js 백엔드:**
- `/api/stages/stage3/yield-prediction` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 ID 전달

**Python FastAPI:**
- `POST /api/v1/stage3/yield-prediction` 엔드포인트에서 요청 수신
- Redis에서 2단계 데이터 로드
- `yield_prediction` 함수 실행
- 수율 예측 결과를 Redis에 저장

**결과:**
```json
{
  "success": true,
  "message": "수율 예측 완료",
  "data": {
    "message": "수율 예측 완료",
    "predicted_yields": 2,
    "average_yield": 0.95
  }
}
```

### 4단계: DAG 생성
**프론트엔드:**
- 3단계 완료 후 "4단계 실행" 버튼 활성화
- 세션 ID와 함께 Node.js 백엔드로 요청

**Node.js 백엔드:**
- `/api/stages/stage4/dag-creation` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 ID 전달

**Python FastAPI:**
- `POST /api/v1/stage4/dag-creation` 엔드포인트에서 요청 수신
- Redis에서 3단계 데이터 로드
- `create_complete_dag_system` 함수 실행
- DAG 생성 결과를 Redis에 저장

**결과:**
```json
{
  "success": true,
  "message": "DAG 생성 완료",
  "data": {
    "message": "DAG 생성 완료",
    "dag_nodes": 2,
    "machines": 1
  }
}
```

### 5단계: 스케줄링 (비동기)
**프론트엔드:**
- 4단계 완료 후 "5단계 실행" 버튼 활성화
- 세션 ID와 윈도우 일수와 함께 Node.js 백엔드로 요청

**Node.js 백엔드:**
- `/api/stages/stage5/scheduling` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 ID와 윈도우 일수 전달

**Python FastAPI:**
- `POST /api/v1/stage5/scheduling` 엔드포인트에서 요청 수신
- `ThreadPoolExecutor`로 백그라운드에서 스케줄링 실행
- 즉시 응답 반환 (비동기 처리)

**결과:**
```json
{
  "success": true,
  "message": "스케줄링이 백그라운드에서 시작되었습니다",
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "status": "running",
  "data": {
    "message": "스케줄링이 백그라운드에서 시작되었습니다",
    "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
    "status": "running"
  }
}
```

### 5단계 상태 확인 (폴링)
**프론트엔드:**
- 5단계 시작 후 2초마다 상태 확인
- `getStage5Status()` 함수로 Node.js 백엔드에 요청

**Node.js 백엔드:**
- `/api/stages/stage5/status/:sessionId` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 상태 조회

**Python FastAPI:**
- `GET /api/v1/session/{session_id}/status` 엔드포인트에서 요청 수신
- Redis에서 세션 상태 확인
- 완료된 단계 목록 반환

**결과:**
```json
{
  "success": true,
  "message": "5단계 상태 조회 성공",
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "stage": 5,
  "status": "completed",
  "data": {
    "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
    "completed_stages": ["stage1", "stage2", "stage3", "stage4", "stage5"],
    "total_stages": 6,
    "status": "completed"
  }
}
```

### 6단계: 결과 후처리
**프론트엔드:**
- 5단계 완료 후 "6단계 실행" 버튼 활성화
- 세션 ID와 함께 Node.js 백엔드로 요청

**Node.js 백엔드:**
- `/api/stages/stage6/results` 엔드포인트에서 요청 수신
- Python FastAPI로 세션 ID 전달

**Python FastAPI:**
- `POST /api/v1/stage6/results` 엔드포인트에서 요청 수신
- Redis에서 5단계 데이터 로드
- `create_results` 함수 실행
- 최종 결과를 Redis에 저장

**결과:**
```json
{
  "success": true,
  "message": "결과 후처리 완료",
  "data": {
    "message": "결과 후처리 완료",
    "late_orders": 0,
    "results_summary": {...}
  }
}
```

## 🔧 기술 스택

### 프론트엔드 (React)
- **포트**: 3000
- **기술**: React, React Router, Styled Components, Axios
- **주요 기능**:
  - 단계별 실행 버튼
  - 로딩 애니메이션
  - 결과 데이터 시각화
  - 상태 관리

### Node.js 백엔드
- **포트**: 3001
- **기술**: Express.js, Axios, Winston
- **주요 기능**:
  - API 오케스트레이션
  - 요청 라우팅
  - 에러 처리
  - 세션 관리

### Python FastAPI
- **포트**: 8000
- **기술**: FastAPI, Pandas, Redis, ThreadPoolExecutor
- **주요 기능**:
  - 스케줄링 알고리즘 실행
  - 데이터 처리
  - Redis 세션 관리
  - 비동기 처리

### Redis
- **포트**: 6379
- **기능**: 세션 데이터 저장 및 관리

## 📁 파일 구조

```
production-scheduling-system/
├── frontend/                    # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   └── StepByStepScheduling.js
│   │   ├── services/
│   │   │   └── api.js
│   │   └── App.js
│   └── package.json
├── backend/                     # Node.js 백엔드
│   ├── routes/
│   │   └── stages.js
│   ├── server.js
│   └── package.json
├── python_engine/               # Python FastAPI
│   ├── api_server.py
│   ├── src/
│   │   ├── preprocessing/
│   │   ├── yield_management/
│   │   ├── dag_management/
│   │   ├── scheduler/
│   │   └── results/
│   └── requirements.txt
└── SYSTEM_ARCHITECTURE.md       # 이 문서
```

## 🚀 실행 방법

### 1. Python FastAPI 서버 시작
```bash
cd production-scheduling-system/python_engine
python api_server.py
```

### 2. Node.js 백엔드 시작
```bash
cd production-scheduling-system/backend
npm start
```

### 3. React 프론트엔드 시작
```bash
cd production-scheduling-system/frontend
npm start
```

### 4. Redis 시작 (선택사항)
```bash
redis-server
```

## 🔍 API 엔드포인트

### 프론트엔드 → Node.js 백엔드
- `POST /api/stages/stage1/load-data` - 1단계 데이터 로딩
- `POST /api/stages/stage2/preprocessing` - 2단계 전처리
- `POST /api/stages/stage3/yield-prediction` - 3단계 수율 예측
- `POST /api/stages/stage4/dag-creation` - 4단계 DAG 생성
- `POST /api/stages/stage5/scheduling` - 5단계 스케줄링
- `GET /api/stages/stage5/status/:sessionId` - 5단계 상태 확인
- `POST /api/stages/stage6/results` - 6단계 결과 후처리

### Node.js 백엔드 → Python FastAPI
- `POST /api/v1/stage1/load-data` - 1단계 데이터 로딩
- `POST /api/v1/stage2/preprocessing` - 2단계 전처리
- `POST /api/v1/stage3/yield-prediction` - 3단계 수율 예측
- `POST /api/v1/stage4/dag-creation` - 4단계 DAG 생성
- `POST /api/v1/stage5/scheduling` - 5단계 스케줄링
- `GET /api/v1/session/{session_id}/status` - 세션 상태 확인
- `POST /api/v1/stage6/results` - 6단계 결과 후처리

## 🎯 주요 특징

1. **단계별 독립 실행**: 각 단계를 독립적으로 실행할 수 있음
2. **세션 기반 관리**: Redis를 통한 세션 데이터 관리
3. **비동기 처리**: 5단계 스케줄링은 백그라운드에서 비동기 처리
4. **실시간 상태 확인**: 폴링을 통한 실시간 상태 업데이트
5. **에러 처리**: 각 단계별 에러 처리 및 복구
6. **시각적 피드백**: 로딩 애니메이션 및 결과 표시

## 🔄 데이터 흐름 요약

```
사용자 액션 → React → Node.js → Python FastAPI → Redis
                ↑                                    ↓
            결과 표시 ← Node.js ← Python FastAPI ← Redis
```

이 아키텍처를 통해 사용자는 직관적인 인터페이스로 복잡한 스케줄링 알고리즘을 단계별로 실행하고 결과를 확인할 수 있습니다.
