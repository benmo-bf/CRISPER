"""CRMS 基础功能测试"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_memory import MemoryStore, ConsolidationEngine, IndexNetwork
from agent_memory import ReflexEngine, SeedLoader, Config
from agent_memory.utils import parse_tags, ensure_dir, write_md, read_md


class TestUtils:
    def test_parse_tags(self):
        tags = parse_tags("今天完成了 #项目 和 #开发")
        assert "项目" in tags
        assert "开发" in tags
        print("  ✅ parse_tags")

    def test_ensure_dir(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a", "b", "c")
            ensure_dir(path)
            assert os.path.exists(path)
            print("  ✅ ensure_dir")


class TestMemoryStore:
    def test_init_and_diary(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(d)
            store = MemoryStore(cfg)
            store.init_storage()
            assert os.path.exists(cfg.memory_path)
            store.create_diary("2099-01-01", "# 测试日记")
            content = store.get_diary("2099-01-01")
            assert "测试日记" in content
            print("  ✅ MemoryStore init + diary")

    def test_longterm(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(d)
            store = MemoryStore(cfg)
            store.init_storage()
            events = [{"date": "2099-01-01", "summary": "测试事件", "tags": ["test"]}]
            store.update_longterm(events)
            content = store.read_longterm()
            assert "测试事件" in content
            print("  ✅ MemoryStore longterm")


class TestIndexNetwork:
    def test_search(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(d)
            store = MemoryStore(cfg)
            store.init_storage()
            idx = IndexNetwork(cfg)
            idx.add_tag("测试", "/tmp/test.md", "这是一个测试标签")
            results = idx.search("测试")
            assert len(results) > 0
            assert results[0].tag == "测试"
            print("  ✅ IndexNetwork search")


class TestConsolidation:
    def test_extract_events(self):
        engine = ConsolidationEngine()
        text = "# 今天做了什么\n\n完成了 #项目A 的开发工作！\n\n## 教训\n下次要注意备份"
        events = engine.extract_key_events(text, "2099-01-01")
        assert len(events) > 0
        # Should have at least the section with "完成了"
        found = any("项目A" in e.summary for e in events)
        assert found
        print("  ✅ ConsolidationEngine extract_events")


class TestReflexEngine:
    def test_match(self):
        engine = ReflexEngine()
        engine.load_rules()
        rule = engine.match("连服务器看看情况")
        assert rule is not None
        assert "SSH" in rule.action or "服务器" in rule.action
        print("  ✅ ReflexEngine match")


if __name__ == "__main__":
    print("\n🔍 CRMS 基础功能测试\n")
    TestUtils().test_parse_tags()
    TestUtils().test_ensure_dir()
    TestMemoryStore().test_init_and_diary()
    TestMemoryStore().test_longterm()
    TestIndexNetwork().test_search()
    TestConsolidation().test_extract_events()
    TestReflexEngine().test_match()
    print("\n✅ 全部测试通过\n")
