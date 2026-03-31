import logging
import numpy as np
import pandas as pd

from qlib.data import D
from qlib.contrib.strategy import WeightStrategyBase

logger = logging.getLogger(__name__)


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

        # 确保 score 是 Series
        if isinstance(score, pd.DataFrame):
            score = score.iloc[:, 0]

        # 确保 score 是数值类型
        score = score.astype(float)

        topk_scores = score.nlargest(self.topk)
        if len(topk_scores) == 0:
            return {}

        # 权重计算
        #min_s = topk_scores.min()
        #max_s = topk_scores.max()
        #if max_s == min_s:
        #    normalized = pd.Series(1.0 / len(topk_scores), index=topk_scores.index)
        #else:
        #    normalized = (topk_scores - min_s) / (max_s - min_s)

        #weights = (normalized / normalized.sum()) * (1.0 - self.cash_reserve)
        # 得分高的股票权重明显更大
        exp_scores = np.exp(topk_scores * 2)  # 2是调整参数，越大越集中
        weights = exp_scores / exp_scores.sum() * (1 - self.cash_reserve)
        return dict(weights)