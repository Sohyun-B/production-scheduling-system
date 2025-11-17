"""
주문별 지각 정보 리포트 모듈

전체 주문의 납기일, 완성시각, 지각여부, 지각시간 제공
"""

import pandas as pd
from config import config


class OrderLatenessReporter:
    """주문별 지각 정보 리포터 클래스"""

    def __init__(self, result_cleaned, original_order, base_date, sequence_seperated_order):
        """
        Args:
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과
            original_order (pd.DataFrame): 원본 주문 데이터
            base_date (datetime): 기준 날짜
            sequence_seperated_order (pd.DataFrame): 공정별 분리 주문 (ID-PO_NO 매핑용)
        """
        self.result_cleaned = result_cleaned
        self.original_order = original_order
        self.base_date = base_date
        self.sequence_seperated_order = sequence_seperated_order

    def calculate_completion_time(self):
        """
        PO별 완성시각 계산

        Returns:
            pd.DataFrame: [P/O NO, completion_datetime]
        """
        # result_cleaned에 PO_NO 추가 (id 기준 병합)
        # 주의: result_cleaned의 컬럼명은 'id' (소문자)
        result_with_po = pd.merge(
            self.result_cleaned[['id', 'node_end']],
            self.sequence_seperated_order[[config.columns.PROCESS_ID, config.columns.PO_NO]],
            left_on='id',
            right_on=config.columns.PROCESS_ID,
            how='left'
        )

        # PO별 max(node_end) 추출
        po_completion = result_with_po.groupby(config.columns.PO_NO).agg({
            'node_end': 'max'
        }).reset_index()

        # 실제 datetime으로 변환
        po_completion['completion_datetime'] = (
            self.base_date +
            pd.to_timedelta(
                po_completion['node_end'] * config.constants.TIME_MULTIPLIER,
                unit='m'
            )
        )

        return po_completion[[config.columns.PO_NO, 'completion_datetime']]

    def determine_lateness(self, completion_df):
        """
        지각 여부 및 지각시간 계산

        Args:
            completion_df (pd.DataFrame): calculate_completion_time() 결과

        Returns:
            pd.DataFrame: 지각 정보가 추가된 DataFrame
        """
        # 원본 주문과 병합
        merged = pd.merge(
            completion_df,
            self.original_order,
            on=config.columns.PO_NO,
            how='left'
        )

        # 납기일 타입 확인 및 변환
        if not pd.api.types.is_datetime64_any_dtype(merged[config.columns.DUE_DATE]):
            merged[config.columns.DUE_DATE] = pd.to_datetime(
                merged[config.columns.DUE_DATE]
            )

        # 지각 여부 판정
        merged['지각여부'] = merged.apply(
            lambda row: '지각' if row['completion_datetime'] > row[config.columns.DUE_DATE] else '준수',
            axis=1
        )

        # 지각시간 계산 (일 단위, 소수점 포함)
        merged['지각시간(일)'] = merged.apply(
            lambda row: max(
                0,
                (row['completion_datetime'] - row[config.columns.DUE_DATE]).total_seconds() / 86400
            ),
            axis=1
        ).round(2)

        return merged

    def create_lateness_table(self):
        """
        주문 지각 정보 테이블 생성

        Returns:
            pd.DataFrame: 7개 컬럼 (P/O NO, GITEM, GITEM명, 납기일, 완성시각, 지각여부, 지각시간)
        """
        # 완성시각 계산
        completion_df = self.calculate_completion_time()

        # 지각 정보 추가
        lateness_df = self.determine_lateness(completion_df)

        # 필요한 컬럼만 선택 및 재정렬
        result_columns = [
            config.columns.PO_NO,
            config.columns.GITEM,
            config.columns.GITEM_NAME,
            config.columns.DUE_DATE,
            'completion_datetime',
            '지각여부',
            '지각시간(일)'
        ]

        # 컬럼 존재 여부 확인 후 선택
        available_columns = [col for col in result_columns if col in lateness_df.columns]
        result_df = lateness_df[available_columns].copy()

        # 컬럼명 변경
        result_df = result_df.rename(columns={
            'completion_datetime': '완성시각'
        })

        # 납기일 기준 정렬
        if config.columns.DUE_DATE in result_df.columns:
            result_df = result_df.sort_values(config.columns.DUE_DATE).reset_index(drop=True)

        return result_df

    def get_lateness_summary(self):
        """
        지각 요약 통계

        Returns:
            dict: {
                'total_orders': int,
                'ontime_orders': int,
                'late_orders': int,
                'ontime_rate': float,
                'avg_lateness_days': float
            }
        """
        lateness_table = self.create_lateness_table()

        if lateness_table.empty:
            return {
                'total_orders': 0,
                'ontime_orders': 0,
                'late_orders': 0,
                'ontime_rate': 0.0,
                'avg_lateness_days': 0.0
            }

        total_orders = len(lateness_table)
        ontime_orders = (lateness_table['지각여부'] == '준수').sum()
        late_orders = (lateness_table['지각여부'] == '지각').sum()
        ontime_rate = (ontime_orders / total_orders * 100) if total_orders > 0 else 0.0

        # 지각 주문의 평균 지각일수
        late_orders_only = lateness_table[lateness_table['지각여부'] == '지각']
        avg_lateness_days = late_orders_only['지각시간(일)'].mean() if not late_orders_only.empty else 0.0

        return {
            'total_orders': total_orders,
            'ontime_orders': ontime_orders,
            'late_orders': late_orders,
            'ontime_rate': round(ontime_rate, 2),
            'avg_lateness_days': round(avg_lateness_days, 2)
        }

    def get_late_orders_only(self):
        """
        지각 주문만 필터링

        Returns:
            pd.DataFrame: 지각 주문만 포함
        """
        lateness_table = self.create_lateness_table()

        if lateness_table.empty:
            return pd.DataFrame()

        late_orders = lateness_table[lateness_table['지각여부'] == '지각'].copy()

        # 지각시간 기준 내림차순 정렬
        if not late_orders.empty and '지각시간(일)' in late_orders.columns:
            late_orders = late_orders.sort_values(
                '지각시간(일)',
                ascending=False
            ).reset_index(drop=True)

        return late_orders
