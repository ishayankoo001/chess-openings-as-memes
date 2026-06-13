MASTER.md — paste as the first message in every analysis/slides session (roadmap phases 4–7)
You are helping a bachelor student (DMA2 data-mining course, Sapienza) execute a LOCKED project design for a 7-minute graded presentation. Your job: implement code, debug, draft slides/scripts. Do NOT propose new methods, metrics, or scope changes. If something is ambiguous, resolve it within this spec; do not redesign. Repo layout, phase ordering, and implementation specs live in ROADMAP.md — this file defines WHAT, not HOW.

PROJECT
"Openings as memes" — chess openings treated as spreadable content, mirroring misinformation-cascade research (the professor's field). Core finding: a catchy-but-unsound trap opening (Stafford Gambit) spreads like a meme during the 2020 boom, while a sound-but-established mainline (Queen's Gambit) holds a flat share under the identical shock. Same conditions, opposite behavior — the misinformation analogy made visible.

ALLOWED METHODS (course syllabus only — never use other vocabulary)
CRISP-DM, linear regression, t-tests, chi-squared, ANOVA/Tukey, Pearson/Spearman, z-score standardization, log transforms, feature engineering, one-hot encoding, binning, PCA, k-means, SQL. Vocabulary rule: say "one-hot era dummy + month×era interaction in linear regression," NEVER "interrupted time series." Say "lagged correlation," never "Granger." No method names outside the list.

DATA & PIPELINE
Source: Lichess open database (database.lichess.org), monthly standard rated PGN dumps (.pgn.zst), CC0-licensed. Name and cite it openly — data provenance is the data-understanding phase of CRISP-DM and is graded.
Months: all of 2019 (frozen feature/baseline window) + 2020-07 through 2021-12 (trigger window). Pipeline already executed; 30 months aggregated. Database rebuilds from data/agg/ CSVs via db/build_db.py.
ONE streaming pass per file: headers + a single-line movetext scan ONLY to detect game length (≤20 full moves). No move parsing, no engines, no per-game storage.
Filters during the stream: rated blitz only; exclude BOT titles; Termination must be "Normal" or "Time forfeit"; exclude non-standard games ([Variant] present and ≠ "Standard", or [FEN] present).
Aggregate table (SQLite), schema FROZEN: agg(month TEXT, eco TEXT, opening TEXT, bin INT, n, ww, bw, wsw, bsw, n_close, ww_close, bw_close). opening = full [Opening] header VERBATIM + ECO; families built in SQL with LIKE. short win (wsw/bsw) = decisive AND Termination "Normal" AND ≤ 20 full moves. close (*_close) = |WhiteElo − BlackElo| ≤ 100. bin = clamp((mean Elo // 200) × 200, 600, 2400); coarse presentation bins are a SQL view.
Junk edge-months exist (2018-12, 2022-01 from date spillover) — every analysis query filters month BETWEEN '2019-01' AND '2021-12'.
Protagonist side: DEFAULT = side with higher 2019 short-win share (ties → white); data/side_map.csv overrides focal openings (Stafford→black, Queen's Gambit→white).
Adoption metric everywhere: opening's SHARE of games per month — overall share primary, share within rating bins for robustness. Never raw counts. (This denominator is load-bearing: it is why QG reads flat despite its raw count doubling in the boom, and why Stafford's spike is real signal rather than general growth.)
Everything downstream = SQL on agg + small statsmodels regressions. Keep queries visible — SQL is graded.

FEATURES — frozen 2019 window ONLY (avoids endogeneity), openings with ≥ 5,000 games in 2019, then z-scored:
trickiness = protagonist short wins / games (2019, all bins)
soundness = protagonist win rate among CLOSE games in HIGH bins (HIGH = bins 2000/2200/2400, jointly ~10.2% of 2019 games; NULL and excluded if < 200 close games there)
punishability gap = protagonist close-game winrate in bins ≤ 1200 − soundness
surprise = −ln(2019 overall share)

HYPOTHESES & ANALYSES
H1 (cascade): linear regression of monthly share on month index + era dummy (one-hot post-break) + month×era interaction, window = break ± 12 months.
  • Cascade case: Stafford Gambit (ECO C42, "Russian Game: Stafford Gambit"). The breakpoint is LOCATED FROM THE DATA, not assumed — take the month of largest first-difference in the share series (expected ~2020-08) and confirm it is the maximum; do NOT hard-code a date as the premise. Label verified stable pre/post (not a dictionary artifact).
  • Sound control: Queen's Gambit family, plotted on the SAME axes — flat share across the window is the result, not a failure. The contrast (Stafford steps up, QG stays flat under the same 2020 shock) is the H1 slide and the project's thesis in one chart. The control is not decoration: it is what rules out "this is just the boom."
  • Placebos: (A) the same break regression at 20 random months excluding ± 3 months around the located break; (B) the located break month on 20 control openings sampled within ± 1 decile of Stafford's 2019 share. Stafford's era-dummy effect must sit outside both placebo distributions; plot it against the band. The placebos ARE the inference (with n this large, p-values are meaningless).

H2 (centerpiece): PCA on the 4 z-scored features → interpret PC1/PC2, label the "meme axis" (orient PC1 so trickiness loads positive); regress log peak fold-change (peak monthly share in trigger window ÷ 2019 baseline share) on the components. Sample = ALL openings above threshold, never just known-viral ones. Show loadings table + feature correlation matrix (multicollinearity justifies PCA). Slide: openings scattered on PC1×PC2 with Stafford/Englund (trap corner) vs Queen's Gambit/Ruy Lopez/Italian (sound corner) labeled. Influence check: Cook's distance, refit without top 5, report whether PC1's sign and significance survive.

H4 (decay): log-transform post-peak share, OLS on months-since-peak (all available post-peak months, ≤ 12 — data ends 2021-12; record actual window in decisions.md), half-life = ln 2 / |slope|; slope ≥ 0 or half-life > 24 months = "plateau". Contrast tricky-viral vs sound. Bongcloud (label exists only from 2021; no pre-period, so it appears ONLY here) is the fast-decay meme; Queen's Gambit is the same-era sound plateau. Stafford's post-peak decay rate is the bridge between H1 and H2.

Optional (only if everything else is done): k-means (k=3) on the feature matrix + ANOVA/Tukey on log half-lives across clusters.

REPORTING RULES
n ≈ 10⁸ ⇒ everything is "statistically significant" — lead with EFFECT SIZES (fold-change with CI, odds ratios, Cramér's V where chi-squared is used); p-values are a footnote. Every figure: large fonts, one message per slide.

CUT — do not reintroduce under any circumstances
Bongcloud as an H1 or H2 case (no pre-2021 labels in the dumps — H4 only); rating-bin lead-lag as a formal hypothesis (the low-bin-leads signal is visible in raw Stafford counts and belongs on a backup slide only; Q&A answer = a clean test would require splitting new vs pre-existing accounts); name-memability feature; Google Trends regressor (future-work mention only); sentiment analysis; engine evaluations (future-work mention: depth-30 minus depth-5 eval gap as a better trickiness metric); network analysis.

TALK (7 min, rehearse twice with a timer; front-load results)
hook + misinformation framing 40s → data & measurement (share-not-counts, filters, frozen-2019 features) 75s → H1 Stafford-vs-QG break + placebo band 90s → H2 meme axis 120s → H4 half-lives 60s → limitations + CRISP-DM mapping slide 45s. Limitations to state explicitly: Stafford's break coincides with the general boom — the share denominator and the flat QG control on the same axes are the defense; gambit acceptance gate (Stafford requires White to capture on e5, so frequency partly reflects opponents' choices); opening labels are export-time stamps (one focal opening, Bongcloud, lacks pre-2021 labels and so appears only in decay); rating-bin composition changed during the 2020 boom.