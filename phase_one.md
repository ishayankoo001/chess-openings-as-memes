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