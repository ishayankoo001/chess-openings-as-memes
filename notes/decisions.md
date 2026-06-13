
# Decisions Log

## Phase 1 — Streaming Parser

- **Schema frozen**: `agg(month TEXT, eco TEXT, opening TEXT, bin INT, n, ww, bw, wsw, bsw, n_close, ww_close, bw_close)`
- **Elo bins**: 200-point bins, `clamp((mean // 200) * 200, 600, 2400)`
  - Coarse bins for presentation: `<1200`, `1200–1599`, `1600–1999`, `≥2000` (SQL view only)
- **Short wins**: `Termination == "Normal"` AND decisive AND `" 21."` absent from movetext (≤20 full moves)
- **Close games**: `|WhiteElo − BlackElo| ≤ 100`
- **Game length detection**: scan movetext for `" 21."` (leading space prevents false match on move 121)
- **Filters**: Rated Blitz only, no BOTs, Standard variant only (explicit presence of Variant≠Standard or FEN kills the game), Termination Normal/Time forfeit only
- **Opening field**: full `[Opening]` header value verbatim (never truncate at colon — preserves variation names like "Russian Game: Stafford Gambit")
- **No regex in hot loop**, no python-chess, no per-game DataFrames
- **Truncated .zst handling**: catch `zstandard.ZstdError`, finalize with games parsed so far

## Decisions to be filled in later phases

- Games threshold (for features, Phase 3): 5,000 games in 2019
- Close-game floor for soundness (Phase 3): 200 close games in HIGH bins; otherwise `soundness` and `punish_gap` are NULL
- HIGH bin cutoff (Phase 3): bins `[2400, 2200, 2000]`, selected by descending 2019 rating-bin distribution until cumulative share reached 10.20%
- Bongcloud exact trigger date: TBD (Phase 5)
- Queen's Gambit trigger: 2020-10-23 (Netflix release)
- Fold/floor thresholds for H4 spikers: TBD (Phase 6)


2026-06-13 — H1 reframe (LOCKED)
- QG share is FLAT across window (0.045→0.041, drifts down). Share denominator working:
  the 2020 boom lifted all openings' raw counts together; QG's SLICE did not grow.
  → QG is NOT a cascade case. It becomes the SOUND CONTROL: established mainline, share
    steady under the same shock that made Stafford spike.
- Stafford = the H1 cascade case. Label "Russian Game: Stafford Gambit" (C42) stable
  pre/post; not a dictionary artifact (verified grep 2020-07 vs 2020-08).
- Empirical breakpoint = 2020-08 (data-derived argmax of first-difference, not a Netflix-style date).
  ~4x overall, 7x vs 2019 baseline, holds ~18 months.
- Adoption concentrated in 1000-1400 bins (~5-6x); elite 2200+ barely moves (diffusion-direction
  signal, free, → backup slide). Trickiness: black-short-rate ~27% at 1000, ~12% at 2200
  (trap works on weak, fizzles vs strong = punishability gap, visible in raw counts).
- H1 cases: Stafford (cascade, break 2020-08) vs Queen's Gambit (flat control), same axes.