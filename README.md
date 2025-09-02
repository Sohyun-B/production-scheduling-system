# Production Scheduling System

React + FastAPI를 활용한 생산계획 스케줄링 시스템

## 📁 프로젝트 구조

```
생산계획/
├── backend/              # FastAPI 백엔드 애플리케이션
│   ├── app/
│   │   ├── api/         # REST API 엔드포인트
│   │   ├── core/        # 설정 및 핵심 로직
│   │   ├── db/          # 데이터베이스 연결
│   │   ├── models/      # SQLAlchemy 모델
│   │   ├── schemas/     # Pydantic 스키마
│   │   └── services/    # 비즈니스 로직
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React 프론트엔드 애플리케이션
│   ├── src/
│   │   ├── components/  # React 컴포넌트
│   │   └── services/    # API 서비스
│   ├── Dockerfile
│   └── package.json
├── python_engine/        # 기존 Python 스케줄링 엔진
│   ├── config.py        # 설정
│   ├── main.py         # 메인 실행 파일
│   ├── preprocessing/   # 데이터 전처리
│   ├── scheduler/       # 스케줄링 로직
│   ├── dag_management/  # DAG 관리
│   ├── yield_management/# 수율 예측
│   └── results/         # 결과 처리
├── media/               # 미디어 파일 (간트차트 등)
└── docker-compose.yml   # 개발환경 구성
```

## 🚀 빠른 시작

### 개발 환경 실행

1. **백엔드 실행**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

2. **프론트엔드 실행** (새 터미널)
```bash
cd frontend
npm install
npm start
```

### Docker로 실행
```bash
docker-compose up --build
```

## 📊 접속 주소

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (Docker 사용 시)

## 🔧 주요 기능

### ✅ 구현 완료 (Phase 1)
- FastAPI 백엔드 기본 구조
- React 프론트엔드 대시보드
- SQLite 데이터베이스
- 기존 Python 엔진 연동
- Docker 환경 구성

### 🚧 개발 예정 (Phase 2)
- 주문 데이터 CRUD
- 파일 업로드/다운로드
- 스케줄링 실행 UI
- 실시간 간트차트
- 결과 분석 대시보드

## 🔄 개발 로드맵

- **Phase 1**: 기본 인프라 ✅
- **Phase 2**: 핵심 기능 구현 (2-3주)
- **Phase 3**: 고급 기능 (간트차트, 최적화)
- **Phase 4**: 배포 및 최적화

## 🛠 기술 스택

- **Backend**: FastAPI, SQLAlchemy, SQLite/PostgreSQL
- **Frontend**: React, TypeScript
- **Engine**: Python, pandas, numpy
- **DevOps**: Docker, Docker Compose