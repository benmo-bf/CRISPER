# -*- coding: utf-8 -*-
"""修复回归测试：覆盖保护 / 标签过滤 / 无 #tag 语料。

跑法（仓库根目录）:
    PYTHONPATH=core python3 tests/test_index_guard.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from agent_memory.index import IndexNetwork, normalize_tag, is_rich_index
from agent_memory.config import Config

RICH = """# 记忆索引

**节点：10-23「污染链」系统事件 · 2026-10-24**
```
  ·时间→ 2026-10-23 全天
  ·关键词→ contam_blast / core_nt / 名实不符
  ·情境→ 三个库路径三种名
  ·情绪→ 名实不符比缺库更难查
  ·引申→ → 待办：DB 真相源统一
```
"""


class TestGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "memory"), exist_ok=True)
        self.cfg = Config(workspace=self.tmp)
        self.net = IndexNetwork(self.cfg)

    def test_rich_index_detected(self):
        self.assertTrue(is_rich_index(RICH))
        self.assertFalse(is_rich_index("# 记忆索引\n- **#a** — [f](f) — x _(2026-01-01)_\n"))

    def test_refuse_overwrite_rich(self):
        with open(self.cfg.index_path, "w", encoding="utf-8") as f:
            f.write(RICH)
        before = open(self.cfg.index_path, encoding="utf-8").read()
        self.net.add_tag("正常标签", "/tmp/x.md", "ctx")
        after = open(self.cfg.index_path, encoding="utf-8").read()
        self.assertEqual(before, after, "富格式 index.md 不得被覆盖")
        self.assertTrue(os.path.exists(self.cfg.index_path + ".rebuilt"), "应写 .rebuilt")

    def test_force_overwrites(self):
        with open(self.cfg.index_path, "w", encoding="utf-8") as f:
            f.write(RICH)
        self.net.add_tag("正常标签", "/tmp/x.md", "ctx")
        out = self.net._save(force=True)
        self.assertEqual(out, self.cfg.index_path)
        self.assertIn("正常标签", open(self.cfg.index_path, encoding="utf-8").read())

    def test_tag_filter(self):
        self.assertEqual(normalize_tag("62"), "")
        self.assertEqual(normalize_tag("#1"), "")
        self.assertEqual(normalize_tag("MEMORY.md"), "")
        self.assertEqual(normalize_tag("——"), "")
        self.assertEqual(normalize_tag("污染筛查"), "污染筛查")
        self.assertEqual(normalize_tag("contam_chain"), "contam_chain")

    def test_fallback_without_hash_tags(self):
        tags = IndexNetwork._fallback_tags("## 污染链归因\n**core_nt 可用**\n「名实不符」")
        self.assertIn("污染链归因", tags)
        self.assertTrue(any("core_nt" in t for t in tags))
        self.assertFalse(any(t.isdigit() for t in tags))

    def test_rebuild_batch(self):
        with open(os.path.join(self.tmp, "memory", "2026-01-01.md"), "w", encoding="utf-8") as f:
            f.write("## 组装 OOM\n**hifiasm 退出 137**\n")
        self.net.rebuild_from_memory()
        self.assertTrue(self.net._nodes)
        # 日记日期应取自文件名
        self.assertTrue(any(n.date == "2026-01-01" for n in self.net._nodes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
