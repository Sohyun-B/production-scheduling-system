# 제조업 생산 스케줄링 시스템

## 개요
제약 조건을 고려한 유연 작업장 스케줄링 문제(FJSP) 해결 시스템입니다. 기계별 처리 속도, 수율 예측, 셋업 시간, 기계 제약 등을 종합적으로 고려하여 최적 생산 스케줄을 생성합니다.

## 시스템 구조

### 1. 설정 관리 (`config.py`)
시스템 전반의 설정을 dataclass로 구조화하여 관리:
- **FilePaths**: Excel 파일 경로 관리
- **SheetNames**: 시트명 정의 
- **ColumnNames**: 컬럼명 표준화
- **BusinessConstants**: 비즈니스 상수 (기준일, 윈도우 기간, 표준 너비 등)

### 2. 전처리 모듈 (`preprocessing/`)
주문 데이터와 공정 정보를 스케줄링에 적합한 형태로 변환:

**핵심 함수**: `preprocessing()` (`preprocessing/__init__.py:6`)
- `seperate_order_by_month()`: 납기일 기준 월별 주문 분리
- `same_order_groupby()`: 동일 주문 통합으로 배치 효율화
- `create_sequence_seperated_order()`: 주문별 상세 공정 순서 생성
- `operation_machine_limit()`: 기계 제약 조건 적용
- `operation_machine_exclusive()`: 강제 할당 처리

### 3. 수율 관리 (`yield_management/`)
과거 데이터 기반 수율 예측 및 생산량 조정:

**핵심 함수**: `yield_prediction()` (`yield_management/__init__.py:3`)
- `YieldPredictor.preprocessing()`: 수율 데이터 전처리
- `YieldPredictor.calculate_predicted_yield()`: 공정별 수율 예측
- `YieldPredictor.predict_sequence_yield()`: 시퀀스별 종합 수율 계산
- `YieldPredictor.adjust_production_length()`: 예측 수율 반영한 생산량 조정

### 4. DAG 관리 (`dag_management/`)
공정 간 의존성을 DAG(방향성 비순환 그래프)로 모델링:

**핵심 함수**: `run_dag_pipeline()` (`dag_management/__init__.py:6`)
- `make_process_table()`: 공정 정보 테이블 생성
- `Create_dag_dataframe.create_full_dag()`: DAG 데이터프레임 생성
- `create_opnode_dict()`: 작업 노드 딕셔너리 생성
- `DAGGraphManager.build_from_dataframe()`: DAG 그래프 구축
- `create_machine_dict()`: 기계별 정보 사전 생성

### 5. 스케줄링 엔진 (`scheduler/`)
핵심 스케줄링 로직과 전략 구현:

**주요 컴포넌트**:
- `SchedulingCore` (`scheduler/scheduling_core.py:31`): 핵심 스케줄링 로직
  - `validate_ready_node()`: 선행 작업 완료 확인
  - `calculate_start_time()`: 최조 시작 시간 계산
- `DelayProcessor` (`scheduler/delay_dict.py`): 셋업 시간 및 폭 변경 처리
- `Scheduler` (`scheduler/scheduler.py`): 메인 스케줄러
  - `allocate_resources()`: 자원 할당
  - `allocate_machine_downtime()`: 기계 다운타임 적용
- `DispatchPriorityStrategy` (`scheduler/scheduling_core.py`): 우선순위 기반 스케줄링 전략
- `create_dispatch_rule()` (`scheduler/dispatch_rules.py`): 디스패치 규칙 생성

### 6. 결과 처리 (`results/`)
스케줄링 결과를 분석하고 가독성 있는 형태로 변환:

**핵심 함수**: `create_results()` (`results/__init__.py:6`)
- `LateOrderCalculator`: 납기 지연 계산
  - `calculate_late_order()`: 지각 주문 식별
  - `calc_late_days()`: 총 지각 일수 계산
- `ResultMerger.merge_everything()`: 모든 결과 데이터 통합
- `MachineScheduleProcessor`: 기계 스케줄 처리
  - `make_readable_result_file()`: 읽기 쉬운 기계 스케줄 생성
  - `machine_info_decorate()`: 기계 정보 장식

## 실행 파이프라인

**메인 실행**: `test_simple_level4.py`의 `run_level4_scheduling()`

1. **데이터 로딩**: Excel 파일들에서 필요한 모든 데이터 로드
2. **전처리**: `preprocessing()` - 주문 데이터 정규화 및 공정 정보 병합
3. **수율 예측**: `yield_prediction()` - 과거 데이터 기반 수율 예측
4. **DAG 생성**: `run_dag_pipeline()` - 공정 의존성 그래프 구축
5. **스케줄링**: `DispatchPriorityStrategy.execute()` - 우선순위 기반 작업 할당
6. **결과 처리**: `create_results()` - 지연 분석 및 결과 정리
7. **파일 저장**: Excel 형태로 최종 결과 출력

## 주요 기능

- **복합 제약 조건**: 기계 제한, 셋업 시간, 폭 변경, 강제 할당 등
- **수율 통합**: 품질 고려사항을 반영한 생산 계획
- **DAG 기반 의존성**: 공정 간 선후 관계 정확한 모델링  
- **유연한 기계 할당**: 다중 기계 옵션을 가진 FJSP 해결
- **성과 지표**: 메이크스팬, 지연일수, 기계 활용률 등

## 입력 데이터
- `품목별 분리 라인스피드 및 공정 순서.xlsx`: 기계 정보, 공정 순서, 수율 데이터
- `공정 재분류 내역 및 교체 시간 정리(250820).xlsx`: 공정군, 교체 시간, 폭변경 시간
- `불가능한 공정 입력값.xlsx`: 기계 제한, 강제 할당 정보
- `25년 5월 PO 내역(송부건).xlsx`: 주문 정보 및 제품 사양

## 출력 결과
- `level4_result.xlsx`: 원본 스케줄링 결과
- `level4_스케줄링결과.xlsx`: 가공된 결과 (주문 요약, 기계 정보 등)
- 간트 차트 시각화 (옵션)