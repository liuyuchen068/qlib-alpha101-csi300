.. _workflow:

=============================
工作流：工作流管理
=============================
.. currentmodule:: qlib

简介
====

`Qlib 框架 <../introduction/introduction.html#framework>`_ 的各个组件采用松耦合设计。用户可以基于这些组件构建自己的量化研究工作流，参见示例：`examples/workflow_by_code.py <https://github.com/microsoft/qlib/blob/main/examples/workflow_by_code.py>`_。

此外，``Qlib`` 提供了更易用的命令行工具 `qrun`，用于根据配置自动运行完整工作流。一次完整运行称为一次 `execution`（执行）。使用 `qrun`，用户可以方便地启动一次执行，通常包含以下步骤：

- 数据
    - 加载
    - 处理
    - 切分
- 模型
    - 训练与推理
    - 保存与加载
- 评估
    - 预测信号分析
    - 回测

对于每次执行，``Qlib`` 提供一套完整的系统来追踪训练、推理与评估阶段产生的信息与产物（artifacts）。关于 Qlib 如何处理这些内容，请参见：`Recorder：实验管理 <../component/recorder.html>`_。

完整示例
=========

在深入细节前，下面给出一个完整的 `qrun` 配置示例，展示典型的量化研究工作流。将下述配置保存为 `configuration.yaml` 后，可通过 single 命令运行：

.. code-block:: YAML

    qlib_init:
        provider_uri: "~/.qlib/qlib_data/cn_data"
        region: cn
    market: &market csi300
    benchmark: &benchmark SH000300
    data_handler_config: &data_handler_config
        start_time: 2008-01-01
        end_time: 2020-08-01
        fit_start_time: 2008-01-01
        fit_end_time: 2014-12-31
        instruments: *market
    port_analysis_config: &port_analysis_config
        strategy:
            class: TopkDropoutStrategy
            module_path: qlib.contrib.strategy.strategy
            kwargs:
                topk: 50
                n_drop: 5
                signal: <PRED>
        backtest:
            start_time: 2017-01-01
            end_time: 2020-08-01
            account: 100000000
            benchmark: *benchmark
            exchange_kwargs:
                limit_threshold: 0.095
                deal_price: close
                open_cost: 0.0005
                close_cost: 0.0015
                min_cost: 5
    task:
        model:
            class: LGBModel
            module_path: qlib.contrib.model.gbdt
            kwargs:
                loss: mse
                colsample_bytree: 0.8879
                learning_rate: 0.0421
                subsample: 0.8789
                lambda_l1: 205.6999
                lambda_l2: 580.9768
                max_depth: 8
                num_leaves: 210
                num_threads: 20
        dataset:
            class: DatasetH
            module_path: qlib.data.dataset
            kwargs:
                handler:
                    class: Alpha158
                    module_path: qlib.contrib.data.handler
                    kwargs: *data_handler_config
                segments:
                    train: [2008-01-01, 2014-12-31]
                    valid: [2015-01-01, 2016-12-31]
                    test: [2017-01-01, 2020-08-01]
        record:
            - class: SignalRecord
              module_path: qlib.workflow.record_temp
              kwargs: {}
            - class: PortAnaRecord
              module_path: qlib.workflow.record_temp
              kwargs:
                  config: *port_analysis_config

运行命令：

.. code-block:: bash

    qrun configuration.yaml

如需在调试模式下运行 `qrun`：

.. code-block:: bash

    python -m pdb qlib/cli/run.py examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml

.. note::
    安装 Qlib 后，`qrun` 将位于系统的 `$PATH` 中。

.. note::
    在 YAML 配置中，符号 `&` 表示锚点（anchor），便于在其他字段中引用此参数。例如上面的配置中，可直接修改 `market` 与 `benchmark` 的值而无需遍历整个文件。

配置文件详解
============

本节将详细说明 `qrun` 的配置文件结构。整体设计逻辑较简单：预定义常见工作流，并通过 YAML 接口让用户指定如何初始化各组件。该初始化遵循 `init_instance_by_config` 的设计：每个组件通过 `class`、`module_path` 与 `kwargs` 指定。

示例等价关系：下列 YAML 与 Python 代码等价（用于模型初始化）。

.. code-block:: YAML

    model:
        class: LGBModel
        module_path: qlib.contrib.model.gbdt
        kwargs:
            loss: mse
            colsample_bytree: 0.8879
            learning_rate: 0.0421
            subsample: 0.8789
            lambda_l1: 205.6999
            lambda_l2: 580.9768
            max_depth: 8
            num_leaves: 210
            num_threads: 20

等价 Python 初始化示例：

.. code-block:: python

        from qlib.contrib.model.gbdt import LGBModel
        kwargs = {
            "loss": "mse" ,
            "colsample_bytree": 0.8879,
            "learning_rate": 0.0421,
            "subsample": 0.8789,
            "lambda_l1": 205.6999,
            "lambda_l2": 580.9768,
            "max_depth": 8,
            "num_leaves": 210,
            "num_threads": 20,
        }
        LGBModel(kwargs)

Qlib 初始化部分
----------------

配置文件应包含用于 qlib 初始化的基础参数：

.. code-block:: YAML

    provider_uri: "~/.qlib/qlib_data/cn_data"
    region: cn

字段含义：

- `provider_uri`：字符串，Qlib 数据的 URI（例如 `get_data.py` 下载的数据所在目录）。
- `region`：若为 `us` 则初始化为美股模式；若为 `cn` 则为中国市场模式。

.. note::
    `region` 的取值应与 `provider_uri` 中的数据区域一致。

任务（Task）部分
-----------------

配置中的 `task` 字段对应一次任务（task），包含三部分参数：`Model`、`Dataset` 与 `Record`。

模型（Model）部分
~~~~~~~~~~~~~~~~~

`task` 下的 `model` 段定义用于训练与推理的模型参数，更多基类信息见 `Qlib Model <../component/model.html>`_。

.. code-block:: YAML

    model:
        class: LGBModel
        module_path: qlib.contrib.model.gbdt
        kwargs:
            loss: mse
            colsample_bytree: 0.8879
            learning_rate: 0.0421
            subsample: 0.8789
            lambda_l1: 205.6999
            lambda_l2: 580.9768
            max_depth: 8
            num_leaves: 210
            num_threads: 20

字段含义：

- `class`：字符串，模型类名。
- `module_path`：字符串，模型在 Qlib 中的模块路径。
- `kwargs`：模型的关键字参数，具体请参考各模型实现（见 `models <https://github.com/microsoft/qlib/blob/main/qlib/contrib/model>`_）。

.. note::
    Qlib 提供工具 `init_instance_by_config`，可根据上述配置自动初始化任意类实例。

数据集（Dataset）部分
~~~~~~~~~~~~~~~~~~~~~

`dataset` 段描述了 `Dataset` 与 `DataHandler` 的参数，负责训练/测试阶段的数据预处理与切片。更多信息见 `Qlib Data <../component/data.html#dataset>`_。

DataHandler 的配置示例如下：

.. code-block:: YAML

    data_handler_config: &data_handler_config
        start_time: 2008-01-01
        end_time: 2020-08-01
        fit_start_time: 2008-01-01
        fit_end_time: 2014-12-31
        instruments: *market

关于每个字段的含义，请参见 `DataHandler 文档 <../component/data.html#datahandler>`_。

Dataset 模块配置示例：

.. code-block:: YAML

    dataset:
        class: DatasetH
        module_path: qlib.data.dataset
        kwargs:
            handler:
                class: Alpha158
                module_path: qlib.contrib.data.handler
                kwargs: *data_handler_config
            segments:
                train: [2008-01-01, 2014-12-31]
                valid: [2015-01-01, 2016-12-31]
                test: [2017-01-01, 2020-08-01]

记录（Record）部分
~~~~~~~~~~~~~~~~~~~

`record` 段定义了 `Record` 模块的参数，`Record` 负责以标准格式追踪训练过程与结果（如信息系数 IC 与回测结果）。

下面为回测与策略的配置示例：

.. code-block:: YAML

    port_analysis_config: &port_analysis_config
        strategy:
            class: TopkDropoutStrategy
            module_path: qlib.contrib.strategy.strategy
            kwargs:
                topk: 50
                n_drop: 5
                signal: <PRED>
        backtest:
            limit_threshold: 0.095
            account: 100000000
            benchmark: *benchmark
            deal_price: close
            open_cost: 0.0005
            close_cost: 0.0015
            min_cost: 5

关于 `strategy` 与 `backtest` 配置中各字段的含义，请参阅文档：`Strategy <../component/strategy.html>`_ 与 `Backtest <../component/backtest.html>`_。

不同 `Record Template`（如 `SignalRecord`、`PortAnaRecord`）的配置示例如下：

.. code-block:: YAML

    record:
        - class: SignalRecord
          module_path: qlib.workflow.record_temp
          kwargs: {}
        - class: PortAnaRecord
          module_path: qlib.workflow.record_temp
          kwargs:
            config: *port_analysis_config

更多关于 `Record` 模块的信息，请参阅：`Record <../component/recorder.html#record-template>`_。
