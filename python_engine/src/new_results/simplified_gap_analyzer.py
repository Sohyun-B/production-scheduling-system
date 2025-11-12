"""
간결하고 실무 친화적인 간격 분석 모듈

기존 detailed_gaps (23개 컬럼)를 12개 컬럼으로 축소하고
"변경사유" 컬럼을 추가하여 한눈에 셋업 발생 원인을 파악할 수 있도록 개선
"""

import pandas as pd
from config import config


class SimplifiedGapAnalyzer:
    """간결하고 실무 친화적인 간격 분석 클래스"""

    def __init__(self, scheduler, delay_processor, machine_mapper, base_date):
        """
        Args:
            scheduler: 스케줄러 인스턴스
            delay_processor: DelayProcessor 인스턴스
            machine_mapper (MachineMapper): 기계 정보 매핑 관리 객체
            base_date (datetime): 기준 날짜
        """
        self.scheduler = scheduler
        self.delay_processor = delay_processor
        self.machine_mapper = machine_mapper
        self.base_date = base_date

        # 기계 매핑 (인덱스 → 코드, 이름)
        self.machine_idx_to_code = {
            idx: machine_mapper.index_to_code(idx)
            for idx in machine_mapper.get_all_indices()
        }

        self.machine_idx_to_name = {
            idx: machine_mapper.index_to_name(idx)
            for idx in machine_mapper.get_all_indices()
        }

    def analyze_all_gaps(self):
        """
        모든 기계의 간격을 분석하여 간결한 DataFrame 반환

        Returns:
            pd.DataFrame: 12개 컬럼의 간격 분석 결과
        """
        gaps = []

        for machine in self.scheduler.Machines:
            machine_gaps = self._analyze_machine_gaps(machine)
            gaps.extend(machine_gaps)

        df = pd.DataFrame(gaps)

        # 시간순 정렬
        if not df.empty and '간격시작시각' in df.columns:
            df = df.sort_values(['기계코드', '간격시작시각']).reset_index(drop=True)

        return df

    def _analyze_machine_gaps(self, machine):
        """
        단일 기계의 간격 분석

        Args:
            machine: Machine_Time_window 객체

        Returns:
            list: 간격 정보 딕셔너리 리스트
        """
        gaps = []

        # 작업이 2개 미만이면 간격 없음
        if len(machine.assigned_task) < 2:
            return gaps

        # 시간순 정렬
        sorted_indices = sorted(
            range(len(machine.O_start)),
            key=lambda i: machine.O_start[i]
        )

        for i in range(len(sorted_indices) - 1):
            curr_idx = sorted_indices[i]
            next_idx = sorted_indices[i + 1]

            gap_start = machine.O_end[curr_idx]
            gap_end = machine.O_start[next_idx]
            gap_duration = gap_end - gap_start

            if gap_duration <= 0:
                continue  # 간격 없음

            # 간격 정보 계산
            gap_info = self._calculate_gap_info(
                machine.Machine_index,
                machine.assigned_task[curr_idx],
                machine.assigned_task[next_idx],
                gap_start,
                gap_end,
                gap_duration
            )

            if gap_info:
                gaps.append(gap_info)

        return gaps

    def _calculate_gap_info(self, machine_idx, prev_task, next_task,
                           gap_start, gap_end, gap_duration):
        """
        간격 정보 계산 (핵심 로직)

        Args:
            machine_idx (int): 기계 인덱스
            prev_task (tuple): (depth, task_id)
            next_task (tuple): (depth, task_id)
            gap_start (float): 간격 시작 시간 (TIME_MULTIPLIER 단위)
            gap_end (float): 간격 종료 시간 (TIME_MULTIPLIER 단위)
            gap_duration (float): 간격 시간 (TIME_MULTIPLIER 단위)

        Returns:
            dict or None: 간격 정보 딕셔너리 (12개 키)
        """
        # 시스템 작업 (depth == -1) 제외
        if prev_task[0] == -1 or next_task[0] == -1:
            return None

        prev_task_id = prev_task[1]
        next_task_id = next_task[1]

        # 이론적 셋업시간 계산
        theoretical_setup = self.delay_processor.delay_calc_whole_process(
            prev_task_id, next_task_id, machine_idx
        )

        # 셋업시간 vs 대기시간 분류
        if theoretical_setup == 0:
            gap_type = "순수대기"
            setup_time = 0
            idle_time = gap_duration
        elif gap_duration <= theoretical_setup:
            gap_type = "순수셋업"
            setup_time = gap_duration
            idle_time = 0
        else:
            gap_type = "혼합(셋업+대기)"
            setup_time = theoretical_setup
            idle_time = gap_duration - theoretical_setup

        # 작업 정보 추출
        prev_info = self.delay_processor.opnode_dict.get(prev_task_id, {})
        next_info = self.delay_processor.opnode_dict.get(next_task_id, {})

        # 변경사유 분석
        change_reason = self._analyze_change_reason(prev_info, next_info)

        # 작업 요약
        prev_work = self._format_task_summary(prev_info)
        next_work = self._format_task_summary(next_info)

        # 시간 변환 (TIME_MULTIPLIER → 분)
        time_mult = config.constants.TIME_MULTIPLIER

        # 실제 datetime 변환
        gap_start_dt = self.base_date + pd.Timedelta(minutes=gap_start * time_mult)
        gap_end_dt = self.base_date + pd.Timedelta(minutes=gap_end * time_mult)

        # 셋업비율 계산
        setup_ratio = (setup_time / gap_duration * 100) if gap_duration > 0 else 0

        return {
            '기계코드': self.machine_idx_to_code.get(machine_idx, f'M{machine_idx}'),
            '기계명': self.machine_idx_to_name.get(machine_idx, f'기계{machine_idx}'),
            '간격시작시각': gap_start_dt,
            '간격종료시각': gap_end_dt,
            '간격시간(분)': round(gap_duration * time_mult, 1),
            '간격유형': gap_type,
            '셋업시간(분)': round(setup_time * time_mult, 1),
            '대기시간(분)': round(idle_time * time_mult, 1),
            '이전작업': prev_work,
            '다음작업': next_work,
            '변경사유': change_reason,
            '셋업비율(%)': round(setup_ratio, 1)
        }

    def _analyze_change_reason(self, prev_info, next_info):
        """
        변경사유 분석 (핵심!)

        Args:
            prev_info (dict): 이전 작업 정보
            next_info (dict): 다음 작업 정보

        Returns:
            str: 변경사유 문자열
        """
        reasons = []

        # 정보가 없으면 "정보없음"
        if not prev_info or not next_info:
            return "정보없음"

        # 1. 공정 변경
        prev_op_type = prev_info.get("OPERATION_CLASSIFICATION")
        next_op_type = next_info.get("OPERATION_CLASSIFICATION")

        if prev_op_type and next_op_type and prev_op_type != next_op_type:
            reasons.append(f"공정변경({prev_op_type}→{next_op_type})")

        # 2. 배합액 변경
        prev_chem = prev_info.get("SELECTED_CHEMICAL")
        next_chem = next_info.get("SELECTED_CHEMICAL")

        if prev_chem and next_chem and prev_chem != next_chem:
            reasons.append("배합액변경")

        # 3. 폭 변경
        prev_width = prev_info.get("FABRIC_WIDTH")
        next_width = next_info.get("FABRIC_WIDTH")

        if prev_width and next_width and prev_width != next_width:
            if prev_width > next_width:
                reasons.append(f"폭변경(대→소: {prev_width}→{next_width})")
            else:
                reasons.append(f"폭변경(소→대: {prev_width}→{next_width})")

        # 변경사유 없으면 순수 대기
        if not reasons:
            return "변경없음(대기)"

        return ", ".join(reasons)

    def _format_task_summary(self, task_info):
        """
        작업 요약 포맷 (공정-GITEM)

        Args:
            task_info (dict): 작업 정보

        Returns:
            str: 작업 요약 문자열
        """
        if not task_info:
            return "N/A"

        op_code = task_info.get("OPERATION_CODE", "")
        gitem = task_info.get("GITEM", "")

        if op_code and gitem:
            return f"{op_code}-{gitem}"
        elif op_code:
            return op_code
        else:
            return "N/A"

    def get_summary_by_machine(self):
        """
        기계별 간격 요약 정보

        Returns:
            pd.DataFrame: 기계별 요약 (간격 개수, 총 시간, 평균 셋업비율 등)
        """
        gaps_df = self.analyze_all_gaps()

        if gaps_df.empty:
            return pd.DataFrame()

        summary = gaps_df.groupby(['기계코드', '기계명']).agg({
            '간격시간(분)': ['count', 'sum', 'mean'],
            '셋업시간(분)': 'sum',
            '대기시간(분)': 'sum',
            '셋업비율(%)': 'mean'
        }).round(1)

        # 컬럼명 평탄화
        summary.columns = ['간격개수', '총간격시간(분)', '평균간격시간(분)',
                          '총셋업시간(분)', '총대기시간(분)', '평균셋업비율(%)']

        return summary.reset_index()

    def get_summary_by_gap_type(self):
        """
        간격유형별 요약 정보

        Returns:
            pd.DataFrame: 간격유형별 요약
        """
        gaps_df = self.analyze_all_gaps()

        if gaps_df.empty:
            return pd.DataFrame()

        summary = gaps_df.groupby('간격유형').agg({
            '간격시간(분)': ['count', 'sum', 'mean']
        }).round(1)

        summary.columns = ['개수', '총시간(분)', '평균시간(분)']

        return summary.reset_index()
