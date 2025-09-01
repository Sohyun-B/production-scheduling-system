# 제조업 생산 스케줄링 시스템 모듈별 입출력 가이드

## 1. 전체 파이프라인 - main.py의 run_level4_scheduling()

### Input (필요한 Excel 파일들)

- **품목별 분리 라인스피드 및 공정 순서.xlsx**
  - 0. 기준정보 정리.ipynb를 통해 전처리된 테이블. 전처리 관련 부분은 파이썬으로 구현하지 않을 것이기에 전처리 파일은 볼 필요 없음.
  - 시트:
    - 품목별 라인스피드: 각 아이템의 공정별 기계에서 수행하는데 걸리는 시간(라인스피드), 빈 값이면 해당 기계에서 생산할 수 없음
    - 공정순서: 각 아이템의 공정에 사용되는 배합액과 공정순서 정보.
    - 기계기준정보: 기계정보
    - 수율데이터: 아이템의 공정별 수율. 현재 기계에 따라 분리되어있지 않음
    - GITEM별 공정: 각 아이템별 공정 (공정순서 시트의 내용과 겹침)
- **공정 재분류 내역 및 교체 시간 정리(250820).xlsx**
  - 시트:
    - 공정군: 각 공정들의 상위분류( = 공정군, 공정분류)
    - 공정교체시간: 공정분류별 교체시간. (단위: 30분)
    - 폭변경: 폭변경으로 인한 교체시간 (단위: 30분)
- **불가능한 공정 입력값.xlsx**
  - 사용자가 입력하는 제약조건.
  - 시트:
    - 기계: 특정 기계가 특정 시간동안 사용 불가능한 경우 작성
    - 공정강제할당: 특정 기계가 원래는 수행할 수 있는 특정 공정을 수행하지 못하는 경우 작성
    - 공정강제회피: 특정 공정을 특정 기계에만 할당하려고 하는 경우 작성

- **preprocesssed_order.xlsx**
  - 시트:
    - Sheet1: 전처리된 25년 5월 주문 내역 (원본: 25년 5월 PO 내역(송부건))

### Output

- **result.xlsx**: 원본 스케줄링 결과 DataFrame (해당 데이터를 가공해서 간트 차트 생성)
- **0829 스케줄링결과.xlsx**: 원본 스케줄링 결과를 사용자가 보기 쉽게 가공한 결과 (고객용, 필요 X)
- **level4_gantt.png**: 간트 차트 이미지 (필요 X)

## 2. preprocessing 모듈

### preprocessing() 함수

**위치**: `preprocessing/__init__.py:6`

#### Input Parameters

- `order`: pandas.DataFrame - 주문 데이터
  - 컬럼: P/O NO, GITEM, GITEM명, SPEC, 의뢰량, 납기일
- `operation_seperated_sequence`: pandas.DataFrame - 공정순서 데이터
- `operation_types`: pandas.DataFrame - 공정분류 데이터
- `machine_limit`: pandas.DataFrame - 공정강제회피 데이터
- `machine_allocate`: pandas.DataFrame - 공정강제할당 데이터
- `linespeed`: pandas.DataFrame - 라인스피드 데이터

#### Output Returns

- `sequence_seperated_order`: pandas.DataFrame
  - 주문별로 공정이 분리된 데이터
  - 컬럼: P/O NO, GITEM, GITEM명, 너비, 길이, 의뢰량, 원단길이, 납기일, 공정명, 공정분류
- `linespeed`: pandas.DataFrame
  - 공정강제할당과 공정강제회피가 적용된 업데이트된 라인스피드 데이터

### 처리 과정 (참조)

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
  - 추가 컬럼: 예측*수율, 전체*예측*수율, 수율*생산비율, 생산길이

### 핵심 처리 (참조)

- 과거 수율 데이터 분석 → 공정별 수율 예측 → 시퀀스별 종합 수율 계산 → 필요 생산량 역산

## 4. dag_management 모듈

### make_process_table() 함수

**위치**: `dag_management/__init__.py:1`

#### Input Parameters
- `sequence_seperated_order`: pandas.DataFrame - 공정별 분리된 주문 데이터

#### Output Returns
- `merged_df`: pandas.DataFrame - 공정 정보 테이블
  - 공정 ID, 위계 구조 정보 포함

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

### 핵심 처리 (참조)

- 공정 의존성을 방향성 비순환 그래프(DAG)로 모델링
- 각 작업 노드의 선행/후행 관계 정의
- 기계별 작업 가능한 공정과 속도 정보 구성

## 5. scheduler 모듈

### create_dispatch_rule() 함수

**위치**: `scheduler/dispatch_rules.py`

#### Input Parameters
- `dag_df`: pandas.DataFrame - DAG 데이터프레임
- `sequence_seperated_order`: pandas.DataFrame - 공정별 분리 주문

#### Output Returns
- `dispatch_rule_ans`: pandas.DataFrame - 우선순위 정렬된 작업 리스트
- `dag_df`: pandas.DataFrame - 업데이트된 DAG 데이터프레임

### DelayProcessor 클래스

**위치**: `scheduler/delay_dict.py`

#### 초기화 Parameters
- `opnode_dict`: dict - 작업 노드 딕셔너리
- `operation_delay_df`: pandas.DataFrame - 공정교체시간 데이터
- `width_change_df`: pandas.DataFrame - 폭변경 시간 데이터

#### 주요 기능
- 셋업 시간 계산 및 공정 간 교체 시간 처리

### Scheduler 클래스

**위치**: `scheduler/scheduler.py`

#### 초기화 Parameters
- `machine_dict`: dict - 기계별 정보 사전
- `delay_processor`: DelayProcessor - 지연 처리 객체

#### 주요 메서드
- `allocate_resources()`: 자원 할당
- `allocate_machine_downtime(machine_rest, base_date)`: 기계 다운타임 적용
- `create_machine_schedule_dataframe()`: 기계 스케줄 데이터프레임 생성

#### 속성
- `Machines`: 기계 객체들의 컬렉션

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

### 핵심 처리 (참조)

- 우선순위에 따라 작업을 순차적으로 스케줄링
- 선행 작업 완료 확인 → 기계 가용시간 계산 → 셋업시간 고려 → 작업 할당

## 6. results 모듈 (중요X)

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

## 7. 결과 데이터 구조

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

- **시간 단위**: 모든 시간은 추상적 시간 단위 사용 (1단위 = 30분)
- **기계 식별**: 기계인덱스(0,1,2...) ↔ 기계코드(C2010, C2250...) ↔ 기계명(1호기, 25호기...) 매핑 필요 (기계기준정보 시트에 정보 존재)
- **날짜 형식**: datetime 객체 사용, 문자열 변환시 "YYYY-MM-DD" 형식


### 확장성 고려사항
- **유저 변경 핸들링**: 유저가 간트에서 DRAG&DROP (혹은 다른 방식으로) 스케줄 변경 시 변경한 스케줄에 맞게 재계산 수행 기능 추후 확장 가능.
                    (현재 이 부분으로 인해 scheduler 관련 상태 관리를 어떻게 해야할지 몰라서 scheduler 관련 함수들 캡슐화 안 되고 main에서 수행중 main.py 66-100줄 (논의 후 변경 필요))
- **최적화 알고리즘(유전 알고리즘)**: 현재 우선순위 규칙 기반, 유전 알고리즘 기능 추가 시 원래 버전 VS 유전 알고리즘으로 생성한 버전 비교 기능 추후 확장 가능
- **main.py 105줄 이후 내용은 고객 협의용. 개발시 중요하게 안 봐도 됨.**


