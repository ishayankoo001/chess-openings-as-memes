#!/usr/bin/env python3
"""Phase 2: Download monthly Lichess dumps, parse them, and clean up raw files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def month_range(start: str, end: str) -> list[str]:
    """Return inclusive YYYY-MM months from start through end."""
    start_year, start_month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))

    months: list[str] = []
    year = start_year
    month = start_month
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return months


MONTHS = month_range("2019-01", "2019-12") + month_range("2020-07", "2021-12")


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
AGG_DIR = ROOT / "data" / "agg"
LOG_PATH = AGG_DIR / "run_log.txt"
PARSE_MONTH = ROOT / "ingest" / "parse_month.py"
URL_TEMPLATE = (
    "https://database.lichess.org/standard/"
    "lichess_db_standard_rated_{month}.pgn.zst"
)


def paths_for_month(month: str) -> tuple[Path, Path, Path]:
    raw_path = RAW_DIR / f"lichess_db_standard_rated_{month}.pgn.zst"
    csv_path = AGG_DIR / f"agg_{month}.csv"
    meta_path = AGG_DIR / f"meta_{month}.json"
    return raw_path, csv_path, meta_path


def download_month(month: str, raw_path: Path) -> None:
    url = URL_TEMPLATE.format(month=month)
    subprocess.run(
        ["curl", "-L", "-C", "-", "-o", str(raw_path), url],
        check=True,
    )


def run_parser(raw_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(PARSE_MONTH), str(raw_path), str(AGG_DIR)],
        check=True,
    )


def outputs_ok(csv_path: Path, meta_path: Path) -> bool:
    return csv_path.exists() and csv_path.stat().st_size > 0 and meta_path.exists()


def read_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {"raw_games": 0, "kept_games": 0, "games_per_second": 0}
    with open(meta_path) as f:
        return json.load(f)


def log_result(month: str, meta: dict, status: str) -> None:
    with open(LOG_PATH, "a") as f:
        f.write(
            f"{month},"
            f"{meta.get('raw_games', 0)},"
            f"{meta.get('kept_games', 0)},"
            f"{meta.get('games_per_second', 0)},"
            f"{status}\n"
        )


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    AGG_DIR.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, int, int, float, str]] = []

    for month in MONTHS:
        raw_path, csv_path, meta_path = paths_for_month(month)

        if csv_path.exists():
            meta = read_meta(meta_path)
            status = "skipped"
            print(f"{month}: {csv_path} already exists, skipping")
            log_result(month, meta, status)
            results.append(
                (
                    month,
                    meta.get("raw_games", 0),
                    meta.get("kept_games", 0),
                    meta.get("games_per_second", 0),
                    status,
                )
            )
            continue

        try:
            print(f"{month}: downloading raw dump")
            download_month(month, raw_path)

            print(f"{month}: parsing month")
            run_parser(raw_path)

            if not outputs_ok(csv_path, meta_path):
                raise RuntimeError("parser finished but CSV/meta output is missing or empty")

            meta = read_meta(meta_path)
            raw_path.unlink(missing_ok=True)
            status = "success"
            print(f"{month}: success; deleted {raw_path}")

        except subprocess.CalledProcessError as exc:
            meta = read_meta(meta_path)
            status = f"failed_command_{exc.returncode}"
            print(f"{month}: command failed; keeping {raw_path}")

        except Exception as exc:
            meta = read_meta(meta_path)
            status = "failed_verify"
            print(f"{month}: {exc}; keeping {raw_path}")

        log_result(month, meta, status)
        results.append(
            (
                month,
                meta.get("raw_games", 0),
                meta.get("kept_games", 0),
                meta.get("games_per_second", 0),
                status,
            )
        )

    print("\nFinal summary")
    print(f"{'month':10s} {'raw_games':>12s} {'kept_games':>12s} {'games/sec':>12s} status")
    for month, raw_games, kept_games, games_per_second, status in results:
        print(
            f"{month:10s} "
            f"{raw_games:12,} "
            f"{kept_games:12,} "
            f"{games_per_second:12,.0f} "
            f"{status}"
        )


if __name__ == "__main__":
    main()
