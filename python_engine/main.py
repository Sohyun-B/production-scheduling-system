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
    # JSON 파일들에서 데이터 로딩
    try:
        # print("JSON 파일에서 데이터 로딩 중...")
        
        # # 1. 품목별 라인스피드 및 공정 순서 관련
        # linespeed = pd.read_json(config.files.JSON_LINESPEED)
        # operation_seperated_sequence = pd.read_json(config.files.JSON_OPERATION_SEQUENCE)
        # machine_master_info = pd.read_json(config.files.JSON_MACHINE_INFO)
        # yield_data = pd.read_json(config.files.JSON_YIELD_DATA)
        # gitem_operation = pd.read_json(config.files.JSON_GITEM_OPERATION)
        
        # # 2. 공정 재분류 내역 및 교체 시간 관련ㄴ
        # operation_types = pd.read_json(config.files.JSON_OPERATION_TYPES)
        # operation_delay_df = pd.read_json(config.files.JSON_OPERATION_DELAY)
        # width_change_df = pd.read_json(config.files.JSON_WIDTH_CHANGE)
    
        # # 3. 불가능한 공정 입력값 관련 (날짜 컬럼 변환 필요)
        # machine_rest = pd.read_json(config.files.JSON_MACHINE_REST)
        # # machine_rest의 날짜 컬럼들을 datetime으로 변환
        # if '시작시간' in machine_rest.columns:
        #     machine_rest['시작시간'] = pd.to_datetime(machine_rest['시작시간'])
        # if '종료시간' in machine_rest.columns:
        #     machine_rest['종료시간'] = pd.to_datetime(machine_rest['종료시간'])
        
        # machine_allocate = pd.read_json(config.files.JSON_MACHINE_ALLOCATE)
        # machine_limit = pd.read_json(config.files.JSON_MACHINE_LIMIT)
        
        # # 4. 주문 데이터 (날짜 컬럼 변환 필요)
        # order = pd.read_json(config.files.JSON_ORDER_DATA)

        linespeed = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "linespeed", skiprows=[0])
        linespeed = linespeed.drop(columns = {"영문명"})

        operation_seperated_sequence = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "operation_sequence", skiprows=[0])
        operation_seperated_sequence = operation_seperated_sequence.drop(columns = {"영문명"})
        machine_master_info = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "machine_master_info", skiprows=[0])
        machine_master_info = machine_master_info.drop(columns = {"영문명"})
        yield_data = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "yield_data", skiprows=[0])
        yield_data = yield_data.drop(columns = {"영문명"})
        gitem_operation = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "gitem_operation", skiprows=[0])
        gitem_operation = gitem_operation.drop(columns = {"영문명"})
        
        # 2. 공정 재분류 내역 및 교체 시간 관련
        operation_types = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "operation_types", skiprows=[0])
        operation_types = operation_types.drop(columns = {"영문명"})
        operation_delay_df = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "operation_delay", skiprows=[0])
        operation_delay_df = operation_delay_df.drop(columns = {"영문명"})
        width_change_df = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "width_change", skiprows=[0])
        width_change_df = width_change_df.drop(columns = {"영문명"})

        machine_allocate = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "machine_allocate", skiprows=[0])
        machine_rest = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "machine_rest", skiprows=[0])
        machine_limit = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "machine_limit", skiprows=[0])
        if 'dt_start' in machine_rest.columns:
            machine_rest['dt_start'] = pd.to_datetime(machine_rest['dt_start'])
        if 'dt_end' in machine_rest.columns:
            machine_rest['dt_end'] = pd.to_datetime(machine_rest['dt_end'])

        order = pd.read_excel("data/input/생산계획_db샘플.xlsx", sheet_name = "order_data", skiprows=[0])
        order = order.drop(columns = {"영문명"})


        # 날짜 컬럼을 datetime으로 변환
        if config.columns.DUE_DATE in order.columns:
            order[config.columns.DUE_DATE] = pd.to_datetime(order[config.columns.DUE_DATE])
        
    except FileNotFoundError as e:
        print(f"오류: {e}")

    # 1단계: VALIDATION

    # === 2단계: 전처리 ===
    sequence_seperated_order, linespeed, unable_gitems, unable_order, unable_details = preprocessing(
        order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed)
    

    # === 2단계 완료: JSON 저장 ===
    from src.web_interface.stage_formatters import StageDataExtractor
    
    stage2_data = StageDataExtractor.extract_stage2_data(
        order=order,
        sequence_seperated_order=sequence_seperated_order, 
        unable_gitems=unable_gitems,
        unable_order=unable_order,
        unable_details=unable_details
    )
    
    # stage_formatters에서 처리된 결과를 CSV로 저장
    if stage2_data['data']['excluded_orders']:
        processed_df = pd.DataFrame(stage2_data['data']['excluded_orders'])
        processed_df.to_csv("0910_확인용_unable_order.csv", encoding='utf-8-sig', index=False)
    
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
        width_change_df = pd.merge(width_change_df, machine_master_info, on = config.columns.MACHINE_CODE, how = 'left')
        print(machine_rest.columns)
        delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)

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
        
    except Exception as e:
        print(f"[ERROR] Level 4 스케줄링 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    run_level4_scheduling()