# -*- coding: utf-8 -*-
"""
ARMS 反射引擎模块 — ReflexEngine
著作权人：曹修达 v1.0

快系统：基于规则的快速反射机制
  条件匹配 → 直接执行，不经过深度思考（慢系统）
  类似于人类的条件反射。
"""

import os
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from .config import Config
from .utils import ensure_dir, read_md, write_md, today_str


@dataclass
class ReflexRule:
    """一条反射规则。
    trigger:    触发条件（关键词/正则）
    action:     动作描述
    priority:   优先级（0-9，9最高）
    enabled:    是否启用
    count:      触发次数
    category:   分类（"direct"=直接执行 | "check"=先检查 | "ask"=先问）
    """
    trigger: str = ""
    action: str = ""
    priority: int = 5
    enabled: bool = True
    count: int = 0
    category: str = "direct"

    def matches(self, text: str) -> bool:
        """检查文本是否匹配触发器。支持正则。"""
        try:
            return bool(re.search(self.trigger, text, re.IGNORECASE))
        except re.error:
            return self.trigger.lower() in text.lower()

    def to_dict(self):
        return {
            "trigger": self.trigger,
            "action": self.action,
            "priority": self.priority,
            "enabled": self.enabled,
            "count": self.count,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            trigger=d.get("trigger", ""),
            action=d.get("action", ""),
            priority=d.get("priority", 5),
            enabled=d.get("enabled", True),
            count=d.get("count", 0),
            category=d.get("category", "direct"),
        )


class ReflexEngine:
    """反射引擎。管理触发规则集，执行匹配和动作。"""

    def __init__(self, config=None):
        self.config = config or Config()
        self._rules: List[ReflexRule] = []
        self._loaded = False

    # ── 规则管理 ──

    def load_rules(self):
        """从 reflex.json 加载规则。"""
        path = self.config.reflex_path
        if not os.path.exists(path):
            self._rules = self._default_rules()
            self.save_rules()
            return
        try:
            data = json.loads(read_md(path) or "[]")
            self._rules = [ReflexRule.from_dict(r) for r in data]
        except (json.JSONDecodeError, Exception):
            self._rules = self._default_rules()
        self._loaded = True

    def save_rules(self):
        """保存规则到 reflex.json。"""
        ensure_dir(self.config.system_path)
        data = [r.to_dict() for r in self._rules]
        write_md(self.config.reflex_path, json.dumps(data, ensure_ascii=False, indent=2))

    def _default_rules(self):
        """返回默认的内置规则集。"""
        return [
            ReflexRule("看看服务器|连服务器|ssh.*服务器", "SSH 三跳到服务器", 9, category="direct"),
            ReflexRule("去电脑看看|去pc|PC.*目录", "SSH 到 PC 查看目录", 8, category="direct"),
            ReflexRule("工作日志|worklog", "检查本地和服务端工作日志", 8, category="check"),
            ReflexRule("不对", "直接认错 + 改正", 7, category="direct"),
            ReflexRule("MAN", "暗号续接 See you again~~→MAN!", 9, category="direct"),
            ReflexRule("有人堵桥来", "回「他老冯起飞」", 9, category="direct"),
            ReflexRule("EMERGENCY|URGENT", "紧急模式，高优先级处理", 9, category="direct"),
            ReflexRule("清理pc|清理临时文件|释放空间", "执行 pc-cleanup.sh --dry-run", 7, category="check"),
            ReflexRule("回收站|送回收站", "用 Recycle-Item.ps1 送回收站", 7, category="check"),
            ReflexRule("密码", "身份验证：谁 + 初中语文老师", 9, category="ask"),
            ReflexRule("在吗|在线", "回答 + 自检", 6, category="direct"),
        ]

    def add_rule(self, rule: ReflexRule):
        """添加一条规则。"""
        self._rules.append(rule)
        self.save_rules()

    def remove_rule(self, trigger: str):
        """按触发条件删除规则。"""
        self._rules = [r for r in self._rules if r.trigger != trigger]
        self.save_rules()

    # ── 匹配与执行 ──

    def match(self, text: str) -> Optional[ReflexRule]:
        """匹配输入文本，返回匹配到的最高优先级规则。"""
        if not self._loaded:
            self.load_rules()
        matched = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.matches(text):
                matched.append(rule)
        if not matched:
            return None
        # 按优先级降序排序
        matched.sort(key=lambda r: -r.priority)
        best = matched[0]
        best.count += 1
        self.save_rules()
        return best

    def match_all(self, text: str) -> List[ReflexRule]:
        """匹配所有符合条件的规则。"""
        if not self._loaded:
            self.load_rules()
        matched = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.matches(text):
                matched.append(rule)
                rule.count += 1
        self.save_rules()
        return matched

    # ── 命令导出 ──

    def export_as_markdown(self) -> str:
        """将规则集导出为 Markdown 表格。"""
        lines = [
            "# 快系统触发条件表",
            "",
            "| 触发条件 | 动作 | 优先级 | 触发次数 |",
            "|---------|------|--------|---------|",
        ]
        for r in sorted(self._rules, key=lambda x: -x.priority):
            status = "✅" if r.enabled else "⛔"
            lines.append(f"| {status} {r.trigger} | {r.action} | {r.priority} | {r.count} |")
        lines.append("")
        lines.append(f"*共 {len(self._rules)} 条规则 | 生成于 {today_str()}*")
        return "\n".join(lines)
