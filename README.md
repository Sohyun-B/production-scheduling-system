# Production Scheduling System

제조업 공정 스케줄링을 위한 전체 스택 웹 애플리케이션입니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React         │    │   Node.js       │    │   Python        │
│   Frontend      │◄──►│   Backend       │◄──►│   API Server    │
│   (Port 3000)   │    │   (Port 3001)   │    │   (Port 8000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Redis       │    │   Data Files    │
                       │   (Port 6379)   │    │   (JSON/Excel)  │
                       └─────────────────┘    └─────────────────┘
```

## 🚀 주요 기능

### 1. 단계별 스케줄링 실행
- **1단계**: 데이터 로딩 (직접 업로드 또는 외부 API)
- **2단계**: 전처리 (주문 데이터 분리 및 정리)
- **3단계**: 수율 예측 (생산 수율 계산)
- **4단계**: DAG 생성 (공정 간 의존성 구축)
- **5단계**: 스케줄링 실행 (최적 일정 생성)
- **6단계**: 결과 후처리 (분석 및 정리)

### 2. 실시간 진행 상황 추적
- 단계별 진행 상황 시각화
- 실시간 상태 업데이트
- 오류 발생 시 상세 정보 제공

### 3. 결과 분석 및 시각화
- 스케줄링 결과 대시보드
- 성과 지표 및 메트릭
- 차트 및 그래프를 통한 시각화

### 4. 세션 관리
- Redis 기반 세션 저장
- 단계별 데이터 지속성
- 자동 만료 및 정리

## 🛠️ 기술 스택

### Frontend
- **React 18** - UI 라이브러리
- **React Router** - 라우팅
- **React Query** - 서버 상태 관리
- **Styled Components** - CSS-in-JS
- **Lucide React** - 아이콘
- **React Hot Toast** - 알림

### Backend (Node.js)
- **Express.js** - 웹 프레임워크
- **Axios** - HTTP 클라이언트
- **Joi** - 데이터 검증
- **Winston** - 로깅
- **CORS** - Cross-Origin 요청 처리

### Backend (Python)
- **FastAPI** - 고성능 API 프레임워크
- **Pandas** - 데이터 처리
- **Redis** - 세션 저장소
- **Pydantic** - 데이터 검증

### Infrastructure
- **Docker** - 컨테이너화
- **Docker Compose** - 오케스트레이션
- **Redis** - 인메모리 데이터베이스
- **Nginx** - 웹 서버 (프로덕션)

## 📦 설치 및 실행

### 1. 전체 시스템 실행 (Docker Compose)

```bash
# 저장소 클론
git clone <repository-url>
cd production-scheduling-system

# 전체 시스템 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 시스템 중지
docker-compose down
```

### 2. 개별 서비스 실행

#### Python API 서버
```bash
cd python_engine

# 의존성 설치
pip install -r requirements.txt

# Redis 실행 (별도 터미널)
redis-server

# Python API 실행
python run_server.py
```

#### Node.js 백엔드 서버
```bash
cd backend

# 의존성 설치
npm install

# 환경 변수 설정
cp env.example .env

# 서버 실행
npm run dev
```

#### React 프론트엔드
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm start
```

## 🔧 환경 설정

### 환경 변수

#### Python API (.env)
```env
REDIS_URL=redis://localhost:6379/0
SESSION_TIMEOUT=3600
LOG_LEVEL=info
```

#### Node.js Backend (.env)
```env
PORT=3001
NODE_ENV=development
PYTHON_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://localhost:6379/0
```

#### React Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:3001
```

## 📊 API 문서

### Node.js Backend API

#### 스케줄링 API
- `POST /api/scheduling/load-data` - 직접 데이터 로딩
- `POST /api/scheduling/load-external-data` - 외부 API 데이터 로딩
- `POST /api/scheduling/preprocessing` - 2단계: 전처리
- `POST /api/scheduling/yield-prediction` - 3단계: 수율 예측
- `POST /api/scheduling/dag-creation` - 4단계: DAG 생성
- `POST /api/scheduling/scheduling` - 5단계: 스케줄링 실행
- `POST /api/scheduling/results` - 6단계: 결과 후처리
- `POST /api/scheduling/step-by-step` - 단계별 실행
- `GET /api/scheduling/session/:id/status` - 세션 상태 조회
- `DELETE /api/scheduling/session/:id` - 세션 삭제

#### 헬스 체크 API
- `GET /api/health` - 서버 상태 확인
- `GET /api/health/python` - Python API 상태 확인
- `GET /api/health/detailed` - 상세 상태 확인

### Python API
- `GET /docs` - Swagger UI 문서
- `GET /redoc` - ReDoc 문서

## 🔄 데이터 흐름

### 1. 데이터 업로드
```
사용자 → React Frontend → Node.js Backend → Python API → Redis
```

### 2. 단계별 실행
```
React Frontend → Node.js Backend → Python API → Redis (세션 저장)
```

### 3. 결과 조회
```
React Frontend → Node.js Backend → Python API → Redis (세션 로드)
```

## 📁 프로젝트 구조

```
production-scheduling-system/
├── frontend/                 # React 프론트엔드
│   ├── public/
│   ├── src/
│   │   ├── components/       # 재사용 가능한 컴포넌트
│   │   ├── pages/           # 페이지 컴포넌트
│   │   ├── services/        # API 서비스
│   │   └── App.js
│   ├── package.json
│   └── Dockerfile
├── backend/                 # Node.js 백엔드
│   ├── routes/             # API 라우트
│   ├── services/           # 비즈니스 로직
│   ├── middleware/         # 미들웨어
│   ├── utils/              # 유틸리티
│   ├── package.json
│   └── Dockerfile
├── python_engine/          # Python API 서버
│   ├── src/                # 소스 코드
│   ├── data/               # 데이터 파일
│   ├── api_server.py       # FastAPI 서버
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml      # Docker Compose 설정
└── README.md
```

## 🧪 테스트

### 단위 테스트
```bash
# Node.js 백엔드 테스트
cd backend
npm test

# Python API 테스트
cd python_engine
python -m pytest
```

### API 테스트
```bash
# 샘플 데이터 생성
cd python_engine
python sample_data_generator.py

# API 테스트 실행
python test_api_client.py
```

## 🚀 배포

### 프로덕션 배포
```bash
# 프로덕션 빌드
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

### 스케일링
```bash
# 서비스 스케일링
docker-compose up -d --scale node-backend=3
```

## 🔍 모니터링

### 헬스 체크
- Node.js Backend: http://localhost:3001/api/health
- Python API: http://localhost:8000/health
- React Frontend: http://localhost:3000

### 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f python-api
docker-compose logs -f node-backend
docker-compose logs -f react-frontend
```

## 🐛 문제 해결

### 일반적인 문제

1. **Redis 연결 오류**
   ```bash
   # Redis 상태 확인
   redis-cli ping
   
   # Redis 재시작
   docker-compose restart redis
   ```

2. **Python API 연결 오류**
   ```bash
   # Python API 상태 확인
   curl http://localhost:8000/health
   
   # Python API 재시작
   docker-compose restart python-api
   ```

3. **포트 충돌**
   ```bash
   # 포트 사용 확인
   netstat -tulpn | grep :3000
   netstat -tulpn | grep :3001
   netstat -tulpn | grep :8000
   ```

## 📝 라이선스

MIT License

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.

---

**Production Scheduling System** - 제조업 공정 스케줄링을 위한 통합 솔루션