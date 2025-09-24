from config import config
import pandas as pd
from .order_preprocessing import seperate_order_by_month, same_order_groupby
from .sequence_preprocessing import process_operations_by_category, create_sequence_seperated_order
from .operation_machine_limit import operation_machine_limit, operation_machine_exclusive

def preprocessing(order, operation_seperated_sequence, operation_types, machine_limit, machine_allocate, linespeed):
    """
    order -> 월별 분리 -> 동일 주문 병합 -> 시퀀스 주문 생성 -> 공정 타입 병합 + 컬럼 타입 변환
    한 번에 처리하는 파이프라인 함수
    """
    # 1-A. 납기일 월별 분리
    order_list = seperate_order_by_month(order)

    # 1-B. 동일 주문 병합
    groupby_columns = [config.columns.GITEM, config.columns.GITEM_NAME, config.columns.WIDTH, config.columns.LENGTH]
    order_list = [same_order_groupby(groupby_columns, df) for df in order_list]

    # 1-C. 시퀀스 주문 생성
    sequence_order = create_sequence_seperated_order(order_list, operation_seperated_sequence)

    # 1-D. 공정 타입 정보 병합 및 형 변환
    sequence_order = sequence_order.merge(
        operation_types[[config.columns.OPERATION_CODE, config.columns.OPERATION_CLASSIFICATION]],
        left_on=config.columns.OPERATION_CODE,
        right_on=config.columns.OPERATION_CODE,
        how='left'
    )
    sequence_order[config.columns.GITEM] = sequence_order[config.columns.GITEM].astype(str)

    # 2. 기계 정보 수정
    

    # unable_gitems: 기계의 특정 공정 휴기 때문에 생산하지 못하는 공정 리스트
    # unable_details: GITEM과 해당 불가능한 공정명 정보


    linespeed, unable_gitems, unable_details = operation_machine_limit(linespeed, machine_limit)
    linespeed = operation_machine_exclusive(linespeed, machine_allocate)

    print(f"unable gitems: {len(unable_gitems)}개")

    if unable_gitems:
        """
        사용하지 않는 gitem과 p/o 데이터가 존재할 때
        sequence_order에서 제외 후 제외된 데이터를 unable_gitems, unable_order에 저장
        """
        unable_order = sequence_order[(sequence_order[config.columns.GITEM].isin(unable_gitems))]
        sequence_order = sequence_order[~ (sequence_order[config.columns.GITEM].isin(unable_gitems))]

        unable_order = unable_order[['P/O NO', 'GITEM']] # 생산 불가능한 GITEM과 P/O 정보
        print(f"unable order: {len(unable_order)}개")

        return sequence_order, linespeed, unable_gitems, unable_order, unable_details
    else:
        return sequence_order, linespeed, [], pd.DataFrame(), []
