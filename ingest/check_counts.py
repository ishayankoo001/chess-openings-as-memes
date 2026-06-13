#!/usr/bin/env python3
"""Check parsed raw game counts against Lichess database monthly totals."""

from __future__ import annotations

from pathlib import Path


EXPECTED_RAW_GAMES = {
    "2019-01": 33886899,
    "2019-02": 31023718,
    "2019-03": 34869171,
    "2019-04": 33565536,
    "2019-05": 35236588,
    "2019-06": 33935786,
    "2019-07": 35728182,
    "2019-08": 36745427,
    "2019-09": 36996010,
    "2019-10": 40440254,
    "2019-11": 40357832,
    "2019-12": 44055757,
    "2020-07": 70592022,
    "2020-08": 71405167,
    "2020-09": 68027862,
    "2020-10": 70572373,
    "2020-11": 78268317,
    "2020-12": 89422803,
    "2021-01": 95853038,
    "2021-02": 89892001,
    "2021-03": 100023791,
    "2021-04": 99184138,
    "2021-05": 101011629,
    "2021-06": 92190803,
    "2021-07": 92193352,
    "2021-08": 93679328,
    "2021-09": 88133339,
    "2021-10": 88092721,
    "2021-11": 87113345,
    "2021-12": 95600810,
}


def latest_successful_counts(log_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        month, raw_games, kept_games, games_per_second, status = line.split(",", 4)
        raw = int(raw_games)
        if status in {"success", "skipped"} and raw > 0:
            counts[month] = raw
    return counts


def main() -> None:
    agg_dir = Path("data/agg")
    log_path = agg_dir / "run_log.txt"
    if not log_path.exists():
        raise SystemExit(f"Missing {log_path}")

    seen = latest_successful_counts(log_path)
    missing: list[str] = []
    bad: list[tuple[str, float]] = []

    print(f"{'month':10s} {'parsed':>12s} {'lichess':>12s} {'diff':>8s}")
    for month, official in EXPECTED_RAW_GAMES.items():
        parsed = seen.get(month)
        if parsed is None:
            missing.append(month)
            print(f"{month:10s} {'MISSING':>12s} {official:12,} {'':>8s}")
            continue

        diff_pct = 100 * abs(parsed - official) / official
        print(f"{month:10s} {parsed:12,} {official:12,} {diff_pct:7.3f}%")
        if diff_pct > 2:
            bad.append((month, diff_pct))

    print()
    print(f"agg csv files:   {len(list(agg_dir.glob('agg_*.csv')))}")
    print(f"meta json files: {len(list(agg_dir.glob('meta_*.json')))}")

    if missing:
        print("MISSING:", ", ".join(missing))
    if bad:
        print("BAD:", ", ".join(f"{month} ({diff:.3f}%)" for month, diff in bad))
    if not missing and not bad:
        print("PASS: all required months are within 2%.")


if __name__ == "__main__":
    main()
