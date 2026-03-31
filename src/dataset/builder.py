import logging
from pathlib import Path
import pandas as pd

from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP

from src.utils.config import Config
from src.dataset.loader import create_data_loader

logger = logging.getLogger(__name__)


class DataBuilder:
    """负责数据准备：股票列表、特征、DataLoader、Dataset"""

    def __init__(self, config: Config):
        self.config = config

    def get_stock_list(self) -> list[str]:
        file_path = Path(self.config.data["input_file"])
        if not file_path.exists():
            raise FileNotFoundError(f"股票列表文件不存在: {file_path}")

        df = pd.read_csv(file_path)
        stocks = df.iloc[:, 0].astype(str).tolist()
        logger.info(f"加载 {len(stocks)} 只股票")
        return stocks

    def get_feature_columns(self) -> list[str]:
        n = self.config.model["alpha_factors"]
        alpha_cols = [f"$alpha_{i:03d}" for i in range(1, n + 1)]
        risk_cols = ["$is_suspended", "$is_limit_up", "$is_limit_down", "$is_st"]
        cols = ["$close", "$volume"] + alpha_cols + risk_cols
        logger.info(f"特征列数量：{len(cols)}")
        return cols

    def build_dataset(self, stock_list: list[str], feature_cols: list[str]) -> DatasetH:
        start = self.config.date["train_start"]
        seg = self.config.date["train_end"]
        end = self.config.date["test_end"]

        handler = DataHandlerLP(
            instruments=stock_list,
            start_time=start,
            end_time=end,
            data_loader=create_data_loader(feature_cols),
            infer_processors=[{"class": "Fillna", "kwargs": {"fields_group": "feature"}}],
            learn_processors=[{"class": "DropnaLabel", "kwargs": {}}],
        )

        dataset = DatasetH(
            handler=handler,
            segments={
                "train": (start, seg),
                "test": (seg, end),
            }
        )
        logger.info(f"数据集构建完成  训练:{start} ~ {seg}  测试:{seg} ~ {end}")
        return dataset