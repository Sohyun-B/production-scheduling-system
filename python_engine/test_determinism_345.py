"""
비결정성 테스트 - 3, 4, 5 단계 집중 검증
테스트 1-2: 1회만 실행 (데이터 준비)
테스트 3-5: 10회 반복 검증
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

NUM_ITERATIONS = 10  # 테스트 3-5만 10회 반복

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
        print(f"  -> 발견된 고유 해시값들: {set([h[:8] for h in hash_list])}")
    return all_same

print("=" * 80)
print("비결정성 테스트 - 3, 4, 5 단계 집중 검증")
print("=" * 80)
print("테스트 1-2: 1회만 실행 (이미 검증됨)")
print(f"테스트 3-5: {NUM_ITERATIONS}회 반복")
print("=" * 80)

# ============================================================================
# 테스트 1-2: 데이터 준비 (1회만)
# ============================================================================
print("\n[준비 단계] 테스트 1-2 데이터 생성 중...")
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

# 시나리오 파일 로드
scenario_file = "data/input/시나리오_공정제약조건.xlsx"
local_machine_limit = pd.read_excel(scenario_file, sheet_name='machine_limit')
machine_allocate = pd.read_excel(scenario_file, sheet_name='machine_allocate')

print("\n준비 완료! 테스트 3-5 시작합니다.\n")

# ============================================================================
# 테스트 3: 주문 시퀀스 생성 (10회 반복)
# ============================================================================
print(f"\n[테스트 3] 주문 시퀀스 생성 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.order_sequencing import generate_order_sequences

all_sequences = []
all_linespeeds = []

for i in range(NUM_ITERATIONS):
    with SuppressOutput():
        seq, linespeed, unable, unable_order, unable_details = generate_order_sequences(
            processed['order_data'].copy(),
            processed['operation_sequence'].copy(),
            processed['operation_types'].copy(),
            local_machine_limit.copy(),
            processed['global_machine_limit'].copy(),
            machine_allocate.copy(),
            processed['linespeed'].copy(),
            processed['chemical_data'].copy()
        )
    all_sequences.append(seq)
    all_linespeeds.append(linespeed)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

seq_hashes = [hash_dataframe(seq) for seq in all_sequences]
seq_consistent = check_consistency(seq_hashes, "sequence_seperated_order")

linespeed_hashes = [hash_dataframe(ls) for ls in all_linespeeds]
linespeed_consistent = check_consistency(linespeed_hashes, "linespeed")

if not seq_consistent:
    print("\n[WARN] sequence_seperated_order가 다릅니다!")
    print("첫 3개 실행 결과 비교 (shape):")
    for i in range(min(3, NUM_ITERATIONS)):
        print(f"  Run {i+1}: shape={all_sequences[i].shape}")

    # 차이나는 행 찾기
    for i in range(1, NUM_ITERATIONS):
        if seq_hashes[0] != seq_hashes[i]:
            print(f"\nRun 1 vs Run {i+1} 차이 분석:")
            # 컬럼별 차이 확인
            for col in all_sequences[0].columns:
                if col in all_sequences[i].columns:
                    try:
                        diff_mask = all_sequences[0][col] != all_sequences[i][col]
                        if diff_mask.any():
                            print(f"  차이 발견 컬럼: {col} (차이나는 행 수: {diff_mask.sum()})")
                    except:
                        pass
            break

if not linespeed_consistent:
    print("\n[WARN] linespeed가 다릅니다!")

# ============================================================================
# 테스트 4: 수율 예측 (10회 반복)
# ============================================================================
print(f"\n[테스트 4] 수율 예측 결정성 검증 ({NUM_ITERATIONS}회)")
print("-" * 80)

from src.yield_management import yield_prediction

all_yield_sequences = []

for i in range(NUM_ITERATIONS):
    with SuppressOutput():
        seq_yield = yield_prediction(processed['yield_data'].copy(), all_sequences[i].copy())
    all_yield_sequences.append(seq_yield)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

yield_hashes = [hash_dataframe(seq) for seq in all_yield_sequences]
yield_consistent = check_consistency(yield_hashes, "yield_predicted_sequence")

if not yield_consistent:
    print("\n[WARN] yield_predicted_sequence가 다릅니다!")
    print("첫 3개 실행 결과 비교 (shape):")
    for i in range(min(3, NUM_ITERATIONS)):
        print(f"  Run {i+1}: shape={all_yield_sequences[i].shape}")

    # 차이나는 컬럼 찾기
    for i in range(1, NUM_ITERATIONS):
        if yield_hashes[0] != yield_hashes[i]:
            print(f"\nRun 1 vs Run {i+1} 차이 분석:")
            for col in all_yield_sequences[0].columns:
                if col in all_yield_sequences[i].columns:
                    try:
                        diff_mask = all_yield_sequences[0][col] != all_yield_sequences[i][col]
                        if diff_mask.any():
                            print(f"  차이 발견 컬럼: {col} (차이나는 행 수: {diff_mask.sum()})")
                            # 샘플 값 출력
                            diff_rows_1 = all_yield_sequences[0][diff_mask][col].head(3)
                            diff_rows_2 = all_yield_sequences[i][diff_mask][col].head(3)
                            print(f"    Run 1 샘플: {list(diff_rows_1.values)}")
                            print(f"    Run {i+1} 샘플: {list(diff_rows_2.values)}")
                    except:
                        pass
            break

# ============================================================================
# 테스트 5: DAG 생성 (10회 반복)
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
all_machine_dicts = []

for i in range(NUM_ITERATIONS):
    with SuppressOutput():
        dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
            all_yield_sequences[i].copy(),
            all_linespeeds[i].copy(),
            machine_mapper,
            processed['aging_data'].copy()
        )
    all_dag_dfs.append(dag_df)
    all_opnode_dicts.append(opnode_dict)
    all_machine_dicts.append(machine_dict)
    print(f"  Iteration {i+1}/{NUM_ITERATIONS} 완료", end='\r')

print()  # 줄바꿈

dag_hashes = [hash_dataframe(df) for df in all_dag_dfs]
dag_consistent = check_consistency(dag_hashes, "dag_df")

opnode_hashes = [hash_object(opd) for opd in all_opnode_dicts]
opnode_consistent = check_consistency(opnode_hashes, "opnode_dict")

machine_dict_hashes = [hash_object(md) for md in all_machine_dicts]
machine_dict_consistent = check_consistency(machine_dict_hashes, "machine_dict")

if not dag_consistent:
    print("\n[WARN] dag_df가 다릅니다!")
    print("첫 3개 실행 결과 비교 (shape):")
    for i in range(min(3, NUM_ITERATIONS)):
        print(f"  Run {i+1}: shape={all_dag_dfs[i].shape}")

if not opnode_consistent:
    print("\n[WARN] opnode_dict가 다릅니다!")
    print("첫 3개 실행 결과 비교 (keys 개수):")
    for i in range(min(3, NUM_ITERATIONS)):
        print(f"  Run {i+1}: keys={len(all_opnode_dicts[i])}")

if not machine_dict_consistent:
    print("\n[WARN] machine_dict가 다릅니다!")

# ============================================================================
# 요약
# ============================================================================
print("\n" + "=" * 80)
print("테스트 요약")
print("=" * 80)
print(f"테스트 3 (주문 시퀀스): {NUM_ITERATIONS}회 반복")
print(f"  - sequence_seperated_order: {'[OK]' if seq_consistent else '[DIFF]'}")
print(f"  - linespeed: {'[OK]' if linespeed_consistent else '[DIFF]'}")
print(f"\n테스트 4 (수율 예측): {NUM_ITERATIONS}회 반복")
print(f"  - yield_predicted_sequence: {'[OK]' if yield_consistent else '[DIFF]'}")
print(f"\n테스트 5 (DAG 생성): {NUM_ITERATIONS}회 반복")
print(f"  - dag_df: {'[OK]' if dag_consistent else '[DIFF]'}")
print(f"  - opnode_dict: {'[OK]' if opnode_consistent else '[DIFF]'}")
print(f"  - machine_dict: {'[OK]' if machine_dict_consistent else '[DIFF]'}")

all_consistent = (seq_consistent and linespeed_consistent and yield_consistent and
                  dag_consistent and opnode_consistent and machine_dict_consistent)

print("\n" + "=" * 80)
if all_consistent:
    print("[결론] 테스트 3-5 모두 결정적입니다!")
else:
    print("[결론] 일부 단계에서 비결정성이 발견되었습니다.")
    print("위의 차이 분석을 확인하세요!")
print("=" * 80)
