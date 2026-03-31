import qlib
from qlib.constant import REG_CN

from src.utils.config import Config
from src.utils.env import limit_threads
from src.dataset.builder import DataBuilder
from src.model.lgb_model import ModelManager
from src.backtest.executor import BacktestExecutor


import logging
import multiprocessing
import os

import qlib
from qlib.constant import REG_CN

from src.utils.config import Config, DirectoryManager
from src.utils.logger import setup_logging, limit_threads
from src.dataset.builder import DataBuilder
from src.model.lgb_model import ModelManager
from src.backtest.executor import BacktestExecutor

logger = setup_logging("BacktestPipeline")


class BacktestExperiment:
    """整个回测实验的协调者"""

    def __init__(self):
        limit_threads()
        self.config = Config("config.yaml")
        self.dir_manager = DirectoryManager(self.config)
        self.data_builder = DataBuilder(self.config)
        self.model_manager = ModelManager(self.config)
        self.backtest_executor = BacktestExecutor(self.config)

    def run(self):
        try:
            # 准备环境
            multiprocessing.freeze_support()
            self.dir_manager.prepare()

            # 初始化 qlib
            qlib.init(
                provider_uri=os.path.expanduser(self.config.data["qlib_path"]),
                region=REG_CN,
                skip_if_reg=True
            )
            logger.info(f"QLIB 初始化完成：{self.config.data['qlib_path']}")

            # 数据准备
            stock_list = self.data_builder.get_stock_list()
            feature_cols = self.data_builder.get_feature_columns()
            dataset = self.data_builder.build_dataset(stock_list, feature_cols)

            # 模型训练与预测
            model = self.model_manager.create_model()
            predictions = self.model_manager.train_and_predict(model, dataset)

            # 回测执行
            strategy_cfg = self.backtest_executor.create_strategy_config(predictions)
            report, positions = self.backtest_executor.run(strategy_cfg)

            # 保存结果
            self.backtest_executor.save_results(report, positions)

            logger.info("完整回测实验执行成功！")

        except Exception as e:
            logger.error(f"回测实验失败：{e}", exc_info=True)
            raise