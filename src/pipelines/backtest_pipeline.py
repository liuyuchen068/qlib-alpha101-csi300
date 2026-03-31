import qlib
from qlib.constant import REG_CN

from src.utils.config import Config
from src.utils.env import limit_threads
from src.dataset.builder import DataBuilder
from src.model.lgb_model import ModelManager
from src.backtest.executor import BacktestExecutor


class BacktestPipeline:

    def __init__(self):
        limit_threads()
        self.cfg = Config("config/config.yaml")

    def run(self):
        qlib.init(provider_uri=self.cfg.data["qlib_path"], region=REG_CN)

        builder = DataBuilder(self.cfg)
        model_mgr = ModelManager(self.cfg)
        executor = BacktestExecutor(self.cfg)

        stocks = ["SH600000"]  # 示例
        cols = builder.feature_cols()
        dataset = builder.build(stocks, cols)

        model = model_mgr.create()
        pred = model_mgr.train_predict(model, dataset)

        strategy = {
            "class": "ScoreWeightedStrategy",
            "module_path": "src.strategy.score_strategy",
            "kwargs": {"signal": pred}
        }

        report, _ = executor.run(strategy)
        executor.save(report)