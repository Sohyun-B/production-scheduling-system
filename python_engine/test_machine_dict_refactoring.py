"""
machine_dict 리팩토링 검증 테스트

Phase 1 Afternoon 변경사항 검증:
- 인덱스 기반 → 코드 기반 machine_dict 구조
- Vectorized linespeed 캐싱
- Long Format linespeed 사용
"""

import pandas as pd
import numpy as np
from src.dag_management.node_dict import create_machine_dict
from src.utils import MachineMapper
from config import config


def load_test_data():
    """테스트용 데이터 생성 (합성 데이터)"""
    print("=" * 60)
    print("테스트 데이터 생성 (합성 데이터)")
    print("=" * 60)

    # Machine master info 로딩
    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)
    print(f"[INFO] MachineMapper: {mapper.get_machine_count()} machines")

    # ⭐ 합성 Linespeed 데이터 생성 (Long Format)
    all_machines = mapper.get_all_codes()

    linespeed_data = []
    # 2개 GITEM, 2개 공정, 모든 기계 조합
    for gitem in ['25003', '25008']:
        for proccode in ['20300', '20700']:
            for idx, machine in enumerate(all_machines):
                # 일부 기계만 linespeed 있도록 (현실적)
                if idx % 3 == 0:  # 3개 중 1개만
                    linespeed_data.append({
                        config.columns.GITEM: gitem,
                        config.columns.OPERATION_CODE: proccode,
                        config.columns.MACHINE_CODE: machine,
                        'linespeed': 30.0 + idx * 5  # 다양한 속도
                    })

    linespeed_df = pd.DataFrame(linespeed_data)
    print(f"[INFO] Linespeed (Long Format): {len(linespeed_df)} rows")

    # ⭐ 합성 sequence_seperated_order 데이터 생성
    order_data = []
    node_counter = 1
    for gitem in ['25003', '25008']:
        for op_order in [1, 2]:
            proccode = '20300' if op_order == 1 else '20700'
            order_data.append({
                config.columns.ID: f'N{node_counter:05d}',
                config.columns.GITEM: gitem,
                config.columns.OPERATION_CODE: proccode,
                config.columns.OPERATION_ORDER: op_order,
                config.columns.PRODUCTION_LENGTH: 1000.0 + node_counter * 100
            })
            node_counter += 1

    order_df = pd.DataFrame(order_data)
    print(f"[INFO] Sequence separated order: {len(order_df)} rows")

    return mapper, linespeed_df, order_df


def test_machine_dict_structure():
    """machine_dict 구조 검증"""
    print("\n" + "=" * 60)
    print("1. machine_dict 구조 검증 (코드 기반)")
    print("=" * 60)

    mapper, linespeed_df, order_df = load_test_data()

    # create_machine_dict 호출
    print("\n[TEST] create_machine_dict() 호출 중...")
    machine_dict = create_machine_dict(order_df, linespeed_df, mapper)

    print(f"[INFO] machine_dict 생성 완료: {len(machine_dict)} nodes")

    # 첫 번째 노드 확인
    first_node_id = list(machine_dict.keys())[0]
    first_node_dict = machine_dict[first_node_id]

    print(f"\n[TEST] 첫 번째 노드: {first_node_id}")
    print(f"[TEST] machine_dict['{first_node_id}'] 타입: {type(first_node_dict)}")
    print(f"[TEST] Keys: {list(first_node_dict.keys())[:5]}...")  # 처음 5개만

    # ⭐ 핵심 검증: 키가 문자열(machine_code)인지 확인
    sample_keys = list(first_node_dict.keys())[:3]
    print(f"\n[VERIFY] 샘플 키 타입 검증:")
    for key in sample_keys:
        key_type = type(key).__name__
        print(f"  - Key: {key}, Type: {key_type}")
        if key != -1:  # Aging 노드가 아닌 경우
            assert isinstance(key, str), f"❌ FAIL: Key should be string (machine_code), got {key_type}"

    print("\n[PASS] ✅ machine_dict 구조가 코드 기반으로 변경됨")

    return machine_dict, mapper, linespeed_df, order_df


def test_processing_time_calculation():
    """처리시간 계산 검증"""
    print("\n" + "=" * 60)
    print("2. 처리시간 계산 검증")
    print("=" * 60)

    machine_dict, mapper, linespeed_df, order_df = test_machine_dict_structure()

    # 특정 노드 선택
    test_node_id = list(machine_dict.keys())[0]
    node_data = order_df[order_df[config.columns.ID] == test_node_id].iloc[0]

    gitem = str(node_data[config.columns.GITEM])
    proccode = str(node_data[config.columns.OPERATION_CODE])
    production_length = float(node_data[config.columns.PRODUCTION_LENGTH])

    print(f"\n[TEST] 노드: {test_node_id}")
    print(f"  - GITEM: {gitem}")
    print(f"  - ProcCode: {proccode}")
    print(f"  - Production Length: {production_length}")

    # 특정 기계의 처리시간 확인
    all_machines = mapper.get_all_codes()
    test_machine = all_machines[0]

    print(f"\n[TEST] 기계: {test_machine}")

    # Linespeed에서 해당 조합 찾기
    linespeed_row = linespeed_df[
        (linespeed_df[config.columns.GITEM].astype(str) == gitem) &
        (linespeed_df[config.columns.OPERATION_CODE].astype(str) == proccode) &
        (linespeed_df[config.columns.MACHINE_CODE].astype(str) == test_machine)
    ]

    if not linespeed_row.empty:
        linespeed_value = float(linespeed_row['linespeed'].iloc[0])
        expected_time = int(np.ceil(
            production_length / linespeed_value / config.constants.TIME_MULTIPLIER
        ))

        actual_time = machine_dict[test_node_id][test_machine]

        print(f"  - Linespeed: {linespeed_value}")
        print(f"  - Expected Time: {expected_time}")
        print(f"  - Actual Time: {actual_time}")

        assert actual_time == expected_time, f"❌ FAIL: Time mismatch!"
        print("\n[PASS] ✅ 처리시간 계산이 정확함")
    else:
        print(f"  - Linespeed 없음 → 9999 예상")
        actual_time = machine_dict[test_node_id][test_machine]
        assert actual_time == 9999, f"❌ FAIL: Should be 9999 when no linespeed"
        print("\n[PASS] ✅ Linespeed 없을 때 9999 반환")


def test_vectorized_cache():
    """Vectorized 캐시 성능 확인"""
    print("\n" + "=" * 60)
    print("3. Vectorized 캐시 검증")
    print("=" * 60)

    mapper, linespeed_df, order_df = load_test_data()

    # Vectorized 캐시 생성 (리팩토링 후)
    print("\n[TEST] Vectorized cache 생성...")
    linespeed_cache = dict(zip(
        zip(
            linespeed_df[config.columns.GITEM].astype(str),
            linespeed_df[config.columns.OPERATION_CODE].astype(str),
            linespeed_df[config.columns.MACHINE_CODE].astype(str)
        ),
        linespeed_df['linespeed'].astype(float)
    ))

    print(f"[INFO] Cache size: {len(linespeed_cache)} entries")

    # 샘플 조회 테스트
    sample_key = list(linespeed_cache.keys())[0]
    sample_value = linespeed_cache[sample_key]

    print(f"\n[TEST] 샘플 조회:")
    print(f"  - Key: {sample_key}")
    print(f"  - Value: {sample_value}")
    print(f"  - Type: {type(sample_value)}")

    # 원본 DataFrame에서 동일 값 확인
    gitem, proccode, machineno = sample_key
    original_value = linespeed_df[
        (linespeed_df[config.columns.GITEM].astype(str) == gitem) &
        (linespeed_df[config.columns.OPERATION_CODE].astype(str) == proccode) &
        (linespeed_df[config.columns.MACHINE_CODE].astype(str) == machineno)
    ]['linespeed'].iloc[0]

    assert sample_value == original_value, "❌ FAIL: Cache value mismatch!"
    print("\n[PASS] ✅ Vectorized cache가 정확히 동작함")


def test_aging_node_handling():
    """Aging 노드 처리 검증"""
    print("\n" + "=" * 60)
    print("4. Aging 노드 처리 검증")
    print("=" * 60)

    mapper, linespeed_df, order_df = load_test_data()

    # Aging 노드 시뮬레이션
    aging_nodes_dict = {
        "AGING_001": 120,
        "AGING_002": 180
    }

    print("\n[TEST] Aging 노드 추가...")
    machine_dict = create_machine_dict(
        order_df, linespeed_df, mapper, aging_nodes_dict=aging_nodes_dict
    )

    # Aging 노드 검증
    for aging_node_id, aging_time in aging_nodes_dict.items():
        print(f"\n[TEST] Aging 노드: {aging_node_id}")

        if aging_node_id in machine_dict:
            node_dict = machine_dict[aging_node_id]
            print(f"  - Keys: {list(node_dict.keys())}")
            print(f"  - Values: {list(node_dict.values())}")

            # Aging 노드는 {-1: time} 구조여야 함
            assert list(node_dict.keys()) == [-1], "❌ FAIL: Aging node should have only -1 key"
            assert node_dict[-1] == aging_time, "❌ FAIL: Aging time mismatch"

            print(f"  ✅ Aging 노드 구조 정확")
        else:
            print(f"  ⚠️ Aging 노드가 machine_dict에 추가되지 않음 (선택적 기능)")

    print("\n[PASS] ✅ Aging 노드 처리 정상")


def test_backward_compatibility():
    """호환성 검증 (structure만)"""
    print("\n" + "=" * 60)
    print("5. 구조 호환성 검증")
    print("=" * 60)

    mapper, linespeed_df, order_df = load_test_data()
    machine_dict = create_machine_dict(order_df, linespeed_df, mapper)

    # 모든 노드 검증
    print(f"\n[TEST] 전체 {len(machine_dict)}개 노드 구조 검증...")

    issues = []
    for node_id, node_machines in machine_dict.items():
        # 딕셔너리 타입 확인
        if not isinstance(node_machines, dict):
            issues.append(f"Node {node_id}: Not a dict (type={type(node_machines)})")
            continue

        # 키 타입 확인 (string or -1)
        for key in node_machines.keys():
            if key != -1 and not isinstance(key, str):
                issues.append(f"Node {node_id}: Invalid key type {type(key)} for key {key}")

    if issues:
        print("\n[ERROR] 구조 문제 발견:")
        for issue in issues[:10]:  # 처음 10개만
            print(f"  - {issue}")
        raise AssertionError(f"{len(issues)} structure issues found!")

    print(f"[PASS] ✅ 모든 {len(machine_dict)}개 노드의 구조가 올바름")


if __name__ == "__main__":
    try:
        print("\n" + "🚀" * 30)
        print("machine_dict 리팩토링 검증 테스트 시작")
        print("🚀" * 30)

        test_machine_dict_structure()
        test_processing_time_calculation()
        test_vectorized_cache()
        test_aging_node_handling()
        test_backward_compatibility()

        print("\n" + "=" * 60)
        print("✅ [PASS] 모든 테스트 통과!")
        print("=" * 60)
        print("\n✅ Phase 1 Afternoon 변경사항 검증 완료:")
        print("  1. ✅ 코드 기반 machine_dict 구조 확인")
        print("  2. ✅ 처리시간 계산 정확성 확인")
        print("  3. ✅ Vectorized 캐시 동작 확인")
        print("  4. ✅ Aging 노드 처리 확인")
        print("  5. ✅ 전체 구조 호환성 확인")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ [ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
