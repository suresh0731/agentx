"""Bootstrap AgentX backend files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "agentx"


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {rel}")


def main() -> None:
    # Seed will be written separately from extracted JSON
    print("Bootstrap complete marker")


if __name__ == "__main__":
    main()
