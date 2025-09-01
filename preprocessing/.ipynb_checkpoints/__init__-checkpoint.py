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
    order_list = [same_order_groupby(['GITEM', 'GITEM명', '너비', '길이'], df) for df in order_list]

    # 1-C. 시퀀스 주문 생성
    sequence_order = create_sequence_seperated_order(order_list, operation_seperated_sequence)

    # 1-D. 공정 타입 정보 병합 및 형 변환
    sequence_order = sequence_order.merge(
        operation_types[['공정명', '공정분류']],
        left_on='공정',
        right_on='공정명',
        how='left'
    )
    sequence_order['GITEM'] = sequence_order['GITEM'].astype(str)

    # 2. 기계 정보 수정
    # unable_gitems: 기계의 특정 공정 휴기 때문에 생산하지 못하는 공정 리스트
    linespeed, unable_gitems = operation_machine_limit(linespeed, machine_limit)
    linespeed = operation_machine_exclusive(linespeed, machine_allocate)

    display(sequence_order)
    sequence_order = sequence_order[~ (sequence_order['GITEM'].isin(unable_gitems))]
    
    if unable_gitems:
        print("preprocessing 단계에서 특정 기계의 특정 공정 휴기로 인해 해당 공정 포함된 아이템 생산 불가")
    
    return sequence_order, linespeed
