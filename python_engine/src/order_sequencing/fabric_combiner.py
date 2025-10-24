import pandas as pd
from config import config


class FabricRuleHandler:
    """원단 조합 규칙 처리 클래스 (전체 구현)"""
    
    def __init__(self):
        self.handlers = {
            0: self._handle_type0,
            1: self._handle_type1,
            2: self._handle_type2,
            3: self._handle_type3,
            4: self._handle_type4
        }
    
    @staticmethod
    def classify_width(width: int) -> int:
        """원단 너비 기반 조합분류 계산"""
        if width == 1524:
            return 0
        if width in {1016, 508}:
            return 1
        if width in {609, 914}:
            return 2
        if width == 762:
            return 3
        return 4

    def _handle_type0(self, sub_df: pd.DataFrame) -> dict:
        """1524mm 단일 원단 처리 (조합분류 0)"""
        return {
            'fabric_width': 1500,
            'production_length': sub_df[config.columns.PRODUCTION_LENGTH].sum()
        }

    def _handle_type1(self, sub_df: pd.DataFrame) -> dict:
        """508mm + 1016mm 조합 처리 (조합분류 1)
        1. 508mm만 존재하는 경우: 
        
        """
        # 필수 원단 존재 여부 확인
        has_508 = 508 in sub_df[config.columns.WIDTH].values
        has_1016 = 1016 in sub_df[config.columns.WIDTH].values
        
        # 예외 처리
        if not has_508 and not has_1016:
            raise ValueError("조합분류 1 규칙에 필요한 원단(508/1016mm)이 없습니다")
        
        # 단독 처리 케이스
        if not has_508:
            return self._handle_1016_only(sub_df)
        if not has_1016:
            return self._handle_508_only(sub_df)
        
        # 조합 처리
        len_508 = sub_df.loc[sub_df[config.columns.WIDTH] == 508, config.columns.PRODUCTION_LENGTH].sum()
        len_1016 = sub_df.loc[sub_df[config.columns.WIDTH] == 1016, config.columns.PRODUCTION_LENGTH].sum()
        
        if len_508 > len_1016:
            return {'fabric_width': 1500, 'production_length': (len_508 - len_1016) // 3 + len_1016} 
        elif len_508 < len_1016:
            return {'fabric_width': 1000, 'production_length': len_1016 + (len_508 // 2)} # 1016의 길이가 더 큰 경우 
        return {'fabric_width': 1500, 'production_length': len_1016} # 둘의 길이가 같은 경우

    def _handle_508_only(self, sub_df: pd.DataFrame) -> dict:
        """508mm 단독 처리 (3:1 비율 적용)"""
        total_len = sub_df[config.columns.PRODUCTION_LENGTH].sum()
        return {
            'fabric_width': 1500,
            'production_length': total_len // 3  # 정수 나눗셈
        }

    def _handle_1016_only(self, sub_df: pd.DataFrame) -> dict:
        """1016mm 단독 처리"""
        return {
            'fabric_width': 1000,
            'production_length': sub_df[config.columns.PRODUCTION_LENGTH].sum()
        }

    def _handle_type2(self, sub_df: pd.DataFrame) -> dict:
        """609mm + 914mm 조합 처리
            둘 중 하나만 존재하거나 둘의 길이가 안 맞는 경우 더 긴 것을 기준으로 수행.
        """
        # 필수 원단 존재 여부 확인
        has_609 = 609 in sub_df[config.columns.WIDTH].values
        has_914 = 914 in sub_df[config.columns.WIDTH].values

        # 예외 처리
        if not has_609 and not has_914:
            raise ValueError("조합분류 2 규칙에 필요한 원단(609/914mm)이 없습니다")
        
        # 단독 처리 케이스
        if not has_914: # 914 없고 609만 있는 경우
            print("원단 길이에 맞는 914mm의 주문이 없어서 609mm 단독처리")
            return {
                'fabric_width': 1500,
                'production_length': sub_df.loc[sub_df[config.columns.WIDTH] == 609, config.columns.PRODUCTION_LENGTH].sum()
            }
        if not has_609: # 609 없고 914만 있는 경우
            print("원단 길이에 맞는 609mm의 주문이 없어서 914mm 단독처리")
            return {
                'fabric_width': 1500,
                'production_length': sub_df.loc[sub_df[config.columns.WIDTH] == 914, config.columns.PRODUCTION_LENGTH].sum()
            }

        # 원단이 둘 다 존재하는 경우
        # 둘 중 더 긴 것 기준으로
        return {
            'fabric_width': 1500,
            'production_length': max(sub_df.loc[sub_df[config.columns.WIDTH] == 609, config.columns.PRODUCTION_LENGTH].sum(), 
                                     sub_df.loc[sub_df[config.columns.WIDTH] == 914, config.columns.PRODUCTION_LENGTH].sum())
        }

    def _handle_type3(self, sub_df: pd.DataFrame) -> dict:
        """762mm 원단 처리 (조합분류 3)"""
        return {
            'fabric_width': 1500,
            'production_length': sub_df[config.columns.PRODUCTION_LENGTH].sum() / 2
        }

    def _handle_type4(self, sub_df: pd.DataFrame) -> dict:
        """1300mm 원단 처리 (조합분류 4)"""
        return {
            'fabric_width': 1300,
            'production_length': sub_df[config.columns.PRODUCTION_LENGTH].sum()
        }

    def get_handler(self, combination_type: int):
        """조합 타입에 따른 핸들러 반환"""
        return self.handlers.get(combination_type)



class FabricCombiner:
    """
    입력받은 조합기준(groupby_cols)에 맞는 경우 FabricRuleHandler에 따라 폭조합 실행.  

    param: groupby_cols : list
        groupby 기준 컬럼명 리스트 (default: ['GITEM', '공정', '공정순서', '조합분류'])
    param: dropna : bool
        groupby에서 NA(결측치)도 그룹으로 포함할지 여부 (pandas groupby dropna 옵션, default: False)

    Notes
    -----
    - 인풋 데이터프레임에 반드시 필요한 컬럼: 
      ['P/O NO', 'GITEM', '공정', '공정순서', '너비', '생산길이', '납기일']
    - 결과 데이터프레임의 컬럼:
      ['P/O NO', 'GITEM', '공정', '공정순서', '조합분류', '납기일', '원단너비', '생산길이']
    
    """
    def __init__(self, groupby_cols=None, dropna=False):
        self.rule_handler = FabricRuleHandler()
        self.groupby_cols = groupby_cols or [config.columns.GITEM, config.columns.OPERATION_CODE, config.columns.OPERATION_ORDER, config.columns.COMBINATION_CLASSIFICATION]
        self.dropna = dropna  # groupby에서 NA 그룹 포함 여부 

    def process(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """
        전체 처리 프로세스 실행
        1. 조합분류 컬럼 추가
        2. 그룹별로 규칙 적용 및 결과 집계
        """
        input_df = self._add_combination_type(input_df)
        return self._process_groups(input_df)

    def _add_combination_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """조합분류 컬럼 추가 (너비 기준)"""
        df = df.copy()
        df[config.columns.COMBINATION_CLASSIFICATION] = df[config.columns.WIDTH].apply(self.rule_handler.classify_width)
        return df 

    def _process_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """그룹별로 assign_fabric_quantity 실행"""
        return (
            df.groupby(self.groupby_cols, group_keys=True, as_index=False, dropna=self.dropna)
              .apply(self._assign_fabric_quantity)
              .reset_index(drop=True)
        )

    def _assign_fabric_quantity(self, sub_df: pd.DataFrame) -> pd.DataFrame:
        comb_type = sub_df[config.columns.COMBINATION_CLASSIFICATION].iloc[0]
        handler = self.rule_handler.get_handler(comb_type) 
        if not handler:
            raise ValueError(f"Invalid combination type: {comb_type}")
        result = handler(sub_df)

        # MIDDLE로 묶지 않는 공정의 경우 MIDDLE을 빈칸으로
        # if 'MIDDLE (점착제)' in sub_df.columns:
        #     middle_value = sub_df['MIDDLE (점착제)'].iloc[0]
        #     if sub_df['MIDDLE (점착제)'].nunique() > 1:
        #         middle_value = ''
        # else:
        #     middle_value = ''

        return pd.DataFrame([{
            config.columns.PO_NO: ', '.join(map(str, sub_df[config.columns.PO_NO].explode().unique())),
            config.columns.GITEM: sub_df[config.columns.GITEM].iloc[0],
            config.columns.OPERATION_CODE: sub_df[config.columns.OPERATION_CODE].iloc[0],
            config.columns.OPERATION_ORDER: sub_df[config.columns.OPERATION_ORDER].iloc[0],
            config.columns.COMBINATION_CLASSIFICATION: comb_type,
            config.columns.DUE_DATE: sub_df[config.columns.DUE_DATE].min(),
            config.columns.FABRIC_WIDTH: result['fabric_width'],
            config.columns.PRODUCTION_LENGTH: result['production_length'],
            config.columns.CHEMICAL_LIST: sub_df[config.columns.CHEMICAL_LIST].iloc[0],
            #'MIDDLE (점착제)': middle_value  # 항상 포함
        }])
