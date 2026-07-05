mootdxplus - 通达信数据读取接口
==============================

[![GitHub stars](https://img.shields.io/github/stars/BiomancerGame/mootdxPlus?style=social)](https://github.com/BiomancerGame/mootdxPlus)
[![GitHub issues](https://img.shields.io/github/issues/BiomancerGame/mootdxPlus)](https://github.com/BiomancerGame/mootdxPlus/issues)
[![License](https://img.shields.io/github/license/BiomancerGame/mootdxPlus)](LICENSE)

## 项目说明

mootdxplus 是在原 [mootdx](https://github.com/mootdx/mootdx) 项目基础上继续维护和扩展的版本。

非常感谢 mootdx 项目以及原作者长期以来的工作。我非常喜欢之前的 mootdx 项目，它为通达信数据读取提供了很好的基础。由于原项目目前更新较少，本项目会在尊重原项目设计和开源协议的基础上，继续修复问题、补充接口能力，并逐步增加更多新的功能。

当前项目名称为 **mootdxplus**。为了兼容已有代码，Python 包名和导入路径仍保持 `mootdx`，例如：

```python
from mootdx.quotes import Quotes
```

如果你也需要一个持续维护、可扩展、对量化研究和数据分析更友好的通达信数据读取工具，欢迎 Star、提 Issue 或提交 PR。你的反馈会直接影响这个项目接下来优先补齐哪些能力。

**郑重声明: 本项目只作学习交流, 不得用于任何商业目的.**

-   开源协议: MIT license
-   原项目仓库: <https://github.com/mootdx/mootdx>
-   原项目文档: <https://www.mootdx.com>
-   当前项目仓库: <https://github.com/BiomancerGame/mootdxPlus>
-   问题交流: <https://github.com/BiomancerGame/mootdxPlus/issues>

当前增强能力
------------

-   修复并增强 TDX 行情主站探测能力，提升 `bestip=True` 的可用性。
-   修复历史分笔 `transactions()` 参数调用问题，补充 `date`、`datetime`、`code`、`order` 字段。
-   新增 `transactions_all()`，支持按日期分页获取全日历史分笔。
-   新增 `bars_all()` / `index_bars_all()`，支持全量 K 线分页获取。
-   新增 `quotes_batch()`，支持批量行情自动拆批。
-   新增 `quote_depth()`，支持五档盘口字段读取。
-   新增 `auction()`、`capital_flow()`、`fund_flow()`、`boards()`、`board_members()`、`belong_boards()`、`board_summary()`、`board_ranking()`、`market_stat()`、`symbol_info()`、`price_limits()`，补齐 P1-B 核心行情增强接口。
-   新增 `minutes_recent()`、`minute_extra()`、`mini_chart()`、`gbbq()`、`shares_at()`、`turnover()`、`finance_batch()`，补齐 P2 数据补全接口。
-   新增 `mootdx.cninfo`、`mootdx.indicators`、`mootdx.offline`，支持公告检索、技术指标和本地 vipdoc 写入。
-   增加离线单元测试和真实联网验收测试，便于持续维护。

### P1 行情能力

| 优先级 | 能力 | 方法 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| P1 | 历史分笔全日分页 | `transactions_all()` | 已支持 | 基于历史分笔分页合并，补齐高频成交数据。 |
| P1 | 五档盘口/深度行情 | `quote_depth()` | 已支持 | 基于 TDX 已解析盘口字段，便于构建行情面板。 |
| P1 | 批量行情自动拆批 | `quotes_batch()` | 已支持 | 自动按批拆分大列表，提升大批量行情查询稳定性。 |
| P1 | 全量 K 线分页 | `bars_all()` / `index_bars_all()` | 已支持 | 分页拉取并合并 K 线，适合历史数据补全。 |
| P1 | 集合竞价 / 09:25 快照 | `auction()` | 已支持 | 返回开盘集合竞价阶段成交明细。 |
| P1 | 当日/近实时资金流向 | `capital_flow()` | 已支持 | 返回最新资金流向快照。 |
| P1 | 历史资金流向 | `fund_flow()` | 已支持 | 支持按日期范围过滤历史资金流向。 |
| P1 | 板块列表 / 成分股 / 所属板块 | `boards()` / `board_members()` / `belong_boards()` | 已支持 | 支持行业 `HY`、概念 `GN`，兼容 TDX 板块文件兜底。 |
| P1 | 板块汇总 / 板块排行 | `board_summary()` / `board_ranking()` | 已支持 | 汇总成交额、资金流向、涨跌家数等字段。 |
| P1 | 市场统计 | `market_stat()` | 已支持 | 基于通达信统计指数返回涨跌家数、涨跌停家数等。 |
| P1 | 个股基础信息 | `symbol_info()` | 已支持 | 返回价格、市值、估值、资金等基础字段。 |
| P1 | 涨跌停价 | `price_limits()` | 已支持 | 优先使用行情源返回结果，缺失时按 A 股基础规则兜底计算。 |

### P2 数据补全能力

| 优先级 | 能力 | 状态 |
| --- | --- | --- |
| P2 | 近期历史分时、分时副图、小走势图 | 已支持 |
| P2 | GBBQ 股本变迁、指定日期股本、换手率辅助计算 | 已支持 |
| P2 | 批量财务基础信息 | 已支持 |
| P2 | 公告检索 `mootdx.cninfo` | 已支持 |
| P2 | 技术指标 `mootdx.indicators`，首批 MACD/KDJ/RSI/BOLL | 已支持 |
| P2 | 离线数据写入 / 同步到本地通达信 `vipdoc` | 已支持 |

### 后续路线图

| 优先级 | 能力 | 状态 |
| --- | --- | --- |
| P3 | 结构化模型 + JSON 序列化 | 规划中 |
| P3 | CLI JSON / CSV / Table 输出增强 | 规划中 |
| P3 | MCP 工具服务 | 规划中 |
| P3 | 可选 Web API | 规划中 |

后续计划
--------

-   继续梳理和补齐原项目中失效或不稳定的行情接口。
-   根据使用反馈扩展更多批量查询、分页查询和数据清洗能力。
-   保持兼容优先，尽量不破坏原 `mootdx` 用户已有代码。
-   欢迎通过 Issue 提交需求、错误样例、主站连接问题和协议差异。

运行环境
--------

-   操作系统: Windows / MacOS / Linux 都可以运行。
-   Python: 3.8 - 3.14。

安装方法
--------

> 当前代码仓库名为 `mootdxplus`，导入路径仍兼容 `mootdx`。

### 从 GitHub 安装

```shell
pip install -U "git+https://github.com/BiomancerGame/mootdxPlus.git"
```

这个命令会直接安装本项目以及项目声明的依赖，不需要再单独安装原 `mootdx`。

### 本地开发安装

```shell
git clone git@github.com:BiomancerGame/mootdxPlus.git
cd mootdxPlus
pip install -e .
```

### 升级安装

```shell
pip install -U "git+https://github.com/BiomancerGame/mootdxPlus.git"
```

使用说明
--------

> 以下只列举一些常用例子。原 `mootdx` 用法大部分保持兼容，新增能力会优先在本 README 和 Issue 中说明。

### 通达信离线数据读取

```python
from mootdx.reader import Reader

# market 参数 std 为标准市场(就是股票), ext 为扩展市场(期货、黄金等)
# tdxdir 是通达信的数据目录, 根据自己的情况修改
reader = Reader.factory(market='std', tdxdir='C:/new_tdx')

# 读取日线数据
reader.daily(symbol='600036')

# 读取分钟数据
reader.minute(symbol='600036')

# 读取时间线数据
reader.fzline(symbol='600036')
```

### 通达信线上行情读取

```python
from mootdx.quotes import Quotes

# 标准市场
client = Quotes.factory(market='std', multithread=True, heartbeat=True)

# K 线数据
client.bars(symbol='600036', frequency=9, offset=10)

# 指数
client.index(symbol='000001', frequency=9)

# 分钟
client.minute(symbol='000001')

# 全量 K 线分页
client.bars_all(symbol='600036', frequency=9)

# 历史分笔全日分页
client.transactions_all(symbol='000001', date='20170209')

# 批量行情自动拆批
client.quotes_batch(['000001', '600036'])

# 五档盘口
client.quote_depth(['000001', '600036'])

# 集合竞价 / 09:25 快照
client.auction('000001')

# 资金流向
client.capital_flow('000001')
client.fund_flow('000001', start='20260701', end='20260703')

# 板块能力
client.boards(type='HY')
client.board_members('BK0475')
client.belong_boards('000001')
client.board_summary('BK0475')
client.board_ranking(type='HY', sort_by='change', top=20)

# 市场统计 / 个股基础信息 / 涨跌停价
client.market_stat()
client.symbol_info('000001')
client.price_limits('000001')

# P2 数据补全
client.minutes_recent('000001', days=5)
client.minute_extra('000001')
client.mini_chart('000001')
client.gbbq('000001', filepath='C:/new_tdx/T0002/hq_cache/gbbq')
client.shares_at('000001', '2024-01-01', filepath='C:/new_tdx/T0002/hq_cache/gbbq')
client.turnover('000001', date='2024-01-01', volume=1000000, filepath='C:/new_tdx/T0002/hq_cache/gbbq')
client.finance_batch(['000001', '600036'])
```

### 通达信财务数据读取

```python
from mootdx.affair import Affair

# 远程文件列表
files = Affair.files()

# 下载单个
Affair.fetch(downdir='tmp', filename='gpcw19960630.zip')

# 下载全部
Affair.parse(downdir='tmp')
```

### 巨潮公告检索

```python
from mootdx.cninfo import CninfoClient

client = CninfoClient()
announcements = client.get_announcements('000001', count=5)

# 下载单条公告 PDF
client.download_pdf(announcements.iloc[0], dest_dir='tmp')
```

### 技术指标

```python
from mootdx.indicators import MACD, KDJ, RSI, BOLL, compute_indicators

bars = client.bars_all(symbol='600036', frequency=9)

MACD(bars)
KDJ(bars)
RSI(bars)
BOLL(bars)

compute_indicators(bars, ['MACD', 'KDJ', 'RSI', 'BOLL'])
```

### 通达信离线数据写入

```python
from mootdx.offline import append_daily, append_minute, write_daily, write_minute

# 写入或追加 vipdoc 日线
write_daily('C:/new_tdx/vipdoc/sh/lday/sh600036.day', bars, append=True)
append_daily('C:/new_tdx/vipdoc/sh/lday/sh600036.day', bars)

# 写入或追加 1 分钟 / 5 分钟线
write_minute('C:/new_tdx/vipdoc/sh/minline/sh600036.lc1', minute_df, kind='lc1', append=True)
append_minute('C:/new_tdx/vipdoc/sh/fzline/sh600036.lc5', five_minute_df, kind='lc5')
```

参与贡献
--------

欢迎大家一起把 mootdxplus 维护得更好。你可以：

-   提交无法连接、返回空数据、字段异常等可复现问题。
-   提供不同券商、地区、网络环境下的 TDX 主站可用性反馈。
-   补充测试样例、文档和使用示例。
-   针对新接口能力提交 PR。

交流方式
--------

-   QQ: 1431620471
-   QQ 群: 1022479289

![QQ群 1022479289](docs/img/qq-group.png)
