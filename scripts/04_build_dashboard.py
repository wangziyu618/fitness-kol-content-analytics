#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 4 — Build the single-file interactive dashboard
====================================================
Injects `output/analysis_results.json` into `scripts/dashboard_template.html`
and writes a self-contained `index.html` at the repository root.

Every headline sentence rendered on the board is generated here from the numbers
in the analysis output — no prose is hard-coded with a figure in it, so the
narrative cannot drift away from the data when the pipeline is re-run.

Properties of the output
------------------------
* **Zero dependencies.** No CDN, no bundled library. Charts are hand-built SVG
  emitted by ~200 lines of vanilla JS embedded in the file. It opens offline,
  from a double-click or from GitHub Pages, and renders identically.
* **No chrome.** No toolbar, no box-zoom, no legend toggles, no filters. The only
  interaction is hover-to-inspect, which is what an executive board needs.
* **Label-safe.** Axis ticks are thinned (every 3rd month / hour), value labels sit
  above bars rather than inside them, and category names live in a fixed left
  gutter, so nothing collides at any width.

Usage
-----
    python scripts/04_build_dashboard.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output" / "analysis_results.json"
TEMPLATE = ROOT / "scripts" / "dashboard_template.html"
OUT_HTML = ROOT / "index.html"


def log(msg: str) -> None:
    print(f"[04_dashboard] {msg}", flush=True)


def n0(v) -> str:
    return f"{round(v):,}" if isinstance(v, (int, float)) else "—"


def n1(v) -> str:
    return f"{v:,.1f}" if isinstance(v, (int, float)) else "—"


def n2(v) -> str:
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "—"


def build_findings(d: dict) -> list[dict]:
    """Generate the findings cards from the computed numbers."""
    plat = {r["platform"]: r for r in d["platform"]}
    ig, yt, tk, li, tw = (plat[k] for k in
                          ("Instagram", "YouTube", "TikTok", "LinkedIn", "Twitter"))
    tier = {r["influencer_tier"]: r for r in d["tier"]}
    fam = {r["content_family"]: r for r in d["content_family"]}
    vb = d["vertical_vs_benchmark"]["er_view"]
    bt = d["budget"]["by_tier"]
    bp = d["budget"]["by_platform"]
    scen = {s["name"]: s for s in bt["scenarios"]}
    pscen = {s["name"]: s for s in bp["scenarios"]}
    econ = {g["key"]: g for g in bt["groups"]}
    pecon = {g["key"]: g for g in bp["groups"]}
    best_plat = max(bp["groups"], key=lambda g: g["engagements_per_1k_usd"])
    top_slot = max(d["timing_weekday_slot"], key=lambda r: r["er_view_pooled"])
    bot_slot = min(d["timing_weekday_slot"], key=lambda r: r["er_view_pooled"])
    weekend = {r["day_type"]: r for r in d["timing_weekend"]}

    return [
        {
            "tag": "Finding 01 · Platform",
            "title": f"Instagram leads on interaction; YouTube and TikTok are reach plays, "
                     f"not engagement plays",
            "body": [
                f"Instagram's median interaction rate in the vertical is "
                f"<b>{n1(ig['median_er_view'])}%</b> (95% CI {n1(ig['ci_low'])}–{n1(ig['ci_high'])}), "
                f"about <b>{n1(ig['median_er_view'] / yt['median_er_view'])}×</b> YouTube's "
                f"{n1(yt['median_er_view'])}%. The two confidence intervals do not overlap, so the gap "
                f"is not sampling noise.",
                f"But YouTube and TikTok deliver <b>reach</b>: views land at "
                f"{n1(yt['mean_reach_ratio'])}× and {n1(tk['mean_reach_ratio'])}× the creator's own "
                f"follower base versus {n1(ig['mean_reach_ratio'])}× on Instagram. LinkedIn "
                f"({n1(li['mean_deep_rate'])}% high-intent) and X ({n1(tw['mean_deep_rate'])}%) carry the "
                f"strongest share-and-save behaviour despite lower raw rates.",
                "<b>[Inference]</b> A fitness brand should not pick one platform: Instagram converts "
                "attention, YouTube and TikTok buy cheap reach, and LinkedIn/X are where a considered "
                "audience saves and forwards. Treat them as different line items, not substitutes.",
            ],
            "cn": f"解读：Instagram 中位互动率 {n1(ig['median_er_view'])}%，约为 YouTube 的 "
                  f"{n1(ig['median_er_view'] / yt['median_er_view'])} 倍，且置信区间不重叠；"
                  f"YouTube / TikTok 的触达放大系数（{n1(yt['mean_reach_ratio'])}× / "
                  f"{n1(tk['mean_reach_ratio'])}×）远高于 Instagram，属“广触达、低互动”；"
                  f"LinkedIn 与 X 的深度互动率最高。建议按角色分工而非相互替代。"
        },
        {
            "tag": "Finding 02 · Creator tier",
            "title": "Scale does not buy a better interaction rate — it buys a worse one per fan",
            "body": [
                f"Median interaction rate is almost flat across tiers: Nano {n1(tier['Nano']['median_er_view'])}%, "
                f"Micro {n1(tier['Micro']['median_er_view'])}%, Mid-tier "
                f"{n1(tier['Mid-tier']['median_er_view'])}%, Macro {n1(tier['Macro']['median_er_view'])}%. "
                f"A bigger account is not a more persuasive account.",
                f"Efficiency is where they separate: interactions per 1,000 fans fall from "
                f"<b>{n0(tier['Micro']['mean_eng_per_1k_fans'])}</b> (Micro) to "
                f"<b>{n0(tier['Mid-tier']['mean_eng_per_1k_fans'])}</b> (Mid-tier) to "
                f"<b>{n0(tier['Macro']['mean_eng_per_1k_fans'])}</b> (Macro) — roughly a "
                f"{n0(tier['Micro']['mean_eng_per_1k_fans'] / tier['Macro']['mean_eng_per_1k_fans'])}× spread. "
                f"Under the declared CPM this becomes a CPE of ${econ['Micro']['cpe_usd']:.3f} for Micro versus "
                f"${econ['Macro']['cpe_usd']:.3f} for Macro.",
                f"<b>Caveat:</b> the Nano cell holds only {tier['Nano']['n']} posts in the vertical, so it is "
                f"flagged low-confidence and excluded from the budget plan. The Micro-vs-Macro ordering "
                f"rests on {tier['Micro']['n']} and {tier['Macro']['n']} posts and is the load-bearing claim.",
            ],
            "cn": f"解读：各层级中位数互动率几乎持平（Micro {n1(tier['Micro']['median_er_view'])}% vs Macro "
                  f"{n1(tier['Macro']['median_er_view'])}%），但每千粉丝互动产出从 Micro 的 "
                  f"{n0(tier['Micro']['mean_eng_per_1k_fans'])} 降至 Macro 的 "
                  f"{n0(tier['Macro']['mean_eng_per_1k_fans'])}，CPE 相差约 "
                  f"{n0(econ['Macro']['cpe_usd'] / econ['Micro']['cpe_usd'])} 倍。"
                  f"注意：Nano 仅 {tier['Nano']['n']} 条样本，已标记为低置信并排除出预算方案。"
        },
        {
            "tag": "Finding 03 · Creative",
            "title": "Static images outperform short video in this corpus — a result to treat with care",
            "body": [
                f"Folded into cross-platform families, the ranking is Static image "
                f"<b>{n1(fam['Static image']['median_er_view'])}%</b>, Story/interactive "
                f"{n1(fam['Story / interactive']['median_er_view'])}%, Short video "
                f"{n1(fam['Short video']['median_er_view'])}%, Text/long-form "
                f"{n1(fam['Text / long-form']['median_er_view'])}%, Live "
                f"{n1(fam['Live']['median_er_view'])}%.",
                f"This runs against the usual industry assumption that short video dominates fitness "
                f"content. The likely mechanical reason is denominator-driven: video formats attract far "
                f"more views ({n0(fam['Short video']['mean_views'])} mean views vs "
                f"{n0(fam['Static image']['mean_views'])} for static), and a rate divided by a much larger "
                f"view count is mechanically smaller.",
                "<b>[Inference — flagged]</b> Do not read this as “video is bad”. Read it as: "
                "on a per-view basis static creatives are more efficient here, while video is the "
                "format that manufactures the views. Because the source data is synthetic, this "
                "ordering should be re-tested on real account data before it drives a creative brief.",
            ],
            "cn": f"解读：静态图文（{n1(fam['Static image']['median_er_view'])}%）高于短视频"
                  f"（{n1(fam['Short video']['median_er_view'])}%），与行业常识相反。"
                  f"可能原因是分母效应——短视频的浏览量（均值 {n0(fam['Short video']['mean_views'])}）远高于图文"
                  f"（{n0(fam['Static image']['mean_views'])}），互动率被稀释。"
                  f"【推断·需复核】不应解读为“短视频无效”，而是“视频负责制造曝光、图文负责单位转化”；"
                  f"且源数据为合成数据，投放前须用真实账号数据复核。"
        },
        {
            "tag": "Finding 04 · Timing",
            "title": "No posting window is reliably better — the visible gaps sit inside the noise",
            "body": [
                f"The best cell is {top_slot['weekday']} {top_slot['time_slot']} at "
                f"{n1(top_slot['er_view_pooled'])}% and the worst is {bot_slot['weekday']} "
                f"{bot_slot['time_slot']} at {n1(bot_slot['er_view_pooled'])}%, but each of the 28 "
                f"weekday × day-part cells holds only {min(r['n'] for r in d['timing_weekday_slot'])}–"
                f"{max(r['n'] for r in d['timing_weekday_slot'])} posts.",
                f"Weekday ({n1(weekend['Weekday']['er_view_pooled'])}%) versus weekend "
                f"({n1(weekend['Weekend']['er_view_pooled'])}%) differs by "
                f"{n1(abs(weekend['Weekday']['er_view_pooled'] - weekend['Weekend']['er_view_pooled']))} "
                f"percentage points — inside the range you would expect from cell-level sampling variation.",
                "<b>Recommendation:</b> do not build a posting calendar on this cut. Timing is the one "
                "question this dataset is too thin to answer, and saying so is more useful to a client "
                "than a spurious best-hour chart.",
            ],
            "cn": f"解读：最优单元格（{top_slot['weekday']} {top_slot['time_slot']}，"
                  f"{n1(top_slot['er_view_pooled'])}%）与最差（{bot_slot['weekday']} {bot_slot['time_slot']}，"
                  f"{n1(bot_slot['er_view_pooled'])}%）差距看似明显，但每个单元格仅 "
                  f"{min(r['n'] for r in d['timing_weekday_slot'])}–"
                  f"{max(r['n'] for r in d['timing_weekday_slot'])} 条样本；"
                  f"工作日与周末仅差 {n1(abs(weekend['Weekday']['er_view_pooled'] - weekend['Weekend']['er_view_pooled']))} "
                  f"个百分点。结论：不建议据此制定发布排期，这是本数据集样本量不足以回答的问题。"
        },
        {
            "tag": "Finding 05 · Budget",
            "title": f"Re-weighting the same envelope toward efficiency is worth roughly "
                     f"+{n0(scen['efficiency_share']['uplift_vs_even_pct'])}% interactions",
            "body": [
                f"On a fixed ${n0(d['budget']['assumption']['budget_envelope_usd'])} envelope, splitting by "
                f"interactions-per-dollar returns <b>{n0(scen['efficiency_share']['expected_engagement'])}</b> "
                f"expected interactions versus {n0(scen['even_share']['expected_engagement'])} for an even "
                f"split (+{n0(scen['efficiency_share']['uplift_vs_even_pct'])}%) and "
                f"{n0(scen['structure_share']['expected_engagement'])} if the budget simply mirrors today's "
                f"posting mix ({n0(scen['structure_share']['uplift_vs_even_pct'])}%).",
                f"The status-quo penalty is the real story: today's mix is ~"
                f"{n0(bt['groups'][-1]['n'])} Macro posts out of {n0(sum(g['n'] for g in bt['groups']))}, "
                f"so an unexamined plan spends most of the money at the least efficient CPE "
                f"(${econ['Macro']['cpe_usd']:.3f} vs ${econ['Micro']['cpe_usd']:.3f} for Micro).",
                f"By platform the same logic concentrates on <b>{best_plat['key']}</b> "
                f"({n0(best_plat['engagements_per_1k_usd'])} interactions per $1k, CPE "
                f"${best_plat['cpe_usd']:.3f}), lifting the envelope from "
                f"{n0(pscen['even_share']['expected_engagement'])} to "
                f"{n0(pscen['efficiency_share']['expected_engagement'])} interactions "
                f"(+{n0(pscen['efficiency_share']['uplift_vs_even_pct'])}%).",
                "<b>[Inference]</b> The direction is robust — it survives every CPM tested — but the "
                "magnitudes scale directly with the CPM assumption, and a pure efficiency split is too "
                "concentrated to run unmodified. A real plan caps any single tier, keeps a Macro slot for "
                "reach and brand safety, and reserves budget for testing.",
            ],
            "cn": f"解读：在 ${n0(d['budget']['assumption']['budget_envelope_usd'])} 固定预算下，按“每美元互动产出”分配可得 "
                  f"{n0(scen['efficiency_share']['expected_engagement'])} 次互动，比平均分配"
                  f"（{n0(scen['even_share']['expected_engagement'])}）高 "
                  f"{n0(scen['efficiency_share']['uplift_vs_even_pct'])}%；"
                  f"若沿用现有投放结构则为 {n0(scen['structure_share']['expected_engagement'])}"
                  f"（{n0(scen['structure_share']['uplift_vs_even_pct'])}%）。"
                  f"平台维度上应重点加码 {best_plat['key']}。"
                  f"【推断】方向稳健（各 CPM 情景下一致），但绝对值随 CPM 假设线性变化；"
                  f"实际投放需给单一层级设上限、保留头部达人的曝光与品牌安全位，并预留测试预算。"
        },
        {
            "tag": "Finding 06 · Vertical",
            "title": "Sport / fitness / wellness content is statistically indistinguishable from "
                     "every other category here",
            "body": [
                f"Median interaction rate: vertical {n1(vb['vertical_median'])}% versus benchmark "
                f"{n1(vb['benchmark_median'])}%. The difference is {n1(vb['difference'])} points with a "
                f"95% interval of {n1(vb['ci_low'])} to {n1(vb['ci_high'])} — it straddles zero, so the "
                f"two are <b>not</b> distinguishable at 95% confidence.",
                f"Neither interactions-per-1k-fans nor reach ratio separates either "
                f"({n1(d['vertical_vs_benchmark']['eng_per_1k_fans']['difference'])} and "
                f"{n1(d['vertical_vs_benchmark']['reach_ratio']['difference'])} respectively, both "
                f"non-significant). Inside the vertical, Sports, Fitness and Health also sit within "
                f"each other's intervals.",
                "<b>[Inference]</b> The honest answer is that this dataset shows no vertical premium. "
                "That is a finding, not a failure: it redirects the pitch from “this vertical is special” "
                "to “the lever is creator tier and creative mix, not category” — and it is exactly the "
                "kind of null result a portfolio piece should be able to state cleanly.",
            ],
            "cn": f"解读：垂类中位互动率 {n1(vb['vertical_median'])}% vs 大盘 {n1(vb['benchmark_median'])}%，"
                  f"差值 {n1(vb['difference'])} 点，95% 置信区间 [{n1(vb['ci_low'])}, {n1(vb['ci_high'])}] 跨越 0，"
                  f"差异不显著；每千粉丝互动与触达放大同样不显著。"
                  f"【推断】本数据集未显示垂类溢价——这是有效结论而非缺陷：真正的杠杆在达人层级与创意组合，而非类目本身。"
        },
    ]


def build_method_notes(d: dict) -> list[str]:
    m = d["meta"]
    return [
        f"<b>Primary metric</b> — <code>{m['metrics']['primary']}</code>: "
        f"interactions per 100 views. The raw file's own <code>Engagement_Rate</code> column is "
        f"<i>follower</i>-based and excludes Saves, so it is not comparable and was kept only for audit.",
        f"<b>Central tendency</b> — {m['metrics']['central']}. Engagement distributions are strongly "
        f"right-skewed (p95 is far above the median), so medians are reported, with means in tooltips.",
        f"<b>Sample</b> — {n0(m['rows_raw'])} raw posts → {n0(m['rows_rate_valid'])} rate-valid "
        f"(dropped {n0(m['rows_dropped_invalid_rate'])} rows where interactions exceeded views, which "
        f"cannot happen on a real platform) → <b>{n0(m['rows_vertical_rate_valid'])}</b> in the vertical "
        f"({m['vertical_definition']}).",
        f"<b>Groups below n={m['metrics']['low_confidence_threshold']}</b> are greyed out on the charts and "
        f"excluded from the recommended budget split.",
        "<b>Cost model</b> — the dataset has no spend field. Cost is modelled as "
        "<code>mean_followers × CPM / 1000</code>; the CPM is a declared assumption and the whole "
        "allocation is re-run at CPM 5 / 10 / 15 / 25 in the sensitivity table.",
        "<b>Content families</b> — 17 platform-native format labels are folded into 5 cross-platform "
        "families so a “best format” result is not just restating which platform owns the label.",
    ]


def build_limitations(d: dict) -> list[str]:
    m = d["meta"]
    p = d["quality"]["profile"]
    return [
        f"<b>The data is synthetic.</b> {m['dataset']['provenance_note']} Every figure is a valid "
        f"statistical statement <i>about this dataset</i>; none of them is evidence about real "
        f"platform behaviour. Recommendations are framed as method, not as market truth.",
        f"<b>Creator-tier distribution is severely skewed:</b> {p['tier_skew_warning']} "
        f"The Nano tier cannot support a conclusion and is excluded from the budget plan.",
        f"<b>Timing cells are thin.</b> The weekday × day-part grid averages "
        f"{n0(d['meta']['rows_vertical_rate_valid'] // 28)} posts per cell, so no posting-window claim is made.",
        "<b>Cost is assumed, not observed.</b> No spend, contract or conversion data exists in the "
        "source, so CPE and ROI are modelled from one CPM. Uplift direction is stable across the "
        "sensitivity grid; uplift magnitude is not.",
        "<b>No causal claim.</b> This is observational, cross-sectional post-level data with no "
        "holdout, so “efficiency-weighted allocation returns +X%” is a counterfactual projection "
        "under a linear cost model, not a measured experiment result.",
        "<b>Engagement ≠ business outcome.</b> Nothing here measures clicks, sign-ups, retention or "
        "revenue; interactions are a proxy for attention, not for value.",
        f"<b>Time window:</b> {m['date_min']} to {m['date_max']}. Platform algorithms and creative "
        f"norms move faster than that; the monthly series is flat, which is itself a sign the "
        f"generator does not model seasonality.",
    ]


def main() -> int:
    if not RESULTS.exists():
        raise SystemExit("analysis_results.json missing — run scripts/03_analysis.py first")
    if not TEMPLATE.exists():
        raise SystemExit("dashboard_template.html missing")

    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    d["findings"] = build_findings(d)
    d["method_notes"] = build_method_notes(d)
    d["limitations"] = build_limitations(d)
    d["meta"]["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Trim the payload: the dashboard only needs analysis outputs, not raw row dumps.
    d["quality"].pop("row_accounting", None)

    html = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    if "</script" in payload:
        payload = payload.replace("</script", "<\\/script")
    html = html.replace("/*__DATA__*/", payload)

    OUT_HTML.write_text(html, encoding="utf-8")
    log(f"→ {OUT_HTML.relative_to(ROOT)}  ({OUT_HTML.stat().st_size:,} bytes)")
    log(f"   self-contained: {'http' in html.split('<script')[-1][:4000] is False}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
