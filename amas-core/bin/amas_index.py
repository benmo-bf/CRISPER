#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""amas_index.py — AMaS 倒排索引（v3：IDF 排序 + 2-gram 回退）

v2 → v3（2026-10-25）：
  1. 存 df（词出现在多少文件），查询用 tf·idf 排序，抑制大文件偏置
     ——原按 tf 排序时「端粒」被 server_bioinfo_resources.md 压住。
  2. 中文 2-gram 回退：「OOM内存」这种无分隔查询，整体查不到就拆成
     OOM / OO / OM / 内存 / 存… 的 bigram，按匹配覆盖度排序。
  3. 自动停用：df > 40% 文件的词（benmo / pi / memory 这类）索引里保存但降权。
  4. 索引体积：df 单独存，文件列表只存 tf。

只读：永不改动任何 .md。

用法:
  amas_index.py build               # 重建 memory/.amas_index_map.json
  amas_index.py query 污染 OOM
  amas_index.py stats
  amas_index.py coverage            # 日记 vs index.md 收录差
"""
import json
import math
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

MAX_TERMS_PER_FILE = 60
RARE_DF = 5
MAX_FILE_BYTES = 2_000_000
GENERIC_DF_RATIO = 0.40      # 出现在 40% 以上文件的词视为泛词
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
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
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
    inv, df_out, pairs = {}, {}, 0
    for fn, b in bags.items():
        top = sorted(b.items(), key=lambda x: -x[1])[:MAX_TERMS_PER_FILE]
        keep = {t for t, _ in top} | {t for t in b if df[t] <= RARE_DF}
        for t in keep:
            inv.setdefault(t, []).append([fn, b[t]])
            pairs += 1
    for t in inv:
        inv[t].sort(key=lambda x: (-x[1], x[0]))
        df_out[t] = len(inv[t])
    data = {"built_from": MEM, "files": len(files), "n_files": len(files),
            "terms": len(inv), "pairs": pairs, "df": df_out, "index": inv}
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


def _idf(d, term):
    n = d.get("n_files") or d.get("files") or 1
    f = d.get("df", {}).get(term, 1)
    w = math.log(1.0 + n / max(f, 1))
    # 泛词降权（benmo / pi / memory 这类）
    if f > GENERIC_DF_RATIO * n:
        w *= 0.15
    return w


def _grams(word):
    """中文 2-gram；拉丁词整体保留。"""
    if re.fullmatch(r"[A-Za-z0-9_.+-]+", word):
        return [word.lower()]
    out = []
    for seg in CJK.findall(word):
        if len(seg) == 2:
            out.append(seg)
        else:
            out.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    lat = LAT.findall(word)
    out.extend(w.lower() for w in lat)
    return out


def query(words, limit=12):
    d = load()
    idx = d["index"]
    scores = defaultdict(float)
    covered = defaultdict(int)
    for w in words:
        keys = [k for k in (w, w.lower()) if k in idx]
        if not keys:
            keys = [k for k in _grams(w) if k in idx]
        if not keys:
            # 末路回退：包含匹配（contam_chain → contam_chain.sh）
            low = w.lower()
            keys = [t for t in idx if len(t) > len(low) and low in t.lower()][:20]
        if not keys:
            continue
        for k in keys:
            idf = _idf(d, k)
            for fn, tf in idx.get(k, []):
                scores[fn] += tf * idf
                covered[fn] += 1
        # AND 倾向：命中该词拆分项越多，加权越高
    if not scores:
        print("(no hit)")
        return
    need = max(1, len(_grams("".join(words))) // 2)
    rows = sorted(scores.items(), key=lambda x: -(x[1] * (1 + 0.5 * min(covered[x[0]], 3))))
    shown = 0
    for fn, sc in rows:
        if covered[fn] < min(need, 2) and len(rows) > 5:
            continue
        print("%8.2f  memory/%s" % (sc, fn))
        shown += 1
        if shown >= limit:
            break
    if shown == 0:
        for fn, sc in rows[:limit]:
            print("%8.2f  memory/%s" % (sc, fn))


def stats():
    d = load()
    print("files=%d terms=%d pairs=%d  built_from=%s"
          % (d["files"], d["terms"], d["pairs"], d["built_from"]))
    top = sorted(d["index"].items(), key=lambda kv: -len(kv[1]))[:10]
    for t, v in top:
        print("  %-14s %d files" % (t, len(v)))


def coverage():
    idx_path = os.path.join(MEM, "index.md")
    idx = ""
    if os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8", errors="ignore") as f:
            idx = f.read()
    diaries = [fn for fn in list_md() if DATE.match(fn)]
    missing = [fn for fn in diaries if fn[:10] not in idx and fn not in idx]
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
