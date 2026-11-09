# -*- coding: utf-8 -*-
"""阶段 1 · 量一下"只保留纽约"到底砍掉多少样本。
决定要基于真实数字，不是估计。
"""
import gzip, json, os, re, sys, collections
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


def locs(ats, j):
    """把一条岗位的所有地点文本拼起来"""
    if ats == "ashby":
        parts = [j.get("location") or ""]
        parts += [s.get("location") or "" for s in (j.get("secondaryLocations") or [])]
    elif ats == "greenhouse":
        parts = [(j.get("location") or {}).get("name") or ""]
        parts += [o.get("name") or "" for o in (j.get("offices") or [])]
    else:
        c = j.get("categories") or {}
        parts = [c.get("location") or ""]
        parts += list(c.get("allLocations") or [])
    return " ; ".join(p for p in parts if p)


NYC = re.compile(
    r"\bNew York\b|\bNYC\b|\bBrooklyn\b|\bQueens\b|\bBronx\b|\bStaten Island\b"
    r"|\bManhattan\b|\bJersey City\b|\bLong Island City\b|\bFlushing\b", re.I)
# "New York" 也可能是州名里的别的城市，排掉明显不是市区的
NOT_NYC = re.compile(r"\bAlbany\b|\bBuffalo\b|\bRochester\b|\bSyracuse\b|\bYonkers\b"
                     r"|\bIthaca\b|\bWhite Plains\b|\bArmonk\b", re.I)
REMOTE_US = re.compile(r"remote", re.I)
US = re.compile(r"United States|USA|\bUS\b|, ?(?:NY|CA|TX|WA|MA|IL|CO|GA|FL|NC|PA|OR|AZ|VA|UT|MN|TN|MI|OH|NJ|MD|DC)\b", re.I)
MK = re.compile(r"market|brand|growth|content|communicat|social media|demand gen|\bseo\b|\bsem\b"
                r"|\bcrm\b|lifecycle|creative|campaign|paid media|acquisition|pr\b|public relations", re.I)


def title(ats, j):
    return j.get("text") if ats == "lever" else j.get("title") or ""


rows = []
for ats in ("ashby", "greenhouse", "lever"):
    for c, j in load(ats):
        L = locs(ats, j)
        rows.append({
            "ats": ats, "company": c, "title": title(ats, j) or "", "loc": L,
            "nyc": bool(NYC.search(L)) and not NOT_NYC.search(L),
            "remote": bool(REMOTE_US.search(L)),
            "us": bool(US.search(L)),
        })
    # Lever 用自己的 country 字段更准
for r in rows:
    r["mk"] = bool(MK.search(r["title"]))

T = len(rows)
def pr(label, sel):
    n = len(sel); m = sum(1 for r in sel if r["mk"])
    print(f"  {label:<40}{n:>7,}  其中 marketing {m:>5,}")
    return m

print(f"全部岗位 {T:,}\n")
us  = [r for r in rows if r["us"]]
nyc = [r for r in rows if r["nyc"]]
rem = [r for r in rows if r["remote"] and r["us"] and not r["nyc"]]
both= [r for r in rows if r["nyc"] or (r["remote"] and r["us"])]
pr("美国（宽口径）", us)
m_nyc  = pr("严格纽约市 + Jersey City", nyc)
m_rem  = pr("美国远程（不含上面已算的纽约）", rem)
m_both = pr("纽约 或 美国远程", both)

print("\n  纽约样本里的地点样例:")
for r in nyc[:6]:
    print("   ", r["loc"][:88])
print("\n  被 NOT_NYC 排掉的样例:")
for r in rows[:0]:
    pass
drop = [r for r in rows if NYC.search(r["loc"]) and NOT_NYC.search(r["loc"])]
for r in drop[:4]:
    print("   ", r["loc"][:88])
print(f"  （共排掉 {len(drop)} 条）")

print("\n  纽约 marketing 岗按公司分布（前 12）:")
cc = collections.Counter(r["company"] for r in nyc if r["mk"])
for c, n in cc.most_common(12):
    print(f"    {c:<22}{n}")
print(f"  共 {len(cc)} 家公司有纽约 marketing 岗")
