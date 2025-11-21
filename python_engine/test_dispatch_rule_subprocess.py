"""
dispatch_rule의 비결정성 테스트 (subprocess 버전)
각 프로세스마다 hash seed가 다른 상황에서 dispatch_rule 결과가 달라지는지 확인
"""

import subprocess
import sys
import pickle
import os

# 단일 실행용 스크립트
SINGLE_RUN_SCRIPT = """
import sys
import pickle
from datetime import datetime
import pandas as pd
from config import config
from src.validation import preprocess_production_data
from src.order_sequencing import generate_order_sequences
from src.yield_management import yield_prediction
from src.dag_management import create_complete_dag_system
from src.utils.machine_mapper import MachineMapper
from src.scheduler.dispatch_rules import create_dispatch_rule

# 데이터 로딩
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
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

base_date = datetime(config.constants.BASE_YEAR, 8, 29)

# Preprocessing
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

# Order sequencing
scenario_file = "data/input/시나리오_공정제약조건.xlsx"
local_machine_limit = pd.read_excel(scenario_file, sheet_name='machine_limit')
machine_allocate = pd.read_excel(scenario_file, sheet_name='machine_allocate')

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

# Yield prediction
seq_yield = yield_prediction(processed['yield_data'], seq.copy())

# DAG creation
machine_master_file = "data/input/machine_master_info.xlsx"
machine_master_info_df = pd.read_excel(machine_master_file)
machine_mapper = MachineMapper(machine_master_info_df)

dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
    seq_yield, linespeed, machine_mapper, processed['aging_data']
)

# ========== 핵심: dispatch_rule 생성 ==========
dispatch_rule, dag_df_updated = create_dispatch_rule(dag_df, seq_yield)

# 결과를 pickle로 저장
output_file = sys.argv[1] if len(sys.argv) > 1 else 'dispatch_result.pkl'
with open(output_file, 'wb') as f:
    pickle.dump(dispatch_rule, f)

print(f"Dispatch rule saved to {output_file}")
print(f"First 10 items: {dispatch_rule[:10]}")
"""

NUM_RUNS = 10

print("=" * 80)
print(f"dispatch_rule 비결정성 테스트 ({NUM_RUNS}회 subprocess 실행)")
print("=" * 80)
print()

# 단일 실행 스크립트를 임시 파일로 저장
script_file = "temp_dispatch_test.py"
with open(script_file, 'w', encoding='utf-8') as f:
    f.write(SINGLE_RUN_SCRIPT)

results = []

for i in range(NUM_RUNS):
    output_file = f'dispatch_result_{i+1}.pkl'

    print(f"[Run {i+1}/{NUM_RUNS}] 실행 중...", end='', flush=True)

    # 새로운 프로세스로 실행 (각각 다른 hash seed)
    result = subprocess.run(
        ['python', script_file, output_file],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    if result.returncode != 0:
        print(f" [ERROR]")
        print(f"stderr: {result.stderr[:300]}")
        continue

    # 결과 로드
    with open(output_file, 'rb') as f:
        dispatch_rule = pickle.load(f)

    results.append(dispatch_rule)
    print(f" 완료 (length: {len(dispatch_rule)})")

print()
print("=" * 80)
print("결과 비교")
print("=" * 80)
print()

# 첫 10개 항목 비교
print("각 실행의 첫 10개 dispatch rule:")
for i, dr in enumerate(results, 1):
    print(f"Run {i}: {dr[:10]}")

print()

# 해시 비교
import hashlib
hashes = []
for i, dr in enumerate(results, 1):
    h = hashlib.md5(pickle.dumps(dr)).hexdigest()
    hashes.append(h)
    print(f"Run {i} hash: {h[:16]}")

print()

# 일관성 체크
unique_hashes = len(set(hashes))
if unique_hashes == 1:
    print(f"[OK] 모든 {NUM_RUNS}회 실행에서 동일한 dispatch_rule 생성!")
    print("     -> dispatch_rule은 결정적입니다.")
else:
    print(f"[DIFF] {unique_hashes}개의 서로 다른 dispatch_rule 발견!")
    print(f"       -> dispatch_rule은 비결정적입니다.")

    # 그룹화
    from collections import defaultdict
    hash_groups = defaultdict(list)
    for i, h in enumerate(hashes, 1):
        hash_groups[h].append(i)

    print()
    print("동일한 결과 그룹:")
    for idx, (h, runs) in enumerate(hash_groups.items(), 1):
        print(f"  그룹 {idx} (hash: {h[:16]}): Run {runs}")

    # 첫 번째와 두 번째 비교
    if len(results) >= 2:
        print()
        print("Run 1 vs Run 2 상세 비교:")
        dr1 = results[0]
        dr2 = results[1]

        # 차이나는 첫 인덱스 찾기
        first_diff_idx = None
        for idx, (item1, item2) in enumerate(zip(dr1, dr2)):
            if item1 != item2:
                first_diff_idx = idx
                break

        if first_diff_idx is not None:
            print(f"  첫 차이 발생 인덱스: {first_diff_idx}")
            print(f"    Run 1: {dr1[first_diff_idx]}")
            print(f"    Run 2: {dr2[first_diff_idx]}")

            # 주변 항목도 출력
            start = max(0, first_diff_idx - 2)
            end = min(len(dr1), first_diff_idx + 3)
            print(f"  주변 항목 비교 (index {start}-{end}):")
            for i in range(start, end):
                marker = " <-- DIFF" if i == first_diff_idx else ""
                print(f"    [{i}] Run 1: {dr1[i]}")
                print(f"    [{i}] Run 2: {dr2[i]}{marker}")
        else:
            print("  모든 항목이 동일하지만 해시가 다름 (순서는 같음)")

print()
print("=" * 80)

# 임시 파일 정리
os.remove(script_file)
for i in range(1, NUM_RUNS + 1):
    try:
        os.remove(f'dispatch_result_{i}.pkl')
    except:
        pass

print("테스트 완료")
print("=" * 80)
