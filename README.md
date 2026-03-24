# CSI300 量化回测系统

基于 **Qlib** 框架和 **聚宽数据** 的沪深300（CSI300）成分股量化交易回测系统。本项目提供了两种实现方式，支持从数据获取、因子计算、模型训练到回测评估的完整工作流，方案一在调用qlib的接口的基础上，完全自定义 Python 脚本；方案二直接使用 Qlib 原生 qrun 功能。两种方案结果相同，只是实现方式不同。

## 🎯 项目概述

### 核心目标
- **数据获取**：通过聚宽API获取沪深300成分股的历史行情数据
- **因子获取**：从聚宽数据集获取Alpha101因子，进行特征工程
- **模型训练**：使用LightGBM模型基于因子预测股票收益
- **策略回测**：构建权重策略并进行历史回测
- **风险控制**：识别并排除停牌、ST、涨跌停等风险股票

### 项目特色
✨ **双层实现方案**
- 方案一：完全自定义 Python 脚本：
优点：灵活性高，自定义化强，支持复杂的交易逻辑；避免输出临时文件和日志，保证输出有用信息；可以更好地控制线程数，保证平稳运行。
缺点：需要手动处理数据、模型训练、回测等流程，工作量较大。

- 方案二：Qlib 原生 qrun：
优点：开箱即用，无需手动处理数据、模型训练、回测等流程，工作量较小。
缺点：灵活性较低，自定义化弱，不支持复杂的交易逻辑；输出存在临时文件和日志，需要手动清理。



✨ **风险管理**
- 自动识别 ST 股票、停牌、涨跌停
- 回测时动态排除风险标的
- 支持 A 股多板块的涨跌停阈值差异

✨ **加权策略**
- 基于预测分数的权重分配
- 支持现金储备配置
- 归一化处理（MinMax）

## 📋 环境要求

### Python 环境
- Python 3.8+
- Qlib >= 0.9.0
- LightGBM >= 3.3
- pandas >= 1.3
- pyyaml >= 5.4
- numpy >= 1.20

### 外部服务
- **聚宽 API 账号**：需提前注册 [https://www.joinquant.com/](https://www.joinquant.com/)
- **Qlib 数据源**：需下载 CSI300 对应的 qlib 数据文件

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd csi300-backtest
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置聚宽账号

创建 `.env` 文件，填入聚宽凭证：
```env
JQDATASDK_PHONE=your_phone_number
JQDATASDK_PASSWORD=your_password
```

### 4. 准备 Qlib 数据

按照 Qlib 官方文档下载 CSI300 数据到本地：
```bash
# 假设解压后的数据目录为
~/Desktop/my-project/data/input/qlib_data/
```

确保 `config.yaml` 或 `config_qrun.yaml` 中的数据路径与实际目录一致。

---

## 📁 项目结构

```
.
├── README.md                  # 项目说明文档
├── requirements.txt           # Python 依赖列表
├── .env.example              # 环境变量模板
├── .bash                      # 方案二的执行脚本
├── .dump.bin.py               # 数据从csv格式转为bin格式的脚本
├── config.yaml               # 方案一的配置文件
├── config_qrun.yaml           # 方案二的配置文件
├── data_preparation.py       # 方案一：数据准备模块
├── workflow.py               # 方案一：回测工作流
└── data/
    ├── input/
    │   ├── qlib_data/        # 满足 Qlib 数据格式的目录(bin格式)
    │   ├── my_data/          # 提取的数据(csv格式)
    │   └── csi300_stocks.csv # 股票列表
    ├── results_raw/          # 方案一回测结果
    └── results_qrun/          # 方案二回测结果
```

---

## 💻 使用方法

### 第一步：数据准备
运行数据准备模块，从聚宽获取原始行情和Alpha因子：
```bash
python data_preparation.py
```

**功能说明**
- 按配置的日期范围遍历所有交易日
- 获取当日沪深300成分股的行情数据（前复权）
- 获取 Alpha001~Alpha010（可配置因子数量）
- 识别 ST 股、停牌股、涨跌停情况
- 输出：`data/input/my_data/SH??????.csv`、`SZ??????.csv`


### 第二步：模型训练与回测

#### 方案一：Python 脚本方式

```bash
python workflow.py
```

**功能说明**
- 加载数据集（使用 Qlib 的 DatasetH 接口）
- 训练 LightGBM 模型
- 生成测试期预测信号
- 执行日度回测，按预测分数加权配置持仓
- 输出：回测报告和持仓记录

**策略配置** (scaleWeightedStrategy)
- **topk**：选择分数最高的 N 只股票（默认 20）
- **cash_reserve**：保留的现金比例（默认 5%）
- **normalize_method**：权重归一化方法（minmax 或 other）

**输出文件** 
- `data/results_raw/backtest_report.csv`：日度收益、基准、对标等
- `data/results_raw/backtest_positions.csv`：每日持仓细节

---

#### 方案二：Qlib qrun 一键模式

Qlib 原生提供的高级用户界面，无需编写 Python 代码。

```bash
# Windows
cd c://Users/ASUS/Desktop/my-project
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
qrun config_new.yaml

# Linux / macOS
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
qrun config_new.yaml
```

或直接运行 `.bash` 脚本。

**配置说明 (`config_qrun.yaml`)**
完整的 YAML 配置，定义了：
- **qlib_init**：MLflow 实验管理器
- **data_handler_config**：数据时间范围和股票列表
- **port_analysis_config**：策略和回测参数
- **task**：模型、数据集加载、因子特征


**输出**
- `data/results_qrun/`：MLflow 管理的实验结果
- 包含预测信号、回测报告、评估指标

---


## 📊 输出结果说明

### 方案一输出(只有回测报告和持仓记录)

#### backtest_report.csv
```
date,benchmark_return,return,excess_return,sharpe_ratio,...
2025-06-16,0.0123,0.0156,0.0033,1.25,...
2025-06-17,0.0045,0.0067,0.0022,1.18,...
```

关键指标：
- **return**：组合日收益率
- **benchmark_return**：基准（沪深300）日收益率
- **excess_return**：超额收益率
- **sharpe_ratio**：夏普比率
- **年化收益**、**最大回撤**、**胜率** 等

#### backtest_positions.csv
```
date,symbol,weight,market_value,shares,...
2025-06-16,000001,0.0245,2450000,1000,...
2025-06-16,000002,0.0198,1980000,800,...
```

### 方案二输出

结果存储在 MLflow 后端（通常为 `data/results_qrun/`），包括：
- Qlib 原生的模型评估指标
- 因子分析结果
- 回测报告和持仓记录

---

## ⚠️ 注意事项

1. **聚宽 API 限制**
   - 请求频率可能受限，脚本内已添加延时
   - 注意账户配额和数据权限

2. **Qlib 数据下载**
   - 初次使用需要下载完整的 Qlib 数据源（较大）
   - 建议设置合理的数据路径

3. **线程限制**
   - `.bash` 和 `workflow.py` 中已限制 OMP 线程数
   - 防止 LightGBM 和 Numpy 过度并行导致性能下降

4. **内存占用**
   - CSI300 成分股较多，计算 Alpha 因子耗时较长
   - 建议在配置中合理设置 `alpha_factors` 数量

5. **数据对齐**
   - 确保股票列表、日期范围、数据路径配置一致
   - 缺失数据会自动填充或跳过，检查日志以确保数据质量

---

## 📚 参考资源

- **Qlib 官方文档**：[https://qlib.readthedocs.io/](https://qlib.readthedocs.io/)
- **聚宽 API 文档**：[https://www.joinquant.com/help/api](https://www.joinquant.com/help/api)
- **LightGBM 文档**：[https://lightgbm.readthedocs.io/](https://lightgbm.readthedocs.io/)
- **Alpha101 因子**：[https://arxiv.org/abs/1601.00991](https://arxiv.org/abs/1601.00991)

---

## 📝 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新**：2025-03-24  
**项目状态**：维护中 ✅
