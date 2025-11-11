import pandas as pd
from itertools import product
from typing import List, Dict, Tuple, Union
from config import config


class DelayProcessor:
    def __init__(self, opnode_dict, operation_delay_df, width_change_df, machine_index_list):
        """
        V5 방식 구조 유지 + chemical 로직 추가
        
        Args:
            opnode_dict: 노드 정보 딕셔너리
            machine_index_list: 공정교체시간 존재하는기계인덱스 리스트
            operation_delay_df: 공정별 지연시간 규칙 데이터프레임
            width_change_df: 폭 변경 지연시간 규칙 데이터프레임
        """
        self.opnode_dict = opnode_dict
        self.machine_index_list = machine_index_list
        self.base_df = self._generate_base_df(operation_delay_df, width_change_df)
        self.final_df = self._apply_delay_conditions(operation_delay_df, width_change_df)
        self.delay_dict = self._dataframe_to_dict()

    def delay_calc_whole_process(self, item_id1, item_id2, machine_index):
        """
        ID로 지연시간을 구하는 메인 함수
        
        Args:
            item_id1: 이전 아이템 ID (먼저 들어갈 ID)
            item_id2: 다음 아이템 ID (나중에 들어갈 ID)  
            machine_index: 사용 기계 인덱스 (0, 2, 3만 유효)
            
        Returns:
            delay_time: 계산된 지연시간 (분 단위)
        """
        if machine_index not in self.machine_index_list:
            return 0
            
        # 기본값 딕셔너리 생성
        empty_dict = {
            "OPERATION_ORDER": 0,
            "OPERATION_CODE": "",
            "OPERATION_CLASSIFICATION": "",
            "FABRIC_WIDTH": 0,
            "CHEMICAL_LIST": (),
            "PRODUCTION_LENGTH": 0
        }
        values1 = self.opnode_dict.get(item_id1, empty_dict)
        values2 = self.opnode_dict.get(item_id2, empty_dict)
        
        input_key = self.calculate_delay(values1, values2, machine_index)
        delay_time = self.delay_dict.get(input_key, 0)
        return delay_time

    def _generate_base_df(self, operation_delay_df, width_change_df) -> pd.DataFrame:
        """
        지연 규칙 관련 컬럼으로 기본 데이터프레임 생성 (V5 방식)
        
        Returns:
            기본 조합 데이터프레임
        """
        columns = {
            'machine_index': self.machine_index_list,
            'earlier_operation_type': operation_delay_df[config.columns.EARLIER_OPERATION_TYPE].unique().tolist(),
            'later_operation_type': operation_delay_df[config.columns.LATER_OPERATION_TYPE].unique().tolist(),
            'long_to_short': [True, False],  # 장폭 -> 단폭 여부
            'short_to_long': [True, False],  # 단폭 -> 장폭 여부
            'same_type': [True, False],      # 공정 유형 동일 여부
            'same_chemical': [True, False]    # chemical 동일 여부 (추가)
        }
        return pd.DataFrame(product(*columns.values()), columns=columns.keys())

    def _apply_delay_conditions(
        self,
        operation_delay_df: pd.DataFrame,
        width_change_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        지연 조건들을 적용하여 최종 지연시간 계산 (V5 방식 + chemical 로직)
        
        Args:
            operation_delay_df: 공정 타입별 지연 규칙
            width_change_df: 기계별 폭 변경 지연 규칙
            
        Returns:
            지연시간이 계산된 최종 데이터프레임
        """
        df = self.base_df.copy()
        
        # 공정 타입별 지연시간 규칙 적용
        type_rules = operation_delay_df[[config.columns.EARLIER_OPERATION_TYPE, config.columns.LATER_OPERATION_TYPE, config.columns.TYPE_CHANGE_TIME]].copy()
        type_rules = type_rules.rename(columns={
            config.columns.EARLIER_OPERATION_TYPE: 'earlier_operation_type',
            config.columns.LATER_OPERATION_TYPE: 'later_operation_type'
        })
        
        df = df.merge(
            type_rules,
            on=['earlier_operation_type', 'later_operation_type'],
            how='left'
        )
        
        # 기계별 폭 변경 지연시간 규칙 적용
        machine_rules = width_change_df[[config.columns.MACHINE_INDEX, config.columns.LONG_TO_SHORT, config.columns.SHORT_TO_LONG]].copy()
        machine_rules = machine_rules.rename(columns={
            config.columns.MACHINE_INDEX: 'machine_index',
            config.columns.LONG_TO_SHORT: 'width_l2s_minutes',   # 컬럼명 충돌 방지
            config.columns.SHORT_TO_LONG: 'width_s2l_minutes'    # 컬럼명 충돌 방지
        })
        
        df = df.merge(
            machine_rules,
            on='machine_index',
            how='left'
        )
        
        # 지연시간 계산: 각 조건에 해당하는 지연시간 중 최대값 선택
        delay_columns = []
        
        # 1. 공정 타입 변경 지연시간 (chemical가 다를 때만 적용)
        type_delay = df[config.columns.TYPE_CHANGE_TIME].fillna(0)
        type_delay = type_delay.where(~df['same_chemical'].fillna(False), 0)  # same_chemical=True면 0
        delay_columns.append(type_delay)
        
        # 2. 장폭 -> 단폭 지연시간 (조건 만족시에만)
        l2s_delay = df['width_l2s_minutes'].fillna(0)
        l2s_delay = l2s_delay.where(df['long_to_short'].fillna(False), 0)
        delay_columns.append(l2s_delay)
        
        # 3. 단폭 -> 장폭 지연시간 (조건 만족시에만)  
        s2l_delay = df['width_s2l_minutes'].fillna(0)
        s2l_delay = s2l_delay.where(df['short_to_long'].fillna(False), 0)
        delay_columns.append(s2l_delay)
        
        # 최종 지연시간 = 모든 지연시간 중 최대값
        df['delay_time'] = pd.concat(delay_columns, axis=1).max(axis=1)
        return df

    def _dataframe_to_dict(self) -> dict:
        """데이터프레임을 딕셔너리로 변환 (V5 방식)"""
        # 실제 컬럼명 확인 후 사용
        columns = self.final_df.columns.tolist()
        
        # long_to_short와 short_to_long 컬럼명 찾기
        long_to_short_col = 'long_to_short'
        short_to_long_col = 'short_to_long'
        
        # _x, _y 접미사가 붙은 경우 처리
        for col in columns:
            if col.startswith('long_to_short'):
                long_to_short_col = col
            elif col.startswith('short_to_long'):
                short_to_long_col = col
        
        return {
            tuple(row[['machine_index', 'earlier_operation_type', 'later_operation_type', 
                      long_to_short_col, short_to_long_col, 'same_type', 'same_chemical']]): row['delay_time']
            for _, row in self.final_df.iterrows()
        }

    @staticmethod
    def calculate_delay(earlier: list, later: list, machine_idx: int) -> Tuple:
        """
        지연 키 계산 (V5 방식 + chemical 로직)

        Args:
            earlier: 이전 공정 정보 딕셔너리 (OPERATION_ORDER, OPERATION_CODE, OPERATION_CLASSIFICATION, FABRIC_WIDTH, SELECTED_CHEMICAL, PRODUCTION_LENGTH)
            later: 다음 공정 정보 딕셔너리 (OPERATION_ORDER, OPERATION_CODE, OPERATION_CLASSIFICATION, FABRIC_WIDTH, SELECTED_CHEMICAL, PRODUCTION_LENGTH)
            machine_idx: 기계 인덱스

        Returns:
            지연 계산을 위한 키 튜플
        """
        # 기본값 초기화
        long_to_short = False
        short_to_long = False
        same_type = False
        same_chemical = False

        # 공정 정보 추출
        earlier_operation_type = earlier["OPERATION_CLASSIFICATION"]
        later_operation_type = later["OPERATION_CLASSIFICATION"]
        earlier_width = earlier["FABRIC_WIDTH"]
        later_width = later["FABRIC_WIDTH"]
        earlier_chemical = earlier["SELECTED_CHEMICAL"]
        later_chemical = later["SELECTED_CHEMICAL"]

        # 1. 너비 변경 여부 확인
        if earlier_width > later_width:
            long_to_short = True
        elif earlier_width < later_width:
            short_to_long = True

        # 2. 공정 타입 동일 여부 확인
        if earlier_operation_type == later_operation_type:
            same_type = True

        # 3. chemical 동일 여부 확인 (SELECTED_CHEMICAL 기준)
        # 둘 다 None인 경우도 같은 것으로 처리
        if earlier_chemical == later_chemical:
            same_chemical = True

        return (machine_idx, earlier_operation_type, later_operation_type,
                long_to_short, short_to_long, same_type, same_chemical)