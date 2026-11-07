"""Stage named four-view references in a timestamped Blender-host working directory."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from reference_common import ReferenceError, VIEWS, image_dimensions, load_references

MIN_SHORT_SIDE = 512
EXTENSIONS = {".png", ".jpg", ".jpeg"}


def downloads_directory() -> Path:
    """Resolve Windows redirected Downloads and Linux XDG user directories."""
    home = Path.home()
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
            target = Path(os.path.expandvars(value))
        except OSError as exc:
            raise ReferenceError("Cannot locate Windows Downloads. Supply its actual host path.") from exc
    elif sys.platform.startswith("linux"):
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        user_dirs = config_home / "user-dirs.dirs"
        target = home / "Downloads"
        if user_dirs.exists():
            try:
                text = user_dirs.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ReferenceError(f"Cannot read {user_dirs}. Supply the actual Downloads path.") from exc
            for line in text.splitlines():
                match = re.fullmatch(r'\s*XDG_DOWNLOAD_DIR="([^"]*)"\s*(?:#.*)?', line)
                if match:
                    value = match[1].replace("${HOME}", str(home)).replace("$HOME", str(home))
                    if "$" in value:
                        raise ReferenceError("Unsupported XDG Downloads path. Supply its actual path.")
                    target = Path(value)
                    break
    else:
        raise ReferenceError("Supply the Downloads path for this operating system.")
    if not target.is_absolute() or not target.is_dir() or target.resolve() == home.resolve():
        raise ReferenceError("Downloads directory is unavailable or disabled. Supply its actual host path.")
    return target.resolve()


def inspect_inputs(inputs) -> tuple[dict[str, Path], list[str]]:
    paths = [Path(path).expanduser() for path in inputs]
    if len(paths) == 1 and paths[0].is_dir():
        try:
            paths = list(paths[0].iterdir())
        except OSError as exc:
            raise ReferenceError(f"Cannot read image folder. Check its path and permissions: {exc}") from exc
    images = {}
    for path in paths:
        view = path.stem.lower()
        if view not in VIEWS:
            continue
        if path.suffix.lower() not in EXTENSIONS:
            raise ReferenceError(f"{path.name}: export as PNG, JPG, or JPEG.")
        if view in images:
            raise ReferenceError(f"Multiple {view} images. Keep one front/back/left/right image per view.")
        if not path.is_file():
            raise ReferenceError(f"Cannot access {path}. Provide files readable on the Blender host.")
        images[view] = path.resolve()

    missing = [name for name in VIEWS if name not in images]
    if missing:
        raise ReferenceError(
            f"Missing views: {', '.join(missing)}. Provide front, back, left, right "
            "with .png, .jpg, or .jpeg extensions."
        )
    sizes = {name: image_dimensions(path) for name, path in images.items()}
    small = [f"{name} ({w}x{h})" for name, (w, h) in sizes.items()
             if min(w, h) < MIN_SHORT_SIDE]
    if small:
        raise ReferenceError(
            f"Resolution too low: {', '.join(small)}. Supply originals with a short side "
            f"of at least {MIN_SHORT_SIDE}px, preferably 1024px or more. "
            "Upscaling cannot restore missing details."
        )
    guidance = []
    if len(set(sizes.values())) > 1:
        details = ", ".join(f"{name}={w}x{h}" for name, (w, h) in sizes.items())
        guidance.append(
            f"Different resolutions: {details}. Prefer matching canvas sizes and character proportions. "
            "Check crown/sole/centerline anchors separately for each image. "
            "Uniform scaling can align margins but cannot correct pose or perspective."
        )
    return images, guidance


def prepare_session(inputs, *, destination=None) -> dict:
    """Copy inputs and write run-local configuration without changing the skill."""
    images, guidance = inspect_inputs(inputs)
    destination = Path(destination).expanduser() if destination is not None else downloads_directory()
    if not destination.is_absolute() or not destination.is_dir():
        raise ReferenceError("Supply an existing absolute destination folder on the Blender host.")
    session = destination.resolve() / datetime.now().strftime("char_base_%Y%m%d_%H%M%S")
    try:
        session.mkdir()
    except FileExistsError as exc:
        raise ReferenceError("A run already exists in this second. Retry to create a fresh timestamp.") from exc
    except OSError as exc:
        raise ReferenceError(f"Cannot create a session in the destination. Check write permissions: {exc}") from exc
    try:
        (session / "references").mkdir()
        (session / "config").mkdir()
        config = {
            "character_height_m": 1.6, "plane_offset_m": 2.5, "opacity": 0.5,
            "anchors_reviewed": False, "input_guidance": guidance, "images": {},
        }
        for name in VIEWS:
            filename = f"{name}{images[name].suffix.lower()}"
            shutil.copyfile(images[name], session / "references" / filename)
            config["images"][name] = {
                "path": f"references/{filename}",
                "head_y": 0.0, "foot_y": 1.0, "center_x": 0.5,
            }
        config_path = session / "config/reference_setup.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        load_references(config_path)
    except Exception:
        # This directory was created exclusively by this call.
        shutil.rmtree(session)
        raise
    return {
        "status": "INPUTS_STAGED_UNVERIFIED",
        "session": str(session),
        "config": str(config_path),
        "output": str(session / "reference_stage.blend"),
        "guidance": guidance,
        "next": "Inspect the four images, set anchors and anchors_reviewed=true, then run setup via MCP.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="One folder or four named image paths")
    parser.add_argument("--destination", type=Path, help="Override the parent folder; defaults to host Downloads")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare_session(args.inputs, destination=args.destination), indent=2))
    except (ReferenceError, OSError) as exc:
        print(f"INPUT_ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
