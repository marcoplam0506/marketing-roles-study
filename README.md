# Does data fluency pay in marketing?

Short answer: not in the raw numbers, and that turned out to be the interesting part.

Across **367 marketing roles at 95 New York employers**, jobs that demand hard data
skills pay **+3.3%** more than jobs that don't — with a 95% bootstrap interval of
**[−$11,553, +$17,645]**. The interval crosses zero. Four sensitivity checks move
the estimate by less than a point and none of them clears zero either.

Then the same comparison, run inside each marketing function:

| Function | Data required | Not required | Gap |
|---|---|---|---|
| Other Marketing | $217,500 | $163,625 | +32.9% |
| Brand & Creative | $224,050 | $177,462 | +26.3% |
| Content & Social | $173,400 | $139,000 | +24.7% |
| Field & Partner | $206,475 | $178,012 | +16.0% |
| Growth & Performance | $176,500 | $157,700 | +11.9% |
| Product Marketing | $188,575 | $184,675 | +2.1% |

Six functions with enough data on both sides. Six positive gaps.

Both things are true because **the functions that demand data sit at the cheap end of
marketing**. Comms & PR asks it of no role and pays a median of $211,000, the highest
of nine. Marketing Ops asks it of every role and pays $165,500, eighth of nine. Compare
everyone at once and the two effects cancel.

Put function in the model and the premium comes back:

| Model | Coefficient on data skills | 95% CI | |
|---|---|---|---|
| Data skills alone | +7.2% | [−0.9%, +15.4%] | crosses zero |
| Hold seniority equal | +6.3% | [−1.5%, +14.7%] | crosses zero |
| Hold seniority and function equal | **+11.1%** | **[+2.4%, +21.4%]** | **clears zero** |

Textbook Simpson's paradox, in live job postings.

One more number for scale: sitting one level up is worth **+$54,250**, CI
[+$31,250, +$83,479] — about nine times the raw data gap, and its interval does not
cross zero.

---

## The finding I trust most

Data fluency is **a property of the function, not the rank**.

| Cut the same measure by | Highest | Lowest | Spread |
|---|---|---|---|
| Seniority | Leadership 40.7% | Senior 37.3% | **3.3 points** |
| Function | Marketing Ops 100% | Comms & PR 5% | **95 points** |

Twenty-nine times wider. The seniority cells hold 158 / 150 / 59 roles, so this is not
a small-sample artefact. "The more senior you get, the more you need to read data"
is not visible in this market at all.

---

## Where the data comes from

Public job-board APIs — Greenhouse, Ashby, Lever — read straight from each company's
own board:

```
https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true
https://api.lever.co/v0/postings/{company}?mode=json
```

704 candidate companies probed, 339 reachable, 27,078 postings pulled, 4,260 of them
in New York.

No LinkedIn and no Indeed. Both forbid scraping, both ban accounts for it, and neither
can be re-run by someone checking my work. An ATS endpoint can.

New York only, and on purpose. The city's pay-transparency law (Local Law 32) is why
**82.5%** of these postings carry a salary band at all; nationally it is closer to half.
The cost is that the finding stops at the city line.

---

## Running it

```bash
pip install pandas numpy scipy
python src/01_discover_boards.py     # which companies have a reachable board
python src/02_fetch_raw.py           # pull every posting  (writes data/raw, ~33 MB)
python src/06_build_table.py         # one row per posting, salary parsed
python src/09_classify.py            # is this a marketing role, and which kind
python src/10_label.py               # does it require data skills, and at what level
python src/11_analyze.py             # the question list, with bootstrap intervals
python src/12_regression.py          # the Simpson's paradox, quantified
python src/13_story_numbers.py       # the numbers behind the write-up
```

`data/raw/` is not committed — `02_fetch_raw.py` rebuilds it. Everything downstream of
it is in the repo, so you can re-run the analysis without re-fetching.

---

## Three traps worth knowing about

**Lever hides pay in the legal boilerplate.** I had excluded `additionalPlain` from the
text used for labelling, because it is full of equal-opportunity language that would
trigger every keyword. That same section is where Lever employers put the pay
disclosure. One correct decision was serving two conflicting purposes, and Lever
contributed zero salaries until I split the labelling text from the salary text.

**Free-text pay needs a sanity check, not a regex.** Real strings in this data:
`$180-$220k` (the "k" applies to both numbers), `deal sizes range from $200K to $1M`
(not a salary at all), `$112,000 - $140,00 CAD` (employer typo, wrong currency). The
parser checks magnitude, currency, and whether salary words appear nearby, and declines
to guess when they don't.

**Keyword labels find phrases, not requirements.** `dbt` matched "dbt Labs" in a
company's own blurb. `analytics` matched "partner with Analytics" — the name of a
neighbouring team, not a skill being asked for. Every keyword hit is written to
`data/interim/03_label_audit.csv` with 130 characters of context either side, which is
how all three defects surfaced.

---

## What this cannot tell you

1. Pay is the **midpoint of a posted range**. Where a real offer lands inside that range
   is invisible here.
2. **Small cells at the extremes.** Comms & PR holds 16 roles, Marketing Ops 14. The two
   ends of the cancellation sit on the two smallest groups.
3. Functions were assigned by **title rules I wrote**, not by employers. Three
   misclassifications were found and fixed by audit; nobody else has checked them.
4. The result says data-heavy roles are **priced** higher inside a function. It does not
   say that learning the skill raises an individual's pay.
5. **A snapshot**, pulled October–November 2026. No trend.

`docs/decisions.md` carries every call made along the way, with dates, and the full list
of open questions.

---

Marco Lam · [pingting-lam](https://www.linkedin.com/in/pingting-lam/) · New York City
