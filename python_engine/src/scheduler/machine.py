class Machine_Time_window:
    """
    Machine_Time_window 클래스는 특정 기계(machine)의 공정(operation) 할당 상태와 빈 시간 창을 관리하는 클래스
    ⭐ 리팩토링: Machine_index → Machine_code

    Attributes:
        Machine_code (str): 기계의 코드 (예: 'A2020', 'C2010', 'C2250')
        assigned_task (list): 기계에 할당된 일(task)을 기록하는 리스트. (depth, ID)로 구성
        O_start (list): 각 공정(operation)의 시작 시간을 기록하는 리스트
        O_end (list): 각 공정(operation)의 종료 시간을 기록하는 리스트
        End_time (int): 기계(machine)에서 마지막 공정(operation)의 종료 시간. makespan 계산시 활용

    Note:
        operation: job-level의 일의 최소 단위.
        task: machine-level의 일의 최소 단위.
            operation_순서 != task_순서
            operation 순서: 한 작업(job)의 공정(operation)의 실행 순서 (불변)
            task 순서: 한 기계(machine)에 할당된 공정(operation)의 실행 순서 (가변)
        task는 [job_index, operation_index]의 형태로 저장
    """
    def __init__(self, Machine_index, allow_overlapping=False):
        """
        클래스 Machine_Time_window의 초기화 매서드
        ⭐ 리팩토링: Machine_index → Machine_code (파라미터명은 호환성 위해 유지)

        Args:
            Machine_index (str): 기계의 코드 (예: 'A2020', 'C2010', 'C2250')
            allow_overlapping (bool): overlapping 허용 여부 (aging 전용, 기본값 False)
        """
        self.Machine_code = Machine_index  # ★ 속성명을 Machine_code로 변경 (파라미터는 호환성 유지)
        self.assigned_task = []  # Records tasks assigned to the machine, including job index and operation index
        self.O_start = []  # Records the start time of each task's operation
        self.O_end = []  # Records the end time of each task's operation
        self.End_time = 0
        self.allow_overlapping = allow_overlapping  # NEW: Aging 기계용 overlapping 플래그



    def Empty_time_window(self):
        """
        특정 기계(machine)의 할당되지 않은 빈 시간 창을 반환
        Returns
            tuple: 다음 세가지 요소를 포함한 튜플:
            - list: time_window_start; 빈 시간 창의 시작 시간 리스트
            - list: tine_window_end; 빈 시간 창의 종료 시간 리스트
            - list: len_time_window; 빈 시간 창의 길이 리스트

        Note:
        0_end가 비어있으면 작업 할당이 되지 않았음, 해당 기계(machine)의 전체 시간 사용 가능
        """
        time_window_start = []
        time_window_end = []
        len_time_window = []
        if self.O_end is None:
            pass # 작업 할당이 아예 없으므로 구할 필요가 없다.
        elif len(self.O_end) == 1: # 기계에 작업이 하나만 할당 된 경우
            if self.O_start[0] != 0: # 첫번째 작업이 0에서 시작하지 않으면 빈 시간 존재
                time_window_start = [0] # 0애서 operation이 시작하지 않으므로 빈 시간은 0애서 시작한다
                time_window_end = [self.O_start[0]] # 빈 시간은 첫번째 작업 시작 전에 끝남.
            ###### empty window 길이를 항상 machine의 operation 수와 동일하게 하기 위해 추가
            else:
                time_window_start = [0]
                time_window_end = [0]
        elif len(self.O_end) > 1: # 기계에 작업이 2개 이상 있는 경우
            if self.O_start[0] != 0: # 첫번째 작업이 0에서 시작하지 않는 경우
                time_window_start.append(0) # 빈 시간은 0에서 시작
                time_window_end.append(self.O_start[0]) # 빈 시간은 첫번째가 시작되지 전에 끝남
            ###### empty window 길이를 항상 machine의 operation 수와 동일하게 하기 위해 추가
            else:
                time_window_start.append(0)
                time_window_end.append(0)
            #################
            # The end point of a used time window is the start point of an empty time window
            # 연속된 작업들 사이의 빈 시간 계산
            time_window_start.extend(self.O_end[:-1]) # 맨 마지막 빼고 모두 선택
            time_window_end.extend(self.O_start[1:]) # 맨 처음 말고 모두 선택
        if time_window_end is not None: # 빈 시간 창의 길이 계산
            len_time_window = [time_window_end[i] - time_window_start[i] for i in range(len(time_window_end))]
        return time_window_start, time_window_end, len_time_window



    # 새로운 operation이 기계에 들어왔을때, 기계 내 operation의 작동 순서를 오로지 작업 시작 시간이 빠른 순서로 정렬
    # Job: 추가하려는 작업의 Job 인덱스
    # M_Earliest: operation이 (이 기계 외부의 원인으로 인해) 해당 기계에서 시작할 수 있는 가장 빠른 시간
    # P_t: 이 operation이 해당 기계에서 처리되는 데 필요한 시간 (Processing Time)
    # 0_num: Job 내에서의 operation의 인덱스
    def _Input(self, depth, node_id, M_Ealiest, P_t, operation_nodes = None):
        """
        새로운 공정(operation)을 기계(machine)에 추가하고 일(task) 순서를 업데이트
        M_Earlist < O_start[i]인 곳에 insert.

        Args:
            Job (int): 해당 공정의 작업(Job) 인덱스
            M_Earlist (int): 해당 작업(job)의 이전 공정(operation)이 끝나는 시각, 해당 공정(operation)이 기계(machine)에서 시작할 수 있는 가장 빠른 시간
            P_t (int): 해당 공정(operation)이 해당 기계(machine)에서 처리되는데 필요한 시간
            O_num (int):  해당 공정(operation)의 인덱스
            operation_nodes: 3공정의 일부만 수행되는 경우 해당 2공정의 node_id

        Note:
            대부분의 경우 해당 메소드 내에서는 makespan은 계산하지 않고, empty time window가 새로운 공정의 p_t보다 큰지도 확인하지 않는다. 그저 한 기계(machine)에 할당된 공정(operation)의 순서를 정한다.
        """
        task = [depth, node_id]
        if operation_nodes:
            task = [depth, node_id, operation_nodes]

        # NEW: Overlapping 처리 (Aging 기계 전용)
        if self.allow_overlapping:
            # overlapping: 빈 시간 체크 없이 바로 추가
            self.assigned_task.append(task)
            self.O_start.append(M_Ealiest)
            self.O_end.append(M_Ealiest + P_t)
            # 정렬 유지
            self.O_start.sort()
            self.O_end.sort()
            # End_time은 가장 늦게 끝나는 시간으로 업데이트
            self.End_time = max(self.End_time, M_Ealiest + P_t)
            return

        # 기존 로직 (overlapping=False인 경우)
        if self.O_end != []: # 기존 작업이 비어있지 않다면
            if self.O_start[-1] > M_Ealiest: # 가장 늦은 시작 시간보다 지금 들어온 시작 가능 시간이 더 빠르면
                for i in range(len(self.O_end)):
                    if self.O_start[i] >= M_Ealiest: # M_Earlist가 0_start[i]보다 빨리 시작하면 insert
                        # i 번째로 실행된다는 뜻
                        self.assigned_task.insert(i, task)
                        break
            else: # 그렇지 않으면 맨 뒤 순서에 append
                self.assigned_task.append(task)
        else: # 그렇지 않으면 맨 뒤 순서에 append
            self.assigned_task.append(task)

        # Update start and end times for the task
        self.O_start.append(M_Ealiest)
        self.O_start.sort()
        self.O_end.append(M_Ealiest + P_t)
        self.O_end.sort()

        # end_time 업데이트, end_time은 makespan 계산시 사용
        self.End_time = self.O_end[-1]
        
    
    def force_Input(self, depth, node_id, start_time, end_time):
        """
        특정 시간대에 기계가 사용되지 못하게 가짜 일을 추가하는 방식
        가짜 업무의 depth는 -1
        스케줄링이 할당되기 전에 먼저 추가해야한다
        """
        self.assigned_task.append([depth, node_id])
        self.O_start.append(start_time)
        self.O_end.append(end_time)
        self.End_time = max(self.End_time, end_time)
        
        
        
    def machine_fixed_Input(self, depth, node_id, M_Ealiest, P_t, operation_nodes = None):
        """
        특정 공정을 특정 기계에 고정하여 할당. 재스케줄링에 사용하는 방식.
        이때 특정 기계의 맨 뒤에 할당한다. 

        Args:
            Job (int): 해당 공정의 작업(Job) 인덱스
            M_Earlist (int): 해당 작업(job)의 이전 공정(operation)이 끝나는 시각, 해당 공정(operation)이 기계(machine)에서 시작할 수 있는 가장 빠른 시간
            P_t (int): 해당 공정(operation)이 해당 기계(machine)에서 처리되는데 필요한 시간
            O_num (int):  해당 공정(operation)의 인덱스
            operation_nodes: 3공정의 일부만 수행되는 경우 해당 2공정의 node_id

        Note:
            대부분의 경우 해당 메소드 내에서는 makespan은 계산하지 않고, empty time window가 새로운 공정의 p_t보다 큰지도 확인하지 않는다. 그저 한 기계(machine)에 할당된 공정(operation)의 순서를 정한다.
        """
        task = [depth, node_id]
        if operation_nodes:
            task = [depth, node_id, operation_nodes]

        M_Ealiest = max(M_Ealiest, self.O_end[-1]) # 기계 맨 뒤 공정이 끝나는 시간보다 늦게 시작할 수 있으면 더 늦게 시작, 아니면 해당 기계 공정 끝나고 시작
        self.assigned_task.append(task) # 맨 뒤 순서에 append

        # Update start and end times for the task
        self.O_start.append(M_Ealiest)
        self.O_start.sort()
        self.O_end.append(M_Ealiest + P_t)
        self.O_end.sort()

        # end_time 업데이트, end_time은 makespan 계산시 사용
        self.End_time = self.O_end[-1]
        


        
