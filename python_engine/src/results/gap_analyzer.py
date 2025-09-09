"""
완성된 스케줄에서 기계별 빈 시간을 셋업시간 vs 대기시간으로 구분하는 분석 클래스
"""

import pandas as pd
from config import config


class ScheduleGapAnalyzer:
    """완성된 스케줄에서 기계별 간격을 셋업시간/대기시간으로 분석"""
    
    def __init__(self, scheduler, delay_processor):
        """
        Args:
            scheduler: 완성된 Scheduler 인스턴스
            delay_processor: DelayProcessor 인스턴스
        """
        self.scheduler = scheduler
        self.delay_processor = delay_processor
        self.gap_analysis_results = []
    
    def analyze_all_machine_gaps(self):
        """모든 기계의 간격을 분석하여 셋업시간/대기시간 구분"""
        self.gap_analysis_results = []
        
        for machine in self.scheduler.Machines:
            machine_gaps = self._analyze_single_machine_gaps(machine)
            self.gap_analysis_results.extend(machine_gaps)
        
        return pd.DataFrame(self.gap_analysis_results)
    
    def _analyze_single_machine_gaps(self, machine):
        """단일 기계의 모든 간격 분석"""
        gaps = []
        tasks = machine.assigned_task
        starts = machine.O_start
        ends = machine.O_end
        
        if len(tasks) < 2:
            return gaps  # 작업이 1개 이하면 간격 없음
        
        # 시간순 정렬 (혹시 순서가 뒤바뀌었을 경우 대비)
        sorted_indices = sorted(range(len(starts)), key=lambda i: starts[i])
        
        for i in range(len(sorted_indices) - 1):
            current_idx = sorted_indices[i]
            next_idx = sorted_indices[i + 1]
            
            current_end = ends[current_idx]
            next_start = starts[next_idx]
            gap_duration = next_start - current_end
            
            if gap_duration > 0:  # 간격이 있는 경우만
                gap_info = self._classify_gap(
                    machine.Machine_index,
                    tasks[current_idx],
                    tasks[next_idx], 
                    current_end,
                    next_start,
                    gap_duration
                )
                gaps.append(gap_info)
        
        return gaps
    
    def _classify_gap(self, machine_index, prev_task, next_task, gap_start, gap_end, gap_duration):
        """간격을 셋업시간/대기시간으로 분류"""
        
        # DOWNTIME 등 가짜 작업은 제외
        if prev_task[0] == -1 or next_task[0] == -1:
            return {
                'machine_index': machine_index,
                'gap_start': gap_start,
                'gap_end': gap_end,
                'gap_duration': gap_duration,
                'gap_type': 'system_gap',  # 시스템 제약
                'setup_time': 0,
                'idle_time': gap_duration,
                'prev_task_id': prev_task[1],
                'next_task_id': next_task[1],
                'setup_reason': 'system_downtime'
            }
        
        # 실제 셋업시간 계산
        prev_task_id = prev_task[1]
        next_task_id = next_task[1]
        
        # DelayProcessor로 이론적 셋업시간 계산
        theoretical_setup_time = self.delay_processor.delay_calc_whole_process(
            prev_task_id, next_task_id, machine_index
        )
        
        # 셋업 이유 분석
        setup_reason = self._analyze_setup_reason(prev_task_id, next_task_id, machine_index)
        
        # 실제 간격과 이론적 셋업시간 비교
        if theoretical_setup_time == 0:
            # 셋업시간이 0이면 모든 간격이 대기시간
            gap_type = 'pure_idle'
            setup_time = 0
            idle_time = gap_duration
        elif gap_duration <= theoretical_setup_time:
            # 간격이 셋업시간보다 작거나 같으면 모두 셋업시간
            gap_type = 'pure_setup'
            setup_time = gap_duration
            idle_time = 0
        else:
            # 간격이 셋업시간보다 크면 셋업시간 + 대기시간
            gap_type = 'setup_plus_idle'
            setup_time = theoretical_setup_time
            idle_time = gap_duration - theoretical_setup_time
        
        return {
            'machine_index': machine_index,
            'gap_start': gap_start,
            'gap_end': gap_end,
            'gap_duration': gap_duration,
            'gap_type': gap_type,
            'setup_time': setup_time,
            'idle_time': idle_time,
            'theoretical_setup_time': theoretical_setup_time,
            'prev_task_id': prev_task_id,
            'next_task_id': next_task_id,
            'setup_reason': setup_reason
        }
    
    def _analyze_setup_reason(self, prev_task_id, next_task_id, machine_index):
        """셋업 발생 이유 분석"""
        if machine_index not in [0, 2, 3]:
            return 'no_setup_machine'
        
        # opnode_dict에서 작업 정보 추출
        prev_info = self.delay_processor.opnode_dict.get(prev_task_id, [0]*6)
        next_info = self.delay_processor.opnode_dict.get(next_task_id, [0]*6)
        
        if len(prev_info) < 5 or len(next_info) < 5:
            return 'insufficient_data'
        
        prev_operation_type = prev_info[2]
        next_operation_type = next_info[2]
        prev_width = prev_info[3]
        next_width = next_info[3]
        prev_mixture = prev_info[4]
        next_mixture = next_info[4]
        
        reasons = []
        
        # 배합액 변경
        if prev_mixture != next_mixture:
            reasons.append('mixture_change')
        
        # 공정 타입 변경
        if prev_operation_type != next_operation_type:
            reasons.append('operation_type_change')
        
        # 너비 변경
        if prev_width != next_width:
            if prev_width > next_width:
                reasons.append('width_long_to_short')
            else:
                reasons.append('width_short_to_long')
        
        return '+'.join(reasons) if reasons else 'no_change_detected'
    
    def get_machine_summary(self):
        """기계별 셋업시간/대기시간 요약"""
        if not self.gap_analysis_results:
            self.analyze_all_machine_gaps()
        
        df = pd.DataFrame(self.gap_analysis_results)
        if df.empty:
            return pd.DataFrame()
        
        summary = df.groupby('machine_index').agg({
            'gap_duration': ['count', 'sum'],
            'setup_time': 'sum', 
            'idle_time': 'sum',
            'theoretical_setup_time': 'sum'
        }).round(2)
        
        summary.columns = [
            'gap_count', 'total_gap_time', 
            'total_setup_time', 'total_idle_time', 
            'total_theoretical_setup_time'
        ]
        
        # 효율성 지표 추가
        summary['setup_efficiency'] = (
            summary['total_setup_time'] / summary['total_theoretical_setup_time'] * 100
        ).fillna(0).round(1)
        
        return summary.reset_index()
    
    def export_detailed_gaps(self):
        """상세한 간격 정보를 DataFrame으로 반환"""
        if not self.gap_analysis_results:
            self.analyze_all_machine_gaps()
        
        df = pd.DataFrame(self.gap_analysis_results)
        if df.empty:
            return df
        
        # 시간을 실제 시간으로 변환 (30분 단위 → 분)
        time_columns = ['gap_start', 'gap_end', 'gap_duration', 'setup_time', 'idle_time', 'theoretical_setup_time']
        for col in time_columns:
            if col in df.columns:
                df[f'{col}_minutes'] = df[col] * config.constants.TIME_MULTIPLIER
        
        return df