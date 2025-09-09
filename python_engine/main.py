"""
Level 4 전략 테스트 및 결과 생성

Level 4 DispatchPriorityStrategy를 사용하여 스케줄링 결과를 생성하고
main.ipynb와 동일한 형태로 결과를 저장합니다.
"""

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import pandas as pd
from datetime import datetime
import sys
import os
import json

from config import config
from src.preprocessing import preprocessing
from src.yield_management import yield_prediction
from src.dag_management import create_complete_dag_system
from src.scheduler.scheduling_core import DispatchPriorityStrategy
from src.results import create_results

def run_level4_scheduling():

    base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
    window_days = config.constants.WINDOW_DAYS

    # === 1단계: JSON 데이터 로딩 ===
    print("[10%] JSON 데이터 로딩 중...")
    
    # JSON 파일들에서 데이터 로딩
    try:
        print("JSON 파일에서 데이터 로딩 중...")
        
        # 1. 품목별 라인스피드 및 공정 순서 관련
        linespeed = pd.read_json(config.files.JSON_LINESPEED)
        operation_seperated_sequence = pd.read_json(config.files.JSON_OPERATION_SEQUENCE)
        machine_master_info = pd.read_json(config.files.JSON_MACHINE_INFO)
        yield_data = pd.read_json(config.files.JSON_YIELD_DATA)
        gitem_operation = pd.read_json(config.files.JSON_GITEM_OPERATION)
        
        print(f"[데이터] 라인스피드 {len(linespeed)}개, 기계정보 {len(machine_master_info)}개")
        
        # 2. 공정 재분류 내역 및 교체 시간 관련
        operation_types = pd.read_json(config.files.JSON_OPERATION_TYPES)
        operation_delay_df = pd.read_json(config.files.JSON_OPERATION_DELAY)
        width_change_df = pd.read_json(config.files.JSON_WIDTH_CHANGE)
        
        print(f"[데이터] 공정분류 {len(operation_types)}개, 지연정보 {len(operation_delay_df)}개")
        
        # 3. 불가능한 공정 입력값 관련 (날짜 컬럼 변환 필요)
        machine_rest = pd.read_json(config.files.JSON_MACHINE_REST)
        # machine_rest의 날짜 컬럼들을 datetime으로 변환
        if '시작시간' in machine_rest.columns:
            machine_rest['시작시간'] = pd.to_datetime(machine_rest['시작시간'])
        if '종료시간' in machine_rest.columns:
            machine_rest['종료시간'] = pd.to_datetime(machine_rest['종료시간'])
        
        machine_allocate = pd.read_json(config.files.JSON_MACHINE_ALLOCATE)
        machine_limit = pd.read_json(config.files.JSON_MACHINE_LIMIT)
        
        print(f"[데이터] 기계할당 {len(machine_allocate)}개, 기계제한 {len(machine_limit)}개")
        
        # 4. 주문 데이터 (날짜 컬럼 변환 필요)
        order = pd.read_json(config.files.JSON_ORDER_DATA)
        # 날짜 컬럼을 datetime으로 변환
        if config.columns.DUE_DATE in order.columns:
            order[config.columns.DUE_DATE] = pd.to_datetime(order[config.columns.DUE_DATE])
        
        print(f"[주문] 총 {len(order)}개 주문 로딩 완료")
        
    except FileNotFoundError as e:
        print(f"오류: {e}")

    # # === 1단계 완료: JSON 저장 ===
    # DB-백엔드에서 바로 전달하는 방식으로 변경 
    # import json
    # stage1_data = {
    #     "stage": "loading",
    #     "data": {
    #         "linespeed_count": len(linespeed),
    #         "machine_count": len(machine_master_info),
    #         "operation_types_count": len(operation_types),
    #         "operation_delay_count": len(operation_delay_df),
    #         "total_orders": len(order),
    #         "base_config": {
    #             "base_year": config.constants.BASE_YEAR,
    #             "base_month": config.constants.BASE_MONTH,
    #             "base_day": config.constants.BASE_DAY,
    #             "window_days": window_days
    #         }
    #     }
    # }
    
    # with open("data/output/stage1_loading.json", "w", encoding="utf-8") as f:
    #     json.dump(stage1_data, f, ensure_ascii=False, default=str)
    # print("[단계1] JSON 저장 완료: data/output/stage1_loading.json")


    # 1단계: VALIDATION

    # === 2단계: 전처리 ===
    print("[30%] 주문 데이터 전처리 중...")
    sequence_seperated_order, linespeed = preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
    print(f"[전처리] 전처리 완료: {len(sequence_seperated_order)}개 작업 생성")
    
    # === 2단계 완료: JSON 저장 ===
    stage2_data = {
        "stage": "preprocessing", 
        "data": {
            "input_orders": len(order),
            "processed_jobs": len(sequence_seperated_order),
            "machine_constraints": {
                "machine_rest": machine_rest.to_dict('records'),
                "machine_allocate": machine_allocate.to_dict('records'),
                "machine_limit": machine_limit.to_dict('records')
            }
        }
    }
    
    with open("data/output/stage2_preprocessing.json", "w", encoding="utf-8") as f:
        json.dump(stage2_data, f, ensure_ascii=False, default=str)
    print("[단계2] JSON 저장 완료: data/output/stage2_preprocessing.json")
    
    # === 3단계: 수율 예측 (3단계, 4단계 건너뛰기) ===
    print("[35%] 수율 예측 처리 중...")
    yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(
        yield_data, gitem_operation, sequence_seperated_order
    )
    
    # === 4단계: DAG 생성 ===
    print("[40%] DAG 시스템 생성 중...")
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
        sequence_seperated_order, linespeed, machine_master_info, config
    )
    print(f"[50%] DAG 시스템 생성 완료 - 노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")
    
    # === 5단계: 스케줄링 실행 ===
    print("[60%] 스케줄링 알고리즘 초기화 중...")
    try:
        # 스케줄링 준비
        from src.scheduler.delay_dict import DelayProcessor
        from src.scheduler.scheduler import Scheduler
        from src.scheduler.dispatch_rules import create_dispatch_rule
        
        # 디스패치 룰 생성
        print("[65%] 디스패치 규칙 생성 중...")
        dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
        print(f"[디스패치] 우선순위 규칙 생성 완료: {len(dispatch_rule_ans)}개 규칙")
        
        # 스케줄러 초기화
        print("[70%] 스케줄러 초기화 및 자원 할당 중...")
        delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
        scheduler = Scheduler(machine_dict, delay_processor)
        scheduler.allocate_resources()
        scheduler.allocate_machine_downtime(machine_rest, base_date)
        print("[스케줄러] 기계 자원 할당 완료, 기계 중단시간 설정 완료")
        
        # 전략 실행 (가장 시간이 오래 걸리는 단계)
        print("[75%] 스케줄링 알고리즘 실행 중...")
        strategy = DispatchPriorityStrategy()
        result = strategy.execute(
            dag_manager=manager,
            scheduler=scheduler,
            dag_df=dag_df,
            priority_order=dispatch_rule_ans,
            window_days=window_days
        )
        print("[85%] 스케줄링 알고리즘 실행 완료!")
        
        # depth -1인 가짜 공정 제외한 실제 makespan 계산
        actual_makespan = result[~(result['depth'] == -1)]['node_end'].max()
        total_makespan = result['node_end'].max()
        
        # 기계 스케줄 정보 생성 (stage5용)
        machine_schedule_df_stage5 = scheduler.create_machine_schedule_dataframe()
        # 할당 작업이 -1 공정인 경우 삭제
        machine_schedule_df_stage5 = machine_schedule_df_stage5[~machine_schedule_df_stage5['할당 작업'].astype(str).str.startswith('[-1', na=False)]
        
        # === 5단계 완료: JSON 저장 (machine_info 포함) ===
        stage5_data = {
            "stage": "scheduling",
            "data": {
                "window_days_used": window_days,
                "makespan_slots": int(actual_makespan),
                "makespan_hours": actual_makespan * 0.5,
                "total_days": (actual_makespan * 0.5) / 24,
                "processed_jobs_count": len(result[~(result['depth'] == -1)]),
                "machine_info": machine_schedule_df_stage5.to_dict('records')
            }
        }
        
        with open("data/output/stage5_scheduling.json", "w", encoding="utf-8") as f:
            json.dump(stage5_data, f, ensure_ascii=False, default=str)
        print("[단계5] JSON 저장 완료 (machine_info 포함): data/output/stage5_scheduling.json")
        
        # === 6단계: 결과 후처리 ===
        print(f"[90%] 스케줄링 완료! Makespan: {actual_makespan:.1f} (총 {actual_makespan/48:.1f}일)")
        print(f"[결과] 실제 Makespan: {actual_makespan} (가짜 공정 제외)")
        print(f"[결과] 전체 Makespan: {total_makespan} (가짜 공정 포함)")
        print(f"[결과] 총 소요시간: {actual_makespan / 48:.2f}일")
        
        # 원본 결과 저장
        print("[92%] 원본 결과 파일 저장 중...")
        excel_filename = "data/output/result.xlsx"
        result.to_excel(excel_filename, index=False)
        print(f"[저장] 원본 결과를 '{excel_filename}'에 저장 완료")
        
        # 가공된 결과 생성 및 저장
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
        
        # 결과 분석
        print(f"[분석] 지각 총 일 수: {results['late_days_sum']}")
        print(f"[분석] 총 소요시간: {results['new_output_final_result']['종료시각'].max() / 48}일")
        print(f"[분석] 총 makespan: {results['new_output_final_result']['종료시각'].max()}")
        
        # 데이터 검증
        print(f"[검증] 원본 결과 행 수: {len(result_cleaned)}")
        print(f"[검증] 처리된 결과 행 수: {len(results['new_output_final_result'])}")
        print(f"[검증] 원본 최대 node_end: {result_cleaned['node_end'].max()}")
        print(f"[검증] 처리된 최대 종료시각: {results['new_output_final_result']['종료시각'].max()}")
        
        # GITEM명 정보는 이미 전처리된 order 데이터에 있음
        order_with_names = order[['GITEM', 'GITEM명']].drop_duplicates()
        
        # main.ipynb와 동일한 후처리 과정
        order_summary = results['new_output_final_result'].copy()
        machine_info = results['machine_info'].copy()
        machine_info.to_csv("이걸로 간트만들어야함.csv", encoding='utf-8-sig')
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
        print("[95%] 최종 Excel 파일 저장 중...")
        processed_filename = "data/output/0829 스케줄링결과.xlsx"
        with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
            order_summary.to_excel(writer, sheet_name="주문_생산_요약본", index=False)
            order_info.to_excel(writer, sheet_name="주문_생산_정보", index=False)
            machine_info.to_excel(writer, sheet_name="호기_정보", index=False)
        
        print(f"[저장] 가공된 결과를 '{processed_filename}'에 저장 완료")
        
        # === 간격 분석 추가 ===
        print("[96%] 스케줄 간격 분석 중...")
        try:
            from src.results.gap_analyzer import ScheduleGapAnalyzer
            
            # 간격 분석기 생성
            gap_analyzer = ScheduleGapAnalyzer(scheduler, delay_processor)
            
            # 기계별 스케줄 결과 처리기에 간격 분석기 전달
            from src.results.machine_schedule import MachineScheduleProcessor
            processor = MachineScheduleProcessor(
                machine_master_info.set_index('기계인덱스')['기계코드'].to_dict(),
                machine_schedule_df,
                result_cleaned,
                base_date,
                gap_analyzer
            )
            
            # 간격 분석 요약 출력
            processor.print_gap_summary()
            
            # 상세 간격 분석 결과 저장
            detailed_gaps, machine_summary = processor.create_gap_analysis_report()
            if detailed_gaps is not None:
                detailed_gaps.to_excel("data/output/schedule_gaps_detailed.xlsx", index=False)
                print("[간격분석] 상세 간격 분석 결과 저장: schedule_gaps_detailed.xlsx")
            
            if machine_summary is not None:
                machine_summary.to_excel("data/output/machine_gap_summary.xlsx", index=False)
                print("[간격분석] 기계별 간격 요약 저장: machine_gap_summary.xlsx")
            
        except Exception as gap_error:
            print(f"[WARNING] 간격 분석 중 오류 (계속 진행): {gap_error}")
            gap_analyzer = None

        # 간트 차트 생성 및 저장 (간격 정보 포함)
        print("[97%] 간트 차트 생성 중...")
        gantt_filename = "data/output/level4_gantt.png"
        try:
            from src.scheduler.chart import DrawChart
            
            # 간격 분석기가 있으면 포함하여 차트 생성
            gantt = DrawChart(scheduler.Machines, gap_analyzer)
            gantt_plot = gantt.plot(show_gaps=True if gap_analyzer else False)
            
            # matplotlib 백엔드를 Agg로 설정하여 창이 뜨지 않도록 함
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            if hasattr(gantt_plot, 'savefig'):
                gantt_plot.savefig(gantt_filename, dpi=300, bbox_inches='tight')
                plt.close('all')  # 모든 figure 닫기
                print(f"[차트] Gantt chart를 '{gantt_filename}'에 저장 완료")
                
            elif hasattr(gantt_plot, 'write_image'):
                gantt_plot.write_image(gantt_filename)
                print(f"[차트] Gantt chart를 '{gantt_filename}'에 저장 완료")
                
            else:
                print(f"[차트] 간트 차트 타입: {type(gantt_plot)}")
                
            # 파일 생성 확인
            if os.path.exists(gantt_filename):
                file_size = os.path.getsize(gantt_filename)
                print(f"[차트] 간트 차트 파일: {gantt_filename} ({file_size} bytes)")
                if gap_analyzer:
                    print("[차트] 📍 빨간색: 셋업시간, 회색: 대기시간으로 표시됨")
                    
        except Exception as chart_error:
            print(f"[ERROR] 간트 차트 생성 중 오류: {chart_error}")
        
        # 지각한 제품 정보 추출
        late_products = results['new_output_final_result'][results['new_output_final_result']['지각일수'] > 0]
        late_po_numbers = late_products['P/O NO'].tolist() if len(late_products) > 0 else []
        
        # === 6단계 완료: JSON 저장 (지각 정보만) ===
        stage6_data = {
            "stage": "results",
            "data": {
                "late_days_sum": results['late_days_sum'],
                "late_products_count": len(late_products),
                "late_po_numbers": late_po_numbers
            }
        }
        
        with open("data/output/stage6_results.json", "w", encoding="utf-8") as f:
            json.dump(stage6_data, f, ensure_ascii=False, default=str)
        print("[단계6] JSON 저장 완료: data/output/stage6_results.json")
        
        # 최종 완료
        print("[100%] 스케줄링 완료! 모든 결과 파일 저장 완료")
        
    except Exception as e:
        print(f"[ERROR] Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()