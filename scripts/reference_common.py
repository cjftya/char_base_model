"""Reference input validation and orthographic calibration (no Blender dependency)."""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

VIEWS = ("front", "back", "left", "right")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ReferenceError(ValueError):
    """Invalid project reference input."""


@dataclass(frozen=True)
class ReferenceView:
    name: str
    path: Path
    width_px: int
    height_px: int
    head_y: float
    foot_y: float
    center_x: float
    world_width_m: float
    world_height_m: float
    offset_x_m: float
    offset_z_m: float


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read the PNG header; Blender performs full image decoding later."""
    try:
        with path.open("rb") as image:
            header = image.read(24)
    except OSError as exc:
        raise ReferenceError(f"Cannot read {path}: {exc}") from exc
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ReferenceError(f"Not a valid PNG header: {path}")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise ReferenceError(f"Invalid dimensions: {path}")
    return width, height


def _ratio(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReferenceError(f"{key} must be a number between 0 and 1")
    if not 0 <= value <= 1:
        raise ReferenceError(f"{key} must be between 0 and 1")
    return float(value)


def load_references(config_path: Path) -> tuple[dict, dict[str, ReferenceView]]:
    """Validate images and calibrate world Z=0 soles / Z=height crown."""
    config_path = config_path.resolve()
    root = config_path.parent.parent
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceError(f"Cannot load config {config_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise ReferenceError("Config root must be an object")

    height = config.get("character_height_m")
    distance = config.get("plane_offset_m")
    opacity = config.get("opacity")
    for key, value in (("character_height_m", height), ("plane_offset_m", distance)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 1e6:
            raise ReferenceError(f"{key} must be positive and fit in Blender coordinates")
    if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0 < opacity <= 1:
        raise ReferenceError("opacity must be greater than 0 and at most 1")

    images = config.get("images")
    if not isinstance(images, dict) or set(images) != set(VIEWS):
        raise ReferenceError("images must contain exactly: front, back, left, right")

    views: dict[str, ReferenceView] = {}
    seen_paths = set()
    for name in VIEWS:
        spec = images[name]
        if not isinstance(spec, dict):
            raise ReferenceError(f"images.{name} must be an object")
        filename = spec.get("path")
        if not isinstance(filename, str) or Path(filename).suffix.lower() != ".png":
            raise ReferenceError(f"images.{name}.path must be a .png path")
        if Path(filename).is_absolute():
            raise ReferenceError(f"Path must be relative to the project root: {filename}")
        try:
            path = (root / filename).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ReferenceError(f"Cannot resolve {name} image path: {exc}") from exc
        if not path.is_relative_to(root):
            raise ReferenceError(f"Path must be inside project root: {filename}")
        if not path.is_file():
            raise ReferenceError(f"Missing {name} image: {path}")
        if path in seen_paths:
            raise ReferenceError(f"Each view needs a separate PNG file: {path}")
        seen_paths.add(path)
        width_px, height_px = png_dimensions(path)
        head_y = _ratio(spec.get("head_y"), f"images.{name}.head_y")
        foot_y = _ratio(spec.get("foot_y"), f"images.{name}.foot_y")
        center_x = _ratio(spec.get("center_x"), f"images.{name}.center_x")
        if foot_y <= head_y:
            raise ReferenceError(f"images.{name}: foot_y must be below head_y")
        scale = float(height) / ((foot_y - head_y) * height_px)
        world_width = width_px * scale
        world_height = height_px * scale
        if any(not math.isfinite(size) or not 1e-6 <= size <= 1e6
               for size in (world_width, world_height)):
            raise ReferenceError(f"images.{name}: calibrated size outside supported range")
        views[name] = ReferenceView(
            name=name, path=path, width_px=width_px, height_px=height_px,
            head_y=head_y, foot_y=foot_y, center_x=center_x,
            world_width_m=world_width, world_height_m=world_height,
            offset_x_m=(0.5 - center_x) * world_width,
            offset_z_m=(foot_y - 0.5) * world_height,
        )
    return config, views
