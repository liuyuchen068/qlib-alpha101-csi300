# Qlib Recorder：实验管理

## 简介

Qlib 包含一个名为 `QlibRecorder` 的实验管理系统，旨在帮助用户高效地管理实验并分析结果。

系统包含三个组件：

- **ExperimentManager**：管理实验的类。
- **Experiment**：实验类，每个实例对应一个独立实验。
- **Recorder**：记录器类，每个实例负责一次运行（run）。

系统结构示例：

```
ExperimentManager
    - Experiment 1
        - Recorder 1
        - Recorder 2
        - ...
    - Experiment 2
        - Recorder 1
        - Recorder 2
        - ...
    - ...
```

该系统定义了一组接口，并提供了基于 MLFlow 的具体实现 `MLflowExpManager`（详见 https://mlflow.org/）。当配置使用 `MLflowExpManager` 时，可通过 `mlflow ui` 可视化查看实验结果。

## Qlib Recorder

`QlibRecorder` 封装了对实验管理系统的高级 API；在 Qlib 中以变量 `R` 暴露，用户可直接导入并使用：

```python
from qlib.workflow import R
```

`QlibRecorder` 提供了管理实验与记录器的常用接口，更多接口请参考下文关于 **Experiment Manager**、**Experiment** 与 **Recorder** 的章节。

## Experiment Manager

`ExpManager` 负责管理不同的实验。其核心 API 包括 `get_exp`（获取实验）和 `list_experiments`（列出实验）。其他接口如 `create_exp`、`delete_exp` 可参考 API 文档。

## Experiment

`Experiment` 类负责单个实验的生命周期管理（如 `start`、`end`），并提供与记录器相关的操作（如 `get_recorder`、`list_recorders`）。

Qlib 还会在使用某些便捷 API（如 `log_metrics` 或 `get_exp`）时自动创建并使用一个默认实验（默认名称为 `Experiment`），可在配置或初始化时修改该默认名称。

## Recorder

`Recorder` 类负责单次运行的记录工作，支持记录指标（`log_metrics`）、参数（`log_params`）等操作，便于追踪运行过程与产物。

重要 API（部分未在 `QlibRecorder` 中封装）示例：

- `list_artifacts`, `list_metrics`, `list_params`, `list_tags`

其他接口如 `save_objects`, `load_object` 请参阅 Recorder API 文档。

## Record Template（记录模板）

`RecordTemp` 类用于以特定格式生成实验结果（例如 IC、回测报告等）。Qlib 提供三类常用记录模板：

- **SignalRecord**：生成模型的预测信号结果。
- **SigAnaRecord**：生成模型的 IC、ICIR、Rank IC 与 Rank ICIR 等评估指标。
- **PortAnaRecord**：生成回测（backtest）结果，结合策略与回测配置得到回测报告与仓位信息。

示例：计算 IC 与 Long-Short Return

```python
from qlib.contrib.eva.alpha import calc_ic, calc_long_short_return
ic, ric = calc_ic(pred.iloc[:, 0], label.iloc[:, 0])
long_short_r, long_avg_r = calc_long_short_return(pred.iloc[:, 0], label.iloc[:, 0])
```

示例：基于预测进行回测并分析

```python
from qlib.contrib.strategy.strategy import TopkDropoutStrategy
from qlib.contrib.evaluate import backtest as normal_backtest, risk_analysis

STRATEGY_CONFIG = {"topk": 50, "n_drop": 5}
BACKTEST_CONFIG = {
    "limit_threshold": 0.095,
    "account": 100000000,
    "benchmark": BENCHMARK,
    "deal_price": "close",
    "open_cost": 0.0005,
    "close_cost": 0.0015,
    "min_cost": 5,
}

strategy = TopkDropoutStrategy(**STRATEGY_CONFIG)
report_normal, positions_normal = normal_backtest(pred_score, strategy=strategy, **BACKTEST_CONFIG)

analysis = dict()
analysis["excess_return_without_cost"] = risk_analysis(report_normal["return"] - report_normal["bench"])
analysis["excess_return_with_cost"] = risk_analysis(report_normal["return"] - report_normal["bench"] - report_normal["cost"])
analysis_df = pd.concat(analysis)
print(analysis_df)
```

## 已知限制

- Python 对象使用 pickle 保存，若保存环境与加载环境存在差异，可能导致无法反序列化或兼容性问题。