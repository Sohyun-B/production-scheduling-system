import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from collections import defaultdict

class YieldPredictor:
    def __init__(self, df):
        """
        공정 개수 동적으로 계산 안됨 지금 6공정 까지 있는 걸로 컬럼명 fixed
        df: melted_machine_linespeed: 필요 컬럼 GITEM, 공정명, 수율
        operation_sequence: 필요 컬럼 GITEM, 공정명, 공정명.1, 공정명.2, 공정명.3, 공정명.4, 공정명.5, 공정명.6 
                            predict_sequence_yield에서 입력받는 데이터
        
        """
        self.df = df
        self.model = None
        self.grid_df = None
        self.operation_sequence_yield = None
        self.gitem_yield_dict = defaultdict(float)
        
    def preprocessing(self):
        pass

    def fit_rf_by_gitem_op(self):
        """
        GITEM, 공정명 조합으로 랜덤포레스트 수율 예측모델 피팅
        grid_df에 조합별 예측수율 결과 저장
        """
        self.df['GITEM'] = self.df['GITEM'].astype(str)
        X = pd.get_dummies(self.df[['GITEM', '공정명']])
        y = self.df['수율']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = RandomForestRegressor(random_state=42)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        print('RMSE:', mean_squared_error(y_test, y_pred, squared=False))

        gitem_list = self.df['GITEM'].unique()
        process_list = self.df['공정명'].unique()

        grid_df = pd.DataFrame([(g, p) for g in gitem_list for p in process_list], columns=['GITEM', '공정명'])
        grid_X = pd.get_dummies(grid_df)

        missing_cols = set(X.columns) - set(grid_X.columns)
        for c in missing_cols:
            grid_X[c] = 0
        grid_X = grid_X[X.columns]

        grid_df['예측_수율'] = self.model.predict(grid_X)
        self.grid_df = grid_df

    def predict_sequence_yield(self, operation_sequence):
        """
        operation_sequence: 공정 시퀀스 DataFrame (ex: GITEM, 1공정, 2공정, ... 동적으로)
        예측수율 결과 및 생산비율 컬럼 추가
        """
        grid_df = self.grid_df.copy()
        operation_sequence['GITEM'] = operation_sequence['GITEM'].astype(str)
        grid_df['GITEM'] = grid_df['GITEM'].astype(str)
        grid_df['공정명'] = grid_df['공정명'].astype(str)
    
        process_cols = [col for col in operation_sequence.columns if col != 'GITEM']
        # 모든 공정 컬럼 문자열 변환
        for col in process_cols:
            operation_sequence[col] = operation_sequence[col].astype(str)
    
        # 공정별 예측 수율 merge 및 컬럼명 지정 (접두사 '예측_수율.' + 공정명)
        for col in process_cols:
            operation_sequence = pd.merge(
                operation_sequence,
                grid_df,
                left_on=['GITEM', col],
                right_on=['GITEM', '공정명'],
                how='left',
                suffixes=('', '_drop')
            )
            operation_sequence.drop(columns=['공정명'], inplace=True)
            operation_sequence.rename(columns={'예측_수율': f'예측_수율.{col}'}, inplace=True)
    
        yield_cols = [col for col in operation_sequence.columns if col.startswith('예측_수율.')]
    
        print(f"예측수율 컬럼 리스트: {yield_cols}")
    
        # 전체 예측 수율 계산 (곱)
        operation_sequence['전체_예측_수율'] = operation_sequence[yield_cols].apply(lambda row: np.nanprod(row), axis=1)
        operation_sequence['전체_예측_수율'] = operation_sequence['전체_예측_수율'].round(4)
        operation_sequence['수율_생산비율'] = 100 / operation_sequence['전체_예측_수율']
    
        self.operation_sequence_yield = operation_sequence
        self._get_gitem_yield_dict()


    def _get_gitem_yield_dict(self):
        """
        self.operation_sequence_yield 가 있어야 작동함 (predict_sequence_yield 수행 후)
        GITEM별 평균 전체_예측_수율 딕셔너리 리턴
        """
        if self.operation_sequence_yield is None:
            raise ValueError("predict_sequence_yield 메서드를 먼저 호출하여 데이터를 생성하세요.")
        
        grouped = self.operation_sequence_yield.groupby('GITEM')['수율_생산비율'].mean()
        self.gitem_yield_dict = grouped.to_dict()