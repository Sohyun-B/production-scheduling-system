# 제조업 생산 스케줄링 시스템 모듈별 입출력 가이드

## 1. 전체 파이프라인 - main.py의 run_level4_scheduling()

### Input (필요한 Excel 파일들)
- **품목별 분리 라인스피드 및 공정 순서.xlsx**
  - 시트: 품목별 라인스피드, 공정순서, 기계기준정보, 수율데이터, GITEM별 공정
- **공정 재분류 내역 및 교체 시간 정리(250820).xlsx**  
  - 시트: 공정군, 공정교체시간, 폭변경
- **불가능한 공정 입력값.xlsx**
  - 시트: 기계, 공정강제할당, 공정강제회피
- **25년 5월 PO 내역(송부건).xlsx**
  - 시트: 25년 5월 PO확정 내역

### Output
- **result.xlsx**: 원본 스케줄링 결과 DataFrame
- **0829 스케줄링결과.xlsx**: 3개 시트로 구성된 가공 결과
  - 주문_생산_요약본, 주문_생산_정보, 호기_정보
- **level4_gantt.png**: 간트 차트 이미지
- **Console 출력**: makespan, 지각일수, 실행시간 등

## 2. preprocessing 모듈

### preprocessing() 함수
**위치**: `preprocessing/__init__.py:6`

#### Input Parameters
- `order`: pandas.DataFrame - 주문 데이터
  - 컬럼: P/O NO, GITEM, GITEM명, SPEC, 의뢰량, 납기일
- `operation_seperated_sequence`: pandas.DataFrame - 공정순서 데이터
- `operation_types`: pandas.DataFrame - 공정분류 데이터  
- `machine_limit`: pandas.DataFrame - 기계제한 데이터
- `machine_allocate`: pandas.DataFrame - 강제할당 데이터
- `linespeed`: pandas.DataFrame - 라인스피드 데이터

#### Output Returns
- `sequence_seperated_order`: pandas.DataFrame
  - 주문별로 공정이 분리된 데이터
  - 컬럼: P/O NO, GITEM, GITEM명, 너비, 길이, 의뢰량, 원단길이, 납기일, 공정명, 공정분류
- `linespeed`: pandas.DataFrame 
  - 기계제약이 적용된 업데이트된 라인스피드 데이터

### 내부 처리 과정
1. 월별 주문 분리 → 동일 주문 병합 → 시퀀스 주문 생성 → 공정 타입 병합
2. 기계제한/강제할당 적용으로 불가능 아이템 제거

## 3. yield_management 모듈

### yield_prediction() 함수  
**위치**: `yield_management/__init__.py:3`

#### Input Parameters
- `yield_data`: pandas.DataFrame - 과거 수율 데이터
- `operation_sequence`: pandas.DataFrame - GITEM별 공정순서 
- `sequence_seperated_order`: pandas.DataFrame - 전처리된 주문 데이터

#### Output Returns
- `YieldPredictor`: 수율 예측 모델 객체
- `sequence_yield_df`: pandas.DataFrame 
  - GITEM별 공정순서별 예측 수율
- `adjusted_sequence_order`: pandas.DataFrame
  - 예측 수율이 반영되어 생산길이가 조정된 주문 데이터
  - 추가 컬럼: 예측_수율, 전체_예측_수율, 수율_생산비율, 생산길이

### 핵심 처리
- 과거 수율 데이터 분석 → 공정별 수율 예측 → 시퀀스별 종합 수율 계산 → 필요 생산량 역산

## 4. dag_management 모듈

### run_dag_pipeline() 함수
**위치**: `dag_management/__init__.py:6`

#### Input Parameters  
- `merged_df`: pandas.DataFrame - 공정 정보 테이블
- `hierarchy`: list - 공정 순서 컬럼명 리스트 (["1공정ID", "2공정ID", ...])
- `sequence_seperated_order`: pandas.DataFrame - 공정별 분리 주문
- `linespeed`: pandas.DataFrame - 라인스피드 데이터
- `machine_columns`: list - 기계 컬럼명 리스트

#### Output Returns
- `dag_df`: pandas.DataFrame
  - DAG 구조 데이터프레임
  - 컬럼: id, children, depth, po_no, gitem 등
- `opnode_dict`: dict
  - 작업 노드 딕셔너리 {node_id: node_info}
- `manager`: DAGGraphManager 객체
  - DAG 그래프 관리 객체
- `machine_dict`: dict  
  - 기계별 정보 사전 {operation: {machines: [...], gitem_speeds: {...}}}

### 핵심 처리
- 공정 의존성을 방향성 비순환 그래프(DAG)로 모델링
- 각 작업 노드의 선행/후행 관계 정의
- 기계별 작업 가능한 공정과 속도 정보 구성

## 5. scheduler 모듈  

### DispatchPriorityStrategy.execute() 함수
**위치**: `scheduler/scheduling_core.py`

#### Input Parameters
- `dag_manager`: DAGGraphManager - DAG 그래프 관리자
- `scheduler`: Scheduler - 스케줄러 객체 (자원할당, 다운타임 적용 완료)
- `dag_df`: pandas.DataFrame - DAG 데이터프레임  
- `priority_order`: pandas.DataFrame - 우선순위 정렬된 작업 리스트
- `window_days`: int - 스케줄링 윈도우 일수

#### Output Returns  
- `result`: pandas.DataFrame
  - 최종 스케줄링 결과
  - 컬럼: id, machine_index, node_start, node_end, depth, children 등

### 핵심 처리
- 우선순위에 따라 작업을 순차적으로 스케줄링
- 선행 작업 완료 확인 → 기계 가용시간 계산 → 셋업시간 고려 → 작업 할당

## 6. results 모듈

### create_results() 함수
**위치**: `results/__init__.py:6`

#### Input Parameters
- `output_final_result`: pandas.DataFrame - 스케줄러 최종 결과
- `merged_df`: pandas.DataFrame - 주문 및 공정 병합 데이터
- `original_order`: pandas.DataFrame - 원본 주문 데이터
- `sequence_seperated_order`: pandas.DataFrame - 공정별 분리 주문
- `machine_mapping`: dict - 기계인덱스 → 기계코드 매핑
- `machine_schedule_df`: pandas.DataFrame - 기계 스케줄 데이터
- `base_date`: datetime - 기준 시간
- `scheduler`: Scheduler - 스케줄러 인스턴스

#### Output Returns
- `dict` 포함 항목:
  - `new_output_final_result`: pandas.DataFrame - 지각 계산 완료된 최종 결과
  - `late_days_sum`: int - 총 지각 일수  
  - `merged_result`: pandas.DataFrame - 모든 정보가 병합된 결과
  - `machine_info`: pandas.DataFrame - 기계별 상세 스케줄 정보

### 핵심 처리
- 납기 지연 계산 → 결과 데이터 병합 → 기계 스케줄 가독성 개선

## 7. 주요 데이터 구조

### Order 데이터 구조
```
P/O NO: 주문번호 (문자열)
GITEM: 제품코드 (문자열)  
GITEM명: 제품명 (문자열)
SPEC: 제품규격 "두께*너비*길이" (문자열)
의뢰량: 주문수량 (정수)
납기일: 납기일자 (datetime)
```

### Scheduling Result 구조  
```
id: 작업 고유식별자 "PO번호_공정명" (문자열)
machine_index: 할당된 기계 인덱스 (정수)
node_start: 작업 시작시간 (시간단위, 실수)
node_end: 작업 종료시간 (시간단위, 실수)  
depth: DAG 깊이 (정수)
children: 후행 작업 리스트 (리스트)
```

## 8. 개발시 주의사항

### 데이터 타입 및 형식
- **시간 단위**: 모든 시간은 추상적 시간 단위 사용 (48단위 = 1일)
- **기계 식별**: 기계인덱스(0,1,2...) ↔ 기계코드(C2010, C2250...) ↔ 기계명(1호기, 25호기...) 매핑 필요
- **날짜 형식**: datetime 객체 사용, 문자열 변환시 "YYYY-MM-DD" 형식

### 성능 고려사항
- **대용량 데이터**: 주문 1000건 이상시 메모리 최적화 필요
- **실행 시간**: 전체 파이프라인 30-60초 소요 예상
- **병목 구간**: DAG 생성, 스케줄링 실행 단계

### 에러 처리 포인트
- **필수 컬럼 누락**: Excel 파일 구조 변경시 컬럼명 불일치
- **데이터 타입 오류**: 숫자 컬럼에 문자열 입력
- **제약 위반**: 불가능한 기계-공정 조합 할당  
- **순환 의존성**: DAG 구성시 순환 참조 발생
- **메모리 부족**: 대규모 데이터셋 처리시

### 확장성 고려사항
- **다중 공장**: 현재는 단일 공장 기준, 다중 공장 확장 필요시 구조 변경
- **실시간 업데이트**: 현재는 배치 처리, 실시간 주문 추가/변경 기능 확장 가능
- **최적화 알고리즘**: 현재 우선순위 기반, 메타휴리스틱 알고리즘으로 확장 가능

## 구현 권장사항

1. **비동기 처리**: 대용량 데이터 처리시 백그라운드 작업으로 실행
2. **상태 추적**: 장시간 실행되는 스케줄링의 진행상황 추적 기능 제공
3. **데이터 검증**: 입력 데이터 유효성 검사 로직 강화
4. **에러 핸들링**: 각 단계별 세부적인 에러 메시지 및 복구 방안 제공
5. **로깅**: 실행 과정의 상세 로그 기록으로 디버깅 지원
6. **결과 캐싱**: 동일한 입력에 대한 결과 캐싱으로 성능 향상
7. **설정 관리**: config.py를 통한 중앙화된 설정 관리 활용