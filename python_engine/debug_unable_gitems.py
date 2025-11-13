"""
생산 불가능한 GITEM 분석 스크립트
"""
import pandas as pd
from config import config
from src.validation import preprocess_production_data
from src.order_sequencing.operation_machine_limit import operation_machine_limit

# Excel 파일 로딩
input_file = "data/input/생산계획 입력정보.xlsx"

order_df = pd.read_excel(input_file, sheet_name="tb_polist", dtype={config.columns.GITEM: str}, parse_dates=[config.columns.DUE_DATE])
linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
operation_df = pd.read_excel(input_file, sheet_name="tb_itemproc", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
yield_df = pd.read_excel(input_file, sheet_name="tb_productionyield", dtype={config.columns.GITEM: str})
chemical_df = pd.read_excel(input_file, sheet_name="tb_chemical", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
operation_delay_df = pd.read_excel(input_file, sheet_name="tb_changetime")
width_change_df = pd.read_excel(input_file, sheet_name="tb_changewidth")
gitem_sitem_df = pd.read_excel(input_file, sheet_name="tb_itemspec", dtype={config.columns.GITEM: str})
aging_gitem = pd.read_excel(input_file, sheet_name="tb_agingtime_gitem", dtype={config.columns.GITEM: str})
aging_gbn = pd.read_excel(input_file, sheet_name="tb_agingtime_gbn")
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

print("="*80)
print("생산 불가능 GITEM 분석")
print("="*80)

# 전처리 실행
print("\n[1단계] 전처리 실행...")
processed_data = preprocess_production_data(
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
    linespeed_period='6_months',
    yield_period='6_months',
    validate=False,
    save_output=False
)

linespeed = processed_data['linespeed']
global_machine_limit = processed_data['global_machine_limit']

print(f"\n전처리 후 linespeed: {len(linespeed)}행")
print(f"global_machine_limit: {len(global_machine_limit)}행")

# 전처리 직후 상태 확인
print("\n[2단계] 전처리 직후 linespeed 상태 확인...")
order_gitems = order_df[config.columns.GITEM].unique()
print(f"주문에 있는 GITEM 수: {len(order_gitems)}개")

# 각 주문 GITEM이 linespeed에 있는지 확인
linespeed_gitems = linespeed[config.columns.GITEM].unique()
print(f"linespeed에 있는 GITEM 수: {len(linespeed_gitems)}개")

missing_gitems = set(order_gitems) - set(linespeed_gitems)
print(f"주문에는 있지만 linespeed에 없는 GITEM: {len(missing_gitems)}개")
if missing_gitems:
    print(f"  예시: {list(missing_gitems)[:5]}")

# Global 제약조건 적용 전후 비교
print("\n[3단계] Global 제약조건 샘플 확인...")
print(f"\nGlobal 제약조건 샘플 (처음 10개):")
print(global_machine_limit.head(10))

# Local limit 로딩
local_machine_limit = pd.read_excel("data/input/시나리오_공정제약조건.xlsx", sheet_name="machine_limit")
print(f"\nLocal 제약조건: {len(local_machine_limit)}행")

# operation_machine_limit 실행
print("\n[4단계] operation_machine_limit 실행...")
linespeed_filtered, unable_gitems, unable_details = operation_machine_limit(
    linespeed, local_machine_limit, global_machine_limit
)

print(f"\n필터링 후 linespeed: {len(linespeed_filtered)}행")
print(f"생산 불가능한 GITEM: {len(unable_gitems)}개")

if unable_gitems:
    print(f"\n샘플 unable_gitems (처음 10개): {unable_gitems[:10]}")
    print(f"\n샘플 unable_details (처음 5개):")
    for detail in unable_details[:5]:
        print(f"  - GITEM {detail['gitem']}, 공정 {detail['operation']}")

# 특정 GITEM 상세 분석
print("\n[5단계] 샘플 unable GITEM 상세 분석...")
if unable_gitems:
    sample_gitem = unable_gitems[0]

    print(f"\nGITEM {sample_gitem} 분석:")

    # 원본 linespeed에서 확인
    original_data = linespeed[linespeed[config.columns.GITEM] == sample_gitem]
    print(f"  전처리 후 원본 linespeed: {len(original_data)}개 행")
    if len(original_data) > 0:
        print(f"  유효한 linespeed (>0): {len(original_data[original_data['linespeed'] > 0])}개")
        print(f"\n  샘플 데이터:")
        print(original_data[[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE, 'linespeed']].head())

    # Global 제약조건 확인
    constraints = global_machine_limit[global_machine_limit[config.columns.GITEM] == sample_gitem]
    print(f"\n  Global 제약조건: {len(constraints)}개")
    if len(constraints) > 0:
        print(constraints[[config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.MACHINE_CODE]].head())

    # 필터링 후 데이터
    filtered_data = linespeed_filtered[linespeed_filtered[config.columns.GITEM] == sample_gitem]
    print(f"\n  필터링 후: {len(filtered_data)}개 행")
    if len(filtered_data) > 0:
        print(f"  유효한 linespeed (>0): {len(filtered_data[filtered_data['linespeed'] > 0])}개")

print("\n" + "="*80)
