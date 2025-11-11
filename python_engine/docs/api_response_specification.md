# 스케줄링 결과 API 응답 스펙

## 개요

`create_new_results()` 함수는 스케줄링 결과를 JSON 직렬화 가능한 형태로 반환합니다.
백엔드 API에서 이 데이터를 직접 사용하여 클라이언트에게 전달할 수 있습니다.

---

## 응답 구조

```json
{
  "machine_info": [...],              // 호기_정보 (작업 상세)
  "performance_summary": [...],       // 스케줄링_성과_지표 (4개 행)
  "machine_detailed_performance": [...],  // 장비별_상세_성과
  "order_lateness_report": [...],     // 주문_지각_정보
  "gap_analysis": [...],              // 간격_분석
  "metadata": {...},                  // 메타 정보
  "performance_metrics": {...},       // 성과 지표 요약
  "lateness_summary": {...}           // 지각 요약
}
```

---

## 1. machine_info (호기_정보)

각 작업의 기계 할당 및 실행 정보

### 필드 설명

```json
[
  {
    "기계코드": "C2210",                    // 기계 코드
    "기계명": "C2210 염색기",                // 기계 이름
    "GITEM": "32571",                      // 제품 코드
    "GITEM명": "제품명",                    // 제품 이름
    "공정": "20500",                       // 공정 코드
    "작업시작시각": "2025-08-29 00:00:00", // 작업 시작 시각
    "작업종료시각": "2025-08-29 05:30:00", // 작업 종료 시각
    "작업시간(분)": 330.0,                  // 작업 소요 시간 (분)
    "ID": "32571_20500_1300_T01514_4_M3",  // 노드 ID
    "할당된일": 123.5,                      // 할당된 작업량
    "지각일수": 0.0                         // 지각 일수
  },
  ...
]
```

### 활용

- 간트 차트 시각화
- 작업 스케줄 조회
- 기계별 작업 목록 조회

---

## 2. performance_summary (스케줄링_성과_지표)

전체 스케줄링의 핵심 성과 지표 (4개 행)

### 필드 설명

```json
[
  {
    "지표명": "PO제품수",
    "값": 27,
    "단위": "개"
  },
  {
    "지표명": "총 생산시간",
    "값": 87.5,
    "단위": "시간"
  },
  {
    "지표명": "납기준수율",
    "값": 88.0,
    "단위": "%"
  },
  {
    "지표명": "장비가동률(전체평균)",
    "값": 15.71,
    "단위": "%"
  }
]
```

### 활용

- 대시보드 KPI 표시
- 성과 리포트 생성
- 스케줄링 품질 평가

---

## 3. machine_detailed_performance (장비별_상세_성과)

각 기계의 가동률, 대기시간, 셋업시간 분석

### 필드 설명

```json
[
  {
    "기계코드": "C2210",
    "기계명": "C2210 염색기",
    "가동시간(분)": 4500.0,
    "가동율(%)": 85.7,
    "대기시간(분)": 500.0,
    "대기loss율(%)": 9.5,
    "공정교체시간(분)": 250.0,
    "공정교체loss율(%)": 4.8,
    "총시간(분)": 5250.0
  },
  ...
]
```

### 검증 규칙

```
가동율(%) + 대기loss율(%) + 공정교체loss율(%) ≈ 100%
```

### 활용

- 기계별 효율성 분석
- 병목 구간 식별
- 개선 포인트 도출

---

## 4. order_lateness_report (주문_지각_정보)

전체 주문의 납기 준수 현황

### 필드 설명

```json
[
  {
    "P/O NO": "SW1250904701",
    "GITEM": "32571",
    "GITEM명": "제품명",
    "납기일": "2025-09-15T00:00:00",
    "완성시각": "2025-09-10T15:30:00",
    "지각여부": "준수",
    "지각시간(일)": 0.0
  },
  {
    "P/O NO": "SW1250904703",
    "GITEM": "31722",
    "GITEM명": "제품명",
    "납기일": "2025-09-10T00:00:00",
    "완성시각": "2025-09-15T10:00:00",
    "지각여부": "지각",
    "지각시간(일)": 5.42
  },
  ...
]
```

### 지각여부 값

- `"준수"`: 납기일 내 완료
- `"지각"`: 납기일 초과

### 활용

- 지각 주문 모니터링
- 고객 알림 대상 선별
- 납기 준수율 분석

---

## 5. gap_analysis (간격_분석)

기계 간 작업 간격 및 셋업 시간 분석 (23컬럼 → 12컬럼으로 간소화)

### 필드 설명

```json
[
  {
    "기계코드": "C2210",
    "기계명": "C2210 염색기",
    "이전작업ID": "32571_20500_...",
    "다음작업ID": "31722_20500_...",
    "이전작업종료(분)": 330.0,
    "다음작업시작(분)": 380.0,
    "간격시간(분)": 50.0,
    "간격유형": "혼합(셋업+대기)",      // 순수대기 / 순수셋업 / 혼합(셋업+대기)
    "변경사유": "공정변경(염색→코팅), 배합액변경",  // 직관적인 변경 이유
    "셋업시간(분)": 30.0,
    "대기시간(분)": 20.0,
    "셋업비율(%)": 60.0
  },
  ...
]
```

### 간격유형 분류

- **순수대기**: 변경사유가 없는 경우 (아무 변경 없음)
- **순수셋업**: 대기시간이 0인 경우
- **혼합(셋업+대기)**: 셋업과 대기가 모두 있는 경우

### 변경사유 포맷

- `"공정변경(염색→코팅)"`: 공정이 변경된 경우
- `"배합액변경"`: 배합액이 변경된 경우
- `"폭변경(대→소: 150→180)"`: 원단 폭이 변경된 경우
- `"변경없음(대기)"`: 모든 속성이 동일한 경우 (순수 대기)
- 여러 변경사항이 있는 경우 쉼표로 구분 (예: `"공정변경(염색→코팅), 배합액변경"`)

### 활용

- 셋업 시간 최적화 분석
- 대기 시간 원인 파악
- 작업 순서 개선 포인트 도출

---

## 6. metadata (메타 정보)

스케줄링 전체 정보

### 필드 설명

```json
{
  "actual_makespan": 175.0,           // 실제 makespan (분 단위)
  "total_makespan": 175.0,            // 전체 makespan (분 단위)
  "gantt_filename": "data/output/level4_gantt.png",  // 간트차트 파일명
  "total_nodes": 83,                  // 전체 노드 수 (Aging 포함)
  "total_machines": 12                // 전체 기계 수
}
```

### 활용

- 간트차트 파일 경로 제공
- 전체 작업 규모 파악
- 스케줄링 완료 여부 확인

---

## 7. performance_metrics (성과 지표 요약)

프로그래밍 활용을 위한 성과 지표 (dict 형태)

### 필드 설명

```json
{
  "po_count": 27,                     // PO 제품 수
  "makespan_hours": 87.5,             // 총 생산시간 (시간)
  "ontime_delivery_rate": 88.0,      // 납기준수율 (%)
  "avg_utilization": 15.71            // 평균 장비가동률 (%)
}
```

### 활용

- 빠른 요약 정보 조회
- 알림/알람 조건 체크
- 비즈니스 로직 처리

---

## 8. lateness_summary (지각 요약)

납기 지각 관련 통계

### 필드 설명

```json
{
  "total_orders": 25,                 // 전체 주문 수
  "ontime_orders": 24,                // 준수 주문 수
  "late_orders": 1,                   // 지각 주문 수
  "ontime_rate": 96.0,                // 준수율 (%)
  "avg_lateness_days": 54.75          // 평균 지각일수 (지각 주문만)
}
```

### 주의사항

- `avg_lateness_days`는 **지각한 주문만**의 평균입니다
- 준수 주문은 평균 계산에서 제외됩니다

### 활용

- 납기 준수 현황 모니터링
- 지각 주문 알림 발송 여부 판단
- 고객 CS 우선순위 결정

---

## 데이터 타입 주의사항

### datetime 필드

`machine_info`와 `order_lateness_report`의 날짜/시간 필드는 ISO 8601 포맷으로 직렬화됩니다:

```json
"작업시작시각": "2025-08-29T00:00:00"
```

백엔드에서 파싱 시 적절한 datetime 라이브러리 사용 필요.

### float → int 변환

일부 필드는 명시적으로 `int`로 변환됩니다:
- `po_count`
- `total_orders`, `ontime_orders`, `late_orders`
- `total_nodes`, `total_machines`

### NaN 처리

DataFrame에서 NaN 값은 `null`로 직렬화됩니다. 백엔드에서 `null` 체크 필요.

---

## 사용 예시 (Python 백엔드)

### Flask 예시

```python
from flask import Flask, jsonify
from src.new_results import create_new_results

app = Flask(__name__)

@app.route('/api/scheduling/results', methods=['POST'])
def get_scheduling_results():
    # ... 스케줄링 실행 ...

    final_results = create_new_results(
        raw_scheduling_result=result,
        merged_df=merged_df,
        original_order=order,
        sequence_seperated_order=sequence_seperated_order,
        machine_master_info=machine_master_info,
        base_date=base_date,
        scheduler=scheduler
    )

    # JSON 직렬화 가능한 형태이므로 바로 반환
    return jsonify(final_results), 200
```

### FastAPI 예시

```python
from fastapi import FastAPI
from src.new_results import create_new_results

app = FastAPI()

@app.post("/api/scheduling/results")
async def get_scheduling_results():
    # ... 스케줄링 실행 ...

    final_results = create_new_results(
        raw_scheduling_result=result,
        merged_df=merged_df,
        original_order=order,
        sequence_seperated_order=sequence_seperated_order,
        machine_master_info=machine_master_info,
        base_date=base_date,
        scheduler=scheduler
    )

    return final_results  # FastAPI가 자동으로 JSON 변환
```

---

## 응답 크기 최적화

### 대용량 데이터 처리

`machine_info`와 `gap_analysis`는 노드 수에 비례하여 크기가 증가합니다.

**권장 사항:**
1. **Pagination**: 대용량 결과는 페이지네이션 적용
2. **필터링**: 클라이언트가 필요한 기계/주문만 요청하도록 필터 제공
3. **압축**: gzip 압축 활성화
4. **캐싱**: Redis 등을 활용한 결과 캐싱

### 응답 압축 예시 (Flask)

```python
from flask_compress import Compress

app = Flask(__name__)
Compress(app)  # 자동으로 gzip 압축 적용
```

---

## 에러 처리

`create_new_results()`는 예외를 발생시킬 수 있습니다. 백엔드에서 적절히 처리해야 합니다:

```python
try:
    final_results = create_new_results(...)
    return jsonify(final_results), 200
except KeyError as e:
    return jsonify({"error": f"Missing required column: {e}"}), 500
except Exception as e:
    return jsonify({"error": f"Scheduling failed: {str(e)}"}), 500
```

---

## 변경 이력

### v2.0.0 (2025-01-11)

- **[Breaking Change]** DataFrame 반환 → dict 반환으로 변경
- `machine_info`, `performance_summary` 등 5개 테이블을 `to_dict('records')` 형태로 반환
- `metadata`, `performance_metrics`, `lateness_summary` 추가
- 모든 숫자 값을 명시적으로 Python 네이티브 타입으로 변환 (numpy 타입 제거)

### v1.0.0 (Initial)

- 기존 `results` 모듈을 대체하는 `new_results` 모듈 최초 구현
- 5개 테이블 생성: 호기_정보, 스케줄링_성과_지표, 장비별_상세_성과, 주문_지각_정보, 간격_분석
- 간격_분석을 23컬럼 → 12컬럼으로 간소화

---

## 문의

API 스펙 관련 문의 사항은 개발팀에 문의하세요.
