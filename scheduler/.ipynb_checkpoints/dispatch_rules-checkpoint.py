import heapq
import pandas as pd
import numpy as np
from collections import defaultdict

def create_dispatch_rule(dag_df, sequence_seperated_order):
    # --- 전처리 ---
    dag_df = pd.merge(dag_df, sequence_seperated_order[['납기일', '원단너비', 'ID']], on = 'ID', how='left')
    dag_df['CHILDREN'] = dag_df['CHILDREN'].apply(lambda x: x if isinstance(x, list) else eval(x) if isinstance(x, str) and len(x)>0 else [])
    
    # child → parent 맵, 그리고 parent → children 맵 구축
    children_map = defaultdict(list)
    parents_map = defaultdict(list)
    for idx, row in dag_df.iterrows():
        parent = row['ID']
        for child in row['CHILDREN']:
            children_map[parent].append(child)
            parents_map[child].append(parent)
    
    all_ids = set(dag_df['ID'])
    
    # 본인 기준 parents 개수 계산: 선행해야 하는 작업수
    in_degree = {}
    for idx, row in dag_df.iterrows():
        node = row['ID']
        # depth 기준으로 진입차수(선행 필요 갯수) 설정
        if row['DEPTH'] == 1:
            in_degree[node] = 0  # 바로 처리 가능
        else:
            # 자신을 child로 가지고 있는 노드 수 → 부모 수
            in_degree[node] = len(parents_map[node])
    
    # 납기일, 너비, id 정보 dict 빠르게 접근
    due_dict = dag_df.set_index('ID')['납기일'].to_dict()
    width_dict = dag_df.set_index('ID')['원단너비'].to_dict()
    
    # --- 우선순위 큐 활용 Topological Sort ---
    # heap 항목: (납기일, -원단너비, ID 순)로 heapq 사용
    ready = []
    for node in all_ids:
        if in_degree[node] == 0:
            heapq.heappush(ready, (due_dict[node], -width_dict[node], node))
    
    answer = []
    while ready:
        # 우선순위 조건대로 pop
        _, _, current = heapq.heappop(ready)
        answer.append(current)
        # current가 child로 있는 parent의 in_degree 줄이기
        for child in children_map[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                heapq.heappush(
                    ready,
                    (due_dict[child], -width_dict[child], child)
                )

    return answer, dag_df


def allocating_schedule_by_dispatching_priority(dag_df, answer, window_days=5, manager=None):
    if manager is None:
        raise ValueError("manager 인스턴스를 반드시 전달해야 합니다.")
    
    result = [(ans, dag_df.loc[dag_df['ID'] == ans, '납기일'].values[0]) for ans in answer]

    while result:
        base_date = result[0][1]
        window_result = [
            item[0] for item in result 
            if np.abs((item[1] - base_date) / np.timedelta64(1, 'D')) <= window_days
        ]
        used_ids = manager.schedule_minimize_setup(window_result[0], window_result[1:])
        if used_ids:
            result = [item for item in result if item[0] not in used_ids]
    output_final_result = manager.to_dataframe()

    # print(f"초기 result 노드 수량: {len(result)}")
    # print(f"window_result: {window_result}")
    # print(f"window_result[0]: {window_result[0]}")
    # print(f"window_result[0] in manager.nodes? {window_result[0] in manager.nodes}")

    return output_final_result
