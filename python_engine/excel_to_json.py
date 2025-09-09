"""
Excel 파일을 JSON으로 변환하는 유틸리티
"""
import pandas as pd
import json
import os
from pathlib import Path
from config import config

def convert_excel_to_json():
    """모든 Excel 파일을 JSON으로 변환"""
    
    # JSON 저장할 디렉토리 생성
    json_dir = Path(config.files.JSON_DIR)
    json_dir.mkdir(exist_ok=True)
    
    print("Excel 파일을 JSON으로 변환 중...")
    
    # 1. 품목별 라인스피드 및 공정 순서 파일 변환
    print("1. 품목별 라인스피드 및 공정 순서 변환 중...")
    excel_data_1 = pd.read_excel(config.files.ITEM_LINESPEED_SEQUENCE, sheet_name=None)
    
    # 각 시트를 개별 JSON 파일로 저장
    excel_data_1[config.sheets.ITEM_LINESPEED].to_json(
        json_dir / "md_step2_linespeed.json", 
        orient='records', 
        force_ascii=False, 
        indent=2
    )
    
    excel_data_1[config.sheets.OPERATION_SEQUENCE].to_json(
        json_dir / "md_step3_operation_sequence.json",
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    excel_data_1[config.sheets.MACHINE_MASTER_INFO].to_json(
        json_dir / "md_step4_machine_master_info.json",
        orient='records', 
        force_ascii=False,
        indent=2
    )
    
    excel_data_1[config.sheets.YIELD_DATA].to_json(
        json_dir / "md_step3_yield_data.json",
        orient='records',
        force_ascii=False, 
        indent=2
    )
    
    excel_data_1[config.sheets.GITEM_OPERATION].to_json(
        json_dir / "md_step3_gitem_operation.json",
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    # 2. 공정 재분류 내역 및 교체 시간 파일 변환
    print("2. 공정 재분류 내역 및 교체 시간 변환 중...")
    excel_data_2 = pd.read_excel(config.files.OPERATION_RECLASSIFICATION, sheet_name=None)
    
    excel_data_2[config.sheets.OPERATION_TYPES].to_json(
        json_dir / "md_step2_operation_types.json",
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    excel_data_2[config.sheets.OPERATION_DELAY].to_json(
        json_dir / "md_step5 operation_delay.json", 
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    excel_data_2[config.sheets.WIDTH_CHANGE].to_json(
        json_dir / "md_step5_width_change.json",
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    # 3. 불가능한 공정 입력값 파일 변환
    print("3. 불가능한 공정 입력값 변환 중...")
    excel_data_3 = pd.read_excel(config.files.IMPOSSIBLE_OPERATION, sheet_name=None)
    
    excel_data_3[config.sheets.MACHINE_REST].to_json(
        json_dir / "user_step5_machine_rest.json",
        orient='records',
        force_ascii=False,
        indent=2,
        date_format='iso'  # 날짜를 ISO 형식으로 저장
    )
    
    excel_data_3[config.sheets.MACHINE_ALLOCATE].to_json(
        json_dir / "user_step2_machine_allocate.json",
        orient='records', 
        force_ascii=False,
        indent=2
    )
    
    excel_data_3[config.sheets.MACHINE_LIMIT].to_json(
        json_dir / "user_step2_machine_limit.json",
        orient='records',
        force_ascii=False,
        indent=2
    )
    
    # 4. 주문 데이터 변환
    print("4. 주문 데이터 변환 중...")
    order_data = pd.read_excel(config.files.ORDER_DATA)
    order_data.to_json(
        json_dir / "md_step2_order_data.json",
        orient='records',
        force_ascii=False,
        indent=2,
        date_format='iso'  # 날짜를 ISO 형식으로 저장
    )
    
    print(f"변환 완료! JSON 파일들이 {json_dir}에 저장되었습니다.")
    
    # 변환된 파일 목록 출력
    print("\n생성된 JSON 파일들:")
    for json_file in json_dir.glob("*.json"):
        print(f"  - {json_file.name}")

if __name__ == "__main__":
    convert_excel_to_json()