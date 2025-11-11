# 제조업 생산 스케줄링 시스템

## 개요
제약 조건을 고려한 유연 작업장 스케줄링 문제(FJSP) 해결 시스템입니다. 기계별 처리 속도, 수율 예측, 배합액 최적화, 셋업 시간, 에이징(aging) 공정, 기계 제약 등을 종합적으로 고려하여 최적 생산 스케줄을 생성합니다.

## 핵심 특징
- **에이징 공정 처리**: 특정 공정 후 필수 대기 시간(에이징)을 자동으로 삽입
- **배합액 최적화**: 동적 배합액 선택 및 셋업 시간 최소화
- **윈도우 기반 동적 스케줄링**: 고정 윈도우 크기로 준비된 작업만 스케줄링
- **DAG 기반 의존성 관리**: 공정 간 선후 관계를 정확히 추적

## 시스템 구조

### 1. 설정 관리 (`config.py`)
시스템 전반의 설정을 dataclass로 구조화하여 관리:
- **ColumnNames**: 컬럼명 표준화 (GitemNo, PoNo, PROCCODE 등)
- **BusinessConstants**: 비즈니스 상수 (기준일, 윈도우 기간, 수율/라인스피드 기간 등)

### 2. 데이터 검증 및 전처리 (`src/validation/`)
원본 Excel 데이터의 유효성 검사 및 표준 형식 변환:

**핵심 함수**: `preprocess_production_data()` (`src/validation/__init__.py:13`)
- **DataValidator**: 데이터 유효성 검사 및 중복 제거
  - 제품군-GITEM-SITEM 정합성 검증
  - 공정, 수율, 라인스피드 데이터 GITEM 존재성 검증
  - 배합액 데이터 검증
- **ProductionDataPreprocessor**: 데이터 변환
  - `preprocess_order_data()`: 주문 데이터 전처리 및 납기 여유일자 반영
  - `preprocess_linespeed_data()`: 라인스피드 피벗 테이블 생성
  - `preprocess_operation_data()`: 공정 타입 및 순서 정보 생성
  - `preprocess_yield_data()`: 수율 데이터 정제
  - `preprocess_chemical_data()`: 배합액 정보 변환
  - `preprocess_machine_master_info()`: 설비 마스터 정보 생성

**입력**: Ver4 Excel 파일의 각 시트 (order_df, linespeed_df, operation_df, yield_df, chemical_df 등)
**출력**: 표준화된 데이터 딕셔너리 (order_data, linespeed, operation_types, yield_data, machine_master_info 등)

### 3. 주문 시퀀스 생성 (`src/order_sequencing/`)
주문 데이터와 공정 정보를 스케줄링에 적합한 형태로 변환:

**핵심 함수**: `generate_order_sequences()` (`src/order_sequencing/__init__.py:8`)
- **OrderPreprocessor**: 주문 데이터 전처리
  - `seperate_order_by_month()`: 납기일 기준 월별 주문 분리
  - `same_order_groupby()`: 동일 주문 통합으로 배치 효율화
- **SequencePreprocessor**: 공정 시퀀스 생성
  - `create_sequence_seperated_order()`: 주문별 상세 공정 순서 생성
- **OperationMachineLimit**: 기계 제약 처리
  - `operation_machine_limit()`: 기계 제약 조건 적용
  - `operation_machine_exclusive()`: 강제 할당 처리
- **FabricCombiner**: 폭 조합 처리
  - `combine_fabric_width()`: 너비 조합 로직 적용

**입력**: order, operation_sequence, operation_types, machine_limit, machine_allocate, linespeed, chemical_data
**출력**: sequence_seperated_order, updated_linespeed, unable_gitems, unable_order, unable_details

### 4. 수율 관리 (`src/yield_management/`)
과거 데이터 기반 수율 예측 및 생산량 조정:

**핵심 함수**: `yield_prediction()` (`src/yield_management/__init__.py:4`)
- GITEM별 수율 데이터 병합
- 생산비율(product_ratio = 1/yield) 계산
- 원본 생산길이 백업 및 수율 반영 생산길이 조정

**입력**: yield_data, sequence_seperated_order
**출력**: 수율이 반영된 sequence_seperated_order (original_production_length, production_length 포함)

### 5. DAG 관리 (`src/dag_management/`)
공정 간 의존성을 DAG(방향성 비순환 그래프)로 모델링:

**핵심 함수**: `create_complete_dag_system()` (`src/dag_management/__init__.py:10`)
- **DAGDataFrameCreator**: DAG 데이터프레임 생성
  - `create_full_dag()`: 전체 DAG 구조 생성
- **NodeDictCreator**: 노드 딕셔너리 생성
  - `create_opnode_dict()`: 작업 노드 정보 딕셔너리 (CHEMICAL_LIST, SELECTED_CHEMICAL 포함)
- **DAGGraphManager**: DAG 그래프 구축
  - `build_from_dataframe()`: 그래프 구조 생성 및 의존성 관리
- **MachineDict**: 기계 정보 딕셔너리
  - `create_machine_dict()`: 기계별 작업 가능 리스트 생성
- **MergeProcessor**: 데이터 병합
  - `merge_order_operation()`: 주문-공정 정보 통합

**입력**: sequence_seperated_order, linespeed, machine_master_info
**출력**: dag_df, opnode_dict, manager, machine_dict, merged_df

### 6. 스케줄링 엔진 (`src/scheduler/`)
핵심 스케줄링 로직과 배합액 최적화 구현:

**주요 컴포넌트**:
- **DispatchPriorityStrategy** (`scheduler/scheduling_core.py:117`): 우선순위 기반 스케줄링 전략
  - `execute()`: 윈도우 기반 동적 스케줄링 실행
- **SetupMinimizedStrategy** (`scheduler/scheduling_core.py:258`): 배합액 기반 셋업 최소화 전략
  - `find_best_chemical()`: 윈도우 내 최적 배합액 선택
  - 같은 공정 내 배합액별 그룹화 및 순차 스케줄링
  - SELECTED_CHEMICAL 동적 할당
- **DelayProcessor** (`scheduler/delay_dict.py:13`): 셋업 시간 처리
  - `calculate_delay()`: 공정 교체 시간 계산 (SELECTED_CHEMICAL 기준)
  - 폭 변경 지연시간 계산
- **Scheduler** (`scheduler/scheduler.py:10`): 메인 스케줄러
  - `allocate_resources()`: 자원 할당
  - `allocate_machine_downtime()`: 기계 다운타임 적용
- **DispatchRule** (`scheduler/dispatch_rules.py:8`): 디스패치 규칙 생성
  - `create_dispatch_rule()`: 납기일, depth, 너비 기반 우선순위 생성

**입력**: dag_manager, scheduler, dag_df, priority_order, window_days
**출력**: result (스케줄링 결과 DataFrame - 노드별 시작/종료 시간 포함)

### 7. 결과 처리 (`src/results/`)
스케줄링 결과를 분석하고 가독성 있는 형태로 변환:

**핵심 함수**: `create_results()` (`src/results/__init__.py:14`)
- **DataCleaner** (`results/data_cleaner.py`): 가짜 작업 제거 및 makespan 계산
  - `clean_all_data()`: depth -1 노드 제거, 실제 makespan 계산
- **LateProcessor** (`results/late_processor.py`): 납기 지연 분석
  - `process()`: 지각 주문 식별, 지각 일수 계산
- **MergeProcessor** (`results/merge_processor.py`): 데이터 병합
  - `process()`: 주문-공정-스케줄 정보 통합
- **MachineProcessor** (`results/machine_processor.py`): 기계 스케줄 처리
  - `process()`: 읽기 쉬운 기계 스케줄 생성
- **GapAnalysisProcessor** (`results/gap_analyzer.py`): 간격 분석
  - `process()`: 작업 간 지연시간 상세 분석 (공정교체, 폭변경, 배합액교체 등)
- **GanttChartGenerator** (`results/gantt_chart_generator.py`): 간트차트 생성
  - `generate()`: PNG 형식 간트차트 시각화

**입력**: raw_scheduling_result, merged_df, original_order, sequence_seperated_order, machine_master_info, base_date, scheduler
**출력**: final_results 딕셔너리 (makespan, order_summary, order_info, machine_info, detailed_gaps, machine_summary, gantt_filename 등)

## 실행 파이프라인

**메인 실행**: `main.py`의 `run_level4_scheduling()`

```
1. Excel 파일 로딩 (main.py:31-98)
   ├─ "생산계획 입력정보.xlsx" 로드 (8개 시트)
   │   (tb_polist, tb_linespeed, tb_itemproc, tb_productionyield, tb_chemical 등)
   ├─ Aging 데이터 로드 및 병합
   │   (tb_agingtime_gitem, tb_agingtime_gbn)
   └─ Global 기계 제약조건 로드

2. Validation (10-30%) - main.py:105-147
   └─ preprocess_production_data()
      ├─ DataValidator: 데이터 유효성 검사 및 중복 제거
      └─ ProductionDataPreprocessor: 표준 형식 변환

3. Order Sequencing (30-35%) - main.py:150-151
   └─ generate_order_sequences()
      ├─ 월별 주문 분리 및 통합
      ├─ 공정 시퀀스 생성
      ├─ 기계 제약 및 강제 할당 처리
      └─ 폭 조합 로직 적용

4. Yield Prediction (35%) - main.py:157-160
   └─ yield_prediction()
      └─ 수율 기반 생산길이 조정

5. Aging 요구사항 파싱 (38%) - main.py:164-166 ⭐ NEW
   └─ parse_aging_requirements()
      └─ Aging 맵 생성 (에이징 노드 자동 생성 준비)

6. DAG Creation (40-50%) - main.py:169-170
   └─ create_complete_dag_system()
      ├─ DAG 데이터프레임 생성 (에이징 노드 포함)
      ├─ opnode_dict 생성 (CHEMICAL_LIST, AGING_TIME 포함)
      ├─ DAG 그래프 구축
      └─ 기계 딕셔너리 생성

7. Scheduling (60-85%) - main.py:183-195
   └─ run_scheduler_pipeline()
      ├─ 디스패치 규칙 생성 (납기일, depth, 너비 기준)
      ├─ DelayProcessor 초기화 (공정교체, 폭변경, 배합액 지연시간)
      ├─ 스케줄러 초기화 및 자원 할당
      ├─ 기계 다운타임 적용
      └─ 윈도우 기반 동적 스케줄링 실행
         ├─ DispatchPriorityStrategy: 우선순위 기반 디스패치
         ├─ SetupMinimizedStrategy: 배합액 최적화 및 셋업 최소화
         └─ AgingMachineStrategy: 에이징 노드 특별 처리

8. Results Processing (80-100%) - main.py:202-210
   └─ create_results()
      ├─ 가짜 작업 제거 및 makespan 계산
      ├─ 지각 작업 처리
      ├─ 주문-공정 병합
      ├─ 간격 분석 (공정교체, 폭변경, 배합액교체 지연시간)
      └─ 간트차트 생성

9. 파일 저장 (100%) - main.py:227-244
   ├─ result.xlsx: 원본 스케줄링 결과
   ├─ 0829 스케줄링결과.xlsx: 가공된 결과 (5개 시트)
   │   ├─ 주문_생산_요약본
   │   ├─ 주문_생산_정보
   │   ├─ 호기_정보
   │   ├─ 지연시간분석
   │   └─ 지연시간호기요약
   └─ level4_gantt.png: 간트차트
```

## 주요 기능

### 핵심 알고리즘
- **에이징 노드 자동 삽입**: 특정 공정 후 필수 대기 시간을 DAG에 자동 삽입
  - 에이징 노드는 특별한 기계(machine_index=-1)에 할당
  - 에이징 중 다른 공정과 병렬 처리 가능
- **윈도우 기반 동적 스케줄링**: 고정 윈도우 크기로 준비된 작업만 스케줄링
- **배합액 최적화**: 같은 공정 내에서 사용 빈도 기반 배합액 선택 및 그룹화
- **셋업 최소화**: 배합액별 작업 연속 배치로 교체 시간 최소화
- **우선순위 기반 디스패치**: 납기일, depth, 너비 기준 작업 우선순위 결정

### 제약 조건 처리
- **에이징 시간**: 특정 공정 후 필수 대기 시간 (자동으로 DAG에 삽입)
- **기계 제한**: 특정 공정을 수행할 수 없는 기계 제약 (local, global)
- **강제 할당**: 특정 GITEM을 특정 기계에 강제 할당
- **공정 교체 시간**: 이전 공정 타입과 다음 공정 타입 간 셋업 시간
- **폭 변경 시간**: 작업 간 너비 차이에 따른 조정 시간
- **배합액 교체 시간**: SELECTED_CHEMICAL가 다를 때 발생하는 지연
- **기계 다운타임**: 기계 중단 시간 반영
- **수율 반영**: 품질 손실을 고려한 생산량 조정

### 성과 지표
- **Makespan**: 전체 작업 완료 시간
- **납기준수율**: 납기 내 완료된 주문 비율
- **지각 일수**: 납기 대비 지연된 총 일수
- **기계 활용률**: 작업 시간 / 전체 시간
- **간격 분석**: 작업 간 유휴 시간 상세 분석 (대기, 공정교체, 폭변경, 배합액교체)

## 입력 데이터

### 필수 입력 파일

#### 1. 메인 입력 파일
**`data/input/생산계획 입력정보.xlsx`** - 모든 입력 데이터를 포함하는 통합 Excel 파일

**시트 구성:**
1. **tb_polist**: 주문 정보
   - 필수 컬럼: gitemno, ponumber, ipgm_qty, duedate, length, width 등

2. **tb_itemspec**: 제품군-GITEM-SITEM 매핑 (검증용)
   - 필수 컬럼: grp2_name, gitemno, sitem 등

3. **tb_linespeed**: 기계별 처리 속도
   - 필수 컬럼: gitemno, proccode, machineno, line_speed 등

4. **tb_itemproc**: 제품별 공정 순서
   - 필수 컬럼: gitemno, procseq, procname, proccode, procgbn 등

5. **tb_productionyield**: 수율 데이터
   - 필수 컬럼: gitemno, yield 등

6. **tb_chemical**: 공정별 사용 가능 배합액
   - 필수 컬럼: gitemno, proccode, che1, che2 등

7. **tb_changetime**: 공정 타입 간 교체 시간
   - 필수 컬럼: prev_proccode, next_proccode, change_time 등

8. **tb_changewidth**: 너비 변경에 따른 지연시간
   - 필수 컬럼: machineno, long_to_short, short_to_long 등

9. **tb_agingtime_gitem**: GITEM별 에이징 시간 ⭐ NEW
   - 필수 컬럼: gitemno, prev_procgbn, aging_time 등

10. **tb_agingtime_gbn**: 제품군별 에이징 시간 ⭐ NEW
   - 필수 컬럼: grp2_name, prev_procgbn, aging_time 등

#### 2. 시나리오 파일 (선택 사항)
**`data/input/시나리오_공정제약조건.xlsx`**
- **machine_limit**: 공정별 기계 제약 (local)
- **machine_allocate**: 강제 할당 조건
- **machine_rest**: 기계 중단 시간

#### 3. Global 제약조건 파일 (선택 사항)
**`data/input/글로벌_제약조건_블랙리스트.xlsx`**
- 제품군별 기계 제외 조건 (Global Machine Limit)

### 설정 파라미터 (`config.py`)
```python
BASE_YEAR = 2025          # 기준 년도
BASE_MONTH = 5            # 기준 월
BASE_DAY = 15             # 기준 일
WINDOW_DAYS = 5           # 스케줄링 윈도우 크기 (일)
LINESPEED_PERIOD = '6_months'  # 라인스피드 집계 기간
YIELD_PERIOD = '6_months'      # 수율 집계 기간
BUFFER_DAYS = 7           # 납기 여유일자
```

## 출력 결과

### 1. Excel 파일
**`data/output/result.xlsx`** - 원본 스케줄링 결과
- 모든 노드의 스케줄링 정보 (node_start, node_end, 할당 기계 등)

**`data/output/0829 스케줄링결과.xlsx`** - 가공된 최종 결과
- **주문_생산_요약본**: 주문별 완료 시간, 납기, 지각일수
- **주문_생산_정보**: 상세 작업 정보
- **호기_정보**: 기계별 작업 스케줄
- **지연시간분석**: 작업 간 간격 상세 분석 (대기, 공정교체, 폭변경, 배합액교체)
- **지연시간호기요약**: 기계별 간격 요약

### 2. 시각화
**`data/output/level4_gantt.png`** - 간트차트
- 기계별 작업 타임라인 시각화
- 간격(gap) 표시 옵션

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 스케줄링 실행
python main.py
```

## 기술 스택
- **Python 3.11+**
- **pandas**: 데이터 처리
- **openpyxl**: Excel 파일 읽기/쓰기
- **matplotlib**: 간트차트 시각화
- **networkx**: DAG 그래프 관리

## 프로젝트 구조
```
python_engine/
├── config.py                    # 설정 관리
├── main.py                      # 메인 실행 파일
├── requirements.txt             # 의존성 목록
├── data/
│   ├── input/                   # 입력 데이터
│   │   └── 생산계획 필요기준정보 내역-Ver4.xlsx
│   └── output/                  # 출력 결과
├── src/
│   ├── validation/              # 데이터 검증 및 전처리
│   │   ├── __init__.py
│   │   ├── validator.py
│   │   └── production_preprocessor.py
│   ├── order_sequencing/        # 주문 시퀀스 생성
│   │   ├── __init__.py
│   │   ├── order_preprocessing.py
│   │   ├── sequence_preprocessing.py
│   │   ├── operation_machine_limit.py
│   │   └── fabric_combiner.py
│   ├── yield_management/        # 수율 관리
│   │   ├── __init__.py
│   │   └── yield_predictor.py
│   ├── dag_management/          # DAG 관리
│   │   ├── __init__.py
│   │   ├── dag_dataframe.py
│   │   ├── node_dict.py
│   │   ├── dag_manager.py
│   │   └── dag_visualizer.py
│   ├── scheduler/               # 스케줄링 엔진
│   │   ├── __init__.py
│   │   ├── scheduling_core.py   # 핵심 전략 (배합액 최적화)
│   │   ├── scheduler.py
│   │   ├── delay_dict.py        # 지연시간 계산
│   │   ├── dispatch_rules.py
│   │   └── machine.py
│   └── results/                 # 결과 처리
│       ├── __init__.py
│       ├── data_cleaner.py
│       ├── late_processor.py
│       ├── merge_processor.py
│       ├── machine_processor.py
│       ├── gap_analyzer.py      # 간격 분석
│       └── gantt_chart_generator.py
└── 원본데이터(사용X)/          # 레거시 데이터
```

## 주요 개선 사항 (최신 버전)

### v3.0 주요 변경사항 (에이징 기능 추가) ⭐
1. **에이징 공정 자동화**: parse_aging_requirements() 함수로 aging_map 자동 생성
   - Aging 데이터를 DAG에 자동으로 에이징 노드 삽입
   - 에이징 노드는 특별한 기계(machine_index=-1)에 할당
   - AgingMachineStrategy로 겹치는 에이징 처리
2. **입력 파일 구조 변경**: "생산계획 필요기준정보 내역-Ver4.xlsx" → "생산계획 입력정보.xlsx"
   - Aging 관련 시트 추가 (tb_agingtime_gitem, tb_agingtime_gbn)
   - 시트명 변경 (한글 → 영문 접두사)
3. **Global 제약조건 통합**: 글로벌_제약조건_블랙리스트.xlsx 자동 처리
4. **opnode_dict 확장**: AGING_TIME 컬럼 추가

### v2.0 주요 변경사항
1. **통합 입력 파일**: 여러 Excel 파일 → 단일 파일로 통합
2. **Validation 모듈 추가**: 데이터 유효성 검사 및 중복 제거 자동화
3. **배합액 최적화**: 동적 배합액 선택 및 셋업 최소화 알고리즘
4. **모듈 재구성**: preprocessing → validation + order_sequencing으로 분리
5. **간격 분석 강화**: 대기, 공정교체, 폭변경, 배합액교체 세부 분류

### 배합액 최적화 로직
- **CHEMICAL_LIST**: 각 노드가 사용 가능한 배합액 목록 (튜플)
- **SELECTED_CHEMICAL**: 스케줄링 시 실제 선택된 배합액 (문자열)
- **최적화 전략**:
  1. 윈도우 내 같은 공정 노드 그룹화
  2. 가장 많이 사용 가능한 배합액 선택
  3. 같은 배합액 사용 노드를 연속 스케줄링
  4. 배합액 교체 시 지연시간 적용

### 에이징 공정 처리 로직
- **AGING_TIME**: 각 노드의 에이징 시간 (시간 단위)
- **에이징 노드 자동 생성**:
  1. parse_aging_requirements()가 aging_map 생성
  2. create_complete_dag_system()에서 에이징 노드 자동 삽입
  3. 에이징 노드는 부모-자식 관계로 DAG에 통합
- **에이징 노드 스케줄링**:
  1. AgingMachineStrategy로 특별한 기계(machine_index=-1)에 할당
  2. 에이징 기계에서는 작업이 겹치는 것을 허용
  3. 에이징 완료 후 다음 공정이 자동으로 스케줄됨

상세 알고리즘은 `src/dag_management/dag_dataframe.py:parse_aging_requirements()` 참조

## 라이선스
Proprietary - 내부 사용 전용
