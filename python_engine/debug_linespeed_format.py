"""
linespeed 형태 확인 스크립트
"""
import pandas as pd
from config import config
from src.validation import preprocess_production_data

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
print("Linespeed 형태 분석")
print("="*80)

# 1. 전처리 실행
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

print(f"\n전처리 후 linespeed 형태:")
print(f"  - 행 수: {len(linespeed)}")
print(f"  - 컬럼: {linespeed.columns.tolist()}")
print(f"\n첫 5행:")
print(linespeed.head())

# 2. 문제 GITEM 확인
print("\n[2단계] 문제 GITEM의 linespeed 확인...")
problem_gitem = "32265"
problem_proccode = "20500"

problem_data = linespeed[
    (linespeed[config.columns.GITEM] == problem_gitem) &
    (linespeed[config.columns.OPERATION_CODE] == problem_proccode)
]

print(f"\nGITEM {problem_gitem}, 공정 {problem_proccode}:")
print(problem_data)

# 3. C2270이 있는지 확인
c2270_data = problem_data[problem_data[config.columns.MACHINE_CODE] == 'C2270']
print(f"\nC2270 데이터:")
print(c2270_data)

# 4. generate_order_sequences 호출 전에 형태 확인
print("\n[3단계] generate_order_sequences에 전달되는 linespeed 형태 확인...")
print(f"  형태: {'Long Format' if config.columns.MACHINE_CODE in linespeed.columns else 'Wide Format'}")

if config.columns.MACHINE_CODE in linespeed.columns:
    print(f"  Long Format 감지!")
    print(f"  문제: operation_machine_limit()는 Wide Format을 예상함")
else:
    print(f"  Wide Format 감지")
    print(f"  정상: operation_machine_limit()는 Wide Format을 예상함")

print("\n" + "="*80)
