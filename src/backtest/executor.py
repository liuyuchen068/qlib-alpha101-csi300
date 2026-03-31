import logging
from pathlib import Path
import pandas as pd

from qlib.data import D
from qlib.contrib.evaluate import backtest_daily

from src.utils.config import Config

logger = logging.getLogger(__name__)


class BacktestExecutor:
    """回测执行与结果处理"""

    def __init__(self, config: Config):
        self.config = config

    def create_strategy_config(self, predictions: pd.Series) -> dict:
        # fixme： 我在全局中没有搜索到任何一个地方使用这个函数？什么意思？：应该是在src/pipelines/backtest_pipeline.py中使用,上次提交版本存在问题，已经补上了
        return {
            "class": "ScoreWeightedStrategy",
            "module_path": "src.strategy.score_strategy",
            "kwargs": {
                "signal": predictions,
                "topk": self.config.strategy["topk"],
                "cash_reserve": self.config.strategy.get("cash_reserve", 0.05),
                "normalize_method": self.config.strategy.get("normalize_method", "minmax"),
            }
        }

    def run(self, strategy_cfg: dict) -> tuple[pd.DataFrame, dict | None]:
        logger.info("开始执行回测...")
        report, positions = backtest_daily(
            start_time=self.config.date["backtest_start"],
            end_time=self.config.date["backtest_end"],
            strategy=strategy_cfg,
            account=self.config.backtest["account"],
            benchmark=self.config.strategy["benchmark"],
            exchange_kwargs={
                "deal_price": "close",
                "open_cost": 0.00005,
                "close_cost": 0.00015,
                "min_cost": 5,
            }
        )
        logger.info("回测执行完成")
        return report, positions

    # todo 同样搜不到：应该是在src/pipelines/backtest_pipeline.py中使用,上次提交版本存在问题，已经补上了
    def save_results(self, report: pd.DataFrame, positions: dict | None):
        output_dir = Path(self.config.backtest["output_dir"])

        # 处理日期索引
        trading_dates = D.calendar(
            start_time=self.config.date["backtest_start"],
            end_time=self.config.date["backtest_end"]
        )
        date_strs = [str(d.date()) for d in trading_dates]

        if len(report) == len(date_strs):
            report.index = date_strs

        report = report.reset_index(names="date")

        # 保存报告
        report_path = output_dir / "backtest_report.csv"
        report.to_csv(report_path, index=False)
        logger.info(f"回测报告已保存：{report_path}")

        # 保存持仓（如果有）
        if positions and len(positions) > 0:
            positions_df = pd.DataFrame(list(positions.values()))
            pos_path = output_dir / "backtest_positions.csv"
            positions_df.to_csv(pos_path, index=False)
            logger.info(f"持仓记录已保存：{pos_path}")
        else:
            logger.warning("本次回测无持仓记录")