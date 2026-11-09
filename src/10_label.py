# -*- coding: utf-8 -*-
"""阶段 3b · 给每份 JD 打"数据能力要求"的标签，并抽出职级。

这是整个项目的核心变量。两个已知陷阱，代码里都处理：
  1 公司自我介绍里的 "data-driven culture" 不是岗位要求
  2 "Excel" 几乎每份 JD 都有，单独出现不足以算数据要求

输入  data/interim/02_classified.csv.gz
输出  data/interim/03_labeled.csv.gz
      data/interim/03_label_audit.csv   每条命中的上下文，供人工抽查
"""
import os, re, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "interim", "02_classified.csv.gz")
OUT = os.path.join(ROOT, "data", "interim", "03_labeled.csv.gz")
AUD = os.path.join(ROOT, "data", "interim", "03_label_audit.csv")

R = lambda p: re.compile(p, re.I)

# ---------- 数据能力的七个面向 ----------
SIGNALS = {
    "sql":        R(r"\bSQL\b|\bBigQuery\b|\bSnowflake\b|\bRedshift\b|\bdbt\s+(?!Labs)|\bquery\s+(?:the\s+)?(?:data|database)"),
    "bi_tool":    R(r"\bLooker\b|\bTableau\b|\bPower\s?BI\b|\bMode\b(?=\s+Analytics)|\bAmplitude\b|\bMixpanel\b"
                    r"|\bHeap\b|\bGA4\b|Google Analytics|\bHex\b|\bSigma\b(?=\s+Computing)|\bMetabase\b|\bDomo\b"),
    "experiment": R(r"\bA/?B test|\bmultivariate test|\bexperimentation\b|\bexperiment design"
                    r"|\bincrementality\b|\bholdout\b|\bstatistical significance\b|\btest[\s-]and[\s-]learn\b"),
    "attribution":R(r"\battribution\b|\bMMM\b|media mix model|marketing mix model|\bmulti[\s-]touch\b"
                    r"|\bincrementality testing\b|\bmeasurement framework\b|\bLTV\b|\bCAC\b|\bROAS\b|\bMER\b"),
    "analytics":  R(r"\banalytics\b|\bdata analysis\b|\banalyze data\b|\bdata analyst\b|\breporting and analysis\b"
                    r"|\bquantitative\b|\bdata[\s-]informed\b|\bmetrics\b|\bKPIs?\b|\bdashboards?\b"),
    "coding":     R(r"\bPython\b|\bR\b(?=\s*(?:,|/|and)\s*Python)|\bpandas\b|\bJupyter\b|\bscripting\b"),
    "sheets":     R(r"\bExcel\b|Google Sheets|\bspreadsheet"),
}

# 公司自我介绍里的套话，不算岗位要求
BOILER = R(r"data[\s-]driven (?:culture|company|organi[sz]ation|team|approach|mindset)"
           r"|we are a data|our data[\s-]driven"
           # "partner with Analytics" 是在说跟哪个团队协作，不是要求技能
           r"|(?:partner|work|collaborat\w+|align)\s+(?:closely\s+)?with\s+(?:the\s+)?Analytics"
           r"|Analytics\s+(?:team|org|group|partners)"
           r"|culture of (?:creativity|experimentation|innovation)|fosters? a culture")

# ---------- 职级：三档 ----------
# 美国科技业营销岗的陷阱是 "Manager" 多半是个人贡献者，不带人
SENIOR = [
    ("Leadership", R(r"\b(?:VP|SVP|EVP|Vice President|Chief|CMO|Head of|Director)\b")),
    ("Senior",     R(r"\b(?:Senior|Sr\.?|Lead|Principal|Staff|Group)\b")),
    ("IC",         R(r".")),
]

SENIOR_HINT = R(r"\b(\d{1,2})\+?\s*(?:-|to|–)?\s*(\d{1,2})?\s*years?\b")


def ctx(text, m, w=130):
    s = re.sub(r"\s+", " ", text[max(0, m.start()-w):m.end()+w])
    return s.strip()


def main():
    df = pd.read_csv(SRC)
    mk = df[df.is_marketing].copy()
    print(f"营销岗 {len(mk):,}\n")

    rows, audit = [], []
    for r in mk.itertuples():
        t = str(r.jd_text or "")
        flags, hits = {}, []
        for name, pat in SIGNALS.items():
            ms = list(pat.finditer(t))
            # 命中全部落在公司套话里就不算
            real = [m for m in ms if not BOILER.search(ctx(t, m, 90))]
            flags[name] = len(real) > 0
            if real:
                hits.append(name)
                audit.append(dict(job_id=r.job_id, company=r.company, title=r.title,
                                  signal=name, n=len(real), context=ctx(t, real[0])[:260]))
        # Excel 单独出现不算数据要求：几乎每份 JD 都有
        core = ["sql", "bi_tool", "experiment", "attribution", "analytics", "coding"]
        flags["data_required"] = any(flags[k] for k in core)
        flags["data_depth"] = sum(flags[k] for k in core)
        # 硬技能：SQL / BI / 实验 / 归因 / 代码，比泛泛的 "analytics" 强
        hard = ["sql", "bi_tool", "experiment", "attribution", "coding"]
        flags["data_hard"] = any(flags[k] for k in hard)
        lvl = next(n for n, p in SENIOR if p.search(str(r.title or "")))
        yrs = SENIOR_HINT.search(t)
        rows.append(dict(job_id=r.job_id, seniority=lvl,
                         years_min=int(yrs.group(1)) if yrs else None, **flags))

    lab = pd.DataFrame(rows)
    mk = mk.merge(lab, on="job_id", how="left")

    print("各信号命中率:")
    for k in list(SIGNALS) + ["data_required", "data_hard"]:
        print(f"  {k:<16}{mk[k].mean()*100:>6.1f}%   ({int(mk[k].sum())} 条)")
    print(f"\n数据深度分布 (0-6):\n{mk.data_depth.value_counts().sort_index().to_string()}")
    print(f"\n职级分布:\n{mk.seniority.value_counts().to_string()}")
    print(f"\n职级 x 是否要求数据能力:")
    print(pd.crosstab(mk.seniority, mk.data_required).to_string())
    print(f"\n带薪资的交叉表:")
    print(pd.crosstab(mk[mk.sal_min.notna()].seniority, mk[mk.sal_min.notna()].data_required).to_string())

    mk.to_csv(OUT, index=False, compression="gzip")
    pd.DataFrame(audit).to_csv(AUD, index=False, encoding="utf-8-sig")
    print(f"\n已写出 {OUT}")
    print(f"      {AUD}  ({len(audit):,} 条命中上下文，供抽查)")


if __name__ == "__main__":
    main()
