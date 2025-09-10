# 📚 API Documentation

## 🔗 API 엔드포인트 목록

### 프론트엔드 → Node.js 백엔드 (포트 3001)

#### 1. 1단계: 데이터 로딩
```
POST /api/stages/stage1/load-data
```

**요청 본문:**
```json
{
  "linespeed": [
    {
      "GITEM": "G001",
      "공정명": "C2010",
      "C2010": 100,
      "C2250": 0,
      "C2260": 0,
      "C2270": 0,
      "O2310": 0,
      "O2340": 0
    }
  ],
  "operation_sequence": [
    {
      "공정순서": 1,
      "공정명": "C2010",
      "공정분류": "CUT",
      "배합코드": "BH001"
    }
  ],
  "machine_master_info": [
    {
      "기계인덱스": 1,
      "기계코드": "C2010",
      "기계이름": "커팅기1"
    }
  ],
  "yield_data": [
    {
      "GITEM": "G001",
      "공정명": "C2010",
      "수율": 0.95
    }
  ],
  "gitem_operation": [
    {
      "GITEM": "G001",
      "공정명": "C2010",
      "공정분류": "CUT",
      "배합코드": "BH001"
    }
  ],
  "operation_types": [
    {
      "공정명": "C2010",
      "공정분류": "CUT",
      "설명": "커팅공정1"
    }
  ],
  "operation_delay": [
    {
      "선행공정분류": "CUT",
      "후행공정분류": "CUT",
      "타입교체시간": 30,
      "long_to_short": 10,
      "short_to_long": 20
    }
  ],
  "width_change": [
    {
      "기계인덱스": 1,
      "이전폭": 1000,
      "이후폭": 1200,
      "변경시간": 15,
      "long_to_short": 10,
      "short_to_long": 20
    }
  ],
  "machine_rest": [
    {
      "기계인덱스": 1,
      "시작시간": "2024-01-01 00:00:00",
      "종료시간": "2024-01-01 08:00:00",
      "사유": "야간휴무"
    }
  ],
  "machine_allocate": [
    {
      "기계인덱스": 1,
      "공정명": "C2010",
      "할당유형": "EXCLUSIVE"
    }
  ],
  "machine_limit": [
    {
      "기계인덱스": 1,
      "공정명": "C2010",
      "시작시간": "2024-01-01 08:00:00",
      "종료시간": "2024-01-01 18:00:00",
      "제한사유": "작업시간"
    }
  ],
  "order_data": [
    {
      "P/O NO": "PO001",
      "GITEM": "G001",
      "GITEM명": "제품1",
      "너비": 1000,
      "길이": 2000,
      "의뢰량": 100,
      "원단길이": 914,
      "납기일": "2024-01-15"
    }
  ]
}
```

**응답:**
```json
{
  "success": true,
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "message": "데이터 로딩 완료",
  "data": {
    "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
    "message": "데이터 로딩 완료",
    "data_summary": {
      "linespeed_count": 1,
      "machine_count": 1,
      "total_orders": 1
    }
  }
}
```

#### 2. 2단계: 전처리
```
POST /api/stages/stage2/preprocessing
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "success": true,
  "message": "전처리 완료",
  "data": {
    "message": "전처리 완료",
    "processed_jobs": 2,
    "machine_constraints": {
      "total_machines": 1,
      "constraints_applied": 3
    }
  }
}
```

#### 3. 3단계: 수율 예측
```
POST /api/stages/stage3/yield-prediction
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
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

#### 4. 4단계: DAG 생성
```
POST /api/stages/stage4/dag-creation
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
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

#### 5. 5단계: 스케줄링
```
POST /api/stages/stage5/scheduling
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "window_days": 5
}
```

**응답:**
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

#### 6. 5단계 상태 확인
```
GET /api/stages/stage5/status/:sessionId
```

**응답:**
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

#### 7. 6단계: 결과 후처리
```
POST /api/stages/stage6/results
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "success": true,
  "message": "결과 후처리 완료",
  "data": {
    "message": "결과 후처리 완료",
    "late_orders": 0,
    "results_summary": {
      "total_jobs": 2,
      "completed_jobs": 2,
      "late_jobs": 0,
      "efficiency": 0.95
    }
  }
}
```

### Node.js 백엔드 → Python FastAPI (포트 8000)

#### 1. 1단계: 데이터 로딩
```
POST /api/v1/stage1/load-data
```

**요청 본문:** (프론트엔드와 동일)

**응답:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "message": "데이터 로딩 완료",
  "data_summary": {
    "linespeed_count": 1,
    "machine_count": 1,
    "total_orders": 1
  }
}
```

#### 2. 2단계: 전처리
```
POST /api/v1/stage2/preprocessing
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "message": "전처리 완료",
  "processed_jobs": 2,
  "machine_constraints": {
    "total_machines": 1,
    "constraints_applied": 3
  }
}
```

#### 3. 3단계: 수율 예측
```
POST /api/v1/stage3/yield-prediction
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "message": "수율 예측 완료",
  "predicted_yields": 2,
  "average_yield": 0.95
}
```

#### 4. 4단계: DAG 생성
```
POST /api/v1/stage4/dag-creation
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "message": "DAG 생성 완료",
  "dag_nodes": 2,
  "machines": 1
}
```

#### 5. 5단계: 스케줄링
```
POST /api/v1/stage5/scheduling
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "window_days": 5
}
```

**응답:**
```json
{
  "message": "스케줄링이 백그라운드에서 시작되었습니다",
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "status": "running"
}
```

#### 6. 세션 상태 확인
```
GET /api/v1/session/{session_id}/status
```

**응답:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df",
  "completed_stages": ["stage1", "stage2", "stage3", "stage4", "stage5"],
  "total_stages": 6,
  "status": "completed",
  "created_at": "2024-01-01T00:00:00Z",
  "last_updated": "2024-01-01T00:05:00Z"
}
```

#### 7. 6단계: 결과 후처리
```
POST /api/v1/stage6/results
```

**요청 본문:**
```json
{
  "session_id": "88cbf9d1-7fbc-4499-b0a1-1083828c33df"
}
```

**응답:**
```json
{
  "message": "결과 후처리 완료",
  "late_orders": 0,
  "results_summary": {
    "total_jobs": 2,
    "completed_jobs": 2,
    "late_jobs": 0,
    "efficiency": 0.95
  }
}
```

## 🔧 에러 응답 형식

### 일반적인 에러 응답
```json
{
  "success": false,
  "message": "오류 메시지",
  "error": "상세 오류 정보"
}
```

### HTTP 상태 코드
- `200`: 성공
- `400`: 잘못된 요청
- `404`: 리소스를 찾을 수 없음
- `422`: 유효성 검사 실패
- `500`: 서버 내부 오류

## 📊 데이터 타입 정의

### 세션 ID
- **타입**: String (UUID)
- **형식**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **예시**: `88cbf9d1-7fbc-4499-b0a1-1083828c33df`

### 날짜 형식
- **타입**: String
- **형식**: `YYYY-MM-DD` 또는 `YYYY-MM-DD HH:MM:SS`
- **예시**: `2024-01-15` 또는 `2024-01-01 08:00:00`

### 수율 값
- **타입**: Number
- **범위**: 0.0 ~ 1.0
- **예시**: `0.95` (95% 수율)

### 윈도우 일수
- **타입**: Integer
- **범위**: 1 ~ 30
- **기본값**: 5

## 🔍 테스트 방법

### 1. Python FastAPI 서버 테스트
```bash
cd production-scheduling-system/python_engine
python test_simple_stage5.py
```

### 2. 전체 시스템 테스트
```bash
# 1. Python 서버 시작
cd production-scheduling-system/python_engine
python api_server.py

# 2. Node.js 서버 시작
cd production-scheduling-system/backend
npm start

# 3. React 앱 시작
cd production-scheduling-system/frontend
npm start
```

### 3. API 문서 확인
- Python FastAPI: `http://localhost:8000/docs`
- Node.js 백엔드: `http://localhost:3001/api/scheduling/docs`

## 🚨 주의사항

1. **세션 의존성**: 2-6단계는 반드시 1단계 완료 후 실행
2. **비동기 처리**: 5단계는 백그라운드에서 처리되므로 상태 확인 필요
3. **데이터 형식**: 모든 날짜는 올바른 형식으로 전달
4. **에러 처리**: 각 단계별 에러 발생 시 이전 단계 재실행 필요
5. **타임아웃**: 5단계 스케줄링은 시간이 오래 걸릴 수 있음
