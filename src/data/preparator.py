import logging
import time
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np

from jqdatasdk import get_price, get_index_stocks
from jqdatasdk import alpha101
from jqdatasdk import get_extras
from jqdatasdk.alpha101 import *

from src.utils.config import Config
from src.utils.logger import setup_logging
from src.utils.env import authenticate_jqdata
from src.data.utils import get_trade_dates
from src.data.risk import add_risk_flags


class DataPreparator:
    """数据准备器（面向对象封装）"""

    def __init__(self, config: Config):
        """初始化：加载配置、设置日志、认证聚宽"""
        self.config = config
        self.logger = setup_logging("DataPreparator")
        authenticate_jqdata()

        # 从配置中读取常用参数
        self.start_date = self.config.date["data_start_date"]
        self.end_date = self.config.date["data_end_date"]
        self.basic_cols = self.config.feature["basic_cols"].splitlines()
        self.trade_dates = get_trade_dates(self.start_date, self.end_date)
        self.n_factors = self.config.model.get("alpha_factors", 10)
        self.qlib_output_dir = Path(self.config.data["my_qlib_path"]).expanduser()
        self.st_cache = {}
        self.prev_close_cache = {}

        if not self.trade_dates:
            raise ValueError("config.yaml 中缺少 trade_dates 列表")

        self.logger.info("DataPreparator 初始化完成")

    def get_previous_close(self, df_close: pd.DataFrame) -> dict:
        return dict(zip(df_close['code'], df_close['close']))

    def fetch_daily_data(self, date_str: str, prev_close_dict: Optional[dict] = None) -> Optional[pd.DataFrame]:
        """获取单日沪深300成分股的行情 + Alpha因子"""
        if prev_close_dict is None:
            prev_close_dict = {}

        date_obj = pd.to_datetime(date_str)
        if date_obj < pd.to_datetime(self.start_date) or date_obj > pd.to_datetime(self.end_date):
            return None

        try:
            stocks = get_index_stocks("000300.XSHG", date=date_str)
            if not stocks:
                self.logger.warning(f"{date_str} 无沪深300成分股")
                return None

            # 获取当日行情（前复权）
            df_price = get_price(
                stocks,
                start_date=date_str,
                end_date=date_str,
                frequency="daily",
                fields=self.basic_cols,
                skip_paused=False,  # 包含停牌数据
                fq="pre"
            )

            if df_price.empty:
                self.logger.warning(f"{date_str} 无行情数据")
                return None

            # 处理缺失行，检查无缺失
            actual_codes = set(df_price['code'].unique())
            all_codes = set(stocks)
            missing_codes = all_codes - actual_codes

            # 处理缺失行
            if missing_codes:
                missing_rows = []
                for code in missing_codes:
                    missing_rows.append({
                        'code': code,
                        'open': np.nan,
                        'close': np.nan,
                        'high': np.nan,
                        'low': np.nan,
                        'volume': 0,
                        'money': 0,
                        'time': pd.to_datetime(date_str)
                    })

                df_missing = pd.DataFrame(missing_rows)
                df_price = pd.concat([df_price, df_missing], ignore_index=True)
                self.logger.debug(f"{date_str} 添加了 {len(missing_rows)} 行缺失数据")

            # 处理ST列
            df_st = get_extras('is_st', security_list=stocks, start_date=date_str, end_date=date_str, df=True)
            st_row = df_st.iloc[0]
            st_dict = {
                code: (1 if st_row[code] else 0)
                for code in stocks
            }
            df_price['is_st'] = df_price['code'].map(st_dict).fillna(0).astype(int)

            # 标准化time列
            df_price["date"] = df_price["time"].dt.strftime("%Y-%m-%d")
            df_price = df_price.drop(columns=['time'], errors='ignore')

            # 增加权重factor列
            df_price["factor"] = 1.0

            # 处理缺失值
            for code in stocks:
                if code not in prev_close_dict:
                    prev_close_dict[code] = 0

            # 添加风险标志列
            df_price = add_risk_flags(df_price, prev_close_dict)

            # 逐个添加 Alpha101 因子
            for i in range(1, self.n_factors + 1):
                alpha_name = f"alpha_{i:03d}"
                try:
                    func = getattr(alpha101, alpha_name)   # 从alpha101模块中获取函数
                    result = func(date_str, stocks)

                    if isinstance(result, pd.Series):
                        df_alpha = pd.DataFrame({
                            "code": result.index,
                            alpha_name: result.values
                        })

                        df_price = df_alpha.merge(df_price, on="code", how="left")

                    time.sleep(0.08)  # 防频控

                except Exception as e:
                    self.logger.error(f"{date_str} {alpha_name} 获取失败: {e}")

            self.logger.info(f"{date_str} 数据获取完成，{len(df_price)} 行")
            return df_price

        except Exception as e:
            self.logger.error(f"{date_str} 获取失败: {e}")
            return None

    def collect_all_data(self) -> pd.DataFrame:
        """遍历所有交易日，收集完整数据集"""
        all_dfs = []
        prev_close_dict = {}

        for idx, date_str in enumerate(self.trade_dates, 1):
            df_day = self.fetch_daily_data(date_str, prev_close_dict)
            if df_day is not None:
                all_dfs.append(df_day)
                prev_close_dict = self.get_previous_close(df_day[['code', 'close']].drop_duplicates(subset=['code']))
            if idx % 5 == 0:
                self.logger.info(f"已处理 {idx}/{len(self.trade_dates)} 个交易日")

        if not all_dfs:
            raise RuntimeError("没有任何交易日的数据被成功获取")

        df_final = pd.concat(all_dfs, ignore_index=True)

        # 保证列顺序
        base_cols = self.basic_cols + ["code", "date", "factor", "is_suspended", "is_limit_up", "is_limit_down", "is_st"]
        alpha_cols = [f"alpha_{i:03d}" for i in range(1, self.n_factors + 1)]
        final_cols = base_cols + [c for c in alpha_cols if c in df_final.columns]

        df_final = df_final[final_cols].sort_values(["code", "date"]).reset_index(drop=True)
        df_final["code"] = df_final["code"].str.split(".").str[0]
        self.logger.info(f"总计收集 {len(df_final)} 行，{df_final['code'].nunique()} 只股票")
        return df_final

    def save_to_qlib_format(self, df: pd.DataFrame):
        """按 qlib 格式保存为单股票 csv 文件"""
        self.qlib_output_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for code, group in df.groupby("code"):
            try:
                prefix = "SH" if code.startswith("6") else "SZ"
                filename = f"{prefix}{code}.csv"

                group = group.sort_values("date")
                group.to_csv(self.qlib_output_dir / filename, index=False)
                saved_count += 1

            except Exception as e:
                self.logger.error(f"保存 {code} 失败: {e}")

        self.logger.info(f"已保存 {saved_count} 只股票数据到 {self.qlib_output_dir}")

    def run(self):
        """完整执行流程"""
        self.logger.info("===== 开始沪深300数据准备 =====")
        df_all = self.collect_all_data()
        self.save_to_qlib_format(df_all)
        self.logger.info("===== 数据准备完成 =====")