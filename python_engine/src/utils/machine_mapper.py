"""
기계 정보 매핑 관리 모듈

MachineMapper 클래스를 통해 machineindex, machineno, machinename 간의
매핑을 중앙 집중식으로 관리합니다.
"""

import pandas as pd
from typing import Dict, List, Optional
from config import config

class MachineMapper:
    """
    기계 정보 매핑 관리 클래스

    machine_master_info DataFrame을 받아서 code ↔ name 매핑 기능을 제공합니다.
    모든 매핑 딕셔너리는 초기화 시 한 번만 생성되며 캐싱됩니다.

    Attributes:
        _machine_master_info (pd.DataFrame): 원본 기계 마스터 정보
        _code_to_name (Dict[str, str]): machineno → machinename
        _name_to_code (Dict[str, str]): machinename → machineno
    """

    def __init__(self, machine_master_info: pd.DataFrame):
        """
        MachineMapper 초기화

        Args:
            machine_master_info (pd.DataFrame): 기계 마스터 정보
                필수 컬럼: machineno, machinename

        Raises:
            ValueError: 필수 컬럼이 없거나 데이터가 유효하지 않은 경우
        """
        # 필수 컬럼 검증
        required_columns = [config.columns.MACHINE_CODE, config.columns.MACHINE_NAME]
        missing_columns = [col for col in required_columns if col not in machine_master_info.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # 중복 검증: machineno만 체크
        if machine_master_info[config.columns.MACHINE_CODE].duplicated().any():
            duplicates = machine_master_info[machine_master_info[config.columns.MACHINE_CODE].duplicated()][config.columns.MACHINE_CODE].tolist()
            raise ValueError(f"Duplicate machineno found: {duplicates}")

        # 원본 데이터 저장 (복사본)
        self._machine_master_info = machine_master_info.copy()

        # machineno로 정렬 (일관된 순서 보장)
        self._machine_master_info = self._machine_master_info.sort_values(config.columns.MACHINE_CODE).reset_index(drop=True)

        # 매핑 딕셔너리 초기화
        self._build_mapping_dicts()

    def _build_mapping_dicts(self):
        """매핑 딕셔너리 생성 (캐싱)"""
        df = self._machine_master_info

        # Code → Name
        self._code_to_name = dict(zip(df[config.columns.MACHINE_CODE], df[config.columns.MACHINE_NAME]))

        # Name → Code
        self._name_to_code = dict(zip(df[config.columns.MACHINE_NAME], df[config.columns.MACHINE_CODE]))

    # === Public API: Code ↔ Name ===

    def code_to_name(self, code: str) -> Optional[str]:
        """
        machineno → machinename 변환

        Args:
            code (str): 기계 코드

        Returns:
            Optional[str]: 기계명 (없으면 None)

        Example:
            >>> mapper.code_to_name('C2010')
            '염색1호기_WIN'
        """
        return self._code_to_name.get(code)

    def code_to_info(self, code: str) -> Optional[Dict]:
        """
        machineno → {name} 변환

        Args:
            code (str): 기계 코드

        Returns:
            Optional[Dict]: {'name': machinename} (없으면 None)

        Example:
            >>> mapper.code_to_info('C2010')
            {'name': '염색1호기_WIN'}
        """
        name = self._code_to_name.get(code)
        if name is None:
            return None
        return {'name': name}

    # === Public API: Name → Code ===

    def name_to_code(self, name: str) -> Optional[str]:
        """
        machinename → machineno 변환

        Args:
            name (str): 기계명

        Returns:
            Optional[str]: 기계 코드 (없으면 None)

        Example:
            >>> mapper.name_to_code('염색1호기_WIN')
            'C2010'
        """
        return self._name_to_code.get(name)

    # === Public API: Bulk Operations ===

    def get_all_codes(self) -> List[str]:
        """
        모든 machineno 리스트 반환 (machineindex 순서)

        Returns:
            List[str]: 기계 코드 리스트

        Example:
            >>> mapper.get_all_codes()
            ['C2010', 'C2250', 'C2260', ...]
        """
        return self._machine_master_info[config.columns.MACHINE_CODE].tolist()

    def get_all_names(self) -> List[str]:
        """
        모든 machinename 리스트 반환 (machineno 정렬 순서)

        Returns:
            List[str]: 기계명 리스트

        Example:
            >>> mapper.get_all_names()
            ['AgNW2호기', '코팅1호기_WIN', '코팅25호기_WIN', ...]
        """
        return self._machine_master_info[config.columns.MACHINE_NAME].tolist()

    def get_machine_count(self) -> int:
        """
        기계 개수 반환

        Returns:
            int: 기계 개수

        Example:
            >>> mapper.get_machine_count()
            12
        """
        return len(self._machine_master_info)

    def get_master_info(self) -> pd.DataFrame:
        """
        원본 machine_master_info 반환 (복사본)

        Returns:
            pd.DataFrame: 기계 마스터 정보 복사본
        """
        return self._machine_master_info.copy()

    # === Validation Helpers ===

    def validate_machine_order(self, machine_columns: List[str]) -> bool:
        """
        machine_columns 순서가 machine_master_info와 일치하는지 검증

        Args:
            machine_columns (List[str]): 검증할 기계 코드 리스트

        Returns:
            bool: 순서가 일치하면 True, 아니면 False

        Example:
            >>> mapper.validate_machine_order(['C2010', 'C2250', 'C2260'])
            True
            >>> mapper.validate_machine_order(['C2250', 'C2010', 'C2260'])
            False
        """
        expected_order = self.get_all_codes()

        # machine_columns가 expected_order의 부분집합인지 확인
        # (모든 기계가 포함되지 않을 수 있으므로)
        if not all(code in expected_order for code in machine_columns):
            return False

        # 순서 확인: expected_order에서 machine_columns의 순서를 추출했을 때 동일한지
        filtered_expected = [code for code in expected_order if code in machine_columns]
        return filtered_expected == machine_columns

    def validate_linespeed_columns(self, linespeed_df: pd.DataFrame,
                                  key_columns: List[str] = None) -> tuple:
        """
        linespeed DataFrame의 기계 컬럼이 machine_master_info와 일치하는지 검증

        Args:
            linespeed_df (pd.DataFrame): 검증할 linespeed DataFrame
            key_columns (List[str]): 제외할 키 컬럼들 (기본값: [config.columns.GITEM, config.columns.OPERATION_CODE])

        Returns:
            tuple: (is_valid: bool, missing: List[str], extra: List[str])
                - is_valid: 모든 기계 코드가 일치하면 True
                - missing: machine_master_info에는 있지만 linespeed에 없는 기계
                - extra: linespeed에는 있지만 machine_master_info에 없는 기계
        """
        if key_columns is None:
            key_columns = [config.columns.GITEM, config.columns.OPERATION_CODE]

        # linespeed의 기계 컬럼 추출
        linespeed_machine_cols = [col for col in linespeed_df.columns
                                  if col not in key_columns]

        expected_codes = set(self.get_all_codes())
        actual_codes = set(linespeed_machine_cols)

        missing = list(expected_codes - actual_codes)
        extra = list(actual_codes - expected_codes)

        is_valid = len(missing) == 0 and len(extra) == 0

        return is_valid, missing, extra

    # === String Representation ===

    def format_machine_info(self, code: str) -> str:
        """
        기계 정보를 사람이 읽기 쉬운 형태로 포맷팅

        Args:
            code (str): 기계 코드

        Returns:
            str: 포맷된 기계 정보 문자열

        Example:
            >>> mapper.format_machine_info('C2010')
            '코팅1호기_WIN (C2010)'
        """
        name = self.code_to_name(code)
        if name is None:
            return f"Unknown machine [{code}]"
        return f"{name} ({code})"

    def __repr__(self) -> str:
        """
        MachineMapper 객체의 문자열 표현

        Returns:
            str: 기계 개수를 포함한 객체 표현
        """
        return f"MachineMapper(machines={self.get_machine_count()})"

    def __str__(self) -> str:
        """
        MachineMapper 객체의 상세 문자열 표현

        Returns:
            str: 모든 기계 정보를 포함한 문자열
        """
        lines = [f"MachineMapper: {self.get_machine_count()} machines"]
        for code in self.get_all_codes():
            lines.append(f"  {code} - {self.code_to_name(code)}")
        return "\n".join(lines)
