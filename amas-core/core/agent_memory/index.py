# -*- coding: utf-8 -*-
"""
ARMS 索引网络模块 — IndexNetwork
著作权人：曹修达 v1.0

标签 → 文件 → 事件的三层双向索引结构。
支持关键词搜索、标签关联和索引重建。
"""

import os
import re
import shutil
import time
from collections import defaultdict

from .config import Config
from .utils import read_md, write_md, ensure_dir, parse_tags, strip_md, today_str

# ── 2026-10-25 修复（Crisper）──────────────────────────────────────────────
# 1) 数值型/无意义标签过滤：v1 把「规则 0-16」「卦 62」里的序号当成标签，
#    实测 49 个标签里大半是纯数字。
# 2) 覆盖保护：v1 的 _save() 无条件重写 index.md，会把富格式索引（时间/关键词/
#    阶段/情境/情绪/文件/引申 七字段节点）整篇抹成四字段单行。现网 index.md
#    422KB / 167 节点，直接 rebuild 等于毁库。
#    现在：检测到「富格式」时拒绝覆盖，改写到 index.md.rebuilt 并打印提示；
#    需要覆盖必须显式 force=True。
# 3) rebuild 只吃日记（YYYY-MM-DD.md）与主题文件，跳过 .dreams / index.md /
#    关键字索引，并给单文件加大小上限。
TAG_STOPWORDS = {
    "关键词", "标签", "节点", "文件", "引申", "情境", "情绪", "阶段", "时间",
    "完成", "todo", "TODO", "memory", "index", "MEMORY", "index.md",
}
MAX_REBUILD_BYTES = 2_000_000
RICH_MARKERS = ("**节点", "·关键词→", "·情境→", "·引申→")
# 文件名/纯标点也会被当标签，一并排除
TAG_STOPWORDS |= {
    "MEMORY.md", "learnings.md", "projects.md", "todos.md", "workflows.md",
    "infra.md", "identity.md", "keywords.md", "skills.md", "ops-reference.md",
}
TAG_MEANINGFUL = re.compile(r"[\u4e00-\u9fff]{2}|[A-Za-z]{3,}")


def normalize_tag(tag):
    """规整标签：去首尾空白与 # 号；纯数字、过短、停用词一律视为无效。"""
    t = (tag or "").strip().strip('"\'“”‘’—…·').lstrip("#").strip()
    if len(t) < 2:
        return ""
    if t.isdigit():
        return ""
    if t.lower() in {s.lower() for s in TAG_STOPWORDS}:
        return ""
    if not TAG_MEANINGFUL.search(t):          # 纯标点/符号
        return ""
    return t


def is_rich_index(content):
    """判断 index.md 是否为富格式（会被 v1 _save() 破坏）。"""
    if len(content) > 20000:
        return True
    return any(m in content for m in RICH_MARKERS)


class IndexNode:
    """索引节点：一个标签关联的文件和摘要信息。"""

    def __init__(self, tag, filepath="", context="", date=""):
        self.tag = tag
        self.filepath = filepath
        self.context = context
        self.date = date or today_str()

    def to_line(self):
        return f"- **#{self.tag}** — [{os.path.basename(self.filepath)}]({self.filepath}) — {self.context} _({self.date})_"

    @classmethod
    def from_line(cls, line):
        """从 Markdown 行解析 IndexNode。"""
        m = re.match(r'-\s+\*\*#(.+?)\*\*\s*—\s*\[(.+?)\]\((.+?)\)\s*—\s*(.+?)\s*_\((.+?)\)_', line)
        if m:
            return cls(tag=m.group(1), filepath=m.group(3), context=m.group(4), date=m.group(5))
        # 宽松匹配
        m2 = re.match(r'-\s+\*\*#(.+?)\*\*', line)
        if m2:
            return cls(tag=m2.group(1))
        return None


class IndexNetwork:
    """标签索引网络，维护标签到记忆节点的关联。"""

    def __init__(self, config=None):
        self.config = config or Config()
        self._nodes = []  # 缓存
        self._loaded = False

    # ── 加载与持久化 ──

    def _load(self):
        """从 index.md 加载所有节点到缓存。"""
        self._nodes = []
        content = read_md(self.config.index_path)
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(">"):
                continue
            node = IndexNode.from_line(line)
            if node:
                self._nodes.append(node)
        self._loaded = True

    def _save(self, force=False):
        """将缓存写回 index.md。

        2026-10-25 修复：默认**不覆盖富格式索引**。
        目标文件若判定为富格式（>20KB 或含七字段节点标记），改写
        <index>.rebuilt 并打印提示；确需覆盖传 force=True。
        """
        target = self.config.index_path
        out = target
        if not force and os.path.exists(target):
            try:
                old = read_md(target)
            except OSError:
                old = ""
            if is_rich_index(old):
                out = target + ".rebuilt"
                if not getattr(self, "_warned_rich", False):
                    print("[AMaS] %s 是富格式索引（%d 字节），拒绝覆盖；"
                          "改写 %s（force=True 才覆盖原文件）"
                          % (target, len(old), os.path.basename(out)))
                    self._warned_rich = True
            elif old.strip():
                bak = "%s.bak-%s" % (target, time.strftime("%Y%m%d_%H%M%S"))
                shutil.copy2(target, bak)
        lines = [
            "# 记忆索引",
            "",
            "> 标签 → 文件 → 事件 双向索引网络",
            f"> 最后更新: {today_str()}",
            "",
            "---",
            "",
        ]
        self._nodes.sort(key=lambda n: n.tag)
        for node in self._nodes:
            lines.append(node.to_line())
        ensure_dir(self.config.memory_path)
        write_md(out, "\n".join(lines) + "\n")
        return out

    # ── 核心操作 ──

    def add_tag(self, tag, filepath, context="", date=""):
        """添加一个标签索引节点。无效标签（纯数字/过短/停用词）返回 None。"""
        tag = normalize_tag(tag)
        if not tag:
            return None
        if not self._loaded:
            self._load()
        # 去重：同标签+同文件不重复添加
        for node in self._nodes:
            if node.tag == tag and node.filepath == filepath:
                node.context = context
                node.date = date or today_str()
                if not getattr(self, "_batch", False):
                    self._save()
                return node
        node = IndexNode(tag=tag, filepath=filepath, context=context, date=date)
        self._nodes.append(node)
        if not getattr(self, "_batch", False):
            self._save()
        return node

    @staticmethod
    def _fallback_tags(text, limit=8):
        """没有 #标签 语法时，从标题与加粗里取候选词（2026-10-25 新增）。

        v1 只认 #tag；实际语料（日记/learnings/index）几乎不用该语法，
        导致 rebuild 出 0 节点。这里退化为「标题 + 加粗 + 引号」短语，
        仍走 normalize_tag 过滤纯数字与停用词。
        """
        def ok(t, maxlen):
            if not t or len(t) > maxlen:
                return False
            if re.search(r"[0-9:：/|→\[\]（）()]", t):
                return False
            if any(ord(ch) > 0x1F000 for ch in t):     # emoji
                return False
            return True

        terms, heads = [], []
        for line in text.split("\n"):
            s = line.strip()
            m = re.match(r"^#{1,6}\s+(.+)$", s)
            if m:
                heads.append(m.group(1).strip())
            for m2 in re.finditer(r"\*\*([^*]{2,16})\*\*", line):
                terms.append(m2.group(1).strip())
            for m3 in re.finditer(r"[「『]([^」』]{2,16})[」』]", line):
                terms.append(m3.group(1).strip())
        out = []
        for c in terms + heads:
            maxlen = 16 if c in terms else 12
            t = normalize_tag(c)
            t = re.sub(r"\s+", " ", t).strip()
            if ok(t, maxlen) and t not in out:
                out.append(t)
            if len(out) >= limit:
                break
        return out

    def add_tags_from_text(self, text, filepath, date=""):
        """从文本中提取标签并添加到索引。"""
        tags = parse_tags(text)
        if not tags:
            tags = self._fallback_tags(text)
        lines = text.split("\n")
        for tag in tags:
            # 提取标签所在行的上下文
            context = ""
            for line in lines:
                if f"#{tag}" in line or tag in line:
                    context = strip_md(line)[:80]
                    break
            self.add_tag(tag, filepath, context, date)

    def search(self, query):
        """搜索索引，返回匹配的 IndexNode 列表。"""
        if not self._loaded:
            self._load()
        query = query.lower()
        results = []
        for node in self._nodes:
            if (query in node.tag.lower()
                    or query in node.context.lower()
                    or query in os.path.basename(node.filepath).lower()):
                results.append(node)
        return results[:self.config.MAX_SEARCH_RESULTS]

    def get_network(self, tag):
        """获取指定标签的关联节点（同文件的其它标签）。"""
        if not self._loaded:
            self._load()
        # 找所有带有该标签的文件
        files_with_tag = set()
        for node in self._nodes:
            if node.tag == tag:
                files_with_tag.add(node.filepath)
        # 找这些文件上的所有标签
        related = defaultdict(list)
        for node in self._nodes:
            if node.filepath in files_with_tag:
                related[node.filepath].append(node)
        return dict(related)

    def list_tags(self):
        """列出所有标签及其使用次数。"""
        if not self._loaded:
            self._load()
        counts = defaultdict(int)
        for node in self._nodes:
            counts[node.tag] += 1
        return sorted(counts.items(), key=lambda x: -x[1])

    def rebuild_from_memory(self, source_dir=None, force=False):
        """从指定目录中的所有 .md 文件重建索引。

        2026-10-25 修复：批量写入（原来每个标签写一次盘）；跳过隐藏目录/
        索引自身/超限文件；日记用文件名里的日期做 node 日期。
        """
        source_dir = source_dir or self.config.memory_path
        if not os.path.exists(source_dir):
            return False
        self._nodes = []
        self._batch = True
        try:
            for fname in sorted(os.listdir(source_dir)):
                if not fname.endswith(".md") or fname in ("index.md", "keywords.md"):
                    continue
                fpath = os.path.join(source_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    if os.path.getsize(fpath) > MAX_REBUILD_BYTES:
                        continue
                except OSError:
                    continue
                m = re.match(r"(\d{4})-(\d{2})-(\d{2})", fname)
                date = "%s-%s-%s" % m.groups() if m else ""
                content = read_md(fpath)
                self.add_tags_from_text(content, fpath, date)
        finally:
            self._batch = False
        out = self._save(force=force)
        print("[AMaS] rebuilt %d nodes -> %s" % (len(self._nodes), out))
        return True
