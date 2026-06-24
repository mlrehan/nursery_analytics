"""Tiny CLI: ``python -m app.cli migrate|seed|reset-seed``."""
from __future__ import annotations

import sys


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "migrate":
        from app.migrations.runner import run_migrations
        run_migrations()
    elif cmd == "seed":
        from app.seed.seed import seed
        seed(force=False)
    elif cmd == "reset-seed":
        from app.seed.seed import seed
        seed(force=True)
    else:
        print("usage: python -m app.cli [migrate|seed|reset-seed]")
        sys.exit(1)


if __name__ == "__main__":
    main()
