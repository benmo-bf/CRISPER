# -*- coding: utf-8 -*-
"""
ARMS 全局配置模块
著作权人：曹修达 v1.0
"""

import os


class Config:
    """ARMS 系统配置。可通过 init() 时传入参数覆盖默认值。"""

    # 默认目录名
    MEMORY_DIR = "memory"          # 记忆数据目录
    SEED_DIR = "seed_memory"       # 种子记忆目录
    SYSTEM_DIR = ".agent-memory"        # 系统配置目录

    # 默认文件
    LONGTERM_FILE = "MEMORY.md"    # 长期记忆文件名
    INDEX_FILE = os.path.join(MEMORY_DIR, "index.md")  # 索引路径
    REFLEX_FILE = os.path.join(SYSTEM_DIR, "reflex.json")

    # 巩固参数
    CONSOLIDATE_HOUR = 1           # 巩固执行时间（凌晨1点）
    CONSOLIDATE_WINDOW = 3         # 窗口小时数
    DIARY_RETENTION_DAYS = 90      # 日记保留天数

    # 索引搜索
    MAX_SEARCH_RESULTS = 20        # 最大搜索结果数
    TAG_MIN_LENGTH = 2             # 标签最小长度

    def __init__(self, workspace=None):
        self.workspace = workspace or os.getcwd()

    # ── 路径计算 ──
    @property
    def memory_path(self):
        return os.path.join(self.workspace, self.MEMORY_DIR)

    @property
    def system_path(self):
        return os.path.join(self.workspace, self.SYSTEM_DIR)

    @property
    def longterm_path(self):
        return os.path.join(self.workspace, self.LONGTERM_FILE)

    @property
    def index_path(self):
        return os.path.join(self.workspace, self.INDEX_FILE)

    @property
    def reflex_path(self):
        return os.path.join(self.workspace, self.REFLEX_FILE)

    def diary_path(self, date_str):
        """获取指定日期的日记文件路径。date_str: '2026-05-31'"""
        return os.path.join(self.memory_path, f"{date_str}.md")

    def __repr__(self):
        return f"Config(workspace={self.workspace})"
