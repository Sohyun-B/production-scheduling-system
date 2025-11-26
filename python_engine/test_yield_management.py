"""
yield_management 모듈 테스트 스크립트

실제 데이터를 사용하여 yield_management 모듈의 기능을 테스트합니다.
"""

import pandas as pd
from config import config
from src.yield_management.yield_calc import yield_prediction


def test_yield_management():
    """yield_management 모듈의 전체 기능을 테스트합니다."""

    print("=" * 80)
    print("yield_management 모듈 테스트 시작")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1] 데이터 로딩...")

    # yield_data 로드
    yield_data = pd.read_csv('yield_data.csv', dtype={config.columns.GITEM: str})
    print(f"yield_data 로드 완료: {len(yield_data)} rows")
    print(f"컬럼: {yield_data.columns.tolist()}")
    print(f"샘플 데이터:\n{yield_data.head()}\n")

    # sequence_seperated_order 로드 (수율 적용 전 데이터 사용)
    try:
        # 수율 적용 전 원본 데이터 로드
        sequence_order = pd.read_csv('수율이전_sequence_seperated_order.csv', dtype={config.columns.GITEM: str})
        print(f"sequence_seperated_order 로드 완료: {len(sequence_order)} rows")
        print(f"컬럼: {sequence_order.columns.tolist()}")
        print(f"샘플 데이터:\n{sequence_order.head()}\n")
    except FileNotFoundError:
        print("sequence_seperated_order 파일을 찾을 수 없습니다. 더미 데이터로 테스트합니다.")
        # 더미 데이터 생성
        sequence_order = pd.DataFrame({
            config.columns.PROCESS_ID: ['proc_1', 'proc_2', 'proc_3'],
            config.columns.GITEM: ['25003', '25003', '25004'],
            config.columns.OPERATION_CODE: ['24000', '24100', '24000'],
            config.columns.PRODUCTION_LENGTH: [1000, 1500, 2000],
            config.columns.DUE_DATE: pd.to_datetime(['2025-01-01', '2025-01-05', '2025-01-03'])
        })
        print(f"더미 sequence_seperated_order 생성 완료: {len(sequence_order)} rows\n")

    # work_in_progress 로드
    try:
        wip = pd.read_excel('data/input/재공품.xlsx', dtype={config.columns.GITEM: str})
        print(f"재공품 데이터 로드 완료: {len(wip)} rows")
        print(f"컬럼: {wip.columns.tolist()}")
        print(f"샘플 데이터:\n{wip.head()}\n")
    except FileNotFoundError:
        print("재공품 파일을 찾을 수 없습니다. 재공품 없이 테스트합니다.\n")
        wip = None

    # 2. yield_prediction 실행
    print("\n[2] yield_prediction 실행...")
    result = yield_prediction(
        yield_data=yield_data,
        sequence_seperated_order=sequence_order,
        work_in_progress=wip
    )

    # 3. 결과 확인
    print("\n[3] 결과 확인")
    print("-" * 80)

    adjusted_orders = result['adjusted_orders']
    wip_usage_log = result['wip_usage_log']
    unused_wip = result['unused_wip']

    print(f"\n조정된 주문 데이터: {len(adjusted_orders)} rows")
    print(f"컬럼: {adjusted_orders.columns.tolist()}")
    if not adjusted_orders.empty:
        print(f"샘플 데이터:\n{adjusted_orders.head()}")
        print(f"\n3가지 길이 컬럼 비교:")
        if config.columns.ORIGINAL_PRODUCTION_LENGTH in adjusted_orders.columns:
            comparison = adjusted_orders[[
                config.columns.PROCESS_ID,
                config.columns.GITEM,
                config.columns.OPERATION_CODE,
                config.columns.ORIGINAL_PRODUCTION_LENGTH,
                config.columns.PRODUCTION_LENGTH_WO_WIP,
                config.columns.PRODUCTION_LENGTH
            ]].head(10)
            print(comparison)
            print(f"\n설명:")
            print(f"  - original_production_length: 수율/재공품 미고려 원본 길이")
            print(f"  - production_length_wo_wip: 수율만 고려한 길이 (재공품 미고려)")
            print(f"  - production_length: 수율 + 재공품 모두 고려한 최종 생산 길이")

    print(f"\n재공품 사용 이력: {len(wip_usage_log)} rows")
    if not wip_usage_log.empty:
        print(f"컬럼: {wip_usage_log.columns.tolist()}")
        print(f"샘플 데이터:\n{wip_usage_log.head()}")
    else:
        print("재공품 사용 이력이 없습니다.")

    print(f"\n미사용 재공품: {len(unused_wip)} rows")
    if not unused_wip.empty:
        print(f"컬럼: {unused_wip.columns.tolist()}")
        print(f"샘플 데이터:\n{unused_wip.head()}")
    else:
        print("미사용 재공품이 없습니다.")

    # 4. 결과 저장 - 하나의 엑셀 파일에 여러 시트로 저장
    print("\n[4] 결과 저장...")
    output_file = 'test_yield_management_result.xlsx'

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 조정된 주문 데이터
        adjusted_orders.to_excel(writer, sheet_name='조정된_주문', index=False)
        print(f"  - 시트 '조정된_주문': {len(adjusted_orders)} rows")

        # 재공품 사용 이력
        if not wip_usage_log.empty:
            wip_usage_log.to_excel(writer, sheet_name='재공품_사용_이력', index=False)
            print(f"  - 시트 '재공품_사용_이력': {len(wip_usage_log)} rows")

        # 미사용 재공품
        if not unused_wip.empty:
            unused_wip.to_excel(writer, sheet_name='미사용_재공품', index=False)
            print(f"  - 시트 '미사용_재공품': {len(unused_wip)} rows")

    print(f"\n결과 파일 저장 완료: {output_file}")

    # 불필요한 파일 삭제
    print("\n[5] 불필요한 파일 정리...")
    import os
    files_to_remove = [
        'test_adjusted_orders.csv',
        'test_wip_usage_log.csv',
        'test_unused_wip.csv',
        '수율확인1.csv',
        '수율확인2.csv'
    ]

    removed_count = 0
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            removed_count += 1
            print(f"  - 삭제: {file}")

    if removed_count == 0:
        print("  - 삭제할 파일 없음")
    else:
        print(f"  - 총 {removed_count}개 파일 삭제")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

    return result


if __name__ == "__main__":
    test_yield_management()
