.. _strategy:

========================================
投资组合策略：组合管理
========================================
.. currentmodule:: qlib

简介
====

``投资组合策略（Portfolio Strategy）`` 用于采用不同的组合构建算法，即用户可以根据 ``预测模型（Forecast Model）`` 的预测分数选择不同的算法来生成投资组合。用户可以在 `Workflow` 模块的自动化工作流中使用 ``投资组合策略``，详见 `工作流：工作流管理 <workflow.html>`_。

由于 Qlib 的组件采用松耦合设计，``投资组合策略`` 也可以作为独立模块使用。

Qlib 提供了若干已实现的组合策略，同时也支持用户自定义策略，用户可按自身需求定制策略。

当用户指定好模型（预测信号）和策略后，运行回测可用于检验自定义模型（预测信号）/策略的表现。

基类与接口
============

BaseStrategy
------------

Qlib 提供了基类 ``qlib.strategy.base.BaseStrategy``。所有策略类需继承该基类并实现其接口。

- `generate_trade_decision`
    - `generate_trade_decision` 是一个关键接口，用于在每个交易周期生成交易决策。
    - 调用该方法的频率取决于执行器的频率（默认 `time_per_step="day"`）。但交易频率可由用户在实现中决定。
    - 例如，当执行器的 `time_per_step` 为 `day`，但用户希望按周交易时，可以每周返回非空的 TradeDecision（其它时间返回空），示例见 `此处 <https://github.com/microsoft/qlib/blob/main/qlib/contrib/strategy/signal_strategy.py#L132>`_。

用户可继承 `BaseStrategy` 来自定义策略类。

WeightStrategyBase
------------------

Qlib 还提供了子类 ``qlib.contrib.strategy.WeightStrategyBase``，它继承自 `BaseStrategy`。

`WeightStrategyBase` 关注于目标仓位（target positions），并能根据目标仓位自动生成委托单列表。它提供了 `generate_target_weight_position` 接口：

- `generate_target_weight_position`
    - 根据当前持仓与交易日生成目标仓位（输出为权重分布，不考虑现金）。
    - 返回目标仓位。

    .. note::
        这里的 `目标仓位` 指的是总资产中的目标占比（百分比）。

`WeightStrategyBase` 实现了 `generate_order_list` 接口，其处理流程如下：

- 调用 `generate_target_weight_position` 生成目标仓位。
- 将目标仓位转换为目标持仓数量。
- 根据目标持仓数量生成委托单列表。

用户可以继承 `WeightStrategyBase` 并实现 `generate_target_weight_position`，仅需关注目标仓位的生成。

已实现的策略
=============

Qlib 提供了已实现的策略类 `TopkDropoutStrategy`。

TopkDropoutStrategy
-------------------

`TopkDropoutStrategy` 继承自 `BaseStrategy`，并实现了 `generate_order_list` 接口，处理流程如下：

- 采用 "Topk-Drop" 算法计算每只股票的目标持仓数量。

    .. note::
        ``Topk-Drop`` 算法包含两个参数：

        - `Topk`：持仓股票数
        - `Drop`：每个交易日卖出的股票数

        通常当前持仓数为 `Topk`（交易初期可能为 0）。对于每个交易日，令 $d$ 为当前持仓中在按预测分数从高到低排序时排名 > K 的股票数量。
        此时，会卖出这 `d` 只当前持仓中预测分数最差的股票，并买入相同数量在未持仓中预测分数最好的股票。

        一般情况下 $d=$`Drop`（当候选池大、K 大且 `Drop` 较小时亦然）。

        在大多数场景中，``TopkDrop`` 算法每天卖出并买入 `Drop` 支股票，因此大致换手率为 2×`Drop`/`K`。

        下图展示了典型场景：

        .. image:: ../_static/img/topk_drop.png
            :alt: Topk-Drop


- 根据目标持仓数量生成委托单列表。

EnhancedIndexingStrategy
------------------------

`EnhancedIndexingStrategy`（增强指数化策略）将主动管理与被动跟踪结合，目标是在控制风险敞口（即跟踪误差）的同时，力争在组合收益上跑赢基准指数（例如 S&P 500）。

更多信息见 `qlib.contrib.strategy.signal_strategy.EnhancedIndexingStrategy` 与 `qlib.contrib.strategy.optimizer.enhanced_indexing.EnhancedIndexingOptimizer`。

使用与示例
===========

首先，用户应生成预测信号（变量名在下例中为 ``pred_score``）。

预测分数（Prediction Score）
---------------------------

`prediction score` 为 pandas DataFrame，其索引为 <datetime(pd.Timestamp), instrument(str)>，并且必须包含 `score` 列。

预测示例格式如下：

.. code-block:: python

      datetime instrument     score
    2019-01-04   SH600000 -0.505488
    2019-01-04   SZ002531 -0.320391
    2019-01-04   SZ000999  0.583808
    2019-01-04   SZ300569  0.819628
    2019-01-04   SZ001696 -0.137140
                 ...            ...
    2019-04-30   SZ000996 -1.027618
    2019-04-30   SH603127  0.225677
    2019-04-30   SH603126  0.462443
    2019-04-30   SH603133 -0.302460
    2019-04-30   SZ300760 -0.126383

`Forecast Model` 模块可生成预测，详见 `预测模型：模型训练与预测 <model.html>`_。

通常预测分数是模型的输出，但某些模型训练的标签尺度不同，因而预测分数的数值尺度可能与预期（例如资产收益）不同。

Qlib 未对所有模型输出进行统一尺度化，原因包括：
- 并非所有策略都关心分数的绝对尺度（例如 `TopkDropoutStrategy` 只关心排名顺序），因此由策略负责对预测分数做必要的重标度（对于基于组合优化的策略，分数需要有意义的尺度）。
- 模型可以灵活定义目标、损失与数据处理流程，因此不存在一种对所有模型统一适用的通用反向尺度化方法。如果需要将分数恢复到有意义的值（例如股票收益），一种直观的做法是基于模型近期输出与近期真实目标值训练一个回归模型来完成尺度映射。

运行回测
--------

- 在大多数情况下，用户可使用 `backtest_daily` 对其组合管理策略进行回测：

    .. code-block:: python

        from pprint import pprint

        import qlib
        import pandas as pd
        from qlib.utils.time import Freq
        from qlib.utils import flatten_dict
        from qlib.contrib.evaluate import backtest_daily
        from qlib.contrib.evaluate import risk_analysis
        from qlib.contrib.strategy import TopkDropoutStrategy

        # 初始化 qlib
        qlib.init(provider_uri=<qlib data dir>)

        CSI300_BENCH = "SH000300"
        STRATEGY_CONFIG = {
            "topk": 50,
            "n_drop": 5,
            # pred_score, pd.Series
            "signal": pred_score,
        }


        strategy_obj = TopkDropoutStrategy(**STRATEGY_CONFIG)
        report_normal, positions_normal = backtest_daily(
            start_time="2017-01-01", end_time="2020-08-01", strategy=strategy_obj
        )
        analysis = dict()
        # 默认频率为日频（即 "day"）
        analysis["excess_return_without_cost"] = risk_analysis(report_normal["return"] - report_normal["bench"])
        analysis["excess_return_with_cost"] = risk_analysis(report_normal["return"] - report_normal["bench"] - report_normal["cost"])

        analysis_df = pd.concat(analysis)  # type: pd.DataFrame
        pprint(analysis_df)


- 若用户需在更细的层面控制策略（例如使用更高级的 executor），可参考下例：

    .. code-block:: python

        from pprint import pprint

        import qlib
        import pandas as pd
        from qlib.utils.time import Freq
        from qlib.utils import flatten_dict
        from qlib.backtest import backtest, executor
        from qlib.contrib.evaluate import risk_analysis
        from qlib.contrib.strategy import TopkDropoutStrategy

        # 初始化 qlib
        qlib.init(provider_uri=<qlib data dir>)

        CSI300_BENCH = "SH000300"
        # Benchmark 用于计算策略的超额收益，其数据格式为单只基准标的（例如 SH000300）

        FREQ = "day"
        STRATEGY_CONFIG = {
            "topk": 50,
            "n_drop": 5,
            # pred_score, pd.Series
            "signal": pred_score,
        }

        EXECUTOR_CONFIG = {
            "time_per_step": "day",
            "generate_portfolio_metrics": True,
        }

        backtest_config = {
            "start_time": "2017-01-01",
            "end_time": "2020-08-01",
            "account": 100000000,
            "benchmark": CSI300_BENCH,
            "exchange_kwargs": {
                "freq": FREQ,
                "limit_threshold": 0.095,
                "deal_price": "close",
                "open_cost": 0.0005,
                "close_cost": 0.0015,
                "min_cost": 5,
            },
        }

        # 策略对象
        strategy_obj = TopkDropoutStrategy(**STRATEGY_CONFIG)
        # 执行器对象
        executor_obj = executor.SimulatorExecutor(**EXECUTOR_CONFIG)
        # 回测
        portfolio_metric_dict, indicator_dict = backtest(executor=executor_obj, strategy=strategy_obj, **backtest_config)
        analysis_freq = "{0}{1}".format(*Freq.parse(FREQ))
        # 获取回测报告
        report_normal, positions_normal = portfolio_metric_dict.get(analysis_freq)

        # 分析
        analysis = dict()
        analysis["excess_return_without_cost"] = risk_analysis(
            report_normal["return"] - report_normal["bench"], freq=analysis_freq
        )
        analysis["excess_return_with_cost"] = risk_analysis(
            report_normal["return"] - report_normal["bench"] - report_normal["cost"], freq=analysis_freq
        )

        analysis_df = pd.concat(analysis)  # type: pd.DataFrame
        # 记录指标
        analysis_dict = flatten_dict(analysis_df["risk"].unstack().T.to_dict())
        # 输出结果
        pprint(f"The following are analysis results of benchmark return({analysis_freq}).")
        pprint(risk_analysis(report_normal["bench"], freq=analysis_freq))
        pprint(f"The following are analysis results of the excess return without cost({analysis_freq}).")
        pprint(analysis["excess_return_without_cost"])
        pprint(f"The following are analysis results of the excess return with cost({analysis_freq}).")
        pprint(analysis["excess_return_with_cost"])

结果
----

回测结果示例：

.. code-block:: python

                                                      risk
    excess_return_without_cost mean               0.000605
                               std                0.005481
                               annualized_return  0.152373
                               information_ratio  1.751319
                               max_drawdown      -0.059055
    excess_return_with_cost    mean               0.000410
                               std                0.005478
                               annualized_return  0.103265
                               information_ratio  1.187411
                               max_drawdown      -0.075024


- `excess_return_without_cost`
    - `mean`
        `CAR`（累计超额收益）不计成本的均值
    - `std`
        `CAR`（累计超额收益）不计成本的标准差
    - `annualized_return`
        `CAR`（累计超额收益）不计成本的年化收益率
    - `information_ratio`
        不计成本的信息比，详见 Information Ratio – IR: https://www.investopedia.com/terms/i/informationratio.asp
    - `max_drawdown`
        `CAR`（累计超额收益）不计成本的最大回撤，详见 Maximum Drawdown (MDD): https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp

- `excess_return_with_cost`
    - `mean`
        `CAR`（累计超额收益）计入成本后的均值
    - `std`
        `CAR`（累计超额收益）计入成本后的标准差
    - `annualized_return`
        `CAR`（累计超额收益）计入成本后的年化收益率
    - `information_ratio`
        计入成本的信息比
    - `max_drawdown`
        `CAR`（累计超额收益）计入成本后的最大回撤

参考
====

有关预测分数 `pred_score`（由 `Forecast Model` 输出）的更多信息，请参阅 `预测模型：模型训练与预测 <model.html>`_。
