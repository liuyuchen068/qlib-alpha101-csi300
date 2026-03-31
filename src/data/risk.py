import logging
import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


def add_risk_flags(df_price: pd.DataFrame, prev_close_dict: dict) -> pd.DataFrame:
    """添加停牌、涨跌停标志列"""
    # fixme 什么是风险标志啊？：这里的风险标志是指停牌、涨跌停
    date_str = df_price['date'].iloc[0].replace("-", "")
    df = ak.stock_tfp_em(date=date_str)
    df_zt = ak.stock_zt_pool_em(date=date_str)
    df_dt = ak.stock_zt_pool_dtgc_em(date=date_str)

    if df is None or df.empty:
        df_price['is_suspended'] = 0
    else:
        suspended_codes = df["代码"].tolist()
        df_test = df_price["code"].str.split(".").str[0]
        df_price['is_suspended'] = (df_test.isin(suspended_codes)).astype(int)

    if df_zt is None or df_zt.empty:
        df_price['is_limit_up'] = 0
    else:
        suspended_codes = df_zt["代码"].tolist()
        df_test = df_price["code"].str.split(".").str[0]
        df_price['is_limit_up'] = (df_test.isin(suspended_codes)).astype(int)

    if df_dt is None or df_dt.empty:
        df_price['is_limit_down'] = 0
    else:
        suspended_codes = df_dt["代码"].tolist()
        df_test = df_price["code"].str.split(".").str[0]
        df_price['is_limit_down'] = (df_test.isin(suspended_codes)).astype(int)

    return df_price