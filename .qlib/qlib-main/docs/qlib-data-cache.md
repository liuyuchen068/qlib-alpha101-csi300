# qlib.data.cache — 模块详解（中文）

本文档对 `qlib/data/cache.py` 做详细说明，补充专业术语解释与使用示例，便于理解缓存子系统的设计与使用方式。

**概览**

- **模块职责**: 提供内存缓存与磁盘缓存（针对 expression 和 dataset）的通用实现与工具函数，并封装读写锁（基于 Redis）以解决多进程/多实例下的并发读写问题。该模块实现了多种缓存机制（内存、磁盘、基于 URI 的缓存、本地简单缓存），并提供索引管理、缓存生成、更新与清理的工具。
- **核心设计理念**: 将缓存分层（内存 vs 磁盘），并按提供者类型拆分（ExpressionCache: 对表达式结果做缓存；DatasetCache: 对数据集做缓存）；在服务器端以磁盘形式存储缓存文件，在分布式/客户端场景使用 URI 做协调与传输。

**配置项（来自 C）**

- `C.mem_cache_size_limit`：内存缓存最大容量（数值含义取决于 `mem_cache_limit_type`）。
- `C.mem_cache_limit_type`：内存限制类型，`"length"` 表示按数量计数，`"sizeof"` 表示按对象大小(sys.getsizeof)计数。
- `C.mem_cache_expire`：内存缓存的过期阈值（秒），超过该时间将被视为过期。
- `C.features_cache_dir_name` / `C.dataset_cache_dir_name`：磁盘缓存目录名，用于生成缓存路径。
- `C.dpm.get_data_uri(freq)`：数据存储根 URI（Path）生成函数，缓存路径基于此构建。
- `C.dump_protocol_version`：pickle 的序列化协议版本。
- `C.dataset_provider`：决定是否使用本地 provider（在 DatasetURICache 中参考）。
- `C["local_cache_path"]`：SimpleDatasetCache 使用的本地缓存目录。

（注意：确切的配置名与含义请参见项目全局配置文件）

---

**主要类与职责**

- `MemCacheUnit` (抽象类)
  - 内存缓存单元基类（采用 OrderedDict 保持 LRU 顺序），维护 `_size` 与 `od`（OrderedDict）。
  - 子类须实现 `_get_value_size(value)` 来计算项大小（用于容量控制）。
  - 提供 `__setitem__/__getitem__/pop/popitem/clear` 等操作，设置时会将 key 移到末尾（表示最近使用），当容量超限会弹出最旧项（LRU）。

- `MemCacheLengthUnit` / `MemCacheSizeofUnit`
  - 前者将每个缓存项视作大小 1（按长度限制），后者使用 `sys.getsizeof` 估算对象大小（按字节限制）。

- `MemCache`
  - 顶层内存缓存容器，包含三个子缓存：日历(`'c'`)、工具表/标的(`'i'`)与特征(`'f'`)。
  - 通过 `H = MemCache()` 全局实例访问（代码底部）。

- `MemCacheExpire`
  - 以 (value, timestamp) 形式存放缓存项，并根据 `CACHE_EXPIRE` 判断是否过期。
  - 提供 `set_cache(mem_cache, key, value)` 和 `get_cache(mem_cache, key)`。

- `CacheUtils`
  - 包含与缓存元信息、锁相关的工具函数：`visit`（更新 .meta 的访问次数/时间）、`reset_lock`（清理 Redis 锁）、以及基于 `redis_lock` 实现的 `reader_lock` / `writer_lock` 上下文管理器。
  - `reader_lock` 与 `writer_lock` 协同实现读者-写者锁：多个并发读允许，但写入时需独占（写者优先由实现细节决定）。

- `BaseProviderCache`
  - 缓存包装器基类，接收一个 `provider`（如 expression provider / dataset provider），并把未实现的缓存逻辑交给子类。
  - 提供 `check_cache_exists`、`clear_cache`、`get_cache_dir` 等通用工具。

- `ExpressionCache` / `DatasetCache` (抽象基类)
  - 分别定义表达式与数据集缓存的接口：`_uri`、`_expression` / `_dataset`、`update` 等方法需子类实现以匹配具体的缓存策略。
  - `DatasetCache` 还定义了 `cache_to_origin_data`（将缓存列名转回原始列名）与 `normalize_uri_args`。

- `DiskExpressionCache`
  - 针对服务器端的表达式缓存实现：以二进制 `.bin`（以及 `.meta`）保存序列化的数值数组（float），并在请求时通过索引读取子区间。
  - 当缓存缺失或表达式是非原始 `Feature` 时，会调用 provider 计算并生成缓存（调用 `gen_expression_cache`）。
  - `update` 方法用于在缓存落后于最新日历时追加数据（按表达式的 extended window 计算需要追加/删除的部分）。

- `DiskDatasetCache`
  - 针对服务器端的数据集缓存实现：缓存由三部分组成（`.index`、`.meta`、数据 HDF 文件），数据以 HDFStore 存放，按 `datetime` 排序。
  - `IndexManager` 负责索引（记录每个日期对应的 start/end 行索引），并支持从磁盘同步、写回、追加与根据时间区间获取对应行区间。
  - `gen_dataset_cache` 会调用 provider 获取完整历史区间的数据，写入 `.data`、`.meta` 与 `.index`（并最终将 `.data` 重命名为无后缀的缓存文件）。
  - `read_data_from_cache` 会基于 IndexManager 得到对应文件行区间，再用 `HDFStore.select` 读取子区间并恢复原始列名顺序。
  - `update` 支持增量更新：根据字段的 extended-window（可能用到未来信息）决定需要移除多少历史周期，然后 append 新数据并更新索引/`.meta`。

- `SimpleDatasetCache`
  - 简单本地缓存实现（适用于客户端或本地开发）；将整个 DataFrame 用 pickle 存储到 `local_cache_path`。

- `DatasetURICache`
  - 适用于 server-client 模式：服务器生成缓存并返回 URI，客户端可基于 URI 直接读取缓存文件；若 `local` provider，则直接使用本地 provider。它会优先尝试内存层（`H`）的 URI 缓存与磁盘路径判断。

- `CalendarCache` / `MemoryCalendarCache`
  - 对时间日历（calendar）的内存缓存实现，使用 `H['c']` 做缓存并通过 `MemCacheExpire` 管理过期。

---

**工作流（高层）**

1. 请求数据（expression/dataset）时先判断是否启用缓存（disk_cache 参数）。
2. 若启用，构造 cache URI（由 `_uri` 方法决定）并检测缓存是否存在（包含 .meta/.index 等）。
3. 若缓存存在，通过 IndexManager/二进制读取直接按区间读取并返回（快速）。若缓存不存在或需替换，调用 provider 计算并由相应机制生成缓存文件（并用 writer_lock 防止并发写入）。
4. 对于并发，读操作有读锁 protocol（允许并发读），写操作需要独占写锁（通过 Redis 锁实现）。
5. 内存层（H）用于存放常用的 uri/数据副本以减少磁盘或远程读取。

---

**重要实现细节与注意事项**

- LRU 行为：`MemCacheUnit` 用 OrderedDict 并在访问时将 key 移到末尾；插入时若容量超限则弹出 oldest（last=False），实现 LRU。
- 大文件并发问题：`CacheUtils.reader_lock` 中采用了 redis 的 `reader` 计数器与 rlock/wlock 协同来实现读者-写者锁；但源代码中也注释指出在某些分支（表达式读）并未使用 reader_lock，存在并发风险（FIXME 注释）。
- 数据类型一致性：DiskDatasetCache 在 `update` 时尝试把新 append 数据的列 dtype 与已有缓存 schema 对齐；若类型不同会失败，因此用户在扩展字段或计算方式时需注意 dtype 一致性。
- 索引语义：Index 文件中 `start` 为闭区间（包含），`end` 为开区间（不包含），用于映射每个日期在 `.data` 文件中的行起止位置。
- 二进制表达式缓存采用 float 类型(`<f`)，并用 numpy 原始二进制写入/读取以提升 IO 性能。
- extended window: 表达式可能需要未来或左右扩展窗口（如滚动计算），更新缓存时要考虑移除末尾会影响窗口的依赖。

---

**常见术语（专业术语解释）**

- Provider: 数据提供者，封装数据源读取逻辑（如从数据库或 CSV 读取原始数据）并提供统一接口（expression/dataset）。
- Expression: qlib 中的表达式/特征计算表达式，可能是原始 feature（如 `$close`）或组合/运算表达式（如 rolling mean）。
- Feature: 表示可直接读取的原始字段或已注册的特征算子实例。
- HDFStore: pandas 提供的 HDF5 存储接口，支持分块读取（`select`）与追加（`append`），适合大表的分段 IO。
- Reader/Writer Lock: 并发控制机制，允许多个读者并发读取，但写操作需要独占，以避免读写冲突。实现中使用 `redis_lock` 与 Redis 原子计数器实现分布式锁。
- LRU（Least Recently Used）: 最近最少使用缓存淘汰策略，使用 OrderedDict 维护访问顺序。
- URI Cache: 将缓存以文件路径（URI）方式表示并在服务端生成，客户端只需通过 URI 下载或直接访问该缓存文件。
- Extended Window（扩展窗口）: 某些表达式在计算时需要额外的历史或未来数据（如卷积/滞后特征），`get_extended_window_size` 返回左右扩展的天数，用于在生成/更新缓存时正确裁剪/追加数据。

---

**示例与使用说明**

- 访问内存缓存示例：

```python
from qlib.data import cache as qcache
# 全局内存缓存 H
H = qcache.H
# 对特征层（'f'）以 URI 缓存为 key 存放一个 DataFrame 的副本（或 uri）
# 存：
qcache.MemCacheExpire.set_cache(H['f'], 'feature-uri-key', 'some-uri-or-df')
# 取：
value, expire = qcache.MemCacheExpire.get_cache(H['f'], 'feature-uri-key')
```

- 强烈推荐使用模块提供的上下文锁来保护写入：

```python
# 在生成或更新磁盘缓存时（server 侧）
from qlib.data.cache import CacheUtils, DiskDatasetCache
r = get_redis_connection()
with CacheUtils.writer_lock(r, 'some-lock-name'):
    # 调用 DiskDatasetCache.gen_dataset_cache 或 DiskExpressionCache.gen_expression_cache
    pass
```

- 生成 dataset cache 的高层流程（伪代码）:

```text
1. 构造 cache uri = hash_args(normalized_instruments, normalized_fields, freq, ...)
2. cache_path = get_cache_dir(freq) / cache_uri
3. if cache exists: read via IndexManager (返回指定时间区间)
4. else: acquire writer_lock -> provider.dataset(full_calendar) -> write .data/.meta/.index
```

---

**常见问题与建议**

- 如果遇到 Redis 锁残留（导致无法 acquire），可调用 `CacheUtils.reset_lock()` 在 dev 环境清理所有 redis_lock（注意：该操作影响所有锁，线上谨慎使用）。
- 在集群/多进程环境中，尽量使用 `DiskDatasetCache` / `DiskExpressionCache` 的读写锁保护生成与更新过程，避免部分路径未创建而导致的并发写错误。
- 对于仅在本地开发或无需分布式访问的场景，优先使用 `SimpleDatasetCache`，它更简单并且基于 pickle。
- 更新缓存（`update`）函数依赖字段表达式的 extended window，大量字段不同 ETD 时可能导致较复杂的移除/追加逻辑，关注日志与返回值（0/1/2 表示成功/无须更新/失败）。

---

文档已生成到： [docs/qlib-data-cache.md](docs/qlib-data-cache.md)

需要我把该文档转换成英文版、或生成 side-by-side（中英对照）版本吗？