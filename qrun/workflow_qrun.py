import numpy as np
import pandas as pd

from qlib.data import D
from qlib.contrib.strategy import WeightStrategyBase


class ScoreWeightedStrategy(WeightStrategyBase):
    """定义回测策略，确定回测所需的权重"""

    def __init__(self, topk=50, cash_reserve=0.05, normalize_method='minmax', **kwargs):
        """
        todo: 为参数添加说明，并对特殊的数据结构进行说明。例如：score 参数，是一个复杂数据类型，但是没有类型提示
        """
        super().__init__(**kwargs)
        self.topk = topk
        self.cash_reserve = cash_reserve
        self.normalize_method = normalize_method
    def generate_target_weight_position(self, score: pd.Series, current=None, **kwargs) -> dict:
        """
        score: pd.Series，index 是 stock_id，value 是模型预测分数（qlib 保证格式）
        """
        trade_start_time = kwargs.get('trade_start_time')
        trade_date_str = str(trade_start_time.date()) if hasattr(trade_start_time, 'date') else str(trade_start_time)

        # 过滤风险股票：收集需排除的代码，不修改原始 score
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

        # 用布尔掩码过滤，不做 drop（immutable 方式）
        valid_score = score[~score.index.isin(exclude_codes)]

        # qlib 保证 score 是 pd.Series 且值为 float，无需类型判断和强制转换
        topk_scores = valid_score.nlargest(self.topk)
        if len(topk_scores) == 0:
            return {}

        # 得分高的股票权重明显更大
        exp_scores = np.exp(topk_scores * 2)  # 2是调整参数，越大越集中
        weights = exp_scores / exp_scores.sum() * (1 - self.cash_reserve)
        return dict(weights)
