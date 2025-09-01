def seperate_order_by_month(order):
    return [group for _, group in order.groupby(order['납기일'].dt.month)]

def same_order_groupby(grouby_condition_list, df):
    """
    groupby_condition_list: 그룹화를 하는 조건. 해당 리스트 내의 컬럼의 값이 전부 같을 경우 그룹화 진행

    조건:
    데이터프레임에 의뢰량, 원단길이, 납기일, P/O NO 컬럼이 각각 존재해야함.
    """
    df = df.groupby(
        grouby_condition_list,
        as_index = False,
        dropna = False,
    ).agg({
        '의뢰량': 'sum',
        '원단길이': 'sum',
        '납기일': 'min',
        'P/O NO': lambda x: list(x)
    })
    return df