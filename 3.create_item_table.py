#-*- coding: utf-8 -*-
import pandas as pd
from collections import Counter

ACTION_201602_FILE = "data_ori/JData_Action_201602.csv"
ACTION_201603_FILE = "data_ori/JData_Action_201603.csv"
ACTION_201603_EXTRA_FILE = "data_ori/JData_Action_201603_extra.csv"
ACTION_201604_FILE = "data_ori/JData_Action_201604.csv"
COMMENT_FILE = "data_ori/JData_Comment.csv"
PRODUCT_FILE = "data_ori/JData_Product.csv"
USER_FILE = "data_ori/JData_User_New.csv"
NEW_USER_FILE = "data_ori/JData_User_New.csv"
ITEM_TABLE_FILE = "data_ori/item_table.csv"


def get_from_jdata_product():
    df_item = pd.read_csv(PRODUCT_FILE, header=0)
    return df_item


# apply type count
def add_type_count(group):
    behavior_type = group.type.astype(int)
    type_cnt = Counter(behavior_type)

    group['browse_num'] = type_cnt[1]
    group['addcart_num'] = type_cnt[2]
    group['delcart_num'] = type_cnt[3]
    group['buy_num'] = type_cnt[4]
    group['favor_num'] = type_cnt[5]
    group['click_num'] = type_cnt[6]

    return group[['sku_id', 'browse_num', 'addcart_num',
                  'delcart_num', 'buy_num', 'favor_num',
                  'click_num']]


def get_from_action_data(fname, chunk_size=100000):
    reader = pd.read_csv(fname, header=0, iterator=True)
    chunks = []
    loop = True
    while loop:
        try:
            chunk = reader.get_chunk(chunk_size)[["sku_id", "type"]]
            chunks.append(chunk)
        except StopIteration:
            loop = False
            print("Iteration is stopped")

    df_ac = pd.concat(chunks, ignore_index=True)

    df_ac = df_ac.groupby(['sku_id'], as_index=False).apply(add_type_count)
    # Select unique row
    df_ac = df_ac.drop_duplicates('sku_id')

    return df_ac


def get_from_jdata_comment():
    df_cmt = pd.read_csv(COMMENT_FILE, header=0)
    df_cmt['dt'] = pd.to_datetime(df_cmt['dt'])
    # find latest comment index
    idx = df_cmt.groupby(['sku_id'])['dt'].transform(max) == df_cmt['dt']
    df_cmt = df_cmt[idx]

    return df_cmt[['sku_id', 'comment_num',
                   'has_bad_comment', 'bad_comment_rate']]


def merge_action_data():
    df_ac = []
    df_ac.append(get_from_action_data(fname=ACTION_201602_FILE))
    df_ac.append(get_from_action_data(fname=ACTION_201603_FILE))
    df_ac.append(get_from_action_data(fname=ACTION_201603_EXTRA_FILE))
    df_ac.append(get_from_action_data(fname=ACTION_201604_FILE))

    df_ac = pd.concat(df_ac, ignore_index=True)
    df_ac = df_ac.groupby(['sku_id'], as_index=False).sum()

    df_ac['buy_addcart_ratio'] = df_ac['buy_num'] / df_ac['addcart_num']
    df_ac['buy_browse_ratio'] = df_ac['buy_num'] / df_ac['browse_num']
    df_ac['buy_click_ratio'] = df_ac['buy_num'] / df_ac['click_num']
    df_ac['buy_favor_ratio'] = df_ac['buy_num'] / df_ac['favor_num']

    df_ac.ix[df_ac['buy_addcart_ratio'] > 1., 'buy_addcart_ratio'] = 1.
    df_ac.ix[df_ac['buy_browse_ratio'] > 1., 'buy_browse_ratio'] = 1.
    df_ac.ix[df_ac['buy_click_ratio'] > 1., 'buy_click_ratio'] = 1.
    df_ac.ix[df_ac['buy_favor_ratio'] > 1., 'buy_favor_ratio'] = 1.

    return df_ac


if __name__ == "__main__":

    item_base = get_from_jdata_product()
    item_behavior = merge_action_data()
    item_comment = get_from_jdata_comment()

    # SQL: left join
    item_behavior = pd.merge(
        item_base, item_behavior, on=['sku_id'], how='left')
    item_behavior = pd.merge(
        item_behavior, item_comment, on=['sku_id'], how='left')

    item_behavior.to_csv(ITEM_TABLE_FILE, index=False)
