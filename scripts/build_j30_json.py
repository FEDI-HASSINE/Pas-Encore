#!/usr/bin/env python3
"""
Generate j30_all_parsed.json from the .sm files in data/.

Usage:
    python scripts/build_j30_json.py
"""

import json
from pathlib import Path
import sys

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.env.psplib_loader import load_all_psplib


def main():
    data_dir = Path("data")

    if not data_dir.is_dir():
        print(f"Error: {data_dir} not found", file=sys.stderr)
        sys.exit(1)

    all_data = load_all_psplib(data_dir)

    output = [
        {"instance": filename, "tasks": tasks}
        for filename, tasks in all_data.items()
    ]

    output_path = data_dir / "j30_all_parsed.json"

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(output)} instances to {output_path}")


if __name__ == "__main__":
    main()
