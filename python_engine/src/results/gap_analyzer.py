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
            result = {
                'machine_index': machine_index,
                'gap_start': gap_start,
                'gap_end': gap_end,
                'gap_duration': gap_duration,
                'gap_type': 'system_gap',  # 시스템 제약
                'setup_time': 0,
                'idle_time': gap_duration, # 우선은 전체 시간으로 초기화
                'prev_task_id': prev_task[1],
                'next_task_id': next_task[1]
            }
            
            # 시스템 gap에 대한 setup_details 추가
            system_details = {
                'earlier_operation_type': 'system',
                'later_operation_type': 'system',
                'long_to_short': False,
                'short_to_long': False,
                'same_type': True,
                'same_mixture': True,
                'setup_key': 'system_downtime'
            }
            result.update(system_details)
            
            return result
        
        # 실제 셋업시간 계산
        prev_task_id = prev_task[1]
        next_task_id = next_task[1]
        
        # DelayProcessor로 이론적 셋업시간 계산
        theoretical_setup_time = self.delay_processor.delay_calc_whole_process(
            prev_task_id, next_task_id, machine_index
        )
        
        # 셋업 상세 정보 분석
        setup_details = self._analyze_setup_details(prev_task_id, next_task_id, machine_index)
        
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
        
        # 결과에 setup_details 추가
        result = {
            'machine_index': machine_index,
            'gap_start': gap_start,
            'gap_end': gap_end,
            'gap_duration': gap_duration,
            'gap_type': gap_type,
            'setup_time': setup_time,
            'idle_time': idle_time,
            'theoretical_setup_time': theoretical_setup_time,
            'prev_task_id': prev_task_id,
            'next_task_id': next_task_id
        }
        
        # setup_details를 result에 추가
        result.update(setup_details)
        
        return result
    
    def _analyze_setup_details(self, prev_task_id, next_task_id, machine_index):
        """DelayProcessor에서 사용하는 키 값들을 그대로 반환"""
        if machine_index not in [0, 2, 3]:
            return {
                'machine_index': machine_index,
                'earlier_operation_type': 'N/A',
                'later_operation_type': 'N/A', 
                'long_to_short': False,
                'short_to_long': False,
                'same_type': True,
                'same_mixture': True,
                'setup_key': 'no_setup_machine'
            }
        
        # opnode_dict에서 작업 정보 추출
        prev_info = self.delay_processor.opnode_dict.get(prev_task_id, [0]*6)
        next_info = self.delay_processor.opnode_dict.get(next_task_id, [0]*6)
        
        if len(prev_info) < 5 or len(next_info) < 5:
            return {
                'machine_index': machine_index,
                'earlier_operation_type': 'unknown',
                'later_operation_type': 'unknown',
                'long_to_short': False,
                'short_to_long': False, 
                'same_type': False,
                'same_mixture': False,
                'setup_key': 'insufficient_data'
            }
        
        # DelayProcessor의 calculate_delay와 동일한 로직
        earlier_operation_type = prev_info[2]
        later_operation_type = next_info[2]
        earlier_width = prev_info[3]
        later_width = next_info[3]
        earlier_mixture = prev_info[4]
        later_mixture = next_info[4]
        
        # 조건 계산
        long_to_short = earlier_width > later_width
        short_to_long = earlier_width < later_width
        same_type = earlier_operation_type == later_operation_type
        same_mixture = earlier_mixture == later_mixture
        
        # DelayProcessor가 실제로 사용하는 키 생성
        setup_key = (machine_index, earlier_operation_type, later_operation_type, 
                    long_to_short, short_to_long, same_type, same_mixture)
        
        return {
            'machine_index': machine_index,
            'earlier_operation_type': earlier_operation_type,
            'later_operation_type': later_operation_type,
            'long_to_short': long_to_short,
            'short_to_long': short_to_long,
            'same_type': same_type,
            'same_mixture': same_mixture,
            'setup_key': str(setup_key)
        }
    
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


class GapAnalysisProcessor:
    """간격 분석 처리 및 결과 저장 통합 클래스"""
    
    def __init__(self, base_date):
        """
        Args:
            base_date (datetime): 기준 날짜
        """
        self.base_date = base_date
    
    def process(self, scheduler, machine_schedule_df, result_cleaned, machine_master_info):
        """
        간격 분석 파이프라인 실행
        
        Args:
            scheduler: 스케줄러 인스턴스
            machine_schedule_df (pd.DataFrame): 정리된 기계 스케줄
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과
            machine_master_info (pd.DataFrame): 기계 마스터 정보
            
        Returns:
            dict: {
                'gap_analyzer': ScheduleGapAnalyzer,  # 간격 분석기 객체
                'detailed_gaps': pd.DataFrame,        # 상세 간격 분석 결과 (None일 수 있음)
                'machine_summary': pd.DataFrame       # 기계별 간격 요약 (None일 수 있음)
            }
        """
        gap_analyzer = None
        detailed_gaps = None
        machine_summary = None
        
        try:
            print("[간격분석] 간격 분석 시작...")
            
            # 지연 처리기 가져오기
            delay_processor = scheduler.delay_processor
            
            # 간격 분석기 생성
            gap_analyzer = ScheduleGapAnalyzer(scheduler, delay_processor)
            
            # 기계 매핑 정보
            machine_mapping = machine_master_info.set_index('기계인덱스')['기계코드'].to_dict()
            
            # 기계별 스케줄 결과 처리기에 간격 분석기 전달
            from .machine_processor import MachineScheduleProcessor
            processor = MachineScheduleProcessor(
                machine_mapping,
                machine_schedule_df,
                result_cleaned,
                self.base_date,
                gap_analyzer
            )
            
            # 간격 분석 요약 출력
            processor.print_gap_summary()
            
            # 상세 간격 분석 결과 저장
            detailed_gaps, machine_summary = processor.create_gap_analysis_report()
            
            # Excel 파일 저장
            if detailed_gaps is not None:
                detailed_gaps.to_excel("data/output/schedule_gaps_detailed.xlsx", index=False)
                print("[간격분석] 상세 간격 분석 결과 저장: schedule_gaps_detailed.xlsx")
            
            if machine_summary is not None:
                machine_summary.to_excel("data/output/machine_gap_summary.xlsx", index=False)
                print("[간격분석] 기계별 간격 요약 저장: machine_gap_summary.xlsx")
            
            print("[간격분석] 완료")
            
        except Exception as gap_error:
            print(f"[WARNING] 간격 분석 중 오류 (계속 진행): {gap_error}")
            gap_analyzer = None
        
        return {
            'gap_analyzer': gap_analyzer,
            'detailed_gaps': detailed_gaps, # 데이터프레임
            'machine_summary': machine_summary # 데이터프레임
        }