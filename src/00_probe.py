# -*- coding: utf-8 -*-
"""探针 2：三件事必须在动手采集前确认
   1 Ashby 到底给不给 JD 正文和薪资
   2 Greenhouse 的薪资是不是只写在正文里
   3 一家公司平均有几个 marketing 岗（决定需要多少家公司）
"""
import json, re, sys, html, urllib.request, urllib.error, time
sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (research; job-posting field survey)"}

def get(url, timeout=25):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"__err": str(e)[:70]}

print("=== 1. Ashby 列表接口的完整字段（ramp 第一条）===")
d = get("https://api.ashbyhq.com/posting-api/job-board/ramp?includeCompensation=true")
jobs = d.get("jobs", [])
if jobs:
    print("  keys:", list(jobs[0].keys()))
    for k in ("descriptionHtml", "descriptionPlain", "compensation", "jobUrl", "applyUrl"):
        v = jobs[0].get(k)
        print(f"  {k:<18}", (json.dumps(v, ensure_ascii=False)[:150] if v is not None else "缺失"))

print("\n=== 2. Greenhouse 正文里有没有薪资 ===")
g = get("https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true")
gj = g.get("jobs", [])
pay = re.compile(r"\$\s?\d{2,3},\d{3}|\$\s?\d{2,3}K", re.I)
hit = sum(1 for j in gj if pay.search(html.unescape(j.get("content") or "")))
print(f"  figma {len(gj)} 条岗位中，正文出现美元薪资区间的: {hit} 条 ({hit/max(len(gj),1)*100:.0f}%)")
for j in gj:
    t = html.unescape(j.get("content") or "")
    m = pay.search(t)
    if m:
        s = re.sub(r"<[^>]+>", " ", t[max(0, m.start()-170):m.start()+170])
        print("  例:", re.sub(r"\s+", " ", s).strip()[:300]); break

print("\n=== 3. 每家公司有几个 marketing 岗 ===")
MK = re.compile(r"market|brand|growth|content|communicat|social media|demand gen|seo|crm|lifecycle", re.I)
def count(name, titles):
    m = [t for t in titles if MK.search(t)]
    print(f"  {name:<14} 总 {len(titles):>4}  marketing 相关 {len(m):>3}  ({len(m)/max(len(titles),1)*100:>4.1f}%)")
    return len(m)
tot = 0
for c in ("figma", "databricks", "robinhood", "duolingo"):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs"); time.sleep(.4)
    tot += count(c, [j["title"] for j in d.get("jobs", [])])
for c in ("ramp", "notion", "vanta", "openai"):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{c}"); time.sleep(.4)
    tot += count(c, [j["title"] for j in d.get("jobs", [])])
print(f"\n  8 家公司合计 marketing 岗: {tot} 条  -> 平均每家 {tot/8:.1f} 条")
print(f"  要凑到 2000 条，需要约 {int(2000/(tot/8))} 家公司")
