#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""amas_index.py — AMaS 倒排索引构建器（只读，永不改动任何 .md）

背景
----
AMaS Core v1 的 IndexNetwork.rebuild_from_memory() 会重写 memory/index.md，
而现网 index.md 是富格式（时间/关键词/阶段/情境/情绪/文件/引申，167 节点/422KB）。
v1 的写入器只认四字段单行格式，直接跑等于毁库；它的标签提取还会把
「规则 0-16」「卦 62」的序号当标签（实测 49 个标签大半是纯数字）。

本工具因此只做**只读**的倒排表，不改任何记忆文件：
  memory/.amas_index_map.json   {词 -> [[文件, 权重], ...]}

检索路径：词 → 文件列表（毫秒级）→ 再打开命中文件。替代全目录 grep。

用法
----
  amas_index.py build                 # 重建倒排表
  amas_index.py query 污染 筛查        # AND 优先，退化 OR
  amas_index.py stats                 # 概况 + 高频词
  amas_index.py coverage              # 日记 与 index.md 节点覆盖差
"""
import json
import os
import re
import sys
from collections import defaultdict

MEM = os.environ.get("AMAS_MEMORY_DIR", "/database/ai/crisper/memory")
OUT = os.environ.get("AMAS_INDEX_MAP", os.path.join(MEM, ".amas_index_map.json"))
SKIP = {"index.md", "keywords.md"}
CJK = re.compile(r"[\u4e00-\u9fff]{2,}")
LAT = re.compile(r"[A-Za-z][A-Za-z0-9_.+-]{1,}")
HEAD = re.compile(r"^#{1,6}\s+(.+)$")
BOLD = re.compile(r"\*\*([^*]{2,40})\*\*")
QUOTE = re.compile(r"[「『]([^」』]{2,40})[」』]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")

MAX_TERMS_PER_FILE = 60   # 高频词上限
RARE_DF = 5               # 全局出现 <= 5 个文件的词不设上限（保住 contam_chain 这类专名）
MAX_FILE_BYTES = 2_000_000
STOP = {"关键词", "标签", "节点", "文件", "引申", "情境", "情绪", "阶段", "时间", "完成"}


def list_md():
    out = []
    for fn in sorted(os.listdir(MEM)):
        if not fn.endswith(".md") or fn in SKIP:
            continue
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            if os.path.getsize(p) > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        out.append(fn)
    return out


def bag_of(path):
    """返回 {词: 权重}。标题/加粗/引号/标签行加权 3，正文计 1。"""
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return {}
    hot = []
    for line in text.split("\n"):
        s = line.strip()
        m = HEAD.match(s)
        if m:
            hot.append(m.group(1))
        for m in BOLD.finditer(line):
            hot.append(m.group(1))
        for m in QUOTE.finditer(line):
            hot.append(m.group(1))
        if "关键词" in line or "标签" in line:
            hot.append(line)
    bag = defaultdict(int)
    for chunk in hot:
        for w in CJK.findall(chunk):
            bag[w] += 3
        for w in LAT.findall(chunk):
            bag[w.lower()] += 3
    for w in CJK.findall(text):
        bag[w] += 1
    for w in LAT.findall(text):
        bag[w.lower()] += 1
    for s in STOP:
        bag.pop(s, None)
    bag.pop("todo", None)
    return bag


def build():
    files = list_md()
    bags = {fn: bag_of(os.path.join(MEM, fn)) for fn in files}
    df = defaultdict(int)
    for b in bags.values():
        for t in b:
            df[t] += 1
    inv = defaultdict(list)
    pairs = 0
    for fn, b in bags.items():
        top = sorted(b.items(), key=lambda x: -x[1])[:MAX_TERMS_PER_FILE]
        keep = {t for t, _ in top} | {t for t in b if df[t] <= RARE_DF}
        for t in keep:
            inv[t].append([fn, b[t]])
            pairs += 1
    for t in inv:
        inv[t].sort(key=lambda x: (-x[1], x[0]))
    data = {"built_from": MEM, "files": len(files), "terms": len(inv),
            "pairs": pairs, "index": inv}
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    print("built %s: files=%d terms=%d pairs=%d size=%dKB"
          % (OUT, len(files), len(inv), pairs, os.path.getsize(OUT) // 1024))


def load():
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)


def query(words, limit=12):
    idx = load()["index"]
    hit = {}
    for w in words:
        for key in (w, w.lower()):
            for fn, n in idx.get(key, []):
                hit[fn] = hit.get(fn, 0) + n
    if not hit and len(words) > 1:
        for w in words:
            for key in (w, w.lower()):
                for fn, n in idx.get(key, []):
                    hit[fn] = hit.get(fn, 0) + n
    if not hit:
        print("(no hit)")
        return
    for fn, n in sorted(hit.items(), key=lambda x: -x[1])[:limit]:
        print("%6d  memory/%s" % (n, fn))


def stats():
    d = load()
    print("files=%d terms=%d pairs=%d  built_from=%s"
          % (d["files"], d["terms"], d["pairs"], d["built_from"]))
    for t, v in sorted(d["index"].items(), key=lambda kv: -len(kv[1]))[:10]:
        print("  %-14s %d files" % (t, len(v)))


def coverage():
    """对比日记日期 与 index.md 里出现过的日期/文件名。"""
    idx_path = os.path.join(MEM, "index.md")
    idx = open(idx_path, encoding="utf-8", errors="ignore").read() if os.path.exists(idx_path) else ""
    diaries = [fn for fn in list_md() if DATE.match(fn)]
    missing = [fn for fn in diaries
               if fn[:10] not in idx and fn not in idx]
    print("日记 %d 篇；index.md 未收录 %d 篇" % (len(diaries), len(missing)))
    for fn in missing:
        print("  -", fn)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "build":
        build()
    elif cmd == "query":
        query(sys.argv[2:])
    elif cmd == "coverage":
        coverage()
    else:
        stats()
