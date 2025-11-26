import pandas as pd

# ------------------------------------------
# 1. 데이터 설정
# ------------------------------------------
data_routing = {
    'gitemno': ['ITEM-001', 'ITEM-001', 'ITEM-001'],
    'proccode': ['공정1', '공정2', '공정3'],
    'procseq': [1, 2, 3],
    'production_ratio': [8.0, 4.0, 2.0] 
}
df_routing = pd.DataFrame(data_routing)

# 공정2 완료품 재고 100m (공정3의 Input으로 사용됨)
data_inventory = {
    'inv_id': ['INV-101'],
    'gitemno': ['ITEM-001'],
    'compl_proccode': [2], 
    'length': [100.0] 
}
df_inventory = pd.DataFrame(data_inventory)

data_order = {
    'pono': ['ORD-001'],
    'gitemno': ['ITEM-001'],
    'target_length': [100.0]
}
df_order = pd.DataFrame(data_order)

# ------------------------------------------
# 2. 로직 수정 (가동량 vs 절감량 분리)
# ------------------------------------------
def calculate_real_workload(order_df, routing_df, inventory_df):
    schedule_results = []

    for _, order in order_df.iterrows():
        target_item = order['gitemno']
        final_order_length = order['target_length']
        
        # '앞 공정에 요청해야 할 수량' (역전개 되면서 변함)
        current_request_length = final_order_length
        
        item_routing = routing_df[routing_df['gitemno'] == target_item].sort_values('procseq', ascending=False)
        routing_list = item_routing.to_dict('records')
        
        for i, process in enumerate(routing_list):
            step = process['procseq']
            current_ratio = process['production_ratio']
            proc_name = process['proccode']

            # 1. 배수(Multiplier) 계산
            if i == 0: next_step_ratio = 1.0
            else: next_step_ratio = routing_list[i-1]['production_ratio']
            step_multiplier = current_ratio / next_step_ratio

            # 2. [이론상 작업량] (재고 없을 때 정석대로 해야 하는 양)
            # 공정3: 100 * 2 = 200
            # 공정2: 100 * 4 = 400 (누적 개념이므로 최종제품 기준)
            # 공정1: 100 * 8 = 800
            theoretical_workload = final_order_length * current_ratio

            # 3. [이번 공정에 필요한 총 투입량] (앞 공정 요청분 + 재고 사용분)
            # 앞 공정에서 넘어온 요청량 * 배수
            required_input_gross = current_request_length * step_multiplier

            # 4. 재고 찾기 (이전 단계 완료품)
            input_source_step = step - 1
            available_stock = inventory_df[
                (inventory_df['gitemno'] == target_item) & 
                (inventory_df['compl_proccode'] == input_source_step)
            ]['length'].sum()

            # 5. [실제 앞 공정에 요청할 양] (Net Input)
            # 총 필요량에서 재고를 뺀 만큼만 앞 공정에 "만들어달라"고 요청
            net_input_request = max(0, required_input_gross - available_stock)
            
            # 6. [실제 공정 가동량] (Real Workload)
            # 기계가 실제로 돌리는 양 = (앞에서 만들어 온 것) + (창고에서 꺼낸 것)
            stock_used = required_input_gross - net_input_request
            real_workload = net_input_request + stock_used

            # 7. [작업 절감량]
            # 이론상 해야 할 양 - 실제로 기계 돌린 양
            work_saved = theoretical_workload - real_workload

            schedule_results.append({
                '공정명': proc_name,
                '이론상_작업량': theoretical_workload,
                '재고_투입량': stock_used,
                '전공정_생산품': net_input_request,
                '▶실제_공정가동': real_workload,     # 이 공정에서 수행하는 총 작업
                '▼작업절감량': work_saved            # 이 공정이 재고 덕분에 덜 한 작업
            })
            
            # **중요**: 앞 공정으로는 '내가 실제로 작업을 요청한 양(Net)'만 넘어갑니다.
            # 재고로 충당한 건 앞 공정이 알 필요가 없음(만들 필요 없음).
            current_request_length = net_input_request

    return pd.DataFrame(schedule_results).sort_values(['이론상_작업량'], ascending=False) # 공정1->2->3 순

# ------------------------------------------
# 3. 결과 출력
# ------------------------------------------
df_final = calculate_real_workload(df_order, df_routing, df_inventory)

cols = ['공정명', '이론상_작업량', '재고_투입량', '전공정_생산품', '▶실제_공정가동', '▼작업절감량']
print("\n========== [ 작업 부하 및 절감 분석 ] ==========")
print(df_final[cols].to_string(index=False))