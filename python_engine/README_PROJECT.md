# Production Scheduling System

React + FastAPI를 활용한 생산계획 스케줄링 시스템입니다.

## 시스템 구조

```
├── backend/          # FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── preprocessing/    # 기존 Python 전처리 로직
├── scheduler/        # 기존 Python 스케줄링 로직
├── dag_management/   # DAG 관리
├── yield_management/ # 수율 예측
└── results/         # 결과 처리
```

## 기능

### Phase 1 (현재)
- ✅ FastAPI 백엔드 기본 구조
- ✅ SQLite 데이터베이스 설계
- ✅ React 프론트엔드 기본 구조
- ✅ Docker 환경 구성
- ✅ 기존 Python 로직 래핑

### Phase 2 (예정)
- 주문 데이터 CRUD API
- 파일 업로드/다운로드
- 스케줄링 실행 및 결과 조회
- 간트차트 시각화

## 설치 및 실행

### 개발 환경

#### 백엔드 (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 프론트엔드 (React)
```bash
cd frontend
npm install
npm start
```

### Docker 환경
```bash
docker-compose up --build
```

## API 엔드포인트

- `GET /api/v1/orders` - 주문 목록 조회
- `POST /api/v1/orders` - 주문 생성
- `POST /api/v1/scheduling/run` - 스케줄링 실행
- `GET /api/v1/scheduling/runs` - 스케줄링 실행 기록
- `POST /api/v1/files/upload` - 파일 업로드

## 데이터베이스 마이그레이션

### SQLite → PostgreSQL
```bash
# PostgreSQL 컨테이너 실행
docker-compose up db

# 환경변수 변경
DATABASE_URL=postgresql://postgres:password@localhost:5432/production_scheduling
```

### SQLite → MS SQL Server
```bash
# Docker compose에서 MS SQL 서비스 추가
DATABASE_URL=mssql://sa:password@localhost:1433/production_scheduling
```

## 기존 Python 로직 연동

기존의 `main.py`, `config.py`, 및 각종 모듈들이 FastAPI를 통해 래핑되어 실행됩니다:

1. FastAPI에서 스케줄링 요청 수신
2. 기존 Python 스케줄링 엔진 실행 (`main.py`)
3. 결과 파싱 및 데이터베이스 저장
4. React 프론트엔드에서 결과 조회

## 개발 로드맵

- **Phase 1**: 기본 인프라 ✅
- **Phase 2**: 핵심 기능 구현 (2-3주)
- **Phase 3**: 고급 기능 (2-3주)
- **Phase 4**: 최적화 및 배포 (1-2주)