# DMA2 "Openings as Memes" — Coding Roadmap for Cheap-Model Sessions

**How to use this file.** One phase = one fresh session with the cheap model. Phases 0–3 are pure engineering: paste only the phase card (they need zero knowledge of the hypotheses). Phases 4–7 are analysis: paste `MASTER.md` (the execution prompt from our earlier chat — save it as a file) **first**, then the phase card. Never let a session touch code from another phase.

**Ground rules for every session:**
- Ask for complete files, never diffs. Keep each file under ~200 lines.
- If something errors, paste the exact traceback + the phase card again in a fresh message.
- The model may not add features, metrics, or dependencies beyond the card. If it suggests one, the answer is no.
- After every phase, append parameters and choices to `notes/decisions.md` (thresholds, dates, bin edges). This file is your Q&A ammunition.
- Pin the environment once: `python 3.11+, zstandard, pandas, numpy, scikit-learn, statsmodels, matplotlib`. Nothing else.

**Repo layout (create in Phase 0):**
```
chess-memes/
  MASTER.md                 # the execution prompt
  ingest/peek.py            # Phase 0
  ingest/parse_month.py     # Phase 1
  ingest/run_months.py      # Phase 2
  data/agg/                 # tiny per-month CSVs + meta JSONs (the only data you keep)
  db/build_db.py, chess.sqlite
  analysis/h2_pca.py, h1_breaks.py, h4_decay.py, k3_clusters.py
  exports/                  # features.csv, shares_total.csv, shares_by_bin.csv
  figures/
  notes/decisions.md
```

**Data source:** https://database.lichess.org — monthly `lichess_db_standard_rated_YYYY-MM.pgn.zst`. The site lists exact game counts and file sizes per month: use the counts as ground truth for parser QC, and check sizes before downloading (roughly 5–25 GB compressed per month depending on year; never store decompressed data). Full study window 2019-01 → 2022-06 is a multi-hundred-GB download — do the MVP subset first, backfill later (torrents available on the site, resumable and polite).

**MVP month set (run first, gives plottable results):** 2019-03, 2019-06, 2019-09, 2019-12, then 2020-08 → 2021-06. **Full set (backfill overnight):** 2019-01 → 2022-06.

---

## Phase 0 — Environment + first contact (~30–45 min)

**Goal:** see real data flow through your machine tonight. No commitments yet.

**Paste this:**
```
Write two things for a Python 3.11 project.

1) Setup: a requirements.txt containing zstandard, pandas, numpy, scikit-learn, statsmodels, matplotlib, and the shell commands to create a venv and install.

2) ingest/peek.py — a script that streams a Lichess PGN zstd dump WITHOUT decompressing to disk.
- Input: path to a .pgn.zst file (argv[1]).
- Use zstandard.ZstdDecompressor().stream_reader wrapped in io.TextIOWrapper(encoding='utf-8'), iterate line by line.
- PGN structure: each game = consecutive header lines like [Key "Value"], then a blank line, then ONE movetext line, then a blank line.
- Parse the first 5 games into dicts of {header_key: value} plus the movetext string, and pretty-print them.
- Then keep streaming and count total games in the file (a game ends at its movetext line), printing a running count every 100,000 games. Stop cleanly on EOF or on a zstd error from a truncated file (catch it, print the count so far, exit 0 — truncated input is expected during testing).
- No external libraries beyond zstandard. Do NOT use python-chess.
```

**Before running it:** download a test slice instead of a full month — `curl -r 0-200000000 -o sample.pgn.zst "<URL of any 2021 month>"` grabs the first ~200 MB; the script's truncation handling makes this fine.

**Done when:** you've seen real headers (Event, WhiteElo, ECO, Opening, Termination, sometimes WhiteTitle/Variant/FEN) and movetext containing `{ [%clk ...] }` comments, and the counter runs at a sane speed.

---

## Phase 1 — The streaming parser (one evening; the heart of the project)

**Goal:** `parse_month.py` turns one monthly dump into one tiny aggregate CSV. Everything downstream depends on this schema — it is frozen after this phase.

**Paste this:**
```
Write ingest/parse_month.py for Python 3.11. It streams a Lichess monthly PGN zstd dump and writes ONE aggregate CSV plus a meta JSON. Stdlib + zstandard only. Do NOT use python-chess. Do NOT use regex in the per-line hot loop. Do NOT load the file into memory or build per-game DataFrames.

INPUT: argv[1] = path to .pgn.zst (or an https URL — if URL, open via urllib.request and feed the response stream into the zstd stream_reader). argv[2] = output directory.

STREAMING: zstandard stream_reader + io.TextIOWrapper, iterate lines. State machine: lines starting with '[' are headers — extract key (chars between '[' and first space) and value (between the two double quotes); the first non-empty line not starting with '[' is the movetext and completes the game. Only store these header keys, skip others immediately: Event, Result, UTCDate, WhiteElo, BlackElo, ECO, Opening, Termination, WhiteTitle, BlackTitle, Variant.

PER-GAME FILTERS (count every drop reason). Keep a game only if ALL hold:
- Event starts with "Rated Blitz"
- Variant header absent or equal to "Standard"
- Neither WhiteTitle nor BlackTitle equals "BOT"
- WhiteElo and BlackElo present and integer-parseable
- Termination is "Normal" or "Time forfeit"
- ECO and Opening present and not "?"

DERIVED PER GAME:
- month = UTCDate[:7] with '.' replaced by '-'  (e.g. "2021-03")
- elo_mean = (WhiteElo + BlackElo) // 2
- bin = clamp((elo_mean // 200) * 200, 600, 2400)   # 600 means "<=799 incl. lower", 2400 means "2400+"
- close = abs(WhiteElo - BlackElo) <= 100
- white_win = Result == "1-0"; black_win = Result == "0-1"
- short = (Termination == "Normal") and (white_win or black_win) and (" 21." not in movetext)
  # " 21." absent means the game ended within 20 full moves; the leading space avoids matching "121."

AGGREGATION: dict keyed by (month, ECO, Opening, bin) -> list of 8 counters:
[n, white_wins, black_wins, white_short_wins, black_short_wins, n_close, white_wins_close, black_wins_close]
Increment the *_close counters only when close is True; increment white_short_wins/black_short_wins only when short is True.

OUTPUT:
- CSV {outdir}/agg_{month}.csv with header:
  month,eco,opening,bin,n,ww,bw,wsw,bsw,n_close,ww_close,bw_close
  (month = the file's dominant month; if a few games belong to other months, write rows for them too — the key already contains month.)
- JSON {outdir}/meta_{month}.json: raw_games, kept_games, dict of drop counts per filter, wall_seconds, games_per_second.

PERFORMANCE: target >= 50,000 games/sec on a laptop. Print progress every 1,000,000 raw games. Use str.startswith / slicing / 'in' checks only.

VALIDATION MODE: flag --limit N stops after N raw games (for testing on partial files; catch zstd truncation errors and finalize cleanly).
```

**Done when, on a ~1M-game test slice:** kept/raw blitz fraction lands somewhere in 25–55%; Elo-parse drops < 0.5%; output CSV has fewer than ~50K rows; spot-check that `Russian Game: Stafford Gambit` and Queen's Gambit rows exist with sane counts.

**Don't let it:** import python-chess; use `re` in the loop; append rows to a pandas DataFrame; "simplify" the schema. The `n_close/ww_close/bw_close` columns look redundant now — they are the only way to compute the soundness feature later, because the aggregate destroys per-game Elo differences. Non-negotiable.

---

## Phase 2 — Batch runner (one setup hour, then unattended)

**Goal:** all months processed with checkpointing; raw dumps never accumulate on disk.

**Paste this:**
```
Write ingest/run_months.py. It processes a list of Lichess months end-to-end by calling the existing parse_month.py (subprocess or import — your choice, but do not modify parse_month.py).

- MONTHS list at the top of the file (editable), URL template:
  https://database.lichess.org/standard/lichess_db_standard_rated_{YYYY-MM}.pgn.zst
- For each month: SKIP if data/agg/agg_{month}.csv already exists (checkpointing). Otherwise: download with resume support (wget -c or curl -C - via subprocess), run the parser, verify the CSV exists and is non-empty and the meta JSON exists, then DELETE the .zst. If anything fails, keep the .zst, log the failure, continue to the next month.
- Append one line per month to data/agg/run_log.txt: month, raw_games, kept_games, games_per_second, status.
- Print a final summary table.
```

**Run order:** MVP set first (results in a day), full set overnight later. **Done when:** every month in `run_log.txt` shows `raw_games` within ~2% of the count listed on database.lichess.org for that month. Any bigger gap = parser bug, stop and investigate before Phase 3.

---

## Phase 3 — SQLite + core SQL (one evening; this is your syllabus showcase)

**Goal:** one `chess.sqlite`, the share/feature views in SQL, three exported CSVs that the analysis phases consume.

**Paste this:**
```
Write db/build_db.py for Python 3.11 (stdlib sqlite3 + csv only).

1) Create table agg(month TEXT, eco TEXT, opening TEXT, bin INT, n INT, ww INT, bw INT, wsw INT, bsw INT, n_close INT, ww_close INT, bw_close INT). Load every data/agg/agg_*.csv. Index on (opening, month) and on (month, bin).

2) Create these views/queries and export the results to CSV:

a) exports/shares_total.csv — opening, month, share:
   share = SUM(n) for that opening-month / SUM(n) over all openings that month.

b) exports/shares_by_bin.csv — opening, month, bin, share_in_bin:
   same but within (month, bin).

c) exports/features.csv — one row per opening with >= 5000 games in 2019 (months '2019-%'), columns:
   opening, eco, n2019,
   share2019           = opening's 2019 games / all 2019 games,
   white_short_rate    = SUM(wsw)/SUM(n) over 2019,
   black_short_rate    = SUM(bsw)/SUM(n) over 2019,
   weapon_side         = 'white' if white_short_rate >= black_short_rate else 'black',
   trickiness          = MAX(white_short_rate, black_short_rate),
   soundness           = weapon side's win rate in 2019 close games (ww_close or bw_close / n_close) restricted to HIGH bins,
   low_winrate         = weapon side's close-game win rate in bins <= 1200,
   punish_gap          = low_winrate - soundness,
   surprise            = -LN(share2019).
   HIGH bins = the top rating bins that together contain ~10% of all 2019 games (compute the cumulative distribution of n by bin descending over 2019 and take bins above the 90th percentile cutoff). Print which bins were selected.
   If an opening has < 200 close games in HIGH bins, set soundness and punish_gap to NULL (too noisy).

3) QC printed to console: total games per month; the 10 largest openings by share2019; the full monthly share series for openings matching 'Queen''s Gambit%', '%Bongcloud%', '%Stafford%'.
```

**Done when:** the QC printout passes the eyeball test — Queen's Gambit family share jumps visibly starting 2020-11, Bongcloud spikes around 2021-03, Stafford is elevated through 2020–21. If those three sanity signals aren't visible here, no regression later will save you. Note in `decisions.md`: games threshold 5000, close-game floor 200, HIGH-bin cutoff, bin edges.

---

## Phase 4 — Features → PCA → H2 regression (one evening; paste MASTER.md first)

**Paste this after MASTER.md:**
```
Write analysis/h2_pca.py. Inputs: exports/features.csv, exports/shares_total.csv. Use pandas, numpy, scikit-learn PCA, statsmodels OLS, matplotlib.

1) Sample: all openings in features.csv with non-NULL soundness. Report how many.
2) Z-score these four features: trickiness, soundness, punish_gap, surprise. (z-score = subtract mean, divide by std — print the means/stds.)
3) Pearson correlation matrix of the four features (print; this justifies PCA).
4) PCA on the 4 z-scored features. Print explained variance ratios and the 4x4 loadings table. Orient PC1 so that the trickiness loading is positive; call it the "meme axis".
5) DV: for each opening, peak_share = max monthly share over 2020-07..2021-12; baseline = mean monthly share over 2019; y = ln(peak_share / baseline).
6) OLS: y ~ PC1 + PC2. Report coefficients with 95% CIs, R². Then influence check: Cook's distance, print the top 5 openings by influence, and refit excluding them — report whether the PC1 coefficient's sign and significance survive.
7) Stability check: redo PCA four times, each time dropping one feature; print PC1 loadings each time.
8) Figures (big fonts, one message per figure): figures/h2_loadings.png (bar chart of PC1/PC2 loadings) and figures/h2_scatter.png (PC1 vs y, label the 8 most extreme points by name).
9) Append all headline numbers to exports/results.md under a "## H2" section.

Do not add features, do not change the sample rule, do not use any model other than PCA + OLS.
```

**Done when:** loadings are interpretable (expect trickiness and surprise loading together on PC1, soundness opposite or orthogonal) and the scatter shows the Bongcloud/Stafford corner. **Don't let it:** recompute features on post-2019 data, drop the threshold, or swap in regularized regression.

---

## Phase 5 — H1 structural breaks + placebos (one evening; paste MASTER.md first)

**Before this session:** verify the exact date of the Nakamura–Carlsen double-Bongcloud game (March 2021) and lock it in decisions.md. Queen's Gambit trigger = Netflix release, 2020-10-23.

**Paste this after MASTER.md:**
```
Write analysis/h1_breaks.py. Input: exports/shares_total.csv. statsmodels OLS + matplotlib.

CASES (opening-name SQL-LIKE patterns aggregated into one series each):
- "Queen's Gambit": openings LIKE "Queen's Gambit%", trigger month 2020-11 (event 2020-10-23).
- "Bongcloud": openings LIKE "%Bongcloud%", trigger month 2021-03 (event date: PARAM_BONGCLOUD_DATE).

For each case:
1) Build the monthly share series, window = trigger ± 12 months. t = months since trigger (negative pre). post = 1 if t >= 0.
2) OLS: share ~ t + post + t:post.
3) Report: post coefficient; pre-trigger mean share; jump as fold-change = (pre_mean + post_coef)/pre_mean with 95% CI from the coefficient CI.
4) PLACEBO A (time): rerun the same regression on the same series at 20 random trigger months drawn from 2019-01..2022-06 excluding ±3 months around the real trigger. Collect the 20 post coefficients.
5) PLACEBO B (openings): rerun at the REAL trigger month on 20 random control openings sampled from features.csv within ±1 decile of the case's share2019, excluding any opening matching Queen's Gambit/Bongcloud/Stafford patterns. Collect the 20 post coefficients.
6) Verdict line: where the real post coefficient sits relative to the 40 placebo coefficients (rank / max ratio).
7) Figure per case: the share time series with the fitted pre/post lines, a vertical line at the trigger, and a shaded horizontal band spanning the placebo-A coefficient range. figures/h1_qg.png, figures/h1_bongcloud.png.
8) Append numbers to exports/results.md under "## H1".

Effect sizes lead, p-values are a footnote. No other openings, no other dates, no autocorrelation corrections — the placebos are the inference story.
```

**Done when:** real coefficients sit outside the placebo band in both cases. If Bongcloud's doesn't, that's reportable too ("stunt without sustained cascade") — do not let the model fish for a better window.

---

## Phase 6 — H4 decay half-lives + optional k-means (one evening; paste MASTER.md first)

**Paste this after MASTER.md:**
```
Write analysis/h4_decay.py. Inputs: exports/shares_total.csv, exports/features.csv, plus the PC1 scores saved by h2_pca.py (save them to exports/pc_scores.csv in Phase 4 if not already — column: opening, PC1).

1) SPIKERS: openings with fold = (peak share 2020-07..2021-12) / (2019 mean share) >= 4 AND peak share >= 0.0002 AND present in features.csv. Print the list.
2) For each spiker: peak month = argmax. Fit OLS on the 12 months after the peak: ln(share) ~ months_since_peak. Keep only fits with negative slope; half_life = ln(2)/|slope| in months. Openings whose share does NOT decay (slope >= 0 or half_life > 24) are labeled "plateau".
3) Always include the Queen's Gambit aggregate series in the table regardless of fold (it is the same-shock sound control).
4) Output table to exports/results.md "## H4": opening, fold, peak month, half_life or "plateau", trickiness, PC1. Plus Spearman correlation between PC1 and half_life across spikers (plateau coded as the max observed half-life; report it both ways: with and without plateaus).
5) Figure: figures/h4_decay.png — ln(share) vs months-since-peak for the 3 case openings (Stafford, Bongcloud, Queen's Gambit) with fitted lines and half-lives in the legend.

OPTIONAL SECOND SCRIPT analysis/k3_clusters.py (only if asked): k-means k=3 on the four z-scored features from Phase 4, then one-way ANOVA + Tukey HSD (statsmodels pairwise_tukeyhsd) on ln(half_life) across clusters, spikers only. Boxplot to figures/k3_halflives.png.
```

**Done when:** the three-case decay figure tells the story on its own: trap memes die fast, the sound opening from the same shock plateaus. Log the fold/floor thresholds in decisions.md.

---

## Phase 7 — Independent audit + slide pack (half a day)

**Audit session (fresh session, paste ONLY this — deliberately no MASTER.md, no prior code):**
```
You have a SQLite database chess.sqlite with one table:
agg(month TEXT, eco TEXT, opening TEXT, bin INT, n INT, ww INT, bw INT, wsw INT, bsw INT, n_close INT, ww_close INT, bw_close INT)
where wsw/bsw are white/black wins within 20 moves and *_close columns count games with Elo difference <= 100. Write standalone SQL (and minimal Python to run it) that computes, from scratch:
1) Queen's Gambit family share of all games, per month, 2019-2022.
2) Its mean share over 2020-05..2020-10 vs 2020-11..2021-04, and the ratio.
3) Same two numbers for openings containing 'Bongcloud' around 2021-03.
4) The 2019 trickiness (max of white/black short-win share) and high-bin close-game win rate for the opening containing 'Stafford'.
Print everything.
```
Compare every number against `exports/results.md`. Mismatch = bug hunt before any slide exists.

**Slide session (paste MASTER.md + this):**
```
Draft the 7-minute slide pack as a markdown outline (one slide per heading, max 20 words of text per slide, name which figure file goes where), following the timing in MASTER.md exactly: hook + misinformation framing 40s / data & measurement 75s / H1 + placebo band 90s / H2 meme axis 120s / H4 half-lives 60s / limitations + CRISP-DM mapping 45s. Include the backup slide for the rating-bin lead-lag question (new vs pre-existing accounts answer). Then write a spoken script, max 950 words total, in plain conversational English.
```

**Done when:** you can re-derive every number on every slide from `decisions.md` + the SQL by hand. That's the defense.

---

## Known traps recap (the things a cheap model will silently get wrong)

1. Using python-chess to parse → 50× too slow, days instead of minutes.
2. Dropping the `*_close` columns from the Phase-1 schema → soundness becomes uncomputable; full re-run required.
3. Forgetting `--limit` truncation handling → can't test on partial downloads.
4. Counting short wins without the Termination == "Normal" condition → time-forfeit pollution.
5. Matching "21." without the leading space → move 121 false-positives.
6. Computing features on all years instead of frozen 2019 → endogeneity, the exact hole the design closes.
7. Reporting p-values as the headline with n ≈ 10⁸ → effect sizes lead, always.
