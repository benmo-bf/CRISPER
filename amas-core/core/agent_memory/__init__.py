# -*- coding: utf-8 -*-
"""
Agent 递归记忆管理系统 (ARMS) v1.0
著作权人：曹修达 | Copyright © 2026
许可证：专有软件，保留所有权利

三层递归记忆管理引擎：日记(短期) → 长期记忆 → 专题网络
模拟海马体→新皮层记忆巩固模型，支持AI Agent跨会话记忆持久化。
"""

__version__ = "1.0.0"
__author__ = "曹修达"
__license__ = "专有软件"
__description__ = "AI Agent 三层递归记忆管理引擎"

from .store import MemoryStore
from .consolidator import ConsolidationEngine, KeyEvent
from .index import IndexNetwork, IndexNode
from .reflex import ReflexEngine, ReflexRule
from .seed import SeedLoader
from .config import Config
from .utils import ensure_dir, read_md, write_md, append_md

__all__ = [
    "MemoryStore", "ConsolidationEngine", "KeyEvent",
    "IndexNetwork", "IndexNode",
    "ReflexEngine", "ReflexRule",
    "SeedLoader", "Config",
    "ensure_dir", "read_md", "write_md", "append_md",
]
