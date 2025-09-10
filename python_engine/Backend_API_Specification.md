# 생산 스케줄링 시스템 백엔드 API 명세서

## 개요
이 문서는 생산 스케줄링 시스템의 프론트엔드에서 필요로 하는 백엔드 API 데이터 구조를 정의합니다.

## 데이터 소스 구분

### 🔴 사용자 입력 데이터 (User Input)
프론트엔드에서 사용자가 직접 입력하거나 설정하는 데이터

### 🔵 DB/API 제공 데이터 (Backend Provided)
데이터베이스나 백엔드 시스템에서 계산/조회하여 제공하는 데이터

### 🟡 혼합 데이터 (Mixed)
사용자 입력과 백엔드 데이터가 결합된 데이터

## 1. 스케줄링 시작 API

### 1.1 스케줄링 설정 및 제약조건 전송 🔴
**데이터 소스**: 사용자 입력  
**Endpoint**: `POST /api/scheduling/start`

**Request Body**:
```json
{
  "schedulingSettings": {
    "baseDate": "2025-05-15",        // 🔴 사용자가 설정한 기준날짜 (스케줄링 시작 기준점)
    "windowSize": 14,                // 🔴 사용자가 설정한 윈도우 크기 (일 단위, 스케줄링 대상 기간)
    "yieldPeriod": 30,               // 🔴 사용자가 설정한 수율 기준기간 (일 단위, 수율 계산 기간)
    "schedulingStrategy": "efficiency", // 🔴 사용자가 선택한 스케줄링 전략
                                     // 옵션: "efficiency" (효율성 우선), "delivery" (납기 우선), "balanced" (균형)
    "optimizationTarget": "makespan" // 🔴 사용자가 선택한 최적화 목표
                                     // 옵션: "makespan" (총 완료시간), "tardiness" (지연 최소화), "utilization" (활용도)
  },
  "constraints": {
    "timeRestrictions": [
      {
        "machine": "1호기",           // 🔴 사용자가 드롭다운에서 선택
        "date": "2025-05-15",        // 🔴 사용자가 date picker에서 선택
        "startTime": "14:00",        // 🔴 사용자가 30분 단위 드롭다운에서 선택
        "endTime": "16:30",          // 🔴 사용자가 30분 단위 드롭다운에서 선택
        "reason": "정기점검"          // 🔴 사용자가 텍스트 입력 (선택사항)
      }
    ],
    "processRestrictions": [
      {
        "machine": "25호기",         // 🔴 사용자가 드롭다운에서 선택
        "process": "투명점착",        // 🔴 사용자가 드롭다운에서 선택
        "reason": "장비 호환성 문제"   // 🔴 사용자가 텍스트 입력 (선택사항)
      }
    ],
    "dedicatedMachines": [
      {
        "machine": "30호기",         // 🔴 사용자가 드롭다운에서 선택
        "process": "마무리코팅",      // 🔴 사용자가 드롭다운에서 선택
        "reason": "품질 보장"        // 🔴 사용자가 텍스트 입력 (선택사항)
      }
    ]
  }
}
```

### 1.2 기계 및 공정 목록 조회 🔵
**데이터 소스**: DB/API 제공  
**Endpoint**: `GET /api/machines/list`

**Response**:
```json
{
  "machines": ["1호기", "25호기", "30호기", "35호기", "40호기"], // 🔵 DB에서 조회
  "processes": ["투명점착", "유광S/R", "마무리코팅", "검사"]      // 🔵 DB에서 조회
}
```

### 1.3 스케줄링 설정 기본값 조회 🔵
**데이터 소스**: Backend 시스템 설정  
**Endpoint**: `GET /api/scheduling/default-settings`

**Response**:
```json
{
  "defaultSettings": {
    "baseDate": "2025-05-15",            // 🔵 시스템 기본값 (오늘 날짜 기준)
    "windowSize": 14,                    // 🔵 시스템 기본값 (2주)
    "yieldPeriod": 30,                   // 🔵 시스템 기본값 (1개월)
    "schedulingStrategy": "balanced",    // 🔵 시스템 기본값
    "optimizationTarget": "makespan"     // 🔵 시스템 기본값
  },
  "availableOptions": {
    "schedulingStrategies": [
      {"value": "efficiency", "label": "효율성 우선", "description": "기계 활용도와 처리량 최대화"}, // 🔵 시스템 정의
      {"value": "delivery", "label": "납기 우선", "description": "납기 준수율 최대화"}, // 🔵 시스템 정의
      {"value": "balanced", "label": "균형", "description": "효율성과 납기의 균형"} // 🔵 시스템 정의
    ],
    "optimizationTargets": [
      {"value": "makespan", "label": "총 완료시간 최소화", "description": "전체 작업 완료 시간 단축"}, // 🔵 시스템 정의
      {"value": "tardiness", "label": "지연 최소화", "description": "납기 지연 건수 및 시간 최소화"}, // 🔵 시스템 정의
      {"value": "utilization", "label": "활용도 최대화", "description": "기계 및 인력 활용도 극대화"} // 🔵 시스템 정의
    ]
  }
}
```

## 2. 스케줄링 진행 상태 API

### 2.1 진행률 조회 🔵
**데이터 소스**: Backend 계산  
**Endpoint**: `GET /api/scheduling/progress`

**Response**:
```json
{
  "currentStage": "preprocessing",           // 🔵 Backend에서 현재 진행 단계 제공
  "progress": 30,                           // 🔵 Backend에서 진행률(%) 계산
  "status": "running",                      // 🔵 Backend에서 상태 관리
  "message": "주문 데이터 전처리 중..."        // 🔵 Backend에서 상태 메시지 제공
}
```

## 3. 데이터 로딩 결과 API

### 3.1 로딩된 파일 목록 🔵
**데이터 소스**: Backend 파일 시스템/DB  
**Endpoint**: `GET /api/data-loading/files`

**Response**:
```json
{
  "files": [
    {
      "fileName": "orders_2025.json",       // 🔵 실제 로딩된 파일명
      "status": "완료",                     // 🔵 파일 로딩 상태
      "records": 1245,                     // 🔵 파일에서 읽은 레코드 수
      "size": "2.3MB",                     // 🔵 파일 크기
      "loadTime": "0.8초"                  // 🔵 로딩 소요 시간
    }
  ],
  "pagination": {
    "currentPage": 1,                      // 🔵 Backend에서 페이징 관리
    "totalPages": 2,
    "totalItems": 8,
    "itemsPerPage": 5
  }
}
```

## 4. 전처리 결과 API

### 4.1 전처리 통계 및 제외 항목 🟡
**데이터 소스**: Backend 계산 + 사용자 제약조건 반영  
**Endpoint**: `GET /api/preprocessing/results`

**Response**:
```json
{
  "statistics": {
    "totalOrders": 2845,                   // 🔵 원본 주문 데이터에서 집계
    "usedOrders": 2837,                    // 🔵 제약조건 필터링 후 사용 가능한 주문 수
    "totalGitems": 145,                    // 🔵 원본 GITEM 종류 수
    "usedGitems": 142,                     // 🔵 제약조건 필터링 후 사용 가능한 GITEM 수
    "excludedGitems": 8                    // 🔵 제외된 GITEM 수
  },
  "excludedItems": [
    {
      "gitem": "G12399",                   // 🔵 원본 주문 데이터
      "po": "PO-2025-156",                 // 🔵 원본 주문 데이터
      "reason": "투명점착 공정 전용장비 1호기의 사용불가로, 생산 불가" // 🟡 사용자 제약조건 기반 계산
    }
  ],
  "pagination": {
    "currentPage": 1,                      // 🔵 Backend 페이징 관리
    "totalPages": 2,
    "totalItems": 8,
    "itemsPerPage": 5
  }
}
```

## 5. 수율 예측 결과 API

### 5.1 GITEM/공정별 수율 정보 🔵
**데이터 소스**: Backend ML 모델 계산  
**Endpoint**: `GET /api/yield/prediction`

**Response**:
```json
{
  "defaultYieldItems": [
    {
      "gitem": "G12350",                   // 🔵 원본 주문 데이터
      "process": "투명점착",               // 🔵 원본 주문 데이터
      "affectedPOs": ["PO-2025-001", "PO-2025-045"] // 🔵 해당 GITEM/공정의 P/O 조회
    }
  ],
  "lowestYieldItems": [
    {
      "gitem": "G12399",                   // 🔵 원본 주문 데이터
      "process": "유광S/R",               // 🔵 원본 주문 데이터
      "yield": 0.65,                       // 🔵 ML 모델에서 예측한 수율
      "affectedPOs": ["PO-2025-234"]      // 🔵 해당 GITEM/공정의 P/O 조회
    }
  ],
  "pagination": {
    "yieldData": {
      "currentPage": 1,                    // 🔵 Backend 페이징 관리
      "totalPages": 32,
      "totalItems": 156,
      "itemsPerPage": 5
    },
    "noYieldData": {
      "currentPage": 1,                    // 🔵 Backend 페이징 관리
      "totalPages": 32,
      "totalItems": 156,
      "itemsPerPage": 5
    }
  }
}
```

## 6. 주문 묶음 결과 API

### 6.1 주문 묶음 상세 정보 🔵
**데이터 소스**: Backend 알고리즘 계산  
**Endpoint**: `GET /api/order-grouping/details`

**Response**:
```json
{
  "summary": {
    "totalGroups": 856,                    // 🔵 묶음 알고리즘 결과
    "originalPOCount": 2845,               // 🔵 원본 주문 수
    "averageGroupSize": 3.3                // 🔵 평균 묶음 크기 계산
  },
  "groups": [
    {
      "gitem": "G12345",                   // 🔵 원본 주문 데이터
      "process": "투명점착→유광S/R→마무리코팅→검사", // 🔵 원본 주문 데이터 
      "bundleLength": 3760,                // 🔵 묶음 내 개별 길이 합계 계산
      "bundleWidth": 1200,                 // 🔵 묶음 내 공통 너비 (GITEM 기준)
      "groupSize": 3,                      // 🔵 묶음 알고리즘 결과
      "dagId": "DAG_NODE_G12345_PROC_COMPLEX_001", // 🔵 DAG 생성 알고리즘 결과
      "orders": [
        {
          "poNumber": "PO-2025-001",       // 🔵 원본 주문 데이터
          "dueDate": "2025-05-18",         // 🔵 원본 주문 데이터
          "quantity": 2450,                // 🔵 원본 주문 데이터
          "length": 1250,                  // 🔵 원본 주문 데이터
          "width": 1200                    // 🔵 원본 주문 데이터
        },
        {
          "poNumber": "PO-2025-045",       // 🔵 원본 주문 데이터
          "dueDate": "2025-05-19",         // 🔵 원본 주문 데이터
          "quantity": 1890,                // 🔵 원본 주문 데이터
          "length": 950,                   // 🔵 원본 주문 데이터
          "width": 1200                    // 🔵 원본 주문 데이터
        },
        {
          "poNumber": "PO-2025-089",       // 🔵 원본 주문 데이터
          "dueDate": "2025-05-20",         // 🔵 원본 주문 데이터
          "quantity": 3120,                // 🔵 원본 주문 데이터
          "length": 1560,                  // 🔵 원본 주문 데이터
          "width": 1200                    // 🔵 원본 주문 데이터
        }
      ]
    }
  ],
  "pagination": {
    "currentPage": 1,                      // 🔵 Backend 페이징 관리
    "totalPages": 172,
    "totalItems": 856,
    "itemsPerPage": 5
  }
}
```

### 6.2 DAG ID 상세 정보 🔵
**데이터 소스**: Backend DAG 생성 알고리즘  
**Endpoint**: `GET /api/order-grouping/dag-details/{gitem}`

**Response**:
```json
{
  "gitem": "G12345",                       // 🔵 요청된 GITEM
  "processes": ["투명점착", "유광S/R", "마무리코팅", "검사"], // 🔵 해당 GITEM의 공정 순서
  "dagIds": [
    "DAG_NODE_G12345_PROC_TRANSPARENT_ADH_001_BATCH_A_2025051509", // 🔵 DAG 생성 알고리즘 결과
    "DAG_NODE_G12345_PROC_GLOSSY_SR_002_BATCH_A_2025051510",      // 🔵 DAG 생성 알고리즘 결과
    "DAG_NODE_G12345_PROC_FINISH_COAT_003_BATCH_A_2025051511",    // 🔵 DAG 생성 알고리즘 결과
    "DAG_NODE_G12345_PROC_INSPECTION_004_BATCH_A_2025051512"      // 🔵 DAG 생성 알고리즘 결과
  ]
}
```

## 7. 스케줄링 실행 결과 API

### 7.1 스케줄링 완료 정보 🟡
**데이터 소스**: Backend 스케줄링 알고리즘 + 사용자 제약조건 반영  
**Endpoint**: `GET /api/scheduling/execution-result`

**Response**:
```json
{
  "executionTime": "245초",                // 🔵 스케줄링 알고리즘 실행 시간
  "processChangeoverCount": 67,            // 🔵 스케줄링 결과 + 🔴 사용자 제약조건 반영
  "processChangeoverTime": "4시간 25분",    // 🔵 스케줄링 결과 + 🔴 사용자 제약조건 반영
  "scheduledOrders": 2837                  // 🔵 실제 스케줄된 주문 수 (제약조건 필터링 후)
}
```

## 8. 최종 결과 API

### 8.1 기계별 스케줄 타임라인 🟡
**데이터 소스**: Backend 스케줄링 알고리즘 + 사용자 제약조건 반영  
**Endpoint**: `GET /api/results/machine-schedule`

**Response**:
```json
{
  "machines": [
    {
      "machineId": "1호기",               // 🔵 원본 기계 데이터
      "processes": [
        {
          "processName": "투명점착",       // 🔵 원본 주문 데이터
          "gitem": "G12345",             // 🔵 원본 주문 데이터
          "poNumber": "PO-2025-001",     // 🔵 원본 주문 데이터
          "startTime": "2025-05-15T09:00:00", // 🟡 스케줄링 결과 + 사용자 제약조건 반영
          "endTime": "2025-05-15T13:30:00",   // 🟡 스케줄링 결과 + 사용자 제약조건 반영
          "duration": "4시간 30분"        // 🔵 스케줄링 알고리즘 계산
        }
      ]
    }
  ]
}
```

### 8.2 P/O별 분석 결과 🟡
**데이터 소스**: Backend 스케줄링 알고리즘 + 사용자 제약조건 반영  
**Endpoint**: `GET /api/results/po-analysis`

**Response**:
```json
{
  "orders": [
    {
      "poNumber": "PO-2025-001",           // 🔵 원본 주문 데이터
      "gitem": "G12345",                   // 🔵 원본 주문 데이터
      "status": "early",                   // 🔵 스케줄링 결과 vs 납기일 비교 계산
      "statusText": "1일 여유",            // 🔵 스케줄링 결과 vs 납기일 비교 계산
      "processFlow": "투명점착 → 유광S/R → 마무리코팅 → 검사", // 🔵 원본 주문 데이터
      "machineFlow": ["1호기", "25호기", "30호기", "35호기"], // 🟡 스케줄링 결과 + 사용자 제약조건 반영
      "startTime": "2025-05-15T09:00:00",  // 🟡 스케줄링 결과 + 사용자 제약조건 반영
      "completionTime": "2025-05-16T14:30:00", // 🟡 스케줄링 결과 + 사용자 제약조건 반영
      "dueDate": "2025-05-19"              // 🔵 원본 주문 데이터
    }
  ]
}
```

## 9. 분석 리포트 API

### 9.1 스케줄링 성과 분석 🟡
**데이터 소스**: Backend 스케줄링 결과 분석 + 사용자 제약조건 반영  
**Endpoint**: `GET /api/analysis/performance`

**Response**:
```json
{
  "onTimeDelivery": 89.2,                 // 🔵 스케줄링 결과 vs 납기일 분석
  "averageDelay": 1.3,                    // 🔵 스케줄링 결과 vs 납기일 분석  
  "machineUtilization": 87.5,             // 🟡 스케줄링 결과 + 사용자 제약조건 반영
  "totalProcessChangeoverCount": 67,      // 🟡 스케줄링 결과 + 사용자 제약조건 반영
  "totalProcessChangeoverTime": "4시간 25분" // 🟡 스케줄링 결과 + 사용자 제약조건 반영
}
```

## 10. 수율 상세 분석 API

### 10.1 GITEM별 수율 상세 🔵
**데이터 소스**: Backend ML 모델 계산  
**Endpoint**: `GET /api/yield/details`

**Response**:
```json
{
  "items": [
    {
      "gitem": "G12345",                   // 🔵 원본 주문 데이터
      "processes": [
        {
          "processName": "투명점착",       // 🔵 원본 주문 데이터
          "yield": 0.92,                   // 🔵 ML 모델 예측 수율
          "expectedProduction": 7542       // 🔵 수율 * 주문량 계산
        },
        {
          "processName": "유광S/R",       // 🔵 원본 주문 데이터
          "yield": 0.88,                   // 🔵 ML 모델 예측 수율
          "expectedProduction": 6637       // 🔵 수율 * 주문량 계산
        }
      ]
    }
  ],
  "pagination": {
    "currentPage": 1,                      // 🔵 Backend 페이징 관리
    "totalPages": 29,
    "totalItems": 142,
    "itemsPerPage": 5
  }
}
```

## 데이터 소스 구분 요약

### 🔴 사용자 입력 데이터 (User Input)
- **스케줄링 기본 설정**: 
  - 기준날짜 (스케줄링 시작 기준점)
  - 윈도우 크기 (스케줄링 대상 기간, 일 단위)
  - 수율 기준기간 (수율 계산 기간, 일 단위)
  - 스케줄링 전략 (효율성/납기/균형 우선)
  - 최적화 목표 (총완료시간/지연최소화/활용도)
- **기계 제약조건**: 시간대 휴식, 공정 제외, 전용 기계 설정
- **UI 인터랙션**: 페이지 선택, 탭 전환 등
- **폼 입력**: 제약조건 사유, 시간 선택 등

### 🔵 DB/API 제공 데이터 (Backend Provided)
- **원본 데이터**: 주문 정보, GITEM 데이터, 기계/공정 목록
- **알고리즘 결과**: 주문 묶음, DAG ID, 스케줄링 결과
- **계산 결과**: 수율 예측, 통계 정보, 성과 분석
- **시스템 데이터**: 진행률, 로딩 상태, 페이징 정보

### 🟡 혼합 데이터 (Mixed)
- **제약조건 반영 결과**: 사용자 제약조건이 스케줄링에 미치는 영향
- **필터링된 데이터**: 제약조건으로 인해 제외된 주문/GITEM
- **조건부 계산**: 제약조건을 고려한 기계 활용도, 공정교체 시간 등

### 중요 고려사항
1. **제약조건 연쇄 효과**: 사용자가 설정한 제약조건이 전체 스케줄링 결과에 미치는 영향을 모든 API에서 반영
2. **실시간 계산**: 제약조건 변경 시 관련된 모든 데이터의 재계산 필요
3. **데이터 일관성**: 같은 GITEM/P/O는 모든 API에서 일관된 제약조건 적용 상태 유지

## 데이터 타입 정의

### 공통 타입
```typescript
interface Pagination {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
}

interface SchedulingSettings {
  baseDate: string; // YYYY-MM-DD, 스케줄링 기준날짜
  windowSize: number; // 일 단위, 스케줄링 대상 기간
  yieldPeriod: number; // 일 단위, 수율 계산 기간
  schedulingStrategy: "efficiency" | "delivery" | "balanced"; // 스케줄링 전략
  optimizationTarget: "makespan" | "tardiness" | "utilization"; // 최적화 목표
}

interface MachineConstraint {
  timeRestrictions: TimeRestriction[];
  processRestrictions: ProcessRestriction[];
  dedicatedMachines: DedicatedMachine[];
}

interface TimeRestriction {
  machine: string;
  date: string; // YYYY-MM-DD
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  reason?: string;
}

interface ProcessRestriction {
  machine: string;
  process: string;
  reason?: string;
}

interface DedicatedMachine {
  machine: string;
  process: string;
  reason?: string;
}

interface SchedulingRequest {
  schedulingSettings: SchedulingSettings;
  constraints: MachineConstraint;
}
```

### 주문 관련 타입
```typescript
interface Order {
  poNumber: string;
  dueDate: string; // YYYY-MM-DD
  quantity: number;
  length: number;
  width: number;
}

interface OrderGroup {
  gitem: string;
  process: string;
  bundleLength: number;
  bundleWidth: number;
  groupSize: number;
  dagId: string;
  orders: Order[];
}
```

### 스케줄링 결과 타입
```typescript
interface ScheduleProcess {
  processName: string;
  gitem: string;
  poNumber: string;
  startTime: string; // ISO 8601
  endTime: string; // ISO 8601
  duration: string;
}

interface MachineSchedule {
  machineId: string;
  processes: ScheduleProcess[];
}

interface POAnalysis {
  poNumber: string;
  gitem: string;
  status: "early" | "on-time" | "late";
  statusText: string;
  processFlow: string;
  machineFlow: string[];
  startTime: string; // ISO 8601
  completionTime: string; // ISO 8601
  dueDate: string; // YYYY-MM-DD
}
```

## 에러 응답 형식

모든 API는 다음과 같은 에러 응답 형식을 사용합니다:

```json
{
  "error": {
    "code": "INVALID_CONSTRAINT",
    "message": "기계명이 유효하지 않습니다.",
    "details": {
      "field": "machine",
      "value": "99호기"
    }
  }
}
```

## 주의사항

1. **시간 형식**: ISO 8601 형식 사용 (YYYY-MM-DDTHH:MM:SS)
2. **페이지네이션**: 모든 목록 API는 페이지네이션 정보 포함
3. **제약조건**: 스케줄링 시작 시 프론트엔드에서 설정한 제약조건이 모든 계산에 반영되어야 함
4. **실시간 업데이트**: 스케줄링 진행 중에는 진행률 API를 통해 실시간 상태 제공
5. **데이터 일관성**: 같은 GITEM/P/O는 모든 API에서 일관된 데이터 제공
