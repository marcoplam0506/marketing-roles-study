# -*- coding: utf-8 -*-
"""阶段 5-7 · 回答问题清单，并把验证内建进来。

口径决定（2026-11-06）：主结论用 data_hard（SQL / BI 工具 / 实验设计 / 归因 / 代码），
不用 data_required。因为后者含 analytics 这个软信号，抽查显示它会捞到
"跟 Analytics 团队协作"这类非技能表述，撑不住追问。

每个比例都标分子分母。每个中位数都带自助法置信区间和样本量。
最后跑三组敏感性检验。

输入  data/interim/03_labeled.csv.gz + 02_classified.csv.gz
输出  data/processed/findings.json + stdout
"""
import json, os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(7)

lab = pd.read_csv(os.path.join(ROOT, "data", "interim", "03_labeled.csv.gz"))
allj = pd.read_csv(os.path.join(ROOT, "data", "interim", "02_classified.csv.gz"))

# ---------------- 薪资归一 ----------------
w = lab[lab.sal_min.notna() & lab.sal_max.notna()].copy()
w = w[w.sal_cur.isna() | (w.sal_cur == "USD")]
mult = w.sal_unit.map({"year": 1, "hour": 2080, "month": 12}).fillna(1)
w["pay"] = (w.sal_min + w.sal_max) / 2 * mult
w = w[(w.pay >= 40_000) & (w.pay <= 600_000)]
ORDER = ["IC", "Senior", "Leadership"]
w["seniority"] = pd.Categorical(w.seniority, ORDER, ordered=True)

F = {}
def say(k, v, line):
    F[k] = v
    print(line)

print("=" * 78)
print("样本")
print("=" * 78)
say("nyc_all", int(len(allj)), f"  纽约全部岗位        {len(allj):,}")
say("marketing", int(len(lab)), f"  判为营销岗          {len(lab):,}   ({len(lab)/len(allj)*100:.1f}% of 纽约全部)")
say("with_pay", int(len(w)), f"  其中薪资可用        {len(w):,}   ({len(w)/len(lab)*100:.0f}%)")
say("companies", int(lab.company.nunique()), f"  覆盖公司            {lab.company.nunique()}")

print("\n" + "=" * 78)
print("Q1-Q2  数据能力的要求有多普遍")
print("=" * 78)
for k, lbl in (("data_hard", "硬技能（SQL/BI/实验/归因/代码）"), ("data_required", "含软信号（再加 analytics）")):
    n, d = int(lab[k].sum()), len(lab)
    say(k + "_rate", round(n / d * 100, 1), f"  {lbl:<34}{n:>4} / {d}  = {n/d*100:.1f}%")

print("\n  分项（分母均为 367 条营销岗）:")
for s in ("sql", "bi_tool", "experiment", "attribution", "analytics", "coding", "sheets"):
    n = int(lab[s].sum())
    say("sig_" + s, round(n / len(lab) * 100, 1), f"    {s:<13}{n:>4}  {n/len(lab)*100:>5.1f}%")

print("\n" + "=" * 78)
print("Q3  哪一类营销岗最离不开数据")
print("=" * 78)
sub = lab.groupby("subcat").agg(n=("data_hard", "size"), hard=("data_hard", "sum"))
sub["pct"] = (sub.hard / sub.n * 100).round(1)
sub = sub[sub.n >= 12].sort_values("pct", ascending=False)
for name, r in sub.iterrows():
    print(f"  {name:<28}{int(r.hard):>3} / {int(r.n):<4} = {r.pct:>5.1f}%")
F["by_subcat"] = [{"subcat": i, "n": int(r.n), "hard": int(r.hard), "pct": r.pct} for i, r in sub.iterrows()]
print("  （样本不足 12 条的子类已略去）")


def boot_med(x, n=4000):
    x = np.asarray(x, float)
    if len(x) < 5:
        return None, None
    b = [np.median(rng.choice(x, len(x), replace=True)) for _ in range(n)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def gap(d, key="data_hard"):
    a, b = d[d[key]].pay, d[~d[key]].pay
    if len(a) < 5 or len(b) < 5:
        return None
    ma, mb = float(np.median(a)), float(np.median(b))
    lo, hi = boot_med(a); lo2, hi2 = boot_med(b)
    # 差值本身也自助
    db = [np.median(rng.choice(a, len(a), True)) - np.median(rng.choice(b, len(b), True)) for _ in range(4000)]
    return dict(n_yes=len(a), n_no=len(b), med_yes=ma, med_no=mb,
                diff=ma - mb, pct=(ma / mb - 1) * 100,
                ci=(float(np.percentile(db, 2.5)), float(np.percentile(db, 97.5))))


print("\n" + "=" * 78)
print("Q4  要求数据能力的岗位，薪资高多少（未控制职级）")
print("=" * 78)
g = gap(w)
F["overall_gap"] = g
print(f"  要求      中位 ${g['med_yes']:>9,.0f}   n={g['n_yes']}")
print(f"  不要求    中位 ${g['med_no']:>9,.0f}   n={g['n_no']}")
print(f"  差额      ${g['diff']:>9,.0f}   ({g['pct']:+.1f}%)")
print(f"  95% 自助区间  ${g['ci'][0]:,.0f} 到 ${g['ci'][1]:,.0f}")
print("  注意：这个差额里混着职级 —— 下一步才是真结论")

print("\n" + "=" * 78)
print("Q5  控制职级之后还剩多少  ← 主结论")
print("=" * 78)
F["by_level"] = {}
for lvl in ORDER:
    d = w[w.seniority == lvl]
    g = gap(d)
    if not g:
        print(f"  {lvl:<12}样本不足")
        continue
    F["by_level"][lvl] = g
    sig = "✓" if (g["ci"][0] > 0 or g["ci"][1] < 0) else "✗ 区间跨零"
    print(f"  {lvl:<12}要求 ${g['med_yes']:>9,.0f} (n={g['n_yes']:>3})   "
          f"不要求 ${g['med_no']:>9,.0f} (n={g['n_no']:>3})   "
          f"差 {g['pct']:>+6.1f}%   CI [${g['ci'][0]:>8,.0f}, ${g['ci'][1]:>8,.0f}]  {sig}")

print("\n" + "=" * 78)
print("Q6-Q7  职级越高，数据要求越强还是越弱")
print("=" * 78)
ct = lab.groupby("seniority").agg(n=("data_hard", "size"), hard=("data_hard", "sum"))
ct = ct.reindex(ORDER)
ct["pct"] = (ct.hard / ct.n * 100).round(1)
for lvl, r in ct.iterrows():
    print(f"  {lvl:<12}{int(r.hard):>3} / {int(r.n):<4} = {r.pct:>5.1f}%")
F["hard_by_level"] = {i: {"n": int(r.n), "hard": int(r.hard), "pct": r.pct} for i, r in ct.iterrows()}

print("\n  各职级的薪资中位数（全部岗位，不分数据要求）:")
for lvl in ORDER:
    d = w[w.seniority == lvl].pay
    lo, hi = boot_med(d)
    print(f"    {lvl:<12}${np.median(d):>9,.0f}   n={len(d):<4} CI [${lo:,.0f}, ${hi:,.0f}]")
F["pay_by_level"] = {lvl: {"median": float(np.median(w[w.seniority == lvl].pay)),
                          "n": int((w.seniority == lvl).sum())} for lvl in ORDER}

print("\n" + "=" * 78)
print("验证链 · 三组敏感性检验")
print("=" * 78)
tests = {
    "去掉 design 梯子": w[w.job_family != "design"],
    "去掉样本最多的 3 家公司": w[~w.company.isin(w.company.value_counts().head(3).index)],
    "只看 2026 年发布的": w[w.posted_at.fillna("").str[:4] == "2026"],
    "改用软口径 data_required": None,
}
F["sensitivity"] = {}
for name, d in tests.items():
    if name.startswith("改用"):
        g = gap(w, "data_required")
    else:
        g = gap(d)
    if not g:
        print(f"  {name:<26}样本不足"); continue
    F["sensitivity"][name] = g
    print(f"  {name:<26}差 {g['pct']:>+6.1f}%   n={g['n_yes']}+{g['n_no']}   "
          f"CI [${g['ci'][0]:>8,.0f}, ${g['ci'][1]:>8,.0f}]")

print("\n  分职级的敏感性（去掉 design 梯子后）:")
for lvl in ORDER:
    d = w[(w.seniority == lvl) & (w.job_family != "design")]
    g = gap(d)
    if g:
        print(f"    {lvl:<12}差 {g['pct']:>+6.1f}%  n={g['n_yes']}+{g['n_no']}")

os.makedirs(os.path.join(ROOT, "data", "processed"), exist_ok=True)
json.dump(F, open(os.path.join(ROOT, "data", "processed", "findings.json"), "w",
                  encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(f"\n已写出 data/processed/findings.json")
