"""
machine_dict 문제 원인 분석 스크립트
"""
import pandas as pd
from config import config

# 문제의 노드들
problem_nodes = [
    "32267_20906_1300_None_4_M11",
    "32265_20500_1300_WRF065_4_M11",
    "32263_20500_1300_WRF065_4_M11"
]

# GITEM과 공정코드 추출
problem_gitem_proccode = [
    ("32267", "20906"),
    ("32265", "20500"),
    ("32263", "20500"),
    ("32267", "20500"),  # 32267의 20500 공정도 확인
]

print("="*80)
print("문제 노드 분석")
print("="*80)

# 1. Excel 파일 로딩
input_file = "data/input/생산계획 입력정보.xlsx"

print("\n[1단계] 원본 데이터 로딩...")
linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
gitem_sitem_df = pd.read_excel(input_file, sheet_name="tb_itemspec", dtype={config.columns.GITEM: str})
global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

print(f"  - linespeed_df: {len(linespeed_df)}행")
print(f"  - gitem_sitem_df: {len(gitem_sitem_df)}행")
print(f"  - global_machine_limit_raw: {len(global_machine_limit_raw)}행")

# 2. 문제 GITEM의 제품군 정보 확인
print("\n[2단계] 문제 GITEM의 제품군 정보 확인...")
for gitem, proccode in problem_gitem_proccode:
    gitem_info = gitem_sitem_df[gitem_sitem_df[config.columns.GITEM] == gitem]
    if not gitem_info.empty:
        grp2_name = gitem_info.iloc[0].get('grp2_name', 'N/A')
        print(f"  - GITEM {gitem}: grp2_name = {grp2_name}")
    else:
        print(f"  - GITEM {gitem}: 정보 없음")

# 3. tb_commonconstraint에서 C2270 관련 제약조건 확인
print("\n[3단계] tb_commonconstraint에서 C2270 관련 제약조건 확인...")
c2270_constraints = global_machine_limit_raw[global_machine_limit_raw['machineno'] == 'C2270']
print(f"  - C2270 관련 제약조건: {len(c2270_constraints)}건")
print(c2270_constraints[['grp2_name', 'machineno', 'procgbn']].to_string())

# 4. linespeed 데이터프레임 컬럼 확인
print("\n[4단계] linespeed 원본 데이터 컬럼 확인...")
print(f"  컬럼 목록: {linespeed_df.columns.tolist()}")

# 4-1. linespeed 데이터에서 문제 GITEM + C2270 조합 확인
print("\n[4-1단계] linespeed 원본 데이터에서 문제 GITEM + C2270 조합 확인...")

# 실제 컬럼명 확인 후 사용
if 'linespeed' in linespeed_df.columns:
    linespeed_col = 'linespeed'
elif 'l11' in linespeed_df.columns:
    linespeed_col = 'l11'  # 6개월 기준
else:
    linespeed_col = linespeed_df.columns[-1]  # 마지막 컬럼 사용

print(f"  사용할 linespeed 컬럼: {linespeed_col}")

for gitem, proccode in problem_gitem_proccode:
    # C2270에 대한 linespeed 확인
    linespeed_c2270 = linespeed_df[
        (linespeed_df[config.columns.GITEM] == gitem) &
        (linespeed_df[config.columns.OPERATION_CODE] == proccode) &
        (linespeed_df[config.columns.MACHINE_CODE] == 'C2270')
    ]

    if not linespeed_c2270.empty:
        print(f"  ✅ GITEM {gitem}, 공정 {proccode}, C2270: linespeed 존재")
        print(f"     값: {linespeed_c2270[linespeed_col].values}")
        print(f"     전체 행: {linespeed_c2270.to_dict('records')}")
    else:
        print(f"  ❌ GITEM {gitem}, 공정 {proccode}, C2270: linespeed 없음")

        # 다른 기계는 있는지 확인
        linespeed_all_machines = linespeed_df[
            (linespeed_df[config.columns.GITEM] == gitem) &
            (linespeed_df[config.columns.OPERATION_CODE] == proccode)
        ]
        if not linespeed_all_machines.empty:
            machines = linespeed_all_machines[config.columns.MACHINE_CODE].unique()
            print(f"     다른 기계: {machines}")
        else:
            print(f"     해당 GITEM+공정 조합이 linespeed에 전혀 없음")

# 5. validation 모듈 실행 후 전처리된 데이터 확인
print("\n[5단계] 전처리 후 데이터 확인...")
from src.validation import preprocess_production_data

order_df = pd.read_excel(input_file, sheet_name="tb_polist", dtype={config.columns.GITEM: str}, parse_dates=[config.columns.DUE_DATE])
operation_df = pd.read_excel(input_file, sheet_name="tb_itemproc", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
yield_df = pd.read_excel(input_file, sheet_name="tb_productionyield", dtype={config.columns.GITEM: str})
chemical_df = pd.read_excel(input_file, sheet_name="tb_chemical", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
operation_delay_df = pd.read_excel(input_file, sheet_name="tb_changetime")
width_change_df = pd.read_excel(input_file, sheet_name="tb_changewidth")
aging_gitem = pd.read_excel(input_file, sheet_name="tb_agingtime_gitem", dtype={config.columns.GITEM: str})
aging_gbn = pd.read_excel(input_file, sheet_name="tb_agingtime_gbn")

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
    validate=False,  # 빠른 테스트를 위해 validation 스킵
    save_output=False
)

linespeed_processed = processed_data['linespeed']

print(f"\n전처리 후 linespeed: {len(linespeed_processed)}행")

# 전처리 후에도 C2270 데이터가 있는지 확인
for gitem, proccode in problem_gitem_proccode:
    linespeed_c2270_processed = linespeed_processed[
        (linespeed_processed[config.columns.GITEM] == gitem) &
        (linespeed_processed[config.columns.OPERATION_CODE] == proccode) &
        (linespeed_processed[config.columns.MACHINE_CODE] == 'C2270')
    ]

    if not linespeed_c2270_processed.empty:
        print(f"  ✅ 전처리 후 GITEM {gitem}, 공정 {proccode}, C2270: 존재")
        print(f"     linespeed 값: {linespeed_c2270_processed['linespeed'].values}")
    else:
        print(f"  ❌ 전처리 후 GITEM {gitem}, 공정 {proccode}, C2270: 제거됨")

# 6. global_machine_limit 전처리 결과 확인
print("\n[6단계] global_machine_limit 전처리 결과 확인...")
global_machine_limit = processed_data['global_machine_limit']

if global_machine_limit is not None:
    print(f"global_machine_limit: {len(global_machine_limit)}행")

    # 문제 GITEM과 관련된 제약조건 확인
    for gitem, proccode in problem_gitem_proccode:
        constraints = global_machine_limit[
            (global_machine_limit[config.columns.GITEM] == gitem) &
            (global_machine_limit[config.columns.OPERATION_CODE] == proccode) &
            (global_machine_limit[config.columns.MACHINE_CODE] == 'C2270')
        ]

        if not constraints.empty:
            print(f"  ❌ GITEM {gitem}, 공정 {proccode}, C2270: 제약조건 존재 (제외됨)")
            print(f"     제약조건: {constraints.to_dict('records')}")
        else:
            print(f"  ✅ GITEM {gitem}, 공정 {proccode}, C2270: 제약조건 없음")
else:
    print("global_machine_limit이 None입니다.")

print("\n" + "="*80)
print("분석 완료")
print("="*80)
