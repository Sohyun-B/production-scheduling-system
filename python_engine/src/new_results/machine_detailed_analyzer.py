"""
장비별 상세 성과 분석 모듈

각 장비의 가동시간, 대기시간, 공정교체시간 및 loss율 계산
"""

import pandas as pd
from config import config


class MachineDetailedAnalyzer:
    """장비별 상세 분석 클래스"""

    def __init__(self, scheduler, gap_analyzer, machine_master_info):
        """
        Args:
            scheduler: 스케줄러 인스턴스
            gap_analyzer: SimplifiedGapAnalyzer 인스턴스
            machine_master_info (pd.DataFrame): 기계 마스터 정보
        """
        self.scheduler = scheduler
        self.gap_analyzer = gap_analyzer
        self.machine_master_info = machine_master_info

        # 기계 매핑
        self.machine_idx_to_code = machine_master_info.set_index(
            config.columns.MACHINE_INDEX
        )[config.columns.MACHINE_CODE].to_dict()

        self.machine_idx_to_name = machine_master_info.set_index(
            config.columns.MACHINE_INDEX
        )[config.columns.MACHINE_NAME].to_dict()

    def calculate_machine_operating_time(self, machine):
        """
        특정 기계의 가동시간 계산 (분 단위)

        Args:
            machine: Machine_Time_window 객체

        Returns:
            float: 가동시간 (분)
        """
        if len(machine.assigned_task) == 0:
            return 0.0

        # 각 작업의 처리시간 합계
        operating_time_raw = sum([
            end - start
            for start, end in zip(machine.O_start, machine.O_end)
        ])

        # 분 단위로 변환
        operating_time_minutes = operating_time_raw * config.constants.TIME_MULTIPLIER

        return operating_time_minutes

    def extract_gap_times(self, machine_idx):
        """
        gap_analyzer에서 특정 기계의 대기시간/셋업시간 추출

        Args:
            machine_idx (int): 기계 인덱스

        Returns:
            dict: {'setup_time': float, 'idle_time': float} (분 단위)
        """
        # SimplifiedGapAnalyzer의 결과 사용
        gaps_df = self.gap_analyzer.analyze_all_gaps()

        if gaps_df.empty:
            return {'setup_time': 0.0, 'idle_time': 0.0}

        # 기계 코드로 필터링
        machine_code = self.machine_idx_to_code.get(machine_idx, f'M{machine_idx}')
        machine_gaps = gaps_df[gaps_df['기계코드'] == machine_code]

        if machine_gaps.empty:
            return {'setup_time': 0.0, 'idle_time': 0.0}

        # 셋업시간 및 대기시간 합계
        setup_time = machine_gaps['셋업시간(분)'].sum()
        idle_time = machine_gaps['대기시간(분)'].sum()

        return {
            'setup_time': setup_time,
            'idle_time': idle_time
        }

    def create_detailed_table(self):
        """
        장비별 상세 성과 테이블 생성

        Returns:
            pd.DataFrame: 9개 컬럼 (기계코드, 기계명, 가동시간, 가동율, ...)
        """
        # makespan 계산 (분 단위)
        makespan_raw = max([
            machine.End_time for machine in self.scheduler.Machines
            if len(machine.assigned_task) > 0
        ], default=0)
        makespan_minutes = makespan_raw * config.constants.TIME_MULTIPLIER

        if makespan_minutes == 0:
            return pd.DataFrame()

        rows = []

        for machine in self.scheduler.Machines:
            machine_idx = machine.Machine_index
            machine_code = self.machine_idx_to_code.get(machine_idx, f'M{machine_idx}')
            machine_name = self.machine_idx_to_name.get(machine_idx, f'기계{machine_idx}')

            # 가동시간 계산
            operating_time = self.calculate_machine_operating_time(machine)

            # 대기/셋업시간 추출
            gap_times = self.extract_gap_times(machine_idx)
            idle_time = gap_times['idle_time']
            setup_time = gap_times['setup_time']

            # 총시간 (makespan과 동일)
            total_time = makespan_minutes

            # 비율 계산
            utilization_rate = (operating_time / total_time * 100) if total_time > 0 else 0
            idle_loss_rate = (idle_time / total_time * 100) if total_time > 0 else 0
            setup_loss_rate = (setup_time / total_time * 100) if total_time > 0 else 0

            # 검증: 가동율 + 대기loss율 + 교체loss율 ≈ 100%
            total_rate = utilization_rate + idle_loss_rate + setup_loss_rate

            rows.append({
                '기계코드': machine_code,
                '기계명': machine_name,
                '가동시간(분)': round(operating_time, 1),
                '가동율(%)': round(utilization_rate, 2),
                '대기시간(분)': round(idle_time, 1),
                '대기loss율(%)': round(idle_loss_rate, 2),
                '공정교체시간(분)': round(setup_time, 1),
                '공정교체loss율(%)': round(setup_loss_rate, 2),
                '총시간(분)': round(total_time, 1)
            })

        df = pd.DataFrame(rows)

        # 기계코드 기준 정렬
        if not df.empty:
            df = df.sort_values('기계코드').reset_index(drop=True)

        return df

    def validate_time_balance(self, detailed_table):
        """
        시간 균형 검증 (가동 + 대기 + 교체 ≈ 총시간)

        Args:
            detailed_table (pd.DataFrame): create_detailed_table() 결과

        Returns:
            pd.DataFrame: 검증 결과 (기계코드, 계산합계, 총시간, 오차)
        """
        if detailed_table.empty:
            return pd.DataFrame()

        validation = detailed_table.copy()

        # 시간 합계 계산
        validation['계산합계(분)'] = (
            validation['가동시간(분)'] +
            validation['대기시간(분)'] +
            validation['공정교체시간(분)']
        )

        # 오차 계산
        validation['오차(분)'] = (
            validation['계산합계(분)'] - validation['총시간(분)']
        ).round(1)

        # 오차율 계산
        validation['오차율(%)'] = (
            (validation['오차(분)'] / validation['총시간(분)'] * 100)
            .round(2)
        )

        return validation[['기계코드', '기계명', '계산합계(분)', '총시간(분)', '오차(분)', '오차율(%)']]
