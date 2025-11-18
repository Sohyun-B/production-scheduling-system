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
from src.order_sequencing import generate_order_sequences
from src.yield_management import yield_prediction
from src.dag_management import create_complete_dag_system
from src.dag_management.dag_dataframe import parse_aging_requirements
from src.scheduler import run_scheduler_pipeline
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
        input_file = "data/input/생산계획 입력정보.xlsx"

        # 각 시트에서 데이터 읽기 (GITEM과 OPERATION_CODE는 문자열로 고정)
        order_df = pd.read_excel(input_file, sheet_name="tb_polist", dtype={config.columns.GITEM: str}, parse_dates=[config.columns.DUE_DATE])
        gitem_sitem_df = pd.read_excel(input_file, sheet_name="tb_itemspec", dtype={config.columns.GITEM: str})
        linespeed_df = pd.read_excel(input_file, sheet_name="tb_linespeed", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
        operation_df = pd.read_excel(input_file, sheet_name="tb_itemproc", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
        yield_df = pd.read_excel(input_file, sheet_name="tb_productionyield", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
        chemical_df = pd.read_excel(input_file, sheet_name="tb_chemical", dtype={config.columns.GITEM: str, config.columns.OPERATION_CODE: str})
        operation_delay_df = pd.read_excel(input_file, sheet_name="tb_changetime")
        width_change_df = pd.read_excel(input_file, sheet_name="tb_changewidth")


        aging_gitem = pd.read_excel(input_file, sheet_name="tb_agingtime_gitem", dtype={config.columns.GITEM: str})
        aging_gbn = pd.read_excel(input_file, sheet_name="tb_agingtime_gbn")
        global_machine_limit_raw = pd.read_excel("data/input/tb_commomconstraint.xlsx")

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
        chemical_df=chemical_df,
        operation_delay_df=operation_delay_df,
        width_change_df=width_change_df,
        gitem_sitem_df=gitem_sitem_df,
        aging_gitem_df=aging_gitem,
        aging_gbn_df=aging_gbn,
        global_machine_limit_df=global_machine_limit_raw,
        linespeed_period=linespeed_period,
        yield_period=yield_period,
        validate=True,
        save_output=True
    )

    # 전처리된 데이터 추출
    linespeed = processed_data['linespeed']
    operation_types = processed_data['operation_types']
    operation_seperated_sequence = processed_data['operation_sequence']
    yield_data = processed_data['yield_data']
    chemical_data = processed_data['chemical_data']
    operation_delay_df = processed_data['operation_delay']
    width_change_df = processed_data['width_change']
    order = processed_data['order_data']
    aging_df = processed_data['aging_data']
    global_machine_limit = processed_data['global_machine_limit']

    # 시나리오 파일 로딩 (Local 제약조건 + 기계 할당)
    local_machine_limit = pd.read_excel("data/input/시나리오_공정제약조건.xlsx", sheet_name="machine_limit")
    machine_allocate = pd.read_excel("data/input/시나리오_공정제약조건.xlsx", sheet_name="machine_allocate")
    machine_rest = pd.read_excel("data/input/시나리오_공정제약조건.xlsx", sheet_name="machine_rest", parse_dates=[config.columns.MACHINE_REST_START, config.columns.MACHINE_REST_END])



    print("[30%] Validation 완료!")

    # === 기계 마스터 정보 로딩 (Validation 이후) ===
    print("[31%] 기계 마스터 정보 로딩 중...")
    machine_master_file = "data/input/machine_master_info.xlsx"
    machine_master_info_df = pd.read_excel(
        machine_master_file,
        dtype={config.columns.MACHINE_CODE: str}
    )
    print(f"[INFO] 기계 마스터 정보 로딩 완료: {len(machine_master_info_df)}대")

    # MachineMapper 객체 생성
    from src.utils import MachineMapper
    machine_mapper = MachineMapper(machine_master_info_df)
    print(f"[INFO] MachineMapper 초기화 완료: {machine_mapper}")

    # === 2단계: 주문 시퀀스 생성 (Order Sequencing) ===
    print("[30%] 주문 시퀀스 생성 중...")
    sequence_seperated_order, linespeed, unable_gitems, unable_order, unable_details = generate_order_sequences(
        order, operation_seperated_sequence, operation_types, local_machine_limit, global_machine_limit, machine_allocate, linespeed, chemical_data)
    
    # === 3단계: 수율 예측 ===
    print("[35%] 수율 예측 처리 중...")
    sequence_seperated_order = yield_prediction(
        yield_data, sequence_seperated_order
    )

    # === 4단계: DAG 생성 ===
    # NEW: aging 요구사항 파싱
    print("[38%] Aging 요구사항 파싱 중...")
    aging_map = parse_aging_requirements(aging_df, sequence_seperated_order)
    print(f"[INFO] {len(aging_map)}개의 aging 노드 생성 예정")



    # DAG 생성 (aging_map 전달)
    dag_df, opnode_dict, manager, machine_dict, merged_df = create_complete_dag_system(
        sequence_seperated_order, linespeed, machine_mapper, aging_map=aging_map)

    print(f"[50%] DAG 시스템 생성 완료 - 노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")

    # === 5단계: 스케줄링 실행 ===
    print("[60%] 스케줄링 알고리즘 초기화 중...")
    try:
        # 스케줄링 준비 및 실행 모듈 호출

        result, scheduler = run_scheduler_pipeline(
            dag_df=dag_df,
            sequence_seperated_order=sequence_seperated_order,
            width_change_df=width_change_df,
            machine_mapper=machine_mapper,
            opnode_dict=opnode_dict,
            operation_delay_df=operation_delay_df,
            machine_dict=machine_dict,
            machine_rest=machine_rest,
            base_date=base_date,
            manager=manager,
            window_days=window_days,
        )
        
        # 원본 결과 저장 (임시)
        excel_filename = "data/output/result.xlsx"
        result.to_excel(excel_filename, index=False)
        print(f"[저장] 원본 결과를 '{excel_filename}'에 저장 완료")


        # === 6단계: 결과 후처리 (results 모듈 사용) ===
        print(f"[80%] 스케줄링 완료! 결과 후처리 시작...")

        # create_results 함수로 모든 후처리 위임
        final_results = create_results(
            raw_scheduling_result=result,
            merged_df=merged_df,
            original_order=order,
            sequence_seperated_order=sequence_seperated_order,
            machine_mapper=machine_mapper,
            base_date=base_date,
            scheduler=scheduler
        )
        
        # 기본 결과 출력
        print(f"\n[결과 요약]")
        print(f"order 수 : {len(order)}")
        print(f"실제 수행한 order: {len(order) - len(unable_order)}")
        print(f"사용 불가능한 gitem: {len(unable_gitems)}")
        print(f"makespan: {final_results['metadata']['actual_makespan']}")

        # 성과 지표 출력
        metrics = final_results['performance_metrics']
        print(f"\n[스케줄링 성과 지표]")
        print(f"PO제품수: {metrics['po_count']}개")
        print(f"총 생산시간: {metrics['makespan_hours']:.2f}시간")
        print(f"납기준수율: {metrics['ontime_delivery_rate']:.2f}%")
        print(f"장비가동률(평균): {metrics['avg_utilization']:.2f}%")

        # 지각 요약
        lateness = final_results['lateness_summary']
        print(f"\n[지각 현황]")
        print(f"준수 주문: {lateness['ontime_orders']}개, 지각 주문: {lateness['late_orders']}개")
        if lateness['late_orders'] > 0:
            print(f"평균 지각일수 (지각 주문만): {lateness['avg_lateness_days']:.2f}일")


        
        # 최종 엑셀 파일 저장 (results 버전 - 5개 시트)
        print("[99%] 최종 Excel 파일 저장 중...")
        processed_filename = "data/output/0829 스케줄링결과.xlsx"
        with pd.ExcelWriter(processed_filename, engine="openpyxl") as writer:
            # 1. 스케줄링 성과 지표 (신규)
            pd.DataFrame(final_results['performance_summary']).to_excel(
                writer, sheet_name="스케줄링_성과_지표", index=False
            )

            # 2. 호기_정보 (기존 유지)
            pd.DataFrame(final_results['machine_info']).to_excel(
                writer, sheet_name="호기_정보", index=False
            )

            # 3. 장비별_상세_성과 (신규)
            pd.DataFrame(final_results['machine_detailed_performance']).to_excel(
                writer, sheet_name="장비별_상세_성과", index=False
            )

            # 4. 주문_지각_정보 (신규)
            pd.DataFrame(final_results['order_lateness_report']).to_excel(
                writer, sheet_name="주문_지각_정보", index=False
            )

            # 5. 간격_분석 (기존 detailed_gaps 개선)
            pd.DataFrame(final_results['gap_analysis']).to_excel(
                writer, sheet_name="간격_분석", index=False
            )

        print(f"[저장] 가공된 결과를 '{processed_filename}'에 저장 완료")
        print(f"[저장] 5개 시트: 스케줄링_성과_지표, 호기_정보, 장비별_상세_성과, 주문_지각_정보, 간격_분석")
        
        # 최종 완료
        print("[100%] 스케줄링 완료! 모든 결과 파일 저장 완료")

        # 배합액 선택 통계
        chemical_selected_count = sum(1 for node_info in opnode_dict.values()
                                     if node_info.get('SELECTED_CHEMICAL') is not None)
        chemical_none_count = len(opnode_dict) - chemical_selected_count
        print(f"\n[배합액] 선택된 노드: {chemical_selected_count}개, None인 노드: {chemical_none_count}개")


    except Exception as e:
        print(f"[ERROR] Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()