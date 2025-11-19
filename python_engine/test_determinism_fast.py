"""
비결정성 테스트 스크립트 (최적화 버전)
테스트 1-5는 이미 검증되었으므로 1회만 실행하여 데이터 준비
테스트 6-7만 10회 반복하여 집중 검증
"""

import sys
import os
import hashlib
import pickle
from datetime import datetime
import pandas as pd
import numpy as np
from config import config

# ============================================================================
# 출력 억제 유틸리티
# ============================================================================
class SuppressOutput:
    """다른 모듈의 print 출력을 억제하는 컨텍스트 매니저"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

NUM_ITERATIONS = 10  # 테스트 6-7만 10회 반복

def hash_dataframe(df):
    """DataFrame의 해시값 계산 (내용 기반)"""
    # 리스트 타입 컬럼 처리 (children 같은 컬럼)
    df_copy = df.copy()
    for col in df_copy.columns:
        if df_copy[col].dtype == 'object':
            # 리스트를 튜플로 변환 (해시 가능하게)
            try:
                df_copy[col] = df_copy[col].apply(lambda x: tuple(x) if isinstance(x, list) else x)
            except:
                pass

    # DataFrame을 정렬하여 순서 무관하게 만듦
    try:
        df_sorted = df_copy.sort_index(axis=1).sort_values(by=list(df_copy.columns))
    except:
        # 정렬이 불가능한 경우 인덱스만 정렬
        df_sorted = df_copy.sort_index(axis=1)

    # pickle로 직렬화 후 해시
    return hashlib.md5(pickle.dumps(df_sorted.values)).hexdigest()

def hash_object(obj):
    """일반 객체의 해시값 계산"""
    return hashlib.md5(pickle.dumps(obj)).hexdigest()

def check_consistency(hash_list, name):
    """해시 리스트의 일관성 체크"""
    all_same = len(set(hash_list)) == 1
    status = "[OK] ALL SAME" if all_same else "[DIFF] DIFFERENT"
    unique_hashes = len(set(hash_list))
    print(f"{name:30s}: {status} (unique hashes: {unique_hashes}/{len(hash_list)})")
    if not all_same:
        print(f"  → 발견된 고유 해시값들: {set([h[:8] for h in hash_list])}")
    return all_same

print("=" * 80)
print("비결정성 단위 테스트 (최적화 버전)")
print("=" * 80)
print("테스트 1-5: 1회만 실행 (이미 검증됨)")
print(f"테스트 6-7: {NUM_ITERATIONS}회 반복")
print("=" * 80)

# ============================================================================
# 테스트 1-5: 데이터 준비 (1회만)
# ============================================================================
print("\n[준비 단계] 테스트 1-5 데이터 생성 중...")
print("-" * 80)

# 1. 입력 데이터 로딩
input_file = "data/input/생산계획 입력정보.xlsx"
order_df = pd.read_excel(input_file, sheet_name="tb_polist", dtype={config.columns.GITEM: str}, parse_dates=[config.columns.DUE_DATE])
gitem_sitem_df = pd.read_excel(input_file, sheet_name="tb_itemspec", dtype={config.columns.GITEM: str})
linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
operation_df = pd.read_excel(input_file, sheet_name="tb_itemproc", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
yield_df = pd.read_excel(input_file, sheet_name="tb_productionyield", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
chemical_df = pd.read_excel(input_file, sheet_name="tb_chemical", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
operation_delay_df = pd.read_excel(input_file, sheet_name="tb_changetime")
width_change_df = pd.read_excel(input_file, sheet_name="tb_changewidth")
aging_gitem = pd.read_excel(input_file, sheet_name="tb_agingtime_gitem", dtype={config.columns.GITEM: str})
aging_gbn = pd.read_excel(input_file, sheet_name="tb_agingtime_gbn")
print("  [OK] 입력 데이터 로딩 완료")

# 2. Validation & Preprocessing
from src.validation import preprocess_production_data
base_date = datetime(config.constants.BASE_YEAR, 8, 29)
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

with SuppressOutput():
    processed = preprocess_production_data(
        order_df=order_df,
        linespeed_df=linespeed_df,
        operation_df=operation_df,
        yield_df=yield_df,
        chemical_df=chemical_df,
        operation_delay_df=operation_delay_df,
        width_change_df=width_change_df,
        gitem_sitem_df=gitem_sitem_df,
        aging_gitem_df=aging_gitem,
        aging_gbn_df=aging_gbn,
        global_machine_limit_df=global_machine_limit_raw,
        linespeed_period=config.constants.LINESPEED_PERIOD,
        yield_period=config.constants.YIELD_PERIOD,
        validate=False,
        save_output=False
    )
print("  [OK] Validation & Preprocessing 완료")

# 3. 주문 시퀀스 생성
from src.order_sequencing import generate_order_sequences
scenario_file = "data/input/시나리오_공정제약조건.xlsx"
local_machine_limit = pd.read_excel(scenario_file, sheet_name='machine_limit')
machine_allocate = pd.read_excel(scenario_file, sheet_name='machine_allocate')

with SuppressOutput():
    seq, linespeed, unable, unable_order, unable_details = generate_order_sequences(
        processed['order_data'],
        processed['operation_sequence'],
        processed['operation_types'],
        local_machine_limit,
        processed['global_machine_limit'],
        machine_allocate,
        processed['linespeed'],
        processed['chemical_data']
    )
print("  [OK] 주문 시퀀스 생성 완료")

# 4. 수율 예측
from src.yield_management import yield_prediction
seq_yield = yield_prediction(processed['yield_data'], seq.copy())
print("  [OK] 수율 예측 완료")

# 5. DAG 생성
from src.dag_management import create_complete_dag_system
from src.utils.machine_mapper import MachineMapper

machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(machine_master_file)
machine_mapper = MachineMapper(machine_master_info_df)

with SuppressOutput():
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
        seq_yield, linespeed, machine_mapper, processed['aging_data']
    )
print("  [OK] DAG 생성 완료")

print("\n준비 완료! 테스트 6-7 시작합니다.\n")

# ============================================================================
# 테스트 6: Dispatch Rule 생성 (10회 반복)
# ============================================================================
print(f"\n[테스트 6] Dispatch Rule 생성 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.scheduler.dispatch_rules import create_dispatch_rule

all_dispatches = []
all_dag_dfs_updated = []

for i in range(NUM_ITERATIONS):
    # DAG는 매번 deep copy 필요 (내부에서 수정되므로)
    dag_df_copy = dag_df.copy()
    seq_yield_copy = seq_yield.copy()

    with SuppressOutput():
        dispatch, dag_df_updated = create_dispatch_rule(dag_df_copy, seq_yield_copy)
    all_dispatches.append(dispatch)
    all_dag_dfs_updated.append(dag_df_updated)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

dispatch_hashes = [hash_object(d) for d in all_dispatches]
is_consistent = check_consistency(dispatch_hashes, "dispatch_rule")

if not is_consistent:
    print("\n[WARN] DISPATCH RULE이 다릅니다!")
    print("첫 3개 실행 결과 비교 (첫 10개 항목):")
    for i in range(min(3, NUM_ITERATIONS)):
        print(f"  Run {i+1}: {all_dispatches[i][:10]}")

    # 첫 번째와 다른 결과 비교
    for i in range(1, NUM_ITERATIONS):
        if dispatch_hashes[0] != dispatch_hashes[i]:
            print(f"\nRun 1 vs Run {i+1} 차이 분석:")
            # 차이나는 첫 인덱스 찾기
            for j, (d1, d2) in enumerate(zip(all_dispatches[0], all_dispatches[i])):
                if d1 != d2:
                    print(f"  첫 차이 발생 인덱스: {j}")
                    print(f"    Run 1  : {d1}")
                    print(f"    Run {i+1}: {d2}")
                    break
            break  # 첫 번째 차이만 보여줌
else:
    print("[OK] Dispatch Rule은 결정적입니다!")

# ============================================================================
# 테스트 7: 스케줄링 실행 (10회 반복)
# ============================================================================
print(f"\n[테스트 7] 스케줄링 실행 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.scheduler import run_scheduler_pipeline

machine_rest = pd.read_excel(scenario_file, sheet_name='machine_rest')

all_results = []
all_schedulers = []

for i in range(NUM_ITERATIONS):
    # 모든 객체 deep copy
    from copy import deepcopy

    dag_df_copy = dag_df.copy()
    opnode_dict_copy = deepcopy(opnode_dict)
    seq_yield_copy = seq_yield.copy()
    width_change_copy = processed['width_change'].copy()
    operation_delay_copy = processed['operation_delay'].copy()

    with SuppressOutput():
        # manager는 재생성 필요 (DAGNode 객체들 때문에)
        from src.dag_management import create_complete_dag_system
        dag_df_new, opnode_dict_new, manager_new, machine_dict_new, merged_df_new = create_complete_dag_system(
            seq_yield_copy, linespeed.copy(), machine_mapper, processed['aging_data'].copy()
        )

        result, scheduler = run_scheduler_pipeline(
            dag_df=dag_df_new,
            opnode_dict=opnode_dict_new,
            manager=manager_new,
            machine_dict=machine_dict_new,
            sequence_seperated_order=seq_yield_copy,
            width_change_df=width_change_copy,
            operation_delay_df=operation_delay_copy,
            machine_mapper=machine_mapper,
            machine_rest=machine_rest.copy(),
            base_date=base_date,
            window_days=config.constants.WINDOW_DAYS
        )
    all_results.append(result)
    all_schedulers.append(scheduler)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

result_hashes = [hash_dataframe(r) for r in all_results]
is_consistent = check_consistency(result_hashes, "scheduling_result")

if not is_consistent:
    print("\n[WARN] 스케줄링 결과가 다릅니다!")
    # 첫 번째와 다른 결과 비교
    for i in range(1, NUM_ITERATIONS):
        if result_hashes[0] != result_hashes[i]:
            print(f"\nRun 1 vs Run {i+1} 차이 분석:")

            # 컬럼별 차이 확인
            for col in all_results[0].columns:
                if col in all_results[i].columns:
                    diff_mask = all_results[0][col] != all_results[i][col]
                    if diff_mask.any():
                        print(f"\n  차이 발견 컬럼: {col}")
                        print(f"    차이나는 행 수: {diff_mask.sum()}")
                        # 첫 5개 차이만 출력
                        diff_rows = all_results[0][diff_mask].head(5)
                        print(f"    Run 1 샘플: {list(diff_rows[col].values)}")
                        diff_rows_2 = all_results[i][diff_mask].head(5)
                        print(f"    Run {i+1} 샘플: {list(diff_rows_2[col].values)}")
            break  # 첫 번째 차이만 보여줌
else:
    print("[OK] 스케줄링 결과는 결정적입니다!")

# ============================================================================
# 요약
# ============================================================================
print("\n" + "=" * 80)
print("테스트 요약")
print("=" * 80)
print(f"테스트 6 (Dispatch Rule): {NUM_ITERATIONS}회 반복 테스트")
print(f"테스트 7 (스케줄링 실행): {NUM_ITERATIONS}회 반복 테스트")
print("\n비결정성이 발견되었다면 위의 차이 분석을 확인하세요!")
print("=" * 80)
