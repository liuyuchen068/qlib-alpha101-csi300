.. _highfreq:

========================================================================
高频交易嵌套决策执行框架设计
========================================================================
.. currentmodule:: qlib

简介
====

日级交易（例如投资组合管理）与日内交易（例如订单执行）是量化投资中的两个热门研究方向，通常被分别研究。

为了获得日级与日内交易联合的整体收益，二者需要互相交互并在回测中联合运行。要支持多层次联合回测，需要相应的框架。目前公开的高频交易框架通常未考虑多层次联合交易，因此上述联合回测的结果可能并不准确。

除了回测，来自不同层次的策略相互之间也并非独立，彼此会互相影响。例如，当订单执行策略提升后（例如更低的执行成本或更高的成交率），此前由于高换手率而不被选的组合策略，可能会变得更优。要实现整体的良好表现，有必要同时考虑不同层次策略之间的相互作用。

因此，有必要设计一个新的多层次交易框架来解决上述问题。为此，我们设计了一个考虑策略相互作用的嵌套决策执行框架（nested decision execution framework）。

.. image:: ../_static/img/framework.svg

上图中间黄色部分展示了框架设计。每一层由 `Trading Agent`（交易代理）和 `Execution Env`（执行环境）组成。`Trading Agent` 包含其自身的数据处理模块（`Information Extractor`）、预测模块（`Forecast Model`）以及决策生成器（`Decision Generator`）。交易算法基于 `Forecast Module` 输出的信号由 `Decision Generator` 生成决策，生成的决策传递到 `Execution Env`，执行环境返回执行结果。

交易算法的频率、决策内容与执行环境可由用户自定义（例如日内交易、日频交易、周频交易等）。执行环境可以嵌套更细粒度的交易算法和执行环境（即图中的子工作流，例如将日频订单在日内进一步分解为更细粒度的决策）。嵌套决策执行框架的灵活性便于用户探索不同层次策略组合的效果，并打破不同层次交易算法之间的优化壁垒。

该嵌套决策执行框架的优化可借助 `QlibRL <./rl/overall.html>`_ 实现。欲了解如何使用 QlibRL，请参阅 API 参考：`RL API <../reference/api.html#rl>`_。

示例
=====

高频嵌套决策执行框架的示例代码见：`此处 <https://github.com/microsoft/qlib/blob/main/examples/nested_decision_execution/workflow.py>`_

此外，以下为 Qlib 中与高频交易相关的其它工作/示例：

- `基于高频数据的预测 <https://github.com/microsoft/qlib/tree/main/examples/highfreq#benchmarks-performance-predicting-the-price-trend-in-high-frequency-data>`_
- `示例：orderbook_data <https://github.com/microsoft/qlib/blob/main/examples/orderbook_data/>`，展示如何从非固定频率的高频数据中提取特征。
- `相关论文/项目 <https://github.com/microsoft/qlib/tree/high-freq-execution#high-frequency-execution>`_，关于高频执行的研究。
