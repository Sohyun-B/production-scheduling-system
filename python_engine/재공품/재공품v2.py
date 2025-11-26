import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ------------------------------------------
# 1. 샘플 데이터 생성
# ------------------------------------------

# (1) 운영 데이터 (df_ops)
# 상황: 같은 아이템(32571)을 사용하는 두 개의 주문(Order_Fast, Order_Slow)이 있음
# Order_Fast가 날짜가 더 급함.
df_ops = pd.read_excel("sequence_seperated_order_after_sequencing.xlsx")

print("=== 주문 데이터 (df_ops) ===")
print(df_ops)

# (2) 마스터 데이터 (df_master) - 수율 정보

df_master = pd.read_csv("yield_ratio.csv")
print("\n=== 공정별 수율 데이터 (df_master) ===")
print(df_master)

# (3) 재고 데이터 (df_inventory)
# **중요**: product_ID 컬럼이 없습니다. gitemno 기준으로 관리됩니다.
# 상황: 공정2(Seq 2)를 완료한 재고가 100개 있음. (필요량보다 적게 설정하여 쟁탈전 유도)

df_inventory = pd.read_excel("재공품.xlsx")

print("\n=== 공정별 수율 데이터 (df_master) ===")
print(df_master)

# ------------------------------------------
# 2. 데이터 전처리
# ------------------------------------------

# Merge
df_merged = pd.merge(df_ops, df_master, on=['gitemno', 'proccode', 'procseq'], how='left')
df_merged['product_ratio'] = df_merged['product_ratio'].fillna(1.0)

# ------------------------------------------
# 3. 핵심 로직: 우선순위 할당 스케줄러
# ------------------------------------------

def calculate_priority_schedule(merged_df, inventory_df):
    schedule_results = []
    
    # [Step 1] 재고를 '실시간 차감 가능한' 딕셔너리로 변환
    # Key: (gitemno, completed_procseq) -> Value: length
    # 이렇게 해야 Loop 돌면서 실시간으로 재고를 깎아먹을 수 있음
    inventory_map = {}
    for _, row in inventory_df.iterrows():
        key = (row['gitemno'], row['completed_procseq'])
        inventory_map[key] = inventory_map.get(key, 0) + row['length']

    # [Step 2] 주문 우선순위 정렬 (Due Date 오름차순 -> 급한 놈이 먼저)
    # product_ID 별 대표 정보(duedate)를 뽑아서 정렬
    order_priority = merged_df[['product_ID', 'duedate']].drop_duplicates().sort_values('duedate')
    
    print(f"Build Order: {order_priority['product_ID'].tolist()} (날짜순 정렬됨)")

    # [Step 3] 정렬된 주문 순서대로 루프 실행
    for pid in order_priority['product_ID']:
        # 해당 주문의 데이터만 추출
        group = merged_df[merged_df['product_ID'] == pid]
        gitemno = group['gitemno'].iloc[0] # 이 주문이 사용하는 아이템 번호
        
        final_target_len = group['production_length'].max()
        current_request_length = final_target_len
        duedate_str = group['duedate'].iloc[0].strftime('%Y-%m-%d')
        
        print(f"\n>> 처리중: {pid} (납기: {duedate_str})")

        # 공정 역순 정렬 (4 -> 3 -> 2 -> 1)
        proc_list = group.sort_values('procseq', ascending=False).to_dict('records')
        
        for i, row in enumerate(proc_list):
            seq = row['procseq']
            curr_ratio = row['product_ratio']
            proc_code = row['proccode']
            
            # 배수 계산
            if i == 0: next_ratio = 1.0
            else: next_ratio = proc_list[i-1]['product_ratio']
            step_multiplier = curr_ratio / next_ratio

            # 이론상 작업량
            theoretical_workload = final_target_len * curr_ratio

            # 필요 투입량 계산
            required_input_gross = current_request_length * step_multiplier
            
            # ---------------------------------------------------------
            # [Core] 전역 재고 맵(inventory_map)에서 조회 및 차감
            # ---------------------------------------------------------
            input_source_seq = seq - 1
            inv_key = (gitemno, input_source_seq)
            
            current_stock = inventory_map.get(inv_key, 0.0) # 현재 남은 재고 확인
            
            # 재고 사용량 결정 (필요한 만큼 쓰거나, 없으면 있는 만큼만)
            stock_to_use = min(required_input_gross, current_stock)
            
            # **중요** 재고 차감 반영 (다음 주문은 줄어든 재고를 보게 됨)
            if stock_to_use > 0:
                inventory_map[inv_key] -= stock_to_use
            
            # Net Input 계산
            net_input_request = required_input_gross - stock_to_use
            
            # 통계 계산
            real_workload = net_input_request + stock_to_use
            work_saved = theoretical_workload - real_workload

            schedule_results.append({
                '우선순위': '1순위(급함)' if pid == 'PID_Fast' else '2순위(느림)', # 시각화용
                'product_ID': pid,
                'duedate': duedate_str,
                '공정명': proc_code,
                '순서': seq,
                '이론상_작업': round(theoretical_workload, 1),
                '재고_사용': round(stock_to_use, 1),
                '실제_요청': round(net_input_request, 1),
                '▼절감량': round(work_saved, 1)
            })
            
            current_request_length = net_input_request

    return pd.DataFrame(schedule_results)

# ------------------------------------------
# 4. 실행 및 결과
# ------------------------------------------

df_final = calculate_priority_schedule(df_merged, df_inventory)

# 보기 좋게 출력
cols = ['우선순위', 'product_ID', 'duedate', '순서', '이론상_작업', '재고_사용', '실제_요청', '▼절감량']
print("\n========== [ 납기 우선순위 할당 결과 ] ==========")
print(df_final[cols].to_string(index=False))