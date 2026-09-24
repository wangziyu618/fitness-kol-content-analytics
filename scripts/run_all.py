#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run the whole pipeline end to end.

    python scripts/run_all.py

Equivalent to:

    python scripts/01_fetch_data.py
    python scripts/02_clean_features.py
    python scripts/03_analysis.py
    python scripts/04_build_dashboard.py

Requires Python 3.9+ and no third-party packages.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ("01_fetch_data.py", "downloading and pinning the source dataset"),
    ("02_clean_features.py", "cleaning, feature engineering, SQLite warehouse"),
    ("03_analysis.py", "running SQL, bootstrap CIs, budget model"),
    ("04_build_dashboard.py", "building the dashboard"),
]


def main() -> int:
    for name, what in STEPS:
        script = ROOT / "scripts" / name
        print(f"\n=== {name} — {what} " + "=" * max(0, 46 - len(name) - len(what)))
        t0 = time.time()
        rc = subprocess.call([sys.executable, str(script)], cwd=str(ROOT))
        if rc != 0:
            print(f"\nFAILED: {name} exited with {rc}")
            return rc
        print(f"    done in {time.time() - t0:.1f}s")

    print("\n" + "=" * 74)
    print("Pipeline complete.")
    print(f"  Dashboard : {ROOT / 'index.html'}")
    print(f"  Results   : {ROOT / 'output' / 'analysis_results.json'}")
    print(f"  Report    : {ROOT / 'docs' / 'strategy_report.md'}")
    print(f"  SQL audit : {ROOT / 'output' / 'analysis_tables'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
