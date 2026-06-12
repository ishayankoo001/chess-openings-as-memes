#!/usr/bin/env python3
"""Phase 1 — Stream a Lichess monthly PGN zstd dump, aggregate into CSV + meta JSON.

Usage:
  python ingest/parse_month.py <path_or_url_to.pgn.zst> <output_dir> [--limit N]
"""

import sys
import os
import io
import csv
import json
import time
import argparse
import urllib.request
import zstandard


# Header keys we keep; everything else is discarded immediately.
KEEP_HEADERS = {
    "Event", "Result", "UTCDate", "WhiteElo", "BlackElo",
    "ECO", "Opening", "Termination", "WhiteTitle", "BlackTitle", "Variant",
}


def parse_header_line(line: str) -> tuple[str, str] | None:
    """Extract (key, value) from a PGN header line like [Key "Value"]."""
    if not line.startswith("["):
        return None
    key_end = line.find(" ")
    if key_end == -1:
        return None
    key = line[1:key_end]
    if key not in KEEP_HEADERS:
        return key, ""  # signal to skip this key
    first_quote = line.find('"', key_end)
    second_quote = line.find('"', first_quote + 1)
    if first_quote == -1 or second_quote == -1:
        return None
    value = line[first_quote + 1 : second_quote]
    return key, value


def clamp_bin(elo_mean: int) -> int:
    """Clamp Elo bin: (mean // 200) * 200, clamped to [600, 2400]."""
    raw = (elo_mean // 200) * 200
    if raw < 600:
        return 600
    if raw > 2400:
        return 2400
    return raw


def main():
    parser = argparse.ArgumentParser(description="Stream-aggregate a Lichess PGN zstd dump")
    parser.add_argument("input", help="Path or https URL to .pgn.zst file")
    parser.add_argument("outdir", help="Output directory for CSV and meta JSON")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N raw games (for testing)")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # ---- Open input stream ----
    if args.input.startswith("https://") or args.input.startswith("http://"):
        response = urllib.request.urlopen(args.input)
        fh = response  # response is file-like
    else:
        fh = open(args.input, "rb")

    dctx = zstandard.ZstdDecompressor()
    reader = dctx.stream_reader(fh)
    text_stream = io.TextIOWrapper(reader, encoding="utf-8")

    # ---- Aggregation state ----
    # key = (month, eco, opening, bin) -> [n, ww, bw, wsw, bsw, n_close, ww_close, bw_close]
    agg: dict[tuple[str, str, str, int], list[int]] = {}

    # Counters
    raw_games = 0
    kept_games = 0
    drop_counts: dict[str, int] = {
        "not_rated_blitz": 0,
        "variant_not_standard": 0,
        "bot_title": 0,
        "elo_missing_or_bad": 0,
        "termination_bad": 0,
        "eco_opening_missing": 0,
    }

    # Game-level accumulator
    headers: dict[str, str] = {}
    in_headers = True
    movetext: str = ""

    t_start = time.perf_counter()

    try:
        for line in text_stream:
            stripped = line.rstrip("\n")

            if stripped == "":
                continue

            if stripped.startswith("["):
                parsed = parse_header_line(stripped)
                if parsed is not None:
                    key, value = parsed
                    if value != "":  # key in KEEP_HEADERS
                        headers[key] = value
                in_headers = True

            elif in_headers:
                # First non-empty, non-'[' line = movetext — game complete
                movetext = stripped
                raw_games += 1

                # ---- Per-game filters ----
                keep = True

                # 1) Rated Blitz
                event = headers.get("Event", "")
                if not event.startswith("Rated Blitz"):
                    drop_counts["not_rated_blitz"] += 1
                    keep = False

                # 2) Variant absent or "Standard"
                variant = headers.get("Variant", "")
                if variant not in ("", "Standard"):
                    drop_counts["variant_not_standard"] += 1
                    keep = False

                # 3) No BOT titles
                wtitle = headers.get("WhiteTitle", "")
                btitle = headers.get("BlackTitle", "")
                if wtitle == "BOT" or btitle == "BOT":
                    drop_counts["bot_title"] += 1
                    keep = False

                # 4) Elos present and integer-parseable
                try:
                    welo = int(headers.get("WhiteElo", ""))
                    belo = int(headers.get("BlackElo", ""))
                except (ValueError, TypeError):
                    drop_counts["elo_missing_or_bad"] += 1
                    keep = False

                # 5) Termination "Normal" or "Time forfeit"
                termination = headers.get("Termination", "")
                if termination not in ("Normal", "Time forfeit"):
                    drop_counts["termination_bad"] += 1
                    keep = False

                # 6) ECO and Opening present and not "?"
                eco = headers.get("ECO", "")
                opening = headers.get("Opening", "")
                if not eco or not opening or eco == "?" or opening == "?":
                    drop_counts["eco_opening_missing"] += 1
                    keep = False

                if keep:
                    kept_games += 1

                    # ---- Derived fields ----
                    # month
                    utcdate = headers.get("UTCDate", "")
                    utcdate = utcdate.replace(".", "-")
                    month = utcdate[:7] if len(utcdate) >= 7 else utcdate

                    elo_mean = (welo + belo) // 2
                    bin_ = clamp_bin(elo_mean)

                    close = abs(welo - belo) <= 100

                    result = headers.get("Result", "")
                    white_win = result == "1-0"
                    black_win = result == "0-1"

                    # short = decisive, Normal-terminated, ≤ 20 full moves
                    # " 21." absent means no 21st full move; leading space avoids false "121."
                    short = (
                        termination == "Normal"
                        and (white_win or black_win)
                        and " 21." not in movetext
                    )

                    # ---- Aggregate ----
                    key = (month, eco, opening, bin_)
                    if key not in agg:
                        agg[key] = [0, 0, 0, 0, 0, 0, 0, 0]
                    row = agg[key]
                    row[0] += 1  # n
                    if white_win:
                        row[1] += 1  # ww
                    if black_win:
                        row[2] += 1  # bw
                    if short and white_win:
                        row[3] += 1  # wsw
                    if short and black_win:
                        row[4] += 1  # bsw
                    if close:
                        row[5] += 1  # n_close
                        if white_win:
                            row[6] += 1  # ww_close
                        if black_win:
                            row[7] += 1  # bw_close

                # ---- Reset for next game ----
                headers = {}
                in_headers = False

                # ---- Progress ----
                if raw_games % 1_000_000 == 0:
                    elapsed = time.perf_counter() - t_start
                    rate = raw_games / elapsed if elapsed > 0 else 0
                    print(
                        f"  {raw_games:>10,} raw  |  {kept_games:>10,} kept  |  "
                        f"{rate:,.0f} games/sec",
                        flush=True,
                    )

                # ---- Limit check ----
                if args.limit > 0 and raw_games >= args.limit:
                    break

            # else: continuation of movetext (multi-line) — ignore

    except zstandard.ZstdError as e:
        print(f"\nZstd error (truncated input?): {e}")

    elapsed = time.perf_counter() - t_start
    rate = raw_games / elapsed if elapsed > 0 else 0

    # ---- Determine file's dominant month for output naming ----
    month_counts: dict[str, int] = {}
    for (month, eco, opening, bin_), row in agg.items():
        month_counts[month] = month_counts.get(month, 0) + row[0]
    dominant_month = max(month_counts, key=month_counts.get) if month_counts else "unknown"

    # ---- Write CSV ----
    csv_path = os.path.join(args.outdir, f"agg_{dominant_month}.csv")
    with open(csv_path, "w", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow(["month", "eco", "opening", "bin", "n", "ww", "bw", "wsw", "bsw",
                          "n_close", "ww_close", "bw_close"])
        for (month, eco, opening, bin_), row in sorted(agg.items()):
            writer.writerow([month, eco, opening, bin_, *row])

    # ---- Write meta JSON ----
    meta_path = os.path.join(args.outdir, f"meta_{dominant_month}.json")
    with open(meta_path, "w") as mf:
        json.dump({
            "raw_games": raw_games,
            "kept_games": kept_games,
            "drop_counts": drop_counts,
            "wall_seconds": round(elapsed, 2),
            "games_per_second": round(rate, 2),
        }, mf, indent=2)

    # ---- Final summary ----
    print(f"\n{'='*60}")
    print(f"  Raw games:        {raw_games:>12,}")
    print(f"  Kept games:       {kept_games:>12,}  ({100*kept_games/max(raw_games,1):.1f}%)")
    print(f"  Wall time:        {elapsed:>12.1f}s")
    print(f"  Rate:             {rate:>12,.0f} games/sec")
    print(f"  Aggregate rows:   {len(agg):>12,}")
    print(f"  Dominant month:   {dominant_month}")
    print(f"  CSV:              {csv_path}")
    print(f"  Meta:             {meta_path}")
    print(f"\nDrop breakdown:")
    for reason, count in sorted(drop_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason:30s} {count:>12,}")
    print(f"{'='*60}")

    # Cleanup
    if hasattr(fh, "close"):
        fh.close()


if __name__ == "__main__":
    main()