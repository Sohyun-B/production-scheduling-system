import os
import sys
import pandas as pd
from typing import Dict, Any, Tuple
from datetime import datetime
from loguru import logger

# Python Engine 경로 설정
ENGINE_PATH = os.path.join(os.path.dirname(__file__), '../../../python_engine')
sys.path.append(ENGINE_PATH)

class PythonEngineService:
    def __init__(self):
        self.engine_path = ENGINE_PATH
        self._import_engine_modules()
    
    def _import_engine_modules(self):
        """Python Engine 모듈들을 import"""
        try:
            # 필요한 모듈들 import (main.py와 동일)
            from config import config
            from src.preprocessing import preprocessing
            from src.yield_management import yield_prediction
            from src.dag_management import create_complete_dag_system
            from src.scheduler.scheduling_core import DispatchPriorityStrategy
            
            # 모듈들을 인스턴스 변수로 저장
            self.config = config
            self.preprocessing = preprocessing
            self.yield_prediction = yield_prediction
            self.create_complete_dag_system = create_complete_dag_system
            self.DispatchPriorityStrategy = DispatchPriorityStrategy
            
            logger.info("Python Engine 모듈 import 완료")
        except ImportError as e:
            logger.error(f"Python Engine 모듈 import 실패: {e}")
            raise
    
    def validate_loaded_data(self, loaded_data: Dict[str, Any], session_id: str, 
                           window_days: int = 5, base_date: str = None, 
                           yield_period: int = 6) -> Dict[str, Any]:
        """
        Node.js에서 로드된 데이터를 검증 (JSON 로딩은 Node.js에서 처리)
        """
        try:
            logger.info(f"로드된 데이터 검증 시작: {session_id}")
            
            validation_result = {
                "session_id": session_id,
                "window_days": window_days,
                "base_date": base_date,
                "yield_period": yield_period,
                "validation_status": "success",
                "errors": [],
                "warnings": []
            }
            
            # 필수 데이터 키 검증
            required_keys = ["order", "linespeed", "operation_seperated_sequence", 
                           "machine_master_info", "yield_data", "gitem_operation", 
                           "operation_types", "operation_delay_df", "width_change_df", 
                           "machine_rest", "machine_allocate", "machine_limit"]
            
            missing_keys = [key for key in required_keys if key not in loaded_data]
            if missing_keys:
                validation_result["validation_status"] = "error"
                validation_result["errors"].append(f"필수 데이터 누락: {missing_keys}")
                logger.error(f"필수 데이터 누락: {missing_keys}")
            
            # 데이터 타입 및 내용 검증
            if loaded_data.get("order"):
                order_data = loaded_data["order"]
                if isinstance(order_data, list) and len(order_data) > 0:
                    validation_result["total_orders"] = len(order_data)
                    logger.info(f"주문 데이터 검증 완료: {len(order_data)}개 레코드")
                else:
                    validation_result["warnings"].append("주문 데이터가 비어있습니다.")
            else:
                validation_result["errors"].append("주문 데이터가 없습니다.")
            
            if loaded_data.get("linespeed"):
                linespeed_data = loaded_data["linespeed"]
                if isinstance(linespeed_data, list):
                    validation_result["total_linespeed"] = len(linespeed_data)
            
            if loaded_data.get("machine_master_info"):
                machine_data = loaded_data["machine_master_info"]
                if isinstance(machine_data, list):
                    validation_result["total_machines"] = len(machine_data)
            
            # 검증 결과 저장
            validation_result["loaded_data"] = loaded_data
            
            if validation_result["errors"]:
                validation_result["validation_status"] = "error"
            elif validation_result["warnings"]:
                validation_result["validation_status"] = "warning"
            
            logger.info(f"로드된 데이터 검증 완료: {validation_result['validation_status']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"로드된 데이터 검증 실패: {e}")
            return {
                "validation_status": "error",
                "message": f"데이터 검증 실패: {str(e)}",
                "loaded_data": loaded_data,
                "errors": [str(e)]
            }
    
    def run_preprocessing(self, order_data: list, operation_data: list, 
                         operation_types: list, machine_limit: list, 
                         machine_allocate: list, linespeed: list) -> Tuple[Any, Any]:
        """
        2단계: 전처리 실행 (main.py와 동일)
        """
        try:
            logger.info("전처리 시작")
            
            # DataFrame으로 변환
            order_df = pd.DataFrame(order_data)
            operation_seperated_sequence = pd.DataFrame(operation_data)
            operation_types_df = pd.DataFrame(operation_types)
            machine_limit_df = pd.DataFrame(machine_limit)
            machine_allocate_df = pd.DataFrame(machine_allocate)
            linespeed_df = pd.DataFrame(linespeed)
            
            # GITEM 컬럼을 숫자로 보장 (main.py와 동일)
            if 'GITEM' in order_df.columns:
                order_df['GITEM'] = pd.to_numeric(order_df['GITEM'], errors='coerce')
                logger.info("order_df GITEM 컬럼을 숫자로 변환 완료")
            
            if 'GITEM' in operation_seperated_sequence.columns:
                operation_seperated_sequence['GITEM'] = pd.to_numeric(operation_seperated_sequence['GITEM'], errors='coerce')
                logger.info("operation_seperated_sequence GITEM 컬럼을 숫자로 변환 완료")
            
            if 'GITEM' in linespeed_df.columns:
                linespeed_df['GITEM'] = pd.to_numeric(linespeed_df['GITEM'], errors='coerce')
                logger.info("linespeed_df GITEM 컬럼을 숫자로 변환 완료")
            
            # 날짜 컬럼 변환 (main.py와 동일, timezone-naive로 강제 변환)
            if '납기일' in order_df.columns:
                order_df['납기일'] = pd.to_datetime(order_df['납기일'], utc=False)
                if order_df['납기일'].dt.tz is not None:
                    order_df['납기일'] = order_df['납기일'].dt.tz_localize(None)
                logger.info("납기일 컬럼을 timezone-naive datetime으로 변환 완료")
            elif 'due_date' in order_df.columns:
                order_df['due_date'] = pd.to_datetime(order_df['due_date'], utc=False)
                if order_df['due_date'].dt.tz is not None:
                    order_df['due_date'] = order_df['due_date'].dt.tz_localize(None)
                logger.info("due_date 컬럼을 timezone-naive datetime으로 변환 완료")
            
            # 전처리 실행
            sequence_seperated_order, linespeed = self.preprocessing(
                order_df, operation_seperated_sequence, operation_types_df,
                machine_limit_df, machine_allocate_df, linespeed_df
            )
            
            logger.info(f"전처리 완료: {len(sequence_seperated_order)}개 작업 생성")
            return sequence_seperated_order, linespeed
            
        except Exception as e:
            logger.error(f"전처리 실패: {e}")
            raise
    
    def run_yield_prediction(self, yield_data: list, gitem_operation: list, 
                           sequence_seperated_order: Any) -> Tuple[Any, Any, Any]:
        """
        3단계: 수율 예측 실행 (main.py와 동일)
        """
        try:
            logger.info("수율 예측 시작")
            
            # DataFrame으로 변환
            yield_df = pd.DataFrame(yield_data)
            gitem_operation_df = pd.DataFrame(gitem_operation)
            
            if isinstance(sequence_seperated_order, list):
                sequence_seperated_order_df = pd.DataFrame(sequence_seperated_order)
            else:
                sequence_seperated_order_df = sequence_seperated_order
            
            # 수율 예측 실행 (main.py와 동일)
            yield_predictor, sequence_yield_df, adjusted_sequence_order = self.yield_prediction(
                yield_df, gitem_operation_df, sequence_seperated_order_df
            )
            
            logger.info("수율 예측 완료")
            return yield_predictor, sequence_yield_df, adjusted_sequence_order
            
        except Exception as e:
            logger.error(f"수율 예측 실패: {e}")
            raise
    
    def run_dag_creation(self, sequence_seperated_order: Any, linespeed: Any, 
                        machine_master_info: list) -> Tuple[Any, Any, Any, Any, Any]:
        """
        4단계: DAG 생성 실행 (main.py와 동일)
        """
        try:
            logger.info("DAG 생성 시작")
            
            # DataFrame으로 변환
            if isinstance(sequence_seperated_order, list):
                sequence_seperated_order_df = pd.DataFrame(sequence_seperated_order)
            else:
                sequence_seperated_order_df = sequence_seperated_order
                
            if isinstance(linespeed, list):
                linespeed_df = pd.DataFrame(linespeed)
            else:
                linespeed_df = linespeed
                
            machine_master_df = pd.DataFrame(machine_master_info)
            
            # DAG 생성 실행
            dag_df, opnode_dict, manager, machine_dict, merged_df = self.create_complete_dag_system(
                sequence_seperated_order_df, linespeed_df, machine_master_df, self.config
            )
            
            logger.info(f"DAG 생성 완료 - 노드: {len(dag_df)}개, 기계: {len(machine_dict)}개")
            logger.info(f"opnode_dict 키 개수: {len(opnode_dict)}")
            logger.info(f"opnode_dict 키 샘플: {list(opnode_dict.keys())[:5]}")
            
            return dag_df, opnode_dict, manager, machine_dict, merged_df
            
        except Exception as e:
            logger.error(f"DAG 생성 실패: {e}")
            raise
    
    def run_scheduling(self, dag_manager: Any, dag_df: Any, sequence_seperated_order: Any,
                      operation_delay_df: list, width_change_df: list, 
                      machine_rest: list, machine_dict: Any, window_days: int,
                      opnode_dict: Any = None, base_date: str = None) -> Tuple[Any, Any, Any]:
        """
        5단계: 스케줄링 실행 (main.py와 동일)
        """
        try:
            logger.info("스케줄링 시작")
            
            # DataFrame으로 변환
            if isinstance(dag_df, list):
                dag_df = pd.DataFrame(dag_df)
            if isinstance(sequence_seperated_order, list):
                sequence_seperated_order = pd.DataFrame(sequence_seperated_order)
            
            # 컬럼명 확인 로그
            logger.info(f"sequence_seperated_order 컬럼: {list(sequence_seperated_order.columns)}")
            logger.info(f"dag_df 컬럼: {list(dag_df.columns)}")
            
            # 필요한 컬럼 확인
            required_columns = ['납기일', '원단너비', 'ID']
            missing_columns = [col for col in required_columns if col not in sequence_seperated_order.columns]
            if missing_columns:
                logger.error(f"sequence_seperated_order에서 누락된 컬럼: {missing_columns}")
                raise ValueError(f"필수 컬럼 누락: {missing_columns}")
            
            # 데이터 타입 변환 (main.py와 동일)
            if '원단너비' in sequence_seperated_order.columns:
                sequence_seperated_order['원단너비'] = pd.to_numeric(sequence_seperated_order['원단너비'], errors='coerce')
            if '납기일' in sequence_seperated_order.columns:
                # timezone-naive datetime으로 강제 변환
                sequence_seperated_order['납기일'] = pd.to_datetime(sequence_seperated_order['납기일'], errors='coerce', utc=False)
                # timezone 정보가 있다면 제거
                if sequence_seperated_order['납기일'].dt.tz is not None:
                    sequence_seperated_order['납기일'] = sequence_seperated_order['납기일'].dt.tz_localize(None)
            
            logger.info("필수 컬럼 확인 및 데이터 타입 변환 완료")
            
            # 다른 DataFrame들도 변환
            operation_delay_df = pd.DataFrame(operation_delay_df)
            width_change_df = pd.DataFrame(width_change_df)
            machine_rest_df = pd.DataFrame(machine_rest)
            
            # machine_rest의 날짜 컬럼을 timezone-naive로 강제 변환
            if '시작시간' in machine_rest_df.columns:
                machine_rest_df['시작시간'] = pd.to_datetime(machine_rest_df['시작시간'], errors='coerce', utc=False)
                if machine_rest_df['시작시간'].dt.tz is not None:
                    machine_rest_df['시작시간'] = machine_rest_df['시작시간'].dt.tz_localize(None)
            if '종료시간' in machine_rest_df.columns:
                machine_rest_df['종료시간'] = pd.to_datetime(machine_rest_df['종료시간'], errors='coerce', utc=False)
                if machine_rest_df['종료시간'].dt.tz is not None:
                    machine_rest_df['종료시간'] = machine_rest_df['종료시간'].dt.tz_localize(None)
            
            # dispatch rule 생성
            from src.scheduler.dispatch_rules import create_dispatch_rule
            dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
            
            # opnode_dict가 None이면 빈 딕셔너리 사용
            if opnode_dict is None:
                opnode_dict = {}
            
            # manager가 None이면 DAG를 재생성
            if dag_manager is None:
                logger.error("❌ DAG Manager가 None입니다. DAG 생성 단계에서 manager 객체를 제대로 저장하지 못했습니다.")
                raise ValueError("DAG Manager 객체가 없습니다. DAG 생성 단계를 다시 실행해주세요.")
            
            # 스케줄링 실행
            from src.scheduler.delay_dict import DelayProcessor
            from src.scheduler.scheduler import Scheduler
            
            delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
            scheduler = Scheduler(machine_dict, delay_processor)
            scheduler.allocate_resources()
            
            # 기계 중단시간 설정 (main.py와 동일)
            if base_date and not machine_rest_df.empty:
                scheduler.allocate_machine_downtime(machine_rest_df, base_date)
                logger.info("기계 중단시간 설정 완료")
            else:
                logger.warning("기계 중단시간 설정을 건너뜁니다 (base_date 또는 machine_rest_df 없음)")
            
            strategy = self.DispatchPriorityStrategy()
            result = strategy.execute(
                dag_manager=dag_manager,
                scheduler=scheduler,
                dag_df=dag_df,
                priority_order=dispatch_rule_ans,
                window_days=window_days
            )
            
            logger.info("스케줄링 완료")
            return result, scheduler, scheduler.create_machine_schedule_dataframe()
            
        except Exception as e:
            logger.error(f"스케줄링 실패: {e}")
            raise

    def run_results_processing(self, output_final_result: Any, merged_df: Any, 
                             original_order: list, sequence_seperated_order: Any,
                             machine_mapping: Dict[str, str], machine_schedule_df: Any,
                             base_date: datetime, scheduler: Any = None) -> Dict[str, Any]:
        """
        6단계: 결과 처리 실행 (main.py와 동일)
        """
        try:
            logger.info("결과 처리 시작")
            
            # DataFrame으로 변환
            if isinstance(output_final_result, list):
                output_final_result = pd.DataFrame(output_final_result)
            if isinstance(merged_df, list):
                merged_df = pd.DataFrame(merged_df)
            if isinstance(sequence_seperated_order, list):
                sequence_seperated_order = pd.DataFrame(sequence_seperated_order)
            if isinstance(machine_schedule_df, list):
                machine_schedule_df = pd.DataFrame(machine_schedule_df)
            
            # 원본 주문 데이터 처리
            if isinstance(original_order, list):
                original_order = pd.DataFrame(original_order)
            
            # create_results 함수 호출 (main.py와 동일)
            from src.results import create_results
            
            results = create_results(
                output_final_result=output_final_result,
                merged_df=merged_df,
                original_order=original_order,
                sequence_seperated_order=sequence_seperated_order,
                machine_mapping=machine_mapping,
                machine_schedule_df=machine_schedule_df,
                base_date=base_date,
                scheduler=scheduler
            )
            
            logger.info("결과 처리 완료")
            return results
            
        except Exception as e:
            logger.error(f"결과 처리 실패: {e}")
            raise

    def run_full_scheduling(self, loaded_data: Dict[str, Any], window_days: int, 
                           base_date: datetime) -> Tuple[Any, Any, Any]:
        """
        전체 스케줄링 프로세스 실행 (main.py와 동일한 방식)
        """
        try:
            logger.info("전체 스케줄링 프로세스 시작")
            
            # 1단계: 데이터 변환 (main.py와 동일)
            order_df = pd.DataFrame(loaded_data.get("order", []))
            operation_seperated_sequence = pd.DataFrame(loaded_data.get("operation_seperated_sequence", []))
            operation_types_df = pd.DataFrame(loaded_data.get("operation_types", []))
            machine_limit_df = pd.DataFrame(loaded_data.get("machine_limit", []))
            machine_allocate_df = pd.DataFrame(loaded_data.get("machine_allocate", []))
            linespeed_df = pd.DataFrame(loaded_data.get("linespeed", []))
            machine_master_df = pd.DataFrame(loaded_data.get("machine_master_info", []))
            yield_df = pd.DataFrame(loaded_data.get("yield_data", []))
            gitem_operation_df = pd.DataFrame(loaded_data.get("gitem_operation", []))
            operation_delay_df = pd.DataFrame(loaded_data.get("operation_delay_df", []))
            width_change_df = pd.DataFrame(loaded_data.get("width_change_df", []))
            machine_rest_df = pd.DataFrame(loaded_data.get("machine_rest", []))
            
            # 날짜 컬럼 변환 (timezone-naive로 강제 변환)
            if '납기일' in order_df.columns:
                order_df['납기일'] = pd.to_datetime(order_df['납기일'], utc=False)
                if order_df['납기일'].dt.tz is not None:
                    order_df['납기일'] = order_df['납기일'].dt.tz_localize(None)
            
            if '시작시간' in machine_rest_df.columns:
                machine_rest_df['시작시간'] = pd.to_datetime(machine_rest_df['시작시간'], utc=False)
                if machine_rest_df['시작시간'].dt.tz is not None:
                    machine_rest_df['시작시간'] = machine_rest_df['시작시간'].dt.tz_localize(None)
            
            if '종료시간' in machine_rest_df.columns:
                machine_rest_df['종료시간'] = pd.to_datetime(machine_rest_df['종료시간'], utc=False)
                if machine_rest_df['종료시간'].dt.tz is not None:
                    machine_rest_df['종료시간'] = machine_rest_df['종료시간'].dt.tz_localize(None)
            
            # 2단계: 전처리
            sequence_seperated_order, linespeed = self.preprocessing(
                order_df, operation_seperated_sequence, operation_types_df,
                machine_limit_df, machine_allocate_df, linespeed_df
            )
            
            # 3단계: 수율 예측
            yield_predictor, sequence_yield_df, sequence_seperated_order = self.yield_prediction(
                yield_df, gitem_operation_df, sequence_seperated_order
            )
            
            # 4단계: DAG 생성
            dag_df, opnode_dict, manager, machine_dict, merged_df = self.create_complete_dag_system(
                sequence_seperated_order, linespeed_df, machine_master_df, self.config
            )
            
            # 5단계: 스케줄링
            from src.scheduler.delay_dict import DelayProcessor
            from src.scheduler.scheduler import Scheduler
            from src.scheduler.dispatch_rules import create_dispatch_rule
            
            # dispatch rule 생성
            dispatch_rule_ans, dag_df = create_dispatch_rule(dag_df, sequence_seperated_order)
            
            # 스케줄링 실행
            delay_processor = DelayProcessor(opnode_dict, operation_delay_df, width_change_df)
            scheduler = Scheduler(machine_dict, delay_processor)
            scheduler.allocate_resources()
            
            # 기계 중단시간 설정
            if not machine_rest_df.empty:
                scheduler.allocate_machine_downtime(machine_rest_df, base_date)
            
            strategy = self.DispatchPriorityStrategy()
            result = strategy.execute(
                dag_manager=manager,
                scheduler=scheduler,
                dag_df=dag_df,
                priority_order=dispatch_rule_ans,
                window_days=window_days
            )
            
            logger.info("전체 스케줄링 프로세스 완료")
            return result, scheduler, scheduler.create_machine_schedule_dataframe()
            
        except Exception as e:
            logger.error(f"전체 스케줄링 프로세스 실패: {e}")
            raise


# 전역 서비스 인스턴스
python_engine_service = PythonEngineService()