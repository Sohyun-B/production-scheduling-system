"""
호기 정보 생성 전용 모듈 (results 전용)
MachineScheduleProcessor 로직 기반으로 단순화
"""

import pandas as pd
from config import config


class MachineInfoBuilder:
    """호기 정보 생성 전용 클래스 (results용)"""

    def __init__(self, machine_mapper, base_date):
        """
        Args:
            machine_mapper (MachineMapper): 기계 매핑 관리자
            base_date (datetime): 기준 날짜
        """
        self.machine_mapper = machine_mapper
        self.base_date = base_date

    def build_machine_info(self, machine_schedule_df):
        """
        기본 호기 정보 생성

        Args:
            machine_schedule_df (pd.DataFrame): 기계 스케줄 (depth -1 제거됨)

        Returns:
            pd.DataFrame: 기본 호기 정보
                - MACHINE_CODE, MACHINE_NAME
                - WORK_START_TIME, WORK_END_TIME (datetime 변환)
                - OPERATION_ORDER, PROCESS_ID

        (MachineScheduleProcessor.make_readable_result_file 로직 기반)
        """
        df = machine_schedule_df.copy()

        # 1. MACHINE_NAME 추가 (code → name 매핑)
        machine_mapping = {
            code: self.machine_mapper.code_to_name(code)
            for code in self.machine_mapper.get_all_codes()
        }
        df[config.columns.MACHINE_NAME] = df[config.columns.MACHINE_CODE].map(machine_mapping)

        # 2. 할당 작업 분리 (tuple → 별도 컬럼)
        df[[config.columns.OPERATION_ORDER, config.columns.PROCESS_ID]] = pd.DataFrame(
            df[config.columns.ALLOCATED_WORK].tolist(),
            index=df.index
        )

        # 3. 필요한 컬럼만 선택
        machine_info = df[[
            config.columns.MACHINE_CODE,
            config.columns.MACHINE_NAME,
            config.columns.WORK_START_TIME,
            config.columns.WORK_END_TIME,
            config.columns.OPERATION_ORDER,
            config.columns.PROCESS_ID
        ]].copy()

        # 4. 시간 변환 (30분 단위 → datetime)
        machine_info[config.columns.WORK_START_TIME] = (
            self.base_date +
            pd.to_timedelta(machine_info[config.columns.WORK_START_TIME] * config.constants.TIME_MULTIPLIER, unit='m')
        )
        machine_info[config.columns.WORK_END_TIME] = (
            self.base_date +
            pd.to_timedelta(machine_info[config.columns.WORK_END_TIME] * config.constants.TIME_MULTIPLIER, unit='m')
        )

        return machine_info

    def decorate_with_process_details(self, machine_info, process_detail_df):
        """
        공정 상세 정보로 호기 정보 장식

        Args:
            machine_info (pd.DataFrame): 기본 호기 정보
            process_detail_df (pd.DataFrame): Aging 포함 긴 형식 결과

        Returns:
            pd.DataFrame: 장식된 호기 정보
                - PO_NO, GITEM, FABRIC_WIDTH, PRODUCTION_LENGTH
                - CHEMICAL_LIST, DUE_DATE (리스트 형태)

        (MachineScheduleProcessor.machine_info_decorate 로직 기반)
        """
        machine_info = machine_info.copy()

        # 각 작업(PROCESS_ID)에 대해 상세 정보 조회
        po_no_list = []
        gitem_list = []
        width_list = []
        length_list = []
        chemical_list = []
        duedate_list = []

        for idx, row in machine_info.iterrows():
            process_id = row[config.columns.PROCESS_ID]

            # process_detail_df에서 해당 작업 필터링
            filtered = process_detail_df[
                process_detail_df[config.columns.PROCESS_ID] == process_id
            ]

            if filtered.empty:
                # Aging 노드이거나 매칭 실패
                po_no_list.append([])
                gitem_list.append([])
                width_list.append([])
                length_list.append([])
                chemical_list.append([])
                duedate_list.append([])
                continue

            # 각 컬럼별로 리스트 추출
            po_no_list.append(filtered[config.columns.PO_NO].tolist())
            gitem_list.append(filtered[config.columns.GITEM].tolist())
            width_list.append(filtered[config.columns.FABRIC_WIDTH].tolist())
            length_list.append(filtered[config.columns.PRODUCTION_LENGTH].tolist())
            chemical_list.append(filtered[config.columns.CHEMICAL_LIST].tolist())
            duedate_list.append(filtered[config.columns.DUE_DATE].tolist())

        # 리스트 정리 함수 (헬퍼)
        def unique_or_single(lst):
            if not lst:
                return None
            unique_vals = list(dict.fromkeys([x for x in lst if pd.notna(x)]))
            return unique_vals[0] if len(unique_vals) == 1 else (unique_vals or None)

        def timestamps_to_dates(lst):
            if not lst:
                return []
            return [
                ts.strftime('%Y-%m-%d') if isinstance(ts, pd.Timestamp) else str(ts)
                for ts in lst if pd.notna(ts)
            ]

        # 컬럼 추가
        machine_info[config.columns.PO_NO] = po_no_list
        machine_info[config.columns.GITEM] = [unique_or_single(x) for x in gitem_list]
        machine_info[config.columns.FABRIC_WIDTH] = [unique_or_single(x) for x in width_list]
        machine_info[config.columns.PRODUCTION_LENGTH] = [unique_or_single(x) for x in length_list]
        machine_info[config.columns.CHEMICAL_LIST] = [unique_or_single(x) for x in chemical_list]
        machine_info[config.columns.DUE_DATE] = [timestamps_to_dates(sublist) for sublist in duedate_list]

        return machine_info

    def add_gitem_names(self, machine_info, original_order):
        """
        GITEM명 매핑 및 추가 컬럼 생성

        Args:
            machine_info (pd.DataFrame): 장식된 호기 정보
            original_order (pd.DataFrame): 원본 주문 데이터

        Returns:
            pd.DataFrame: 최종 호기 정보
                - GITEM_NAME 추가
                - OPERATION (공정명) 추가
                - WORK_TIME (작업시간) 추가

        참고: src/results/__init__.py:111-129
        """
        # GITEM명 매핑
        order_with_names = original_order[[
            config.columns.GITEM,
            config.columns.GITEM_NAME
        ]].drop_duplicates()

        machine_info = pd.merge(
            machine_info,
            order_with_names,
            on=config.columns.GITEM,
            how='left'
        )

        # 추가 컬럼 생성
        machine_info[config.columns.OPERATION] = (
            machine_info[config.columns.PROCESS_ID].str.split('_').str[1]
        )
        machine_info[config.columns.WORK_TIME] = (
            machine_info[config.columns.WORK_END_TIME] -
            machine_info[config.columns.WORK_START_TIME]
        )

        print(machine_info.info())

        return machine_info

    def create_complete_machine_info(
        self,
        machine_schedule_df,
        process_detail_df,
        original_order
    ):
        """
        호기 정보 전체 파이프라인 실행 (원스톱)

        Args:
            machine_schedule_df (pd.DataFrame): 기계 스케줄
            process_detail_df (pd.DataFrame): Aging 포함 긴 형식 결과
            original_order (pd.DataFrame): 원본 주문 데이터

        Returns:
            pd.DataFrame: 완성된 호기_정보 시트 데이터
        """
        machine_info = self.build_machine_info(machine_schedule_df)
        machine_info = self.decorate_with_process_details(machine_info, process_detail_df)
        machine_info = self.add_gitem_names(machine_info, original_order)
        return machine_info
