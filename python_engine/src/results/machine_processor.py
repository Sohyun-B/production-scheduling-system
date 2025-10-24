"""
기계 정보 처리 통합 모듈 (machine_schedule + machine_info_processor 통합)
"""

import pandas as pd
import numpy as np
from config import config


class MachineScheduleProcessor:
    """기계 스케줄 처리 (기존 machine_schedule.py의 클래스)"""
    
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
        chemical_list = []
        duedate_list = []

        for idx, row in machine_info.iterrows():
            process_order = row[config.columns.OPERATION_ORDER]
            
            process_col = f'{process_order}{config.columns.PROCESS_ID_SUFFIX}'
            machine_id = row[config.columns.ID]
            filtered_rows = result_df[result_df[process_col] == machine_id]

            po_nos = filtered_rows[config.columns.PO_NO].tolist()
            po_no_list.append(po_nos)

            gitems = filtered_rows[config.columns.GITEM].tolist()
            gitem_list.append(gitems)

            item_width = filtered_rows[f'{config.columns.FABRIC_WIDTH}_{process_order}{config.columns.PROCESS_ID_SUFFIX}'].tolist()
            width_list.append(item_width)

            item_length = filtered_rows[f'{config.columns.PRODUCTION_LENGTH}_{process_order}{config.columns.PROCESS_ID_SUFFIX}'].tolist()
            length_list.append(item_length)

            chemicals = filtered_rows[f'{config.columns.CHEMICAL_LIST}_{process_order}{config.columns.PROCESS_ID_SUFFIX}'].tolist()
            chemical_list.append(chemicals)

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
        chemical_list = [unique_or_single(x) for x in chemical_list]
        duedate_list = [timestamps_to_dates(sublist) for sublist in duedate_list]

        machine_info[config.columns.PO_NO] = po_no_list
        machine_info[config.columns.GITEM] = gitem_list
        machine_info[config.columns.FABRIC_WIDTH] = width_list
        machine_info[config.columns.PRODUCTION_LENGTH] = length_list
        machine_info[config.columns.CHEMICAL_LIST] = chemical_list
        machine_info[config.columns.DUE_DATE] = duedate_list

        return machine_info

    def print_gap_summary(self):
        """간격 분석 요약 출력"""
        if not self.gap_analyzer:
            print("[간격분석] 간격 분석기가 없습니다.")
            return
        
        try:
            machine_summary = self.gap_analyzer.get_machine_summary()

            if not machine_summary.empty:
                print("\n=== 기계별 간격 요약 ===")
                for _, row in machine_summary.iterrows():
                    machine_idx = row['machine_index']
                    setup_time = row['total_setup_time']
                    idle_time = row['total_idle_time']
                    gap_count = row['gap_count']
                    print(f"기계 {machine_idx}: 총 간격 {gap_count}개, 셋업시간 {setup_time:.1f}, 대기시간 {idle_time:.1f}")
            else:
                print("[간격분석] 분석할 간격이 없습니다.")
        except Exception as e:
            print(f"[간격분석] 요약 출력 중 오류: {e}")
            raise

    def create_gap_analysis_report(self):
        """상세 간격 분석 리포트 생성"""
        if not self.gap_analyzer:
            return None, None
        
        try:
            detailed_gaps = self.gap_analyzer.export_detailed_gaps()
            machine_summary = self.gap_analyzer.get_machine_summary()
            return detailed_gaps, machine_summary
        except Exception as e:
            print(f"[간격분석] 리포트 생성 중 오류: {e}")
            raise


class MachineProcessor:
    """기계 정보 처리 통합 클래스"""
    
    def __init__(self, base_date):
        """
        Args:
            base_date (datetime): 기준 날짜
        """
        self.base_date = base_date
    
    def process(self, machine_schedule_df, result_cleaned, machine_master_info, 
                merged_result, original_order, gap_analyzer=None):
        """
        기계 정보 처리 파이프라인 실행
        
        Args:
            machine_schedule_df (pd.DataFrame): 정리된 기계 스케줄
            result_cleaned (pd.DataFrame): 정리된 스케줄링 결과
            machine_master_info (pd.DataFrame): 기계 마스터 정보
            merged_result (pd.DataFrame): 병합된 결과
            original_order (pd.DataFrame): 원본 주문 데이터
            gap_analyzer: 간격 분석기 (선택적)
            
        Returns:
            dict: {
                'machine_info': pd.DataFrame   # 가공된 기계 정보
            }
        """
        print("[기계처리] 기계 정보 처리 시작...")
        
        # 기계 인덱스 -> 코드 매핑
        machine_mapping = machine_master_info.set_index(config.columns.MACHINE_INDEX)[config.columns.MACHINE_CODE].to_dict()
        
        # 기계 스케줄 처리기 초기화
        machine_proc = MachineScheduleProcessor(
            machine_mapping, 
            machine_schedule_df, 
            result_cleaned, 
            self.base_date,
            gap_analyzer
        )
        
        # 기본 기계 정보 생성
        machine_info = machine_proc.make_readable_result_file()
        machine_info = machine_proc.machine_info_decorate(merged_result)
        
        # === 데이터 가공 및 GITEM명 매핑 ===
        # GITEM명 정보 매핑
        order_with_names = original_order[[config.columns.GITEM, config.columns.GITEM_NAME]].drop_duplicates()
        
        # 기계 정보 가공
        code_to_name_mapping = machine_master_info.set_index(config.columns.MACHINE_CODE)[config.columns.MACHINE_NAME].to_dict()
        machine_info = machine_info.rename(columns={config.columns.MACHINE_INDEX: config.columns.MACHINE_CODE})
        machine_info[config.columns.MACHINE_NAME] = machine_info[config.columns.MACHINE_CODE].map(code_to_name_mapping)
        
        # GITEM명 및 추가 컬럼 생성
        machine_info = pd.merge(machine_info, order_with_names, on=config.columns.GITEM, how='left')
        machine_info[config.columns.OPERATION] = machine_info[config.columns.ID].str.split('_').str[1]
        machine_info[config.columns.WORK_TIME] = machine_info[config.columns.WORK_END_TIME] - machine_info[config.columns.WORK_START_TIME]
        
        print(f"[기계처리] 완료 - 기계 정보: {len(machine_info)}행")
        
        # Gap 분석 관련 메서드들도 포함
        if gap_analyzer:
            machine_proc.print_gap_summary()
        
        return {
            'machine_info': machine_info,
            'processor': machine_proc  # gap 분석 리포트 생성용
        }