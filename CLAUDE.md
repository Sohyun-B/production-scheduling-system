# 생산 스케줄링 시스템 개발 기록

## 프로젝트 개요
React + FastAPI + Python 스케줄링 엔진으로 구성된 생산 스케줄링 시스템 개발

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React Frontend │◄──►│  FastAPI        │◄──►│ Python Engine   │
│  (Port 3000)    │    │  Backend        │    │ (Scheduling)    │
│                 │    │  (Port 8000)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │   (orders.db)   │
                       └─────────────────┘
```

## 완성된 기능들

### 1. 웹 인터페이스 (React Frontend)
- **위치**: `frontend/`
- **메인 컴포넌트**: 
  - `MainDashboard.tsx`: 통합 대시보드 with 탭 네비게이션
  - `Dashboard.tsx`: 스케줄링 실행 결과 대시보드
  - `OrderTable.tsx`: 주문 데이터 CRUD 관리
  - `ProgressMonitor.tsx`: 실시간 진행상황 모니터링
- **실행**: `npm start` (http://localhost:3000)

### 2. API 백엔드 (FastAPI)
- **위치**: `backend/`
- **주요 엔드포인트**:
  - `/api/v1/orders/`: 주문 관리 CRUD
  - `/api/v1/scheduling/`: 스케줄링 실행 및 조회
  - `/api/v1/progress/`: 실시간 진행상황 추적
  - `/health`: 시스템 상태 확인
- **실행**: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

### 3. 스케줄링 엔진 (Python)
- **위치**: `python_engine/`
- **메인 파일**: `main.py`
- **데이터 소스**: `preprocessed_order.xlsx` (174개 실제 주문 데이터)
- **결과 파일**: `0829 스케줄링결과.xlsx`, `level4_gantt.png`

## 데이터베이스 구조 (SQLite)

### Orders 테이블
```sql
- id: INTEGER (Primary Key)
- po_no: VARCHAR (주문번호)
- gitem: VARCHAR (품목코드)  
- gitem_name: VARCHAR (품목명)
- width: FLOAT (폭 - 실제 치수)
- length: FLOAT (길이 - 실제 치수)
- request_amount: INTEGER (의뢰량)
- due_date: DATETIME (납기일)
```

### ScheduleRun 테이블
```sql
- id: INTEGER
- run_id: VARCHAR (UUID)
- name: VARCHAR
- status: VARCHAR (pending/running/completed/failed)
- makespan: FLOAT
- total_late_days: INTEGER
- created_at/completed_at: DATETIME
```

## 실시간 진행상황 추적

스케줄링은 5단계로 구성되며 각 단계별 실시간 모니터링 가능:

1. **데이터 준비**: 데이터베이스에서 주문 데이터 로딩
2. **데이터 전처리**: 월별 분리, 병합, 공정 순서 생성  
3. **DAG 생성**: 작업 의존성 그래프 생성
4. **스케줄링 실행**: 기계 할당 및 스케줄링 실행
5. **결과 저장**: Excel 결과 파싱 후 데이터베이스 저장

## 주요 해결된 문제들

### 1. SQLAlchemy 쿼리 순서 오류
```python
# 수정 전 (오류)
runs = db.query(ScheduleRun).offset(skip).limit(limit).order_by(ScheduleRun.created_at.desc()).all()

# 수정 후 (정상)
runs = db.query(ScheduleRun).order_by(ScheduleRun.created_at.desc()).offset(skip).limit(limit).all()
```

### 2. Unicode 인코딩 문제
Python 엔진의 이모지 문자로 인한 `UnicodeEncodeError` 해결:
```python
# 수정: 모든 이모지 제거
print("📂 데이터 로딩...") → print("데이터 로딩...")
```

### 3. 실제 데이터 연동
- `25년 5월 PO 내역(송부건).xlsx` → `preprocessed_order.xlsx` 사용
- SPEC 컬럼에서 폭x길이 파싱 → 전처리된 너비/길이 컬럼 직접 사용
- 174개 실제 주문 데이터로 정확한 치수 정보 확보

## 실행 방법

### 1. 백엔드 서버 시작
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. 프론트엔드 서버 시작  
```bash
cd frontend
npm start
```

### 3. 주문 데이터 로딩 (필요시)
```bash
cd backend
python load_orders_from_excel.py
```

### 4. 접속
- **웹 인터페이스**: http://localhost:3000
- **API 문서**: http://127.0.0.1:8000/docs
- **헬스체크**: http://127.0.0.1:8000/health

## 중요 파일 위치

### 설정 파일
- `backend/app/core/config.py`: 데이터베이스 및 Python 엔진 경로 설정
- `frontend/src/services/api.ts`: API 클라이언트 설정

### 데이터 파일  
- `python_engine/preprocessed_order.xlsx`: 실제 주문 데이터 (174개)
- `backend/orders.db`: SQLite 데이터베이스
- `python_engine/0829 스케줄링결과.xlsx`: 스케줄링 결과

### 로그 및 디버깅
- FastAPI 서버 로그에서 실시간 API 호출 확인
- 프론트엔드에서 네트워크 탭으로 API 통신 모니터링
- 스케줄링 진행상황은 `/api/v1/progress/runs/{run_id}/progress` 엔드포인트로 실시간 확인

## 다음 단계 가능한 확장 기능

1. **기계 상태 모니터링 대시보드**
2. **스케줄링 결과 비교 기능**  
3. **지연 분석 대시보드**
4. **수율 분석 시각화**
5. **스케줄링 이벤트 알림 시스템**
6. **간트 차트 시각화**
7. **스케줄링 결과 내보내기 기능**

시스템이 완전히 구축되어 실제 생산 스케줄링 업무에 활용 가능한 상태입니다.