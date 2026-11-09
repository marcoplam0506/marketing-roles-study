# -*- coding: utf-8 -*-
"""阶段 0 · 找出哪些公司的 ATS 公开接口是通的。

方法：拿一批候选公司名（slug），依次试 Greenhouse / Ashby / Lever，
通了就记下来。结果增量写盘，中断也不丢。

输入  本文件内的 CANDIDATES 列表
输出  data/raw/boards.json
"""
import json, os, sys, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "boards.json")
UA = {"User-Agent": "Mozilla/5.0 (academic job-posting research; contact marcoplam0506@gmail.com)"}

ENDPOINTS = [
    ("greenhouse", "https://boards-api.greenhouse.io/v1/boards/{}/jobs"),
    ("ashby",      "https://api.ashbyhq.com/posting-api/job-board/{}"),
    ("lever",      "https://api.lever.co/v0/postings/{}?mode=json"),
]

CANDIDATES = """
openai anthropic scale huggingface runwayml perplexityai cohere mistral togetherai replicate
weightsandbiases labelbox databricks datarobot adept sierra decagon writer glean harvey
vercel netlify render railway supabase planetscale neon docker hashicorp gitlab sourcegraph
linear sentry launchdarkly circleci postman retool airbyte dbtlabs prefect dagster temporal
grafanalabs chronosphere honeycomb pulumi warp replit codeium cursor
ramp brex mercury plaid marqeta affirm chime betterment wealthfront robinhood gemini coinbase
circle alloy unit moderntreasury lithic column stripe adyen checkr persona middesk
notion figma airtable asana monday clickup miro canva loom calendly zapier webflow framer
coda pitch slab superhuman shortwave missive height tability
vanta drata snyk 1password tailscale cloudflare crowdstrike abnormalsecurity wiz orca semgrep
socket chainguard sublime material huntress dragos claroty
snowflake fivetran hightouch census amplitude mixpanel heap posthog segment rudderstack
metabase hex sigmacomputing omni mode preset starburst clickhouse timescale cockroachlabs
duolingo spotify strava peloton whoop oura headspace calm bumble hinge discord reddit
pinterest twitch patreon substack medium vimeo cameo masterclass skillshare
shopify faire whatnot etsy instacart doordash gopuff misfitsmarket thrivemarket warbyparker
allbirds glossier away rothys figs chewy wayfair carvana
oscar devoted carbonhealth ro hims cedar komodohealth tempus flatiron included spring
headway alma grow talkiatry
gusto rippling deel remote lattice cultureamp greenhouse lever ashbyhq klaviyo braze iterable
attentive postscript customerio amplemarket clay apollo outreach gong chili
flexport samsara motive nuro zoox lyft lime via turo getaround
opendoor compass divvyhomes roofstock pacaso
roblox discord epicgames unity scopely dreamhaven
watershed arcadia crusoe redwoodmaterials pachama nowrx
openphone front intercom zendesk gitpod resend knock liveblocks clerk workos stytch
benchling verkada appliedintuition anduril palantir shieldai skydio zipline
airbnb lime grammarly descript elevenlabs synthesia opus captions
segment twilio sendbird agora daily mux cloudinary imgix
brexhq modernhealth lyra sondermind
applovin liftoff moloco adjust branch appsflyer amplitude
sprout hootsuite later buffer sproutsocial planoly dash
webflow squarespace wix duda unbounce
hubspot zoominfo clearbit 6sense demandbase drift qualified
mailchimp constantcontact activecampaign omnisend yotpo
cj impact partnerize everflow
smartly skai pacvue perpetua teikametrics
nielsen comscore similarweb semrush ahrefs moz
tubi plex roku vizio
instacart shipt gopuff getir
affirm klarna afterpay sezzle
truebill rocketmoney copilot monarch
notion airtable smartsheet wrike basecamp
"""
CANDIDATES = sorted(set(CANDIDATES.split()))


def probe(url, timeout=14):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if isinstance(d, dict):
        jobs = d.get("jobs")
    elif isinstance(d, list):
        jobs = d
    else:
        jobs = None
    return len(jobs) if jobs else None


def main():
    found = {}
    if os.path.exists(OUT):                      # 支持中断续跑
        found = json.load(open(OUT, encoding="utf-8"))
    todo = [c for c in CANDIDATES if c not in found]
    print(f"候选 {len(CANDIDATES)} 家，待试 {len(todo)} 家\n")

    for i, slug in enumerate(todo, 1):
        hit = None
        for ats, tmpl in ENDPOINTS:
            n = probe(tmpl.format(slug))
            time.sleep(0.25)
            if n:
                hit = {"ats": ats, "jobs": n}
                break
        found[slug] = hit                        # 没通也记下来，避免重复试
        if i % 25 == 0 or i == len(todo):
            ok = sum(1 for v in found.values() if v)
            tot = sum(v["jobs"] for v in found.values() if v)
            print(f"  进度 {i}/{len(todo)}  已命中 {ok} 家 / 共 {tot} 条岗位")
            json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = {k: v for k, v in found.items() if v}
    by = {}
    for v in ok.values():
        by[v["ats"]] = by.get(v["ats"], 0) + 1
    print(f"\n命中 {len(ok)} / {len(found)} 家  ({len(ok)/len(found)*100:.0f}%)")
    print("  按 ATS:", by)
    print(f"  岗位总数 {sum(v['jobs'] for v in ok.values()):,}")
    print(f"  已写出 {OUT}")


if __name__ == "__main__":
    main()
