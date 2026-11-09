# -*- coding: utf-8 -*-
"""阶段 1 · 把"字段存在但内容为空"的陷阱量出来。
字段普查只告诉你 key 在不在，不告诉你里面有没有东西。
"""
import gzip, json, os, sys, re, collections
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")


def load(ats):
    with gzip.open(os.path.join(RAW, f"{ats}.json.gz"), "rt", encoding="utf-8") as f:
        store = json.load(f)
    out = []
    for c, p in store.items():
        if not p:
            continue
        for j in (p.get("jobs") if isinstance(p, dict) else p) or []:
            out.append((c, j))
    return out


ash, gh, lev = load("ashby"), load("greenhouse"), load("lever")

print("=== 陷阱 1 · Ashby 的 compensation 字段 100% 存在，但里面有东西吗 ===")
has_sum = sum(1 for _, j in ash if (j.get("compensation") or {}).get("scrapeableCompensationSalarySummary"))
has_tier = sum(1 for _, j in ash if (j.get("compensation") or {}).get("compensationTierSummary"))
flag = sum(1 for _, j in ash if j.get("shouldDisplayCompensationOnJobPostings"))
print(f"  总 {len(ash):,}")
print(f"  scrapeableCompensationSalarySummary 有值: {has_sum:,} ({has_sum/len(ash)*100:.1f}%)")
print(f"  compensationTierSummary 有值:            {has_tier:,} ({has_tier/len(ash)*100:.1f}%)")
print(f"  shouldDisplayCompensationOnJobPostings=true: {flag:,} ({flag/len(ash)*100:.1f}%)")
for _, j in ash:
    s = (j.get("compensation") or {}).get("scrapeableCompensationSalarySummary")
    if s:
        print("  样例:", s, "|", j.get("title")); break

print("\n=== 陷阱 2 · Lever 的正文被拆在好几个字段里 ===")
parts = ["descriptionPlain", "openingPlain", "descriptionBodyPlain", "additionalPlain"]
L = len(lev)
for p in parts:
    n = sum(1 for _, j in lev if (j.get(p) or "").strip())
    avg = sum(len(j.get(p) or "") for _, j in lev) / L
    print(f"  {p:<24}有值 {n/L*100:>5.1f}%   平均长度 {avg:>6.0f} 字符")
nlists = sum(1 for _, j in lev if j.get("lists"))
avgl = sum(sum(len(x.get("content", "")) for x in (j.get("lists") or [])) for _, j in lev) / L
print(f"  {'lists(要求清单)':<22}有值 {nlists/L*100:>5.1f}%   平均长度 {avgl:>6.0f} 字符")
j = [j for _, j in lev if j.get("lists")][0]
print("  lists 的小标题举例:", [x.get("text") for x in j["lists"]][:5])

print("\n=== 陷阱 3 · 薪资单位不统一 ===")
iv = collections.Counter((j.get("salaryRange") or {}).get("interval") for _, j in lev if j.get("salaryRange"))
print("  Lever salaryRange.interval:", dict(iv))
pat = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+|\$\s?\d{2,3}(?:\.\d)?K", re.I)
hr = re.compile(r"\$\s?\d{1,3}(?:\.\d{1,2})?\s*(?:/|per\s+)h(?:ou)?r", re.I)
import html as H
ghtxt = [H.unescape(H.unescape(j.get("content") or "")) for _, j in gh]
n_pay = sum(1 for t in ghtxt if pat.search(t))
n_hr = sum(1 for t in ghtxt if hr.search(t))
print(f"  Greenhouse 正文含美元区间: {n_pay:,}/{len(gh):,} ({n_pay/len(gh)*100:.1f}%)")
print(f"  Greenhouse 正文含时薪写法: {n_hr:,} ({n_hr/len(gh)*100:.1f}%)")

print("\n=== 陷阱 4 · 能不能判断岗位在不在美国 ===")
c_lev = collections.Counter(j.get("country") for _, j in lev)
print("  Lever country 前五:", c_lev.most_common(5))
ash_cty = collections.Counter(((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "(空)" for _, j in ash)
print("  Ashby addressCountry 前五:", ash_cty.most_common(5))
us = re.compile(r"United States|USA|, ?(?:NY|CA|TX|WA|MA|IL|CO|GA|FL|NC|PA|OR|AZ|VA|UT)\b|New York|San Francisco|Remote - US", re.I)
n_us = sum(1 for _, j in gh if us.search((j.get("location") or {}).get("name") or ""))
print(f"  Greenhouse location 文本能判为美国: {n_us:,}/{len(gh):,} ({n_us/len(gh)*100:.1f}%)")
print("  Greenhouse location 样例:", [((j.get('location') or {}).get('name') or '')[:60] for _, j in gh[:4]])
