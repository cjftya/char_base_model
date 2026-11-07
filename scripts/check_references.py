"""Preflight four reference images without launching Blender."""

from __future__ import annotations

import argparse
from pathlib import Path

from reference_common import ReferenceError, load_references

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/reference_setup.json")
    args = parser.parse_args()
    try:
        config, views = load_references(args.config)
    except ReferenceError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"PASS: all 4 reference files found; model height = {config['character_height_m']} m")
    for name, view in views.items():
        print(f"  {name:5}: {view.width_px}x{view.height_px} px, "
              f"reference plane = {view.world_width_m:.3f}x{view.world_height_m:.3f} m")
    print("Note: Image header validation does not confirm visual consistency or image contents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
