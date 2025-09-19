# 생산 스케줄링 시스템 모듈 입출력 명세

### {pyrhon_Server/app/services/python_engine_service의 함수명} (변경사항 존재여부) main.py에서의 위치 순서로 작성

## 1. run_preprocessing (변경사항 존재) main.py 107

### 입력
- `order` (pd.DataFrame): Excel에서 로드된 원본 주문 데이터
- `operation_seperated_sequence` (pd.DataFrame): Excel에서 로드된 공정 순서 데이터
- `operation_types` (pd.DataFrame): Excel에서 로드된 공정 분류 데이터
- `machine_limit` (pd.DataFrame): Excel에서 로드된 기계 제약 데이터
- `machine_allocate` (pd.DataFrame): Excel에서 로드된 기계 할당 데이터
- `linespeed` (pd.DataFrame): Excel에서 로드된 라인스피드 데이터

### 출력
- `sequence_seperated_order` (pd.DataFrame): 공정별로 분리된 주문 데이터, 월별 분리 및 동일 주문 병합 완료
- `linespeed` (pd.DataFrame): 기계 제약사항이 반영된 수정된 라인스피드 데이터
- `unable_gitems` (list): 생산 불가능한 GITEM 목록
- `unable_order` (pd.DataFrame): 생산 불가능한 주문 데이터
- `unable_details` (list): 불가능한 GITEM과 공정명 상세 정보

## 2. run_yield_prediction (변경사항 X) main.py 133

### 입력
- `yield_data` (pd.DataFrame): Excel에서 로드된 수율 데이터
- `gitem_operation` (pd.DataFrame): Excel에서 로드된 GITEM-공정 매핑 데이터
- `sequence_seperated_order` (pd.DataFrame): preprocessing 모듈 출력값

### 출력
- `yield_predictor` (YieldPredictor): 수율 예측기 인스턴스
- `sequence_yield_df` (pd.DataFrame): 공정별 예측 수율 결과
- `adjusted_sequence_order` (pd.DataFrame): 수율 반영하여 생산길이가 조정된 주문 데이터

## 3. run_dag_creation (변경사항 X) main.py 139 (create_complete_dag_system)

### 입력
- `sequence_seperated_order` (pd.DataFrame): yield_prediction 모듈 출력값
- `linespeed` (pd.DataFrame): preprocessing 모듈 출력값
- `machine_master_info` (pd.DataFrame): Excel에서 로드된 기계 마스터 정보

### 출력
- `dag_df` (pd.DataFrame): 작업 의존성 그래프 데이터프레임
- `opnode_dict` (dict): 운영 노드 딕셔너리
- `manager` (DAGGraphManager): DAG 그래프 관리자 인스턴스
- `machine_dict` (dict): 기계 딕셔너리
- `merged_df` (pd.DataFrame): 주문 및 공정 병합 테이블


## 4. run_scheduling (변경사항 X)main.py 154-174

### 입력
- `dag_manager` (DAGGraphManager): create_complete_dag_system 모듈 출력값
- `scheduler` (Scheduler): 초기화된 스케줄러 인스턴스
- `dag_df` (pd.DataFrame): create_complete_dag_system 모듈 출력값
- `priority_order`: dispatch_rule 생성 결과
- `window_days` (int): 스케줄링 윈도우 일수

### 출력
- `result` (pd.DataFrame): 스케줄링 결과 데이터프레임 (노드별 시작/종료 시간 포함)

## 5. run_results_processing 모듈 (변경사항: 출력값) main.py 181

### 입력
- `raw_scheduling_result` (pd.DataFrame): DispatchPriorityStrategy 모듈 출력값
- `merged_df` (pd.DataFrame): create_complete_dag_system 모듈 출력값
- `original_order` (pd.DataFrame): Excel에서 로드된 원본 주문 데이터
- `sequence_seperated_order` (pd.DataFrame): yield_prediction 모듈 출력값
- `machine_master_info` (pd.DataFrame): Excel에서 로드된 기계 마스터 정보
- `base_date` (datetime): 기준 날짜
- `scheduler` (Scheduler): 스케줄러 인스턴스

### 출력
- `final_results` (dict): 최종 결과 딕셔너리
  - `actual_makespan` (float): 실제 makespan 값
  - `order_summary` (pd.DataFrame): 주문 생산 요약 데이터
  - `order_info` (pd.DataFrame): 주문 생산 정보
  - `machine_info` (pd.DataFrame): 기계 정보
  - `detailed_gaps` (pd.DataFrame): 상세 간격 분석 결과
  - `machine_summary` (pd.DataFrame): 기계별 간격 요약
  - `late_days_sum` (int): 총 지각 일수
  - `late_products` (list): 지각 제품 목록
  - `late_po_numbers` (list): 지각 주문번호 목록

## 데이터 흐름 요약

```
Excel 데이터 → preprocessing → yield_prediction → create_complete_dag_system → DispatchPriorityStrategy → create_results → 최종 Excel/PNG 출력
```