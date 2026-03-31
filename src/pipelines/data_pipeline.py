import logging

from src.utils.config import Config
from src.utils.logger import setup_logging
from src.data.preparator import DataPreparator

logger = setup_logging("DataPipeline")


class DataPipeline:
    """数据准备流水线的协调者"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)

    def run(self):
        try:
            preparator = DataPreparator(self.config)
            preparator.run()
        except Exception as e:
            logger.error(f"数据准备流水线异常终止: {e}", exc_info=True)
            raise