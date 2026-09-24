#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3 — Multidimensional analysis
==================================
Runs `sql/analysis_queries.sql` against the SQLite warehouse, adds bootstrap
uncertainty, and derives the budget-allocation model. Emits:

    output/analysis_results.json        everything the dashboard renders
    output/analysis_tables/*.csv        one CSV per query, for audit

Two things this script does that SQL alone cannot
-------------------------------------------------
1. **Uncertainty.** Engagement rates are right-skewed, so the headline figure is
   the median. A 95% bootstrap percentile interval (B=2,000, fixed seed) is
   attached to every group median, and groups with n < 100 are flagged
   `low_confidence` so the dashboard can grey them out.
2. **The cost side.** The dataset has no spend column. Rather than inventing a
   price list, the model applies ONE openly declared assumption — a CPM — and
   then tests how sensitive the recommendation is to it (CPM 5 / 10 / 15 / 25
   USD). The derivation is data-driven; the input is an assumption, and it is
   labelled as such everywhere it appears.

    cost_per_post(tier)  = mean_followers(tier) * CPM / 1000
    engagements_per_usd  = mean_engagement_per_post(tier) / cost_per_post(tier)
    CPE                  = 1 / engagements_per_usd

Budget scenarios compared on a fixed 100,000 USD envelope
    * `structure_share` — mirror today's posting mix (status quo)
    * `even_share`      — split the envelope equally
    * `efficiency_share`— weight by engagements per USD

Usage
-----
    python scripts/03_analysis.py
"""

from __future__ import annotations

import csv
import json
import random
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "analytics.db"
SQL_PATH = ROOT / "sql" / "analysis_queries.sql"
QUALITY_JSON = ROOT / "data" / "processed" / "quality_report.json"
MANIFEST = ROOT / "data" / "raw" / "MANIFEST.json"
OUT_DIR = ROOT / "output"
TABLE_DIR = OUT_DIR / "analysis_tables"
RESULTS = OUT_DIR / "analysis_results.json"

# --------------------------------------------------------------------------- #
# Declared assumptions — every one is surfaced in the dashboard and the report
# --------------------------------------------------------------------------- #
CPM_DEFAULT = 10.0            # USD per 1,000 followers reached (single-post deal)
CPM_SCENARIOS = (5.0, 10.0, 15.0, 25.0)
BUDGET_ENVELOPE = 100_000.0   # USD, fixed across every scenario
BOOTSTRAP_B = 2_000
BOOTSTRAP_SEED = 20240924
# A group median needs ~50 observations before its bootstrap CI is stable enough
# to plan money against. Below that the cell is greyed out on the dashboard and
# excluded from the recommended allocation. (Only the Nano tier, n=16, trips this.)
LOW_N = 50

TIER_ORDER = ["Nano", "Micro", "Mid-tier", "Macro"]


def log(msg: str) -> None:
    print(f"[03_analysis] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# SQL runner
# --------------------------------------------------------------------------- #
def parse_named_sql(path: Path) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    name, buf = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- @name:"):
            if name:
                blocks.append((name, "\n".join(buf).strip()))
            name, buf = line.split(":", 1)[1].strip(), []
        elif name:
            buf.append(line)
    if name:
        blocks.append((name, "\n".join(buf).strip()))
    return blocks


def run_sql(con: sqlite3.Connection) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for name, sql in parse_named_sql(SQL_PATH):
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        out[name] = rows
        TABLE_DIR.mkdir(parents=True, exist_ok=True)
        with (TABLE_DIR / f"{name}.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        log(f"{name}: {len(rows)} rows")
    return out


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
def bootstrap_median_ci(values: list[float], b: int = BOOTSTRAP_B,
                        seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    """95% percentile interval for the median. Deterministic via fixed seed."""
    n = len(values)
    if n < 8:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    meds = []
    for _ in range(b):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        sample.sort()
        mid = n // 2
        meds.append(sample[mid] if n % 2 else (sample[mid - 1] + sample[mid]) / 2)
    meds.sort()
    lo = meds[int(0.025 * b)]
    hi = meds[min(int(0.975 * b), b - 1)]
    return (round(lo, 4), round(hi, 4))


def bootstrap_diff_ci(a: list[float], b: list[float], b_n: int = BOOTSTRAP_B,
                      seed: int = BOOTSTRAP_SEED) -> tuple[float, float, float]:
    """
    Bootstrap the difference of two medians (a - b).
    Returns (point_estimate, ci_low, ci_high). If the interval straddles 0 the
    two groups are NOT distinguishable at 95% confidence — which is exactly the
    verdict the report needs before claiming any 'vertical premium'.
    """
    rng = random.Random(seed)
    na, nb = len(a), len(b)
    diffs = []
    for _ in range(b_n):
        sa = sorted([a[rng.randrange(na)] for _ in range(na)])
        sb = sorted([b[rng.randrange(nb)] for _ in range(nb)])
        ma = sa[na // 2] if na % 2 else (sa[na // 2 - 1] + sa[na // 2]) / 2
        mb = sb[nb // 2] if nb % 2 else (sb[nb // 2 - 1] + sb[nb // 2]) / 2
        diffs.append(ma - mb)
    point = statistics.median(a) - statistics.median(b)
    diffs.sort()
    return (round(point, 4),
            round(diffs[int(0.025 * b_n)], 4),
            round(diffs[min(int(0.975 * b_n), b_n - 1)], 4))


def vertical_vs_benchmark(con: sqlite3.Connection) -> dict:
    """Is the sport/fitness vertical actually different from the rest of the corpus?"""
    def pull(scope_sql: str, col: str) -> list[float]:
        return [r[0] for r in con.execute(
            f"SELECT {col} FROM posts WHERE rate_valid = 1 AND {scope_sql}")]

    out = {}
    for col, label in (("er_view", "median_er_view"),
                       ("eng_per_1k_fans", "median_eng_per_1k_fans"),
                       ("reach_ratio", "median_reach_ratio")):
        v = pull("is_vertical = 1", col)
        b = pull("is_vertical = 0", col)
        pt, lo, hi = bootstrap_diff_ci(v, b)
        out[col] = {
            "vertical_median": round(statistics.median(v), 4),
            "benchmark_median": round(statistics.median(b), 4),
            "difference": pt,
            "ci_low": lo,
            "ci_high": hi,
            "significant_95": 1 if (lo > 0 or hi < 0) else 0,
            "n_vertical": len(v),
            "n_benchmark": len(b),
        }
    return out


def attach_ci(con: sqlite3.Connection, rows: list[dict], key: str,
              metric: str = "er_view") -> list[dict]:
    """Add median / mean / 95% CI / n / low-confidence flag to grouped rows."""
    cache: dict[str, list[float]] = {}
    q = f"SELECT {key}, {metric} FROM posts WHERE is_vertical = 1 AND rate_valid = 1"
    for k, v in con.execute(q):
        cache.setdefault(k, []).append(v)

    for row in rows:
        vals = cache.get(row[key], [])
        if not vals:
            continue
        vals_sorted = sorted(vals)
        row["n"] = len(vals_sorted)
        row["median_er_view"] = round(statistics.median(vals_sorted), 4)
        row["mean_er_view"] = round(statistics.fmean(vals_sorted), 4)
        lo, hi = bootstrap_median_ci(vals_sorted)
        row["ci_low"] = lo
        row["ci_high"] = hi
        row["low_confidence"] = 1 if len(vals_sorted) < LOW_N else 0
    return rows


# --------------------------------------------------------------------------- #
# Budget model
# --------------------------------------------------------------------------- #
def build_budget(rows: list[dict], key: str, cpm: float) -> dict:
    """
    rows must carry: key, n, mean_followers, mean_engagement_per_post.
    Returns per-group economics plus three allocation scenarios.
    """
    groups = []
    for r in rows:
        cost = (r["mean_followers"] or 0) * cpm / 1000.0
        eng = r["mean_engagement_per_post"] or 0.0
        epd = eng / cost if cost else 0.0
        groups.append({
            "key": r[key],
            "n": r["n"],
            "mean_followers": r["mean_followers"],
            "cost_per_post": round(cost, 2),
            "mean_engagement": round(eng, 1),
            "engagements_per_1k_usd": round(epd * 1000, 1),
            "cpe_usd": round(1 / epd, 4) if epd else None,
            "low_confidence": r.get("low_confidence", 0),
        })

    total_n = sum(g["n"] for g in groups) or 1
    total_epd = sum(g["engagements_per_1k_usd"] for g in groups) or 1

    def scenario(name: str, weights: dict[str, float]) -> dict:
        expected = 0.0
        detail = []
        for g in groups:
            share = weights.get(g["key"], 0.0)
            spend = BUDGET_ENVELOPE * share
            posts = spend / g["cost_per_post"] if g["cost_per_post"] else 0.0
            eng = posts * g["mean_engagement"]
            expected += eng
            detail.append({
                "key": g["key"],
                "share_pct": round(share * 100, 1),
                "spend_usd": round(spend, 0),
                "posts_bought": round(posts, 1),
                "expected_engagement": round(eng, 0),
            })
        return {"name": name, "expected_engagement": round(expected, 0), "detail": detail}

    # The plan is built over an ELIGIBLE SET = groups with n >= LOW_N, so all
    # three scenarios compete on the same set and their comparison is like-for-like.
    # An unfiltered split is reported separately as an indicative upper bound, never
    # as the recommendation: it would park most of the envelope on the noisiest cell.
    elig = [g for g in groups if not g["low_confidence"]] or groups
    elig_n = sum(g["n"] for g in elig) or 1
    elig_epd = sum(g["engagements_per_1k_usd"] for g in elig) or 1

    scenarios = [
        scenario("structure_share", {g["key"]: g["n"] / elig_n for g in elig}),
        scenario("even_share", {g["key"]: 1 / len(elig) for g in elig}),
        scenario("efficiency_share",
                 {g["key"]: g["engagements_per_1k_usd"] / elig_epd for g in elig}),
        scenario("efficiency_share_unfiltered",
                 {g["key"]: g["engagements_per_1k_usd"] / total_epd for g in groups}),
    ]
    for s in scenarios:
        s["eligible_only"] = 0 if s["name"] == "efficiency_share_unfiltered" else 1
    base = scenarios[1]["expected_engagement"] or 1
    for s in scenarios:
        s["uplift_vs_even_pct"] = round((s["expected_engagement"] - base) / base * 100, 1)

    return {
        "cpm": cpm,
        "budget_usd": BUDGET_ENVELOPE,
        "groups": groups,
        "eligible_groups": [g["key"] for g in elig],
        "excluded_groups": [g["key"] for g in groups if g["low_confidence"]],
        "scenarios": scenarios,
        "recommended": "efficiency_share",
        "recommended_note": (
            "Efficiency-weighted, restricted to groups with at least "
            f"{LOW_N} posts ({', '.join(g['key'] for g in elig)}). "
            "'efficiency_share_unfiltered' is an indicative upper bound only — it "
            "leans on cells too thin to plan money against."
        ),
    }


def cpm_sensitivity(rows: list[dict], key: str) -> list[dict]:
    """Re-run the allocation at several CPMs — the one assumption in the model."""
    out = []
    for cpm in CPM_SCENARIOS:
        res = build_budget(rows, key, cpm)
        best = res["scenarios"][3]
        even = res["scenarios"][1]
        top = max((g for g in res["groups"] if not g["low_confidence"]),
                  key=lambda g: g["engagements_per_1k_usd"])
        out.append({
            "cpm": cpm,
            "best_group": top["key"],
            "best_engagements_per_1k_usd": top["engagements_per_1k_usd"],
            "best_cpe_usd": top["cpe_usd"],
            "efficiency_expected_engagement": best["expected_engagement"],
            "even_expected_engagement": even["expected_engagement"],
            "uplift_pct": best["uplift_vs_even_pct"],
        })
    return out


def derive_budget_rows(con: sqlite3.Connection, table: list[dict], key: str) -> list[dict]:
    """Budget inputs need ALL rows (not only rate_valid), plus an n flag."""
    enriched = []
    for r in table:
        enriched.append({
            key: r[key],
            "n": r["n"],
            "mean_followers": r["mean_followers"],
            "mean_engagement_per_post": r["mean_engagement_per_post"],
            "low_confidence": 1 if r["n"] < LOW_N else 0,
        })
    return enriched


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit("analytics.db missing — run scripts/02_clean_features.py first")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)

    results = run_sql(con)

    # --- uncertainty + confidence flags -------------------------------------
    for name, key in (("q02_platform", "platform"),
                      ("q03_tier", "influencer_tier"),
                      ("q04_content_family", "content_family"),
                      ("q11_segment", "vertical_segment"),
                      ("q15_follower_band", "follower_band")):
        attach_ci(con, results[name], key)

    # --- budget models -------------------------------------------------------
    tier_rows = derive_budget_rows(con, results["q09_budget_tier"], "influencer_tier")
    plat_rows = derive_budget_rows(con, results["q10_budget_platform"], "platform")
    budget = {
        "assumption": {
            "cpm_usd_per_1k_followers": CPM_DEFAULT,
            "formula": "cost_per_post = mean_followers * CPM / 1000",
            "budget_envelope_usd": BUDGET_ENVELOPE,
            "note": ("The dataset contains no spend column. Cost is modelled from a "
                     "single declared CPM; the sensitivity grid below re-runs the "
                     "whole allocation at CPM 5 / 10 / 15 / 25 USD."),
        },
        "by_tier": build_budget(tier_rows, "influencer_tier", CPM_DEFAULT),
        "by_platform": build_budget(plat_rows, "platform", CPM_DEFAULT),
        "cpm_sensitivity_tier": cpm_sensitivity(tier_rows, "influencer_tier"),
        "cpm_sensitivity_platform": cpm_sensitivity(plat_rows, "platform"),
    }

    # --- assemble ------------------------------------------------------------
    quality = json.loads(QUALITY_JSON.read_text(encoding="utf-8")) if QUALITY_JSON.exists() else {}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

    vertical_scope = next((r for r in results["q01_overview"] if r["scope"] == "vertical"), {})
    bench_scope = next((r for r in results["q01_overview"] if r["scope"] == "benchmark"), {})
    comparison = vertical_vs_benchmark(con)
    log("vertical vs benchmark (median difference, 95% CI):")
    for k, v in comparison.items():
        log(f"   {k:<16} Δ={v['difference']:>8}  CI=[{v['ci_low']},{v['ci_high']}]  "
            f"significant={bool(v['significant_95'])}")

    payload = {
        "meta": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "dataset": {
                "name": manifest.get("dataset"),
                "publisher": manifest.get("publisher"),
                "permalink": manifest.get("permalink"),
                "license": manifest.get("license"),
                "sha256": manifest.get("sha256"),
                "provenance_note": manifest.get("provenance_note"),
            },
            "vertical_definition": "category IN (Fitness, Sports, Health)",
            "rows_raw": quality.get("profile", {}).get("posts"),
            "rows_rate_valid": quality.get("profile", {}).get("rate_valid_posts"),
            "rows_dropped_invalid_rate": (
                quality.get("profile", {}).get("posts", 0)
                - quality.get("profile", {}).get("rate_valid_posts", 0)
            ),
            "rows_vertical": quality.get("profile", {}).get("vertical_posts"),
            "rows_vertical_rate_valid": vertical_scope.get("posts"),
            "date_min": quality.get("profile", {}).get("date_min"),
            "date_max": quality.get("profile", {}).get("date_max"),
            "metrics": {
                "primary": "er_view = (Likes+Comments+Shares+Saves) / Views * 100",
                "central": "median, with 95% bootstrap percentile CI (B=2000, seed fixed)",
                "low_confidence_threshold": LOW_N,
            },
            "tier_skew_warning": quality.get("profile", {}).get("tier_skew_warning"),
        },
        "overview": {"vertical": vertical_scope, "benchmark": bench_scope},
        "vertical_vs_benchmark": comparison,
        "platform": results["q02_platform"],
        "tier": results["q03_tier"],
        "content_family": results["q04_content_family"],
        "content_type_detail": results["q05_content_type_detail"],
        "timing_weekday_slot": results["q06_timing_weekday_slot"],
        "timing_hour": results["q07_timing_hour"],
        "timing_weekend": results["q08_timing_weekend"],
        "segment": results["q11_segment"],
        "hashtag": results["q12_hashtag"],
        "monthly": results["q13_monthly_trend"],
        "verified": results["q14_verified"],
        "follower_band": results["q15_follower_band"],
        "budget": budget,
        "quality": {
            "row_accounting": quality.get("row_accounting", {}),
            "profile": quality.get("profile", {}),
        },
    }

    RESULTS.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"→ {RESULTS.relative_to(ROOT)}")

    # Console digest — the numbers that will appear in the report.
    log("--- platform (median er_view %) ---")
    for r in payload["platform"]:
        log(f"   {r['platform']:<10} n={r['n']:>4}  median={r['median_er_view']:>6}  "
            f"CI=[{r['ci_low']},{r['ci_high']}]  deep={r['mean_deep_rate']}")
    log("--- tier ---")
    for r in payload["tier"]:
        log(f"   {r['influencer_tier']:<9} n={r['n']:>4}  median={r['median_er_view']:>6}  "
            f"eng/1k fans={r['mean_eng_per_1k_fans']}")
    log("--- content family ---")
    for r in payload["content_family"]:
        log(f"   {r['content_family']:<22} n={r['n']:>4}  median={r['median_er_view']:>6}")
    log("--- budget (tier, CPM=10) ---")
    for g in budget["by_tier"]["groups"]:
        log(f"   {g['key']:<9} cost/post=${g['cost_per_post']:>9,.0f}  "
            f"CPE=${g['cpe_usd']:>6}  eng/1k$={g['engagements_per_1k_usd']}")
    for s in budget["by_tier"]["scenarios"]:
        log(f"   scenario {s['name']:<16} expected_engagement={s['expected_engagement']:,.0f} "
            f"({s['uplift_vs_even_pct']:+}% vs even)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
