"""
비결정성 테스트 스크립트 (10회 반복)
각 단계별로 결정성을 검증하여 어디서 차이가 발생하는지 찾습니다.
각 단계마다 10회 실행하여 모든 결과가 동일한지 확인합니다.
"""

import sys
import hashlib
import pickle
from datetime import datetime
import pandas as pd
import numpy as np
from config import config

NUM_ITERATIONS = 10  # 반복 횟수

# 데이터 로딩 함수들
def load_input_data():
    """입력 데이터 로드"""
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

    return {
        'order_df': order_df,
        'gitem_sitem_df': gitem_sitem_df,
        'linespeed_df': linespeed_df,
        'operation_df': operation_df,
        'yield_df': yield_df,
        'chemical_df': chemical_df,
        'operation_delay_df': operation_delay_df,
        'width_change_df': width_change_df,
        'aging_gitem': aging_gitem,
        'aging_gbn': aging_gbn
    }

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
    print(f"{name:30s}: {status} (unique hashes: {unique_hashes}/{NUM_ITERATIONS})")
    if not all_same:
        print(f"  → 발견된 고유 해시값들: {set([h[:8] for h in hash_list])}")
    return all_same

print("=" * 80)
print(f"비결정성 단위 테스트 시작 ({NUM_ITERATIONS}회 반복)")
print("=" * 80)

# ============================================================================
# 테스트 1: 입력 데이터 로딩
# ============================================================================
print(f"\n[테스트 1] 입력 데이터 로딩 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

all_data = [load_input_data() for _ in range(NUM_ITERATIONS)]

# 각 데이터프레임별로 해시 비교
for key in all_data[0].keys():
    hash_list = [hash_dataframe(data[key]) for data in all_data]
    check_consistency(hash_list, key)

# ============================================================================
# 테스트 2: Validation & Preprocessing
# ============================================================================
print(f"\n[테스트 2] Validation & Preprocessing 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.validation import preprocess_production_data

base_date = datetime(config.constants.BASE_YEAR, 8, 29)
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

all_processed = []
for i in range(NUM_ITERATIONS):
    input_data = load_input_data()
    processed = preprocess_production_data(
        order_df=input_data['order_df'],
        linespeed_df=input_data['linespeed_df'],
        operation_df=input_data['operation_df'],
        yield_df=input_data['yield_df'],
        chemical_df=input_data['chemical_df'],
        operation_delay_df=input_data['operation_delay_df'],
        width_change_df=input_data['width_change_df'],
        gitem_sitem_df=input_data['gitem_sitem_df'],
        aging_gitem_df=input_data['aging_gitem'],
        aging_gbn_df=input_data['aging_gbn'],
        global_machine_limit_df=global_machine_limit_raw,
        linespeed_period=config.constants.LINESPEED_PERIOD,
        yield_period=config.constants.YIELD_PERIOD,
        validate=False,
        save_output=False
    )
    all_processed.append(processed)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

for key in all_processed[0].keys():
    if isinstance(all_processed[0][key], pd.DataFrame):
        hash_list = [hash_dataframe(p[key]) for p in all_processed]
        check_consistency(hash_list, key)

# ============================================================================
# 테스트 3: 주문 시퀀스 생성
# ============================================================================
print(f"\n[테스트 3] 주문 시퀀스 생성 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.order_sequencing import generate_order_sequences

scenario_file = "data/input/시나리오_공정제약조건.xlsx"
local_machine_limit = pd.read_excel(scenario_file, sheet_name='machine_limit')
machine_allocate = pd.read_excel(scenario_file, sheet_name='machine_allocate')

all_sequences = []
all_linespeeds = []

for i in range(NUM_ITERATIONS):
    seq, linespeed, unable, unable_order, unable_details = generate_order_sequences(
        all_processed[i]['order_data'],
        all_processed[i]['operation_sequence'],
        all_processed[i]['operation_types'],
        local_machine_limit,
        all_processed[i]['global_machine_limit'],
        machine_allocate,
        all_processed[i]['linespeed'],
        all_processed[i]['chemical_data']
    )
    all_sequences.append(seq)
    all_linespeeds.append(linespeed)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

seq_hashes = [hash_dataframe(seq) for seq in all_sequences]
check_consistency(seq_hashes, "sequence_seperated_order")

linespeed_hashes = [hash_dataframe(ls) for ls in all_linespeeds]
check_consistency(linespeed_hashes, "linespeed")

# ============================================================================
# 테스트 4: 수율 예측
# ============================================================================
print(f"\n[테스트 4] 수율 예측 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.yield_management import yield_prediction

all_yield_sequences = []

for i in range(NUM_ITERATIONS):
    seq_yield = yield_prediction(all_processed[i]['yield_data'], all_sequences[i].copy())
    all_yield_sequences.append(seq_yield)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

yield_hashes = [hash_dataframe(seq) for seq in all_yield_sequences]
check_consistency(yield_hashes, "yield_predicted_sequence")

# ============================================================================
# 테스트 5: DAG 생성
# ============================================================================
print(f"\n[테스트 5] DAG 생성 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.dag_management import create_complete_dag_system
from src.utils.machine_mapper import MachineMapper

machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(machine_master_file)
machine_mapper = MachineMapper(machine_master_info_df)

all_dag_dfs = []
all_opnode_dicts = []
all_managers = []
all_machine_dicts = []
all_merged_dfs = []

for i in range(NUM_ITERATIONS):
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
        all_yield_sequences[i], all_linespeeds[i], machine_mapper, all_processed[i]['aging_data']
    )
    all_dag_dfs.append(dag_df)
    all_opnode_dicts.append(opnode_dict)
    all_managers.append(manager)
    all_machine_dicts.append(machine_dict)
    all_merged_dfs.append(merged_df)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

dag_hashes = [hash_dataframe(df) for df in all_dag_dfs]
check_consistency(dag_hashes, "dag_df")

opnode_hashes = [hash_object(opd) for opd in all_opnode_dicts]
check_consistency(opnode_hashes, "opnode_dict")

machine_dict_hashes = [hash_object(md) for md in all_machine_dicts]
check_consistency(machine_dict_hashes, "machine_dict")

# ============================================================================
# 테스트 6: Dispatch Rule 생성
# ============================================================================
print(f"\n[테스트 6] Dispatch Rule 생성 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.scheduler.dispatch_rules import create_dispatch_rule

all_dispatches = []
all_dag_dfs_updated = []

for i in range(NUM_ITERATIONS):
    dispatch, dag_df_updated = create_dispatch_rule(all_dag_dfs[i], all_yield_sequences[i])
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

# ============================================================================
# 테스트 7: 스케줄링 실행
# ============================================================================
print(f"\n[테스트 7] 스케줄링 실행 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.scheduler import run_scheduler_pipeline

machine_rest = pd.read_excel(scenario_file, sheet_name='machine_rest')

all_results = []
all_schedulers = []

for i in range(NUM_ITERATIONS):
    # run_scheduler_pipeline은 내부에서 create_dispatch_rule을 다시 호출하므로
    # 원본 dag_df를 전달해야 함
    result, scheduler = run_scheduler_pipeline(
        dag_df=all_dag_dfs[i],  # updated가 아닌 원본 사용
        opnode_dict=all_opnode_dicts[i],
        manager=all_managers[i],
        machine_dict=all_machine_dicts[i],
        sequence_seperated_order=all_yield_sequences[i],
        width_change_df=all_processed[i]['width_change'],
        operation_delay_df=all_processed[i]['operation_delay'],
        machine_mapper=machine_mapper,
        machine_rest=machine_rest,
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
            merged = all_results[0].merge(all_results[i], on=config.columns.PROCESS_ID, how='outer', suffixes=('_1', f'_{i+1}'))
            diff_cols = [col for col in merged.columns if '_1' in col or f'_{i+1}' in col]

            for col_pair in zip([c for c in diff_cols if '_1' in c], [c for c in diff_cols if f'_{i+1}' in c]):
                col1, col2 = col_pair
                diff_rows = merged[merged[col1] != merged[col2]]
                if len(diff_rows) > 0:
                    print(f"\n  차이 발견 컬럼: {col1.replace('_1', '')}")
                    print(f"    차이나는 행 수: {len(diff_rows)}")
                    print(f"    첫 5개 차이:")
                    print(diff_rows[[config.columns.PROCESS_ID, col1, col2]].head())
            break  # 첫 번째 차이만 보여줌

# ============================================================================
# 요약
# ============================================================================
print("\n" + "=" * 80)
print("테스트 요약")
print("=" * 80)
print("✓ = 결정적 (모든 실행에서 동일한 결과)")
print("✗ = 비결정적 (실행마다 다른 결과)")
print(f"\n총 {NUM_ITERATIONS}회 반복 실행하여 일관성을 검증했습니다.")
print("\n비결정성이 처음 발견된 단계를 확인하세요!")
