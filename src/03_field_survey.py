# -*- coding: utf-8 -*-
"""阶段 1 · 字段普查：每个字段的填充率和样例。
不凭印象列字段，用实际数据数出来。
"""
import gzip, json, os, sys, collections, re
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")


def load(ats):
    with gzip.open(os.path.join(RAW, f"{ats}.json.gz"), "rt", encoding="utf-8") as f:
        store = json.load(f)
    rows = []
    for company, payload in store.items():
        if not payload:
            continue
        jobs = payload.get("jobs") if isinstance(payload, dict) else payload
        for j in (jobs or []):
            rows.append((company, j))
    return rows


def brief(v, n=72):
    s = json.dumps(v, ensure_ascii=False)
    s = re.sub(r"\s+", " ", s)
    return (s[:n] + "…") if len(s) > n else s


for ats in ("ashby", "greenhouse", "lever"):
    rows = load(ats)
    print(f"\n{'='*78}\n{ats}  共 {len(rows):,} 条\n{'='*78}")
    fill = collections.Counter()
    samples = {}
    for _, j in rows:
        for k, v in j.items():
            filled = v not in (None, "", [], {})
            if filled:
                fill[k] += 1
                if k not in samples:
                    samples[k] = v
            else:
                fill.setdefault(k, 0)
    for k in sorted(fill, key=lambda x: -fill[x]):
        pct = fill[k] / len(rows) * 100
        print(f"  {k:<36}{pct:>6.1f}%  {brief(samples.get(k, ''))}")
