import a_trade_calendar as atc
import pandas as pd


def get_trade_dates(start_date: str, end_date: str) -> list:
    """获取指定区间内的所有交易日"""
    # fixme 工作日就是交易日吗？：在此代码中，通过a_trade_calendar库获取交易日历（12行atc命令）
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    return [
        date.strftime('%Y-%m-%d')
        for date in all_dates
        if atc.is_trade_date(date.strftime('%Y-%m-%d'))
    ]


def get_stock_prefix(code: str) -> str:
    """根据股票代码判断沪/深前缀"""
    return "SH" if code.startswith("6") else "SZ"