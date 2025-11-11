"""
스케줄링 성과 지표 계산 모듈

주요 지표:
- PO 제품수
- 총 생산시간 (makespan)
- 납기준수율
- 장비가동률 (전체평균)
"""

import pandas as pd
import numpy as np
from config import config


class PerformanceMetricsCalculator:
    """스케줄링 성과 지표 계산 클래스"""

    def __init__(self, result_cleaned, original_order, scheduler, base_date, sequence_seperated_order):
        """
        Args:
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과 (depth -1 제외)
            original_order (pd.DataFrame): 원본 주문 데이터
            scheduler: 스케줄러 인스턴스
            base_date (datetime): 기준 날짜
            sequence_seperated_order (pd.DataFrame): 공정별 분리 주문 (ID-PO_NO 매핑용)
        """
        self.result_cleaned = result_cleaned
        self.original_order = original_order
        self.scheduler = scheduler
        self.base_date = base_date
        self.sequence_seperated_order = sequence_seperated_order

    def calculate_po_count(self):
        """
        PO 제품수 계산

        Returns:
            int: 전체 주문 개수
        """
        po_count = len(self.original_order)
        return po_count

    def calculate_makespan(self):
        """
        총 생산시간(makespan) 계산 (시간 단위)

        Returns:
            float: makespan (시간)
        """
        # node_end의 최댓값 = makespan (단위: TIME_MULTIPLIER)
        makespan_raw = self.result_cleaned['node_end'].max()

        # 시간 단위로 변환
        makespan_hours = makespan_raw * config.constants.TIME_MULTIPLIER / 60

        return makespan_hours

    def calculate_ontime_delivery_rate(self):
        """
        납기준수율 계산 (%)

        Returns:
            float: 납기준수율 (%)
        """
        # result_cleaned에 PO_NO 추가 (id 기준 병합)
        # 주의: result_cleaned의 컬럼명은 'id' (소문자)
        result_with_po = pd.merge(
            self.result_cleaned[['id', 'node_end']],
            self.sequence_seperated_order[[config.columns.ID, config.columns.PO_NO]],
            left_on='id',
            right_on=config.columns.ID,
            how='left'
        )

        # PO별 최종 완료시각 추출
        po_completion = result_with_po.groupby(config.columns.PO_NO).agg({
            'node_end': 'max'
        }).reset_index()

        # 실제 datetime으로 변환
        po_completion['completion_datetime'] = (
            self.base_date +
            pd.to_timedelta(po_completion['node_end'] * config.constants.TIME_MULTIPLIER, unit='m')
        )

        # 원본 주문의 납기일과 병합
        po_with_duedate = pd.merge(
            po_completion,
            self.original_order[[config.columns.PO_NO, config.columns.DUE_DATE]],
            on=config.columns.PO_NO,
            how='left'
        )

        # 납기일 타입 변환 (필요시)
        if not pd.api.types.is_datetime64_any_dtype(po_with_duedate[config.columns.DUE_DATE]):
            po_with_duedate[config.columns.DUE_DATE] = pd.to_datetime(
                po_with_duedate[config.columns.DUE_DATE]
            )

        # 지각 여부 판정
        po_with_duedate['on_time'] = (
            po_with_duedate['completion_datetime'] <= po_with_duedate[config.columns.DUE_DATE]
        )

        # 납기준수율 계산
        ontime_count = po_with_duedate['on_time'].sum()
        total_count = len(po_with_duedate)

        if total_count == 0:
            return 0.0

        ontime_rate = (ontime_count / total_count) * 100

        return ontime_rate

    def calculate_avg_utilization(self):
        """
        장비가동률 전체평균 계산 (%)

        Returns:
            float: 평균 장비가동률 (%)
        """
        makespan = self.result_cleaned['node_end'].max()

        if makespan == 0:
            return 0.0

        # 각 기계의 가동시간 계산
        total_operating_time = 0
        machine_count = 0

        for machine in self.scheduler.Machines:
            if len(machine.assigned_task) == 0:
                continue

            machine_count += 1

            # 각 작업의 처리시간 합계
            operating_time = sum([
                end - start
                for start, end in zip(machine.O_start, machine.O_end)
            ])

            total_operating_time += operating_time

        if machine_count == 0:
            return 0.0

        # 평균 가동율 = (총 가동시간) / (기계수 × makespan) × 100
        avg_utilization = (total_operating_time / (machine_count * makespan)) * 100

        return avg_utilization

    def create_summary_table(self):
        """
        성과지표 요약 테이블 생성

        Returns:
            pd.DataFrame: 4개 행, 3개 컬럼 (지표명, 값, 단위)
        """
        # 각 지표 계산
        po_count = self.calculate_po_count()
        makespan_hours = self.calculate_makespan()
        ontime_rate = self.calculate_ontime_delivery_rate()
        avg_utilization = self.calculate_avg_utilization()

        # DataFrame 생성
        summary_df = pd.DataFrame({
            '지표명': [
                'PO제품수',
                '총 생산시간',
                '납기준수율',
                '장비가동률(전체평균)'
            ],
            '값': [
                po_count,
                round(makespan_hours, 2),
                round(ontime_rate, 2),
                round(avg_utilization, 2)
            ],
            '단위': [
                '개',
                '시간',
                '%',
                '%'
            ]
        })

        return summary_df

    def get_metrics_dict(self):
        """
        성과지표를 딕셔너리로 반환 (프로그래밍 활용용)

        Returns:
            dict: 지표명 → 값 매핑
        """
        return {
            'po_count': self.calculate_po_count(),
            'makespan_hours': self.calculate_makespan(),
            'ontime_delivery_rate': self.calculate_ontime_delivery_rate(),
            'avg_utilization': self.calculate_avg_utilization()
        }
