from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FilePaths:
    # Excel Input files (변환용)
    ITEM_LINESPEED_SEQUENCE: str = "data/input/품목별 분리 라인스피드 및 공정 순서.xlsx"
    OPERATION_RECLASSIFICATION: str = "data/input/공정 재분류 내역 및 교체 시간 정리(250820).xlsx"
    IMPOSSIBLE_OPERATION: str = "data/input/불가능한 공정 입력값.xlsx"
    ORDER_DATA: str = "data/input/preprocessed_order.xlsx"  # 전처리된 주문 데이터
    ORDER_PO_RAW: str = "25년 5월 PO 내역(송부건).xlsx"  # 원본 주문 데이터 (전처리용)
    
    # JSON Data files (실제 사용)
    JSON_DIR: str = "data/json"
    JSON_LINESPEED: str = "data/json/md_step2_linespeed.json"
    JSON_OPERATION_SEQUENCE: str = "data/json/md_step3_operation_sequence.json"
    JSON_MACHINE_INFO: str = "data/json/md_step4_machine_master_info.json"
    JSON_YIELD_DATA: str = "data/json/md_step3_yield_data.json"
    JSON_GITEM_OPERATION: str = "data/json/md_step3_gitem_operation.json"
    JSON_OPERATION_TYPES: str = "data/json/md_step2_operation_types.json"
    JSON_OPERATION_DELAY: str = "data/json/md_step5 operation_delay.json"
    JSON_WIDTH_CHANGE: str = "data/json/md_step5_width_change.json"
    JSON_MACHINE_REST: str = "data/json/user_step5_machine_rest.json"
    JSON_MACHINE_ALLOCATE: str = "data/json/user_step2_machine_allocate.json"
    JSON_MACHINE_LIMIT: str = "data/json/user_step2_machine_limit.json"
    JSON_ORDER_DATA: str = "data/json/md_step2_order_data.json"
    
    # Output files
    RESULT_INTERMEDIATE: str = "data/output/result.xlsx"
    RESULT_FINAL: str = "data/output/0829 스케줄링결과.xlsx"
    GANTT_CHART: str = "data/output/level4_gantt.png"
    GANTT_INPUT: str = "gantt_input.xlsx"


@dataclass
class SheetNames:
    ITEM_LINESPEED: str = "품목별 라인스피드"
    OPERATION_SEQUENCE: str = "공정순서"
    MACHINE_MASTER_INFO: str = "기계기준정보"
    YIELD_DATA: str = "수율데이터"
    GITEM_OPERATION: str = "GITEM별 공정"
    OPERATION_TYPES: str = "공정군"
    OPERATION_DELAY: str = "공정교체시간"
    WIDTH_CHANGE: str = "폭변경"
    MACHINE_REST: str = "기계"
    MACHINE_ALLOCATE: str = "공정강제할당"
    MACHINE_LIMIT: str = "공정강제회피"
    ORDER_CONFIRMED: str = "25년 5월 PO확정 내역"
    ORDER_PRODUCTION_SUMMARY: str = "주문_생산_요약본"
    MACHINE_INFO_RESULT: str = "호기_정보"
    ORDER_PRODUCTION_INFO: str = "주문_생산_정보"


@dataclass
class ColumnNames:
    # Core identifiers
    PO_NO: str = "P/O NO"
    GITEM: str = "GITEM"
    GITEM_NAME: str = "GITEM명"
    ID: str = "ID"
    
    # Product specifications
    WIDTH: str = "너비"                      # Product width from SPEC
    FABRIC_WIDTH: str = "원단너비"           # Different: process-specific fabric width
    LENGTH: str = "길이"                     # Single unit length from SPEC  
    FABRIC_LENGTH: str = "원단길이"          # Different: calculated total length (길이 * 의뢰량)
    PRODUCTION_LENGTH: str = "생산길이"      # Different: actual production length (after yield adjustment)
    ORIGINAL_PRODUCTION_LENGTH: str = "원본생산길이"  # Before yield adjustment
    REQUEST_AMOUNT: str = "의뢰량"
    
    # Dates and times
    DUE_DATE: str = "납기일"
    END_DATE: str = "종료날짜"
    LATE_DAYS: str = "지각일수"
    END_TIME: str = "종료시각"               # End time (abstract units)
    START_TIME: str = "시작시각"             # Start time (abstract units)
    WORK_START_TIME: str = "작업 시작 시간"   # Same semantic meaning as END_TIME but different context
    WORK_END_TIME: str = "작업 종료 시간"     # Same semantic meaning as START_TIME but different context
    WORK_TIME: str = "작업시간"              # Calculated duration
    
    # Machine identifiers (from 기계정보.xlsx)
    MACHINE_INDEX: str = "기계인덱스"        # 0,1,2,3... (numeric index)
    MACHINE_CODE: str = "기계코드"           # C2010, C2250... (unique code)
    MACHINE_NAME: str = "기계명"             # 1호기, 25호기... (human name)
    
    # Operations
    OPERATION_ORDER: str = "공정순서"
    OPERATION: str = "공정명"
    OPERATION_CLASSIFICATION: str = "공정분류"
    MIXTURE_CODE: str = "배합코드"
    ALLOCATED_WORK: str = "할당 작업"
    
    # Process IDs (structured pattern)
    PROCESS_ID_SUFFIX: str = "공정ID"  # 동적 공정 처리용
    
    # Technical fields
    DEPTH: str = "depth"
    CHILDREN: str = "children"
    NODE_END: str = "node_end"
    COMBINATION_CLASSIFICATION: str = "조합분류"
    
    # Yield related
    YIELD: str = "수율"
    PREDICTED_YIELD: str = "예측_수율"
    TOTAL_PREDICTED_YIELD: str = "전체_예측_수율"
    YIELD_PRODUCTION_RATIO: str = "수율_생산비율"
    
    # Scheduler delay/setup time related
    EARLIER_OPERATION_TYPE: str = "선행공정분류"
    LATER_OPERATION_TYPE: str = "후행공정분류"
    TYPE_CHANGE_TIME: str = "타입교체시간"
    LONG_TO_SHORT: str = "long_to_short"
    SHORT_TO_LONG: str = "short_to_long"
    
    # Machine scheduling related
    START_TIME_SCHEDULE: str = "시작시간"
    END_TIME_SCHEDULE: str = "종료시간"


@dataclass
class BusinessConstants:
    BASE_YEAR: int = 2025
    BASE_MONTH: int = 5
    BASE_DAY: int = 15
    WINDOW_DAYS: int = 5
    TIME_MULTIPLIER: int = 30
    GANTT_DPI: int = 300
    FAKE_OPERATION_DEPTH: int = -1


@dataclass
class Config:
    files: FilePaths = field(default_factory=FilePaths)
    sheets: SheetNames = field(default_factory=SheetNames)
    columns: ColumnNames = field(default_factory=ColumnNames)
    constants: BusinessConstants = field(default_factory=BusinessConstants)


config = Config()