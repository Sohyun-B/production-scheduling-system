# 생산 스케줄링 시스템 모듈 입출력 명세 (요약본)

## 전체 흐름

```
0. 데이터 로딩 (4개 Excel 파일 + 설정)
   ↓
1. Validation - preprocess_production_data()
   ↓
2. MachineMapper 생성 ⭐ NEW
   ↓
3. Order Sequencing - generate_order_sequences()
   ↓
4. Yield Prediction - yield_prediction()
   ↓
5. Aging 파싱 - parse_aging_requirements()
   ↓
6. DAG Creation - create_complete_dag_system()
   ↓
7. Scheduling - run_scheduler_pipeline() ⭐ 변경됨
   ↓
8. Results - create_new_results() ⭐ 변경됨
   ↓
9. 파일 저장 (5개 시트) ⭐ 변경됨
```

---

## 0. 데이터 로딩

### 입력 파일 (4개)
1. **생산계획 입력정보.xlsx** (11개 시트)
   - tb_polist, tb_itemspec, tb_linespeed, tb_itemproc
   - tb_productionyield, tb_chemical, tb_changetime, tb_changewidth
   - tb_agingtime_gitem, tb_agingtime_gbn

2. **tb_commomconstraint.xlsx** (글로벌 기계 제약)

3. **시나리오_공정제약조건.xlsx** (3개 시트)
   - machine_limit, machine_allocate, machine_rest

4. **machine_master_info.xlsx** ⭐ NEW (기계 마스터 정보)

### 설정 파라미터
```python
base_date, window_days, linespeed_period, yield_period
```

---

## 1. Validation

**함수**: `preprocess_production_data()`

### 입력
- 11개 DataFrame (order_df, linespeed_df, operation_df 등)
- aging_gitem_df, aging_gbn_df ⭐
- global_machine_limit_df ⭐
- linespeed_period, yield_period, validate, save_output

### 출력
```python
processed_data = {
    'order_data': pd.DataFrame,
    'linespeed': pd.DataFrame,          # wide format
    'operation_types': pd.DataFrame,
    'operation_sequence': pd.DataFrame,
    'yield_data': pd.DataFrame,         # GITEM + PROCCODE ⭐
    'chemical_data': pd.DataFrame,
    'operation_delay': pd.DataFrame,
    'width_change': pd.DataFrame,
    'aging_data': pd.DataFrame,         # gitem + gbn 통합 ⭐
    'global_machine_limit': pd.DataFrame ⭐
}
```

---

## 2. MachineMapper 생성 ⭐ NEW

**클래스**: `MachineMapper`

### 입력
```python
machine_master_info_df (pd.DataFrame)
```

### 출력
```python
machine_mapper (MachineMapper 인스턴스)
  - get_machine_no(machine_code) → machineno
  - get_machine_code(machineno) → machine_code
  - get_machine_type(machine_code) → 공정구분
```

---

## 3. Order Sequencing

**함수**: `generate_order_sequences()`

### 입력
- order, operation_seperated_sequence, operation_types
- local_machine_limit ⭐, global_machine_limit ⭐
- machine_allocate, linespeed, chemical_data

### 출력
```python
(
    sequence_seperated_order,  # 공정별 분리 주문
    linespeed,                 # 제약 반영 후
    unable_gitems,
    unable_order,
    unable_details
)
```

---

## 4. Yield Prediction

**함수**: `yield_prediction()`

### 입력
- yield_data, sequence_seperated_order

### 처리
- **GITEM + PROCCODE** 기준 매칭 ⭐ 변경됨
- **10 단위 반올림** ⭐ 신규

### 출력
```python
sequence_seperated_order (updated)
  + original_production_length
  + production_length (수율 + 10단위 반올림)
```

---

## 5. Aging 파싱

**함수**: `parse_aging_requirements()`

### 입력
- aging_df, sequence_seperated_order

### 출력
```python
aging_map = {
    ("GITEM001", "DY"): 96.0,
    ("GITEM002", "CT"): 48.0,
    ...
}
```

---

## 6. DAG Creation

**함수**: `create_complete_dag_system()`

### 입력
- sequence_seperated_order, linespeed
- **machine_mapper** ⭐ 변경됨 (기존: machine_master_info)
- aging_map

### 출력
```python
(
    dag_df,         # DAG 데이터프레임
    opnode_dict,    # 노드 메타데이터 (AGING_TIME 포함)
    manager,        # DAGGraphManager
    machine_dict,   # {node_id: {machineno: 소요시간}} ⭐ 변경됨
    merged_df       # 주문-공정 병합
)
```

---

## 7. Scheduling

**함수**: `run_scheduler_pipeline()` ⭐ 신규 wrapper

### 입력
- dag_df, sequence_seperated_order, width_change_df
- **machine_mapper** ⭐ 변경됨 (기존: machine_master_info)
- opnode_dict, operation_delay_df, machine_dict
- machine_rest, base_date, manager, window_days

### 출력
```python
(
    result,      # 스케줄링 결과 (machine = machineno) ⭐
    scheduler    # Scheduler 인스턴스
)
```

---

## 8. Results Processing

**함수**: `create_new_results()` ⭐ 변경됨 (기존: create_results)

### 입력
- raw_scheduling_result, merged_df, original_order
- sequence_seperated_order
- **machine_mapper** ⭐ 변경됨
- base_date, scheduler

### 출력
```python
final_results = {
    'metadata': {...},                          # makespan, task 수 등
    'performance_metrics': {...},               # PO수, 납기준수율, 가동률 ⭐
    'lateness_summary': {...},                  # 지각 요약 ⭐
    'performance_summary': List[dict],          # 시트1 ⭐
    'machine_info': pd.DataFrame,               # 시트2
    'machine_detailed_performance': pd.DataFrame, # 시트3 ⭐
    'order_lateness_report': pd.DataFrame,      # 시트4 ⭐
    'gap_analysis': pd.DataFrame                # 시트5 ⭐
}
```

---

## 9. 파일 저장

### 저장 파일
1. **result.xlsx** (원본 결과, 임시)
2. **0829 스케줄링결과.xlsx** (최종 결과, 5개 시트) ⭐ 변경됨

#### 5개 시트 구성 ⭐ 변경됨
1. **스케줄링_성과_지표**: PO수, makespan, 납기준수율, 평균가동률
2. **호기_정보**: 기계별 작업 스케줄
3. **장비별_상세_성과**: 기계별 가동률, 가동시간, 작업 수
4. **주문_지각_정보**: 주문별 납기 대비 완료 일자, 지각일수
5. **간격_분석**: 작업 간 간격(gap) 상세 분석

---

## 주요 변경사항 (v3.0)

### 1. MachineMapper 도입 ⭐
- 기계 인덱스 → **machineno** 기반으로 변경
- `machine_master_info` → `machine_mapper` 사용
- 기계 정보 조회 중앙화

### 2. new_results 모듈 사용 ⭐
- `create_results()` → `create_new_results()`
- **5개 시트**로 재구성 (기존: 5개 다른 구성)

### 3. 입력 파일 구조 변경 ⭐
- aging: 통합 엑셀 시트로 변경 (tb_agingtime_gitem, tb_agingtime_gbn)
- global/local machine limit 분리

### 4. run_scheduler_pipeline 도입 ⭐
- 스케줄링 파이프라인 단순화 (wrapper function)

### 5. 수율 적용 로직 개선 ⭐
- **GITEM + PROCCODE** 기준 (기존: GITEM만)
- **10단위 반올림** 추가

---

## 엔드포인트 설계 (권장)

### 하이브리드 방식 (추천)
```
POST /api/scheduling/preprocess   → 1+2+3+4+5 통합 (데이터 준비)
POST /api/scheduling/schedule     → 6+7 통합 (스케줄링 실행)
POST /api/scheduling/postprocess  → 8 (결과 처리)
```

### 단일 엔드포인트
```
POST /api/scheduling/run → 전체 파이프라인 실행
```

---

## 핵심 객체 구조 변경

### machine_dict (변경됨) ⭐
**기존**:
```python
{"N00001_1_공정": [시간1, 시간2, ...]}  # 리스트 (인덱스 기반)
```

**현재**:
```python
{
    "N00001_1_공정": {
        1: 120.5,    # machineno=1에서의 소요시간
        2: 9999,     # 처리 불가
        3: 150.2     # machineno=3에서의 소요시간
    }
}  # 딕셔너리 (machineno 기반)
```

### DAGNode.machine (변경됨) ⭐
**기존**: `node.machine = 0` (인덱스)
**현재**: `node.machine = 1` (machineno)

### Machine_Time_window (변경됨) ⭐
**기존**: `Machine_index`
**현재**: `machineno`

---

## 주의사항

1. **machineno 기반 작업** ⭐
   - 모든 기계 관련 작업은 machineno 기준
   - MachineMapper를 통한 변환 필수

2. **데이터 직렬화**
   - MachineMapper는 pickle로 직렬화 필요

3. **성능**
   - 전체 실행 시간: 데이터 크기에 따라 수십 초 ~ 수 분
   - 스케줄링(7단계)이 가장 오래 걸림

4. **에러 처리**
   - unable_gitems, unable_order 정보 사용자에게 전달 필수
