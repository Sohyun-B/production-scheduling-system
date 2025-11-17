from dataclasses import dataclass, field
from typing import Dict, List




@dataclass
class ColumnNames:
    # Core identifiers
    PO_NO: str = "pono" # "P/O NO"
    GRP2_NAME: str = "grp2_name" # "GRP2 이름, GITEM보다 상위 분류
    GITEM: str = "gitemno" # "GITEM"
    GITEM_NAME: str = "gitemname" # "GITEM명"

    # ID
    PRODUCT_ID: str = "product_ID"   # 제품 레벨 식별자: {GITEM}_{FABRIC_WIDTH}_{COMB}_M{MONTH}
    PROCESS_ID: str = "process_ID"   # 공정 레벨 식별자: {PRODUCT_ID}_{OPERATION_CODE}_{CHEMICAL}

    SPEC: str = "spec" # "SPEC"
    SITEM: str = "sitemno" # "SITEMNO"
    SITEM_NAME: str = "sitemname" # "SITEM명"

    # Product specifications
    WIDTH: str = "width" # "너비"                      # Product width from SPEC
    FABRIC_WIDTH: str = "fabric_width" # "원단너비"           # Different: process-specific fabric width
    LENGTH: str = "length" # "길이"                       # Single unit length from SPEC  
    FABRIC_LENGTH: str = "fabric_length" # "원단길이"          # Different: calculated total length (길이 * 의뢰량)
    PRODUCTION_LENGTH: str = "production_length" # "생산길이"      # Different: actual production length (after yield adjustment)
    ORIGINAL_PRODUCTION_LENGTH: str = "original_production_length" # "원본생산길이"  # Before yield adjustment
    REQUEST_AMOUNT: str = "ipgmqty" # "의뢰량"
    
    # Dates and times
    DUE_DATE: str = "duedate" # "납기일"
    END_DATE: str = "end_date" # "종료날짜"
    LATE_DAYS: str = "late_days" # "지각일수"
    END_TIME: str = "end_time" # "종료시각"               # End time (abstract units)
    START_TIME: str = "start_time" # "시작시각"             # Start time (abstract units)
    WORK_START_TIME: str = "work_start_time" # "작업 시작 시간"   # Same semantic meaning as END_TIME but different context
    WORK_END_TIME: str = "work_end_time" # "작업 종료 시간"     # Same semantic meaning as START_TIME but different context
    WORK_TIME: str = "work_time" # "작업시간"              # Calculated duration
    
    # Machine identifiers (from 기계정보.xlsx)
    # MACHINE_INDEX: str = "machineindex" # "기계인덱스"        # 0,1,2,3... (numeric index)
    MACHINE_CODE: str = "machineno" # "기계코드"           # C2010, C2250... (unique code)
    MACHINE_NAME: str = "machinename" # "기계명"             # 1호기, 25호기... (human name)
    
    # Operations
    OPERATION_ORDER: str = "procseq" # "공정순서"
    OPERATION: str = "procname" # "공정명"
    OPERATION_CODE: str = "proccode"
    OPERATION_CLASSIFICATION: str = "procgbn" # "공정분류"
    CHEMICAL_LIST: str = "chemical_list" # "배합코드"
    CHEMICAL_1: str = "che1" # 가장 우선적으로 선택되는 배합코드
    CHEMICAL_2: str = "che2" # 두 번째로 선택되는 배합코드
    ALLOCATED_WORK: str = "allocated_work" # "할당 작업"
    
    # Process IDs (structured pattern)
    PROCESS_ID_SUFFIX: str = "_proccode" #  "공정ID"  # 동적 공정 처리용
    
    # Technical fields
    DEPTH: str = "depth"
    CHILDREN: str = "children"
    NODE_END: str = "node_end"
    COMBINATION_CLASSIFICATION: str = "comb_classification" # "조합분류"
    
    # Yield related
    YIELD: str = "yield" # "수율"
    PRODUCT_RATIO: float = "product_ratio" # 수율을 고려한 각 공정의 생산 비율
    # PREDICTED_YIELD: str = "predicted_yield" # "예측_수율"
    # TOTAL_PREDICTED_YIELD: str = "total_predicted_yield" # "전체_예측_수율"
    # YIELD_PRODUCTION_RATIO: str = "yield_production_ratio" # "수율_생산비율"
    
    # Scheduler delay/setup time related
    EARLIER_OPERATION_TYPE: str = "prev_procgbn" # "선행공정분류"
    LATER_OPERATION_TYPE: str = "next_procgbn" # "후행공정분류", 에이징에서도 사용
    TYPE_CHANGE_TIME: str = "type_change_time" # "타입교체시간"
    LONG_TO_SHORT: str = "long_to_short"
    SHORT_TO_LONG: str = "short_to_long"

    # Aging related
    AGING_TIME: str = "aging_time" # "에이징시간"
    
    # Machine scheduling related
    MACHINE_REST_START: str = "rest_start" # 기계 휴기 시작 시간
    MACHINE_REST_END: str = "rest_end" # 기계 휴기 종료 시간

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


@dataclass
class Config:
    columns: ColumnNames = field(default_factory=ColumnNames)
    constants: BusinessConstants = field(default_factory=BusinessConstants)


config = Config()