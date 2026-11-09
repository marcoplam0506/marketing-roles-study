# -*- coding: utf-8 -*-
"""阶段 0 · 把 198 家公司的岗位原样抓下来。

刻意不做任何清洗、不做筛选、不改字段名。
原始数据只读、永不修改 —— 后面任何一步出错都能回到这里重来。
抓全部岗位（不只 marketing），因为"marketing 占招聘总量多少"需要分母。

输入  data/raw/boards.json
输出  data/raw/{ats}.json.gz   {公司: 接口原样返回}
"""
import gzip, json, os, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = {"User-Agent": "Mozilla/5.0 (academic job-posting research; contact marcoplam0506@gmail.com)"}

# 带参数的版本：Greenhouse 要 content=true 才给正文，Ashby 要 includeCompensation=true 才给薪资
FULL = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=true",
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{}?includeCompensation=true",
    "lever":      "https://api.lever.co/v0/postings/{}?mode=json",
}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    boards = json.load(open(os.path.join(RAW, "boards.json"), encoding="utf-8"))
    live = {k: v for k, v in boards.items() if v}
    by_ats = {}
    for slug, info in live.items():
        by_ats.setdefault(info["ats"], []).append(slug)

    for ats, slugs in by_ats.items():
        path = os.path.join(RAW, f"{ats}.json.gz")
        store = {}
        if os.path.exists(path):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                store = json.load(f)
        todo = [s for s in slugs if s not in store]
        print(f"\n{ats}: {len(slugs)} 家，待抓 {len(todo)} 家")

        for i, slug in enumerate(todo, 1):
            try:
                store[slug] = fetch(FULL[ats].format(slug))
            except Exception as e:
                print(f"  失败 {slug}: {str(e)[:60]}")
                store[slug] = None
            time.sleep(0.5)
            if i % 20 == 0 or i == len(todo):
                with gzip.open(path, "wt", encoding="utf-8") as f:
                    json.dump(store, f, ensure_ascii=False)
                print(f"  {i}/{len(todo)}")

        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
        n = 0
        for v in store.values():
            if not v:
                continue
            jobs = v.get("jobs") if isinstance(v, dict) else v
            n += len(jobs or [])
        mb = os.path.getsize(path) / 1048576
        print(f"  完成 {ats}: {n:,} 条岗位, {mb:.1f} MB -> {path}")


if __name__ == "__main__":
    main()
