# -*- coding: utf-8 -*-
"""阶段 3 · 岗位归类。规则由 Marco 定，这里只是执行。

v2 修正（2026-10-08，抽检闸门之后）：
  1 职能守卫优先于关键词白名单。"Director of Engineering, Marketing Agent Platform"
    里的 marketing 不该把一个工程总监变成营销岗。martech 岗单独豁免。
  2 lifecycle 必须带 user/customer/email 等限定词，否则 "Product Lifecycle" 会误伤
  3 子类补 Field & Partner Marketing 与 Events（原先全掉进 Other）
  4 产品梯子与数据梯子的岗位不计入营销集（Marco 裁定）：
    它们走的是另一条薪酬带，留着会让"懂数据更值钱"这个结论凭空成立

输入  data/interim/01_nyc_all.csv.gz
输出  data/interim/02_classified.csv.gz
"""
import os, re, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "interim", "01_nyc_all.csv.gz")
OUT = os.path.join(ROOT, "data", "interim", "02_classified.csv.gz")
R = lambda p: re.compile(p, re.I)

# ---------- 0. martech 豁免：营销系统岗，带 engineer 也留 ----------
MARTECH = R(r"marketing (?:engineer|systems?|technolog|automation|platform engineer)"
            r"|martech|marketing ops|marketing operations")

# ---------- 1. 职能守卫：标题里的职能词决定这个人在哪条梯子上，优先于关键词 ----------
FUNC_GUARD = [
    (R(r"\b(?:software|backend|back[\s-]?end|frontend|front[\s-]?end|full[\s-]?stack|platform"
       r"|infrastructure|security|ml|machine learning|systems?|cloud|devops|site reliability"
       r"|data|web|design|forward deployed|solutions?|sales|support|network|datacenter)\s+engineer\b"
       r"|\bengineer(?:ing)?\s+manager\b|\bdirector of engineering\b|\bhead of engineering\b"
       r"|\bdeveloper\b|\bsre\b|^engineer\b|\bengineer,"), "重工程"),
    # 抽查发现：Solutions Architect / Account Executive 这类售前售后岗
    # 会被标题里的 communications、growth 等词捞进来
    (R(r"\bsolutions?\s+(?:architect|engineer|consultant)\b|\baccount executive\b"
       r"|\bsales engineer\b|\bcustomer success\b|\baccount director\b"), "售前售后"),
    # 行业垂直名不是职能："Communications, Media & Entertainment" 是客户行业
    (R(r"communications,\s*(?:media|and media)|media\s*(?:&|and)\s*entertainment"), "行业垂直名"),
    (R(r"\bdirector of product\b|\bhead of product\b|\bproduct manager\b|\bproduct lead\b"
       r"|\bgroup product\b|\btechnical program manager\b|\b(?:staff|senior|sr\.?|lead|principal)\s+product\s+manager\b"),
     "产品梯子"),
    (R(r"\bdata scientist\b|\bdata analyst\b|\banalytics engineer\b|\bresearch scientist\b"
       r"|\bquantitative\b|\bstatistician\b|\bdata science\b"), "数据梯子"),
]

# ---------- 2. 强白名单：过了职能守卫之后，命中就是营销 ----------
STRONG = R(r"\bmarketing\b|\bmarketer\b|\bbrand\b|\bcopywrit|public relations|\bcomms\b"
           r"|communications|social media|\bseo\b|\bsem\b|demand gen|paid media|paid social"
           r"|\bcrm\b|martech|\bpmm\b|\bpress\b|editorial|influencer")

# ---------- 3. 其余排除守卫 ----------
GUARD = [
    (R(r"mid[\s-]?market"), "Mid-Market 是客户规模分层"),
    (R(r"\bmarketplace\b"), "产品形态"),
    (R(r"capital market|equity research"), "金融"),
    (R(r"market research|quantitative research|user research"), "用户研究，归产品"),
    (R(r"\bcounsel\b|\blegal\b|\bcompliance\b|\bgrc\b"), "法务合规"),
]

# ---------- 4. 弱白名单 ----------
WEAK = R(r"\bgrowth\b|\bcontent\b|\bcreative\b|\bcampaign\b|\bacquisition\b|\bcommunity\b"
         r"|\bevents?\b|\bwebsite\b")
# lifecycle 必须带限定词，否则 Product Lifecycle / Server Lifecycle 会误伤
LIFECYCLE = R(r"(?:user|customer|member|subscriber|email|audience|player)\s+lifecycle"
              r"|lifecycle\s+(?:marketing|manager|lead|program|engagement|crm)")

# ---------- 5. 子类，按优先级从上往下 ----------
SUBCAT = [
    ("Product Marketing",         R(r"product marketing|\bpmm\b")),
    ("Comms & PR",                R(r"public relations|\bcomms\b|communications|\bpress\b")),
    ("Field & Partner Marketing", R(r"field marketing|field marketer|partner marketing|channel marketing"
                                    r"|customer marketing|co[\s-]?marketing|solutions marketing|abm\b")),
    ("Events",                    R(r"\bevents?\b|conference|trade show|\bsummit\b")),
    ("Lifecycle & CRM",           R(r"lifecycle|\bcrm\b|retention|email market")),
    ("Growth & Performance",      R(r"\bgrowth\b|performance market|paid media|paid social|\bseo\b|\bsem\b"
                                    r"|demand gen|acquisition|programmatic|\bppc\b|media buy")),
    ("Content & Social",          R(r"\bcontent\b|social media|\bsocial\b|copywrit|editorial|community"
                                    r"|influencer|\bvideo\b|\bcreator\b")),
    ("Brand & Creative",          R(r"\bbrand\b|\bcreative\b|\bdesign(?:er)?\b|\bmotion\b|art director"
                                    r"|\bproducer\b|\bstudio\b")),
    ("Marketing Ops & Analytics", R(r"marketing (?:ops|operations|analytic|technolog|data|engineer|systems?)"
                                    r"|martech|\banalyst\b|\banalytics\b|\binsight")),
]

FAMILY = [
    ("design", R(r"\bdesigner\b|\bdesign lead\b|art director|\bmotion\b")),
]


def classify(title, dept):
    t, d = str(title or ""), str(dept or "")
    martech = bool(MARTECH.search(t))
    if not martech:
        for g, why in FUNC_GUARD:
            if g.search(t):
                return False, None, None, why
    if STRONG.search(t) or martech:
        why = "strong"
    else:
        hit = next((w for g, w in GUARD if g.search(t)), None)
        if hit:
            return False, None, None, hit
        if re.search(r"go[\s-]?to[\s-]?market|^gtm", d, re.I):
            return False, None, None, "部门为 GTM 销售组织"
        if not (WEAK.search(t) or LIFECYCLE.search(t)):
            return False, None, None, None
        why = "weak"
    for g, w in GUARD:                      # 强白名单也要过这几道
        if g.search(t):
            return False, None, None, w
    sub = next((n for n, p in SUBCAT if p.search(t)), "Other Marketing")
    fam = next((n for n, p in FAMILY if p.search(t)), "marketing_core")
    return True, sub, fam, why


def main():
    df = pd.read_csv(SRC)
    res = [classify(r.title, r.department) for r in df.itertuples()]
    df["is_marketing"] = [x[0] for x in res]
    df["subcat"] = [x[1] for x in res]
    df["job_family"] = [x[2] for x in res]
    df["rule"] = [x[3] for x in res]

    mk = df[df.is_marketing]
    print(f"纽约全部岗位 {len(df):,}")
    print(f"判为营销相关 {len(mk):,}  ({len(mk)/len(df)*100:.1f}%)\n")
    print("子类分布:");  print(mk.subcat.value_counts().to_string())
    print("\n职能梯子:"); print(mk.job_family.value_counts().to_string())
    print("\n被守卫挡下的:"); print(df[df.rule.notna() & ~df.is_marketing].rule.value_counts().head(8).to_string())
    print(f"\n营销岗带薪资: {mk.sal_min.notna().sum():,} ({mk.sal_min.notna().mean()*100:.1f}%)")
    df.to_csv(OUT, index=False, compression="gzip")
    print(f"\n已写出 {OUT}")


if __name__ == "__main__":
    main()
