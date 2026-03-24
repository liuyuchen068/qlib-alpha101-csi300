.. _meta:

======================================================
元控制器：元任务、元数据集与元模型
======================================================
.. currentmodule:: qlib

简介
============

``元控制器（Meta Controller）`` 为 ``预测模型（Forecast Model）`` 提供指导，旨在学习一系列预测任务中的规律性，并将学到的模式用于指导后续的预测任务。用户可以基于 ``Meta Controller`` 模块实现自己的元模型实例。

元任务（Meta Task）
=========

`元任务` 实例是元学习框架中的基本单元，它保存可用于 `Meta Model` 的数据。多个 `Meta Task` 实例可以共享同一个 `Data Handler`（由 `Meta Dataset` 控制）。用户应使用 `prepare_task_data()` 来获取可以直接输入到 `Meta Model` 的数据。

.. autoclass:: qlib.model.meta.task.MetaTask
    :members:

元数据集（Meta Dataset）
============

`Meta Dataset` 控制元信息的生成流程，负责为 `Meta Model` 提供训练所需的数据。用户应使用 `prepare_tasks` 来获取一组 `Meta Task` 实例。

.. autoclass:: qlib.model.meta.dataset.MetaTaskDataset
    :members:

元模型（Meta Model）
==========

通用元模型
------------------
`Meta Model` 实例负责控制元学习的工作流。`Meta Model` 的使用流程包括：

1. 用户使用 `fit` 函数训练 `Meta Model`。
2. 通过 `inference` 函数，`Meta Model` 实例为工作流提供有用的信息以指导后续任务。

.. autoclass:: qlib.model.meta.model.MetaModel
    :members:

元任务模型（Meta Task Model）
---------------
此类元模型可能直接与任务定义交互。继承自 `MetaTaskModel` 的模型通过修改基任务定义来指导基础任务。函数 `prepare_tasks` 可用于获取修改后的基础任务定义。

.. autoclass:: qlib.model.meta.model.MetaTaskModel
    :members:

引导型元模型（Meta Guide Model）
----------------
此类元模型参与基础预测模型的训练过程，元模型可在训练期间对基础预测模型进行引导，以提升其性能。

.. autoclass:: qlib.model.meta.model.MetaGuideModel
    :members:

示例
=======

``Qlib`` 提供了一个元模型实现 ``DDG-DA``，用于适应市场动态变化。

``DDG-DA`` 的流程包括四个步骤：

1. 计算元信息并封装为 `Meta Task` 实例，所有元任务构成一个 `Meta Dataset`。
2. 基于元数据集的训练数据训练 `DDG-DA`。
3. 对训练好的 `DDG-DA` 执行推理以获得引导信息。
4. 将引导信息应用到基础预测模型中以提升其性能。

相关示例代码位于：`examples/benchmarks_dynamic/DDG-DA <https://github.com/microsoft/qlib/tree/main/examples/benchmarks_dynamic/DDG-DA>`_，工作流入口文件为 `workflow.py`。
