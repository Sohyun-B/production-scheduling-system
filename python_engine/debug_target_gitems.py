"""
문제였던 32265, 32267, 32263 GITEM의 C2270 처리 확인
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
print("문제 GITEM (32265, 32267, 32263) C2270 처리 확인")
print("="*80)

# 전처리 실행
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

# Local limit 로딩
local_machine_limit = pd.read_excel("data/input/시나리오_공정제약조건.xlsx", sheet_name="machine_limit")

# operation_machine_limit 실행
linespeed_filtered, unable_gitems, unable_details = operation_machine_limit(
    linespeed, local_machine_limit, global_machine_limit
)

# 문제 GITEM 확인
target_gitems = ['32265', '32267', '32263']
target_proccode = '20500'

print(f"\n[결과 확인] {target_proccode} 공정에서 C2270 사용 가능 여부")
print("-" * 80)

for gitem in target_gitems:
    # 필터링 후 데이터 확인
    gitem_data = linespeed_filtered[
        (linespeed_filtered[config.columns.GITEM] == gitem) &
        (linespeed_filtered[config.columns.OPERATION_CODE] == target_proccode)
    ]

    print(f"\n✅ GITEM {gitem}:")

    if len(gitem_data) == 0:
        print(f"  ❌ 해당 공정 데이터 없음")
        continue

    # C2270 데이터 확인
    c2270_data = gitem_data[gitem_data[config.columns.MACHINE_CODE] == 'C2270']

    if len(c2270_data) == 0:
        print(f"  ❌ C2270 데이터 제거됨")
        print(f"  사용 가능한 기계:")
        for _, row in gitem_data.iterrows():
            if row['linespeed'] > 0:
                print(f"    - {row[config.columns.MACHINE_CODE]}: linespeed={row['linespeed']}")
    else:
        linespeed_value = c2270_data.iloc[0]['linespeed']
        if linespeed_value > 0:
            print(f"  ✅ C2270 사용 가능! (linespeed={linespeed_value})")
        else:
            print(f"  ⚠️ C2270 데이터는 있지만 linespeed=0")

    # 생산 불가능 목록 확인
    if gitem in unable_gitems:
        print(f"  ❌ 생산 불가능 목록에 포함됨")
        # 어떤 공정에서 문제인지 확인
        gitem_unable_details = [d for d in unable_details if d['gitem'] == gitem]
        for detail in gitem_unable_details:
            print(f"     - 공정 {detail['operation']}: 사용 가능한 기계 없음")

print("\n" + "="*80)
print("결론:")
print("="*80)

all_ok = True
for gitem in target_gitems:
    gitem_data = linespeed_filtered[
        (linespeed_filtered[config.columns.GITEM] == gitem) &
        (linespeed_filtered[config.columns.OPERATION_CODE] == target_proccode) &
        (linespeed_filtered[config.columns.MACHINE_CODE] == 'C2270') &
        (linespeed_filtered['linespeed'] > 0)
    ]

    if len(gitem_data) > 0:
        print(f"✅ GITEM {gitem}: {target_proccode} 공정에서 C2270 사용 가능")
    else:
        print(f"❌ GITEM {gitem}: {target_proccode} 공정에서 C2270 사용 불가")
        all_ok = False

if all_ok:
    print("\n🎉 모든 문제 GITEM이 C2270에서 정상 처리 가능합니다!")
else:
    print("\n⚠️ 일부 GITEM에 여전히 문제가 있습니다.")

print("="*80)
