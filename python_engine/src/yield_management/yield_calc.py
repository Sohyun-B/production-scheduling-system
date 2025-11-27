import pandas as pd
from config import config

def yield_prediction(yield_data, sequence_seperated_order, work_in_progress=None):
    """
    수율 데이터를 기반으로 각 공정의 투입 비율을 계산하고,
    재공품을 고려하여 실제 생산해야 할 길이를 조정합니다.

    Args:
        yield_data: 수율 데이터 (gitemno, proccode, procseq, yield)
        sequence_seperated_order: 주문 데이터 (process_ID, gitemno, proccode, product_length, duedate)
        work_in_progress: 재공품 데이터 (gitemno, completed_proccode, completed_procseq, length), optional

    Returns:
        dict: {
            'adjusted_orders': 재공품 적용 후 조정된 주문 DataFrame (3개의 길이 컬럼 포함):
                - production_length: 수율과 재공품을 모두 고려한 실제 생산길이
                - production_length_wo_wip: 수율만 고려하고 재공품을 고려하지 않은 생산길이
                - original_production_length: 수율과 재공품을 모두 고려하기 이전의 생산길이
            'wip_usage_log': 재공품 사용 이력 DataFrame,
            'unused_wip': 미사용 재공품 DataFrame
        }
    """
    # 1. yield_data 정렬 및 product_ratio 계산
    yield_data_sorted = yield_data.sort_values(
        [config.columns.GITEM, config.columns.OPERATION_ORDER]
    ).reset_index(drop=True)

    # pandas FutureWarning 방지를 위해 warning 무시
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=FutureWarning)
        yield_data_with_ratio = yield_data_sorted.groupby(
            config.columns.GITEM,
            group_keys=False
        ).apply(calculate_input_ratio).reset_index(drop=True)

    # 2. sequence_seperated_order에 product_ratio 병합
    # 기존 product_ratio 컬럼이 있다면 제거
    sequence_order_clean = sequence_seperated_order.copy()
    if config.columns.PRODUCT_RATIO in sequence_order_clean.columns:
        sequence_order_clean = sequence_order_clean.drop(columns=[config.columns.PRODUCT_RATIO])

    orders_with_ratio = sequence_order_clean.merge(
        yield_data_with_ratio[[
            config.columns.GITEM,
            config.columns.OPERATION_CODE,
            config.columns.PRODUCT_RATIO
        ]],
        on=[config.columns.GITEM, config.columns.OPERATION_CODE],
        how='left'
    )

    # 3. 길이 컬럼 계산
    # 3-1. original_production_length: 원본 생산길이 (수율, 재공품 미고려)
    orders_with_ratio[config.columns.ORIGINAL_PRODUCTION_LENGTH] = \
        orders_with_ratio[config.columns.PRODUCTION_LENGTH]

    # 3-2. production_length_wo_wip: 수율만 고려한 생산길이 (재공품 미고려)
    orders_with_ratio[config.columns.PRODUCTION_LENGTH_WO_WIP] = \
        orders_with_ratio[config.columns.ORIGINAL_PRODUCTION_LENGTH] * \
        orders_with_ratio[config.columns.PRODUCT_RATIO]

    # 결과 길이를 10의 자리에서 반올림
    orders_with_ratio[config.columns.PRODUCTION_LENGTH_WO_WIP] = \
        orders_with_ratio[config.columns.PRODUCTION_LENGTH_WO_WIP].round(-1).astype(int)

    # 3-3. production_length: 처음에는 production_length_wo_wip와 동일, 재공품 적용 후 변경됨
    orders_with_ratio[config.columns.PRODUCTION_LENGTH] = \
        orders_with_ratio[config.columns.PRODUCTION_LENGTH_WO_WIP]

    # product_ratio 컬럼 제거
    orders_adjusted = orders_with_ratio.drop(columns=[config.columns.PRODUCT_RATIO])

    # 4. 재공품 처리
    if work_in_progress is not None and not work_in_progress.empty:
        # 재공품을 모든 공정으로 확장
        expanded_wip, unused_wip = expand_wip_to_all_processes(
            work_in_progress,
            yield_data_with_ratio
        )

        # 재공품을 주문에 적용
        if not expanded_wip.empty:
            adjusted_orders, wip_usage_log = apply_wip_to_orders(
                orders_adjusted,
                expanded_wip
            )
        else:
            adjusted_orders = orders_adjusted
            wip_usage_log = pd.DataFrame()
    else:
        adjusted_orders = orders_adjusted
        wip_usage_log = pd.DataFrame()
        unused_wip = pd.DataFrame()

    return adjusted_orders, wip_usage_log, unused_wip


def calculate_input_ratio(group):
    """
    공정별 수율을 고려한 투입 비율을 계산합니다.

    역순으로 누적 곱을 계산하여 각 공정에서 필요한 투입량 비율을 산출합니다.

    Args:
        group: 같은 item으로 그룹화된 DataFrame

    Returns:
        input_ratio 컬럼이 추가된 DataFrame

    Example:
        각 공정의 yield가 50%이고 3번의 공정을 수행하는 작업이라면:
        - 공정3 (마지막): product_ratio = 1/0.5 = 2
        - 공정2: product_ratio = 2 * (1/0.5) = 4
        - 공정1 (첫번째): product_ratio = 4 * (1/0.5) = 8
    """
    yields = group[config.columns.YIELD].values
    num_processes = len(yields)
    ratios = [1] * num_processes

    accumulator = 1

    # 역순으로 진행하며 누적 곱을 계산
    for i in range(num_processes - 1, -1, -1):
        accumulator *= 1 / yields[i] * 100
        ratios[i] = accumulator

    group[config.columns.PRODUCT_RATIO] = ratios
    return group


def expand_wip_to_all_processes(work_in_progress, yield_data):
    """
    n번째 공정까지 완료된 재공품을 1~n번째 모든 공정으로 확장하고,
    각 공정에서의 길이를 수율 기반으로 계산합니다.

    Args:
        work_in_progress: 재공품 데이터 (gitemno, completed_proccode, completed_procseq, length)
        yield_data: 수율 데이터 (gitemno, proccode, procseq, yield, product_ratio)

    Returns:
        tuple: (expanded_wip, unused_wip)
            - expanded_wip: 모든 공정으로 확장된 재공품 (gitemno, proccode, procseq, wip_length, wip_id)
            - unused_wip: 사용할 수 없는 재공품 (해당 gitemno가 생산 대상이 아닌 경우)

    Example:
        재공품: gitemno=A, completed_procseq=2, length=100
        yield_data에서 gitemno=A의 공정1 product_ratio=4, 공정2 product_ratio=2
        결과:
            - 공정1: length = 100 * (4/2) = 200
            - 공정2: length = 100 * (2/2) = 100
    """
    if work_in_progress.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 재공품에 wip_id 추가 (추적용)
    work_in_progress = work_in_progress.copy()
    work_in_progress['wip_id'] = range(len(work_in_progress))

    # 재공품의 gitemno가 yield_data에 존재하는지 확인
    valid_gitems = set(yield_data[config.columns.GITEM].unique())

    # 사용 가능한 재공품과 사용 불가능한 재공품 분리
    usable_wip = work_in_progress[
        work_in_progress[config.columns.GITEM].isin(valid_gitems)
    ].copy()
    unused_wip = work_in_progress[
        ~work_in_progress[config.columns.GITEM].isin(valid_gitems)
    ].copy()

    if usable_wip.empty:
        return pd.DataFrame(), unused_wip

    # 확장된 재공품을 저장할 리스트
    expanded_rows = []

    # 각 재공품에 대해 처리
    for _, wip_row in usable_wip.iterrows():
        gitemno = wip_row[config.columns.GITEM]
        completed_procseq = wip_row['completed_procseq']
        wip_length = wip_row['length']
        wip_id = wip_row['wip_id']

        # 해당 gitemno의 모든 공정 정보 가져오기
        gitem_processes = yield_data[
            yield_data[config.columns.GITEM] == gitemno
        ].sort_values(config.columns.OPERATION_ORDER)

        # 완료된 공정의 product_ratio 가져오기
        completed_process = gitem_processes[
            gitem_processes[config.columns.OPERATION_ORDER] == completed_procseq
        ]

        if completed_process.empty:
            # 완료된 공정 정보가 없으면 사용 불가능한 재공품으로 분류
            unused_wip = pd.concat([unused_wip, pd.DataFrame([wip_row])], ignore_index=True)
            continue

        completed_ratio = completed_process.iloc[0][config.columns.PRODUCT_RATIO]

        # 1번부터 completed_procseq번 공정까지 확장
        for _, process_row in gitem_processes[
            gitem_processes[config.columns.OPERATION_ORDER] <= completed_procseq
        ].iterrows():
            procseq = process_row[config.columns.OPERATION_ORDER]
            proccode = process_row[config.columns.OPERATION_CODE]
            process_ratio = process_row[config.columns.PRODUCT_RATIO]

            # 해당 공정에서의 길이 계산: wip_length * (해당 공정 ratio / 완료 공정 ratio)
            process_wip_length = wip_length * (process_ratio / completed_ratio)

            expanded_rows.append({
                config.columns.GITEM: gitemno,
                config.columns.OPERATION_CODE: proccode,
                config.columns.OPERATION_ORDER: procseq,
                'wip_length': process_wip_length,
                'wip_id': wip_id,
                'original_wip_length': wip_length,
                'completed_procseq': completed_procseq
            })

    if not expanded_rows:
        return pd.DataFrame(), unused_wip

    expanded_wip = pd.DataFrame(expanded_rows)
    return expanded_wip, unused_wip


def apply_wip_to_orders(sequence_seperated_order, expanded_wip):
    """
    재공품을 주문에 적용하여 실제 생산 길이를 차감합니다.
    duedate가 짧은 주문부터 우선적으로 재공품을 적용합니다.

    Args:
        sequence_seperated_order: 주문 데이터 (process_ID, gitemno, proccode, product_length, duedate)
        expanded_wip: 확장된 재공품 데이터 (gitemno, proccode, wip_length, wip_id)

    Returns:
        tuple: (adjusted_orders, wip_usage_log)
            - adjusted_orders: 재공품 적용 후 조정된 주문
            - wip_usage_log: 재공품 사용 이력 (wip_id, process_ID, used_length, remaining_order_length)
    """
    if expanded_wip.empty:
        # 재공품이 없으면 원본 주문 반환
        return sequence_seperated_order.copy(), pd.DataFrame()

    # 주문 데이터 복사
    orders = sequence_seperated_order.copy()

    # 재공품 사용 이력을 저장할 리스트
    usage_log = []

    # (gitemno, proccode) 별로 그룹화
    for (gitemno, proccode), group in orders.groupby(
        [config.columns.GITEM, config.columns.OPERATION_CODE]
    ):
        # 해당 (gitemno, proccode)에 사용 가능한 재공품 찾기
        available_wip = expanded_wip[
            (expanded_wip[config.columns.GITEM] == gitemno) &
            (expanded_wip[config.columns.OPERATION_CODE] == proccode)
        ].copy()

        if available_wip.empty:
            continue

        # duedate 오름차순으로 정렬 (마감일이 빠른 주문부터 처리)
        group_sorted = group.sort_values(config.columns.DUE_DATE)

        # 재공품을 wip_id별로 그룹화하여 총 사용 가능한 길이 계산
        wip_by_id = available_wip.groupby('wip_id')['wip_length'].sum().to_dict()

        # 각 주문에 대해 재공품 적용
        for idx in group_sorted.index:
            if not wip_by_id:
                # 사용 가능한 재공품이 모두 소진됨
                break

            process_id = orders.loc[idx, config.columns.PROCESS_ID]
            order_length = orders.loc[idx, config.columns.PRODUCTION_LENGTH]
            remaining_order = order_length

            # 사용 가능한 재공품을 순회하며 적용
            wip_ids_to_remove = []
            for wip_id, wip_length in wip_by_id.items():
                if remaining_order <= 0:
                    break

                # 사용할 길이 결정
                used_length = min(wip_length, remaining_order)

                # 사용 이력 기록
                usage_log.append({
                    'wip_id': wip_id,
                    config.columns.PROCESS_ID: process_id,
                    config.columns.GITEM: gitemno,
                    config.columns.OPERATION_CODE: proccode,
                    'used_length': used_length,
                    'remaining_order_length': remaining_order - used_length,
                    'original_order_length': order_length
                })

                # 주문 길이 차감
                remaining_order -= used_length

                # 재공품 길이 차감
                wip_by_id[wip_id] -= used_length

                if wip_by_id[wip_id] <= 0:
                    wip_ids_to_remove.append(wip_id)

            # 소진된 재공품 제거
            for wip_id in wip_ids_to_remove:
                del wip_by_id[wip_id]

            # 주문 길이 업데이트
            orders.loc[idx, config.columns.PRODUCTION_LENGTH] = remaining_order

    # 사용 이력 DataFrame 생성
    wip_usage_log = pd.DataFrame(usage_log) if usage_log else pd.DataFrame()

    # 길이가 0 이하인 주문 필터링 (완전히 재공품으로 커버된 주문)
    adjusted_orders = orders[orders[config.columns.PRODUCTION_LENGTH] > 0].copy()

    return adjusted_orders, wip_usage_log


