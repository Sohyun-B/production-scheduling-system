"""
Level 4 전략 테스트 및 결과 생성

Level 4 DispatchPriorityStrategy를 사용하여 스케줄링 결과를 생성하고
main.ipynb와 동일한 형태로 결과를 저장합니다.
"""

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import pandas as pd
from datetime import datetime
import json

from config import config
from src.validation import preprocess_production_data
from src.preprocessing import preprocessing
from src.yield_management import yield_prediction
from src.dag_management import create_complete_dag_system
from src.scheduler.scheduling_core import DispatchPriorityStrategy
from src.results import create_results

def run_level4_scheduling():
    # 사용자 입력으로 받는 부분
    base_date = datetime(config.constants.BASE_YEAR, config.constants.BASE_MONTH, config.constants.BASE_DAY)
    window_days = config.constants.WINDOW_DAYS
    linespeed_period = config.constants.LINESPEED_PERIOD
    yield_period = config.constants.YIELD_PERIOD

    # === Excel 파일 로딩 ===
    try:
        print("Excel 파일 로딩 중...")
        input_file = "data/input/생산계획 필요기준정보 내역-Ver4.xlsx"

        # 각 시트에서 데이터 읽기
        order_df = pd.read_excel(input_file, sheet_name="PO정보", skiprows=1)
        gitem_sitem_df = pd.read_excel(input_file, sheet_name="제품군-GITEM-SITEM", skiprows=2)
        linespeed_df = pd.read_excel(input_file, sheet_name="라인스피드-GITEM등", skiprows=5)
        operation_df = pd.read_excel(input_file, sheet_name="GITEM-공정-순서", skiprows=1)
        yield_df = pd.read_excel(input_file, sheet_name="수율-GITEM등", skiprows=5)
        mixture_df = pd.read_excel(input_file, sheet_name="배합액정보", skiprows=5)
        operation_delay_df = pd.read_excel(input_file, sheet_name="공정교체시간", skiprows=1)
        width_change_df = pd.read_excel(input_file, sheet_name="폭변경", skiprows=1)

        print("Excel 파일 로딩 완료!")

    except FileNotFoundError as e:
        print(f"오류: 파일을 찾을 수 없습니다 - {e}")
        return

    # === 1단계: Validation - 데이터 유효성 검사 및 전처리 ===
    print("[10%] 데이터 유효성 검사 및 전처리 (Validation) 시작...")
    processed_data = preprocess_production_data(
        order_df=order_df,
        linespeed_df=linespeed_df,
        operation_df=operation_df,
        yield_df=yield_df,
        mixture_df=mixture_df,
        operation_delay_df=operation_delay_df,
        width_change_df=width_change_df,
        gitem_sitem_df=gitem_sitem_df,
        linespeed_period=linespeed_period,
        yield_period=yield_period,
        validate=True, 
        save_output=False 
    )

    # 전처리된 데이터 추출
    linespeed = processed_data['linespeed']
    operation_types = processed_data['operation_types']
    operation_seperated_sequence = processed_data['operation_sequence']
    yield_data = processed_data['yield_data']
    machine_master_info = processed_data['machine_master_info']
    mixture_data = processed_data['mixture_data']
    operation_delay_df = processed_data['operation_delay']
    width_change_df = processed_data['width_change']
    machine_limit = processed_data['machine_limit']
    machine_allocate = processed_data['machine_allocate']
    machine_rest = processed_data['machine_rest']
    order = processed_data['order_data']

    # 날짜 컬럼을 datetime으로 변환
    if config.columns.DUE_DATE in order.columns:
        order[config.columns.DUE_DATE] = pd.to_datetime(order[config.columns.DUE_DATE])
    if 'dt_start' in machine_rest.columns:
        machine_rest['dt_start'] = pd.to_datetime(machine_rest['dt_start'])
    if 'dt_end' in machine_rest.columns:
        machine_rest['dt_end'] = pd.to_datetime(machine_rest['dt_end'])

    print("[30%] Validation 완료!")

    # === 2단계: 전처리 (Preprocessing) ===
    sequence_seperated_order, linespeed, unable_gitems, unable_order, unable_details = preprocessing(
        order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed, mixture_data)

    print("sequence_seperated_order 정보!!!!!!!")
    print(sequence_seperated_order.columns)

    # === 3단계: 수율 예측 ===
    print("[35%] 수율 예측 처리 중...")
    sequence_seperated_order = yield_prediction(
        yield_data, sequence_seperated_order
    )

    # === 4단계: DAG 생성 ===
    print("[40%] DAG 시스템 생성 중...")
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
        sequence_seperated_order, linespeed, machine_master_info)
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
        
        # 스케줄러 초기화
        print("[70%] 스케줄러 초기화 및 자원 할당 중...")
        print("machine rest")
        print(width_change_df[config.columns.MACHINE_CODE].values.tolist())
        print(width_change_df.columns)
        print(width_change_df)

        # MACHINE_CODE → MACHINE_INDEX dict 생성 후 공정교체시간 존재하는 기계인덱스만 가져옴
        code_to_index = dict(zip(machine_master_info[config.columns.MACHINE_CODE],
                                machine_master_info[config.columns.MACHINE_INDEX]))
        machine_index_list = width_change_df[config.columns.MACHINE_CODE].map(code_to_index).tolist() # 공정교체시간 존재하는기계인덱스 리스ㅌ

        width_change_df = pd.merge(width_change_df, machine_master_info, on = config.columns.MACHINE_CODE, how = 'left')
        delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df, machine_index_list)

        scheduler = Scheduler(machine_dict, delay_processor)
        scheduler.allocate_resources()

        print("machine rest")
        machine_rest = pd.merge(machine_rest, machine_master_info, on = config.columns.MACHINE_CODE, how = 'left')
        print(machine_rest.columns)
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

        # === 6단계: 결과 후처리 (모든 후처리 로직을 create_results에서 처리) ===
        print(f"[80%] 스케줄링 완료! 결과 후처리 시작...")
        
        # create_results 함수로 모든 후처리 위임
        final_results = create_results(
            raw_scheduling_result=result,
            merged_df=merged_df,
            original_order=order,
            sequence_seperated_order=sequence_seperated_order,
            machine_master_info=machine_master_info,
            base_date=base_date,
            scheduler=scheduler
        )
        
        # 기본 결과 출력
        print(f"order 수 : {len(order)}")
        print(f"실제 수행한 order: {len(order) - len(unable_order)}")
        print(f"사용 불가능한 gitem: {len(unable_gitems)}")
        print(f"makespan: {final_results['actual_makespan']}")
        print(f"납기준수율: {1 - (final_results['order_summary'][config.columns.LATE_DAYS] > 0).sum() / len(final_results['order_summary'])}")
        print(f"지각 주문: {(final_results['order_summary'][config.columns.LATE_DAYS] > 0).sum()}")
        # print(f"공정교체 횟수: {(final_results['order_summary']['지각일수'] > 0).sum()}")


        # print(f"[98%] 스케줄링 완료! Makespan: {final_results['actual_makespan']:.1f} (총 {final_results['actual_makespan']/48:.1f}일)")
        # print(f"[결과] 실제 Makespan: {final_results['actual_makespan']} (가짜 공정 제외)")
        # print(f"[결과] 총 소요시간: {final_results['actual_makespan'] / 48:.2f}일")
    
        # 원본 결과 저장 (임시)
        excel_filename = "data/output/result.xlsx"
        result.to_excel(excel_filename, index=False)
        print(f"[저장] 원본 결과를 '{excel_filename}'에 저장 완료")
        
        # 최종 엑셀 파일 저장 (main.ipynb와 동일한 형태)
        print("[99%] 최종 Excel 파일 저장 중...")
        processed_filename = "data/output/0829 스케줄링결과.xlsx"
        with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
            final_results['order_summary'].to_excel(writer, sheet_name="주문_생산_요약본", index=False)
            final_results['order_info'].to_excel(writer, sheet_name="주문_생산_정보", index=False)
            final_results['machine_info'].to_excel(writer, sheet_name="호기_정보", index=False)
            final_results['detailed_gaps'].to_excel(writer, sheet_name="지연시간분석", index=False)
            final_results['machine_summary'].to_excel(writer, sheet_name="지연시간호기요약", index=False)
        
        print(f"[저장] 가공된 결과를 '{processed_filename}'에 저장 완료")
        
        # === 6단계 완료: JSON 저장 (지각 정보만) ===
        stage6_data = {
            "stage": "results", 
            "data": {
                "late_days_sum": final_results['late_days_sum'],
                "late_products_count": len(final_results['late_products']),
                "late_po_numbers": final_results['late_po_numbers']
            }
        }
        
        with open("data/output/stage6_results.json", "w", encoding="utf-8") as f:
            json.dump(stage6_data, f, ensure_ascii=False, default=str)
        print("[단계6] JSON 저장 완료: data/output/stage6_results.json")
        
        # 최종 완료
        print("[100%] 스케줄링 완료! 모든 결과 파일 저장 완료")

        # 배합액 선택 통계
        mixture_selected_count = sum(1 for node_info in opnode_dict.values()
                                     if node_info.get('SELECTED_MIXTURE') is not None)
        mixture_none_count = len(opnode_dict) - mixture_selected_count
        print(f"\n[배합액] 선택된 노드: {mixture_selected_count}개, None인 노드: {mixture_none_count}개")


    except Exception as e:
        print(f"[ERROR] Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()