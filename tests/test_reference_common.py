"""Pure Python contract tests; Blender integration is not exercised here."""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reference_common import ReferenceError, VIEWS, load_references  # noqa: E402


def png(path: Path, width: int = 200, height: int = 400) -> None:
    # The input validator intentionally checks PNG headers only.
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height))


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "references").mkdir()
        self.data = {
            "character_height_m": 2.0, "plane_offset_m": 3.0, "opacity": 0.5,
            "images": {name: {"path": f"references/{name}.png", "head_y": 0.1,
                               "foot_y": 0.9, "center_x": 0.5} for name in VIEWS},
        }
        for name in VIEWS:
            png(self.root / "references" / f"{name}.png")

    def load(self):
        config = self.root / "config/reference_setup.json"
        config.write_text(json.dumps(self.data), encoding="utf-8")
        return load_references(config)

    def test_valid_four_views_and_world_height(self):
        _, views = self.load()
        self.assertEqual(tuple(views), VIEWS)
        self.assertAlmostEqual(views["front"].world_height_m, 2.5)
        self.assertAlmostEqual(views["front"].world_width_m, 1.25)
        self.assertAlmostEqual(views["front"].offset_z_m, 1.0)

    def test_missing_image_is_rejected(self):
        (self.root / "references/right.png").unlink()
        with self.assertRaisesRegex(ReferenceError, "Missing right"):
            self.load()

    def test_bad_anchor_is_rejected(self):
        self.data["images"]["front"]["foot_y"] = 0.05
        with self.assertRaisesRegex(ReferenceError, "foot_y must be below"):
            self.load()

    def test_outside_project_path_is_rejected(self):
        self.data["images"]["left"]["path"] = "../../outside.png"
        with self.assertRaisesRegex(ReferenceError, "inside project root"):
            self.load()

    def test_incorrect_view_set_is_rejected(self):
        del self.data["images"]["right"]
        with self.assertRaisesRegex(ReferenceError, "exactly"):
            self.load()

    def test_canvas_horizontal_offset(self):
        self.data["images"]["back"]["center_x"] = 0.4
        _, views = self.load()
        self.assertAlmostEqual(views["back"].offset_x_m, 0.125)

    def test_calibrated_portrait_and_landscape_anchors(self):
        for name, width, height in (("front", 200, 400), ("left", 640, 400)):
            png(self.root / "references" / f"{name}.png", width, height)
            self.data["images"][name].update(head_y=0.2, foot_y=0.7, center_x=0.25)
        config, views = self.load()
        for view in (views["front"], views["left"]):
            crown = view.offset_z_m + (0.5 - view.head_y) * view.world_height_m
            sole = view.offset_z_m + (0.5 - view.foot_y) * view.world_height_m
            axis = view.offset_x_m + (view.center_x - 0.5) * view.world_width_m
            self.assertAlmostEqual(crown, config["character_height_m"])
            self.assertAlmostEqual(sole, 0)
            self.assertAlmostEqual(axis, 0)
            self.assertAlmostEqual(view.world_width_m / view.world_height_m,
                                   view.width_px / view.height_px)

    def test_bad_extension_is_rejected(self):
        self.data["images"]["right"]["path"] = "references/right.jpg"
        with self.assertRaisesRegex(ReferenceError, r"must be a \.png"):
            self.load()

    def test_duplicate_path_is_rejected(self):
        self.data["images"]["right"]["path"] = "references/left.png"
        with self.assertRaisesRegex(ReferenceError, "separate PNG"):
            self.load()

    def test_unreadable_png_is_rejected(self):
        from unittest.mock import patch

        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            from reference_common import png_dimensions
            with self.assertRaisesRegex(ReferenceError, "Cannot read"):
                png_dimensions(self.root / "references/front.png")

    def test_non_finite_height_is_rejected(self):
        self.data["character_height_m"] = float("nan")
        with self.assertRaisesRegex(ReferenceError, "character_height_m"):
            self.load()


if __name__ == "__main__":
    unittest.main()
