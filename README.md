# Sport · Fitness · Wellness — Content &amp; KOL Marketing Analytics

> **中文简介**：面向「运动 / 健身 / 健康」垂类的内容营销与 KOL 营销数据分析作品集项目。
> 使用**单个公开数据集**，完成「数据获取 → 清洗与特征工程 → 多维分析（SQL）→ 交互式看板 → 策略建议 → 工程化交付」的完整链路。
> 与任何实习经历完全独立，代码可复现、数据可核查、结论均标注来源与置信度。

**🔗 Interactive dashboard · 在线交互式看板：**
**https://wangziyu618.github.io/fitness-kol-content-analytics/**

---

## 1. What this project answers · 项目回答的业务问题

| # | Business question | 业务问题 |
|---|---|---|
| 1 | Which platform actually earns interaction per view? | 哪个平台的单位浏览互动效率最高？ |
| 2 | Do bigger creators justify bigger fees? | 头部达人是否配得上更高的报价？ |
| 3 | Which creative family performs best cross-platform? | 哪类创意形式在跨平台口径下最优？ |
| 4 | Is there a posting window worth scheduling around? | 是否存在值得排期的发布时段？ |
| 5 | How should a fixed budget be split across tiers / platforms? | 预算固定时，如何在层级与平台间分配？ |
| 6 | Is the sport/fitness vertical actually different? | 运动健康垂类是否真的与其他类目不同？ |

The short answers: **Instagram** leads on interaction; **scale does not buy a better rate** (it buys a
worse one per fan); **static image** leads per view (flagged — see limitations); **no reliable posting
window** (sample too thin); **efficiency-weighted allocation is worth ≈ +60% / +84%**; and **the
vertical is statistically indistinguishable from the rest of the corpus**.

---

## 2. Dataset · 数据来源（唯一）

| | |
|---|---|
| **Name** | [Social Media Engagement Dataset](https://www.kaggle.com/datasets/aviral342/social-media-engagement-dataset) |
| **Publisher** | aviral342 (Kaggle) |
| **License** | **CC0 1.0 (Public Domain)** — safe to redistribute and publish |
| **Grain** | one row = one published post |
| **Size** | 5,000 rows × 20 columns, 651 KB |
| **Coverage** | 2024-01-01 → 2025-12-31 · 6 platforms · 12 content categories |
| **Access** | `https://www.kaggle.com/api/v1/datasets/download/aviral342/social-media-engagement-dataset` — **no API key required** (CC0 datasets are served unauthenticated) |
| **Pinned** | SHA256 recorded in `data/raw/MANIFEST.json` on every run |

**Why this one dataset.** It is the smallest public source that still carries every dimension a brand
needs at a single grain: platform, creator tier, creative format, publish timestamp, follower base and
the full interaction breakdown. The vertical is isolated with
`category ∈ (Fitness, Sports, Health)` → **1,115 posts**.

> ⚠️ **The Kaggle card states the data is synthetically generated.** Every figure in this project is a
> valid statistical statement *about this dataset*; none is evidence about real platform behaviour.
> The project is positioned as transferable **method**, not market truth. See
> [`docs/strategy_report.md` §6](docs/strategy_report.md) — this caveat is repeated in the README, the
> report and the dashboard footer, because it should never be buried.

<details>
<summary><b>Field definitions · 字段口径</b></summary>

| Field | Definition |
|---|---|
| `Platform` | Instagram / TikTok / YouTube / X / Facebook / LinkedIn |
| `Influencer_Tier` | Nano / Micro / Mid-tier / Macro |
| `Content_Type` | 17 platform-native labels, folded into 5 cross-platform families (see below) |
| `Follower_Count` | Creator follower base at publish time |
| `Likes / Comments / Shares / Saves / Views` | Interaction counts |

**Content families** (engineered): `Short video` (Video, Reel, Short, Stitch, Duet) ·
`Static image` (Photo, Carousel) · `Live` · `Story / interactive` (Story, Poll) ·
`Text / long-form` (Post, Tweet, Thread, Retweet, Article, Document, Community Post).
Without this folding, a "best format" ranking mostly restates which platform owns the label.

**Metric contract.** The raw `Engagement_Rate` column resolves to
`(Likes + Comments + Shares) / Follower_Count × 100` — a *follower*-based rate that **excludes Saves**.
It is not comparable with view-based media rates, so it is kept for audit only and the project defines
its own: `er_view = (Likes + Comments + Shares + Saves) / Views × 100`.
Full dictionary: [`output/data_dictionary.md`](output/data_dictionary.md).

</details>

---

## 3. Headline findings · 核心发现

1. **Platform is a role, not a rank.** Instagram 22.3% median interaction rate vs YouTube 2.5%
   (non-overlapping CIs), but YouTube reaches 6.6× the creator's own follower base. LinkedIn and X
   carry the highest share-and-save rates.
   *中文：平台应按"角色"分工——Instagram 负责互动，YouTube / TikTok 负责触达，LinkedIn / X 负责深度互动。*
2. **Scale does not buy a better rate.** Median rates are flat across tiers (Micro 10.6% vs Macro
   10.7%), but interactions per 1,000 fans fall from 358 → 37. Under a declared $10 CPM that is
   **$0.033 vs $0.320 CPE** — a 9.7× spread.
   *中文：规模不提升互动率，但显著降低单位粉丝效率，CPE 相差近 10 倍。*
3. **Reallocation is worth more than extra budget.** On a fixed $100k envelope: efficiency-weighted
   split **+59.5%** interactions vs an even split, while mirroring today's posting mix costs **−57.3%**.
   By platform, efficiency-weighting returns **+84.1%**.
4. **No reliable posting window.** Best cell (Thu morning, 12.18%) vs worst (Sun 00-05, 5.00%) rests on
   ~40 posts per cell. Reported as *unanswerable with this data* rather than answered spuriously.
5. **No vertical premium.** All three comparison metrics (interaction rate, interactions per 1k fans,
   reach ratio) have 95% bootstrap intervals straddling zero. A clean null result, stated as such.

---

## 4. Repository structure · 仓库结构

```
.
├── index.html                    ← GitHub Pages entry = the interactive dashboard (self-contained)
├── README.md                     ← this file (EN + 中文)
├── docs/
│   └── strategy_report.md        ← findings, budget recommendations, limitations
├── scripts/
│   ├── 01_fetch_data.py          ← download + SHA256-pin the dataset
│   ├── 02_clean_features.py      ← validate, clean, engineer features, build SQLite warehouse
│   ├── 03_analysis.py            ← run SQL, bootstrap CIs, budget model
│   ├── 04_build_dashboard.py     ← inject results into the template → index.html
│   ├── dashboard_template.html   ← presentation layer (vanilla JS + hand-built SVG)
│   └── run_all.py                ← one-command pipeline
├── sql/
│   └── analysis_queries.sql      ← 15 named analytical queries (the audit trail)
├── data/
│   ├── raw/                      ← source CSV + MANIFEST.json (checksum, provenance)
│   └── processed/                ← posts_clean.csv · analytics.db · quality_report.json
└── output/
    ├── analysis_results.json     ← everything the dashboard renders
    ├── analysis_tables/*.csv     ← one CSV per query
    └── data_dictionary.md        ← field + metric definitions
```

---

## 5. Run it · 运行方式

```bash
python scripts/run_all.py
```

Equivalently, step by step:

```bash
python scripts/01_fetch_data.py      # download + checksum-pin
python scripts/02_clean_features.py  # clean + feature engineering + SQLite
python scripts/03_analysis.py        # SQL + bootstrap + budget model
python scripts/04_build_dashboard.py # → index.html
```

**Requirements: Python 3.9+ and nothing else.** No pandas, no numpy, no plotting library, no network
beyond the one dataset download. This is a deliberate choice:

1. **Reproducibility** — a bare CPython can run the whole pipeline; there is no version-conflict or
   offline-install failure mode for a reviewer.
2. **Auditability** — the analytical layer is *real SQL* in `sql/analysis_queries.sql`, executable in
   any SQLite shell, so every number can be checked without reading Python.
3. **Deliverability** — the dashboard ships as one self-contained HTML file with hand-built SVG, so it
   renders identically offline, from a double-click, or from GitHub Pages.

`requirements.txt` therefore lists no third-party packages.

---

## 6. Method notes · 方法说明

* **Central tendency:** engagement distributions are strongly right-skewed, so headline figures are
  **medians** with a **95% bootstrap percentile interval** (B = 2,000, fixed seed → deterministic).
  Means are available in dashboard tooltips.
* **Confidence gating:** any group with **n < 50** is greyed out on the charts and excluded from the
  recommended allocation. Only the Nano tier (n = 16) trips this.
* **Data quality:** 295 rows (5.9%) had interactions exceeding views — physically impossible on a real
  platform — and are excluded from all rate metrics (flagged as `rate_valid = 0`, retained for volume
  accounting). Full results in `data/processed/quality_report.json`.
* **Sampling skew:** Macro accounts hold 79.9% of all posts and Nano 1.9%. This is surfaced prominently
  rather than smoothed over, and a continuous follower-band cut is provided as a cross-check.
* **Statistical honesty:** the vertical-vs-benchmark comparison is a bootstrap test on the *difference
  of medians*; because all three intervals straddle zero, no vertical effect is claimed.

### The one assumption · 唯一的外生假设

The dataset has **no spend column**. Cost is modelled as
`cost_per_post = mean_followers × CPM / 1000` with CPM = $10 USD, and the **entire allocation is
re-run at CPM 5 / 10 / 15 / 25** in the sensitivity table. Because cost is linear in CPM, relative
efficiency — and therefore the *direction and ranking* — is invariant to the assumption; only absolute
interaction counts scale.

---

## 7. Dashboard design · 看板设计

* **Zero dependencies** — no CDN, no bundled chart library. Charts are hand-built SVG; opens offline.
* **Restrained interaction** — hover-to-inspect only. No toolbar, no box-zoom, no legend toggles,
  no filters. Nothing to get lost in.
* **Label-safe** — axis ticks thinned (every 3rd month/hour), value labels placed above bars rather
  than inside them, category names in a fixed left gutter. No overlap at any width.
* **Light, quiet UI** — Apple / OpenAI-style minimalism: hairline dividers, generous whitespace, one
  accent colour. Bilingual: English labels with Chinese explanation underneath.
* **Every narrative sentence is generated from the data** — `04_build_dashboard.py` builds the findings
  text from `analysis_results.json`, so prose cannot drift away from the numbers when re-run.

---

## 8. Limitations · 局限性

1. **The data is synthetic.** Findings are about this dataset, not about real platform behaviour.
2. **Creator-tier distribution is severely skewed** (Macro 79.9%, Nano 1.9%); Nano is excluded from the
   budget plan.
3. **Timing cells are thin** (~40 posts each); no posting-window claim is made.
4. **Cost is assumed, not observed** — direction robust, magnitude not.
5. **No causal claim** — observational cross-sectional data with no holdout.
6. **Engagement ≠ business outcome** — no clicks, conversions or revenue in the source.
7. **No seasonality** — the 24-month series is flat, so no trend claim is made either.
8. **Single dataset, no triangulation.**

Full discussion: [`docs/strategy_report.md` §6](docs/strategy_report.md).

---

## 9. Skills demonstrated · 能力覆盖

`data acquisition & provenance pinning` · `SQL aggregation & window functions` ·
`data cleaning & validation` · `feature engineering` · `bootstrap inference` ·
`unit-economics / budget modelling` · `sensitivity analysis` ·
`data visualisation (hand-built SVG)` · `front-end delivery (GitHub Pages)` ·
`technical writing (EN + 中文)` · `stating null results honestly`

---

## License

Project code: **MIT**. Source dataset: **CC0 1.0** (public domain, Kaggle / aviral342).
