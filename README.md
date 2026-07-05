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
-   增加离线单元测试和真实联网验收测试，便于持续维护。

后续计划
--------

-   继续梳理和补齐原项目中失效或不稳定的行情接口。
-   根据使用反馈扩展更多批量查询、分页查询和数据清洗能力。
-   保持兼容优先，尽量不破坏原 `mootdx` 用户已有代码。
-   欢迎通过 Issue 提交需求、错误样例、主站连接问题和协议差异。

运行环境
--------

-   操作系统: Windows / MacOS / Linux 都可以运行。
-   Python: 3.8 以及以上版本。

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
