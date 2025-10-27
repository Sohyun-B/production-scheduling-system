# FSD: 생산 스케줄링 최적화 웹 서비스 기능 명세서

## 문서 정보
- **문서 버전**: v1.4
- **작성일**: 2025-10-20
- **최종 수정일**: 2025-10-21
- **기반 문서**: PRD v1.2
- **기술 스택**:
  - Frontend: React 18+ with TypeScript
  - Backend: Node.js with Express
  - Database: PostgreSQL (권장)

---

## 1. 기능 구조 (Feature Map)

```
생산 스케줄링 웹 서비스
├── 인증 및 사용자 관리
│   ├── 로그인/로그아웃
│   └── 사용자 프로필 조회
├── 프로젝트 관리
│   ├── 프로젝트 생성
│   ├── 프로젝트 목록 조회
│   ├── 프로젝트 상세 조회
│   └── 프로젝트 삭제
├── 스케줄링 실행
│   ├── 파라미터 입력
│   ├── 파라미터 검증 (Pre-Validation)
│   ├── 전체 스케줄링 실행
│   ├── 실행 상태 조회 (Polling)
│   ├── 중간 단계 결과 조회 (2-4단계)
│   └── 최종 단계 결과 조회 (5-6단계)
├── 결과 조회 및 시각화
│   ├── 설비별 작업 통계 테이블
│   ├── Gantt Chart 시각화
│   └── 테이블 뷰 (필터링/정렬)
├── 이력 관리
│   ├── 실행 이력 목록 조회
│   ├── 이력 상세 조회
│   └── 이력 비교
└── 기준정보 조회
    ├── 설비정보 조회
    ├── 공정정보 조회
    ├── 라인스피드 조회
    ├── 배합액정보 조회
    └── 기타 마스터 데이터 조회
```

### 기능 간 종속성
```
프로젝트 생성 → 파라미터 입력 → 파라미터 검증 → 스케줄링 실행 → 중간 결과 조회(2-4단계) → 최종 결과 조회(5-6단계)
                                                      ↓
                                                  이력 관리
```

---

## 2. 기능 상세 명세

### 2.1 프로젝트 생성

#### 기능명
**Project Creation**

#### 트리거 조건
- 사용자가 "새 프로젝트 생성" 버튼 클릭
- 인증된 사용자만 접근 가능

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 입력 단계
1. ProjectCreateForm 컴포넌트 렌더링
2. 사용자 입력 데이터 수집:
   - project_name: string (required, max 100자)
   - base_date: Date (required, YYYY-MM-DD 형식)
   - description: string (optional, max 500자)
3. 클라이언트 측 Validation:
   - 필수 필드 확인
   - 날짜 형식 검증 (moment.js 또는 date-fns 사용)
   - 프로젝트명 길이 제한
4. Validation 통과 시 POST /api/v1/projects 호출

// 처리 단계
5. API 응답 대기 (Loading 상태 표시)
6. 성공 응답 시:
   - 생성된 프로젝트 ID를 받아 프로젝트 대시보드로 라우팅
   - Toast 메시지: "프로젝트가 생성되었습니다"
7. 실패 응답 시:
   - 오류 메시지 표시 (Toast 또는 Form 하단)
   - base_date 중복 시: "동일한 기준날짜의 프로젝트가 이미 존재합니다"
```

##### Backend (Express + Node.js)
```javascript
// POST /api/v1/projects
1. Request Body 파싱 및 검증:
   - express-validator 사용
   - 필수 필드 존재 여부
   - 데이터 타입 검증
   
2. 비즈니스 로직 검증:
   - 프로젝트명 중복 확인 (동일 사용자 내)
   - base_date 중복 확인 (중요: 동일 사용자 내에서 같은 base_date 존재 시 생성 불가)
   - 날짜 유효성 검증
   - 과거 날짜 입력 시 경고 로그 기록 (단, 생성은 허용)

3. Database Transaction:
   BEGIN TRANSACTION
   - base_date 중복 체크 쿼리 실행:
     SELECT COUNT(*) FROM projects 
     WHERE created_by = :user_id AND base_date = :base_date
   - 결과가 0이 아니면 409 Conflict 에러 반환
   - projects 테이블에 새 레코드 INSERT
   - UUID 생성 (uuid v4)
   - created_at, updated_at 자동 설정
   - created_by에 인증된 user_id 저장
   COMMIT

4. 응답 생성:
   - 201 Created 상태 코드
   - 생성된 프로젝트 객체 반환
```

#### 입력 데이터 구조 (Frontend → Backend)
```typescript
interface ProjectCreateRequest {
  project_name: string;      // required, max 100자
  base_date: string;         // required, YYYY-MM-DD 형식
  description?: string;      // optional, max 500자
}
```

#### 출력 데이터 구조 (Backend → Frontend)
```typescript
interface ProjectCreateResponse {
  status: 'success';
  message: string;
  data: {
    project_id: string;      // UUID
    project_name: string;
    base_date: string;
    description: string | null;
    status: 'active';
    created_at: string;      // ISO 8601 형식
    created_by: string;      // user_id
  };
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| 프로젝트명 중복 | 409 | "동일한 이름의 프로젝트가 이미 존재합니다" | Toast 오류 메시지 표시 |
| base_date 중복 | 409 | "동일한 기준날짜의 프로젝트가 이미 존재합니다" | Toast 오류 메시지 표시, base_date 필드 하이라이트 |
| 필수 필드 누락 | 400 | "필수 항목을 입력해주세요" | 해당 필드에 오류 표시 |
| 날짜 형식 오류 | 400 | "올바른 날짜 형식이 아닙니다 (YYYY-MM-DD)" | 날짜 필드에 오류 표시 |
| 인증 실패 | 401 | "인증이 필요합니다" | 로그인 페이지로 리다이렉트 |
| DB 연결 실패 | 500 | "서버 오류가 발생했습니다" | 일반 오류 메시지 표시 |

#### 상태 변화 (State Transition)
```
[초기 상태: 프로젝트 목록 페이지]
    ↓ "새 프로젝트" 버튼 클릭
[프로젝트 생성 폼 표시]
    ↓ 폼 입력 및 "생성" 버튼 클릭
[Loading 상태 - API 호출 중]
    ↓ 성공 응답
[프로젝트 대시보드로 이동] (project_id 포함)
    또는
    ↓ 실패 응답 (base_date 중복)
[프로젝트 생성 폼 유지 - 오류 메시지 표시]
```

#### UI 연계
- **컴포넌트**: `ProjectCreateForm`, `ProjectList`
- **라우트**: 
  - 생성 폼: `/projects/new`
  - 대시보드: `/projects/:projectId`

#### 테스트 조건

##### 성공 테스트 케이스
1. 모든 필수 필드 입력 후 생성 성공
2. 설명 필드 생략 후 생성 성공
3. 과거 날짜 입력 시 생성 성공 (경고 없음)

##### 실패 테스트 케이스
1. 프로젝트명 누락 시 400 에러
2. 날짜 형식 오류 (예: "2025/10/20") 시 400 에러
3. 중복 프로젝트명 시 409 에러
4. 동일한 base_date로 프로젝트 생성 시도 시 409 에러
5. 인증 토큰 없이 요청 시 401 에러

##### 경계 조건 테스트
1. 프로젝트명 100자 정확히 입력
2. 프로젝트명 101자 입력 시 오류
3. 설명 500자 정확히 입력
4. 동시에 동일한 base_date로 프로젝트 생성 시도 (Race Condition)

---

### 2.2 스케줄링 파라미터 입력

#### 기능명
**Scheduling Parameter Input**

#### 트리거 조건
- 사용자가 프로젝트 대시보드에서 "새 스케줄 생성" 버튼 클릭
- 유효한 project_id가 존재해야 함

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 입력 단계
1. ParameterInputForm 컴포넌트 렌더링
2. 프로젝트 정보 로드:
   - GET /api/v1/projects/:projectId 호출
   - base_date를 자동으로 표시 (읽기 전용)

3. 필수 파라미터 입력 폼 표시:
   - window_size: number (1~90)
   - yield_period: number (1~365)

4. 선택 파라미터 동적 입력 UI:
   - machine_unavailable: 배열 입력
     - "사용불가 시간대 추가" 버튼으로 동적 추가/삭제
     - machine_id: select (설비 목록 API 조회)
     - start_time, end_time: datetime-local input
   - process_restrictions: 배열 입력
     - machine_id, restricted_process 입력
   - dedicated_equipment: 배열 입력
     - machine_id, dedicated_process 입력

5. 클라이언트 측 Validation:
   - 필수 필드 확인
   - 숫자 범위 검증
   - 날짜 시간 형식 검증
   - 시작 시간 < 종료 시간 검증

6. "검증 시작" 버튼 클릭 시:
   - POST /api/v1/schedules/validate 호출
   - 파라미터 데이터 전송
```

##### Backend (Express + Node.js)
```javascript
// POST /api/v1/schedules/validate
1. Request Body 파싱 및 검증:
   - project_id 존재 여부 확인
   - 필수 파라미터 검증
   - 선택 파라미터 배열 구조 검증

2. 프로젝트 정보 조회:
   - projects 테이블에서 base_date 확인
   - 프로젝트 상태가 'active'인지 확인

3. 파라미터 저장 (임시):
   - scheduling_parameters 테이블에 INSERT
   - status: 'pending'
   - 이후 검증 단계에서 사용

4. 응답 생성:
   - 200 OK
   - parameter_id 반환 (검증 단계에서 사용)
```

#### 입력 데이터 구조 (Frontend → Backend)
```typescript
interface SchedulingParameterRequest {
  project_id: string;
  required: {
    base_date: string;        // YYYY-MM-DD (프로젝트에서 자동 설정)
    window_size: number;      // 1~90
    yield_period: number;     // 1~365
  };
  optional: {
    machine_unavailable?: Array<{
      machine_id: string;
      start_time: string;     // ISO 8601
      end_time: string;       // ISO 8601
    }>;
    process_restrictions?: Array<{
      machine_id: string;
      restricted_process: string;
    }>;
    dedicated_equipment?: Array<{
      machine_id: string;
      dedicated_process: string;
    }>;
  };
}
```

#### 출력 데이터 구조 (Backend → Frontend)
```typescript
interface ParameterInputResponse {
  status: 'success';
  message: string;
  data: {
    parameter_id: string;     // UUID
    project_id: string;
    validation_status: 'pending';
  };
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| 필수 파라미터 누락 | 400 | "필수 항목을 입력해주세요" | 해당 필드 오류 표시 |
| 숫자 범위 초과 | 400 | "window_size는 1~90 사이여야 합니다" | 필드 오류 표시 |
| 날짜 형식 오류 | 400 | "올바른 날짜 형식이 아닙니다" | 필드 오류 표시 |
| 존재하지 않는 프로젝트 | 404 | "프로젝트를 찾을 수 없습니다" | 프로젝트 목록으로 리다이렉트 |
| 시작 시간 > 종료 시간 | 400 | "종료 시간이 시작 시간보다 빠릅니다" | 해당 행 오류 표시 |

#### 상태 변화
```
[프로젝트 대시보드]
    ↓ "새 스케줄 생성" 클릭
[파라미터 입력 폼 표시]
    ↓ 폼 입력
[입력 데이터 수집 중]
    ↓ "검증 시작" 클릭
[Loading - 파라미터 저장 중]
    ↓ 성공
[검증 대기 상태] → 2.3 파라미터 검증으로 이동
```

#### UI 연계
- **컴포넌트**: `ParameterInputForm`, `MachineUnavailableInput`, `ProcessRestrictionInput`
- **라우트**: `/projects/:projectId/schedules/new`

#### 테스트 조건

##### 성공 테스트 케이스
1. 필수 파라미터만 입력 후 저장 성공
2. 선택 파라미터 포함하여 저장 성공
3. 동일한 설비에 여러 사용불가 시간대 추가

##### 실패 테스트 케이스
1. window_size 0 입력 시 오류
2. yield_period 400 입력 시 오류
3. 존재하지 않는 machine_id 입력 시 오류

##### 경계 조건 테스트
1. window_size 1, 90 (경계값) 입력
2. 선택 파라미터 배열이 비어있는 경우
3. 선택 파라미터 배열에 50개 이상 항목

---

### 2.3 파라미터 검증 (Pre-Validation)

#### 기능명
**Parameter Validation (Pre-Validation)**

#### 트리거 조건
- 파라미터 입력 완료 후 자동 실행 (2.2에서 parameter_id 생성 직후)
- 또는 사용자가 명시적으로 "검증 시작" 버튼 클릭

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 검증 시작
1. POST /api/v1/schedules/validate/:parameterId 호출
2. Loading 화면 표시:
   - 스피너 애니메이션
   - "데이터 검증 중..." 메시지

3. Polling으로 검증 상태 확인:
   - GET /api/v1/schedules/validate/:parameterId/status
   - 3초 간격으로 호출
   - status가 'completed' 또는 'error'일 때까지 반복

4. 검증 완료 후 결과 페이지 렌더링:
   - ValidationResultPage 컴포넌트
   
5. 성공 시 (validation_status: 'success'):
   - ✅ "검증 완료. 스케줄링 실행 가능합니다." 메시지
   - 데이터 요약 표시 (총 주문 수, 설비 수 등)
   - "스케줄링 실행" 버튼 활성화

6. 실패 시 (validation_status: 'error'):
   - ❌ "데이터 검증에 실패했습니다" 메시지
   - 테이블별 오류 요약 표시:
     - 테이블명, 전체 행 수, 오류 행 수
   - 오류가 있는 테이블에 "상세보기" 버튼 표시
   
7. "상세보기" 버튼 클릭 시:
   - Modal 또는 Expandable Panel로 오류 상세 표시
   - 오류 데이터: 행 번호, 컬럼명, 현재 값, 오류 메시지
   - 페이지네이션 (10개씩 표시)
```

##### Backend (Express + Node.js)
```javascript
// POST /api/v1/schedules/validate/:parameterId
1. Parameter 정보 조회:
   - scheduling_parameters 테이블에서 조회
   - project_id를 통해 base_date 확인

2. 기준정보 테이블 로드:
   - DB에서 다음 테이블 전체 조회:
     * equipment (설비정보)
     * processes (공정정보)
     * orders (주문정보)
     * yield_rates (수율정보)
     * changeover_times (교체시간정보)
     * line_speeds (라인스피드-Gitem등)
     * mixture_info (배합액정보)
   - 각 테이블을 메모리에 로드 (캐싱 고려)

3. Python 알고리즘 호출 (Child Process):
   - child_process.spawn() 사용
   - 0단계 (데이터 전처리):
     * 데이터 타입 변환
     * 결측치 확인
     * 참조 무결성 검증
   - 1단계 (초기 검증):
     * 파라미터와 기준정보 일관성 검증
     * 제약조건 충족 여부 확인
     * 스케줄링 실행 가능성 판단
   
4. 알고리즘 실행 중 상태 업데이트:
   - scheduling_parameters 테이블의 validation_status 필드 업데이트
   - 'pending' → 'running' → 'completed' 또는 'error'

5. 검증 결과 처리:
   a) 성공 시:
      - validation_results 테이블에 요약 정보 저장
      - data_summary (주문 수, 설비 수 등)
      
   b) 실패 시:
      - validation_errors 테이블에 오류 상세 저장
      - 테이블별, 행별 오류 정보
      - 오류 메시지 및 현재 값

6. 응답 생성:
   - 200 OK
   - validation_id 반환
```

```javascript
// GET /api/v1/schedules/validate/:parameterId/status
1. scheduling_parameters 테이블에서 validation_status 조회
2. 현재 상태 반환:
   - 'pending', 'running', 'completed', 'error'
```

```javascript
// GET /api/v1/schedules/validate/:parameterId/result
1. validation_status 확인
2. 성공 시:
   - validation_results 테이블에서 요약 정보 조회
   
3. 실패 시:
   - validation_errors 테이블에서 오류 목록 조회
   - 테이블별로 그룹핑
   - 페이지네이션 적용 (query param: page, limit)
```

#### 입력 데이터 구조
- parameter_id (URL 파라미터)
- 사용자 입력 파라미터 (DB에서 조회)
- 기준정보 테이블 전체 데이터 (DB에서 조회)

#### 출력 데이터 구조

##### 검증 성공 시
```typescript
interface ValidationSuccessResponse {
  validation_status: 'success';
  message: string;
  master_data_loaded: true;
  details: {
    data_summary: {
      total_orders: number;
      total_machines: number;
      total_processes: number;
      total_line_speeds: number;
      total_mixture_info: number;
    };
  };
}
```

##### 검증 실패 시
```typescript
interface ValidationErrorResponse {
  validation_status: 'error';
  message: string;
  master_data_loaded: boolean;
  table_summary: Array<{
    table_name: string;
    total_rows: number;
    error_rows: number;
    has_errors: boolean;
  }>;
  error_details: Array<{
    table_name: string;
    errors: Array<{
      row_number: number;
      column: string;
      current_value: any;
      error_message: string;
    }>;
  }>;
  pagination?: {
    current_page: number;
    total_pages: number;
    per_page: number;
  };
}
```

##### 상태 조회 응답
```typescript
interface ValidationStatusResponse {
  validation_status: 'pending' | 'running' | 'completed' | 'error';
  current_step?: string;  // 예: "데이터 전처리 중"
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| parameter_id 존재하지 않음 | 404 | "파라미터를 찾을 수 없습니다" | 프로젝트 대시보드로 리다이렉트 |
| DB 기준정보 테이블 누락 | 500 | "기준정보 테이블을 로드할 수 없습니다" | 오류 메시지 표시 및 재시도 옵션 |
| 알고리즘 실행 타임아웃 (3분) | 504 | "검증 시간이 초과되었습니다" | 재시도 버튼 표시 |
| 알고리즘 내부 오류 | 500 | "검증 중 오류가 발생했습니다" | 오류 로그 표시 및 지원 요청 안내 |

#### 상태 변화
```
[파라미터 입력 완료]
    ↓ POST /validate/:parameterId
[검증 시작 - status: 'pending']
    ↓
[검증 실행 중 - status: 'running']
    ↓ Polling으로 상태 확인
[검증 완료 - status: 'completed' 또는 'error']
    ↓
[성공] → 스케줄링 실행 가능
    또는
[실패] → 오류 상세 페이지 표시
```

#### UI 연계
- **컴포넌트**: 
  - `ValidationLoadingScreen`
  - `ValidationResultPage`
  - `ValidationErrorModal`
  - `ErrorDetailTable`
- **라우트**: `/projects/:projectId/schedules/:parameterId/validation`

#### 테스트 조건

##### 성공 테스트 케이스
1. 모든 기준정보가 유효하고 파라미터가 올바른 경우
2. 선택 파라미터 없이 필수 파라미터만으로 검증 성공
3. 대용량 기준정보 (주문 10,000개) 검증 성공

##### 실패 테스트 케이스
1. 공정정보 테이블의 공정시간 필드에 null 값
2. 존재하지 않는 machine_id 참조
3. 라인스피드 테이블의 속도 필드에 문자열
4. 알고리즘 실행 중 타임아웃

##### 경계 조건 테스트
1. 오류 데이터가 0개인 경우 (성공)
2. 오류 데이터가 100개 이상인 경우 (페이지네이션)
3. 기준정보 테이블이 완전히 비어있는 경우

---

### 2.4 스케줄링 실행 (Full Scheduling)

#### 기능명
**Full Scheduling Execution**

#### 트리거 조건
- 검증 성공 후 "스케줄링 실행" 버튼 클릭
- validation_status가 'success'여야 함

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 실행 시작
1. POST /api/v1/schedules/execute 호출
   - parameter_id 전달

2. 실행 진행 화면 표시:
   - SchedulingProgressPage 컴포넌트
   - 현재 실행 중인 단계 표시

3. Polling으로 실행 상태 확인:
   - GET /api/v1/schedules/execute/:executionId/status
   - 5초 간격으로 호출
   - status 및 current_stage 확인

4. 현재 단계 업데이트:
   - current_step 텍스트 표시
     예: "2단계: 주문 순서 생성 중"
     예: "4단계: DAG 시스템 구축 중"

5. 중간 단계 완료 처리:
   a) stage_2_4_completed: true 감지 시
      - 자동으로 중간 결과 페이지로 이동
      - /projects/:projectId/schedules/:executionId/stage-2-4
      
   b) stage_5_6_completed: true 감지 시
      - 자동으로 최종 결과 페이지로 이동
      - /projects/:projectId/schedules/:executionId/result

6. 실행 실패 시:
   - status: 'failed'
   - 오류 메시지 표시
   - "재시도" 및 "파라미터 수정" 버튼

7. 실행 취소 기능:
   - "취소" 버튼 클릭 시
   - DELETE /api/v1/schedules/execute/:executionId 호출
   - 확인 Modal: "실행을 중단하시겠습니까?"
```

##### Backend (Express + Node.js)
```javascript
// POST /api/v1/schedules/execute
1. Parameter 및 검증 결과 조회:
   - scheduling_parameters 테이블에서 parameter_id로 조회
   - validation_status가 'success'인지 확인
   
2. Execution 레코드 생성:
   - schedule_executions 테이블에 INSERT
   - execution_id: UUID
   - status: 'queued'
   - current_stage: 'initial'
   - stage_2_4_completed: false
   - stage_5_6_completed: false
   - created_at: 현재 시간

3. 비동기 작업 큐에 등록:
   - Bull Queue 또는 Kafka 사용
   - Job 데이터: parameter_id, execution_id
   
4. 즉시 응답 반환:
   - 202 Accepted
   - execution_id 반환

// Background Worker (Queue Consumer)
5. 큐에서 Job 수신:
   - 기준정보 및 파라미터 로드
   
6. 실행 상태 업데이트:
   - status: 'queued' → 'running'
   - current_stage: 'stage_2_4'
   
7. Python 알고리즘 2-4단계 실행:
   - child_process.spawn() 사용
   - 2단계: generate_order_sequence
   - 3단계: yield_prediction
   - 4단계: create_complete_dag_system
   
8. 2-4단계 완료:
   - 중간 결과를 stage_2_4_results 테이블에 저장
   - stage_2_4_completed: true
   - current_stage: 'stage_2_4_completed'
   - status: 'running' (계속 실행)

9. Python 알고리즘 5-6단계 자동 실행:
   - current_stage: 'stage_5_6'로 업데이트
   - 5단계: DispatchPriorityStrategy.execute
   - 6단계: create_results
    
10. 5-6단계 완료:
    - 최종 결과를 schedule_results 테이블에 저장
    - stage_5_6_completed: true
    - current_stage: 'stage_5_6_completed'
    - status: 'completed'
    - 상세 스케줄은 schedule_details 테이블에 저장
    - completed_at: 현재 시간

11. 단계별 상태 업데이트:
    - 알고리즘에서 stdout으로 현재 단계 출력
    - Worker가 이를 파싱하여 DB 업데이트
    - current_step 필드

12. 실행 실패:
    - status: 'running' → 'failed'
    - error_message 필드에 오류 내용 저장
    - failed_stage 필드에 실패한 단계 저장
    - 로그 파일 저장
```

```javascript
// GET /api/v1/schedules/execute/:executionId/status
1. schedule_executions 테이블에서 조회
2. 현재 상태 반환:
   - status, current_step, current_stage
   - stage_2_4_completed, stage_5_6_completed
   - error_message
```

```javascript
// DELETE /api/v1/schedules/execute/:executionId
1. status 확인:
   - 'running'인 경우만 취소 가능
   
2. 알고리즘 프로세스 종료:
   - Child Process에 SIGTERM 시그널 전송
   
3. 상태 업데이트:
   - status: 'cancelled'
   - cancelled_at: 현재 시간
   
4. 리소스 정리:
   - 임시 파일 삭제
   - 메모리 해제
```

#### 입력 데이터 구조
```typescript
interface SchedulingExecuteRequest {
  parameter_id: string;
}
```

#### 출력 데이터 구조

##### 실행 시작 응답
```typescript
interface ExecutionStartResponse {
  status: 'success';
  message: string;
  data: {
    execution_id: string;
    status: 'queued';
    current_stage: 'initial';
    created_at: string;
  };
}
```

##### 상태 조회 응답
```typescript
interface ExecutionStatusResponse {
  execution_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  current_step: string;    // "3단계: 수율 예측 중"
  current_stage: 'initial' | 'stage_2_4' | 'stage_2_4_completed' | 'stage_5_6' | 'stage_5_6_completed';
  stage_2_4_completed: boolean;
  stage_5_6_completed: boolean;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  failed_stage?: string;
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| 검증 미완료 상태에서 실행 시도 | 400 | "검증을 먼저 완료해주세요" | 검증 페이지로 리다이렉트 |
| 알고리즘 내부 오류 | 500 | "스케줄링 실행 중 오류가 발생했습니다" | 오류 메시지 및 재시도 버튼 |
| 타임아웃 (5분) | 504 | "실행 시간이 초과되었습니다" | 재시도 버튼 및 지원 요청 |
| 서버 리소스 부족 | 503 | "서버가 과부하 상태입니다. 잠시 후 다시 시도해주세요" | 재시도 안내 |
| 실행 취소 요청 | 200 | "실행이 취소되었습니다" | 프로젝트 대시보드로 이동 |

#### 상태 변화
```
[검증 성공 상태]
    ↓ "스케줄링 실행" 버튼 클릭
[실행 요청 - status: 'queued', stage: 'initial']
    ↓ Queue에서 Job 처리 시작
[실행 중 - status: 'running', stage: 'stage_2_4']
    ↓ 2-4단계 실행
[2-4단계 완료 - status: 'running', stage: 'stage_2_4_completed']
    ↓ 자동으로 5-6단계 실행 시작
[실행 중 - status: 'running', stage: 'stage_5_6']
    ↓ 5-6단계 실행
[5-6단계 완료 - status: 'completed', stage: 'stage_5_6_completed']
    ↓ Frontend에서 자동 감지 및 라우팅
[최종 결과 페이지 표시]

또는

[실행 중]
    ↓ 오류 발생
[실행 실패 - status: 'failed']
    ↓ 오류 메시지 표시
[재시도 또는 파라미터 수정]
```

#### UI 연계
- **컴포넌트**: 
  - `SchedulingProgressPage`
  - `CurrentStepIndicator`
  - `CancelExecutionModal`
- **라우트**: `/projects/:projectId/schedules/:executionId/progress`

#### 테스트 조건

##### 성공 테스트 케이스
1. 검증 성공 후 전체 스케줄링 실행 완료
2. 2-4단계 완료 후 자동으로 중간 결과 페이지 이동
3. 5-6단계 완료 후 자동으로 최종 결과 페이지 이동
4. 모든 단계가 순차적으로 실행됨

##### 실패 테스트 케이스
1. 검증 미완료 상태에서 실행 시도 시 오류
2. 알고리즘 실행 중 예외 발생 시 'failed' 상태
3. 타임아웃 발생 시 적절한 오류 처리

##### 경계 조건 테스트
1. 매우 작은 입력 (주문 1개)
2. 매우 큰 입력 (주문 10,000개)
3. 실행 중 취소 요청
4. 동시에 여러 실행 요청 (큐잉 동작 확인)

---

### 2.5 중간 단계 결과 조회 (2-4단계)

#### 기능명
**Stage 2-4 Intermediate Results**

#### 트리거 조건
- 2-4단계 (generate_order_sequence → yield_prediction → create_complete_dag_system) 실행 완료
- stage_2_4_completed가 true일 때 Frontend에서 자동 이동

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 중간 결과 페이지 자동 로드
1. Polling 중 stage_2_4_completed: true 감지
2. 자동으로 /projects/:projectId/schedules/:executionId/stage-2-4로 라우팅
3. GET /api/v1/schedules/execute/:executionId/stage-2-4 호출
4. Stage2_4ResultPage 컴포넌트 렌더링

5. 결과 표시:
   a) 실행 정보 카드:
      - 실행 ID, 시작 시간, 2-4단계 완료 시간
      - 소요 시간

6. 안내 메시지:
   - "2-4단계가 완료되었습니다. 5-6단계가 자동으로 실행 중입니다."
   - 실행 상태 인디케이터 표시
```

##### Backend (Express + Node.js)
```javascript
// GET /api/v1/schedules/execute/:executionId/stage-2-4
1. schedule_executions 테이블에서 execution_id로 조회:
   - stage_2_4_completed가 true인지 확인
   
2. 응답 데이터 구조화:
   - execution_info
```

#### 입력 데이터
- execution_id (URL 파라미터)

#### 출력 데이터 구조
```typescript
interface Stage2_4ResultResponse {
  execution_id: string;
  execution_info: {
    started_at: string;
    stage_2_4_completed_at: string;
    duration: number;  // 초 단위
  };
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| execution_id 존재하지 않음 | 404 | "실행 결과를 찾을 수 없습니다" | 프로젝트 대시보드로 리다이렉트 |
| 2-4단계 미완료 상태 | 400 | "2-4단계가 아직 완료되지 않았습니다" | 진행 페이지로 리다이렉트 |

#### 상태 변화
```
[2-4단계 완료 - stage_2_4_completed: true]
    ↓ Frontend가 자동 감지
[자동 라우팅]
    ↓ GET /stage-2-4
[중간 결과 데이터 로딩]
    ↓ 데이터 수신
[중간 결과 페이지 렌더링]
    (백그라운드에서 5-6단계 자동 실행 중)
```

#### UI 연계
- **컴포넌트**: 
  - `Stage2_4ResultPage`
  - `ExecutionInfoCard`
  - `ExecutionStatusBanner`
- **라우트**: `/projects/:projectId/schedules/:executionId/stage-2-4`

#### 테스트 조건

##### 성공 테스트 케이스
1. 2-4단계 완료 후 중간 결과 정상 조회
2. 백그라운드에서 5-6단계 실행 중임을 표시

##### 실패 테스트 케이스
1. 2-4단계 미완료 상태에서 접근 시 400 에러
2. 존재하지 않는 execution_id로 접근 시 404 에러

---

### 2.6 최종 단계 결과 조회 (5-6단계)

#### 기능명
**Stage 5-6 Final Results**

#### 트리거 조건
- 5-6단계 (DispatchPriorityStrategy.execute → create_results) 실행 완료
- stage_5_6_completed가 true이고 status가 'completed'일 때 Frontend에서 자동 이동

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 최종 결과 페이지 자동 로드
1. Polling 중 stage_5_6_completed: true 및 status: 'completed' 감지
2. 자동으로 /projects/:projectId/schedules/:executionId/result로 라우팅
3. GET /api/v1/schedules/execute/:executionId/result 호출
4. SchedulingResultPage 컴포넌트 렌더링

5. 탭 기반 결과 표시:
   Tab 1: "설비별 통계"
   Tab 2: "Gantt Chart"
   Tab 3: "스케줄 상세"

6. Tab 1: 설비별 통계 테이블
   - EquipmentStatisticsTable 컴포넌트
   - 테이블 컬럼 구조:
     | 장비명 | 작업시간(h) | 가동율(%) | 교체시간(h) | 교체Loss율(%) | 대기시간(h) | 대기Loss율(%) | 계(h) |
     |--------|------------|-----------|-------------|--------------|-------------|--------------|-------|
     | M001   | 120.5      | 87.3      | 12.3        | 8.9          | 5.2         | 3.8          | 138.0 |
     | M002   | 115.2      | 83.5      | 15.1        | 10.9         | 7.7         | 5.6          | 138.0 |
     | ...    | ...        | ...       | ...         | ...          | ...         | ...          | ...   |
     | 합계   | 1205.0     | 85.2      | 135.5       | 9.5          | 72.5        | 5.3          | 1413.0|
   
   - 정렬 기능 (각 컬럼별)
   - 필터링 기능 (장비명 검색)
   - 페이지네이션

7. Tab 2: Gantt Chart 섹션
   - GanttChart 컴포넌트
   - 라이브러리: dhtmlx-gantt 또는 react-gantt-chart
   - X축: 시간 (날짜/시간)
   - Y축: 설비 (Machine)
   - 작업 블록:
     * 색상: 공정별로 구분 (color mapping)
     * 호버 시 툴팁:
       - 작업 ID, 공정명
       - 시작 시간, 종료 시간, 소요 시간
       - 교체시간, 대기시간
   - 줌 인/아웃 기능
   - 시간대별 필터링

8. Tab 3: 스케줄 상세 테이블
   - ScheduleTable 컴포넌트
   - 컬럼:
     * Job ID, Machine ID, Process Name
     * Start Time, End Time, Duration
     * Changeover Time, Waiting Time
   - 기능:
     * 정렬 (각 컬럼별 오름차순/내림차순)
     * 필터링 (Machine, Process 선택)
     * 검색 (Job ID, Process Name)
     * 페이지네이션 (50개씩)

9. 데이터 상호작용:
   - Gantt Chart의 작업 블록 클릭 시:
     * Tab 3(스케줄 상세)로 자동 전환
     * 테이블 뷰의 해당 행으로 스크롤
     * 해당 행 하이라이트
   - 테이블의 행 클릭 시:
     * Tab 2(Gantt Chart)로 자동 전환
     * Gantt Chart의 해당 작업 블록 하이라이트

10. 액션 버튼:
    - "결과 다운로드" 버튼:
      * Tab 3(스케줄 상세 테이블)의 데이터를 Excel 파일로 다운로드
      * 파일명: "스케줄_결과_{execution_id}_{날짜}.xlsx"
```

##### Backend (Express + Node.js)
```javascript
// GET /api/v1/schedules/execute/:executionId/result
1. schedule_executions 테이블에서 execution_id로 조회:
   - status가 'completed'인지 확인
   
2. 설비별 통계 데이터 계산:
   - schedule_details 테이블에서 설비별로 집계:
     * 작업시간: SUM(duration) WHERE 작업 블록
     * 교체시간: SUM(changeover_time)
     * 대기시간: SUM(waiting_time)
     * 계(총 시간): 작업시간 + 교체시간 + 대기시간
   - 가동율 계산: (작업시간 / 계) * 100
   - 교체 Loss율: (교체시간 / 계) * 100
   - 대기 Loss율: (대기시간 / 계) * 100
   
3. 상세 스케줄 데이터 조회:
   - schedule_details 테이블에서 전체 작업 리스트 조회
   - JOIN: equipment, processes 테이블
   - 정렬: start_time 오름차순
   
4. 응답 데이터 구조화:
   - equipment_statistics 배열 (설비별 통계)
   - schedule 배열 (상세 작업 리스트)
   - metadata
```

#### 입력 데이터
- execution_id (URL 파라미터)

#### 출력 데이터 구조
```typescript
interface SchedulingResultResponse {
  execution_id: string;
  equipment_statistics: Array<{
    machine_id: string;
    machine_name: string;
    work_time: number;           // 작업시간 (시간 단위)
    utilization_rate: number;    // 가동율 (%)
    changeover_time: number;     // 교체시간 (시간 단위)
    changeover_loss_rate: number; // 교체 Loss율 (%)
    waiting_time: number;        // 대기시간 (시간 단위)
    waiting_loss_rate: number;   // 대기 Loss율 (%)
    total_time: number;          // 계 (시간 단위)
  }>;
  schedule: Array<{
    job_id: string;
    machine_id: string;
    machine_name: string;
    process_name: string;
    process_code: string;
    start_time: string;          // ISO 8601
    end_time: string;            // ISO 8601
    duration: number;            // 시간 단위
    changeover_time: number;
    waiting_time: number;
    color?: string;              // 공정별 색상 (optional)
  }>;
  metadata: {
    created_at: string;
    completed_at: string;
    parameters: {
      base_date: string;
      window_size: number;
      yield_period: number;
    };
  };
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| execution_id 존재하지 않음 | 404 | "실행 결과를 찾을 수 없습니다" | 이력 페이지로 리다이렉트 |
| 실행 상태가 'completed'가 아님 | 400 | "아직 실행이 완료되지 않았습니다" | 진행 페이지로 리다이렉트 |
| 결과 데이터 손상 | 500 | "결과 데이터를 불러올 수 없습니다" | 오류 메시지 및 재시도 |

#### 상태 변화
```
[5-6단계 완료 - status: 'completed']
    ↓ Frontend가 자동 감지
[자동 라우팅]
    ↓ GET /result
[결과 데이터 로딩]
    ↓ 데이터 수신
[최종 결과 페이지 렌더링]
    ↓ 탭 간 전환
[설비별 통계] ↔ [Gantt Chart] ↔ [스케줄 상세]
    ↓ 사용자 상호작용
[데이터 다운로드 (Excel)]
```

#### UI 연계
- **컴포넌트**: 
  - `SchedulingResultPage`
  - `ResultTabs`
  - `EquipmentStatisticsTable`
  - `GanttChart`
  - `ScheduleTable`
  - `FilterPanel`
  - `ExportExcelButton`
- **라우트**: `/projects/:projectId/schedules/:executionId/result`

#### 테스트 조건

##### 성공 테스트 케이스
1. 실행 완료 후 결과 페이지 정상 로드
2. 설비별 통계 테이블 정확하게 표시
3. Gantt Chart에서 작업 블록 정상 렌더링
4. 스케줄 상세 테이블 정렬/필터링 정상 동작
5. 탭 간 전환 정상 동작
6. Excel 다운로드 정상 동작
7. Gantt Chart 클릭 시 스케줄 상세 탭으로 전환 및 해당 행 하이라이트

##### 실패 테스트 케이스
1. 존재하지 않는 execution_id로 접근 시 404
2. 실행 중인 상태에서 결과 조회 시 400

##### 경계 조건 테스트
1. 작업이 0개인 경우 (빈 스케줄)
2. 작업이 10,000개 이상인 경우 (성능 테스트)
3. 동일한 시간대에 여러 작업이 겹치는 경우
4. 모든 설비의 가동율이 0%인 경우

---

### 2.7 스케줄링 이력 관리

#### 기능명
**Scheduling History Management**

#### 트리거 조건
- 사용자가 "이력" 메뉴 클릭
- 프로젝트 대시보드에서 "과거 실행 보기" 클릭

#### 처리 로직

##### Frontend (React + TypeScript)
```typescript
// 이력 목록 로드
1. GET /api/v1/schedules/history?projectId=:projectId 호출
   - Query Params:
     * page: number (기본값 1)
     * limit: number (기본값 20)
     * status: string[] (optional, 필터)

2. HistoryListPage 컴포넌트 렌더링:
   - 필터 패널:
     * 상태 필터 (completed, failed, cancelled)
     * "필터 적용" 버튼
   - 이력 리스트:
     * 카드 형태로 표시
     * 각 카드 정보:
       - 실행 날짜/시간
       - 파라미터 요약 (window_size, yield_period)
       - 상태 배지 (completed: 녹색, failed: 빨간색)
       - KPI 요약 (총 작업 수, 평균 가동율 등)
     * 최신순 정렬
     * 페이지네이션

3. 이력 카드 클릭:
   - 단일 클릭: 상세 결과 페이지로 이동
     (/projects/:projectId/schedules/:executionId/result)
   
4. 이력 비교 기능:
   - 각 카드에 체크박스 추가
   - 최대 2개 선택 가능
   - 2개 선택 시 "비교" 버튼 활성화
   - "비교" 버튼 클릭:
     * /projects/:projectId/schedules/compare?exec1=:id1&exec2=:id2

5. 비교 대시보드 (ComparisonPage):
   - 좌우 분할 레이아웃
   - 왼쪽: 첫 번째 실행 결과
   - 오른쪽: 두 번째 실행 결과
   - 각각 표시:
     * 파라미터 비교 테이블
     * 설비별 통계 비교 (차트 형태, 증감률 표시)
     * Gantt Chart 병렬 표시
   - 하단: 차이점 요약
     * "실행 2가 실행 1 대비 평균 가동율 +3.5% 향상"
```

##### Backend (Express + Node.js)
```javascript
// GET /api/v1/schedules/history
1. Query Params 파싱:
   - projectId (필수)
   - page, limit (페이지네이션)
   - status (필터)

2. schedule_executions 테이블 조회:
   - WHERE: project_id = :projectId
   - AND: status IN (:status) (optional)
   - ORDER BY: created_at DESC
   - LIMIT, OFFSET 적용

3. 각 실행에 대해 설비별 통계 요약 조회:
   - schedule_results 테이블 또는 집계 쿼리 실행
   - 주요 지표만 선택 (total_jobs, average_utilization 등)

4. 응답 데이터 구조화:
   - history 배열
   - total_count (전체 이력 수)
   - pagination 정보
```

```javascript
// GET /api/v1/schedules/compare?exec1=:id1&exec2=:id2
1. 두 execution_id에 대해 결과 조회:
   - GET /result 로직 재사용
   
2. 비교 데이터 계산:
   - 설비별 통계 차이 계산 (절대값 및 증감률)
   - 파라미터 차이 표시
   
3. 응답 데이터 구조화:
   - execution1, execution2 객체
   - comparison 객체 (차이점)
```

#### 입력 데이터 구조
```typescript
interface HistoryQueryParams {
  projectId: string;
  page?: number;
  limit?: number;
  status?: ('completed' | 'failed' | 'cancelled')[];
}

interface CompareQueryParams {
  exec1: string;
  exec2: string;
}
```

#### 출력 데이터 구조

##### 이력 목록 응답
```typescript
interface HistoryListResponse {
  history: Array<{
    execution_id: string;
    project_id: string;
    created_at: string;
    completed_at?: string;
    parameters: {
      base_date: string;
      window_size: number;
      yield_period: number;
    };
    status: 'completed' | 'failed' | 'cancelled';
    statistics_summary: {
      total_jobs: number;
      average_utilization: number;
      average_changeover_loss_rate: number;
      average_waiting_loss_rate: number;
    };
  }>;
  total_count: number;
  pagination: {
    current_page: number;
    total_pages: number;
    per_page: number;
  };
}
```

##### 비교 응답
```typescript
interface ComparisonResponse {
  execution1: SchedulingResultResponse;
  execution2: SchedulingResultResponse;
  comparison: {
    equipment_statistics_differences: Array<{
      machine_id: string;
      machine_name: string;
      work_time_diff: number;
      utilization_rate_diff: number;
      changeover_time_diff: number;
      changeover_loss_rate_diff: number;
      waiting_time_diff: number;
      waiting_loss_rate_diff: number;
    }>;
    overall_differences: {
      total_jobs: {
        exec1: number;
        exec2: number;
        difference: number;
        change_rate: number;  // %
      };
      average_utilization: {
        exec1: number;
        exec2: number;
        difference: number;
        change_rate: number;
      };
      average_changeover_loss_rate: {
        exec1: number;
        exec2: number;
        difference: number;
        change_rate: number;
      };
      average_waiting_loss_rate: {
        exec1: number;
        exec2: number;
        difference: number;
        change_rate: number;
      };
    };
    parameter_differences: {
      window_size: {
        exec1: number;
        exec2: number;
        is_different: boolean;
      };
      yield_period: {
        exec1: number;
        exec2: number;
        is_different: boolean;
      };
    };
    summary: string;  // "실행 2가 실행 1 대비 평균 가동율 +3.5% 향상"
  };
}
```

#### 예외 및 오류 처리

| 오류 상황 | HTTP 코드 | 응답 메시지 | Frontend 처리 |
|-----------|-----------|-------------|---------------|
| projectId 존재하지 않음 | 404 | "프로젝트를 찾을 수 없습니다" | 프로젝트 목록으로 리다이렉트 |
| 이력이 없음 | 200 | 빈 배열 반환 | "실행 이력이 없습니다" 메시지 표시 |
| 비교 시 1개 또는 3개 이상 선택 | 400 | "정확히 2개의 실행을 선택해주세요" | 체크박스 선택 제한 |
| 비교 시 존재하지 않는 execution_id | 404 | "실행 결과를 찾을 수 없습니다" | 오류 메시지 표시 |

#### 상태 변화
```
[프로젝트 대시보드]
    ↓ "이력" 메뉴 클릭
[이력 목록 로딩]
    ↓ GET /history
[이력 목록 표시]
    ↓ 카드 클릭 or 비교 선택
[상세 결과 페이지] or [비교 대시보드]
```

#### UI 연계
- **컴포넌트**: 
  - `HistoryListPage`
  - `HistoryCard`
  - `StatusFilterPanel`
  - `ComparisonPage`
  - `EquipmentStatisticsComparisonChart`
- **라우트**: 
  - 이력 목록: `/projects/:projectId/history`
  - 비교: `/projects/:projectId/schedules/compare`

#### 테스트 조건

##### 성공 테스트 케이스
1. 이력 목록 정상 로드 및 페이지네이션
2. 상태 필터 (completed, failed) 정상 동작
3. 2개 실행 선택 후 비교 페이지 정상 표시
4. 설비별 통계 차이 계산 정확성

##### 실패 테스트 케이스
1. 이력이 0개인 경우 빈 목록 표시
2. 1개 또는 3개 선택 후 비교 시도 시 오류
3. 존재하지 않는 projectId로 조회 시 404

##### 경계 조건 테스트
1. 이력이 100개 이상인 경우 (페이지네이션 테스트)
2. 파라미터가 동일한 두 실행 비교
3. 파라미터가 매우 상이한 두 실행 비교 (경고 메시지)

---

## 3. 데이터 흐름 (Data Flow)

### 3.1 전체 데이터 흐름 다이어그램
```
[사용자] 
    ↓ 프로젝트 생성
[Frontend: ProjectCreateForm]
    ↓ POST /api/v1/projects
[Backend: Express API]
    ↓ base_date 중복 체크 및 INSERT
[Database: projects 테이블]
    ↓ project_id 반환
[Frontend: Project Dashboard]
    ↓ 파라미터 입력
[Frontend: ParameterInputForm]
    ↓ POST /api/v1/schedules/validate
[Backend: Express API]
    ↓ DB에서 기준정보 로드
[Database: equipment, processes, orders, line_speeds, mixture_info 테이블]
    ↓ 데이터 전달
[Backend: Python 알고리즘 (Child Process)]
    ↓ 0~1단계 검증 실행
[Backend: Express API]
    ↓ 검증 결과 저장
[Database: validation_results, validation_errors 테이블]
    ↓ 검증 성공
[Frontend: ValidationResultPage]
    ↓ 스케줄링 실행
[Backend: Queue (Bull)]
    ↓ Job 전달
[Backend: Worker (Python 알고리즘)]
    ↓ 2-4단계 실행
    ↓ (generate_order_sequence → yield_prediction → create_complete_dag_system)
[Backend: Express API]
    ↓ 중간 결과 저장
[Database: stage_2_4_results 테이블]
    ↓ 2-4단계 완료
[Frontend: 자동 감지 및 라우팅]
    ↓ GET /stage-2-4
[Frontend: Stage2_4ResultPage - 실행 정보만 표시]
    (백그라운드에서 5-6단계 자동 실행)
    ↓
[Backend: Worker (Python 알고리즘)]
    ↓ 5-6단계 실행
    ↓ (DispatchPriorityStrategy.execute → create_results)
[Backend: Express API]
    ↓ 최종 결과 저장
[Database: schedule_results, schedule_details 테이블]
    ↓ 5-6단계 완료
[Frontend: 자동 감지 및 라우팅]
    ↓ GET /result
[Frontend: SchedulingResultPage - 탭 기반 결과 표시]
    ↓ 설비별 통계 / Gantt Chart / 스케줄 상세
[사용자]
```

### 3.2 Frontend ↔ Backend 데이터 흐름

#### 프로젝트 생성 흐름
```
Frontend                          Backend                          Database
--------                          -------                          --------
[Form Input] 
  project_name
  base_date      ────POST────>    [Express API]
  description                      ├─ Validate Input
                                   ├─ Check base_date duplicate
                                   └─ Generate UUID      ──INSERT──> projects
                                                         <──Return──  project_id
            <────201 Created────  [Response]
              project_id
            
            or
            
            <────409 Conflict───  [Response]
              "동일한 기준날짜의 프로젝트가 이미 존재합니다"
```

#### 파라미터 검증 흐름
```
Frontend                          Backend                          Database/Algorithm
--------                          -------                          ------------------
[ParameterInputForm]
  required params
  optional params ────POST────>   [Express API]
                                   ├─ Validate Input
                                   └─ Load Master Data   ──SELECT──> equipment, processes, 
                                                                      line_speeds, mixture_info
                                                          <──Return── Master Data
                                   [Python Algorithm]
                                   ├─ Step 0: Preprocess
                                   └─ Step 1: Validate   ──INSERT──> validation_results
                                                                       validation_errors
                 <────200 OK────  [Response]
                   validation_status
                   error_details
```

#### 스케줄링 실행 흐름
```
Frontend                          Backend                          Queue/Worker
--------                          -------                          ------------
[Execute Button] ──POST────>      [Express API]
                                   ├─ Create execution_id
                                   └─ Enqueue Job        ──Enqueue──> Bull Queue
                 <──202 Accepted─ [Response]
                   execution_id

[Polling]        ──GET Status──>  [Express API]         <──Dequeue── Worker
                                   └─ Query DB                       ├─ Run Algorithm (2-4단계)
                 <──200 OK─────   execution_status                  │  * generate_order_sequence
                   current_step                                      │  * yield_prediction
                   stage: 'stage_2_4'                                │  * create_complete_dag_system
                                                                     └─ Save to stage_2_4_results
                                   
[Polling continues]                                     ──INSERT───> stage_2_4_results
                 ──GET Status──>  [Express API]
                 <──200 OK─────   stage_2_4_completed: true
                   stage: 'stage_2_4_completed'

[Auto Redirect to Stage 2-4 Result Page]
                 ──GET /stage-2-4─> [Express API]      
                 <──200 OK────────  execution_info only
                 
[Render Stage 2-4 Results - 실행 정보만 표시]
                 (백그라운드에서 5-6단계 자동 실행 중)
                                                        Worker continues:
                                                        ├─ Run Algorithm (5-6단계)
                                                        │  * DispatchPriorityStrategy.execute
                                                        │  * create_results
                                                        └─ Save to schedule_results
                                                        
                                                        ──INSERT───> schedule_results
                                                                     schedule_details

[Polling continues]
                 ──GET Status──>  [Express API]
                 <──200 OK─────   stage_5_6_completed: true
                   status: 'completed'
                   
[Auto Redirect to Final Result Page]
                 ──GET /result──> [Express API]
                                   ├─ Calculate equipment statistics
                                   └─ Query schedule details
                 <──200 OK──────  equipment_statistics + schedule data
                 
[Render Final Results]
  Tab 1: 설비별 통계 테이블
  Tab 2: Gantt Chart
  Tab 3: 스케줄 상세 테이블
  
[Excel Download]
                 ──Download───>   Tab 3 데이터를 Excel로 변환
                                  └─ 클라이언트에서 파일 생성
```

---

## 4. UI 연계

### 4.1 페이지 구조 및 컴포넌트 맵핑

#### 페이지 트리
```
/
├── /login (로그인 페이지)
├── /projects (프로젝트 목록)
│   ├── /projects/new (프로젝트 생성)
│   └── /projects/:projectId (프로젝트 대시보드)
│       ├── /projects/:projectId/schedules/new (파라미터 입력)
│       ├── /projects/:projectId/schedules/:parameterId/validation (검증 결과)
│       ├── /projects/:projectId/schedules/:executionId/progress (실행 진행)
│       ├── /projects/:projectId/schedules/:executionId/stage-2-4 (중간 결과: 실행 정보만)
│       ├── /projects/:projectId/schedules/:executionId/result (최종 결과: 탭 기반)
│       ├── /projects/:projectId/history (이력 목록)
│       └── /projects/:projectId/schedules/compare (이력 비교)
└── /master-data (기준정보 조회)
    ├── /master-data/equipment (설비정보)
    ├── /master-data/processes (공정정보)
    ├── /master-data/line-speeds (라인스피드)
    └── /master-data/mixture-info (배합액정보)
```

#### 주요 컴포넌트 리스트

##### Layout Components
- `AppLayout`: 전체 레이아웃 (Header, Sidebar, Main)
- `Header`: 로고, 사용자 프로필, 알림
- `Sidebar`: 내비게이션 메뉴

##### Project Components
- `ProjectList`: 프로젝트 목록 카드
- `ProjectCreateForm`: 프로젝트 생성 폼
- `ProjectDashboard`: 프로젝트 상세 대시보드

##### Parameter Components
- `ParameterInputForm`: 파라미터 입력 폼
- `MachineUnavailableInput`: 설비 사용불가 시간대 입력
- `ProcessRestrictionInput`: 공정 제약 입력
- `DedicatedEquipmentInput`: 전용 설비 입력

##### Validation Components
- `ValidationLoadingScreen`: 검증 진행 중 화면
- `ValidationResultPage`: 검증 결과 페이지
- `ValidationErrorModal`: 오류 상세 모달
- `ErrorDetailTable`: 오류 데이터 테이블

##### Execution Components
- `SchedulingProgressPage`: 스케줄링 진행 화면
- `CurrentStepIndicator`: 현재 단계 표시
- `CancelExecutionModal`: 실행 취소 확인 모달

##### Stage 2-4 Result Components
- `Stage2_4ResultPage`: 2-4단계 중간 결과 페이지
- `ExecutionInfoCard`: 실행 정보 카드
- `ExecutionStatusBanner`: 실행 상태 배너

##### Final Result Components
- `SchedulingResultPage`: 최종 결과 페이지 (탭 기반)
- `ResultTabs`: 탭 전환 컴포넌트
- `EquipmentStatisticsTable`: 설비별 통계 테이블
- `GanttChart`: Gantt Chart 시각화
- `ScheduleTable`: 스케줄 상세 테이블
- `FilterPanel`: 필터 패널
- `ExportExcelButton`: Excel 다운로드 버튼

##### History Components
- `HistoryListPage`: 이력 목록 페이지
- `HistoryCard`: 이력 카드
- `StatusFilterPanel`: 상태 필터 패널
- `ComparisonPage`: 비교 대시보드
- `EquipmentStatisticsComparisonChart`: 설비별 통계 비교 차트

##### Master Data Components
- `EquipmentTable`: 설비정보 테이블
- `ProcessesTable`: 공정정보 테이블
- `LineSpeedsTable`: 라인스피드 테이블
- `MixtureInfoTable`: 배합액정보 테이블

### 4.2 주요 상호작용 시나리오

#### 시나리오 1: 신규 스케줄링 전체 플로우
```
1. 사용자 로그인
2. 프로젝트 목록 조회
3. "새 프로젝트" 버튼 클릭
4. 프로젝트 정보 입력 (base_date 중복 체크)
5. 프로젝트 생성 성공
6. 프로젝트 대시보드 진입
7. "새 스케줄 생성" 버튼 클릭
8. 파라미터 입력 폼에서 필수/선택 파라미터 입력
9. "검증 시작" 버튼 클릭
10. 검증 진행 중 로딩 화면 표시
11. 검증 성공 결과 확인
12. "스케줄링 실행" 버튼 클릭
13. 실행 진행 화면에서 현재 단계 모니터링
14. 2-4단계 완료 시 자동으로 중간 결과 페이지 이동
15. 실행 정보 확인 (소요 시간 등)
16. 백그라운드에서 5-6단계 자동 실행
17. 5-6단계 완료 시 자동으로 최종 결과 페이지 이동
18. Tab 1에서 설비별 통계 테이블 확인
19. Tab 2에서 Gantt Chart 확인
20. Tab 3에서 스케줄 상세 확인
21. Excel 다운로드 버튼으로 Tab 3 데이터 다운로드
```

#### 시나리오 2: 이력 조회 및 비교
```
1. 프로젝트 대시보드에서 "이력" 메뉴 클릭
2. 과거 실행 이력 목록 조회
3. 상태 필터 적용
4. 두 개의 실행 이력 체크박스 선택
5. "비교" 버튼 클릭
6. 비교 대시보드에서 좌우 분할 화면 확인
7. 파라미터 차이 확인
8. 설비별 통계 증감률 분석
9. Gantt Chart 병렬 비교
10. 차이점 요약 확인
```

#### 시나리오 3: 검증 실패 후 재시도
```
1. 파라미터 입력 후 검증 시작
2. 검증 실패 결과 확인
3. 테이블별 오류 요약 확인
4. "상세보기" 버튼 클릭하여 오류 데이터 행 조회
5. 오류 원인 파악 (예: 공정정보 테이블의 null 값)
6. 기준정보 조회 메뉴로 이동
7. 해당 테이블 확인 및 데이터 수정 요청
8. 파라미터 입력 페이지로 돌아가 재검증
```

#### 시나리오 4: 결과 페이지 내 탭 전환 및 상호작용
```
1. 최종 결과 페이지 진입
2. 기본적으로 Tab 1 (설비별 통계) 표시
3. 특정 설비의 통계 확인
4. Tab 2 (Gantt Chart) 클릭
5. Gantt Chart에서 특정 작업 블록 클릭
6. 자동으로 Tab 3 (스케줄 상세)로 전환
7. 해당 작업의 행이 하이라이트됨
8. 스케줄 상세 테이블에서 다른 작업 클릭
9. 자동으로 Tab 2로 전환
10. Gantt Chart에서 해당 작업 블록 하이라이트
11. Tab 3으로 다시 이동
12. "결과 다운로드" 버튼 클릭
13. Excel 파일 다운로드
```

---

## 5. 데이터베이스 연계

### 5.1 주요 테이블 구조

#### projects 테이블
```sql
CREATE TABLE projects (
  project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_name VARCHAR(100) NOT NULL,
  base_date DATE NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'active',
  created_by UUID REFERENCES users(user_id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(created_by, base_date)  -- 동일 사용자, 동일 base_date 중복 방지
);

-- 인덱스
CREATE INDEX idx_projects_created_by ON projects(created_by);
CREATE INDEX idx_projects_base_date ON projects(base_date);
CREATE INDEX idx_projects_created_by_base_date ON projects(created_by, base_date);
```

#### scheduling_parameters 테이블
```sql
CREATE TABLE scheduling_parameters (
  parameter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id),
  base_date DATE NOT NULL,
  window_size INTEGER NOT NULL CHECK (window_size BETWEEN 1 AND 90),
  yield_period INTEGER NOT NULL CHECK (yield_period BETWEEN 1 AND 365),
  machine_unavailable JSONB,
  process_restrictions JSONB,
  dedicated_equipment JSONB,
  validation_status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_parameters_project_id ON scheduling_parameters(project_id);
CREATE INDEX idx_parameters_validation_status ON scheduling_parameters(validation_status);
```

#### validation_results 테이블
```sql
CREATE TABLE validation_results (
  validation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parameter_id UUID REFERENCES scheduling_parameters(parameter_id),
  validation_status VARCHAR(20) NOT NULL,
  data_summary JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_validation_results_parameter_id ON validation_results(parameter_id);
```

#### validation_errors 테이블
```sql
CREATE TABLE validation_errors (
  error_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parameter_id UUID REFERENCES scheduling_parameters(parameter_id),
  table_name VARCHAR(100) NOT NULL,
  row_number INTEGER,
  column_name VARCHAR(100),
  current_value TEXT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_validation_errors_parameter_id ON validation_errors(parameter_id);
CREATE INDEX idx_validation_errors_table_name ON validation_errors(table_name);
```

#### schedule_executions 테이블
```sql
CREATE TABLE schedule_executions (
  execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parameter_id UUID REFERENCES scheduling_parameters(parameter_id),
  project_id UUID REFERENCES projects(project_id),
  status VARCHAR(20) DEFAULT 'queued',
  current_stage VARCHAR(50),
  current_step TEXT,
  stage_2_4_completed BOOLEAN DEFAULT FALSE,
  stage_5_6_completed BOOLEAN DEFAULT FALSE,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  cancelled_at TIMESTAMP,
  error_message TEXT,
  failed_stage VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_executions_project_id ON schedule_executions(project_id);
CREATE INDEX idx_executions_status ON schedule_executions(status);
CREATE INDEX idx_executions_created_at ON schedule_executions(created_at DESC);
```

#### stage_2_4_results 테이블
```sql
CREATE TABLE stage_2_4_results (
  result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  execution_id UUID REFERENCES schedule_executions(execution_id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_stage_2_4_results_execution_id ON stage_2_4_results(execution_id);
```

#### schedule_results 테이블
```sql
CREATE TABLE schedule_results (
  result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  execution_id UUID REFERENCES schedule_executions(execution_id),
  total_jobs INTEGER,
  makespan NUMERIC,
  execution_time VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_schedule_results_execution_id ON schedule_results(execution_id);
```

#### schedule_details 테이블
```sql
CREATE TABLE schedule_details (
  detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  execution_id UUID REFERENCES schedule_executions(execution_id),
  job_id VARCHAR(100),
  machine_id VARCHAR(100),
  machine_name VARCHAR(100),
  process_name VARCHAR(100),
  process_code VARCHAR(50),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  duration NUMERIC,
  changeover_time NUMERIC,
  waiting_time NUMERIC,
  color VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_schedule_details_execution_id ON schedule_details(execution_id);
CREATE INDEX idx_schedule_details_machine_id ON schedule_details(machine_id);
CREATE INDEX idx_schedule_details_start_time ON schedule_details(start_time);
```

#### 기준정보 테이블 (Master Data)

##### equipment 테이블
```sql
CREATE TABLE equipment (
  equipment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  machine_id VARCHAR(100) UNIQUE NOT NULL,
  machine_name VARCHAR(200),
  machine_type VARCHAR(100),
  capacity NUMERIC,
  status VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_equipment_machine_id ON equipment(machine_id);
```

##### processes 테이블
```sql
CREATE TABLE processes (
  process_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  process_code VARCHAR(50) UNIQUE NOT NULL,
  process_name VARCHAR(200),
  process_time NUMERIC,
  sequence_order INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_processes_process_code ON processes(process_code);
```

##### line_speeds 테이블
```sql
CREATE TABLE line_speeds (
  line_speed_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  machine_id VARCHAR(100),
  product_code VARCHAR(100),
  speed NUMERIC,
  unit VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_line_speeds_machine_id ON line_speeds(machine_id);
CREATE INDEX idx_line_speeds_product_code ON line_speeds(product_code);
```

##### mixture_info 테이블
```sql
CREATE TABLE mixture_info (
  mixture_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mixture_code VARCHAR(100) UNIQUE NOT NULL,
  mixture_name VARCHAR(200),
  component_info JSONB,
  ratio JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_mixture_info_mixture_code ON mixture_info(mixture_code);
```

---

## 6. 에러 핸들링 전략

### 6.1 Frontend 에러 처리

#### 에러 타입 정의
```typescript
enum ErrorType {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  TIMEOUT = 'TIMEOUT'
}

interface AppError {
  type: ErrorType;
  message: string;
  details?: any;
  timestamp: string;
}
```

#### 에러 처리 전략
```typescript
// API 호출 시 공통 에러 핸들러
async function apiCall<T>(
  request: Promise<AxiosResponse<T>>
): Promise<T> {
  try {
    const response = await request;
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // 서버 응답 에러
        switch (error.response.status) {
          case 400:
            throw new AppError(ErrorType.VALIDATION_ERROR, error.response.data.message);
          case 401:
            throw new AppError(ErrorType.AUTH_ERROR, '인증이 필요합니다');
          case 404:
            throw new AppError(ErrorType.NOT_FOUND, '요청한 리소스를 찾을 수 없습니다');
          case 409:
            throw new AppError(ErrorType.CONFLICT, error.response.data.message);
          case 500:
            throw new AppError(ErrorType.SERVER_ERROR, '서버 오류가 발생했습니다');
          case 504:
            throw new AppError(ErrorType.TIMEOUT, '요청 시간이 초과되었습니다');
          default:
            throw new AppError(ErrorType.SERVER_ERROR, error.response.data.message);
        }
      } else if (error.request) {
        // 네트워크 에러
        throw new AppError(ErrorType.NETWORK_ERROR, '네트워크 연결을 확인해주세요');
      }
    }
    throw new AppError(ErrorType.SERVER_ERROR, '알 수 없는 오류가 발생했습니다');
  }
}
```

### 6.2 Backend 에러 처리

#### 공통 에러 미들웨어
```javascript
// Express 에러 핸들링 미들웨어
function errorHandler(err, req, res, next) {
  console.error(err.stack);
  
  // Validation 에러
  if (err.name === 'ValidationError') {
    return res.status(400).json({
      status: 'error',
      message: '입력 데이터 검증 실패',
      details: err.details
    });
  }
  
  // 인증 에러
  if (err.name === 'UnauthorizedError') {
    return res.status(401).json({
      status: 'error',
      message: '인증이 필요합니다'
    });
  }
  
  // Not Found 에러
  if (err.name === 'NotFoundError') {
    return res.status(404).json({
      status: 'error',
      message: err.message || '리소스를 찾을 수 없습니다'
    });
  }
  
  // Conflict 에러 (중복 등)
  if (err.name === 'ConflictError' || err.code === '23505') {
    return res.status(409).json({
      status: 'error',
      message: err.message || '데이터 충돌이 발생했습니다'
    });
  }
  
  // 기본 서버 에러
  res.status(500).json({
    status: 'error',
    message: '서버 내부 오류가 발생했습니다',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
}
```

---

## 7. 성능 최적화 전략

### 7.1 Frontend 최적화

#### 1. 코드 스플리팅
```typescript
// React.lazy를 사용한 컴포넌트 지연 로딩
const Stage2_4ResultPage = React.lazy(() => import('./pages/Stage2_4ResultPage'));
const SchedulingResultPage = React.lazy(() => import('./pages/SchedulingResultPage'));
const GanttChart = React.lazy(() => import('./components/GanttChart'));
```

#### 2. 메모이제이션
```typescript
// useMemo를 사용한 비용이 큰 계산 캐싱
const filteredSchedule = useMemo(() => {
  return schedule.filter(job => 
    job.machine_id === selectedMachine &&
    job.start_time >= dateRange.start
  );
}, [schedule, selectedMachine, dateRange]);

// React.memo를 사용한 컴포넌트 리렌더링 최적화
const EquipmentStatisticsRow = React.memo(({ data }: EquipmentStatisticsRowProps) => {
  // ...
});
```

#### 3. 가상 스크롤링
```typescript
// react-window를 사용한 대용량 테이블 렌더링
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={schedule.length}
  itemSize={50}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      {schedule[index].job_id}
    </div>
  )}
</FixedSizeList>
```

### 7.2 Backend 최적화

#### 1. 데이터베이스 인덱싱
```sql
-- 자주 조회되는 컬럼에 인덱스 생성 (위 5.1 참조)
-- 복합 인덱스 활용
CREATE INDEX idx_projects_created_by_base_date ON projects(created_by, base_date);
CREATE INDEX idx_executions_project_status ON schedule_executions(project_id, status);
```

#### 2. 쿼리 최적화
```javascript
// 설비별 통계 계산 최적화 쿼리
const query = `
  SELECT 
    sd.machine_id,
    e.machine_name,
    SUM(CASE WHEN sd.changeover_time = 0 AND sd.waiting_time = 0 THEN sd.duration ELSE 0 END) as work_time,
    SUM(sd.changeover_time) as changeover_time,
    SUM(sd.waiting_time) as waiting_time,
    SUM(sd.duration + sd.changeover_time + sd.waiting_time) as total_time
  FROM schedule_details sd
  INNER JOIN equipment e ON sd.machine_id = e.machine_id
  WHERE sd.execution_id = $1
  GROUP BY sd.machine_id, e.machine_name
  ORDER BY sd.machine_id
`;

// 가동율 및 Loss율 계산은 애플리케이션 레벨에서 수행
const statistics = results.map(row => ({
  ...row,
  utilization_rate: (row.work_time / row.total_time) * 100,
  changeover_loss_rate: (row.changeover_time / row.total_time) * 100,
  waiting_loss_rate: (row.waiting_time / row.total_time) * 100
}));
```

#### 3. 페이지네이션 최적화
```javascript
// OFFSET 대신 Keyset Pagination 사용 (대용량 데이터에 효율적)
const query = `
  SELECT *
  FROM schedule_details
  WHERE execution_id = $1
    AND detail_id > $2  -- 이전 페이지의 마지막 ID
  ORDER BY detail_id
  LIMIT $3
`;
```

---

## 8. 보안 고려사항

### 8.1 인증 및 권한

#### JWT 인증
```javascript
// JWT 생성
const jwt = require('jsonwebtoken');

function generateToken(user) {
  return jwt.sign(
    { user_id: user.user_id, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: '1h' }
  );
}

// JWT 검증 미들웨어
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ message: '인증 토큰이 필요합니다' });
  }
  
  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ message: '유효하지 않은 토큰입니다' });
    }
    req.user = user;
    next();
  });
}
```

### 8.2 입력 검증

#### express-validator 사용
```javascript
const { body, validationResult } = require('express-validator');

app.post('/api/v1/projects',
  [
    body('project_name')
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('프로젝트명은 1-100자 사이여야 합니다'),
    body('base_date')
      .isISO8601()
      .withMessage('올바른 날짜 형식이 아닙니다'),
    body('window_size')
      .isInt({ min: 1, max: 90 })
      .withMessage('window_size는 1-90 사이여야 합니다')
  ],
  (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    // 처리 로직
  }
);
```

### 8.3 SQL Injection 방어

#### Parameterized Queries 사용
```javascript
// 안전하지 않은 방법 (사용 금지)
const query = `SELECT * FROM projects WHERE project_name = '${projectName}'`;

// 안전한 방법 (Parameterized Query)
const query = 'SELECT * FROM projects WHERE project_name = $1';
const result = await db.query(query, [projectName]);
```

---

## 9. 문서 버전 관리

| 버전 | 날짜 | 변경 내역 | 작성자 |
|------|------|-----------|--------|
| v1.0 | 2025-10-20 | 초기 문서 작성 | - |
| v1.1 | 2025-10-21 | 기준정보 테이블 수정 (BOM 제거, 라인스피드/배합액 추가) | - |
| v1.2 | 2025-10-21 | 중간 단계 결과 자동 표시 로직 수정, 진행률 제거 | - |
| v1.3 | 2025-10-21 | 프로젝트 생성 시 base_date 중복 검증 추가, 2-4단계 결과 DAG만 표시, 최종 결과 탭 기반 구조로 변경, 이력 날짜 필터 제거, 캐싱 제거 | - |
| v1.4 | 2025-10-21 | 2-4단계 결과 페이지에서 DAG 섹션 제거, 실행 정보만 표시 | - |

---

**이 FSD는 PRD를 기반으로 모든 기능의 상세 로직, 데이터 흐름, UI 연계, API 명세를 포함합니다. 다음 단계로 DB Schema 세부 설계 및 API Spec 작성이 진행됩니다.**