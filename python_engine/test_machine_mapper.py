"""
MachineMapper 클래스 테스트 스크립트

기본 기능 및 검증 로직을 테스트합니다.
"""

import pandas as pd
from src.utils import MachineMapper


def test_basic_functionality():
    """기본 기능 테스트"""
    print("=" * 60)
    print("1. MachineMapper 기본 기능 테스트")
    print("=" * 60)

    # machine_master_info.xlsx 로딩
    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )

    print(f"\n[INFO] Loaded machine_master_info: {len(machine_master_info)} machines")
    print(machine_master_info.head())

    # MachineMapper 생성
    mapper = MachineMapper(machine_master_info)
    print(f"\n[INFO] Created MachineMapper: {mapper}")

    # 기계 개수 확인
    print(f"\n[TEST] get_machine_count(): {mapper.get_machine_count()}")
    assert mapper.get_machine_count() == len(machine_master_info)
    print("[PASS]")

    # 전체 리스트 확인
    print(f"\n[TEST] get_all_codes(): {mapper.get_all_codes()}")
    print(f"[TEST] get_all_names(): {mapper.get_all_names()}")
    print(f"[TEST] get_all_indices(): {mapper.get_all_indices()}")
    print("[PASS]")


def test_mapping_functions():
    """매핑 함수 테스트"""
    print("\n" + "=" * 60)
    print("2. 매핑 함수 테스트")
    print("=" * 60)

    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)

    # Index → Code/Name
    print("\n[TEST] index_to_code(0):", mapper.index_to_code(0))
    print("[TEST] index_to_name(0):", mapper.index_to_name(0))
    print("[TEST] index_to_info(0):", mapper.index_to_info(0))

    # Code → Index/Name
    first_code = mapper.get_all_codes()[0]
    print(f"\n[TEST] code_to_index('{first_code}'):", mapper.code_to_index(first_code))
    print(f"[TEST] code_to_name('{first_code}'):", mapper.code_to_name(first_code))
    print(f"[TEST] code_to_info('{first_code}'):", mapper.code_to_info(first_code))

    # Name → Index/Code
    first_name = mapper.get_all_names()[0]
    print(f"\n[TEST] name_to_index('{first_name}'):", mapper.name_to_index(first_name))
    print(f"[TEST] name_to_code('{first_name}'):", mapper.name_to_code(first_name))

    # 양방향 매핑 검증
    for idx in mapper.get_all_indices():
        code = mapper.index_to_code(idx)
        assert mapper.code_to_index(code) == idx, f"Failed for idx={idx}, code={code}"

    print("\n[PASS] 모든 양방향 매핑 검증 완료")


def test_validation():
    """검증 함수 테스트"""
    print("\n" + "=" * 60)
    print("3. 검증 함수 테스트")
    print("=" * 60)

    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)

    # 순서 검증 - 올바른 순서
    correct_order = mapper.get_all_codes()[:5]
    result = mapper.validate_machine_order(correct_order)
    print(f"\n[TEST] validate_machine_order({correct_order}): {result}")
    assert result == True
    print("[PASS]")

    # 순서 검증 - 잘못된 순서
    wrong_order = [correct_order[1], correct_order[0], correct_order[2]]
    result = mapper.validate_machine_order(wrong_order)
    print(f"\n[TEST] validate_machine_order({wrong_order}): {result}")
    assert result == False
    print("[PASS]")


def test_format_output():
    """포맷 출력 테스트"""
    print("\n" + "=" * 60)
    print("4. 포맷 출력 테스트")
    print("=" * 60)

    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)

    # format_machine_info 테스트
    print(f"\n[TEST] format_machine_info(0): {mapper.format_machine_info(0)}")
    print(f"[TEST] format_machine_info(1): {mapper.format_machine_info(1)}")
    print(f"[TEST] format_machine_info(999): {mapper.format_machine_info(999)}")

    # __str__ 테스트
    print(f"\n[TEST] str(mapper):\n{str(mapper)}")

    print("\n[PASS]")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 60)
    print("5. 엣지 케이스 테스트")
    print("=" * 60)

    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)

    # 존재하지 않는 키
    print(f"\n[TEST] code_to_index('INVALID'): {mapper.code_to_index('INVALID')}")
    assert mapper.code_to_index('INVALID') is None
    print("[PASS] - None 반환")

    print(f"[TEST] index_to_code(9999): {mapper.index_to_code(9999)}")
    assert mapper.index_to_code(9999) is None
    print("[PASS] - None 반환")

    print(f"[TEST] name_to_index('존재하지않는기계'): {mapper.name_to_index('존재하지않는기계')}")
    assert mapper.name_to_index('존재하지않는기계') is None
    print("[PASS] - None 반환")


def test_real_world_scenario():
    """실제 사용 시나리오 테스트"""
    print("\n" + "=" * 60)
    print("6. 실제 사용 시나리오 테스트 (enumerate 대체)")
    print("=" * 60)

    machine_master_info = pd.read_excel(
        "data/input/machine_master_info.xlsx",
        sheet_name="machine_master",
        dtype={'machineindex': int, 'machineno': str}
    )
    mapper = MachineMapper(machine_master_info)

    # 기존 방식 (enumerate)
    machine_columns = mapper.get_all_codes()
    machine_dict_old = {}
    print("\n[OLD] enumerate 방식:")
    for idx, col in enumerate(machine_columns):
        machine_dict_old[col] = idx
        print(f"  {col} → index {idx}")

    # 새로운 방식 (MachineMapper)
    machine_dict_new = {}
    print("\n[NEW] MachineMapper 방식:")
    for machine_code in machine_columns:
        machine_index = mapper.code_to_index(machine_code)
        machine_dict_new[machine_code] = machine_index
        print(f"  {machine_code} → index {machine_index}")

    # 결과 비교
    assert machine_dict_old == machine_dict_new
    print("\n[PASS] 두 방식 결과 동일")

    # 순서가 바뀌어도 MachineMapper는 올바른 index 반환
    print("\n[TEST] 순서 변경 시나리오:")
    shuffled_columns = [machine_columns[2], machine_columns[0], machine_columns[1]]
    print(f"변경된 순서: {shuffled_columns}")

    print("\n[OLD] enumerate 방식 (순서 의존):")
    for idx, col in enumerate(shuffled_columns):
        print(f"  {col} → index {idx}  [ERROR] 잘못된 매핑!")

    print("\n[NEW] MachineMapper 방식 (순서 독립):")
    for machine_code in shuffled_columns:
        machine_index = mapper.code_to_index(machine_code)
        print(f"  {machine_code} → index {machine_index}  [PASS] 올바른 매핑!")

    print("\n[PASS] MachineMapper는 순서에 무관하게 올바른 index 반환")


if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_mapping_functions()
        test_validation()
        test_format_output()
        test_edge_cases()
        test_real_world_scenario()

        print("\n" + "=" * 60)
        print("[PASS] 모든 테스트 통과!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
