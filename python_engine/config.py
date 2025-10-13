from dataclasses import dataclass, field
from typing import Dict, List




@dataclass
class ColumnNames:
    # Core identifiers
    PO_NO: str = "PoNo" # "P/O NO"
    GITEM: str = "GitemNo" # "GITEM"
    GITEM_NAME: str = "GitemName" # "GITEM명"
    ID: str = "ID" # "ID"
    
    # Product specifications
    WIDTH: str = "Width" # "너비"                      # Product width from SPEC
    FABRIC_WIDTH: str = "fabric_width" # "원단너비"           # Different: process-specific fabric width
    LENGTH: str = "Length" # "길이"                       # Single unit length from SPEC  
    FABRIC_LENGTH: str = "Fabric_Length" # "원단길이"          # Different: calculated total length (길이 * 의뢰량)
    PRODUCTION_LENGTH: str = "production_length" # "생산길이"      # Different: actual production length (after yield adjustment)
    ORIGINAL_PRODUCTION_LENGTH: str = "original_production_length" # "원본생산길이"  # Before yield adjustment
    REQUEST_AMOUNT: str = "IpgmQty" # "의뢰량"
    
    # Dates and times
    DUE_DATE: str = "DUEDATE" # "납기일"
    ORIGINAL_DUE_DATE: str = "original_due_date" # "원본납기일"
    END_DATE: str = "end_date" # "종료날짜"
    LATE_DAYS: str = "late_days" # "지각일수"
    END_TIME: str = "end_time" # "종료시각"               # End time (abstract units)
    START_TIME: str = "start_time" # "시작시각"             # Start time (abstract units)
    WORK_START_TIME: str = "work_start_time" # "작업 시작 시간"   # Same semantic meaning as END_TIME but different context
    WORK_END_TIME: str = "work_end_time" # "작업 종료 시간"     # Same semantic meaning as START_TIME but different context
    WORK_TIME: str = "work_time" # "작업시간"              # Calculated duration
    
    # Machine identifiers (from 기계정보.xlsx)
    MACHINE_INDEX: str = "MachineIndex" # "기계인덱스"        # 0,1,2,3... (numeric index)
    MACHINE_CODE: str = "MachineNo" # "기계코드"           # C2010, C2250... (unique code)
    MACHINE_NAME: str = "MachineName" # "기계명"             # 1호기, 25호기... (human name)
    
    # Operations
    OPERATION_ORDER: str = "PROCSEQ" # "공정순서"
    OPERATION: str = "PROCNAME" # "공정명"
    OPERATION_CODE: str = "PROCCODE"
    OPERATION_CLASSIFICATION: str = "ProcGbn" # "공정분류"
    MIXTURE_LIST: str = "mixture_list" # "배합코드"
    ALLOCATED_WORK: str = "allocated_work" # "할당 작업"
    
    # Process IDs (structured pattern)
    PROCESS_ID_SUFFIX: str = "_PROCCODE" #  "공정ID"  # 동적 공정 처리용
    
    # Technical fields
    DEPTH: str = "depth"
    CHILDREN: str = "children"
    NODE_END: str = "node_end"
    COMBINATION_CLASSIFICATION: str = "comb_classification" # "조합분류"
    
    # Yield related
    YIELD: str = "yield" # "수율"
    PREDICTED_YIELD: str = "predicted_yield" # "예측_수율"
    TOTAL_PREDICTED_YIELD: str = "total_predicted_yield" # "전체_예측_수율"
    YIELD_PRODUCTION_RATIO: str = "yield_production_ratio" # "수율_생산비율"
    
    # Scheduler delay/setup time related
    EARLIER_OPERATION_TYPE: str = "prev_operation_type" # "선행공정분류"
    LATER_OPERATION_TYPE: str = "next_operation_type" # "후행공정분류"
    TYPE_CHANGE_TIME: str = "type_change_time" # "타입교체시간"
    LONG_TO_SHORT: str = "long_to_short"
    SHORT_TO_LONG: str = "short_to_long"
    
    # Machine scheduling related
    START_TIME_SCHEDULE: str = "dt_start" # "시작시간"
    END_TIME_SCHEDULE: str = "dt_end" # "종료시간"


@dataclass
class BusinessConstants:
    BASE_YEAR: int = 2025
    BASE_MONTH: int = 5
    BASE_DAY: int = 15
    WINDOW_DAYS: int = 5
    LINESPEED_PERIOD: str = '6_months'
    YIELD_PERIOD: str = '6_months'
    TIME_MULTIPLIER: int = 30
    GANTT_DPI: int = 300
    FAKE_OPERATION_DEPTH: int = -1
    BUFFER_DAYS: int = 7  # 납기 여유일자 (디폴트 7일)


@dataclass
class Config:
    columns: ColumnNames = field(default_factory=ColumnNames)
    constants: BusinessConstants = field(default_factory=BusinessConstants)


config = Config()