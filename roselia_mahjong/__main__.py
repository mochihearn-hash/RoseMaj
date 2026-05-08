from __future__ import annotations

import sys
from pathlib import Path


if __package__ in {None, ""}:
    # Allows PyCharm or other IDEs to run this file directly as a script.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from roselia_mahjong.cli import main
else:
    from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
