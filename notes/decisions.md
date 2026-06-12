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

- Games threshold (for features, Phase 3): TBD
- Close-game floor for soundness (Phase 3): TBD
- HIGH bin cutoff (Phase 3): TBD
- Bongcloud exact trigger date: TBD (Phase 5)
- Queen's Gambit trigger: 2020-10-23 (Netflix release)
- Fold/floor thresholds for H4 spikers: TBD (Phase 6)