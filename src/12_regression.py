# -*- coding: utf-8 -*-
"""阶段 7 · 把辛普森悖论量出来。

分组看只能说"看起来是"。要说"是"，得在同一个模型里控制住职级和子类，
看 data_hard 的系数在加入控制前后怎么变。

log(薪资) ~ data_hard + 职级 + 子类
自助法 2000 次给置信区间，不依赖正态假设（样本只有 298 条）。
手写最小二乘，不引 statsmodels。

输入  data/interim/03_labeled.csv.gz
输出  data/processed/regression.json + stdout
"""
import json, os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(23)

w = pd.read_csv(os.path.join(ROOT, "data", "interim", "03_labeled.csv.gz"))
w = w[w.sal_min.notna() & w.sal_max.notna()]
w = w[w.sal_cur.isna() | (w.sal_cur == "USD")]
mult = w.sal_unit.map({"year": 1, "hour": 2080, "month": 12}).fillna(1)
w["pay"] = (w.sal_min + w.sal_max) / 2 * mult
w = w[(w.pay >= 40_000) & (w.pay <= 600_000)].copy()
w["logpay"] = np.log(w.pay)


def design(d, use_level, use_subcat):
    X = [np.ones(len(d)), d.data_hard.astype(float).values]
    names = ["截距", "data_hard"]
    if use_level:
        for lvl in ("Senior", "Leadership"):          # IC 作基准
            X.append((d.seniority == lvl).astype(float).values)
            names.append("职级=" + lvl)
    if use_subcat:
        base = d.subcat.value_counts().idxmax()        # 样本最多的子类作基准
        for sc in sorted(set(d.subcat) - {base}):
            X.append((d.subcat == sc).astype(float).values)
            names.append("子类=" + sc)
    return np.column_stack(X), names


def fit(d, use_level, use_subcat, B=2000):
    X, names = design(d, use_level, use_subcat)
    y = d.logpay.values
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    idx = np.arange(len(d))
    draws = []
    for _ in range(B):
        s = rng.choice(idx, len(idx), replace=True)
        try:
            draws.append(np.linalg.lstsq(X[s], y[s], rcond=None)[0][1])
        except np.linalg.LinAlgError:
            pass
    draws = np.array(draws)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    # 对数模型里，系数 b 对应的薪资变化是 exp(b)-1
    return dict(coef=float(beta[1]), pct=float(np.exp(beta[1]) - 1) * 100,
                lo=float(np.exp(lo) - 1) * 100, hi=float(np.exp(hi) - 1) * 100,
                k=len(names), n=len(d))


MODELS = [
    ("只有 data_hard", False, False),
    ("+ 控制职级", True, False),
    ("+ 控制职级和子类", True, True),
]
print("=" * 78)
print("data_hard 对薪资的效应，随着控制变量加入的变化")
print(f"样本 {len(w)} 条，被解释变量 log(薪资中点)")
print("=" * 78)
out = {}
for name, lv, sc in MODELS:
    r = fit(w, lv, sc)
    out[name] = r
    sig = "显著" if (r["lo"] > 0 or r["hi"] < 0) else "区间跨零"
    print(f"  {name:<20}{r['pct']:>+7.1f}%   95% CI [{r['lo']:>+6.1f}%, {r['hi']:>+6.1f}%]   {sig}")

print("\n  读法：前两行接近零，第三行跳正，就是辛普森悖论的量化证据 ——")
print("  同一种营销岗里要求数据的更贵，但要求数据的那几种营销岗本身更便宜。")

print("\n" + "=" * 78)
print("对照：职级的效应（同一模型里）")
print("=" * 78)
X, names = design(w, True, True)
beta = np.linalg.lstsq(X, w.logpay.values, rcond=None)[0]
for nm, b in zip(names, beta):
    if nm.startswith("职级"):
        print(f"  {nm:<20}{(np.exp(b)-1)*100:>+7.1f}%   （基准 = IC）")

print("\n" + "=" * 78)
print("各子类相对基准的薪资差（同一模型里，已控制职级与数据要求）")
print("=" * 78)
base = w.subcat.value_counts().idxmax()
print(f"  基准子类 = {base}  (n={int((w.subcat==base).sum())})")
rows = [(nm.replace("子类=", ""), (np.exp(b) - 1) * 100)
        for nm, b in zip(names, beta) if nm.startswith("子类")]
for nm, v in sorted(rows, key=lambda x: -x[1]):
    n = int((w.subcat == nm).sum())
    hard = w[w.subcat == nm].data_hard.mean() * 100
    print(f"  {nm:<28}{v:>+7.1f}%   n={n:>3}   该类要数据 {hard:>5.1f}%")

out["level_effect"] = {nm: float((np.exp(b) - 1) * 100) for nm, b in zip(names, beta) if nm.startswith("职级")}
out["subcat_effect"] = {nm: v for nm, v in rows}
json.dump(out, open(os.path.join(ROOT, "data", "processed", "regression.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n已写出 data/processed/regression.json")
