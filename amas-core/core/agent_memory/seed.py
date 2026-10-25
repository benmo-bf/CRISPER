# -*- coding: utf-8 -*-
"""
ARMS 种子加载器模块 — SeedLoader
著作权人：曹修达 v1.0

为新的 Agent 环境初始化记忆结构，加载种子记忆网。
种子包含：核心身份、项目注册表、基础设施、学习目录、待办管理、索引框架。
"""

import os
import shutil

from .config import Config
from .utils import ensure_dir, write_md, read_md, today_str


class SeedLoader:
    """种子记忆网加载器。将预设的记忆框架导入目标工作区。"""

    def __init__(self, config=None):
        self.config = config or Config()

    # ═══════════════════════════════════
    #  种子模板内容
    # ═══════════════════════════════════

    SEED_IDENTITY = """# IDENTITY.md — 我的身份

*由 ARMS 种子加载器初始化于 {date}*

## 核心身份

- **名字:** [在此填写]
- **类型:** [AI Agent / 个人知识助手]
- **本体:** [部署位置]

## 核心原则

- 真实比讨好重要
- 先做再优化
- 每次都成章

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_PROJECTS = """# 项目注册表

*由 ARMS 种子加载器初始化于 {date}*

---

## 进行中项目

| 项目 | 状态 | 说明 |
|------|------|------|
| | | |

## 已完成项目

| 项目 | 完成时间 | 说明 |
|------|----------|------|
| | | |

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_INFRA = """# 基础设施映射

*由 ARMS 种子加载器初始化于 {date}*

---

## 计算资源

| 设备 | 用途 | 连接方式 | 状态 |
|------|------|----------|------|

## 网络拓扑

```
[Agent] ── [主链路] ── [服务端]
```

## 关键凭证

> 注意：不要在版本控制中保留明文密码

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_LEARNINGS = """# 学习目录

*由 ARMS 种子加载器初始化于 {date}*

---

## 教训集

| # | 日期 | 教训 | 来源 |
|---|------|------|------|
| 1 | {date} | 每步操作之前：先想最坏结果 | 初始加载 |

## 成功经验

| # | 日期 | 经验 | 可复用场景 |
|---|------|------|-----------|
| 1 | {date} | 记录关键决策，方便复盘追溯 | 日常运维 |

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_TODOS = """# 待办管理

*由 ARMS 种子加载器初始化于 {date}*

---

## 高优先级

- [ ] 探索 ARMS 基本功能

## 普通

- [ ] 记录第一条日记
- [ ] 建立身份文件

## 已完成

（空）

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_INDEX = """# 记忆索引

> 标签 → 文件 → 事件 双向索引网络
> 由 ARMS 种子加载器初始化于 {date}

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    SEED_PRINCIPLES = """# 核心原则与承诺

*由 ARMS 种子加载器初始化于 {date}*

---

## 红线

- 不泄露私密信息
- 破坏性操作先问
- 网络进程不动

## 承诺

- 「每次交流都让你得到成章」

---

*种子模板由 Agent 记忆管理系统 提供*
"""

    # ═══════════════════════════════════
    #  加载器
    # ═══════════════════════════════════

    def _templ(self, text):
        """渲染模板中的 {date} 占位符。"""
        return text.format(date=today_str())

    def load_seed(self, target_dir=None, overwrite=False):
        """将种子记忆网加载到目标目录。
        target_dir: 目标工作区目录（默认为当前目录）
        overwrite: 是否覆盖已有文件
        返回加载的文件列表。
        """
        target_dir = target_dir or os.getcwd()
        memory_dir = os.path.join(target_dir, "memory")
        ensure_dir(memory_dir)

        loaded = []

        seeds = {
            os.path.join(target_dir, "IDENTITY.md"): self._templ(self.SEED_IDENTITY),
            os.path.join(target_dir, "projects.md"): self._templ(self.SEED_PROJECTS),
            os.path.join(target_dir, "infra.md"): self._templ(self.SEED_INFRA),
            os.path.join(target_dir, "learnings.md"): self._templ(self.SEED_LEARNINGS),
            os.path.join(target_dir, "todos.md"): self._templ(self.SEED_TODOS),
            os.path.join(target_dir, "principles.md"): self._templ(self.SEED_PRINCIPLES),
            os.path.join(memory_dir, "index.md"): self._templ(self.SEED_INDEX),
        }

        for path, content in seeds.items():
            if not overwrite and os.path.exists(path):
                continue  # 文件已存在，不覆盖
            write_md(path, content)
            loaded.append(path)

        return loaded

    def seed_status(self, target_dir=None):
        """检查目标目录的种子加载状态。"""
        target_dir = target_dir or os.getcwd()
        memory_dir = os.path.join(target_dir, "memory")
        files_to_check = [
            "IDENTITY.md", "projects.md", "infra.md",
            "learnings.md", "todos.md", "principles.md",
            os.path.join("memory", "index.md"),
        ]
        status = {}
        for f in files_to_check:
            path = os.path.join(target_dir, f)
            status[f] = os.path.exists(path)
        return status
