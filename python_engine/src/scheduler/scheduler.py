from .machine import *
import pandas as pd
import math
from config import config

class Scheduler:
    def __init__(self, machine_dict, delay_processor, machine_mapper):
        """
        ⭐ 리팩토링: 코드 기반 Scheduler

        Args:
            machine_dict: {node_id: {machine_code: processing_time}}
            delay_processor: 공정교체시간 계산 객체
            machine_mapper: MachineMapper 인스턴스
        """
        self.machine_dict = machine_dict
        self.machine_mapper = machine_mapper  # ★ 추가
        self.Machines = {}  # ★ 리스트 → 딕셔너리
        self.aging_machine = None  # NEW: aging 전용 기계 (별도 속성)

        # machine_numbers는 machine_mapper에서 조회
        self.machine_numbers = machine_mapper.get_machine_count()

        self.delay_processor = delay_processor
        self.cantfind_id = [] # 주석용. 삭제예정
        self.ratio_overflow = []

    def allocate_resources(self):
        """
        기계 리소스 할당 (딕셔너리 기반)
        ⭐ 리팩토링: 리스트 → 딕셔너리
        """
        # ★ 딕셔너리로 생성
        self.Machines = {}

        for machine_code in self.machine_mapper.get_all_codes():
            self.Machines[machine_code] = Machine_Time_window(
                Machine_index=machine_code  # ★ 코드 저장
            )

        # NEW: Aging 기계 생성 (별도 속성)
        self.aging_machine = Machine_Time_window(-1, allow_overlapping=True)

        print(f"[INFO] 기계 리소스 할당 완료: {len(self.Machines)}대")

    def get_machine(self, machine_code):
        """
        통합 기계 접근자 (코드 기반)
        ⭐ 리팩토링: machine_index → machine_code

        Args:
            machine_code: 기계 코드 (str, 예: 'A2020') 또는 -1 (aging)

        Returns:
            Machine_Time_window 객체
        """
        if machine_code == -1:
            return self.aging_machine
        return self.Machines[machine_code]

    def machine_earliest_start(self, machine_info, machine_code, node_earliest_start, node_id, machine_window_flag = False):
        """
        특정 기계의 최적 시작시간 계산 (코드 기반)
        ⭐ 리팩토링: machine_index → machine_code

        Args:
            machine_info: {machine_code: processing_time}
            machine_code (str): 기계 코드 (예: 'A2020')
            node_earliest_start: 노드 최초 시작 가능 시간
            node_id: 노드 ID
            machine_window_flag: 빈 시간창 사용 여부

        Returns:
            (machine_earliest_start, machine_code, P_t, last_O_end, End_work_time)
        """
        # ★ 데이터 추출 (코드 기반)
        P_t = machine_info[machine_code]  # ★ 코드로 조회
        last_O_end = node_earliest_start  # 작업의 이전 공정 종료시간
        Selected_Machine = machine_code  # ★ 코드 저장

        # ★ 기계 시간 정보 추출 (딕셔너리 접근)
        target_machine = self.Machines[machine_code]  # ★ 직접 딕셔너리 접근
        M_window = target_machine.Empty_time_window()  # (시작시간, 종료시간, 구간길이)
        M_Tstart, M_Tend, M_Tlen = M_window
        Machine_end_time = target_machine.End_time  # 기계의 최종 작업 종료시간

        # 할당된 작업 조회
        target_machine_task = target_machine.assigned_task

        # delay 계산 (machine_code 전달)
        if target_machine_task:
            normal_delay = self.delay_processor.delay_calc_whole_process(
                target_machine_task[-1][1],
                node_id,
                Selected_Machine  # ← machine_code 전달
            )
        else:
            normal_delay = 0

        # 최소 시작시간 계산
        machine_earliest_start = max(last_O_end, Machine_end_time + normal_delay)


        if machine_window_flag: # 빈 시간대 창을 분석하지 않는 경우
            End_work_time = machine_earliest_start + P_t

            return (
                machine_earliest_start,     # M_earliest
                Selected_Machine,   # ← machine_code 반환
                P_t,                # 수행 시간
                last_O_end,         # 삽입 전 종료시간
                End_work_time       # 삽입 후 종료시간
            )
        
        # 빈 시간대 분석
        if M_Tlen:  # 빈 시간 창이 존재하는 경우
            for le_i in range(len(M_Tlen)):
                # 1. 빈 창 길이가 공정 시간보다 크고, 시작 시간이 작업 종료시간 이후이다.
                if M_Tlen[le_i] >= P_t and M_Tstart[le_i] >= last_O_end:
                    # 지연 시간을 계산해도 사용 가능한지 계산

                    # 빈 창의 앞에 있는 task과 넣으려는 task의 지연 시간
                    if le_i != 0:
                        earlier_delay = self.delay_processor.delay_calc_whole_process(
                            target_machine_task[le_i-1][1], node_id, Selected_Machine  # ← machine_code
                        )
                    else:
                        earlier_delay = 0

                    # 빈 창의 뒤에 있는 task과 넣으려는 task의 지연 시간
                    later_delay = self.delay_processor.delay_calc_whole_process(
                        node_id, target_machine_task[le_i][1], Selected_Machine  # ← machine_code
                    )

                    if M_Tlen[le_i] >=  earlier_delay + P_t + later_delay: # 실제 지연 시간을 포함한 수행시간보다 빈 창이 더 큰 경우
                        machine_earliest_start = M_Tstart[le_i] + earlier_delay
                        break

                # 2. 빈 창 중간에 작업 종료시간이 포함되는 경우
                if (M_Tstart[le_i] < last_O_end and (M_Tend[le_i] - last_O_end) >= P_t):
                    # 지연 시간을 계산해도 사용 가능한지 계산

                    # 빈 창의 앞에 있는 task과 넣으려는 task의 지연 시간
                    if le_i != 0:
                        earlier_delay = self.delay_processor.delay_calc_whole_process(
                            target_machine_task[le_i-1][1], node_id, Selected_Machine  # ← machine_code
                        )
                    else:
                        earlier_delay = 0

                    # 빈 창의 뒤에 있는 task과 넣으려는 task의 지연 시간
                    later_delay = self.delay_processor.delay_calc_whole_process(
                        node_id, target_machine_task[le_i][1], Selected_Machine  # ← machine_code
                    )

                    # 빈 창 + 시작 지연 시간과 이전 작업 종료 시간 중 더 늦은 시간 계산 후, 실행 시간과 이후 지연시간 더해서 종료예정시각 구함
                    # 실제 시작 시간
                    real_machine_earliest_start = max(M_Tstart[le_i] + earlier_delay, last_O_end)
                    if (M_Tend[le_i] - real_machine_earliest_start) >= P_t:
                        machine_earliest_start = real_machine_earliest_start
                        break

        # 최종 종료시간 계산
        End_work_time = machine_earliest_start + P_t

        return (
            machine_earliest_start,     # M_earliest
            Selected_Machine,   # ← machine_code 반환
            P_t,                # 수행 시간
            last_O_end,         # 삽입 전 종료시간
            End_work_time       # 삽입 후 종료시간
        )



    def assign_operation(self, node_earliest_start, node_id, depth):
        """
        최적 기계 선택 및 작업 할당 (코드 기반)
        ⭐ 리팩토링: machine_index → machine_code

        Args:
            node_earliest_start: 노드 최초 시작 가능 시간
            node_id: 노드 ID
            depth: DAG 깊이

        Returns:
            (machine_code, start_time, processing_time)
        """
        machine_info = self.machine_dict.get(node_id)
        # machine_info = {'A2020': 120, 'C2010': 9999, 'C2250': 150}

        if not machine_info:
            print(f"[오류] 노드 {node_id}의 machine_info 없음")
            return None, None, None

        # ★ Aging 노드 감지 및 처리 ({-1: time} 구조 유지)
        is_aging = set(machine_info.keys()) == {-1}
        if is_aging:
            aging_time = machine_info[-1]
            self.aging_machine._Input(depth, node_id, node_earliest_start, aging_time)
            return -1, node_earliest_start, aging_time

        ideal_machine_code = None  # ★ 인덱스 → 코드
        ideal_machine_processing_time = float('inf')
        best_earliest_start = float('inf')

        # ★ 코드 기반 순회
        for machine_code, machine_processing_time in machine_info.items():
            if machine_processing_time != 9999:  # 9999이면 수행하지 않는 기계로 판단
                # machine_code 전달
                earliest_start = self.machine_earliest_start(
                    machine_info, machine_code, node_earliest_start, node_id
                )[0]

                # 최소 완료시간 기준 선택
                if (earliest_start + machine_processing_time) < \
                   (best_earliest_start + ideal_machine_processing_time):
                    ideal_machine_code = machine_code  # ★ 코드 저장
                    ideal_machine_processing_time = machine_processing_time
                    best_earliest_start = earliest_start

        # ★ 선택된 기계에 작업 할당 (코드 기반)
        if ideal_machine_code is not None:
            self.Machines[ideal_machine_code]._Input(  # ★ 딕셔너리 접근
                depth, node_id, best_earliest_start, ideal_machine_processing_time
            )
            # print(f"[DEBUG] 노드 {node_id}를 기계 {ideal_machine_code}에 할당")  # ← 명확한 로그
        else:
            print(f"[경고] 노드 {node_id}: 사용 가능한 기계 없음")
            print(f"  machine_info: {machine_info}")

        return ideal_machine_code, best_earliest_start, ideal_machine_processing_time


    def force_assign_operation(self, machine_code, node_earliest_start, node_id, depth, machine_window_flag = False):
        """
        특정 기계에 강제 할당 (코드 기반)
        ⭐ 리팩토링: machine_idx → machine_code

        Args:
            machine_code (str): 기계 코드 (예: 'A2020')  ← 변경!
            node_earliest_start: 노드 최초 시작 가능 시간
            node_id: 노드 ID
            depth: 깊이
            machine_window_flag: 빈 시간창 사용 여부
                true일 경우 machine의 맨 뒤가 아닌 빈 쉬는 시간에는 할당하지 않음

        Returns:
            (success: bool, start_time, processing_time)
        """
        machine_info = self.machine_dict.get(node_id)

        if not machine_info:
            print(f"[오류] 노드 {node_id}의 machine_info 없음")
            return False, None, None

        # ★ 코드로 조회
        machine_processing_time = machine_info.get(machine_code, 9999)

        if machine_processing_time == 9999:
            print(f"[경고] 기계 {machine_code}에서 노드 {node_id} 처리 불가 (9999)")
            return False, None, None

        # 최적 시작시간 계산
        if machine_window_flag:
            earliest_start, _, processing_time = self.machine_earliest_start(
                machine_info, machine_code, node_earliest_start, node_id, machine_window_flag=True
            )[0:3]
        else:
            earliest_start, _, processing_time = self.machine_earliest_start(
                machine_info, machine_code, node_earliest_start, node_id
            )[0:3]

        # ★ 코드 기반 접근
        self.Machines[machine_code]._Input(depth, node_id, earliest_start, processing_time)

        # print(f"[DEBUG] 강제 할당: 노드 {node_id} → 기계 {machine_code}")

        return True, earliest_start, processing_time



    def create_machine_schedule_dataframe(self):
        """
        머신별 스케줄 정보를 데이터프레임으로 변환 (작업 단위로 행 추가)
        ⭐ 리팩토링: 딕셔너리 순회로 변경

        Returns:
            pandas.DataFrame: 머신 스케줄 정보가 담긴 데이터프레임
        """
        data = []

        # ★ 딕셔너리 순회 (values()로 Machine_Time_window 객체 접근)
        for machine_code, machine in self.Machines.items():
            # 머신의 각 작업에 대해 행 추가
            for task, start_time, end_time in zip(machine.assigned_task, machine.O_start, machine.O_end):
                data.append({
                    config.columns.MACHINE_CODE: machine.Machine_code,  # ★ Machine_index → Machine_code
                    config.columns.ALLOCATED_WORK: task,
                    config.columns.WORK_START_TIME: start_time,
                    config.columns.WORK_END_TIME: end_time
                })

        # NEW: aging_machine 스케줄 추가
        if self.aging_machine:
            for task, start_time, end_time in zip(self.aging_machine.assigned_task, self.aging_machine.O_start, self.aging_machine.O_end):
                data.append({
                    config.columns.MACHINE_CODE: 'AGING',  # ★ -1 → 'AGING' (문자열 코드)
                    config.columns.ALLOCATED_WORK: task,
                    config.columns.WORK_START_TIME: start_time,
                    config.columns.WORK_END_TIME: end_time
                })

        # 데이터프레임 생성
        return pd.DataFrame(data)
    
    
    # def allocate_machine_downtime(self, machine_rest, base_date):
    #     """
    #     기계 휴식 시간을 DOWNTIME 가짜 공정으로 차단
        
    #     Args:
    #         machine_rest: DataFrame with columns [기계인덱스, 시작시간, 종료시간]
    #         base_date: 스케줄링 기준 날짜
    #     """
    #     return self.allocate_unable_machine_info(machine_rest, base_date)
    
    def allocate_machine_downtime(self, machine_rest, base_date):
        """
        기계 휴식 시간을 DOWNTIME 가짜 공정으로 차단
        ⭐ 리팩토링: machine_index → machine_code

        machine_rest: 기계코드, 불가능한 공정, 시작시간, 종료시간
        불가능한 공정이 비어있는 경우 모든 공정을 사용 못하는 상태로 판단
        """

        # 시작시간 미존재시, 전체 스케줄 시작 시간으로
        machine_rest[config.columns.MACHINE_REST_START].fillna(base_date)
        # 종료시간이 없는 경우, 고려 X
        machine_rest = machine_rest[ ~ machine_rest[config.columns.MACHINE_REST_END].isna() ]

        machine_rest[config.columns.MACHINE_REST_START] = ((pd.to_datetime(machine_rest[config.columns.MACHINE_REST_START]) - pd.to_datetime(base_date)).dt.total_seconds() // 1800).astype(int)
        machine_rest[config.columns.MACHINE_REST_END] = ((pd.to_datetime(machine_rest[config.columns.MACHINE_REST_END]) - pd.to_datetime(base_date)).dt.total_seconds() // 1800).astype(int)

        for idx, row in machine_rest.iterrows():
            machine_code = row[config.columns.MACHINE_CODE]  # ★ 코드로 변경
            start_time = row[config.columns.MACHINE_REST_START]
            end_time = row[config.columns.MACHINE_REST_END]
            self.Machines[machine_code].force_Input(-1, "DOWNTIME 기계 사용 불가 시간", start_time, end_time)  # ★ 딕셔너리 접근   
        









