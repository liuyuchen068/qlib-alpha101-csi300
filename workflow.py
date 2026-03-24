"""
面向对象版本的 Qlib + LightGBM 沪深300成分股量化回测流程
2025-2026 风格重构：职责清晰、组合优于继承、易测试、易扩展
"""
import os
import logging
from pathlib import Path
import yaml
import multiprocessing
import pandas as pd

import qlib
from qlib.data import D
from qlib.constant import REG_CN
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.loader import QlibDataLoader
from qlib.contrib.evaluate import backtest_daily
from qlib.contrib.model import LGBModel
from qlib.contrib.strategy import WeightStrategyBase
#from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy

# ─── 日志配置 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def limit_threads():
    """限制多线程，防止 lightgbm / numpy 过度并行"""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"


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
    

    @staticmethod
    def create_data_loader(feature_cols: list[str]) -> QlibDataLoader:
        feature_names = [c.replace("$", "") for c in feature_cols]
        return QlibDataLoader(
            config={
                "feature": (feature_cols, feature_names),
                "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL"])
            }
        )

    def build_dataset(self, stock_list: list[str], feature_cols: list[str]) -> DatasetH:
        start = self.config.date["train_start"]
        seg = self.config.date["train_end"]
        end = self.config.date["test_end"]

        handler = DataHandlerLP(
            instruments=stock_list,
            start_time=start,
            end_time=end,
            data_loader=self.create_data_loader(feature_cols),
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


class ScoreWeightedStrategy(WeightStrategyBase):
    """定义回测策略，确定回测所需的权重"""
    
    def __init__(self, topk=50, cash_reserve=0.05, normalize_method='minmax', **kwargs):
        super().__init__(**kwargs)
        self.topk = topk
        self.cash_reserve = cash_reserve
        self.normalize_method = normalize_method
    
    def generate_target_weight_position(self, score, current=None, **kwargs) -> dict:
        trade_start_time = kwargs.get('trade_start_time')
        trade_date_str = str(trade_start_time.date()) if hasattr(trade_start_time, 'date') else str(trade_start_time)
    
        # 过滤风险股票
        exclude_codes = set()
        for code_short in score.index:
            try:
                fields = ["$is_suspended", "$is_limit_up", "$is_limit_down", "$is_st"]
                feat = D.features(instruments=[code_short], fields=fields, 
                               start_time=trade_date_str, end_time=trade_date_str)
                if feat is not None and len(feat) > 0:
                    row = feat.iloc[0]
                    if (row["is_suspended"] == 1 or row["is_limit_up"] == 1 or 
                    row["is_limit_down"] == 1 or row["is_st"] == 1):
                        exclude_codes.add(code_short)
            except:
                pass
    
        score = score.drop(exclude_codes, errors="ignore")
        topk_scores = score.nlargest(self.topk)
        if len(topk_scores) == 0:
            return {}
        
        # 权重计算
        min_s = topk_scores.min()
        max_s = topk_scores.max()
        if max_s == min_s:
            normalized = pd.Series(1.0 / len(topk_scores), index=topk_scores.index)
        else:
            normalized = (topk_scores - min_s) / (max_s - min_s)
        
        weights = (normalized / normalized.sum()) * (1.0 - self.cash_reserve)
        return dict(weights)


class BacktestExecutor:
    """回测执行与结果处理"""

    def __init__(self, config: Config):
        self.config = config

    def create_strategy_config(self, predictions: pd.Series) -> dict:
        return {
            "class": "ScoreWeightedStrategy",
            "module_path": "workflow",
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
        )
        logger.info("回测执行完成")
        return report, positions

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


if __name__ == "__main__":
    experiment = BacktestExperiment()
    experiment.run()

