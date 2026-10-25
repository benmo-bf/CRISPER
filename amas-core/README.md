# amas-core

AMaS（Agent Memory Architecture）记忆层 —— 源码整理 + 修复版。

## 这是什么

AMaS Core 是「标签 → 文件 → 事件」三层记忆索引引擎，最初部署在 lab-linux
（AlmaLinux 10.2 / RTX 4060），配套实验性 agent 实例 KaltsitEspetanta。
本仓库是从 `AMaS_mod_v1.0.zip`（著作权人：曹修达，2026-06-06 打包）恢复的
v1 源码，加上 2026-10-25 的三处修复，以及一个只读的倒排索引工具。

```
core/agent_memory/
├── index.py         IndexNetwork：标签→文件→事件 索引 + 检索
├── store.py         存储引擎（journal / longterm）
├── consolidator.py  巩固（短期日记 → 长期记忆）
├── reflex.py        快系统触发器
├── seed.py          种子记忆
├── config.py        路径与参数
├── main.py          入口
└── utils.py         读写 / 标签解析 / 文本清洗
tests/test_basic.py  原有测试（全部通过）
tests/test_index_guard.py  本次修复的回归测试
bin/amas_index.py    只读倒排索引构建器（见下）
```

## 为什么需要修复

v1 的 `IndexNetwork` 在实际语料上有两个硬伤，直接 `rebuild_from_memory()` 会**毁库**：

1. **覆盖破坏**：`_save()` 无条件重写 `memory/index.md`，格式固定为四字段单行
   （`- **#tag** — [file](path) — context (date)`）。而现网 index.md 是富格式
   （时间 / 关键词 / 阶段 / 情境 / 情绪 / 文件 / 引申 七字段节点，167 节点 / 422KB）。
   跑一次就把整张网抹成薄薄一层。
2. **标签噪声**：`parse_tags` 用 `#([\w\u4e00-\u9fff]+)` 抓所有 `#` 后续，
   把「规则 0-16」「卦 62」的序号当标签；实测 49 个标签里大半是纯数字。
   同时实际语料几乎不用 `#tag` 语法，导致 rebuild 出 0 节点。

## 三处修复（2026-10-25）

| # | 位置 | 行为 |
|---|---|---|
| 1 | `index.py::_save` | 检测到富格式索引时**拒绝覆盖**，改写到 `index.md.rebuilt`；需要覆盖必须显式 `force=True`。非富格式则先写 `.bak-<时间戳>` 再覆盖。 |
| 2 | `index.py::normalize_tag` | 过滤纯数字、过短（<2）、停用词、文件名、纯标点；剥掉引号/破折号。 |
| 3 | `index.py::add_tags_from_text` + `_fallback_tags` | 无 `#tag` 语法时退化为「加粗 / 引号 / 短标题」提取，仍走同一套过滤；`rebuild_from_memory` 改批量写入（原来每个标签写一次盘），跳过隐藏文件与 >2MB 文件，日记用文件名日期做 node 日期。 |

回归测试：`PYTHONPATH=core python3 tests/test_index_guard.py`

## bin/amas_index.py —— 只读倒排索引

`_save` 的格式决定了 index.md 适合人读，不适合机器快查。检索路径另用一份倒排表：

```bash
python3 bin/amas_index.py build      # 词 → 文件 倒排表，写到 memory/.amas_index_map.json
python3 bin/amas_index.py query 污染 OOM
python3 bin/amas_index.py stats
python3 bin/amas_index.py coverage   # 日记日期 vs index.md 收录差
```

设计要点：
- **只读**：永不改动任何 .md。
- 两遍扫描：先算全局 document frequency，再对每个文件保留「高频词 top 60 ∪ 稀有词（df ≤ 5）」，
  这样 `contam_chain.sh` 这类只出现在少数文件的专名不会因上限被截掉。
- **tf·idf 排序**（v3）：抑制大文件偏置；df > 40% 文件的泛词（benmo / pi / memory）自动降权到 0.15。
- **中文 2-gram 回退**（v3）：`OOM内存` 这种无分隔查询，整体查不到就拆 bigram 再排。
- **包含回退**（v3）：`contam_chain` 命中 `contam_chain.sh`。

实测（277 个 md）：构建 0.6s，倒排表 4.9MB / 69k 词 / 105k 对，查询 0.1s 级。
9 条样例查询全部命中预期文件（污染→10-23、OOM→10-20、contam_chain→10-24、小畜→10-23…）。

## 已知局限

- v1 的标签提取仍是短语级（`已补齐`、`明日要点` 这类会进图），它只解决「不崩」与「不为空」，
  不等于高质量关键词索引；真正的检索走 `bin/amas_index.py`。
- 语义检索未接入（需要 embedding provider）。
- `consolidator.reflex` 依赖外部 LLM 配置，本仓库不含任何密钥。

## 许可

私有仓库，仅著作权人本人使用。
