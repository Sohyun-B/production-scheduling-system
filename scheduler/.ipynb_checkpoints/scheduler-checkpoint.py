from .machine import *
import pandas as pd
import math

class Scheduler:
    def __init__(self, machine_dict, delay_processor):
        """
        order: 작업 순서 정보 (데이터 구조 자유)
        """
        self.machine_dict = machine_dict # order의 machine부분만 리스트로 변경한것
        self.Machines = []
        # self.machine_numbers = 6
        self.machine_numbers = max(len(v) for v in machine_dict.values())

        self.delay_processor = delay_processor
        self.cantfind_id = [] # 주석용. 삭제예정
        self.ratio_overflow = []

    def allocate_resources(self): 
        # Machine 생성 
        self.Machines = [Machine_Time_window(Machine_index=i) 
                       for i in range(self.machine_numbers)]  


    def earliest_start(self, machine_info, machine_index, node_earliest_start, node_id):
##############
        """
        (node_id, machine_index) 필요 <_ 이걸로 machine_List 접근. -> 공정의 수행시간
        node의 earliest_start도 받아오기
        machine_index <_ machine_time_window 접근

        => input(machine_info, machine_index, node_earliest_start)
        """
        # 데이터 추출
        P_t = machine_info[machine_index]  # 해당 공정의 수행 시간
        last_O_end = node_earliest_start  # 작업의 이전 공정 종료시간
        Selected_Machine = machine_index  # 기계 인덱스
        
        # 기계 시간 정보 추출
        target_machine = self.Machines[Selected_Machine]
        M_window = target_machine.Empty_time_window()  # (시작시간, 종료시간, 구간길이)
        M_Tstart, M_Tend, M_Tlen = M_window         
        Machine_end_time = target_machine.End_time  # 기계의 최종 작업 종료시간

        # 지연을 구하기 위해 할당된 작업 불러옴
        # [depth, node_id] 형태
        target_machine_task = target_machine.assigned_task
        
        # 타켓 머신의 가장 뒤에 있는 task의 id와 현재 넣으려는 id를 기반으로 맨 뒤에 할당할 경우 지연시간 계산
        if target_machine_task:
            normal_delay = self.delay_processor.delay_calc_whole_process(node_id, target_machine_task[-1][1], Selected_Machine)
        else:
            normal_delay = 0
        
        # 기본 최소 시작시간 계산: 작업 이전 종료 vs 기계 최종 종료 + 최종 종료 이전 작업 + 딜레이
        earliest_start = max(last_O_end, Machine_end_time + normal_delay)
        
        # 빈 시간대 분석
        if M_Tlen:  # 빈 시간 창이 존재하는 경우
            for le_i in range(len(M_Tlen)):
                # 1. 빈 창 길이가 공정 시간보다 크고, 시작 시간이 작업 종료시간 이후이다. 
                if M_Tlen[le_i] >= P_t and M_Tstart[le_i] >= last_O_end:
                    # 지연 시간을 계산해도 사용 가능한지 계산

                    # 빈 창의 앞에 있는 task과 넣으려는 task의 지연 시간
                    if le_i != 0:
                        earlier_delay = self.delay_processor.delay_calc_whole_process(target_machine_task[le_i-1][1], node_id, Selected_Machine)

                    else:
                        earlier_delay = 0
                    # 빈 창의 뒤에 있는 task과 넣으려는 task의 지연 시간
                    later_delay = self.delay_processor.delay_calc_whole_process(node_id, target_machine_task[le_i][1], Selected_Machine)

                    if M_Tlen[le_i] >=  earlier_delay + P_t + later_delay: # 실제 지연 시간을 포함한 수행시간보다 빈 창이 더 큰 경우
                        earliest_start = M_Tstart[le_i] + earlier_delay
                        break
                
                # 2. 빈 창 중간에 작업 종료시간이 포함되는 경우
                if (M_Tstart[le_i] < last_O_end and (M_Tend[le_i] - last_O_end) >= P_t):
                    # 지연 시간을 계산해도 사용 가능한지 계산

                    # 빈 창의 앞에 있는 task과 넣으려는 task의 지연 시간  
                    if le_i != 0:                  
                        earlier_delay = self.delay_processor.delay_calc_whole_process(target_machine_task[le_i-1][1], node_id, Selected_Machine)
                    else:
                        earlier_delay = 0
                    # 빈 창의 뒤에 있는 task과 넣으려는 task의 지연 시간
                    later_delay = self.delay_processor.delay_calc_whole_process(node_id, target_machine_task[le_i][1], Selected_Machine)

                    # 빈 창 + 시작 지연 시간과 이전 작업 종료 시간 중 더 늦은 시간 계산 후, 실행 시간과 이후 지연시간 더해서 종료예정시각 구함 
                    # 실제 시작 시간 
                    real_earliest_start = max(M_Tstart[le_i] + earlier_delay, last_O_end)
                    if (M_Tend[le_i] - real_earliest_start) >= P_t:
                        earliest_start = real_earliest_start
                        break
        
        # 최종 종료시간 계산
        End_work_time = earliest_start + P_t
        
        return (
            earliest_start,     # M_earliest
            Selected_Machine,   # machine 번호
            P_t,                # 수행 시간
            last_O_end,         # 삽입 전 종료시간
            End_work_time       # 삽입 후 종료시간
        )



    def assign_operation(self, node_earliest_start, node_id, depth, op3node=None):

        """
        input:
            machine_info (list): node_id의 node의 machine 별 수행시간을 보여주는 1차원 리스트
            node_earliest_start: 해당 node의 parent node가 모두 끝나는 시각
            node_id: 머신에 기록용
            op3node: 들어오는 데이터가 op3node일 때만 사용되고 이외에는 None이 값. dag._check_middlegroup_operation의 결과값. 
                    [operation_length: 해당 op3node의 길이 중 현재 시행될 max_length 이하의 길이
                    operation_nodes: 해당 op3node의 부모 노드 중 현재 시행될 작업들의 선행 노드
                    node_length: op3node 원본 노드의 길이. 이 노드 길이 대비 현재 길이로 작업 시간 계산 예정

        output:
        
        """
        
        machine_info = self.machine_dict.get(node_id)
        # if depth == 3: # 3번째 공정인 경우
        #     """
        #         3번째 공정인 경우 노드의 길이를 조절할 필요 존재.
        #     """
        #     if op3node:
        #         operation_length = op3node[0] # 해당 노드 중 현재 진행되는 길이
        #         node_length = op3node[2] # 해당 노드 전체의 길이
        #         work_ratio = operation_length / node_length # 길이의 비율
        #         if work_ratio != 1: # 비율이 100%라면 모든 길이를 사용한 것이므로 별도 계산 불필요
        #             # 길이 비율에 따라 속도도 그만큼 감소하니까 속도 재계산
        #             machine_info = [x if x == 9999 else math.ceil(x * work_ratio) for x in machine_info]
        #         else:
        #             print("work ratio is 1")
                
        #         if work_ratio > 1:
        #             self.ratio_overflow.append(node_id)
        #             print("3공정의 일부의 길이가 3공정 전체의 길이보다 긴 경우")
        #             print(f"node id {node_id}일 때, ")
        #             print(f"현재 진행하는 길이 {operation_length} ")
        #             print(f"해당 노드 전체의 길이 {node_length} ")
        #             print(f"길이의 비율 {work_ratio}")
        #             print(f"machine 정보 {machine_info}")
        #             print("+++++++++++++")
        #     else:
        #         self.cantfind_id.append(node_id)
                # print(f"node id {node_id} 일때 op3node 값이 scheduler.assign_operation에 입력 안됨. 오류 발생")
        
        if not machine_info:
            print(f"Scheduler의 assign_operation에서 문제: {node_id}인 id가 없음")
            return 0
        
        ideal_machine_index = -1
        ideal_machine_processing_time = float('inf')
        best_earliest_start = float('inf')

        # 모든 기계 후보 탐색
        for machine_index, machine_processing_time in enumerate(machine_info):
            if machine_processing_time != 9999: # 0이면 수행하지 않는 기계로 판단]
                earliest_start = self.earliest_start(machine_info, machine_index, node_earliest_start, node_id)[0]  # 튜플 첫 번째 값이 시작 시간

                # 최적 기계 선정 조건
                if (earliest_start + machine_processing_time) < (best_earliest_start + ideal_machine_processing_time):
                    ideal_machine_index = machine_index
                    ideal_machine_processing_time = machine_processing_time
                    best_earliest_start = earliest_start
        

        # 작업/기계 업데이트
        # 머신 클래스 변경 필요
        if ideal_machine_index != -1:
            # if op3node:
            #     #  op3node 있을 경우 INPUT에 op3node 관련 정보 추가
            #     self.Machines[ideal_machine_index]._Input(
            #         depth,
            #         node_id,
            #         best_earliest_start,
            #         ideal_machine_processing_time,
            #         op3node[1], # 해당 op3node에 연결된 op2node 
            #     )
            # else:
                # op3node가 없을 경우 그냥 데이터 넣음.
            self.Machines[ideal_machine_index]._Input(
                depth,
                node_id,
                best_earliest_start,
                ideal_machine_processing_time,
                )
        else:
                print(f"node id: {node_id}\nmachine info{machine_info}")
                print(f"[경고] 이게 나오면 scheduler.assign_operation 관련해서 뭔가 잘못됨.")

        # 리턴값으로 노드 내용 업데이트
        return ideal_machine_index, best_earliest_start, ideal_machine_processing_time


    def force_assign_operation(self, machine_idx, node_earliest_start, node_id, depth):
    
        """
        각 기계의 작업 종료 시간을 고려하지 않고 특정 기계에 강제로 공정을 넣음. 
        
        """
        machine_info = self.machine_dict.get(node_id) # 이전 코드와 동일하게 하기 위해
        machine_processing_time = self.machine_dict.get(node_id)[machine_idx]

        if not machine_info:
            print(f"Scheduler의 force_assign_operation에서 문제: {node_id}인 id가 없음")
            return False, None, None

        if machine_processing_time != 9999: # 0이면 수행하지 않는 기계로 판단]
            earliest_start, _, processing_time = self.earliest_start(machine_info, machine_idx, node_earliest_start, node_id)[0:3]  # 튜플 첫 번째 값이 시작 시간

        # 작업/기계 업데이트
        # 머신 클래스 변경 필요
        if machine_processing_time != 9999:
            self.Machines[machine_idx]._Input(
                depth,
                node_id,
                earliest_start,
                processing_time,
                )
        else:
                # print(f"force_assign_operation에서 해당 기계에서 처리할 수 없는 공정 {node_id}삽입됨")
                return False, None, None
        # 리턴값으로 노드 내용 업데이트
        return True, earliest_start, processing_time


                    
    def print_machine_schedule(self):
        """
        머신별 스케줄 정보 출력 (기본값: self.Machines)
        
        Parameters:
            machines (list): 출력할 Machine 객체 리스트 (옵션)
        """
        target_machines = self.Machines
        
        for machine in target_machines:
            empty_slots = machine.Empty_time_window()
            print(f"Machine {machine.Machine_index} 정보:")
            print(f"- 할당 작업 목록: {machine.assigned_task}")
            print(f"- 작업 시작 시간: {machine.O_start}")
            print(f"- 작업 종료 시간: {machine.O_end}")
            print(f"- 최종 종료 시간: {machine.End_time}")
            print(f"- 빈 시간대 시작: {empty_slots[0]}")
            print(f"- 빈 시간대 종료: {empty_slots[1]}")
            print(f"- 빈 시간대 길이: {empty_slots[2]}")
            print("="*40)



    def create_machine_schedule_dataframe(self):
        """
        머신별 스케줄 정보를 데이터프레임으로 변환 (작업 단위로 행 추가)
        
        Returns:
            pandas.DataFrame: 머신 스케줄 정보가 담긴 데이터프레임
        """
        data = []
        for machine in self.Machines:
            # 머신의 각 작업에 대해 행 추가
            for task, start_time, end_time in zip(machine.assigned_task, machine.O_start, machine.O_end):
                data.append({
                    "Machine Index": machine.Machine_index,
                    "할당 작업": task,
                    "작업 시작 시간": start_time,
                    "작업 종료 시간": end_time
                })
        
        # 데이터프레임 생성
        return pd.DataFrame(data)
    
    
    def allocate_unable_machine_info(self, machine_limit, base_date):
        """
        machine_limit: 기계인덱스, 기계, 불가능한 공정, 시작시간, 종료시간
        불가능한 공정이 비어있는 경우 모든 공정을 사용 못하는 상태로 판단
        """
        
        # 시작시간 미존재시, 전체 스케줄 시작 시간으로 
        machine_limit['시작시간'].fillna(base_date)
        # 종료시간이 없는 경우, 고려 X
        machine_limit = machine_limit[ ~ machine_limit['종료시간'].isna() ]
        
        machine_limit['시작시간'] = ((pd.to_datetime(machine_limit['시작시간']) - pd.to_datetime(base_date)).dt.total_seconds() // 1800).astype(int)
        machine_limit['종료시간'] = ((pd.to_datetime(machine_limit['종료시간']) - pd.to_datetime(base_date)).dt.total_seconds() // 1800).astype(int)
            
        for idx, row in machine_limit.iterrows():
            machine_index = row['기계인덱스']
            start_time = row['시작시간']
            end_time = row['종료시간']
            self.Machines[machine_index].force_Input(-1, "DOWNTIME 기계 사용 불가 시간", start_time, end_time)   
        









