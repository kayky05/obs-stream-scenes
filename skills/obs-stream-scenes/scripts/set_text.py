#!/usr/bin/env python3
"""Change a live text (lesson title, "now playing", starting-soon headline...) while OBS is running.

    python set_text.py <kit_dir>                      # list the texts and their current values
    python set_text.py <kit_dir> title "Episode 12: the boss fight"
    python set_text.py <kit_dir> label "MÓDULO 02  ·  AULA 01" title "Funil de vendas"

The scenes re-read text/<key>.txt every 2 seconds, so the change shows up without touching OBS.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_paths import load_lock  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    lock = load_lock(sys.argv[1])
    text_dir = Path(lock["text_dir"])
    pairs = sys.argv[2:]
    if not pairs:
        for path in sorted(text_dir.glob("*.txt")):
            print(f"{path.stem:<12} {path.read_text(encoding='utf-8-sig').strip()}")
        return 0
    if len(pairs) % 2:
        print("Give key/value pairs: set_text.py <kit> title \"New title\"", file=sys.stderr)
        return 1
    known = {p.stem for p in text_dir.glob("*.txt")}
    for key, value in zip(pairs[::2], pairs[1::2]):
        if key not in known:
            print(f"Unknown text {key!r}. Known: {', '.join(sorted(known))}", file=sys.stderr)
            return 1
        (text_dir / f"{key}.txt").write_text(value.replace("\n", " ").strip() + "\n", encoding="utf-8")
        print(f"{key} = {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
