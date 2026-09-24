# Strategy Report — Sport / Fitness / Wellness Content & KOL Marketing

> **中文说明**：本文是与交互式看板配套的策略报告。所有数字均由仓库内的脚本重新计算得出，
> 未使用任何外部或主观数据。凡属推断（而非直接观测）的结论，均以 **[Inference / 推断]** 显式标注。
> 英文为主、中文为解释，便于直接用于海外岗位申请材料。

**Scope** · `category ∈ (Fitness, Sports, Health)` · 2024-01-01 → 2025-12-31 (24 months)
**Sample** · 5,000 raw posts → 4,705 rate-valid → **1,115 in-vertical posts**
**Source** · [Social Media Engagement Dataset](https://www.kaggle.com/datasets/aviral342/social-media-engagement-dataset)
(aviral342, Kaggle, CC0 1.0) — the single public dataset used by this project.

---

## 1. Executive summary · 摘要

Five things a marketing lead needs from this analysis:

1. **Platform role, not platform ranking.** Instagram converts attention
   (median 22.3 interactions per 100 views); YouTube and TikTok manufacture cheap reach but convert
   poorly per view. They are different budget lines, not substitutes.
   *中文：平台应按"角色"分工，而非简单排序。*
2. **Creator scale does not buy a better interaction rate.** Median rates are flat across tiers
   (Micro 10.6% vs Macro 10.7%), but interactions per 1,000 fans collapse from 358 (Micro) to 37 (Macro).
   *中文：达人规模不提升互动率，但显著降低单位粉丝产出效率。*
3. **Re-weighting the same budget toward efficiency is worth ≈ +60% interactions by tier and ≈ +84% by
   platform.** The bigger number is the *penalty* for doing nothing: mirroring today's posting mix costs
   −57% against an even split. *中文：优化分配可显著提升互动量；沿用现状的代价更大。*
4. **No reliable best posting window exists in this data.** Cell sizes are ~40 posts; the observed
   weekday/weekend gap is 0.5 points. *中文：本数据不足以支撑发布时段结论。*
5. **The vertical is statistically indistinguishable from other categories.** All three comparison
   metrics have confidence intervals straddling zero. *中文：垂类并未表现出可辨识的差异。*

---

## 2. Headline metrics · 核心指标口径

| Metric | Definition | Why it matters |
|---|---|---|
| `er_view` | (Likes + Comments + Shares + Saves) / Views × 100 | Primary KPI — interaction per 100 views |
| `deep_rate` | (Shares + Saves) / Views × 100 | High-intent behaviour, closest thing to "value" here |
| `eng_per_1k_fans` | engagement_total / (Followers / 1000) | How hard an account activates its own audience |
| `reach_ratio` | Views / Followers | Algorithmic amplification beyond the creator's own fans |
| `CPE` | modelled cost per interaction | The only cost-aware number, and the one that drives allocation |

**A cleaning finding worth stating up front.** The raw file ships an `Engagement_Rate` column that
resolves to `(Likes + Comments + Shares) / Follower_Count × 100` — a *follower*-based rate that
**excludes Saves**. It is not comparable with the view-based rates used in media planning. It is kept
as `er_follower_reported` for audit, and every headline number in this report uses the view-based
definition instead. *中文：原始数据的互动率字段口径与行业习惯不同（基于粉丝、且不含收藏），已在清洗阶段单独处理。*

---

## 3. Findings · 核心发现

### 3.1 Platform — three different jobs · 平台：三种不同的分工

| Platform | n | Median `er_view` | 95% CI | Reach × | Deep rate | Eng / 1k fans |
|---|---:|---:|---|---:|---:|---:|
| Instagram | 271 | **22.34%** | 20.04 – 24.12 | 0.49× | 3.54% | 79.5 |
| Facebook | 227 | 12.23% | 10.67 – 13.42 | 0.37× | 3.37% | 44.5 |
| TikTok | 177 | 10.58% | 9.44 – 11.98 | 2.51× | 2.43% | **302.8** |
| LinkedIn | 97 | 9.82% | 7.93 – 10.92 | 0.14× | **4.28%** | 11.6 |
| X (Twitter) | 239 | 8.05% | 7.14 – 8.95 | 0.61× | **4.51%** | 43.1 |
| YouTube | 104 | 2.51% | 2.22 – 3.14 | **6.62×** | 1.68% | 151.5 |

Instagram's interval does not overlap YouTube's — the gap is real inside this dataset. But the
rank flips depending on the objective: **YouTube reaches 6.6× the creator's own follower base** while
converting only 2.5% of views, and **LinkedIn / X carry the highest share-and-save rates** despite the
lowest raw interaction rates.

**[Inference / 推断]** Treat the platform set as a portfolio: Instagram for interaction, YouTube +
TikTok for reach volume, LinkedIn + X for considered audiences who save and forward. A single
"best platform" answer would be wrong for three of these objectives.

### 3.2 Creator tier — flat rate, collapsing efficiency · 达人层级：互动率持平，单位效率坍缩

| Tier | n | Median `er_view` | 95% CI | Eng / 1k fans | Cost / post (CPM $10) | CPE |
|---|---:|---:|---|---:|---:|---:|
| Nano | 16 ⚠ | 9.10% | 5.70 – 10.95 | 1,969 | $58 | $0.006 |
| Micro | 98 | 10.63% | 8.27 – 13.53 | 358 | $303 | $0.033 |
| Mid-tier | 107 | **12.23%** | 10.79 – 15.65 | 119 | $754 | $0.091 |
| Macro | 894 | 10.66% | 9.94 – 11.63 | 37 | $2,994 | $0.320 |

⚠ **Nano is excluded from the budget plan**: 16 posts is far too thin to plan money against.

Median interaction rate is essentially flat (a 1.6-point spread across tiers, with overlapping
intervals). The separation is in efficiency: **Micro delivers ~9.7× more interactions per 1,000 fans
than Macro**, and under the declared CPM that is a **9.7× lower CPE**.

**[Inference / 推断]** Macro accounts are not overpriced per interaction *because* they are bad — they
are priced for reach and brand safety. The finding is that if the objective is interaction volume on a
fixed budget, the long tail wins decisively and the default "buy the biggest account" reflex is the
single most expensive habit in the plan.

### 3.3 Creative format — a counter-intuitive result, flagged · 创意形式：反直觉结论（已标注）

| Creative family | n | Median `er_view` | 95% CI | Mean views |
|---|---:|---:|---|---:|
| Static image (Photo, Carousel) | 126 | **22.25%** | 18.47 – 24.68 | 28,341 |
| Story / interactive | 214 | 11.41% | 9.79 – 13.58 | 38,094 |
| Short video (Video, Reel, Short, Stitch, Duet) | 362 | 10.91% | 9.92 – 12.49 | 214,082 |
| Text / long-form | 328 | 8.81% | 7.92 – 10.15 | 76,440 |
| Live | 85 | 7.97% | 5.86 – 11.21 | 197,134 |

17 platform-native format labels were folded into 5 cross-platform families first — otherwise a
"best format" ranking mostly restates which platform owns the label (Reel → Instagram, Tweet → X).

**[Inference / 推断 — treat with care]** Static image leads on a *per-view* basis, which contradicts
the usual assumption that short video dominates fitness content. The mechanical explanation is the
denominator: short video attracts ~7.6× the mean views of static posts (214,082 vs 28,341), so a rate
divided by a much larger view count is smaller by construction. Read it as *"video manufactures the views, static converts
them more efficiently"* — **not** as *"video is ineffective"*. Because the source data is synthetic,
this ordering must be re-tested on real account data before it drives a creative brief.

### 3.4 Publishing timing — the honest answer is "no answer" · 发布时机：诚实的答案是“无法回答”

Best cell: Thursday 06-11 at 12.18% (n=34). Worst: Sunday 00-05 at 5.00% (n=31). The 28 weekday ×
day-part cells hold 31–51 posts each. Weekday (8.03%) vs weekend (7.48%) is a 0.55-point gap.

**Recommendation: do not build a posting calendar on this cut.** This is the one business question the
dataset is too thin to answer, and reporting a spurious "best hour" would be worse than reporting
nothing. *中文：样本量不足以支撑时段结论，明确说明比给出虚假最佳时段更有价值。*

### 3.5 Secondary signals · 次级信号

* **Hashtags:** a weak inverted-U. 6–10 tags → 9.44% pooled `er_view`; 0 tags → 6.09%; 11–20 → 7.33%.
  More tags past ~10 buy nothing. *(n=31 for the zero-tag cell — direction only.)*
* **Verification:** verified accounts 6.64% vs unverified 8.34% pooled `er_view`. The badge does not
  buy engagement here, consistent with larger accounts being less efficient per fan.

---

## 4. Budget allocation · 预算与投放建议

### 4.1 The one assumption · 唯一的假设

The dataset has **no spend column**. Rather than invent a price list, cost is modelled from a single
declared input and then stress-tested:

```
cost_per_post = mean_followers × CPM / 1000        CPM default $10 USD
engagements_per_USD = mean_engagement_per_post / cost_per_post
CPE = 1 / engagements_per_USD
```

Everything else in this section is derived from the data. **The CPM is an assumption; the uplift
direction survives every value tested, the uplift magnitude does not.**

### 4.2 Unit economics (CPM $10) · 单位经济（CPM $10）

| Tier | Cost / post | Mean interactions | Eng / $1k | CPE |
|---|---:|---:|---:|---:|
| Micro | $303 | 9,169 | 30,258 | **$0.033** |
| Mid-tier | $754 | 8,256 | 10,950 | $0.091 |
| Macro | $2,994 | 9,364 | 3,127 | $0.320 |

| Platform | Cost / post | Mean interactions | Eng / $1k | CPE |
|---|---:|---:|---:|---:|
| TikTok | $2,638 | 28,619 | 10,850 | **$0.092** |
| YouTube | $2,770 | 13,796 | 4,980 | $0.201 |
| Instagram | $2,335 | 5,658 | 2,423 | $0.413 |
| Facebook | $2,497 | 5,194 | 2,080 | $0.481 |
| X (Twitter) | $2,420 | 3,955 | 1,635 | $0.612 |
| LinkedIn | $2,624 | 1,476 | 562 | $1.778 |

Note the split verdict: **Instagram has the best rate, TikTok has the best cost-per-interaction.**
They answer different questions and both belong in the plan.

### 4.3 Scenarios on a fixed $100,000 envelope · 固定 10 万美元预算下的方案对比

| Scenario | Creator-tier split | Expected interactions | vs even split |
|---|---|---:|---:|
| Status-quo mix *(mirror today's posting structure)* | 9% Micro · 10% Mid · 81% Macro | 630,826 | **−57.3%** |
| Even split | 33% / 33% / 33% | 1,477,850 | — |
| **Efficiency-weighted (recommended)** | **68% Micro · 25% Mid · 7% Macro** | **2,357,561** | **+59.5%** |

| Scenario | Platform split | Expected interactions | vs even split |
|---|---|---:|---:|
| Status-quo mix | mirrors posting volume | 359,853 | −4.2% |
| **Efficiency-weighted (recommended)** | **TikTok 48% · YouTube 22% · Instagram 11% · Facebook 9% · X 7% · LinkedIn 3%** | **691,130** | **+84.1%** |

### 4.4 Executable recommendations · 可执行建议

1. **Move the tier mix, not the total.** Shift from ~81% Macro to roughly **68% Micro / 25% Mid-tier /
   7% Macro**. The 7% Macro share is deliberate — it is retained for reach, brand safety and
   anchor-creator value, not because it is efficient.
   *中文：调整层级结构而非总额，保留 7% 头部预算用于曝光与品牌安全。*
2. **Set a hard cap per tier (e.g. 70%).** A pure efficiency split concentrates unrealistically;
   the model's +782% "unfiltered" figure includes the 16-post Nano cell and is shown in the dashboard
   only as an indicative upper bound, never as a plan.
   *中文：效率分配需设上限，避免把预算压到小样本分组上。*
3. **Split the platform budget by objective.** ~48% TikTok + ~22% YouTube for reach volume,
   ~20% Instagram/Facebook for interaction quality, ~10% LinkedIn/X for high-intent saves and shares.
4. **Do not buy on follower count alone.** In this data, follower count is close to uninformative about
   interaction rate (flat across tiers) and strongly *negative* about efficiency. Brief creators on
   `eng_per_1k_fans`, not on reach.
   *中文：不要仅按粉丝量采买；应以"每千粉丝互动产出"作为筛选指标。*
5. **Reserve 10–15% for testing.** Every number here is observational and cross-sectional. The
   efficient split is a hypothesis to validate with a real campaign, not a setting to lock.
6. **Re-run this pipeline on the client's own export before committing money.** The scripts take one
   command and need no third-party packages; the CPM is the only input to change.

### 4.5 Sensitivity · 敏感性

Re-running the entire allocation at CPM 5 / 10 / 15 / 25 USD:

* Best tier by CPE is **Mid-tier** at every CPM tested; best platform is **TikTok** at every CPM.
* The tier uplift stays **+59.5%** and the platform uplift **+84.1%** across the whole grid.

Because cost is linear in CPM, *relative* efficiency — and therefore the **direction and ranking** —
is invariant to the assumption. Only absolute interaction counts scale.
*中文：成本随 CPM 线性变化，因此"方向与排序"对假设稳健，绝对量不稳健。*

---

## 5. Vertical comparison · 垂类对比

| Metric | Vertical median | Benchmark median | Difference | 95% CI | Significant? |
|---|---:|---:|---:|---|---|
| `er_view` | 10.89% | 11.36% | −0.47 | −1.27 to +0.38 | **No** |
| `eng_per_1k_fans` | 26.42 | 25.07 | +1.35 | −1.90 to +4.46 | **No** |
| `reach_ratio` | 0.214 | 0.213 | +0.001 | −0.021 to +0.030 | **No** |

All three intervals straddle zero. Inside the vertical, Sports (11.44%), Fitness (11.06%) and Health
(10.30%) also sit inside each other's intervals.

**[Inference / 推断]** There is no vertical premium in this dataset. That is a finding, not a failure:
it moves the pitch from *"this category is special"* to *"the levers are creator tier and creative
mix, not category"*. Being able to state a clean null result is part of the deliverable.
*中文：本数据集未显示垂类溢价；真正的杠杆在达人层级与创意组合，而非类目本身。*

---

## 6. Limitations · 局限性

1. **The data is synthetic.** The Kaggle card states the records are synthetically generated and
   "platform-realistic". Every figure is a valid statistical statement *about this dataset*; none is
   evidence about real platform behaviour. Recommendations are framed as transferable **method**, not
   as market truth. This is the most important caveat in the project and it is repeated on the
   dashboard, in the README and here.
2. **Creator-tier distribution is severely skewed.** Macro accounts hold 79.9% of all posts and Nano
   only 1.9% (97 rows; 16 in the vertical). Nano is excluded from the budget plan.
3. **Timing cells are thin.** ~40 posts per weekday × day-part cell; no posting-window claim is made.
4. **Cost is assumed, not observed.** No spend, contract or conversion data exists in the source.
   CPE and uplift are modelled from one CPM. Direction is stable; magnitude is not.
5. **No causal claim.** Observational, cross-sectional post-level data with no holdout. The
   "+59.5%" is a counterfactual projection under a linear cost model, not a measured experiment.
6. **Engagement ≠ business outcome.** Nothing here measures clicks, sign-ups, retention or revenue.
   Interactions are a proxy for attention, not for value.
7. **295 rows (5.9%)** had interactions exceeding views and are excluded from all rate metrics.
8. **No seasonality.** The 24-month series is flat, which suggests the generator does not model
   seasonality — so no trend claim is made either.
9. **Single dataset, no triangulation.** Findings are not cross-validated against a second source.

---

## 7. Reproducing every number · 复现方式

```bash
python scripts/01_fetch_data.py      # download + SHA256-pin the dataset
python scripts/02_clean_features.py  # clean, engineer features, build SQLite warehouse
python scripts/03_analysis.py        # run sql/analysis_queries.sql + bootstrap + budget model
python scripts/04_build_dashboard.py # emit the single-file dashboard
# or simply:
python scripts/run_all.py
```

Per-query CSV outputs land in `output/analysis_tables/`, so any figure in this report can be checked
against a file without running Python.
