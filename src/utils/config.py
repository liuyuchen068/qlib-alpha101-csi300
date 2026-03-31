import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class Config:
    """负责读取和提供配置的统一入口"""

    def __init__(self, path: str):
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            logger.error(f"配置文件不存在: {self.path}")
            raise FileNotFoundError(str(self.path))

        with self.path.open(encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"配置加载成功：{self.path}")
        return config

    @property
    def data(self) -> dict:
        return self._data["data"]

    @property
    def date(self) -> dict:
        return self._data["date"]

    @property
    def model(self) -> dict:
        return self._data["model"]

    @property
    def strategy(self) -> dict:
        return self._data["strategy"]

    @property
    def backtest(self) -> dict:
        return self._data["backtest"]

    @property
    def feature(self) -> dict:
        return self._data["feature"]


class DirectoryManager:
    """负责创建和管理输出目录"""

    def __init__(self, config: Config):
        self.config = config

    def prepare(self):
        paths = [
            self.config.backtest["output_dir"]
        ]
        for p in paths:
            Path(p).mkdir(parents=True, exist_ok=True)
            logger.info(f"目录已准备：{p}")