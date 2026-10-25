# -*- coding: utf-8 -*-
"""
ARMS 记忆巩固引擎 — ConsolidationEngine
著作权人：曹修达 v1.0

模拟海马体→新皮层记忆巩固模型：
  ① 读取当日日记 → ② 提取关键事件 → ③ 合并到长期记忆 → ④ 更新索引
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .config import Config
from .utils import read_md, write_md, append_md, parse_tags, today_str, now_str
from .index import IndexNetwork
from .store import MemoryStore


@dataclass
class KeyEvent:
    """从日记中提取的关键事件。"""
    date: str = ""
    summary: str = ""
    category: str = "general"  # decision | milestone | lesson | todo | general
    tags: List[str] = field(default_factory=list)
    priority: int = 0          # 0-5, 5最高
    source_file: str = ""      # 来源日记文件


class ConsolidationEngine:
    """记忆巩固引擎。模拟海马体→新皮层的夜间记忆巩固流程。"""

    CATEGORY_KEYWORDS = {
        "decision": ["决定", "选了", "改用", "换成", "决定采用", "decide", "chose", "switch to"],
        "milestone": ["完成", "上线", "发布", "搞定", "跑通", "里程碑", "finished", "launched", "v1.0", "done"],
        "lesson": ["教训", "血的教训", "学到", "下次注意", "lesson", "learned", "never again", "切记"],
        "todo": ["需要", "还没", "待做", "下一步", "计划", "todo", "pending", "next step"],
    }

    def __init__(self, config=None):
        self.config = config or Config()
        self.store = MemoryStore(self.config)
        self.index = IndexNetwork(self.config)

    # ═══════════════════════════════════
    #  第1步：读取日记
    # ═══════════════════════════════════

    def load_diaries(self, days=1):
        """加载最近 N 天的日记。返回 {date_str: content}"""
        result = {}
        for date_str, path in self.store.list_diaries(days):
            content = read_md(path)
            if content.strip():
                result[date_str] = content
        return result

    # ═══════════════════════════════════
    #  第2步：提取关键事件
    # ═══════════════════════════════════

    def extract_key_events(self, diary_text: str, date: str = "") -> List[KeyEvent]:
        """从单篇日记文本中提取关键事件列表。
        基于规则匹配，无需外部 NLP 服务。
        """
        events = []
        if not diary_text.strip():
            return events

        lines = diary_text.split("\n")
        current_section = "general"
        buffer = []

        for line in lines:
            stripped = line.strip()

            # 识别章节标题
            heading = re.match(r"#{1,3}\s+(.+)", stripped)
            if heading:
                # 处理上一个 buffer
                if buffer:
                    ev = self._make_event("\n".join(buffer), date, current_section)
                    if ev:
                        events.append(ev)
                    buffer = []
                current_section = self._categorize(heading.group(1))
                continue

            # 列表项或正文
            if stripped and not stripped.startswith(">"):
                buffer.append(stripped)

        # 最后一段
        if buffer:
            ev = self._make_event("\n".join(buffer), date, current_section)
            if ev:
                events.append(ev)

        return events

    def _categorize(self, text):
        """根据文本内容判断分类。"""
        text_lower = text.lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return cat
        return "general"

    def _make_event(self, text, date, category):
        """从文本块创建 KeyEvent。"""
        text = text.strip()
        if not text or len(text) < 10:
            return None
        tags = parse_tags(text)
        # 计算优先级：有多个标签或包含感叹号则更高
        priority = 0
        if "!" in text or "❗" in text or "⚠️" in text:
            priority += 2
        if len(tags) >= 2:
            priority += 1
        if category == "milestone":
            priority += 1
        if category == "lesson":
            priority += 1

        return KeyEvent(
            date=date or today_str(),
            summary=text[:200],
            category=category,
            tags=tags,
            priority=min(priority, 5),
        )

    # ═══════════════════════════════════
    #  第3步：合并到长期记忆
    # ═══════════════════════════════════

    def merge_to_longterm(self, events: List[KeyEvent]) -> int:
        """将提取的事件合并到长期记忆，返回新增条目数。"""
        if not events:
            return 0
        # 按优先级排序
        events.sort(key=lambda e: -e.priority)
        # 写入长期记忆
        for ev in events:
            tag_str = " ".join(f"#{t}" for t in ev.tags[:5])
            line = f"- **{ev.date}** [{ev.category}] — {ev.summary} {tag_str}"
            self.store.append_longterm(line)
        return len(events)

    # ═══════════════════════════════════
    #  第4步：更新索引
    # ═══════════════════════════════════

    def update_index(self, events: List[KeyEvent]) -> int:
        """根据提取的事件更新标签索引。返回新增标签数。"""
        count = 0
        for ev in events:
            for tag in ev.tags:
                self.index.add_tag(
                    tag=tag,
                    filepath=f"memory/{ev.date}.md",
                    context=ev.summary[:80],
                    date=ev.date,
                )
                count += 1
        return count

    # ═══════════════════════════════════
    #  全流程：一键巩固
    # ═══════════════════════════════════

    def nightly_consolidate(self, days=1) -> dict:
        """执行完整的夜间记忆巩固流程。返回统计信息。"""
        stats = {"diaries_read": 0, "events_extracted": 0, "merged": 0, "tags_added": 0}

        diaries = self.load_diaries(days)
        stats["diaries_read"] = len(diaries)

        all_events = []
        for date_str, content in diaries.items():
            events = self.extract_key_events(content, date_str)
            all_events.extend(events)

        stats["events_extracted"] = len(all_events)
        stats["merged"] = self.merge_to_longterm(all_events)
        stats["tags_added"] = self.update_index(all_events)

        return stats

    # ═══════════════════════════════════
    #  报告生成
    # ═══════════════════════════════════

    def generate_report(self, stats: dict) -> str:
        """生成巩固报告文本。"""
        parts = [
            f"# 记忆巩固报告",
            f"",
            f"**执行时间:** {now_str()}",
            f"**扫描日记:** {stats['diaries_read']} 篇",
            f"**提取事件:** {stats['events_extracted']} 条",
            f"**合并到长期记忆:** {stats['merged']} 条",
            f"**更新索引标签:** {stats['tags_added']} 个",
            f"",
            f"---",
            f"*ARMS ConsolidationEngine v1.0*",
        ]
        return "\n".join(parts)
