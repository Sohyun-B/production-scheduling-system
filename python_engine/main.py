"""
Level 4 전략 테스트 및 결과 생성

Level 4 DispatchPriorityStrategy를 사용하여 스케줄링 결과를 생성하고
main.ipynb와 동일한 형태로 결과를 저장합니다.
"""

import pandas as pd
from datetime import datetime
import sys
import os

from config import config
from preprocessing import preprocessing
from yield_management import yield_prediction
from dag_management import run_dag_pipeline, make_process_table
from scheduler.scheduling_core import DispatchPriorityStrategy
from results import create_results
from web_progress import reporter, set_run_id

def run_level4_scheduling():
    # 웹 리포터 초기화
    run_id = os.getenv("SCHEDULE_RUN_ID")
    if run_id:
        set_run_id(run_id)
        reporter.update_progress("scheduling", 5, "Python 스케줄링 엔진 시작")
    
    base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
    window_days = config.constants.WINDOW_DAYS

    # === 1단계: 데이터 로딩 ===
    reporter.update_progress("scheduling", 10, "설정 데이터 로딩 중...")
    
    excel_data_1 = pd.read_excel(config.files.ITEM_LINESPEED_SEQUENCE, sheet_name=None)
    linespeed = excel_data_1[config.sheets.ITEM_LINESPEED]
    operation_seperated_sequence = excel_data_1[config.sheets.OPERATION_SEQUENCE]
    machine_master_info = excel_data_1[config.sheets.MACHINE_MASTER_INFO]
    yield_data = excel_data_1[config.sheets.YIELD_DATA]
    operation_sequence = excel_data_1[config.sheets.GITEM_OPERATION]
    reporter.log_detail("데이터", f"라인스피드 {len(linespeed)}개, 기계정보 {len(machine_master_info)}개")

    reporter.update_progress("scheduling", 15, "공정 분류 데이터 로딩 중...")
    excel_data_2 = pd.read_excel(config.files.OPERATION_RECLASSIFICATION, sheet_name=None)
    operation_types = excel_data_2[config.sheets.OPERATION_TYPES]
    operation_delay_df = excel_data_2[config.sheets.OPERATION_DELAY]
    width_change_df = excel_data_2[config.sheets.WIDTH_CHANGE]
    reporter.log_detail("데이터", f"공정분류 {len(operation_types)}개, 지연정보 {len(operation_delay_df)}개")

    reporter.update_progress("scheduling", 20, "기계 제약 데이터 로딩 중...")
    excel_data_3 = pd.read_excel(config.files.IMPOSSIBLE_OPERATION, sheet_name=None)
    machine_rest = excel_data_3[config.sheets.MACHINE_REST]
    machine_allocate = excel_data_3[config.sheets.MACHINE_ALLOCATE]
    machine_limit = excel_data_3[config.sheets.MACHINE_LIMIT]
    reporter.log_detail("데이터", f"기계할당 {len(machine_allocate)}개, 기계제한 {len(machine_limit)}개")

    reporter.update_progress("scheduling", 25, "주문 데이터 로딩 중...")
    order = pd.read_excel(config.files.ORDER_DATA)
    reporter.log_detail("주문", f"총 {len(order)}개 주문 로딩 완료")

    # === 2단계: 전처리 ===
    reporter.update_progress("scheduling", 30, "주문 데이터 전처리 중...")
    sequence_seperated_order, linespeed = preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
    reporter.log_detail("전처리", f"전처리 완료: {len(sequence_seperated_order)}개 작업 생성")
    
    # === 3단계: 수율 예측 ===
    reporter.update_progress("scheduling", 35, "수율 예측 처리 중...")
    yield_predictor, sequence_yield_df, sequence_seperated_order = yield_prediction(
        yield_data, operation_sequence, sequence_seperated_order
    )
    if sequence_yield_df is not None:
        reporter.log_detail("수율", f"수율 예측 완료: {len(sequence_yield_df)}개 데이터 처리")
    else:
        reporter.log_detail("수율", "수율 예측 완료: 기본 수율 사용")
    
    # === 4단계: DAG 생성 ===
    reporter.update_progress("scheduling", 40, "작업 공정 테이블 생성 중...")
    merged_df = make_process_table(sequence_seperated_order)
    reporter.log_detail("공정테이블", f"공정 테이블 생성 완료: {len(merged_df)}개 행")
    
    reporter.update_progress("scheduling", 45, "공정 계층구조 분석 중...")
    hierarchy = sorted(
        [col for col in merged_df.columns if col.endswith(config.columns.ID)],
        key=lambda x: int(x.split('공정')[0])
    )
    reporter.log_detail("계층구조", f"공정 단계: {len(hierarchy)}개 레벨")
    
    reporter.update_progress("scheduling", 50, "DAG 의존성 그래프 생성 중...")
    dag_df, opnode_dict, manager, machine_dict = run_dag_pipeline(
        merged_df, hierarchy, sequence_seperated_order, linespeed,
        machine_columns=machine_master_info[config.columns.MACHINE_CODE].values.tolist()
    )
    
    reporter.update_progress("scheduling", 55, f"DAG 생성 완료 (총 {len(dag_df)}개 노드)")
    reporter.log_detail("DAG", f"노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")
    
    # === 5단계: 스케줄링 실행 ===
    reporter.update_progress("scheduling", 60, "스케줄링 알고리즘 초기화 중...")
    try:
        # 스케줄링 준비
        from scheduler.delay_dict import DelayProcessor
        from scheduler.scheduler import Scheduler
        from scheduler.dispatch_rules import create_dispatch_rule
        
        # 디스패치 룰 생성
        reporter.update_progress("scheduling", 65, "디스패치 규칙 생성 중...")
        dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
        reporter.log_detail("디스패치", f"우선순위 규칙 생성 완료: {len(dispatch_rule_ans)}개 규칙")
        
        # 스케줄러 초기화
        reporter.update_progress("scheduling", 70, "스케줄러 초기화 및 자원 할당 중...")
        delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
        scheduler = Scheduler(machine_dict, delay_processor)
        scheduler.allocate_resources()
        scheduler.allocate_machine_downtime(machine_rest, base_date)
        reporter.log_detail("스케줄러", f"기계 자원 할당 완료, 기계 중단시간 설정 완료")
        
        # 전략 실행 (가장 시간이 오래 걸리는 단계)
        reporter.update_progress("scheduling", 75, "스케줄링 알고리즘 실행 중...")
        strategy = DispatchPriorityStrategy()
        result = strategy.execute(
            dag_manager=manager,
            scheduler=scheduler,
            dag_df=dag_df,
            priority_order=dispatch_rule_ans,
            window_days=window_days
        )
        reporter.update_progress("scheduling", 85, "스케줄링 알고리즘 실행 완료!")
        
        # depth -1인 가짜 공정 제외한 실제 makespan 계산
        actual_makespan = result[~(result['depth'] == -1)]['node_end'].max()
        total_makespan = result['node_end'].max()
        
        # === 6단계: 결과 후처리 ===
        reporter.update_progress("scheduling", 90, f"스케줄링 완료! Makespan: {actual_makespan:.1f} (총 {actual_makespan/48:.1f}일)")
        reporter.log_detail("결과", f"실제 Makespan: {actual_makespan} (가짜 공정 제외)")
        reporter.log_detail("결과", f"전체 Makespan: {total_makespan} (가짜 공정 포함)")
        reporter.log_detail("결과", f"총 소요시간: {actual_makespan / 48:.2f}일")
        
        # 원본 결과 저장
        reporter.update_progress("scheduling", 92, "원본 결과 파일 저장 중...")
        excel_filename = "result.xlsx"
        result.to_excel(excel_filename, index=False)
        reporter.log_detail("저장", f"원본 결과를 '{excel_filename}'에 저장 완료")
        
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
        reporter.log_detail("분석", f"지각 총 일 수: {results['late_days_sum']}")
        reporter.log_detail("분석", f"총 소요시간: {results['new_output_final_result']['종료시각'].max() / 48}일")
        reporter.log_detail("분석", f"총 makespan: {results['new_output_final_result']['종료시각'].max()}")
        
        # 데이터 검증
        reporter.log_detail("검증", f"원본 결과 행 수: {len(result_cleaned)}")
        reporter.log_detail("검증", f"처리된 결과 행 수: {len(results['new_output_final_result'])}")
        reporter.log_detail("검증", f"원본 최대 node_end: {result_cleaned['node_end'].max()}")
        reporter.log_detail("검증", f"처리된 최대 종료시각: {results['new_output_final_result']['종료시각'].max()}")
        
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
        reporter.update_progress("scheduling", 95, "최종 Excel 파일 저장 중...")
        processed_filename = "0829 스케줄링결과.xlsx"
        with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
            order_summary.to_excel(writer, sheet_name="주문_생산_요약본", index=False)
            order_info.to_excel(writer, sheet_name="주문_생산_정보", index=False)
            machine_info.to_excel(writer, sheet_name="호기_정보", index=False)
        
        reporter.log_detail("저장", f"가공된 결과를 '{processed_filename}'에 저장 완료")
        
        # 간트 차트 생성 및 저장
        reporter.update_progress("scheduling", 97, "간트 차트 생성 중...")
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
                reporter.log_detail("차트", f"Gantt chart를 '{gantt_filename}'에 저장 완료")
                
            elif hasattr(gantt_plot, 'write_image'):
                gantt_plot.write_image(gantt_filename)
                reporter.log_detail("차트", f"Gantt chart를 '{gantt_filename}'에 저장 완료")
                
            else:
                reporter.log_detail("차트", f"간트 차트 타입: {type(gantt_plot)}")
                
            # 파일 생성 확인
            if os.path.exists(gantt_filename):
                file_size = os.path.getsize(gantt_filename)
                reporter.log_detail("차트", f"간트 차트 파일: {gantt_filename} ({file_size} bytes)")
        except Exception as chart_error:
            reporter.log_error(f"간트 차트 생성 중 오류: {chart_error}")
        
        # 최종 완료
        reporter.update_progress("scheduling", 100, "스케줄링 완료! 모든 결과 파일 저장 완료")
        
    except Exception as e:
        reporter.log_error(f"Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()