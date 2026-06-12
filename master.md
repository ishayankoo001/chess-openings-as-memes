# MASTER.md — paste as the first message in every analysis/slides session (roadmap phases 4–7)

You are helping a bachelor student (DMA2 data-mining course, Sapienza) execute a LOCKED project design for a 7-minute graded presentation. Your job: implement code, debug, draft slides/scripts. Do NOT propose new methods, metrics, or scope changes. If something is ambiguous, resolve it within this spec; do not redesign. Repo layout, phase ordering, and implementation specs live in ROADMAP.md — this file defines WHAT, not HOW.

## PROJECT
"Openings as memes" — chess openings treated as spreadable content, trigger events as injection points, mirroring misinformation-cascade research (the professor's field).

## ALLOWED METHODS (course syllabus only — never use other vocabulary)
CRISP-DM, linear regression, t-tests, chi-squared, ANOVA/Tukey, Pearson/Spearman, z-score standardization, log transforms, feature engineering, one-hot encoding, binning, PCA, k-means, SQL.
Vocabulary rule: say "one-hot era dummy + month×era interaction in linear regression," NEVER "interrupted time series." Say "lagged correlation," never "Granger." No method names outside the list.

## DATA & PIPELINE
- Source: Lichess open database (database.lichess.org), monthly standard rated PGN dumps (.pgn.zst), CC0-licensed. Name and cite it openly — data provenance is the data-understanding phase of CRISP-DM and is graded.
- Months: all of 2019 (frozen feature/baseline window) + 2020-07 through 2021-12 (trigger window). Download → aggregate → delete; never store decompressed data.
- ONE streaming pass per file: headers + a single-line movetext scan ONLY to detect game length (≤20 full moves). No move parsing, no engines, no per-game storage.
- Filters during the stream: rated blitz only; exclude BOT titles; Termination must be "Normal" or "Time forfeit"; exclude non-standard games ([Variant] header present and ≠ "Standard", or [FEN] present — kills thematic/from-position arenas).
- Output ONE aggregate table (SQLite), schema FROZEN:
  agg(month TEXT, eco TEXT, opening TEXT, bin INT, n, ww, bw, wsw, bsw, n_close, ww_close, bw_close)
  • opening = the full [Opening] header VERBATIM, plus ECO. NEVER truncate at the colon — variation names live after it ("Russian Game: Stafford Gambit"). Families are built later in SQL with LIKE patterns.
  • short win (wsw/bsw) = decisive AND Termination "Normal" AND decided in ≤ 20 full moves.
  • close (*_close columns) = |WhiteElo − BlackElo| ≤ 100. These MUST be counted at parse time — aggregation destroys per-game Elo differences and they cannot be recovered later.
  • bin = clamp((mean(WhiteElo, BlackElo) // 200) × 200, 600, 2400). Parse at 200-point bins; the 4 coarse presentation bins (<1200, 1200–1599, 1600–1999, ≥2000) exist only as a SQL view. Merging bins later is always possible; splitting never is.
- Protagonist side per opening: DEFAULT rule = side with the higher 2019 short-win share (ties → white). data/side_map.csv exists only as a manual override for focal openings (Stafford→black, Englund→black, Bongcloud→white, Queen's Gambit→white). Never hand-label the full sample.
- Adoption metric everywhere: opening's SHARE of games per month — overall share as the primary series, share within rating bins for robustness (normalizes the post-Netflix boom). Never raw counts.
- Everything downstream = SQL on agg + small statsmodels regressions. SQL (joins, grouping, aggregation) is itself graded coursework — keep the queries visible.

## FEATURES — frozen 2019 window ONLY (avoids endogeneity), openings with ≥ 5,000 games in 2019, then z-scored:
- trickiness = protagonist short wins / games (2019, all bins)
- soundness = protagonist win rate among CLOSE games in HIGH bins (HIGH = the top bins jointly holding ~10% of 2019 games; NULL and excluded if < 200 close games there)
- punishability gap = protagonist close-game winrate in bins ≤ 1200 − soundness
- surprise = −ln(2019 overall share)

## HYPOTHESES & ANALYSES
**H1 (cascade):** linear regression of monthly share on month index + era dummy (one-hot post-trigger) + month×era interaction, window = trigger ± 12 months. Cases ONLY: Queen's Gambit family (trigger 2020-10-23 → first post month 2020-11) and Bongcloud (March 2021 — verify the exact Nakamura–Carlsen date by web search before locking).
Placebos: (A) the same regression at 20 random trigger months excluding ± 3 months around the real one; (B) the real trigger month on 20 control openings sampled within ± 1 decile of the case's 2019 share, excluding focal patterns. The real era-dummy effect must sit outside the placebo distribution; plot it against the placebo band.

**H2 (centerpiece):** PCA on the 4 z-scored features → interpret PC1/PC2, label the "meme axis" (orient PC1 so trickiness loads positive); regress log peak fold-change (peak monthly share in trigger window ÷ 2019 baseline share) on the components. Sample = ALL openings above threshold, never just known-viral ones. Show the loadings table + the feature correlation matrix (multicollinearity justifies PCA). Slide: openings scattered on PC1×PC2 with Bongcloud/Stafford/Englund vs Ruy Lopez/Italian labeled. Influence check: Cook's distance, refit without the top 5, report whether PC1's sign and significance survive.

**H4 (decay):** log-transform post-peak share, OLS on months-since-peak (all available post-peak months, ≤ 12 — data ends 2021-12; record the actual window in decisions.md), half-life = ln 2 / |slope|; slope ≥ 0 or half-life > 24 months = "plateau". Contrast tricky-viral vs sound openings; Queen's Gambit = same-shock SOUND control — if it plateaus while the Bongcloud halves in weeks, that is the punchline.

**Optional (only if everything else is done):** k-means (k=3) on the same feature matrix + ANOVA/Tukey on log half-lives across clusters.

## REPORTING RULES
n ≈ 10⁸ ⇒ everything is "statistically significant" — lead with EFFECT SIZES (fold-change with CI, odds ratios, Cramér's V where chi-squared is used); p-values are a footnote. Every figure: large fonts, one message per slide.

## CUT — do not reintroduce under any circumstances
Stafford trigger-date/breakpoint analysis (Stafford = just a row in H2/H4); rating-bin lead-lag "H3" (backup slide only; Q&A answer = would require splitting new vs pre-existing accounts); name-memability feature; Google Trends regressor (future-work mention only); sentiment analysis; engine evaluations (future-work mention: depth-30 minus depth-5 eval gap as a better trickiness metric); network analysis.

## TALK (7 min, rehearse twice with a timer; front-load results)
hook + misinformation framing 40s → data & measurement (share-not-counts, filters, frozen-2019 features) 75s → H1 + placebo band 90s → H2 meme axis 120s → H4 half-lives 60s → limitations + CRISP-DM mapping slide 45s.
Limitations to state explicitly: gambit acceptance gate (Stafford requires White to capture on e5, so frequency partly reflects opponents' choices); rating-bin composition changed during the 2020 boom (new accounts entered low bins).