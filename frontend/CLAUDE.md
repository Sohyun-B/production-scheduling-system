# Frontend React 애플리케이션 구조

## React 프론트엔드 설정

### 프로젝트 구조
```
frontend/
├── public/
├── src/
│   ├── App.tsx                    # 메인 앱 컴포넌트
│   ├── App.css                    # 글로벌 스타일
│   ├── components/
│   │   ├── MainDashboard.tsx      # 통합 대시보드 (메인 화면)
│   │   ├── MainDashboard.css      # 대시보드 스타일
│   │   ├── Dashboard.tsx          # 스케줄링 결과 대시보드
│   │   ├── Dashboard.css          # 대시보드 스타일
│   │   ├── OrderTable.tsx         # 주문 관리 테이블
│   │   ├── OrderForm.tsx          # 주문 생성/수정 폼
│   │   ├── ProgressMonitor.tsx    # 실시간 진행상황 모니터링
│   │   └── SchedulingRunner.tsx   # 스케줄링 실행 컴포넌트
│   └── services/
│       └── api.ts                 # API 클라이언트 서비스
├── package.json
└── tsconfig.json
```

## 주요 컴포넌트

### 1. MainDashboard.tsx (메인 화면)
통합 대시보드로 탭 기반 네비게이션 제공:

```typescript
const tabs = [
  { id: 'overview', label: '개요', icon: '📊' },
  { id: 'orders', label: '주문 관리', icon: '📝' },
  { id: 'scheduling', label: '스케줄링 실행', icon: '⚙️' },
  { id: 'results', label: '결과 조회', icon: '📈' },
  { id: 'analytics', label: '분석', icon: '📊' }
];
```

**기능**:
- 실시간 시스템 상태 표시
- 현재 시간 표시
- 탭 기반 네비게이션
- 반응형 디자인

### 2. Dashboard.tsx (스케줄링 결과)
스케줄링 실행 결과를 표시:

```typescript
interface ScheduleRun {
  id: number;
  run_id: string;
  name: string;
  status: string;
  makespan?: number;
  total_orders?: number;
  total_late_days?: number;
  created_at: string;
  completed_at?: string;
}
```

**기능**:
- 스케줄링 실행 기록 목록
- 실행 통계 (총 실행, 완료, 실행 중, 실패)
- 상태별 색상 표시
- 실행 결과 상세 정보

### 3. OrderTable.tsx (주문 관리)
주문 데이터 CRUD 관리:

```typescript
interface Order {
  id: number;
  po_no: string;
  gitem: string;
  gitem_name: string;
  width: number;
  length: number;
  request_amount: number;
  due_date: string;
  created_at: string;
}
```

**기능**:
- 주문 목록 표시 (페이징)
- 주문 생성/수정/삭제
- 정렬 및 필터링
- 실시간 데이터 업데이트

### 4. ProgressMonitor.tsx (진행상황 모니터링)
실시간 스케줄링 진행상황 추적:

```typescript
interface ProgressStep {
  step: string;
  step_name: string;
  status: string;
  progress_percentage: number;
  current_count: number;
  message: string;
  started_at: string;
  completed_at?: string;
}
```

**기능**:
- 5단계 진행상황 실시간 표시
- 프로그레스 바 및 백분율
- 현재 작업 메시지 표시
- 자동 폴링 (2초 간격)

## API 서비스 (api.ts)

### API 클라이언트 설정
```typescript
const API_BASE_URL = 'http://127.0.0.1:8000';

class ApiService {
  // 주문 관리
  async getOrders(): Promise<Order[]>
  async createOrder(order: OrderCreate): Promise<Order>
  async updateOrder(id: number, order: OrderUpdate): Promise<Order>
  async deleteOrder(id: number): Promise<void>
  
  // 스케줄링 관리
  async getScheduleRuns(): Promise<ScheduleRun[]>
  async createScheduleRun(request: ScheduleRequest): Promise<ScheduleRun>
  
  // 진행상황 추적
  async getProgress(runId: string): Promise<ProgressStep[]>
  async getCurrentProgress(runId: string): Promise<ProgressStep | null>
}
```

## 스타일링 시스템

### App.css (글로벌 스타일)
- CSS 리셋
- 유틸리티 클래스 (.loading, .error, .success)
- 버튼 기본 스타일
- 접근성 지원 (focus 스타일)
- 스크롤바 커스텀 스타일

### MainDashboard.css (대시보드 스타일)
- 그라데이션 배경
- 탭 네비게이션 스타일
- 반응형 그리드 레이아웃
- 애니메이션 효과
- 모바일 대응 (768px, 480px 브레이크포인트)

## 주요 기능

### 1. 실시간 데이터 업데이트
```typescript
// 주문 데이터 자동 새로고침
useEffect(() => {
  const interval = setInterval(loadOrders, 30000); // 30초마다
  return () => clearInterval(interval);
}, []);
```

### 2. 진행상황 실시간 모니터링
```typescript
// 스케줄링 진행상황 폴링
useEffect(() => {
  if (activeRun?.status === 'running') {
    const interval = setInterval(loadProgress, 2000); // 2초마다
    return () => clearInterval(interval);
  }
}, [activeRun]);
```

### 3. 에러 핸들링
```typescript
const handleError = (error: any) => {
  console.error('API Error:', error);
  setError(error.message || 'An error occurred');
  setTimeout(() => setError(null), 5000); // 5초 후 자동 제거
};
```

## 실행 방법

### 개발 서버 시작
```bash
cd frontend
npm install  # 처음 한 번만
npm start    # 개발 서버 시작
```

### 빌드 (배포용)
```bash
npm run build
```

### 타입 체크
```bash
npm run type-check  # 타입스크립트 검사
```

## 중요 설정

### package.json 주요 의존성
```json
{
  "dependencies": {
    "react": "^18.x",
    "typescript": "^4.x",
    "@types/react": "^18.x"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  }
}
```

## 사용자 경험

### 반응형 디자인
- **Desktop**: 풀 기능 대시보드
- **Tablet (768px)**: 컴팩트한 네비게이션
- **Mobile (480px)**: 스택 레이아웃

### 접근성
- 키보드 네비게이션 지원
- Focus 상태 시각화
- 스크린 리더 호환
- 색상 대비 준수

### 성능 최적화
- React.memo() 사용으로 불필요한 리렌더링 방지
- 이미지 지연 로딩
- API 요청 최적화 (폴링 간격 조정)

프론트엔드는 완전히 구축되어 사용자가 직관적으로 사용할 수 있는 인터페이스를 제공합니다.