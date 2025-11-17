"""
기계 정보 매핑 관리 모듈

MachineMapper 클래스를 통해 machineindex, machineno, machinename 간의
매핑을 중앙 집중식으로 관리합니다.
"""

import pandas as pd
from typing import List, Optional
from config import config

class MachineMapper:
    """
    기계 정보 매핑 관리 클래스

    machine_master_info DataFrame을 받아서 code ↔ name 매핑 기능을 제공합니다.
    모든 매핑 딕셔너리는 초기화 시 한 번만 생성되며 캐싱됩니다.

    Attributes:
        _machine_master_info (pd.DataFrame): 원본 기계 마스터 정보
        _code_to_name (dict): machineno → machinename 매핑
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

    # === String Representation ===

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
