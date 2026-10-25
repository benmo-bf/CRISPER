# -*- coding: utf-8 -*-
"""
ARMS 工具函数模块
著作权人：曹修达 v1.0

纯标准库实现，零外部依赖。
"""

import os
import re
from datetime import datetime


def ensure_dir(path):
    """确保目录存在，不存在则创建。"""
    os.makedirs(path, exist_ok=True)
    return path


def read_md(path):
    """读取 Markdown 文件内容，返回字符串。"""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_md(path, content):
    """写入 Markdown 文件。"""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def append_md(path, content):
    """追加内容到 Markdown 文件末尾。"""
    ensure_dir(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)


def today_str():
    """返回今天的日期字符串 'YYYY-MM-DD'。"""
    return datetime.now().strftime("%Y-%m-%d")


def now_str():
    """返回当前时间字符串 'YYYY-MM-DD HH:MM'。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def parse_tags(text):
    """从文本中提取 #标签。返回去重后的标签列表。"""
    tags = re.findall(r"#([\w\u4e00-\u9fff]+)", text)
    return list(set(tags))


def strip_md(text):
    """移除 Markdown 标记，返回纯文本。"""
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip()


def truncate(text, max_len=200):
    """截断文本到指定长度，末尾加..."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def file_size(path):
    """获取文件大小（字节）。"""
    return os.path.getsize(path) if os.path.exists(path) else 0


def list_md_files(directory):
    """列出目录下所有 .md 文件，按修改时间排序。"""
    if not os.path.exists(directory):
        return []
    files = [f for f in os.listdir(directory) if f.endswith(".md")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
    return files
