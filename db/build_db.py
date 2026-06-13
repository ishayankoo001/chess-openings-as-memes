#!/usr/bin/env python3
"""Build the SQLite database and core CSV exports from monthly aggregates."""

from __future__ import annotations

import csv
import math
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGG_DIR = ROOT / "data" / "agg"
EXPORT_DIR = ROOT / "exports"
DB_PATH = ROOT / "data" / "chess.sqlite"

AGG_COLUMNS = [
    "month",
    "eco",
    "opening",
    "bin",
    "n",
    "ww",
    "bw",
    "wsw",
    "bsw",
    "n_close",
    "ww_close",
    "bw_close",
]

INT_COLUMNS = {
    "bin",
    "n",
    "ww",
    "bw",
    "wsw",
    "bsw",
    "n_close",
    "ww_close",
    "bw_close",
}


CREATE_AGG_SQL = """
CREATE TABLE agg (
    month TEXT,
    eco TEXT,
    opening TEXT,
    bin INT,
    n INT,
    ww INT,
    bw INT,
    wsw INT,
    bsw INT,
    n_close INT,
    ww_close INT,
    bw_close INT
);
"""

CREATE_SHARES_TOTAL_SQL = """
CREATE VIEW shares_total AS
WITH opening_month AS (
    SELECT opening, month, SUM(n) AS opening_games
    FROM agg
    WHERE month BETWEEN '2019-01' AND '2021-12'
    GROUP BY opening, month
),
month_total AS (
    SELECT month, SUM(n) AS month_games
    FROM agg
    WHERE month BETWEEN '2019-01' AND '2021-12'
    GROUP BY month
)
SELECT
    om.opening,
    om.month,
    1.0 * om.opening_games / mt.month_games AS share
FROM opening_month AS om
JOIN month_total AS mt USING (month);
"""

CREATE_SHARES_BY_BIN_SQL = """
CREATE VIEW shares_by_bin AS
WITH opening_month_bin AS (
    SELECT opening, month, bin, SUM(n) AS opening_games
    FROM agg
    WHERE month BETWEEN '2019-01' AND '2021-12'
    GROUP BY opening, month, bin
),
month_bin_total AS (
    SELECT month, bin, SUM(n) AS bin_games
    FROM agg
    WHERE month BETWEEN '2019-01' AND '2021-12'
    GROUP BY month, bin
)
SELECT
    omb.opening,
    omb.month,
    omb.bin,
    1.0 * omb.opening_games / mbt.bin_games AS share_in_bin
FROM opening_month_bin AS omb
JOIN month_bin_total AS mbt USING (month, bin);
"""

CREATE_FEATURES_SQL = """
CREATE TABLE features AS
WITH totals_2019 AS (
    SELECT SUM(n) AS total_games
    FROM agg
    WHERE month LIKE '2019-%'
),
opening_2019 AS (
    SELECT
        opening,
        SUM(n) AS n2019,
        SUM(ww) AS ww,
        SUM(bw) AS bw,
        SUM(wsw) AS wsw,
        SUM(bsw) AS bsw
    FROM agg
    WHERE month LIKE '2019-%'
    GROUP BY opening
),
opening_eco_counts AS (
    SELECT opening, eco, SUM(n) AS eco_games
    FROM agg
    WHERE month LIKE '2019-%'
    GROUP BY opening, eco
),
opening_eco AS (
    SELECT opening, eco
    FROM (
        SELECT
            opening,
            eco,
            ROW_NUMBER() OVER (
                PARTITION BY opening
                ORDER BY eco_games DESC, eco ASC
            ) AS rn
        FROM opening_eco_counts
    )
    WHERE rn = 1
),
base AS (
    SELECT
        o.opening,
        e.eco,
        o.n2019,
        1.0 * o.n2019 / t.total_games AS share2019,
        1.0 * o.wsw / o.n2019 AS white_short_rate,
        1.0 * o.bsw / o.n2019 AS black_short_rate,
        CASE
            WHEN o.wsw >= o.bsw THEN 'white'
            ELSE 'black'
        END AS weapon_side,
        CASE
            WHEN o.wsw >= o.bsw THEN 1.0 * o.wsw / o.n2019
            ELSE 1.0 * o.bsw / o.n2019
        END AS trickiness
    FROM opening_2019 AS o
    JOIN opening_eco AS e USING (opening)
    CROSS JOIN totals_2019 AS t
    WHERE o.n2019 >= 5000
),
high_close AS (
    SELECT
        opening,
        SUM(n_close) AS high_close_games,
        SUM(ww_close) AS high_ww_close,
        SUM(bw_close) AS high_bw_close
    FROM agg
    WHERE month LIKE '2019-%'
      AND bin IN (SELECT bin FROM high_bins)
    GROUP BY opening
),
low_close AS (
    SELECT
        opening,
        SUM(n_close) AS low_close_games,
        SUM(ww_close) AS low_ww_close,
        SUM(bw_close) AS low_bw_close
    FROM agg
    WHERE month LIKE '2019-%'
      AND bin <= 1200
    GROUP BY opening
),
with_rates AS (
    SELECT
        b.opening,
        b.eco,
        b.n2019,
        b.share2019,
        b.white_short_rate,
        b.black_short_rate,
        b.weapon_side,
        b.trickiness,
        CASE
            WHEN COALESCE(h.high_close_games, 0) < 200 THEN NULL
            WHEN b.weapon_side = 'white' THEN 1.0 * h.high_ww_close / h.high_close_games
            ELSE 1.0 * h.high_bw_close / h.high_close_games
        END AS soundness,
        CASE
            WHEN COALESCE(l.low_close_games, 0) = 0 THEN NULL
            WHEN b.weapon_side = 'white' THEN 1.0 * l.low_ww_close / l.low_close_games
            ELSE 1.0 * l.low_bw_close / l.low_close_games
        END AS low_winrate
    FROM base AS b
    LEFT JOIN high_close AS h USING (opening)
    LEFT JOIN low_close AS l USING (opening)
)
SELECT
    opening,
    eco,
    n2019,
    share2019,
    white_short_rate,
    black_short_rate,
    weapon_side,
    trickiness,
    soundness,
    low_winrate,
    CASE
        WHEN soundness IS NULL OR low_winrate IS NULL THEN NULL
        ELSE low_winrate - soundness
    END AS punish_gap,
    -LN(share2019) AS surprise
FROM with_rates;
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("LN", 1, math.log)
    return conn


def reset_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP VIEW IF EXISTS shares_total;
        DROP VIEW IF EXISTS shares_by_bin;
        DROP TABLE IF EXISTS features;
        DROP TABLE IF EXISTS high_bins;
        DROP TABLE IF EXISTS agg;
        """
    )
    conn.execute(CREATE_AGG_SQL)
    conn.commit()


def csv_rows(path: Path) -> list[tuple]:
    rows: list[tuple] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != AGG_COLUMNS:
            raise ValueError(f"{path} has unexpected header: {reader.fieldnames}")
        for row in reader:
            rows.append(
                tuple(
                    int(row[col]) if col in INT_COLUMNS else row[col]
                    for col in AGG_COLUMNS
                )
            )
    return rows


def load_agg_csvs(conn: sqlite3.Connection) -> None:
    paths = sorted(AGG_DIR.glob("agg_*.csv"))
    if not paths:
        raise SystemExit(f"No aggregate CSV files found in {AGG_DIR}")

    insert_sql = f"""
        INSERT INTO agg ({", ".join(AGG_COLUMNS)})
        VALUES ({", ".join("?" for _ in AGG_COLUMNS)})
    """
    total_rows = 0
    with conn:
        for path in paths:
            rows = csv_rows(path)
            conn.executemany(insert_sql, rows)
            total_rows += len(rows)
            print(f"Loaded {path.name}: {len(rows):,} rows")
    print(f"Loaded {len(paths)} files and {total_rows:,} aggregate rows.")


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_agg_opening_month ON agg(opening, month);
        CREATE INDEX idx_agg_month_bin ON agg(month, bin);
        """
    )
    conn.commit()


def select_high_bins(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        """
        SELECT bin, SUM(n) AS games
        FROM agg
        WHERE month LIKE '2019-%'
        GROUP BY bin
        ORDER BY bin DESC;
        """
    ).fetchall()
    total = sum(games for _, games in rows)
    if total == 0:
        raise SystemExit("No 2019 games found while selecting HIGH bins.")

    selected: list[int] = []
    running = 0
    for bin_, games in rows:
        selected.append(bin_)
        running += games
        if running / total >= 0.10:
            break

    conn.execute("CREATE TABLE high_bins (bin INT PRIMARY KEY)")
    conn.executemany("INSERT INTO high_bins (bin) VALUES (?)", [(b,) for b in selected])
    conn.commit()

    share = running / total
    print(f"HIGH bins selected: {selected} ({100 * share:.2f}% of 2019 games)")
    running = 0
    selected_set = set(selected)
    for bin_, games in rows:
        if bin_ not in selected_set:
            continue
        running += games
        print(f"bin {bin_}: {games} games, cumulative {100 * running / total:.2f}%")
    return selected


def create_outputs(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='high_bins'"
    ).fetchone()
    if exists is None:
        raise SystemExit("high_bins table missing — run select_high_bins(conn) before create_outputs(conn).")
    conn.execute(CREATE_SHARES_TOTAL_SQL)
    conn.execute(CREATE_SHARES_BY_BIN_SQL)
    conn.execute(CREATE_FEATURES_SQL)
    conn.commit()


def export_query(
    conn: sqlite3.Connection,
    path: Path,
    headers: list[str],
    query: str,
) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(conn.execute(query))
    print(f"Wrote {path.relative_to(ROOT)}")


def export_csvs(conn: sqlite3.Connection) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_query(
        conn,
        EXPORT_DIR / "shares_total.csv",
        ["opening", "month", "share"],
        """
        SELECT opening, month, share
        FROM shares_total
        ORDER BY opening, month;
        """,
    )
    export_query(
        conn,
        EXPORT_DIR / "shares_by_bin.csv",
        ["opening", "month", "bin", "share_in_bin"],
        """
        SELECT opening, month, bin, share_in_bin
        FROM shares_by_bin
        ORDER BY opening, month, bin;
        """,
    )
    export_query(
        conn,
        EXPORT_DIR / "features.csv",
        [
            "opening",
            "eco",
            "n2019",
            "share2019",
            "white_short_rate",
            "black_short_rate",
            "weapon_side",
            "trickiness",
            "soundness",
            "low_winrate",
            "punish_gap",
            "surprise",
        ],
        """
        SELECT
            opening,
            eco,
            n2019,
            share2019,
            white_short_rate,
            black_short_rate,
            weapon_side,
            trickiness,
            soundness,
            low_winrate,
            punish_gap,
            surprise
        FROM features
        ORDER BY opening;
        """,
    )


def print_rows(rows: list[tuple], headers: tuple[str, ...]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(str(value)))

    print("  ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)))


def qc_total_games(conn: sqlite3.Connection) -> None:
    print("\nQC: total kept games per month")
    rows = conn.execute(
        """
        SELECT month, SUM(n) AS games
        FROM agg
        WHERE month BETWEEN '2019-01' AND '2021-12'
        GROUP BY month
        ORDER BY month;
        """
    ).fetchall()
    print_rows(rows, ("month", "games"))


def qc_largest_openings(conn: sqlite3.Connection) -> None:
    print("\nQC: 10 largest openings by share2019")
    rows = conn.execute(
        """
        SELECT
            opening,
            eco,
            n2019,
            printf('%.6f', share2019) AS share2019
        FROM features
        ORDER BY share2019 DESC
        LIMIT 10;
        """
    ).fetchall()
    print_rows(rows, ("opening", "eco", "n2019", "share2019"))


def qc_pattern_series(conn: sqlite3.Connection) -> None:
    patterns = [
        "Queen's Gambit%",
        "%Bongcloud%",
        "%Stafford%",
    ]
    for pattern in patterns:
        print(f"\nQC: monthly share series for opening LIKE {pattern!r}")
        rows = conn.execute(
            """
            WITH pattern_month AS (
                SELECT month, SUM(n) AS pattern_games
                FROM agg
                WHERE opening LIKE ?
                  AND month BETWEEN '2019-01' AND '2021-12'
                GROUP BY month
            ),
            month_total AS (
                SELECT month, SUM(n) AS month_games
                FROM agg
                WHERE month BETWEEN '2019-01' AND '2021-12'
                GROUP BY month
            )
            SELECT
                mt.month,
                COALESCE(pm.pattern_games, 0) AS games,
                printf('%.8f', 1.0 * COALESCE(pm.pattern_games, 0) / mt.month_games) AS share
            FROM month_total AS mt
            LEFT JOIN pattern_month AS pm USING (month)
            ORDER BY mt.month;
            """,
            (pattern,),
        ).fetchall()
        print_rows(rows, ("month", "games", "share"))


def print_qc(conn: sqlite3.Connection) -> None:
    qc_total_games(conn)
    qc_largest_openings(conn)
    qc_pattern_series(conn)


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with connect() as conn:
        reset_database(conn)
        load_agg_csvs(conn)
        create_indexes(conn)
        select_high_bins(conn)
        create_outputs(conn)
        export_csvs(conn)
        print_qc(conn)

    print(f"\nDone. Database: {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
