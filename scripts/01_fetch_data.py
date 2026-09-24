#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1 — Data acquisition
=========================
Downloads the **single** public dataset used by this project and pins it with a
checksum manifest so that every run is verifiable and reproducible.

Dataset
-------
Name        : Social Media Engagement Dataset
Publisher   : aviral342 (Kaggle)
Permalink   : https://www.kaggle.com/datasets/aviral342/social-media-engagement-dataset
License     : CC0 1.0 (Public Domain)  -> safe to redistribute / publish
Granularity : one row = one social media post
Rows        : 5,000   Columns: 20
Coverage    : 2024-01-01 .. 2025-12-31, 6 platforms, 12 content categories

Why this dataset
----------------
It is the smallest public dataset that still carries **every dimension a brand
needs for KOL / content-marketing decisions** in one grain:

  * platform            -> Platform            (Instagram / TikTok / YouTube / ...)
  * creator scale       -> Influencer_Tier     (Nano / Micro / Mid-tier / Macro)
  * creative format     -> Content_Type        (Reel / Video / Photo / Carousel / ...)
  * publishing timing   -> Timestamp, Hour_of_Day, Day_of_Week
  * media spend proxy   -> Follower_Count      (drives the CPM cost model)
  * outcome             -> Likes/Comments/Shares/Saves/Views

The categories `Fitness`, `Sports` and `Health` are used to isolate the
sport / fitness / wellness vertical this project focuses on.

Access method
-------------
Kaggle exposes a **no-authentication** download endpoint for CC0 datasets:

    https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>

It 302-redirects to a short-lived signed Google Cloud Storage URL. No API key,
no cookie and no browser is required, so the fetch step is reproducible inside
CI and for any reviewer. (If that unauthenticated endpoint is ever retired, the
fallback is `kaggle datasets download -d aviral342/social-media-engagement-dataset`
with a personal API token; the README documents both.)

Design note
-----------
The project deliberately uses **only the Python standard library** (plus SQLite).
There is no pandas / numpy / plotting dependency, so `python 01_fetch_data.py`
runs on any vanilla CPython >= 3.9 and cannot break on a version conflict.

Usage
-----
    python scripts/01_fetch_data.py            # download if missing
    python scripts/01_fetch_data.py --force    # always re-download
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_CSV = RAW_DIR / "social_media_engagement_dataset.csv"
MANIFEST = RAW_DIR / "MANIFEST.json"

# --------------------------------------------------------------------------- #
# Dataset registry — the ONLY external data source in this repository
# --------------------------------------------------------------------------- #
DATASET = {
    "name": "Social Media Engagement Dataset",
    "publisher": "aviral342",
    "permalink": "https://www.kaggle.com/datasets/aviral342/social-media-engagement-dataset",
    "download_url": "https://www.kaggle.com/api/v1/datasets/download/aviral342/social-media-engagement-dataset",
    "license": "CC0 1.0 (Public Domain Dedication)",
    "grain": "one row = one post",
    "expected_rows": 5000,
    "expected_columns": [
        "Post_ID", "Timestamp", "Platform", "Content_Type", "Category",
        "Likes", "Comments", "Shares", "Views", "Saves", "Follower_Count",
        "Engagement_Rate", "Hour_of_Day", "Day_of_Week", "Hashtag_Count",
        "Content_Length", "Sentiment", "Influencer_Tier", "Has_Media",
        "Is_Verified",
    ],
    "provenance_note": (
        "Kaggle card states the records are synthetically generated and "
        "platform-realistic. See docs/strategy_report.md 'Limitations'."
    ),
}

USER_AGENT = "fitness-kol-content-analytics/1.0 (+research; stdlib urllib)"
TIMEOUT = 90

# Sport / fitness / wellness vertical — the subject of this project.
VERTICAL_CATEGORIES = ("Fitness", "Sports", "Health")


def log(msg: str) -> None:
    print(f"[01_fetch] {msg}", flush=True)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_zip(url: str, attempts: int = 4) -> bytes:
    """
    Fetch the dataset bundle, following Kaggle's signed GCS redirect.

    Retries with exponential backoff: the signed URL and the TLS tunnel behind a
    corporate proxy both fail intermittently, and a first-attempt failure should
    not make the whole pipeline look broken.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            log(f"GET {url}  (attempt {i}/{attempts})")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                payload = resp.read()
            if len(payload) < 1024:
                raise ValueError(f"suspiciously small response ({len(payload)} bytes)")
            log(f"received {len(payload):,} bytes")
            return payload
        except urllib.error.HTTPError as exc:
            last = exc
            raise SystemExit(
                f"Download failed with HTTP {exc.code}.\n"
                f"Fallback: kaggle datasets download -d "
                f"{DATASET['publisher']}/social-media-engagement-dataset"
            ) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = exc
            log(f"  transient failure: {exc}")
            if i < attempts:
                time.sleep(2 ** i)
    raise SystemExit(f"Network error after {attempts} attempts: {last}")


def extract_csv(payload: bytes) -> str:
    """Unzip the bundle and return the CSV payload as text."""
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not members:
            raise SystemExit(f"No CSV inside archive: {zf.namelist()}")
        member = members[0]
        log(f"extracting {member}")
        return zf.read(member).decode("utf-8-sig", errors="strict")


def validate_csv(text: str) -> tuple[int, list[str]]:
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    rows = sum(1 for _ in reader)
    if header != DATASET["expected_columns"]:
        raise SystemExit(
            "Schema drift detected.\n"
            f"  expected: {DATASET['expected_columns']}\n"
            f"  found   : {header}"
        )
    if rows != DATASET["expected_rows"]:
        log(f"WARNING: expected {DATASET['expected_rows']:,} rows, found {rows:,}")
    return rows, header


def main() -> int:
    ap = argparse.ArgumentParser(description="Download and pin the source dataset.")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    ap.add_argument("--offline", action="store_true",
                    help="never touch the network; use the committed raw CSV")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_CSV.exists() and (args.offline or not args.force):
        log(f"cache hit -> {RAW_CSV.relative_to(ROOT)}")
    elif args.offline and not RAW_CSV.exists():
        raise SystemExit("--offline given but no cached data/raw CSV exists")
    else:
        try:
            payload = download_zip(DATASET["download_url"])
            text = extract_csv(payload)
            rows, _ = validate_csv(text)
            RAW_CSV.write_text(text, encoding="utf-8")
            log(f"wrote {RAW_CSV.relative_to(ROOT)} ({rows:,} rows)")
        except SystemExit as exc:
            # The Kaggle endpoint sits behind proxies that intermittently return
            # 400/502. The raw CSV is committed, so fall back to it rather than
            # failing the whole pipeline for a transient network fault.
            if not RAW_CSV.exists():
                raise
            log(f"WARNING: download unavailable ({exc}); using the committed raw CSV")
            log("         re-run without --offline once the network recovers to re-pin")

    rows, header = validate_csv(RAW_CSV.read_text(encoding="utf-8"))

    manifest = {
        "dataset": DATASET["name"],
        "publisher": DATASET["publisher"],
        "permalink": DATASET["permalink"],
        "download_url": DATASET["download_url"],
        "license": DATASET["license"],
        "grain": DATASET["grain"],
        "provenance_note": DATASET["provenance_note"],
        "vertical_categories": list(VERTICAL_CATEGORIES),
        "file": RAW_CSV.name,
        "sha256": sha256_of(RAW_CSV),
        "bytes": RAW_CSV.stat().st_size,
        "rows": rows,
        "columns": header,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"sha256 {manifest['sha256'][:16]}...  -> {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
