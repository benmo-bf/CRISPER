# -*- coding: utf-8 -*-
"""
ARMS 核心存储模块 — MemoryStore
著作权人：曹修达 v1.0

管理三层记忆架构：
  - 短期（diary / YYYY-MM-DD.md）
  - 长期（MEMORY.md）
  - 专题（memory/*.md）
"""

import os
import re
from datetime import datetime, timedelta

from .config import Config
from .utils import ensure_dir, read_md, write_md, append_md, today_str, list_md_files


class MemoryStore:
    """核心记忆存储，管理三层记忆的读写操作。"""

    def __init__(self, config=None):
        self.config = config or Config()

    # ═══════════════════════════════════
    #  第1层：短期记忆（日记）
    # ═══════════════════════════════════

    def create_diary(self, date_str=None, content=""):
        """创建或覆盖指定日期的日记文件。返回文件路径。"""
        date_str = date_str or today_str()
        path = self.config.diary_path(date_str)
        if os.path.exists(path) and not content:
            return path  # 已有内容，不覆盖空内容
        write_md(path, content)
        return path

    def get_diary(self, date_str=None):
        """读取指定日期的日记内容。"""
        date_str = date_str or today_str()
        return read_md(self.config.diary_path(date_str))

    def append_diary(self, date_str=None, content=""):
        """追加内容到日记末尾。返回文件路径。"""
        date_str = date_str or today_str()
        path = self.config.diary_path(date_str)
        append_md(path, content)
        return path

    def list_diaries(self, days=30):
        """列出最近 N 天的日记列表。返回 [(date_str, path), ...] 最新在前。"""
        result = []
        now = datetime.now()
        for i in range(days):
            d = now - timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            path = self.config.diary_path(ds)
            if os.path.exists(path):
                result.append((ds, path))
        return result

    def search_diaries(self, keyword, days=90):
        """在最近日记中搜索关键词。返回 [(date_str, snippet), ...]"""
        result = []
        for ds, path in self.list_diaries(days):
            content = read_md(path)
            if keyword.lower() in content.lower():
                idx = content.lower().find(keyword.lower())
                start = max(0, idx - 40)
                end = min(len(content), idx + len(keyword) + 40)
                snippet = content[start:end].replace("\n", " ")
                result.append((ds, snippet))
        return result

    # ═══════════════════════════════════
    #  第2层：长期记忆（MEMORY.md）
    # ═══════════════════════════════════

    def read_longterm(self):
        """读取长期记忆文件。"""
        return read_md(self.config.longterm_path)

    def update_longterm(self, events):
        """将一组事件追加到长期记忆。
        events: [{"date": str, "summary": str, "tags": [str]}, ...]
        """
        content = self.read_longterm()
        if not content.strip():
            content = f"# MEMORY.md — 长期记忆\n\n*最后更新: {today_str()}*\n\n---\n\n"
        for ev in events:
            tag_str = " ".join(f"`#{t}`" for t in ev.get("tags", []))
            line = f"- **{ev['date']}** — {ev['summary']} {tag_str}\n"
            content += line
        write_md(self.config.longterm_path, content)
        return True

    def append_longterm(self, text):
        """追加任意文本到长期记忆。"""
        append_md(self.config.longterm_path, f"\n{text}")
        return True

    # ═══════════════════════════════════
    #  第3层：专题记忆（memory/*.md）
    # ═══════════════════════════════════

    def get_thematic(self, name):
        """读取专题记忆文件。name 不含 .md"""
        path = os.path.join(self.config.memory_path, f"{name}.md")
        return read_md(path)

    def list_thematics(self):
        """列出所有专题记忆文件。返回 [name, ...]"""
        files = list_md_files(self.config.memory_path)
        return [f.replace(".md", "") for f in files if f != "index.md"]

    def update_thematic(self, name, content, append=False):
        """写入或追加专题记忆。"""
        path = os.path.join(self.config.memory_path, f"{name}.md")
        if append and os.path.exists(path):
            append_md(path, f"\n---\n{content}")
        else:
            write_md(path, content)
        return path

    # ═══════════════════════════════════
    #  初始化
    # ═══════════════════════════════════

    def init_storage(self):
        """初始化记忆存储目录结构。"""
        ensure_dir(self.config.memory_path)
        ensure_dir(self.config.system_path)
        if not os.path.exists(self.config.longterm_path):
            write_md(self.config.longterm_path,
                     "# MEMORY.md — 长期记忆\n\n*初始化于 " + today_str() + "*\n\n---\n")
        index_path = self.config.index_path
        if not os.path.exists(index_path):
            write_md(index_path,
                     "# 记忆索引\n\n> 标签 → 文件 → 事件 双向索引网络\n\n*初始化于 " + today_str() + "*\n\n---\n")
        return True
