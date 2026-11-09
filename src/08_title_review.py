# -*- coding: utf-8 -*-
"""阶段 3 · 把岗位名摊开给人看，让人来定规则。

交叉用两个信号互相校验：
  A 岗位名正则（我写的粗筛）
  B 雇主自己填的 department 字段
两者不一致的地方，就是规则需要人判断的地方。
"""
import os, re, sys, collections
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT, "data", "interim", "01_nyc_all.csv.gz"))
df["title"] = df["title"].fillna("").str.strip()
df["dept"] = df["department"].fillna("").str.strip()

MK_TITLE = re.compile(r"market|brand|growth|content|communicat|social media|demand gen|\bseo\b|\bsem\b"
                      r"|\bcrm\b|lifecycle|creative|campaign|paid media|acquisition|public relations", re.I)
MK_DEPT = re.compile(r"market|brand|growth|communicat|creative|content|demand", re.I)

df["by_title"] = df.title.str.contains(MK_TITLE)
df["by_dept"] = df.dept.str.contains(MK_DEPT)

n = len(df)
print(f"纽约全部岗位 {n:,}")
print(f"  岗位名命中      {df.by_title.sum():>4}")
print(f"  部门命中        {df.by_dept.sum():>4}")
print(f"  两者都命中      {(df.by_title & df.by_dept).sum():>4}")
print(f"  只有岗位名命中  {(df.by_title & ~df.by_dept).sum():>4}   <- 可能是误伤")
print(f"  只有部门命中    {(~df.by_title & df.by_dept).sum():>4}   <- 可能是漏网")

print("\n" + "=" * 74)
print("A · 两者都命中（基本可以确定是 marketing）—— 按岗位名出现次数")
print("=" * 74)
both = df[df.by_title & df.by_dept]
for t, c in collections.Counter(both.title).most_common(45):
    print(f"  {c:>3}  {t[:66]}")
print(f"  ... 共 {both.title.nunique()} 个不同岗位名，{len(both)} 条")

print("\n" + "=" * 74)
print("B · 只有岗位名命中，部门不是 marketing —— 这些要你判断算不算")
print("=" * 74)
only_t = df[df.by_title & ~df.by_dept]
for (t, d), c in collections.Counter(zip(only_t.title, only_t.dept)).most_common(40):
    print(f"  {c:>3}  {t[:48]:<50}[部门: {d[:20]}]")
print(f"  ... 共 {len(only_t)} 条")

print("\n" + "=" * 74)
print("C · 部门是 marketing 但岗位名没命中 —— 这些是漏网的")
print("=" * 74)
only_d = df[~df.by_title & df.by_dept]
for (t, d), c in collections.Counter(zip(only_d.title, only_d.dept)).most_common(40):
    print(f"  {c:>3}  {t[:48]:<50}[部门: {d[:20]}]")
print(f"  ... 共 {len(only_d)} 条")

print("\n" + "=" * 74)
print("D · 雇主自己填的部门名长什么样（前 30，看看口径有多乱）")
print("=" * 74)
for d, c in collections.Counter(df[df.dept != ""].dept).most_common(30):
    print(f"  {c:>4}  {d[:56]}")
print(f"  共 {df.dept.nunique()} 种不同写法，{(df.dept=='').sum()} 条为空")
