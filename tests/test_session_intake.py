"""Synthetic header fixtures for intake, file isolation, and host path resolution."""

import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from prepare_session import downloads_directory, inspect_inputs, prepare_session
from reference_common import ReferenceError, VIEWS, image_dimensions, load_references


def png(path, width=512, height=1024):
    # Header fixtures test intake only. They are intentionally not Blender inputs.
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13)
                     + b"IHDR" + struct.pack(">II", width, height))


def jpeg(path, width=512, height=1024, marker=0xC0):
    # APP segment followed by SOF supports baseline/progressive header regressions.
    path.write_bytes(b"\xff\xd8\xff\xe0\x00\x04ab\xff" + bytes([marker])
                     + struct.pack(">HBHH", 8, 8, height, width) + b"\x01")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "input"
        self.inputs.mkdir()
        self.destination = self.root / "work"
        self.destination.mkdir()
        for name in VIEWS:
            png(self.inputs / f"{name}.png")

    def test_explicit_destination_copies_inputs_and_preserves_sources(self):
        before = (self.inputs / "front.png").read_bytes()
        with patch("prepare_session.downloads_directory", side_effect=AssertionError("not used")):
            result = prepare_session([self.inputs], destination=self.destination)
        session = Path(result["session"])
        self.assertEqual(session.parent, self.destination)
        self.assertRegex(session.name, r"^char_base_\d{8}_\d{6}$")
        config, views = load_references(Path(result["config"]))
        self.assertFalse(config["anchors_reviewed"])
        self.assertEqual(set(views), set(VIEWS))
        self.assertEqual((session / "references/front.png").read_bytes(), before)
        self.assertEqual((self.inputs / "front.png").read_bytes(), before)

    def test_four_paths_and_mixed_formats(self):
        (self.inputs / "back.png").unlink()
        jpeg(self.inputs / "BACK.JPG")
        (self.inputs / "left.png").unlink()
        jpeg(self.inputs / "left.jpeg", marker=0xC2)
        result = prepare_session(list(self.inputs.iterdir()), destination=self.destination)
        config, views = load_references(Path(result["config"]))
        self.assertEqual(config["images"]["back"]["path"], "references/back.jpg")
        self.assertEqual(views["left"].width_px, 512)

    def test_default_destination_uses_resolved_downloads(self):
        with patch("prepare_session.downloads_directory", return_value=self.destination):
            result = prepare_session([self.inputs])
        self.assertEqual(Path(result["session"]).parent, self.destination)

    def test_missing_views_gives_names_without_creating_session(self):
        (self.inputs / "back.png").unlink()
        (self.inputs / "right.png").unlink()
        with self.assertRaisesRegex(ReferenceError, "Missing views: back, right"):
            prepare_session([self.inputs], destination=self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_low_resolution_guides_and_blocks(self):
        png(self.inputs / "front.png", width=300)
        with self.assertRaisesRegex(ReferenceError, "front.*at least 512px"):
            prepare_session([self.inputs], destination=self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_different_resolutions_returns_guidance(self):
        png(self.inputs / "front.png", width=1024)
        result = prepare_session([self.inputs], destination=self.destination)
        self.assertIn("Different resolutions", result["guidance"][0])
        self.assertIn("front=1024x1024", result["guidance"][0])

    def test_duplicate_view_is_rejected(self):
        jpeg(self.inputs / "front.jpg")
        with self.assertRaisesRegex(ReferenceError, "Multiple front"):
            inspect_inputs([self.inputs])

    def test_invalid_extension_has_export_guidance(self):
        (self.inputs / "front.png").rename(self.inputs / "front.webp")
        with self.assertRaisesRegex(ReferenceError, "export as PNG, JPG, or JPEG"):
            inspect_inputs([self.inputs])

    def test_corrupt_jpeg_is_rejected(self):
        bad = self.inputs / "front.jpg"
        bad.write_bytes(b"\xff\xd8\xff\xe0\x00\x01")
        with self.assertRaisesRegex(ReferenceError, "Invalid JPEG header"):
            image_dimensions(bad)

    def test_failed_copy_cleans_only_its_new_session(self):
        unrelated = self.destination / "keep.txt"
        unrelated.write_text("keep")
        with patch("prepare_session.shutil.copyfile", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                prepare_session([self.inputs], destination=self.destination)
        self.assertEqual(list(self.destination.iterdir()), [unrelated])

    def test_timestamp_collision_preserves_previous_session(self):
        from datetime import datetime

        now = datetime(2026, 11, 7, 14, 30, 25)
        with patch("prepare_session.datetime") as clock:
            clock.now.return_value = now
            first = prepare_session([self.inputs], destination=self.destination)
            original = Path(first["config"]).read_bytes()
            with self.assertRaisesRegex(ReferenceError, "already exists in this second"):
                prepare_session([self.inputs], destination=self.destination)
        self.assertEqual(Path(first["config"]).read_bytes(), original)

    def test_linux_xdg_localized_downloads(self):
        config_dir = self.root / ".config"
        config_dir.mkdir()
        localized = self.root / "다운로드"
        localized.mkdir()
        (config_dir / "user-dirs.dirs").write_text(
            'XDG_DOWNLOAD_DIR="$HOME/다운로드"\n', encoding="utf-8"
        )
        with patch("prepare_session.sys.platform", "linux"), \
             patch("prepare_session.Path.home", return_value=self.root), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_dir)}):
            self.assertEqual(downloads_directory(), localized)

    def test_linux_fallback_requires_existing_downloads(self):
        with patch("prepare_session.sys.platform", "linux"), \
             patch("prepare_session.Path.home", return_value=self.root), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root / "absent")}):
            with self.assertRaisesRegex(ReferenceError, "unavailable or disabled"):
                downloads_directory()
            default = self.root / "Downloads"
            default.mkdir()
            self.assertEqual(downloads_directory(), default)

    def test_windows_registry_redirected_downloads(self):
        winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(), OpenKey=MagicMock(),
            QueryValueEx=Mock(return_value=(str(self.destination), 2))
        )
        with patch.dict(sys.modules, {"winreg": winreg}), \
             patch("prepare_session.sys.platform", "win32"):
            self.assertEqual(downloads_directory(), self.destination)
        self.assertIn("User Shell Folders", winreg.OpenKey.call_args.args[1])

    def test_home_as_disabled_downloads_requires_destination(self):
        config_dir = self.root / "xdg"
        config_dir.mkdir()
        (config_dir / "user-dirs.dirs").write_text('XDG_DOWNLOAD_DIR="$HOME"\n')
        with patch("prepare_session.sys.platform", "linux"), \
             patch("prepare_session.Path.home", return_value=self.root), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_dir)}):
            with self.assertRaisesRegex(ReferenceError, "disabled"):
                downloads_directory()
