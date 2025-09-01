import pandas as pd
import numpy as np
from config import config

class MachineScheduleProcessor:
    def __init__(self, machine_mapping, machine_schedule_df, output_final_result, base_time):
        """
        :param machine_mapping: 머신 인덱스 -> 머신 이름 매핑 딕셔너리
        :param machine_schedule_df: 기계별 스케줄 데이터프레임
        :param output_final_result: 전체 스케줄 출력 결과 데이터프레임
        :param base_time: 기준 시작 시간(datetime.datetime 또는 pd.Timestamp)
        """
        self.machine_mapping = machine_mapping
        self.machine_schedule_df = machine_schedule_df.copy()
        self.output_final_result = output_final_result
        self.base_time = base_time
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