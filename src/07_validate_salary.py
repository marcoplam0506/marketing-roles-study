# -*- coding: utf-8 -*-
"""阶段 6 · 薪资抽取的验证链。三件事：
   1 Lever 结构化字段为空的岗位，薪资是不是写在正文里
   2 Ashby 没有字段薪资的岗位同理
   3 Greenhouse 正则抽出来的数到底对不对 —— 抽样把原文和抽取结果并排看
"""
import os, re, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT, "data", "interim", "01_nyc_all.csv.gz"))

PAY = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+|\$\s?\d{2,3}(?:\.\d)?\s?[Kk]\b")

print("=== 1+2 · 字段没薪资的岗位，正文里有没有 ===")
for ats in ("lever", "ashby", "greenhouse"):
    sub = df[(df.ats == ats) & df.sal_min.isna()]
    if not len(sub):
        continue
    hit = sub.jd_text.fillna("").str.contains(PAY).sum()
    print(f"  {ats:<11}字段无薪资 {len(sub):>4} 条，其中正文出现美元金额 {hit:>4} 条 ({hit/len(sub)*100:.0f}%)")

print("\n  Lever 正文里的薪资写法样例:")
lv = df[(df.ats == "lever") & df.jd_text.fillna("").str.contains(PAY)]
for t in lv.jd_text.head(3):
    m = PAY.search(t)
    print("   ", re.sub(r"\s+", " ", t[max(0, m.start()-130):m.start()+110]).strip()[:230])

print("\n=== 3 · Greenhouse 正则抽取抽样核对（抽 10 条）===")
gh = df[(df.ats == "greenhouse") & df.sal_min.notna()].sample(10, random_state=7)
bad = 0
for _, r in gh.iterrows():
    t = r.jd_text
    # 找出原文里离"salary/compensation"最近的那个金额区间，和抽取结果比
    ctx = ""
    for m in re.finditer(r"\$[\d,.]+\s?[Kk]?\s*(?:-|–|—|to)\s*\$[\d,.]+\s?[Kk]?", t):
        w = t[max(0, m.start()-120):m.end()+40]
        if re.search(r"salary|compensation|pay range|base", w, re.I):
            ctx = re.sub(r"\s+", " ", w).strip(); break
    if not ctx:
        m = re.search(r"\$[\d,.]+\s?[Kk]?\s*(?:-|–|—|to)\s*\$[\d,.]+\s?[Kk]?", t)
        ctx = re.sub(r"\s+", " ", t[max(0, m.start()-120):m.end()+40]).strip() if m else "(正文没找到区间)"
    print(f"\n  {r.title[:56]}")
    print(f"    抽取: {r.sal_min:,.0f} - {r.sal_max:,.0f} / {r.sal_unit}")
    print(f"    原文: …{ctx[:200]}…")

print("\n=== 4 · 数值合理性 ===")
y = df[(df.sal_unit == "year") & df.sal_min.notna()]
h = df[(df.sal_unit == "hour") & df.sal_min.notna()]
print(f"  年薪 {len(y):,} 条   min 中位 ${y.sal_min.median():,.0f}   max 中位 ${y.sal_max.median():,.0f}")
print(f"       min 最低 ${y.sal_min.min():,.0f}   max 最高 ${y.sal_max.max():,.0f}")
print(f"  时薪 {len(h):,} 条   min 中位 ${h.sal_min.median():,.1f}   max 中位 ${h.sal_max.median():,.1f}")
odd = y[(y.sal_min < 30000) | (y.sal_max > 800000) | (y.sal_max < y.sal_min)]
print(f"\n  可疑年薪（<3万 或 >80万 或 上下限反了）: {len(odd)} 条")
for _, r in odd.head(6).iterrows():
    print(f"    {r.sal_min:>10,.0f} - {r.sal_max:>10,.0f}  {r.ats:<11}{r.title[:46]}")
