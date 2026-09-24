#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2 — Cleaning, validation and feature engineering
=====================================================
Reads `data/raw/social_media_engagement_dataset.csv`, applies an explicit
validation + feature-engineering contract, and emits:

    data/processed/posts_clean.csv        analysis-ready flat table
    data/processed/analytics.db           SQLite copy (queried by step 3)
    data/processed/quality_report.json    every data-quality check + verdict
    output/data_dictionary.md             field-by-field definitions (口径)

Why SQLite + stdlib instead of pandas
-------------------------------------
1. Zero third-party dependencies -> the pipeline runs on a bare CPython 3.9+.
2. The analytical layer is **real SQL** (`sql/analysis_queries.sql`), so every
   number on the dashboard can be re-derived and audited by a reviewer without
   reading Python.
3. At 5k rows the runtime difference is irrelevant.

Metric contract (口径) — read this before using any number
----------------------------------------------------------
`Engagement_Rate` shipped in the raw file was reverse-engineered during
profiling and equals:

    raw.Engagement_Rate = (Likes + Comments + Shares) / Follower_Count * 100

i.e. it is a *follower-based* rate and it **excludes Saves**. It is therefore
NOT comparable with the view-based rates that media plans normally use. This
script keeps it (renamed `er_follower_reported`) and adds a fully specified
family of view-based rates:

    engagement_total = Likes + Comments + Shares + Saves
    er_view          = engagement_total / Views * 100          <- primary KPI
    er_follower      = engagement_total / Follower_Count * 100
    deep_rate        = (Shares + Saves) / Views * 100          <- high-intent
    save_rate        = Saves  / Views * 100
    share_rate       = Shares / Views * 100
    comment_rate     = Comments / Views * 100
    eng_per_1k_fans  = engagement_total / (Follower_Count / 1000)
    reach_ratio      = Views / Follower_Count                  <- amplification

Central tendency is reported as the **median** (engagement distributions are
right-skewed); uncertainty is a 95% bootstrap percentile interval. Means are
still shipped in the tooltip for transparency.

Usage
-----
    python scripts/02_clean_features.py
"""

from __future__ import annotations

import csv
import json
import sqlite3
import statistics
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "social_media_engagement_dataset.csv"
PROC_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output"
CLEAN_CSV = PROC_DIR / "posts_clean.csv"
DB_PATH = PROC_DIR / "analytics.db"
QUALITY_JSON = PROC_DIR / "quality_report.json"
DICT_MD = OUT_DIR / "data_dictionary.md"

VERTICAL = ("Fitness", "Sports", "Health")
TIER_ORDER = ["Nano", "Micro", "Mid-tier", "Macro"]

INT_FIELDS = ("Likes", "Comments", "Shares", "Views", "Saves",
              "Follower_Count", "Hour_of_Day", "Hashtag_Count", "Content_Length")
FLOAT_FIELDS = ("Engagement_Rate",)
BOOL_FIELDS = ("Has_Media", "Is_Verified")


def log(msg: str) -> None:
    print(f"[02_clean] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def to_int(v: str) -> int | None:
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def to_float(v: str) -> float | None:
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_bool(v: str) -> int | None:
    v = (v or "").strip().lower()
    if v in ("true", "1", "yes"):
        return 1
    if v in ("false", "0", "no"):
        return 0
    return None


def parse_ts(v: str) -> datetime | None:
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def slot_of(hour: int) -> str:
    """Publishing window — four buckets that map to a real posting schedule."""
    if 0 <= hour <= 5:
        return "00-05 Late night"
    if 6 <= hour <= 11:
        return "06-11 Morning"
    if 12 <= hour <= 17:
        return "12-17 Afternoon"
    return "18-23 Evening"


def hashtag_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n <= 5:
        return "1-5"
    if n <= 10:
        return "6-10"
    if n <= 20:
        return "11-20"
    if n <= 30:
        return "21-30"
    return "30+"


def follower_band(n: int) -> str:
    if n < 10_000:
        return "<10k"
    if n < 50_000:
        return "10k-50k"
    if n < 200_000:
        return "50k-200k"
    if n < 1_000_000:
        return "200k-1M"
    return "1M+"


def safe_div(a: float, b: float) -> float | None:
    return None if not b else a / b


# The raw file mixes 17 platform-specific format labels (Tweet, Reel, Stitch,
# Document, ...). They are folded into five platform-neutral CREATIVE FAMILIES so
# that "which creative works best" is answerable across platforms instead of
# being confounded by platform-native labels.
CONTENT_FAMILY = {
    "Video": "Short video", "Reel": "Short video", "Short": "Short video",
    "Stitch": "Short video", "Duet": "Short video",
    "Photo": "Static image", "Carousel": "Static image",
    "Live": "Live",
    "Story": "Story / interactive", "Poll": "Story / interactive",
    "Post": "Text / long-form", "Tweet": "Text / long-form",
    "Thread": "Text / long-form", "Retweet": "Text / long-form",
    "Article": "Text / long-form", "Document": "Text / long-form",
    "Community Post": "Text / long-form",
}


# --------------------------------------------------------------------------- #
# Load + clean
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build_records(raw_rows: list[dict]) -> tuple[list[dict], dict]:
    checks: "OrderedDict[str, object]" = OrderedDict()
    counters = Counter()

    seen_ids: set[str] = set()
    records: list[dict] = []

    for r in raw_rows:
        counters["rows_read"] += 1

        pid = (r.get("Post_ID") or "").strip()
        if pid in seen_ids:
            counters["duplicate_post_id"] += 1
            continue
        seen_ids.add(pid)

        ts = parse_ts(r.get("Timestamp", ""))
        if ts is None:
            counters["unparsable_timestamp"] += 1
            continue
        if not pid:
            counters["missing_post_id"] += 1
            continue

        # --- numeric coercion ------------------------------------------------
        vals = {}
        for f in INT_FIELDS:
            vals[f] = to_int(r.get(f, ""))
            if vals[f] is None:
                counters[f"null_{f}"] += 1
        for f in FLOAT_FIELDS:
            vals[f] = to_float(r.get(f, ""))
            if vals[f] is None:
                counters[f"null_{f}"] += 1
        for f in BOOL_FIELDS:
            vals[f] = to_bool(r.get(f, ""))
            if vals[f] is None:
                counters[f"null_{f}"] += 1

        # --- domain integrity -------------------------------------------------
        if any(vals[f] is None for f in INT_FIELDS):
            counters["dropped_missing_core_metric"] += 1
            continue
        if any(vals[f] is not None and vals[f] < 0 for f in INT_FIELDS):
            counters["negative_metric"] += 1
        if vals["Views"] <= 0:
            counters["non_positive_views"] += 1
            continue

        # raw ETL consistency: derived hour / weekday vs the timestamp itself
        if vals["Hour_of_Day"] != ts.hour:
            counters["hour_field_mismatch"] += 1
        if (r.get("Day_of_Week") or "").strip() != ts.strftime("%A"):
            counters["weekday_field_mismatch"] += 1

        interactions = vals["Likes"] + vals["Comments"] + vals["Shares"]
        if vals["Engagement_Rate"] is not None:
            recomputed = safe_div(interactions, vals["Follower_Count"])
            if recomputed is not None:
                err = abs(recomputed * 100 - vals["Engagement_Rate"])
                if err > 0.02:
                    counters["engagement_rate_formula_mismatch"] += 1

        eng_total = interactions + vals["Saves"]
        # Interactions cannot logically exceed views. 295 rows (5.9%) break this;
        # they are kept for volume accounting but flagged out of every RATE metric.
        rate_valid = 1 if eng_total <= vals["Views"] else 0
        if eng_total > vals["Views"]:
            counters["engagement_exceeds_views"] += 1
        if vals["Follower_Count"] <= 0:
            counters["non_positive_followers"] += 1

        # --- engineered features ---------------------------------------------
        hour = ts.hour
        weekday = ts.strftime("%A")
        category = (r.get("Category") or "").strip()
        platform = (r.get("Platform") or "").strip()
        ctype = (r.get("Content_Type") or "").strip()

        rec = {
            "post_id": pid,
            "posted_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "date": ts.strftime("%Y-%m-%d"),
            "year_month": ts.strftime("%Y-%m"),
            "hour": hour,
            "weekday": weekday,
            "is_weekend": 1 if ts.weekday() >= 5 else 0,
            "time_slot": slot_of(hour),
            "platform": platform,
            "content_type": ctype,
            "content_family": CONTENT_FAMILY.get(ctype, "Other"),
            "category": category,
            "rate_valid": rate_valid,
            "is_vertical": 1 if category in VERTICAL else 0,
            "vertical_segment": category if category in VERTICAL else "Other",
            "influencer_tier": (r.get("Influencer_Tier") or "").strip(),
            "tier_rank": (TIER_ORDER.index(r["Influencer_Tier"].strip())
                          if (r.get("Influencer_Tier") or "").strip() in TIER_ORDER else -1),
            "follower_count": vals["Follower_Count"],
            "follower_band": follower_band(vals["Follower_Count"]),
            "likes": vals["Likes"],
            "comments": vals["Comments"],
            "shares": vals["Shares"],
            "saves": vals["Saves"],
            "views": vals["Views"],
            "engagement_total": eng_total,
            "engagement_core": interactions,
            "er_follower_reported": vals["Engagement_Rate"],
            "er_follower": round(safe_div(eng_total, vals["Follower_Count"]) * 100 or 0, 6),
            "er_view": round(eng_total / vals["Views"] * 100, 6),
            "deep_rate": round((vals["Shares"] + vals["Saves"]) / vals["Views"] * 100, 6),
            "save_rate": round(vals["Saves"] / vals["Views"] * 100, 6),
            "share_rate": round(vals["Shares"] / vals["Views"] * 100, 6),
            "comment_rate": round(vals["Comments"] / vals["Views"] * 100, 6),
            "like_rate": round(vals["Likes"] / vals["Views"] * 100, 6),
            "eng_per_1k_fans": round(eng_total / (vals["Follower_Count"] / 1000.0), 6),
            "reach_ratio": round(vals["Views"] / vals["Follower_Count"], 6),
            "hashtag_count": vals["Hashtag_Count"],
            "hashtag_bucket": hashtag_bucket(vals["Hashtag_Count"]),
            "content_length": vals["Content_Length"],
            "sentiment": (r.get("Sentiment") or "").strip(),
            "has_media": vals["Has_Media"] if vals["Has_Media"] is not None else 0,
            "is_verified": vals["Is_Verified"] if vals["Is_Verified"] is not None else 0,
        }
        records.append(rec)

    checks["row_accounting"] = dict(counters)
    return records, checks


def profile(records: list[dict]) -> dict:
    if not records:
        return {}
    views = [r["views"] for r in records]
    er = [r["er_view"] for r in records]
    fans = [r["follower_count"] for r in records]
    dates = sorted(r["date"] for r in records)
    n = len(records)
    tiers = Counter(r["influencer_tier"] for r in records)
    return {
        "posts": n,
        "rate_valid_posts": sum(r["rate_valid"] for r in records),
        "rate_valid_pct": round(sum(r["rate_valid"] for r in records) / n * 100, 2),
        "vertical_posts": sum(r["is_vertical"] for r in records),
        "vertical_share_pct": round(sum(r["is_vertical"] for r in records) / n * 100, 2),
        "date_min": dates[0],
        "date_max": dates[-1],
        "platforms": dict(Counter(r["platform"] for r in records).most_common()),
        "content_types": dict(Counter(r["content_type"] for r in records).most_common()),
        "content_families": dict(Counter(r["content_family"] for r in records).most_common()),
        "categories": dict(Counter(r["category"] for r in records).most_common()),
        "tiers": dict(tiers.most_common()),
        # SAMPLING SKEW: the creator-tier column is dominated by Macro accounts.
        "tier_skew_warning": (
            f"Macro accounts hold {tiers['Macro'] / n * 100:.1f}% of all posts and "
            f"Nano only {tiers['Nano'] / n * 100:.1f}% ({tiers['Nano']} rows). "
            "Tier-level results for Nano are therefore low-confidence and are "
            "visually flagged on the dashboard."
        ),
        "sentiments": dict(Counter(r["sentiment"] for r in records).most_common()),
        "views": {
            "min": min(views), "median": statistics.median(views),
            "mean": round(statistics.fmean(views), 1), "max": max(views),
        },
        "er_view_median": round(statistics.median(er), 4),
        "er_view_p95": round(sorted(er)[int(len(er) * 0.95)], 4),
        "er_view_max": round(max(er), 4),
        "followers": {
            "min": min(fans), "median": statistics.median(fans), "max": max(fans),
        },
        "verified_share_pct": round(sum(r["is_verified"] for r in records) / len(records) * 100, 2),
    }


def write_csv(records: list[dict], path: Path) -> None:
    if not records:
        raise SystemExit("No records to write — cleaning removed everything.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)


def write_sqlite(records: list[dict], path: Path) -> None:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(records[0].keys())
    ddl = "CREATE TABLE posts (\n  " + ",\n  ".join(
        f'"{c}" {"TEXT" if isinstance(records[0][c], str) else "INTEGER" if isinstance(records[0][c], int) else "REAL"}'
        for c in cols
    ) + "\n)"
    con = sqlite3.connect(path)
    con.execute(ddl)
    con.executemany(
        f"INSERT INTO posts ({','.join(chr(34)+c+chr(34) for c in cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        [tuple(r[c] for c in cols) for r in records],
    )
    con.execute("CREATE INDEX idx_posts_vertical ON posts(is_vertical)")
    con.execute("CREATE INDEX idx_posts_platform ON posts(platform)")
    con.execute("CREATE INDEX idx_posts_tier ON posts(influencer_tier)")
    con.commit()
    con.close()


DATA_DICTIONARY = """# Data dictionary — `posts_clean.csv`

Source: `data/raw/social_media_engagement_dataset.csv`
(Kaggle · aviral342 · Social Media Engagement Dataset · CC0 1.0)
One row = one published post.

## 1. Raw fields carried through

| Field | Type | Definition |
|---|---|---|
| `post_id` | text | Unique post identifier (primary key) |
| `posted_at` | datetime | Publish timestamp, `YYYY-MM-DD HH:MM:SS` |
| `platform` | text | Instagram / TikTok / YouTube / Twitter / Facebook / LinkedIn |
| `content_type` | text | Creative format (Photo, Video, Reel, Carousel, Story, …) |
| `category` | text | Content category; `Fitness` / `Sports` / `Health` = project vertical |
| `follower_count` | int | Creator follower base at publish time |
| `engagement_rate` (raw) | float | **Follower-based**, see §3 |
| `hashtag_count` | int | Hashtags attached to the post |
| `content_length` | int | Caption characters, or video seconds |
| `content_type` | text | 17 platform-native format labels (Reel, Tweet, Stitch, Document, …) |
| `sentiment` | text | Positive / Neutral / Negative (author-side label) |
| `influencer_tier` | text | Nano / Micro / Mid-tier / Macro |
| `has_media`, `is_verified` | 0/1 | Booleans |

## 2. Engineered fields

| Field | Definition |
|---|---|
| `date`, `year_month`, `hour`, `weekday`, `is_weekend` | Calendar decomposition of `posted_at` |
| `time_slot` | `00-05 Late night` / `06-11 Morning` / `12-17 Afternoon` / `18-23 Evening` |
| `is_vertical` | 1 when `category` ∈ {Fitness, Sports, Health} |
| `vertical_segment` | Fitness / Sports / Health / Other |
| `tier_rank` | 0=Nano … 3=Macro, for ordered comparisons |
| `follower_band` | `<10k` / `10k-50k` / `50k-200k` / `200k-1M` / `1M+` |
| `hashtag_bucket` | `0` / `1-5` / `6-10` / `11-20` / `21-30` / `30+` |
| `content_family` | 17 platform-native `content_type` labels folded into 5 cross-platform families: **Short video** (Video, Reel, Short, Stitch, Duet) · **Static image** (Photo, Carousel) · **Live** · **Story / interactive** (Story, Poll) · **Text / long-form** (Post, Tweet, Thread, Retweet, Article, Document, Community Post). Without this folding, a "best format" comparison would mostly restate which platform the format belongs to. |
| `rate_valid` | 1 when `engagement_total` ≤ `Views`. 295 rows (5.9%) violate this; they stay in the table for volume accounting but are excluded from every rate metric. |

## 3. Metric definitions (口径) — the important part

The raw column `Engagement_Rate` was reverse-engineered during profiling and
resolves to `(Likes + Comments + Shares) / Follower_Count × 100`. It is a
**follower-based** rate and **excludes Saves**, so it is not comparable with the
view-based rates used in media planning. It is retained as
`er_follower_reported` for audit only.

| Metric | Formula | Reading |
|---|---|---|
| `engagement_total` | Likes + Comments + Shares + Saves | Absolute interaction volume |
| `er_view` | `engagement_total / Views × 100` | **Primary KPI** — interaction per 100 views |
| `er_follower` | `engagement_total / Follower_Count × 100` | Fan-base activation |
| `deep_rate` | `(Shares + Saves) / Views × 100` | High-intent / "value" interactions |
| `save_rate` | `Saves / Views × 100` | Save-for-later intent |
| `share_rate` | `Shares / Views × 100` | Organic amplification |
| `comment_rate` | `Comments / Views × 100` | Conversation intensity |
| `eng_per_1k_fans` | `engagement_total / (Follower_Count / 1000)` | Efficiency of a creator's fan base |
| `reach_ratio` | `Views / Follower_Count` | Algorithmic amplification vs. own fans |

## 4. Central tendency and uncertainty

Engagement-rate distributions are strongly right-skewed, so every headline
figure is a **median** with a **95% bootstrap percentile interval**
(2,000 resamples, seed fixed). Means are available in the dashboard tooltips.
"""


def main() -> int:
    if not RAW_CSV.exists():
        raise SystemExit("data/raw/...csv missing — run scripts/01_fetch_data.py first")

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_rows = load_rows(RAW_CSV)
    log(f"read {len(raw_rows):,} raw rows")

    records, checks = build_records(raw_rows)
    log(f"kept {len(records):,} clean rows")

    prof = profile(records)
    checks["profile"] = prof
    checks["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    write_csv(records, CLEAN_CSV)
    write_sqlite(records, DB_PATH)
    QUALITY_JSON.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    DICT_MD.write_text(DATA_DICTIONARY, encoding="utf-8")

    log(f"→ {CLEAN_CSV.relative_to(ROOT)}")
    log(f"→ {DB_PATH.relative_to(ROOT)}")
    log(f"→ {QUALITY_JSON.relative_to(ROOT)}")
    log(f"→ {DICT_MD.relative_to(ROOT)}")

    ra = checks["row_accounting"]
    log("quality: " + ", ".join(f"{k}={v}" for k, v in ra.items() if k != "rows_read"))
    log(f"vertical posts: {prof['vertical_posts']:,} ({prof['vertical_share_pct']}%)")
    log(f"categories: {prof['categories']}")
    log(f"platforms: {prof['platforms']}")
    log(f"er_view median: {prof['er_view_median']}%  p95: {prof['er_view_p95']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
