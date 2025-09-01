"""
Level 4 전략 테스트 및 결과 생성

Level 4 DispatchPriorityStrategy를 사용하여 스케줄링 결과를 생성하고
main.ipynb와 동일한 형태로 결과를 저장합니다.
"""

import pandas as pd
from datetime import datetime

from config import config
from preprocessing import preprocessing
from yield_management import yield_prediction
from dag_management import run_dag_pipeline, make_process_table
from scheduler.scheduling_core import DispatchPriorityStrategy
from results import create_results

def run_level4_scheduling():
    base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
    window_days = config.constants.WINDOW_DAYS

    # 데이터 로딩 및 전처리
    print("📂 데이터 로딩 및 전처리 중...")
    
    excel_data_1 = pd.read_excel(config.files.ITEM_LINESPEED_SEQUENCE, sheet_name=None)
    linespeed = excel_data_1[config.sheets.ITEM_LINESPEED]
    operation_seperated_sequence = excel_data_1[config.sheets.OPERATION_SEQUENCE]
    machine_master_info = excel_data_1[config.sheets.MACHINE_MASTER_INFO]
    yield_data = excel_data_1[config.sheets.YIELD_DATA]
    operation_sequence = excel_data_1[config.sheets.GITEM_OPERATION]

    excel_data_2 = pd.read_excel(config.files.OPERATION_RECLASSIFICATION, sheet_name=None)
    operation_types = excel_data_2[config.sheets.OPERATION_TYPES]
    operation_delay_df = excel_data_2[config.sheets.OPERATION_DELAY]
    width_change_df = excel_data_2[config.sheets.WIDTH_CHANGE]

    excel_data_3 = pd.read_excel(config.files.IMPOSSIBLE_OPERATION, sheet_name=None)
    machine_rest = excel_data_3[config.sheets.MACHINE_REST]
    machine_allocate = excel_data_3[config.sheets.MACHINE_ALLOCATE]
    machine_limit = excel_data_3[config.sheets.MACHINE_LIMIT]

    order = pd.read_excel(config.files.ORDER_DATA)

    # 전처리
    sequence_seperated_order, linespeed = preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
    
    # 수율 예측
    yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(
        yield_data, operation_sequence, sequence_seperated_order
    )
    
    # DAG 생성
    merged_df = make_process_table(sequence_seperated_order)
    hierarchy = sorted(
        [col for col in merged_df.columns if col.endswith(config.columns.ID)],
        key=lambda x: int(x.split('공정')[0])
    )
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        merged_df, hierarchy, sequence_seperated_order, linespeed,
        machine_columns=machine_master_info[config.columns.MACHINE_CODE].values.tolist()
    )
    
    print("✓ 데이터 준비 완료")
    print(f"  - 총 노드 수: {len(dag_df)}")
    
    # 스케줄링 실행
    print("\n🚀 스케줄링 실행 중...")
    try:
        # 스케줄링 준비
        from scheduler.delay_dict import DelayProcessor
        from scheduler.scheduler import Scheduler
        from scheduler.dispatch_rules import create_dispatch_rule
        
        # 디스패치 룰 생성
        dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
        
        # 스케줄러 초기화
        delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
        scheduler = Scheduler(machine_dict, delay_processor)
        scheduler.allocate_resources()
        scheduler.allocate_machine_downtime(machine_rest, base_date)
        
        # 전략 실행
        strategy = DispatchPriorityStrategy()
        result = strategy.execute(
            dag_manager=manager,
            scheduler=scheduler,
            dag_df=dag_df,
            priority_order=dispatch_rule_ans,
            window_days=window_days
        )
        
        # depth -1인 가짜 공정 제외한 실제 makespan 계산
        actual_makespan = result[~(result['depth'] == -1)]['node_end'].max()
        total_makespan = result['node_end'].max()
        
        print(f"✅ 스케줄링 완료!")
        print(f"   실제 Makespan: {actual_makespan} (가짜 공정 제외)")
        print(f"   전체 Makespan: {total_makespan} (가짜 공정 포함)")
        print(f"   총 소요시간: {actual_makespan / 48:.2f}일")
        
        # 📊 원본 결과 저장
        excel_filename = "result.xlsx"
        result.to_excel(excel_filename, index=False)
        print(f"✅ 원본 결과를 '{excel_filename}'에 저장했습니다!")
        
        # 📊 가공된 결과 생성 및 저장
        # depth -1인 가짜 공정 삭제
        result_cleaned = result[~(result['depth'] == -1)]
        
        # 기계 스케줄 데이터프레임 생성
        machine_schedule_df = scheduler.create_machine_schedule_dataframe()
        # 할당 작업이 -1 공정인 경우 삭제
        machine_schedule_df = machine_schedule_df[~machine_schedule_df['할당 작업'].astype(str).str.startswith('[-1', na=False)]
        
        # create_results 함수 호출
        results = create_results(
            output_final_result=result_cleaned,
            merged_df=merged_df,
            original_order=order,
            sequence_seperated_order=sequence_seperated_order,
            machine_mapping=machine_master_info.set_index('기계인덱스')['기계코드'].to_dict(),
            machine_schedule_df=machine_schedule_df,
            base_date=base_date,
            scheduler=scheduler
        )
        
        print(f"지각 총 일 수: {results['late_days_sum']}")
        print(f"총 소요시간: {results['new_output_final_result']['종료시각'].max() / 48}일")
        print(f"총 makespan: {results['new_output_final_result']['종료시각'].max()}")
        
        # 디버그: 원본과 결과 데이터 개수 비교
        print(f"\n📊 데이터 개수 비교:")
        print(f"   원본 결과 행 수: {len(result_cleaned)}")
        print(f"   처리된 결과 행 수: {len(results['new_output_final_result'])}")
        print(f"   원본 최대 node_end: {result_cleaned['node_end'].max()}")
        print(f"   처리된 최대 종료시각: {results['new_output_final_result']['종료시각'].max()}")
        
        # GITEM명 정보는 이미 전처리된 order 데이터에 있음
        order_with_names = order[['GITEM', 'GITEM명']].drop_duplicates()
        
        # main.ipynb와 동일한 후처리 과정
        order_summary = results['new_output_final_result'].copy()
        machine_info = results['machine_info'].copy()
        order_info = results['merged_result'].copy()
        
        # 1. order_info에서 조합분류로 시작하는 컬럼 전부 삭제
        order_info = order_info.loc[:, ~order_info.columns.str.startswith("조합분류")]
        
        # 2. order_summary : 주문 생산 요약본으로 이름 변경, 종료시각 삭제
        if '종료시각' in order_summary.columns:
            order_summary = order_summary[['P/O NO', '1공정ID', '2공정ID', '3공정ID', '4공정ID', 'GITEM', '납기일', '종료날짜', '지각일수']]
        
        # 3. machine_info 처리
        # 기계인덱스를 기계코드로 매핑
        index_to_code_mapping = machine_master_info.set_index('기계인덱스')['기계코드'].to_dict()
        code_to_name_mapping = machine_master_info.set_index('기계코드')['기계이름'].to_dict()
        
        machine_info = machine_info.rename(columns = {"기계인덱스": "기계코드"})
        machine_info['기계이름'] = machine_info['기계코드'].map(code_to_name_mapping)
        
        # GITEM명 추가
        machine_info = pd.merge(machine_info, order_with_names, on='GITEM', how='left')
        
        # 추가 컬럼 생성
        machine_info['공정명'] = machine_info['ID'].str.split('_').str[1]
        machine_info['작업시간'] = machine_info['작업 종료 시간'] - machine_info['작업 시작 시간']
        
        # 최종 엑셀 파일 저장 (main.ipynb와 동일한 형태)
        processed_filename = "0829 스케줄링결과.xlsx"
        with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
            order_summary.to_excel(writer, sheet_name="주문_생산_요약본", index=False)
            order_info.to_excel(writer, sheet_name="주문_생산_정보", index=False)
            machine_info.to_excel(writer, sheet_name="호기_정보", index=False)
        
        print(f"✅ 가공된 결과를 '{processed_filename}'에 저장했습니다! (main.ipynb와 동일한 형태)")
        
        # 📈 간트 차트 생성 및 저장
        try:
            from scheduler.chart import DrawChart
            gantt = DrawChart(scheduler.Machines)
            gantt_plot = gantt.plot()
            
            # 간트 차트 파일 저장 (화면에 띄우지 않음)
            gantt_filename = "level4_gantt.png"
            
            # matplotlib 백엔드를 Agg로 설정하여 창이 뜨지 않도록 함
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            if hasattr(gantt_plot, 'savefig'):
                gantt_plot.savefig(gantt_filename, dpi=300, bbox_inches='tight')
                plt.close('all')  # 모든 figure 닫기
                print(f"✅ Level 4 Gantt chart를 '{gantt_filename}'에 저장했습니다!")
                
            elif hasattr(gantt_plot, 'write_image'):
                gantt_plot.write_image(gantt_filename)
                print(f"✅ Level 4 Gantt chart를 '{gantt_filename}'에 저장했습니다!")
                
            else:
                print(f"간트 차트 타입: {type(gantt_plot)}")
                
            # 파일 생성 확인
            import os
            if os.path.exists(gantt_filename):
                file_size = os.path.getsize(gantt_filename)
                print(f"📊 간트 차트 파일: {gantt_filename} ({file_size} bytes)")
        except Exception as chart_error:
            print(f"❌ 간트 차트 생성 중 오류: {chart_error}")
        
    except Exception as e:
        print(f"❌ Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()