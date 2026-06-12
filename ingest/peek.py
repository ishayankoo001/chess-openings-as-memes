#!/usr/bin/env python3
"""Phase 0 — Stream a Lichess PGN zstd dump, inspect headers, count games."""

import sys
import io
import zstandard


def parse_header_line(line: str) -> tuple[str, str] | None:
    """Extract (key, value) from a PGN header line like [Key "Value"].
    Returns None if the line is not a header."""
    if not line.startswith("["):
        return None
    # Find the first space after '[' — key is between '[' and first space
    key_end = line.find(" ")
    if key_end == -1:
        return None
    key = line[1:key_end]
    # Value is between the two double-quotes
    first_quote = line.find('"', key_end)
    second_quote = line.find('"', first_quote + 1)
    if first_quote == -1 or second_quote == -1:
        return None
    value = line[first_quote + 1:second_quote]
    return key, value


def main():
    if len(sys.argv) < 2:
        print("Usage: python peek.py <path/to/file.pgn.zst>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

    # Open and stream-decompress
    with open(path, "rb") as fh:
        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")

            game: dict[str, str] = {}
            in_headers = True
            game_count = 0
            printed_previews = 0

            try:
                for line in text_stream:
                    stripped = line.rstrip("\n")

                    if stripped == "":
                        # Blank line between headers and movetext, or after movetext
                        continue

                    if stripped.startswith("["):
                        # Header line
                        parsed = parse_header_line(stripped)
                        if parsed is not None:
                            key, value = parsed
                            game[key] = value
                        in_headers = True
                    elif in_headers:
                        # First non-empty, non-'[' line after headers = movetext
                        game["_movetext"] = stripped
                        game_count += 1

                        if printed_previews < 5:
                            # Pretty-print the game
                            print(f"\n=== Game {game_count} ===")
                            for k, v in game.items():
                                if k == "_movetext":
                                    print(f"  movetext: {v[:120]}{'...' if len(v) > 120 else ''}")
                                else:
                                    print(f"  [{k} \"{v}\"]")
                            printed_previews += 1

                        # Reset for next game
                        game = {}
                        in_headers = False
                    else:
                        # Continuation of movetext (multi-line) — ignore
                        pass

                    if game_count > 0 and game_count % 100_000 == 0:
                        print(f"\r... {game_count:,} games parsed", end="", flush=True)

            except zstandard.ZstdError as e:
                # Truncated file — expected during testing
                print(f"\nZstd error (truncated input?): {e}")

    print(f"\n\nTotal games: {game_count:,}")


if __name__ == "__main__":
    main()