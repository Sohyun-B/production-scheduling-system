import pandas as pd
import numpy as np
from config import config

class MachineScheduleProcessor:
    def __init__(self, machine_mapping, machine_schedule_df, output_final_result, base_time, gap_analyzer=None):
        """
        :param machine_mapping: 머신 인덱스 -> 머신 이름 매핑 딕셔너리
        :param machine_schedule_df: 기계별 스케줄 데이터프레임
        :param output_final_result: 전체 스케줄 출력 결과 데이터프레임
        :param base_time: 기준 시작 시간(datetime.datetime 또는 pd.Timestamp)
        :param gap_analyzer: 간격 분석기 (옵션)
        """
        self.machine_mapping = machine_mapping
        self.machine_schedule_df = machine_schedule_df.copy()
        self.output_final_result = output_final_result
        self.base_time = base_time
        self.gap_analyzer = gap_analyzer
        self.machine_info = None

    def make_readable_result_file(self):
        self.machine_schedule_df[config.columns.MACHINE_INDEX] = self.machine_schedule_df[config.columns.MACHINE_INDEX].map(self.machine_mapping)
        # 스케줄 할당 작업 분리
        self.machine_schedule_df[[config.columns.OPERATION_ORDER, config.columns.ID]] = pd.DataFrame(
            self.machine_schedule_df[config.columns.ALLOCATED_WORK].tolist(),
            index=self.machine_schedule_df.index
        )
        machine_info = self.machine_schedule_df[[config.columns.MACHINE_INDEX, config.columns.WORK_START_TIME, config.columns.WORK_END_TIME, config.columns.OPERATION_ORDER, config.columns.ID]].copy()
        machine_info[config.columns.WORK_START_TIME] = self.base_time + pd.to_timedelta(machine_info[config.columns.WORK_START_TIME] * config.constants.TIME_MULTIPLIER, unit='m')
        machine_info[config.columns.WORK_END_TIME] = self.base_time + pd.to_timedelta(machine_info[config.columns.WORK_END_TIME] * config.constants.TIME_MULTIPLIER, unit='m')

        self.machine_info = machine_info
        return self.machine_info

    def machine_info_decorate(self, result_df):
        if self.machine_info is None:
            raise RuntimeError("make_readable_result_file() 먼저 실행해야 합니다.")

        machine_info = self.machine_info.copy()

        po_no_list = []
        gitem_list = []
        width_list = []
        length_list = []
        mixture_list = []
        duedate_list = []

        for idx, row in machine_info.iterrows():
            process_order = row[config.columns.OPERATION_ORDER]
            
            process_col = f'{process_order}공정{config.columns.ID}'
            machine_id = row[config.columns.ID]
            filtered_rows = result_df[result_df[process_col] == machine_id]

            po_nos = filtered_rows[config.columns.PO_NO].tolist()
            po_no_list.append(po_nos)

            gitems = filtered_rows[config.columns.GITEM].tolist()
            gitem_list.append(gitems)

            item_width = filtered_rows[f'{config.columns.FABRIC_WIDTH}_{process_order}공정'].tolist()
            width_list.append(item_width)

            item_length = filtered_rows[f'{config.columns.PRODUCTION_LENGTH}_{process_order}공정'].tolist()
            length_list.append(item_length)

            mixtures = filtered_rows[f'{config.columns.MIXTURE_CODE}_{process_order}공정'].tolist()
            mixture_list.append(mixtures)

            duedates = filtered_rows[config.columns.DUE_DATE].tolist()
            duedate_list.append(duedates)

        def unique_or_single(lst):
            unique_vals = list(dict.fromkeys(lst))  # 순서 유지된 유니크값 추출
            if len(unique_vals) == 1:
                return unique_vals[0]
            else:
                return unique_vals

        def timestamps_to_dates(lst):
            return [ts.strftime('%Y-%m-%d') if isinstance(ts, pd.Timestamp) else str(ts) for ts in lst]

        gitem_list = [unique_or_single(x) for x in gitem_list]
        width_list = [unique_or_single(x) for x in width_list]
        length_list = [unique_or_single(x) for x in length_list]
        mixture_list = [unique_or_single(x) for x in mixture_list]
        duedate_list = [timestamps_to_dates(sublist) for sublist in duedate_list]

        machine_info[config.columns.PO_NO] = po_no_list
        machine_info[config.columns.GITEM] = gitem_list
        machine_info[config.columns.FABRIC_WIDTH] = width_list
        machine_info[config.columns.PRODUCTION_LENGTH] = length_list
        machine_info[config.columns.MIXTURE_CODE] = mixture_list
        machine_info[config.columns.DUE_DATE] = duedate_list

        return machine_info
    
    def create_gap_analysis_report(self):
        """간격 분석 리포트 생성"""
        if not self.gap_analyzer:
            print("간격 분석기가 제공되지 않았습니다.")
            return None, None
        
        # 상세 간격 분석
        detailed_gaps = self.gap_analyzer.export_detailed_gaps()
        
        # 기계별 요약
        machine_summary = self.gap_analyzer.get_machine_summary()
        
        return detailed_gaps, machine_summary
    
    def print_gap_summary(self):
        """간격 분석 요약을 콘솔에 출력"""
        if not self.gap_analyzer:
            print("간격 분석기가 제공되지 않았습니다.")
            return
        
        detailed_gaps, machine_summary = self.create_gap_analysis_report()
        
        if machine_summary is not None and not machine_summary.empty:
            print("\n" + "="*60)
            print("기계별 셋업시간/대기시간 분석 결과")
            print("="*60)
            
            for _, row in machine_summary.iterrows():
                machine_idx = row['machine_index']
                gap_count = row['gap_count']
                total_gap = row['total_gap_time'] * 30  # 분 단위
                setup_time = row['total_setup_time'] * 30
                idle_time = row['total_idle_time'] * 30
                efficiency = row['setup_efficiency']
                
                print(f"\n🔧 기계 {machine_idx}:")
                print(f"   간격 수: {gap_count}개")
                print(f"   전체 간격시간: {total_gap:.0f}분")
                print(f"   └─ 셋업시간: {setup_time:.0f}분")
                print(f"   └─ 대기시간: {idle_time:.0f}분")
                print(f"   셋업 효율성: {efficiency:.1f}%")
        
        if detailed_gaps is not None and not detailed_gaps.empty:
            print(f"\n📊 총 {len(detailed_gaps)}개의 간격 발견")
            
            # 셋업 이유별 통계
            setup_reasons = detailed_gaps['setup_reason'].value_counts()
            print("\n셋업 발생 원인:")
            for reason, count in setup_reasons.items():
                if reason != 'no_change_detected':
                    print(f"   {reason}: {count}회")
        
        print("\n" + "="*60)