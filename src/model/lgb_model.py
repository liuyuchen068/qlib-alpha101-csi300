import logging
import pandas as pd

from qlib.contrib.model import LGBModel
from qlib.data.dataset import DatasetH

from src.utils.config import Config

logger = logging.getLogger(__name__)


class ModelManager:
    """模型创建、训练、预测"""

    def __init__(self, config: Config):
        self.cfg = config.model

    def create_model(self) -> LGBModel:
        model = LGBModel(
            loss=self.cfg["loss"],
            early_stopping_rounds=self.cfg["early_stopping_rounds"],
            num_boost_round=self.cfg["num_boost_round"],
            learning_rate=self.cfg["learning_rate"],
            num_leaves=self.cfg["num_leaves"],
            max_depth=self.cfg["max_depth"]
        )
        logger.info("LGBModel 创建完成")
        return model

    def train_and_predict(self, model: LGBModel, dataset: DatasetH) -> pd.Series:
        logger.info("开始训练模型...")
        model.fit(dataset)
        logger.info("模型训练完成")

        logger.info("生成测试期预测信号...")
        pred = model.predict(dataset, segment="test")
        return pred