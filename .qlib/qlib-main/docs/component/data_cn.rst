.. _data:

==================================
数据层：数据框架与使用指南
==================================

简介
====

``数据层`` 提供便捷的 API 用于管理与获取数据，同时提供高性能的数据基础设施。

该模块面向量化投资场景设计，例如用户可以使用 ``数据层`` 便捷地构建公式化因子（formulaic alphas）。详情请参阅 `构建公式化因子 <../advanced/alpha.html>`_。

“数据层”的介绍包括以下部分：

- 数据准备
- 数据接口（Data API）
- 数据加载器（Data Loader）
- 数据处理器（Data Handler）
- 数据集（Dataset）
- 缓存（Cache）
- 数据与缓存的文件结构

以下为 Qlib 常见的数据工作流示例：

- 用户下载并将原始数据转换为 Qlib 格式（文件后缀为 `.bin`）。在此步骤中，通常只在磁盘上保存一些基础字段（例如 OHLCV）。
- 基于 Qlib 的表达式引擎（Expression Engine）创建基础特征（例如 "Ref($close, 60) / $close"，表示过去 60 个交易日的收益率）。表达式引擎支持的算子可见 `此处 <https://github.com/microsoft/qlib/blob/main/qlib/data/ops.py>`__。通常这一步在 Qlib 的 `数据加载器 <https://qlib.readthedocs.io/en/latest/component/data.html#data-loader>`_ 中实现，作为 `数据处理器 <https://qlib.readthedocs.io/en/latest/component/data.html#data-handler>`_ 的一部分。
- 若需更复杂的数据处理（例如数据归一化），`数据处理器 <https://qlib.readthedocs.io/en/latest/component/data.html#data-handler>`_ 支持用户自定义的处理器（processors），相关示例见 `此处 <https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/processor.py>`__。处理器（processor）与表达式引擎中的算子不同，前者用于实现一些在表达式算子中难以表达的复杂处理逻辑。
- 最后，`Dataset <https://qlib.readthedocs.io/en/latest/component/data.html#dataset>`_ 负责基于 Data Handler 的处理结果，准备模型所需的特定数据集。

数据准备
========

Qlib 格式数据
--------------

我们为金融数据专门设计了一套数据结构，详细设计请参考 `Qlib 论文中的文件存储设计章节 <https://arxiv.org/abs/2009.11189>`_。
这类数据以文件后缀 `.bin` 存储（以下称为 `.bin` 文件、`.bin` 格式或 qlib 格式）。`.bin` 格式针对金融科学计算进行了优化。

``Qlib`` 提供了若干开箱即用的数据集，列表与实现位置可见：`qlib/contrib/data/handler.py <https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py>`__。

========================  =================  ================
Dataset                   美国市场           中国市场
========================  =================  ================
Alpha360                  √                  √

Alpha158                  √                  √
========================  =================  ================

此外，``Qlib`` 还提供高频数据集，相关示例位于 `examples/highfreq <https://github.com/microsoft/qlib/tree/main/examples/highfreq>`__。

Qlib 格式数据集
----------------

``Qlib`` 提供了 `.bin` 格式的现成数据集，用户可通过脚本 ``scripts/get_data.py`` 下载中国市场数据，例如：
（也可以使用 numpy 加载 `.bin` 文件进行校验）。

注意：价格与成交量数据为 **复权后** 的值（adjusted），复权方式可能因数据源而异。Qlib 在每只股票的首个交易日将价格标准化为 1。若需还原原始交易价，可使用 `$factor`（例如 `$close / $factor` 得到未复权的收盘价）。

关于复权的讨论示例：

- https://github.com/microsoft/qlib/issues/991#issuecomment-1075252402

示例命令：

.. code-block:: bash

    # 下载日频数据
    python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn

    # 下载 1 分钟级数据
    python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/qlib_cn_1min --region cn --interval 1min

另外，``Qlib`` 也提供美国市场数据，可用如下命令下载：

.. code-block:: bash

    python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us

执行上述命令后，用户将在 `~/.qlib/qlib_data/cn_data` 与 `~/.qlib/qlib_data/us_data` 找到对应的 Qlib 格式数据目录。

``Qlib`` 提供了 `scripts/data_collector` 中的脚本，用于从互联网上抓取最新数据并转为 qlib 格式。

当用该数据初始化 Qlib 后，用户便可以基于其构建并评估模型。更多初始化信息请参见 `初始化 <../start/initialization.html>`_。

日频数据的自动更新
------------------

**建议用户先通过手动方式（例如 `--trading_date 2021-05-25`）进行一次更新，然后配置自动更新。**

更多信息参见：`yahoo 数据采集器说明 <https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo#Automatic-update-of-daily-frequency-data>`_

- 每个交易日自动更新 qlib 数据目录（Linux）
  - 使用 *crontab*: `crontab -e`
  - 配置定时任务，例如：

    .. code-block:: bash

        * * * * 1-5 python <script path> update_data_to_bin --qlib_data_1d_dir <user data dir>

    - **script path**：scripts/data_collector/yahoo/collector.py

- 手动更新数据：

    .. code-block:: bash

        python scripts/data_collector/yahoo/collector.py update_data_to_bin --qlib_data_1d_dir <user data dir> --trading_date <start date> --end_date <end date>

    - *trading_date*：起始交易日
    - *end_date*：结束交易日（不包含）

将 CSV / Parquet 转换为 Qlib 格式
----------------------------------

``Qlib`` 提供脚本 ``scripts/dump_bin.py``，可将任意满足格式要求的 CSV 或 Parquet 数据转换为 `.bin`（Qlib 格式）。

除了下载准备好的示例数据外，用户也可以通过 Collector 下载示例 CSV 数据，示例命令如下：

- 日频 CSV 示例：

  .. code-block:: bash

    python scripts/get_data.py download_data --file_name csv_data_cn.zip --target_dir ~/.qlib/csv_data/cn_data

- 1 分钟级示例：

  .. code-block:: bash

    python scripts/data_collector/yahoo/collector.py download_data --source_dir ~/.qlib/stock_data/source/cn_1min --region CN --start 2021-05-20 --end 2021-05-23 --delay 0.1 --interval 1min --limit_nums 10

用户也可以提供自己的 CSV 或 Parquet 数据，但需满足以下条件：

- CSV 或 Parquet 文件以股票代码命名，或文件中包含股票名称列。

    - 以股票命名示例：`SH600000.csv`, `AAPL.csv` 或 `SH600000.parquet`, `AAPL.parquet`（大小写不敏感）。

    - 若文件包含股票列，需在转储时指定列名，例如：

        .. code-block:: bash

            python scripts/dump_bin.py dump_all ... --symbol_field_name symbol --file_suffix <.csv or .parquet>

        数据示例：

            +-----------+-------+
            | symbol    | close |
            +===========+=======+
            | SH600000  | 120   |
            +-----------+-------+

- CSV 或 Parquet 文件必须包含日期列，转储时需指定日期列名。例如：

    .. code-block:: bash

        python scripts/dump_bin.py dump_all ... --date_field_name date --file_suffix <.csv or .parquet>

    数据示例：

        +---------+------------+-------+------+----------+
        | symbol  | date       | close | open | volume   |
        +=========+============+=======+======+==========+
        | SH600000| 2020-11-01 | 120   | 121  | 12300000 |
        +---------+------------+-------+------+----------+
        | SH600000| 2020-11-02 | 123   | 120  | 12300000 |
        +---------+------------+-------+------+----------+

假设用户将 CSV / Parquet 数据放在 `~/.qlib/my_data`，可运行以下命令进行转换：

.. code-block:: bash

    python scripts/dump_bin.py dump_all --data_path  ~/.qlib/my_data --qlib_dir ~/.qlib/qlib_data/ --include_fields open,close,high,low,volume,factor --file_suffix <.csv or .parquet>

更多转储时支持的参数可通过帮助命令查看：

.. code-block:: bash

    python scripts/dump_bin.py dump_all --help

转换完成后，Qlib 格式的数据将存放于 `~/.qlib/qlib_data/`。

.. note::

    `--include_fields` 的字段名应与 CSV / Parquet 的列名对应。Qlib 自带数据通常至少包含 open、close、high、low、volume 和 factor。

    - `open`
        复权后的开盘价
    - `close`
        复权后的收盘价
    - `high`
        复权后的最高价
    - `low`
        复权后的最低价
    - `volume`
        复权后的成交量
    - `factor`
        复权因子（通常 factor = adjusted_price / original_price），参见 `复权说明 <https://www.investopedia.com/terms/s/splitadjusted.asp>`_

    在 Qlib 的数据处理约定中，若股票停牌，`open, close, high, low, volume, money 和 factor` 会被设置为 NaN。如果你需要使用无法由 OCHLV 计算出的因子（例如 PE、EPS 等），可以将它们与 OHCLV 一起加入到 CSV/Parquet 中并转换为 Qlib 格式。

数据健康检查
---------------

``Qlib`` 提供脚本用于检测数据健康状况，主要检查点包括：

- 检查 DataFrame 中是否存在缺失值。
- 检查 OHLCV 列中是否存在超过阈值的大幅跳变。
- 检查是否缺失必需列（OLHCV）。
- 检查是否缺失 `factor` 列。

可使用如下命令执行检测：

- 日频数据示例：

  .. code-block:: bash

      python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data

- 1 分钟数据示例：

  .. code-block:: bash

      python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data_1min --freq 1min

你也可以添加参数调整检测阈值，常见参数包括：

- `freq`：数据频率
- `large_step_threshold_price`：价格的大幅变动阈值
- `large_step_threshold_volume`：成交量的大幅变动阈值
- `missing_data_num`：允许的最大缺失数量

示例命令（含参数）：

- 日频：

  .. code-block:: bash

      python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data --missing_data_num 30055 --large_step_threshold_volume 94485 --large_step_threshold_price 20

- 1 分钟：

  .. code-block:: bash

      python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data --freq 1min --missing_data_num 35806 --large_step_threshold_volume 3205452000000 --large_step_threshold_price 0.91

股票池（Market）
----------------

``Qlib`` 将“股票池”定义为股票列表及其时间区间（stock list and their date ranges）。可导入的预定义股票池（例如 csi300）可以通过脚本导入，例如：

.. code-block:: bash

    python collector.py --index_name CSI300 --qlib_dir <user qlib data dir> --method parse_instruments

多股种模式
----------

``Qlib`` 当前支持两种模式：中国市场（China-Stock）与美国市场（US-Stock）。两者在设置上有一些差异：

==============  =================  ================
Region          交易单位           涨跌幅限制
==============  =================  ================
China           100                0.099

US              1                  无
==============  =================  ================

`交易单位` 定义了下单时的最小交易单位，`涨跌幅限制` 定义了股票涨跌幅的监管上限。

- 若使用中国市场模式，请准备中国市场数据并按以下步骤初始化：
    - 下载 Qlib 格式的中国市场数据，参考 `Qlib 格式数据集 <#qlib-format-dataset>`_。
    - 初始化 Qlib（假定数据存放在 `~/.qlib/qlib_data/cn_data`）：

        .. code-block:: python

            from qlib.constant import REG_CN
            qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region=REG_CN)

- 若使用美国市场模式，请准备美国市场数据并按以下步骤初始化：
    - 下载 Qlib 格式的美国市场数据，参考 `Qlib 格式数据集 <#qlib-format-dataset>`_。
    - 初始化 Qlib（假定数据存放在 `~/.qlib/qlib_data/us_data`）：

        .. code-block:: python

            from qlib.config import REG_US
            qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region=REG_US)

.. note::

    欢迎贡献新的数据源（PR）。用户可将抓取数据的代码以 PR 形式提交（示例见 `scripts` 目录）。我们可基于这些代码在服务器端创建数据缓存，供其他用户直接使用。

数据接口（Data API）
====================

数据检索
--------

用户可通过 `qlib.data` 中的接口获取数据，详见 `数据检索 <../start/getdata.html>`_。

特征（Feature）
---------------

``Qlib`` 提供 `Feature` 与 `ExpressionOps` 用于按需获取特征。

- `Feature`
    从数据提供者加载原始字段，例如 `$high`, `$low`, `$open`, `$close` 等，这些字段应与 `--include_fields` 参数一致，参见 `将 CSV 转为 Qlib 格式 <#converting-csv-format-into-qlib-format>`_。

- `ExpressionOps`
    `ExpressionOps` 使用算子（operator）进行特征构造。关于算子接口，请参见 `算子 API <../reference/api.html#module-qlib.data.ops>`_。用户也可以自定义算子（Operator），示例见 `tests/test_register_ops.py`。

关于 `Feature` 的更多细节请参阅 `Feature API <../reference/api.html#module-qlib.data.base>`_。

过滤器（Filter）
---------------

``Qlib`` 提供 `NameDFilter` 与 `ExpressionDFilter` 用于按需筛选标的（instruments）。

- `NameDFilter`
    基于命名规范（正则表达式）筛选标的。

- `ExpressionDFilter`
    基于表达式筛选标的，表达式需引用某个特征字段。

    - 基本特征过滤：`rule_expression = '$close/$open>5'`
    - 横截面过滤：`rule_expression = '$rank($close)<10'`
    - 时间序列过滤：`rule_expression = '$Ref($close, 3)>100'`

下面示例展示如何在配置文件中使用过滤器：

.. code-block:: yaml

    filter: &filter
        filter_type: ExpressionDFilter
        rule_expression: "Ref($close, -2) / Ref($close, -1) > 1"
        filter_start_time: 2010-01-01
        filter_end_time: 2010-01-07
        keep: False

    data_handler_config: &data_handler_config
        start_time: 2010-01-01
        end_time: 2021-01-22
        fit_start_time: 2010-01-01
        fit_end_time: 2015-12-31
        instruments: *market
        filter_pipe: [*filter]

关于过滤器的更多信息，请参阅 `Filter API <../reference/api.html#module-qlib.data.filter>`_。

参考
----

关于 `Data API` 的更多信息，请参阅 `Data API <../reference/api.html#data>`_。

数据加载器（Data Loader）
=======================

`Data Loader` 用于从原始数据源加载原始数据，供 `Data Handler` 使用。

QlibDataLoader
--------------

`QlibDataLoader` 是 Qlib 中用于从 Qlib 数据源加载原始数据的接口类。

StaticDataLoader
----------------

`StaticDataLoader` 是用于从文件或已提供的数据中加载静态数据的接口类。

接口说明
--------

下面列出 `QlibDataLoader` 的接口：

.. autoclass:: qlib.data.dataset.loader.DataLoader
    :members:
    :noindex:

API
---

关于 `Data Loader` 的更多信息，请参阅 `Data Loader API <../reference/api.html#module-qlib.data.dataset.loader>`_。

数据处理器（Data Handler）
========================

`Data Handler` 模块用于封装常见的数据预处理方法（如标准化、去 NaN 等），这些方法可被多数模型复用。

用户可以通过 `qrun` 在自动化工作流中使用 `Data Handler`，详见 `Workflow: Workflow Management <workflow.html>`_。

DataHandlerLP
-------------

除了在 `qrun` 中以自动化流程使用外，`Data Handler` 还可以作为独立模块使用，便于用户对数据进行预处理（如标准化、缺失值处理等）并构建数据集。

为此，Qlib 提供了 `qlib.data.dataset.DataHandlerLP <../reference/api.html#qlib.data.dataset.handler.DataHandlerLP>`_ 基类。该类的核心思想是：引入一些可学习的 `Processors`（处理器），这些处理器可以在训练阶段学习处理参数（例如 z-score 的均值与方差）；在新数据到来时，使用训练好的处理器对新数据进行高效处理，从而支持实时数据处理。处理器的更多细节将在下文介绍。

接口
----

下面列出 `DataHandlerLP` 的重要接口：

.. autoclass:: qlib.data.dataset.handler.DataHandlerLP
    :members: __init__, fetch, get_cols
    :noindex:

如果用户希望通过配置加载特征与标签，可以定义新的 handler，并调用 `qlib.contrib.data.handler.Alpha158` 的静态方法 `parse_config_to_fields`。

此外，用户还可以向 handler 传入 `qlib.contrib.data.processor.ConfigSectionProcessor`，其提供基于配置的特征预处理方法。

处理器（Processor）
------------------

`Processor` 模块用于实现可学习的预处理流程，负责诸如归一化、丢弃 N/A 特征/标签等。

Qlib 提供了以下处理器：

- `DropnaProcessor`：删除缺失特征的处理器。
- `DropnaLabel`：删除缺失标签的处理器。
- `TanhProcess`：使用 tanh 进行去噪处理的处理器。
- `ProcessInf`：处理无穷大值，会以列均值替换。
- `Fillna`：填充缺失值（例如填 0 或指定值）。
- `MinMaxNorm`：最小-最大归一化。
- `ZscoreNorm`：z-score 标准化。
- `RobustZScoreNorm`：鲁棒 z-score 标准化。
- `CSZScoreNorm`：横截面 z-score 标准化。
- `CSRankNorm`：横截面秩归一化。
- `CSZFillna`：按横截面均值填充缺失值。

用户也可通过继承 Processor 的基类自定义处理器，详情参见源码实现（`qlib/data/dataset/processor.py`）。

关于 `Processor` 的更多信息，请参阅 `Processor API <../reference/api.html#module-qlib.data.dataset.processor>`_。

示例
----

`Data Handler` 可通过修改配置使用 `qrun` 运行，也可作为独立模块使用。

更多关于如何用 `qrun` 运行 `Data Handler` 的信息见 `Workflow: Workflow Management <workflow.html>`_。

Qlib 已实现 `Alpha158` 数据处理器，下面示例展示如何以独立模块运行 `Alpha158`：

.. note:: 运行前需先使用 `qlib.init` 初始化 Qlib，参见 `初始化 <../start/initialization.html>`_。

.. code-block:: Python

    import qlib
    from qlib.contrib.data.handler import Alpha158

    data_handler_config = {
        "start_time": "2008-01-01",
        "end_time": "2020-08-01",
        "fit_start_time": "2008-01-01",
        "fit_end_time": "2014-12-31",
        "instruments": "csi300",
    }

    if __name__ == "__main__":
        qlib.init()
        h = Alpha158(**data_handler_config)

        # 获取所有列名
        print(h.get_cols())

        # 获取所有标签
        print(h.fetch(col_set="label"))

        # 获取所有特征
        print(h.fetch(col_set="feature"))

.. note:: 在 `Alpha158` 中，Qlib 使用标签 `Ref($close, -2)/Ref($close, -1) - 1`，表示从 T+1 到 T+2 的变化率；之所以采用该定义，是因为在获取中国股票的 T 日收盘价时，T 日买入实际上需在 T+1 日成交并在 T+2 日卖出。

API
---

关于 `Data Handler` 的更多信息，请参阅 `Data Handler API <../reference/api.html#module-qlib.data.dataset.handler>`_。

数据集（Dataset）
================

`Dataset` 模块旨在为模型训练与推断准备数据。

该模块的动机在于最大化不同模型处理数据的灵活性。不同模型对输入数据的要求可能不同，例如 GBDT 对包含 NaN 或 None 的数据具有一定鲁棒性，而神经网络（如 MLP）在遇到 NaN 时可能无法正常训练。

若模型需要特殊的数据处理方式，用户可以实现自定义的 `Dataset` 类；若数据处理并无特殊需求，可直接使用 `DatasetH`。

`DatasetH` 是与 `Data Handler` 配合使用的 dataset，以下为该类最重要的接口：

.. autoclass:: qlib.data.dataset.__init__.DatasetH
    :members:
    :noindex:

API
---

关于 `Dataset` 的更多信息，请参阅 `Dataset API <../reference/api.html#dataset>`_。

缓存（Cache）
=============

`Cache` 为可选模块，通过将常用数据保存在内存或磁盘上加速数据提供。Qlib 提供全局内存缓存（MemCache）用于缓存常用数据、可继承的 `ExpressionCache` 与 `DatasetCache` 基类用于实现自定义缓存策略。

全局内存缓存
-------------

`MemCache` 是一个全局内存缓存机制，包含三个 `MemCacheUnit` 实例，分别用于缓存 **日历（Calendar）**、**标的（Instruments）** 与 **特征（Features）**。全局实例在 `cache.py` 中以 `H` 定义，用户可通过 `H['c']`, `H['i']`, `H['f']` 访问/操作内存缓存。

.. autoclass:: qlib.data.cache.MemCacheUnit
    :members:
    :noindex:

.. autoclass:: qlib.data.cache.MemCache
    :members:
    :noindex:

表达式缓存（ExpressionCache）
---------------------------

`ExpressionCache` 是用于缓存表达式（例如 Mean($close, 5)）的基类。用户可继承该类并实现自定义的缓存策略，通常包括：

- 重写 `_uri` 方法以定义缓存文件路径生成规则；
- 重写 `_expression` 方法以定义如何获取并缓存表达式数据。

下面为接口说明：

.. autoclass:: qlib.data.cache.ExpressionCache
    :members:
    :noindex:

Qlib 已提供 `DiskExpressionCache`（继承自 `ExpressionCache`）的磁盘实现，表达式数据将被保存到磁盘。

数据集缓存（DatasetCache）
-------------------------

`DatasetCache` 用于缓存数据集。一份数据集由股票池配置（或一组 instruments，不推荐）、一组表达式或静态字段、起止时间与频率共同决定。用户可继承该类实现自定义缓存策略，通常包括：

- 重写 `_uri` 方法定义缓存路径生成规则；
- 重写 `_dataset` 方法定义如何生成并缓存数据集。

接口说明：

.. autoclass:: qlib.data.cache.DatasetCache
    :members:
    :noindex:

Qlib 目前提供 `DiskDatasetCache`（继承自 `DatasetCache`）的磁盘实现，数据集以文件形式存储在磁盘上。

数据与缓存文件结构
===================

我们为数据与缓存专门设计了文件组织结构，详细设计见 `Qlib 论文的文件存储设计章节 <https://arxiv.org/abs/2009.11189>`_。主要结构示例如下：

.. code-block::

    - data/
        [raw data] updated by data providers
        - calendars/
            - day.txt
        - instruments/
            - all.txt
            - csi500.txt
            - ...
        - features/
            - sh600000/
                - open.day.bin
                - close.day.bin
                - ...
            - ...
        [cached data] updated when raw data is updated
        - calculated features/
            - sh600000/
                - [hash(instrtument, field_expression, freq)]
                    - all-time expression -cache data file
                    - .meta : an assorted meta file recording the instrument name, field name, freq, and visit times
            - ...
        - cache/
            - [hash(stockpool_config, field_expression_list, freq)]
                - all-time Dataset-cache data file
                - .meta : an assorted meta file recording the stockpool config, field names and visit times
                - .index : an assorted index file recording the line index of all calendars
            - ...

