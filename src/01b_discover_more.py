# -*- coding: utf-8 -*-
"""阶段 0b · 把公司名单从 330 扩到约 950。

动机：纽约营销岗只有 290 条，按职级 x 数据要求切完每格 38 条，
统计上站不住。样本量是可以直接买的 —— 多试公司就行。

本轮刻意往纽约密度高的行业倾斜：媒体、广告科技、时尚电商、
金融科技、医疗科技、房产科技、代理商，而不只是湾区 SaaS。

输入  本文件的 MORE 列表 + data/raw/boards.json（跳过已试过的）
输出  data/raw/boards.json（增量更新）
"""
import json, os, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "boards.json")
UA = {"User-Agent": "Mozilla/5.0 (academic job-posting research; contact marcoplam0506@gmail.com)"}
ENDPOINTS = [
    ("greenhouse", "https://boards-api.greenhouse.io/v1/boards/{}/jobs"),
    ("ashby",      "https://api.ashbyhq.com/posting-api/job-board/{}"),
    ("lever",      "https://api.lever.co/v0/postings/{}?mode=json"),
]

MORE = """
nytimes vox vice buzzfeed theatlantic bustle axios semafor puck theinformation defector
hearst condenast vimeo patreon substack beehiiv ghost medium wondery iheartmedia audacy
spotify siriusxm pandora soundcloud bandcamp splice landr output
criteo taboola outbrain tripleliftinc magnite pubmatic indexexchange sharethrough
mediaocean innovid doubleverify integralads iab basis quantcast lotame liveramp
amplitude braze iterable attentive klaviyo cordial blueshift movableink
sailthru listrak bluecore insider emarsys
stackadapt viant zeta madhive tvscientific roku samba
shopify bigcommerce commercetools fabric swell bolt fastspring recharge loop
mirakl rithum channeladvisor salsify akeneo syndigo
glossier warbyparker everlane reformation mejuri brilliantearth
quince italic cuyana parachute brooklinen casper purple saatva
hims ro curology musely agency
peloton tonal hydrow mirror lululemon gymshark alo
chewy barkbox ollie thefarmersdog jinx
hellofresh blueapron factor freshly homechef sunbasket
instacart gopuff getir imperfectfoods thrivemarket misfitsmarket
seatgeek stubhub vividseats dice eventbrite resident bandsintown
classpass mindbody equinox barrys solidcore
oscar devoted clover alignment carehealth
cedar zocdoc kry carbonhealth onemedical forward parsley
spring headway alma talkspace cerebral lyrahealth modernhealth
komodohealth tempus flatiron aledade vim turquoisehealth
ro hims nurx wisp simplehealth
betterment wealthfront acorns stash public robinhood webull etoro
marqeta lithic highnote unit synctera treasuryprime
current varo dave moneylion chime
petal mission upgrade avant happymoney achieve
blend roostify maxwell staircase
pagaya upstart prosper lendingclub
alloy persona socure sardine unit21 sentilink
ocrolus plaid finicity mx yodlee
addepar altruist betterment orion advyzon
carta pulley ltse angellist
ramp brex navan expensify airbase mesh center
tipalti stampli bill melio routable
mercury relay found novo bluevine
clearco pipe capchase arc levelpath
openview insightpartners firstmark lerer
attentive postscript emotive community klaviyo
yotpo okendo stamped junip
gorgias kustomer gladly front intercom ada forethought
assembled asapp cresta observe level
zendesk freshworks helpscout hiver
clay apollo lusha seamless zoominfo cognism
gong chorus outreach salesloft
mutiny unbounce instapage leadpages webflow
semrush ahrefs moz conductor brightedge seoclarity botify
similarweb sensortower apptopia appfigures
sprout hootsuite later buffer sproutsocial planoly dash iconosquare
brandwatch meltwater cision muckrack prowly
tagger captiv8 grin aspire creatoriq izea
mediavine raptive adthrive playwire
vidmob vidyard wistia loom descript opus kapwing veed
canva figma frame picsart photoroom
later linktree beacons stanstore
patreon kofi gumroad lemonsqueezy
podium birdeye yotpo trustpilot bazaarvoice powerreviews
narvar aftership route shippo easypost shipbob stord flexe
deliverr shipmonk shipstation
flexport projectfortyfour convoy loadsmart transfix
samsara motive geotab zonar lytx
afresh crisp shelfengine
toast olo tattle presto sevenrooms resy opentable
wonder slutty cava sweetgreen dig
compass opendoor orchard homelight ribbon
pacaso vacasa sonder inspirato placemakr
latch smartrent brivo verkada
procore buildertrend levelset billd
openspace doxel buildots
gusto rippling deel remote oyster velocityglobal papayaglobal
lattice culture15five leapsome charthop pave assemble
greenhouse lever ashby ashbyhq workable breezy
handshake wellfound otta mercor
pelago spring equipt
wayup jumpstart ripplematch
splash hopin bizzabo swapcard cvent brella
luma partiful posh dice
mural miro figjam lucid whimsical
notion coda slab guru tettra
airtable smartsheet monday clickup asana wrike basecamp
dropbox box egnyte
grammarly writer jasper copyai anyword
hubspot pardot act marketo eloqua
sprinklr khoros emplifi dash
contentful sanity storyblok prismic strapi payload
wordpress automattic ghost squarespace wix webflow duda
vercel netlify cloudflare fastly akamai
datadog newrelic sentry honeycomb grafanalabs
"""
CANDIDATES = sorted(set(MORE.split()))


def probe(url, timeout=12):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            if r.status != 200:
                return None
            d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    jobs = d.get("jobs") if isinstance(d, dict) else (d if isinstance(d, list) else None)
    return len(jobs) if jobs else None


def main():
    found = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [c for c in CANDIDATES if c not in found]
    print(f"新候选 {len(CANDIDATES)}，其中没试过的 {len(todo)}（已有记录 {len(found)}）\n")
    for i, slug in enumerate(todo, 1):
        hit = None
        for ats, tmpl in ENDPOINTS:
            n = probe(tmpl.format(slug))
            time.sleep(0.22)
            if n:
                hit = {"ats": ats, "jobs": n}
                break
        found[slug] = hit
        if i % 40 == 0 or i == len(todo):
            ok = sum(1 for v in found.values() if v)
            tot = sum(v["jobs"] for v in found.values() if v)
            print(f"  {i}/{len(todo)}   累计命中 {ok} 家 / {tot:,} 条岗位")
            json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = {k: v for k, v in found.items() if v}
    by = {}
    for v in ok.values():
        by[v["ats"]] = by.get(v["ats"], 0) + 1
    print(f"\n总计命中 {len(ok)} / {len(found)} 家 ({len(ok)/len(found)*100:.0f}%)")
    print("  按 ATS:", by)
    print(f"  岗位总数 {sum(v['jobs'] for v in ok.values()):,}")


if __name__ == "__main__":
    main()
