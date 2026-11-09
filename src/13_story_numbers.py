# -*- coding: utf-8 -*-
"""阶段 8 · 把故事线要用的数字一次算齐，供报告和网页取用。

11 号脚本回答的是问题清单；这里回答的是"怎么讲"。
核心是把辛普森悖论的两半分别量出来：
  同一职能内部，要求数据的贵多少
  跨职能之间，薪资和数据要求的关系是什么方向
两者方向相反、量级相当，合起来才解释了为什么总体看是零。

输入  data/interim/03_labeled.csv.gz
输出  data/processed/story.json + stdout
"""
import io, json, os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(11)

lab = pd.read_csv(os.path.join(ROOT, "data", "interim", "03_labeled.csv.gz"))
w = lab[lab.sal_min.notna() & lab.sal_max.notna()].copy()
w = w[w.sal_cur.isna() | (w.sal_cur == "USD")]
mult = w.sal_unit.map({"year": 1, "hour": 2080, "month": 12}).fillna(1)
w["pay"] = (w.sal_min + w.sal_max) / 2 * mult
w = w[(w.pay >= 40_000) & (w.pay <= 600_000)].copy()
ORDER = ["IC", "Senior", "Leadership"]
S = {}


def boot_diff(a, b, n=4000):
    """两组中位数之差的自助区间。样本小，不靠正态假设。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 4 or len(b) < 4:
        return None
    d = [np.median(rng.choice(a, len(a), True)) - np.median(rng.choice(b, len(b), True))
         for _ in range(n)]
    return float(np.median(a) - np.median(b)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


print("=" * 78)
print("甲 · 职能内部：同一种营销岗里，要求数据的贵多少")
print("=" * 78)
rows = []
for sc, d in w.groupby("subcat"):
    if len(d) < 14:
        continue
    yes, no = d[d.data_hard].pay, d[~d.data_hard].pay
    if len(yes) < 4 or len(no) < 4:
        rows.append(dict(subcat=sc, n=len(d), skip=True,
                         hard_rate=float(d.data_hard.mean() * 100),
                         median=float(d.pay.median())))
        continue
    pct = (yes.median() / no.median() - 1) * 100
    rows.append(dict(subcat=sc, n=len(d), n_yes=int(len(yes)), n_no=int(len(no)),
                     hard_rate=float(d.data_hard.mean() * 100),
                     median=float(d.pay.median()),
                     med_yes=float(yes.median()), med_no=float(no.median()),
                     pct=float(pct), skip=False))
rows.sort(key=lambda r: -r.get("pct", -99))
for r in rows:
    if r["skip"]:
        print(f"  {r['subcat']:<26} n={r['n']:<3} 两边其一不足 4 条，不算内部差"
              f"   （该类要数据 {r['hard_rate']:.0f}%）")
    else:
        print(f"  {r['subcat']:<26} n={r['n']:<3} 要求 ${r['med_yes']:>8,.0f} ({r['n_yes']})"
              f"  不要求 ${r['med_no']:>8,.0f} ({r['n_no']})   {r['pct']:>+6.1f}%")
inner = [r["pct"] for r in rows if not r["skip"]]
pos = sum(1 for p in inner if p > 0)
print(f"\n  可比的 {len(inner)} 个职能里，{pos} 个是正的。中位数 {np.median(inner):+.1f}%")
S["within"] = rows
S["within_positive"] = [pos, len(inner)]
S["within_median"] = float(np.median(inner))

print("\n" + "=" * 78)
print("乙 · 职能之间：越需要数据的职能，本身越便宜还是越贵")
print("=" * 78)
cmp_ = [r for r in rows]
x = np.array([r["hard_rate"] for r in cmp_])
y = np.array([r["median"] for r in cmp_])
r_p = float(np.corrcoef(x, y)[0, 1])
# 相关系数也自助一次，别拿一个点估去讲因果
bs = []
for _ in range(4000):
    i = rng.choice(len(x), len(x), True)
    if len(set(x[i])) > 2:
        bs.append(np.corrcoef(x[i], y[i])[0, 1])
lo, hi = np.percentile(bs, [2.5, 97.5])
for r in sorted(cmp_, key=lambda r: -r["median"]):
    print(f"  {r['subcat']:<26} 中位 ${r['median']:>8,.0f}   该类要数据 {r['hard_rate']:>5.1f}%   n={r['n']}")
print(f"\n  相关系数 r = {r_p:+.3f}   95% 自助区间 [{lo:+.3f}, {hi:+.3f}]   （{len(cmp_)} 个职能）")
S["across"] = dict(r=r_p, lo=float(lo), hi=float(hi), k=len(cmp_))

print("\n" + "=" * 78)
print("丙 · 两个离散度：换职能 vs 换职级，哪个更能解释薪资")
print("=" * 78)
sub_med = w.groupby("subcat").pay.median()
sub_med = sub_med[w.groupby("subcat").size() >= 14]
lvl_med = w.groupby("seniority").pay.median().reindex(ORDER)
print(f"  跨职能   最高 ${sub_med.max():,.0f} ({sub_med.idxmax()})"
      f"   最低 ${sub_med.min():,.0f} ({sub_med.idxmin()})"
      f"   极差 {(sub_med.max()/sub_med.min()-1)*100:.1f}%")
print(f"  跨职级   最高 ${lvl_med.max():,.0f} (Leadership)"
      f"   最低 ${lvl_med.min():,.0f} (IC)"
      f"   极差 {(lvl_med.max()/lvl_med.min()-1)*100:.1f}%")
g = boot_diff(w[w.seniority == "Leadership"].pay, w[w.seniority == "IC"].pay)
print(f"  Leadership 对 IC   ${g[0]:>9,.0f}   95% CI [${g[1]:,.0f}, ${g[2]:,.0f}]")
gd = boot_diff(w[w.data_hard].pay, w[~w.data_hard].pay)
print(f"  要求数据 对 不要求  ${gd[0]:>9,.0f}   95% CI [${gd[1]:,.0f}, ${gd[2]:,.0f}]  ← 区间跨零")
S["spread"] = dict(
    subcat_hi=float(sub_med.max()), subcat_lo=float(sub_med.min()),
    subcat_hi_name=str(sub_med.idxmax()), subcat_lo_name=str(sub_med.idxmin()),
    level_hi=float(lvl_med.max()), level_lo=float(lvl_med.min()),
    lead_vs_ic=dict(diff=g[0], lo=g[1], hi=g[2]),
    data_vs_not=dict(diff=gd[0], lo=gd[1], hi=gd[2]))

print("\n" + "=" * 78)
print("丁 · 数据要求是职能的属性，不是职级的属性")
print("=" * 78)
by_lvl = lab.groupby("seniority").data_hard.agg(["size", "sum"]).reindex(ORDER)
by_lvl["pct"] = by_lvl["sum"] / by_lvl["size"] * 100
for i, r in by_lvl.iterrows():
    print(f"  {i:<12}{int(r['sum']):>3} / {int(r['size']):<4} = {r['pct']:>5.1f}%")
sub_rate = lab.groupby("subcat").data_hard.agg(["size", "mean"])
sub_rate = sub_rate[sub_rate["size"] >= 14].sort_values("mean", ascending=False)
print(f"\n  职级之间最大差 {by_lvl['pct'].max() - by_lvl['pct'].min():.1f} 个点")
print(f"  职能之间最大差 {(sub_rate['mean'].max() - sub_rate['mean'].min())*100:.1f} 个点"
      f"   ({sub_rate.index[0]} {sub_rate['mean'].iloc[0]*100:.0f}%"
      f" vs {sub_rate.index[-1]} {sub_rate['mean'].iloc[-1]*100:.0f}%)")
S["rate_by_level"] = {i: dict(n=int(r["size"]), pct=float(r["pct"])) for i, r in by_lvl.iterrows()}
S["rate_by_subcat"] = [dict(subcat=i, n=int(r["size"]), pct=float(r["mean"] * 100))
                       for i, r in sub_rate.iterrows()]

print("\n" + "=" * 78)
print("戊 · 剂量反应：数据要求越深，薪资越高吗")
print("=" * 78)
from scipy.stats import spearmanr
rho, p = spearmanr(w.data_depth, w.pay)
print(f"  Spearman rho = {rho:+.3f}   p = {p:.3f}   n = {len(w)}")
for d, grp in w.groupby("data_depth"):
    if len(grp) >= 8:
        print(f"    深度 {int(d)}   中位 ${grp.pay.median():>8,.0f}   n={len(grp)}")
S["dose"] = dict(rho=float(rho), p=float(p), n=int(len(w)))

json.dump(S, io.open(os.path.join(ROOT, "data", "processed", "story.json"), "w",
                     encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print("\n已写出 data/processed/story.json")
