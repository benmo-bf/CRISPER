#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARMS 命令行入口 — agent-memory
著作权人：曹修达 v1.0

用法:
  agent-memory init             初始化记忆目录
  agent-memory diary            查看/追加今日日记
  agent-memory diary --date D   查看指定日期日记
  agent-memory diary --append   追加内容到今日日记
  agent-memory consolidate      手动执行记忆巩固
  agent-memory seed --load      加载种子记忆网
  agent-memory seed --status    检查种子加载状态
  agent-memory search <关键词>   搜索记忆
  agent-memory tags             列出所有标签
  agent-memory index --rebuild  重建索引
  agent-memory reflex list      列出快系统规则
  agent-memory version          版本信息
"""

import sys
import os

# 确保从包内导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_memory import MemoryStore, ConsolidationEngine, IndexNetwork
from agent_memory import ReflexEngine, SeedLoader, Config
from agent_memory import __version__ as VERSION


def cmd_init(args):
    """初始化记忆系统。"""
    cfg = Config()
    store = MemoryStore(cfg)
    store.init_storage()
    print(f"✅ 记忆系统初始化完成")
    print(f"   工作区: {os.getcwd()}")
    print(f"   记忆目录: {cfg.memory_path}")
    print(f"   长期记忆: {cfg.longterm_path}")
    print(f"   索引: {cfg.index_path}")
    print(f"\n运行 'agent-memory seed --load' 加载种子记忆网")
    return 0


def cmd_diary(args):
    """日记操作。"""
    cfg = Config()
    store = MemoryStore(cfg)
    date = args.date

    if args.append:
        content = sys.stdin.read() if not sys.stdin.isatty() else input("日记内容: ")
        store.append_diary(date, f"\n- {content}")
        print(f"✅ 已追加到 {date} 日记")
    elif args.edit:
        content = sys.stdin.read()
        store.create_diary(date, content)
        print(f"✅ 已更新 {date} 日记")
    else:
        content = store.get_diary(date)
        if content.strip():
            print(f"\n📖 {date} 日记\n{'='*40}")
            print(content)
        else:
            print(f"📭 {date} 日记为空或不存在")
            print(f"   使用 --append 追加内容")
    return 0


def cmd_consolidate(args):
    """执行记忆巩固。"""
    engine = ConsolidationEngine()
    days = args.days or 1
    print(f"🔄 开始记忆巩固（扫描最近 {days} 天日记）...")
    stats = engine.nightly_consolidate(days)
    print(engine.generate_report(stats))
    return 0


def cmd_seed(args):
    """种子记忆网操作。"""
    loader = SeedLoader()
    if args.load:
        files = loader.load_seed()
        print(f"✅ 种子记忆网已加载 ({len(files)} 个文件)")
        for f in files:
            print(f"   📄 {os.path.relpath(f)}")
    elif args.status:
        status = loader.seed_status()
        print("📊 种子加载状态:")
        for name, exists in status.items():
            icon = "✅" if exists else "⬜"
            print(f"   {icon} {name}")
    return 0


def cmd_search(args):
    """搜索记忆。"""
    query = " ".join(args.query)
    if not query:
        print("❌ 请提供搜索关键词")
        return 1

    # 搜索索引
    index = IndexNetwork()
    results = index.search(query)
    if results:
        print(f"🔍 找到 {len(results)} 条结果（关键词: {query}）\n")
        for r in results[:10]:
            print(f"  #{r.tag}")
            print(f"    📄 {r.filepath}")
            print(f"    💬 {r.context}")
            print()
    else:
        # 回退：搜索日记
        store = MemoryStore()
        diary_results = store.search_diaries(query)
        if diary_results:
            print(f"📖 在日记中找到 {len(diary_results)} 条匹配:\n")
            for date, snippet in diary_results[:5]:
                print(f"  [{date}] ...{snippet}...")
                print()
        else:
            print(f"❌ 未找到与「{query}」相关的记忆")
    return 0


def cmd_tags(args):
    """列出标签。"""
    index = IndexNetwork()
    tags = index.list_tags()
    if tags:
        print(f"🏷️  共 {len(tags)} 个标签:\n")
        for tag, count in tags[:30]:
            bar = "#" * min(count, 20)
            print(f"  #{tag:20s} {bar} ({count})")
    else:
        print("📭 暂无标签")
    return 0


def cmd_index(args):
    """索引操作。"""
    cfg = Config()
    index = IndexNetwork(cfg)
    if args.rebuild:
        print("🔄 重建索引中...")
        index.rebuild_from_memory()
        print("✅ 索引重建完成")
    return 0


def cmd_reflex(args):
    """反射引擎操作。"""
    if "list" in args.command:
        engine = ReflexEngine()
        engine.load_rules()
        print(engine.export_as_markdown())
    return 0


def cmd_version(args):
    """版本信息。"""
    print(f"Agent 递归记忆管理系统 (ARMS)")
    print(f"版本: {VERSION}")
    print(f"作者: 曹修达")
    print(f"许可证: 专有软件")
    return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Agent 递归记忆管理系统 — ARMS v" + VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  agent-memory init
  agent-memory diary
  agent-memory diary --date 2026-05-31
  agent-memory diary --append <<< "今天完成了什么"
  agent-memory consolidate --days 3
  agent-memory seed --load
  agent-memory search "服务器"
  agent-memory tags
  agent-memory index --rebuild"""
    )
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="初始化记忆目录")

    # diary
    p_diary = sub.add_parser("diary", help="日记操作")
    p_diary.add_argument("--date", default="", help="日期 (YYYY-MM-DD), 默认今天")
    p_diary.add_argument("--append", action="store_true", help="追加内容（从 stdin 或交互输入）")
    p_diary.add_argument("--edit", action="store_true", help="覆盖编辑")

    # consolidate
    p_con = sub.add_parser("consolidate", help="执行记忆巩固")
    p_con.add_argument("--days", type=int, default=1, help="扫描最近 N 天日记")

    # seed
    p_seed = sub.add_parser("seed", help="种子记忆网操作")
    p_seed.add_argument("--load", action="store_true", help="加载种子记忆网")
    p_seed.add_argument("--status", action="store_true", help="检查种子加载状态")

    # search
    p_search = sub.add_parser("search", help="搜索记忆")
    p_search.add_argument("query", nargs="+", help="搜索关键词")

    # tags
    sub.add_parser("tags", help="列出所有标签")

    # index
    p_idx = sub.add_parser("index", help="索引操作")
    p_idx.add_argument("--rebuild", action="store_true", help="重建索引")

    # reflex
    p_ref = sub.add_parser("reflex", help="快系统规则")
    p_ref.add_argument("command", nargs="?", default="list", choices=["list"])

    args = parser.parse_args()

    if args.version:
        return cmd_version(args)

    cmds = {
        "init": cmd_init,
        "diary": cmd_diary,
        "consolidate": cmd_consolidate,
        "seed": cmd_seed,
        "search": cmd_search,
        "tags": cmd_tags,
        "index": cmd_index,
        "reflex": cmd_reflex,
    }

    if args.command in cmds:
        return cmds[args.command](args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
