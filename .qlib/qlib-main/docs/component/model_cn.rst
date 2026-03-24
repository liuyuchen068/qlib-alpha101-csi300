.. _model:

===========================================
预测模型：模型训练与预测
===========================================

简介
====

``预测模型（Forecast Model）`` 用于对股票给出 `预测分数（prediction score）`。用户可以在自动化工作流中通过 `qrun` 使用 ``预测模型``，详情请参见 `工作流：工作流管理 <workflow.html>`_。

由于 Qlib 的组件设计为松耦合，``预测模型`` 也可以作为独立模块使用。

基类与接口
============

``Qlib`` 提供了一个基类 `qlib.model.base.Model <../reference/api.html#module-qlib.model.base>`_，所有模型应继承自此类。

该基类提供如下接口：

.. autoclass:: qlib.model.base.Model
    :members:
    :noindex:

``Qlib`` 还提供了基类 `qlib.model.base.ModelFT <../reference/api.html#qlib.model.base.ModelFT>`_，包含用于微调（finetune）模型的方法。

关于诸如 `finetune` 的其他接口，请参阅 `模型 API <../reference/api.html#module-qlib.model.base>`_。

示例
=====

``Qlib`` 的 `Model Zoo` 中包含如 ``LightGBM``, ``MLP``, ``LSTM`` 等模型，这些模型作为预测模型的基线。下面示例展示如何将 ``LightGBM`` 作为独立模块运行。

- 首先使用 `qlib.init` 初始化 Qlib（参见 `初始化 <../start/initialization.html>`_）。
- 使用下列代码获取 `prediction score`（`pred_score`）：

.. code-block:: Python

    from qlib.contrib.model.gbdt import LGBModel
    from qlib.contrib.data.handler import Alpha158
    from qlib.utils import init_instance_by_config, flatten_dict
    from qlib.workflow import R
    from qlib.workflow.record_temp import SignalRecord, PortAnaRecord

    market = "csi300"
    benchmark = "SH000300"

    data_handler_config = {
        "start_time": "2008-01-01",
        "end_time": "2020-08-01",
        "fit_start_time": "2008-01-01",
        "fit_end_time": "2014-12-31",
        "instruments": market,
    }

    task = {
        "model": {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": {
                "loss": "mse",
                "colsample_bytree": 0.8879,
                "learning_rate": 0.0421,
                "subsample": 0.8789,
                "lambda_l1": 205.6999,
                "lambda_l2": 580.9768,
                "max_depth": 8,
                "num_leaves": 210,
                "num_threads": 20,
            },
        },
        "dataset": {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": data_handler_config,
                },
                "segments": {
                    "train": ("2008-01-01", "2014-12-31"),
                    "valid": ("2015-01-01", "2016-12-31"),
                    "test": ("2017-01-01", "2020-08-01"),
                },
            },
        },
    }

    # 模型初始化
    model = init_instance_by_config(task["model"])
    dataset = init_instance_by_config(task["dataset"])

    # 启动实验
    with R.start(experiment_name="workflow"):
        # 训练
        R.log_params(**flatten_dict(task))
        model.fit(dataset)

        # 预测
        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        sr.generate()

.. note::

    `Alpha158` 是 Qlib 提供的数据处理器（data handler），详见 `数据处理器 <data.html#data-handler>`_。
    `SignalRecord` 是 Qlib 中的 `记录模板（Record Template）`，详见 `工作流 <recorder.html#record-template>`_。

上例亦可在 `examples/train_backtest_analyze.ipynb` 中找到。

技术上，模型预测分数的含义取决于用户设计的标签（label）定义。默认情况下，分数通常表示模型对标的的评级（ranking），分数越高表明标的越被模型认为有更高的收益潜力。

自定义模型
===========

Qlib 支持自定义模型。如果用户希望定制并将自有模型集成到 Qlib 中，请参阅 `自定义模型集成 <../start/integration.html>`_。

API
===

更多接口请参阅 `模型 API <../reference/api.html#module-qlib.model.base>`_。
