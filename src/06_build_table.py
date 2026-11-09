# -*- coding: utf-8 -*-
"""阶段 3 · 把三家 ATS 归一成一张纽约宽表。

处理阶段 1 量出来的三个坑：
  1 Lever 正文拆在多个字段 -> descriptionPlain + lists 拼接（排除 EEO/公司介绍样板）
  2 Greenhouse content 双重 HTML 转义 -> unescape 两次再去标签
  3 薪资三种形态 -> 统一成 min/max/unit

输入  data/raw/{ashby,greenhouse,lever}.json.gz
输出  data/interim/01_nyc_all.csv.gz   纽约全部岗位（含非 marketing，留分母）
"""
import gzip, html, json, os, re, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "interim", "01_nyc_all.csv.gz")

NYC = re.compile(r"\bNew York\b|\bNYC\b|\bBrooklyn\b|\bQueens\b|\bBronx\b|\bStaten Island\b"
                 r"|\bManhattan\b|\bJersey City\b|\bLong Island City\b", re.I)
NOT_NYC = re.compile(r"\bAlbany\b|\bBuffalo\b|\bRochester\b|\bSyracuse\b|\bIthaca\b|\bBrewerton\b", re.I)
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"[ \t ]+")


def load(ats):
    with gzip.open(os.path.join(RAW, f"{ats}.json.gz"), "rt", encoding="utf-8") as f:
        store = json.load(f)
    return [(c, j) for c, p in store.items() if p
            for j in ((p.get("jobs") if isinstance(p, dict) else p) or [])]


def detag(s):
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = TAG.sub(" ", s)
    s = html.unescape(s)
    s = WS.sub(" ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


# ---------- 薪资 ----------
# 验证链（src/07）抓到的三类错，在这里修：
#   1 "$180-$220k" K 只写在第二个数上  -> 按量级补齐
#   2 "deal sizes range from $200K to $1M" 不是薪资 -> 附近没有薪资关键词就不要猜
#   3 "$112,000 - $140,00 CAD" 雇主打错字 + 加币 -> 币种判定 + 量级合理性检查
MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[Kk]|\d{1,3}(?:\.\d{1,2})?)"
RANGE = re.compile(MONEY + r"\s*(?:-|–|—|to|and)\s*" + MONEY)
NEAR = re.compile(r"salary|compensation|base pay|pay range|base range|pay transparency"
                  r"|annual(?:ized)? (?:base|pay|salary)|hourly|per hour|OTE|total cash", re.I)
NOTPAY = re.compile(r"deal size|contract value|ARR|ACV|revenue|budget|spend|raised|funding"
                    r"|valuation|portfolio|assets under", re.I)
FOREIGN = re.compile(r"CAD|GBP|EUR|AUD|SGD|INR|CA\$", re.I)
HOURLY = re.compile(r"per\s+hour|/\s?hr|hourly|an hour|/hour", re.I)
OTE = re.compile(r"OTE|on.target earnings|total cash compensation", re.I)


def to_num(s):
    s = s.replace(",", "").replace("$", "").strip()
    if s.lower().endswith("k"):
        return float(s[:-1].strip()) * 1000
    return float(s)


def parse_text_salary(text):
    """返回 (min, max, unit, currency, is_ote)。附近没有薪资关键词就返回空，不猜。"""
    best = None
    for m in RANGE.finditer(text):
        w = text[max(0, m.start() - 180):m.end() + 80]
        if not NEAR.search(w) or NOTPAY.search(w):
            continue
        lo, hi = to_num(m.group(1)), to_num(m.group(2))
        # K 简写：$180-$220k 里的 180 其实是 180000
        if hi >= 1000 and lo < 1000 and hi / max(lo, 1) > 50:
            lo *= 1000
        if lo >= 1000 and hi < 1000 and lo / max(hi, 1) > 50:
            hi *= 1000
        if hi < lo:
            lo, hi = hi, lo
        unit = "hour" if HOURLY.search(w) else "year"
        if unit == "year" and hi < 2000:          # 没写单位但数值像时薪
            unit = "hour"
        # 量级合理性：超出区间的多半是源数据打错字，宁可丢掉
        if unit == "year" and not (20_000 <= lo <= 1_200_000 and 20_000 <= hi <= 1_500_000):
            continue
        if unit == "hour" and not (12 <= lo <= 500 and 12 <= hi <= 600):
            continue
        cur = "non_usd" if FOREIGN.search(w) else "USD"
        cand = (lo, hi, unit, cur, bool(OTE.search(w)))
        if best is None or (best[3] != "USD" and cur == "USD"):
            best = cand
    return best if best else (None, None, None, None, None)


def parse_ashby_salary(j):
    c = j.get("compensation") or {}
    s = c.get("scrapeableCompensationSalarySummary") or c.get("compensationTierSummary")
    if not s:
        return (None, None, None, None, None)
    # 这个字段本身就是薪资，不需要关键词把关
    m = RANGE.search(s)
    if not m:
        return (None, None, None, None, None)
    lo, hi = to_num(m.group(1)), to_num(m.group(2))
    if hi >= 1000 and lo < 1000 and hi / max(lo, 1) > 50:
        lo *= 1000
    if hi < lo:
        lo, hi = hi, lo
    unit = "hour" if (HOURLY.search(s) or hi < 2000) else "year"
    return (lo, hi, unit, "USD", bool(OTE.search(s)))


def parse_lever_salary(j):
    r = j.get("salaryRange") or {}
    if not r.get("min") and not r.get("max"):
        return (None, None, None, None, None)
    iv = (r.get("interval") or "")
    unit = "hour" if "hour" in iv else ("month" if "month" in iv else "year")
    return (r.get("min"), r.get("max"), unit, r.get("currency") or "USD", False)


# ---------- 各家取字段 ----------
def rows_ashby():
    for c, j in load("ashby"):
        loc = " ; ".join([j.get("location") or ""] +
                         [s.get("location") or "" for s in (j.get("secondaryLocations") or [])])
        lo, hi, unit, cur, ote = parse_ashby_salary(j)
        txt = detag(j.get("descriptionPlain"))
        if lo is None:                                   # 字段没有就从正文兜底
            lo, hi, unit, cur, ote = parse_text_salary(txt)
            src = "ashby_text" if lo else None
        else:
            src = "ashby_field"
        yield dict(ats="ashby", company=c, job_id=j.get("id"), title=(j.get("title") or "").strip(),
                   department=j.get("department"), team=j.get("team"),
                   employment_type=j.get("employmentType"), location_raw=loc,
                   remote=j.get("isRemote"), posted_at=j.get("publishedAt"),
                   url=j.get("jobUrl"), jd_text=txt, full_text=txt,
                   sal_min=lo, sal_max=hi, sal_unit=unit, sal_cur=cur, sal_ote=ote,
                   sal_src=src)


def rows_greenhouse():
    intro = re.compile(r'<div class="content-(?:intro|conclusion)">.*?</div>', re.S | re.I)
    for c, j in load("greenhouse"):
        raw = html.unescape(j.get("content") or "")
        body = intro.sub(" ", raw)                      # 去掉公司介绍/结尾样板
        txt = detag(body)
        lo, hi, unit, cur, ote = parse_text_salary(detag(raw))   # 薪资用全文，含法务段
        loc = " ; ".join([(j.get("location") or {}).get("name") or ""] +
                         [o.get("name") or "" for o in (j.get("offices") or [])])
        yield dict(ats="greenhouse", company=j.get("company_name") or c, job_id=j.get("id"),
                   title=(j.get("title") or "").strip(),
                   department=(j.get("departments") or [{}])[0].get("name"), team=None,
                   employment_type=j.get("employment"), location_raw=loc,
                   remote=None, posted_at=j.get("first_published"),
                   url=j.get("absolute_url"), jd_text=txt,
                   full_text=detag(raw),
                   sal_min=lo, sal_max=hi, sal_unit=unit, sal_cur=cur, sal_ote=ote,
                   sal_src="gh_text" if lo else None)


def rows_lever():
    for c, j in load("lever"):
        cat = j.get("categories") or {}
        # 正文拼接：介绍段 + 要求清单。排除 EEO 与公司介绍样板
        parts = [j.get("descriptionPlain") or ""]
        for blk in (j.get("lists") or []):
            parts.append((blk.get("text") or "") + "\n" + detag(blk.get("content") or ""))
        # 关键修正：薪资常写在 additionalPlain（法务段），打标签用的正文却要排除它
        full = "\n\n".join(x for x in [j.get("descriptionPlain") or ""]
                            + [detag(b.get("content") or "") for b in (j.get("lists") or [])]
                            + [j.get("additionalPlain") or "", j.get("openingPlain") or ""] if x)
        lo, hi, unit, cur, ote = parse_lever_salary(j)
        if lo is None:
            lo, hi, unit, cur, ote = parse_text_salary(detag(full))
            lsrc = "lever_text" if lo else None
        else:
            lsrc = "lever_field"
        loc = " ; ".join([cat.get("location") or ""] + list(cat.get("allLocations") or []))
        yield dict(ats="lever", company=c, job_id=j.get("id"), title=(j.get("text") or "").strip(),
                   department=cat.get("department"), team=cat.get("team"),
                   employment_type=cat.get("commitment"), location_raw=loc,
                   remote=(j.get("workplaceType") == "remote"),
                   posted_at=pd.to_datetime(j.get("createdAt"), unit="ms", utc=True).isoformat()
                   if j.get("createdAt") else None,
                   url=j.get("hostedUrl"), jd_text=detag("\n\n".join(p for p in parts if p)),
                   full_text=detag(full),
                   sal_min=lo, sal_max=hi, sal_unit=unit, sal_cur=cur, sal_ote=ote,
                   sal_src=lsrc)


def main():
    allrows = list(rows_ashby()) + list(rows_greenhouse()) + list(rows_lever())
    df = pd.DataFrame(allrows)
    print(f"全部岗位            {len(df):,}")

    loc = df["location_raw"].fillna("")
    df = df[loc.str.contains(NYC) & ~loc.str.contains(NOT_NYC)].copy()
    print(f"纽约市 + Jersey City {len(df):,}")

    df["jd_len"] = df["jd_text"].str.len()
    print(f"\n正文长度中位数 按 ATS:")
    print(df.groupby("ats")["jd_len"].median().to_string())
    print(f"\n带薪资: {df['sal_min'].notna().sum():,} ({df['sal_min'].notna().mean()*100:.1f}%)")
    print(df.groupby("sal_src")["sal_min"].size().to_string())
    print(f"\n薪资单位分布:\n{df['sal_unit'].value_counts(dropna=False).to_string()}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False, compression="gzip")
    print(f"\n已写出 {OUT}  ({os.path.getsize(OUT)/1048576:.1f} MB)")


if __name__ == "__main__":
    main()
