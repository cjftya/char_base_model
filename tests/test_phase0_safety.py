"""Exercise Phase 0 ownership, output guards, and rollback without Blender."""

import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from test_reference_common import ReferenceError


class Collection(dict):
    library = None
    users = 1


class ManagedObject(Collection):
    children = ()


class Links(list):
    def get(self, name):
        return next((item for item in self if item.name == name), None)

    def link(self, item):
        self.append(item)
        if isinstance(item, ManagedObject):
            item.users_collection = (self.owner,)


class Pool(Links):
    def __init__(self, factory):
        super().__init__()
        self.factory = factory

    def new(self, name, *args):
        item = self.factory(*args)
        item.name = name
        self.append(item)
        return item

    def remove(self, item, do_unlink=True):
        if isinstance(item, ManagedObject):
            links = item.users_collection[0].objects
            del links[next(i for i, candidate in enumerate(links) if candidate is item)]
        del self[next(i for i, candidate in enumerate(self) if candidate is item)]


def new_collection():
    collection = Collection()
    collection.objects = Links()
    collection.objects.owner = collection
    return collection


def new_object(data):
    obj = ManagedObject()
    obj.data = data
    obj.type = "CAMERA" if data is not None else "EMPTY"
    obj.location = (0, 0, 0)
    return obj


def new_camera_data():
    data = Collection()
    data.users = 0
    return data


class Phase0SafetyTests(unittest.TestCase):
    def setUp(self):
        self.scene = SimpleNamespace(
            collection=SimpleNamespace(children={}), camera=None
        )
        self.data = SimpleNamespace(collections={}, objects={}, images=Mock())
        bpy = SimpleNamespace(data=self.data, context=SimpleNamespace(scene=self.scene))
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        with patch.dict(sys.modules, {
            "bpy": bpy, "mathutils": SimpleNamespace(Euler=Mock(), Vector=Mock())
        }):
            self.setup = runpy.run_path(str(scripts / "setup_references.py"))

    def owned_reference(self):
        owner = self.setup["OWNER"]
        name = self.setup["COLLECTIONS"][0]
        target = Collection({owner: name})
        self.data.collections[name] = self.scene.collection.children[name] = target
        ref = ManagedObject({owner: "REF_FRONT"})
        ref.users_collection = (target,)
        self.data.objects["REF_FRONT"] = ref
        return ref

    def test_rerun_resolves_owned_reference_for_replacement(self):
        ref = self.owned_reference()
        _, previous = self.setup["check_targets"](self.scene)
        self.assertIs(previous["REF_FRONT"], ref)
        self.assertEqual(len(self.data.objects), 1)

    def test_build_twice_replaces_managed_objects_and_preserves_body_content(self):
        self.scene.name = "Existing project"
        self.scene.collection.children = Links()
        self.data.collections = Pool(new_collection)
        self.data.objects = Pool(new_object)
        self.data.cameras = Pool(new_camera_data)
        views = {
            name: SimpleNamespace(path=Path(f"/blender/{name}.png"),
                                  width_px=100, height_px=200,
                                  world_width_m=1, world_height_m=2)
            for name in self.setup["VIEWS"]
        }
        config = {"images": {name: {} for name in views}, "character_height_m": 2}
        self.data.images.load.side_effect = lambda *a, **kw: MagicMock(
            size=(100, 200), has_data=True, packed_file=object()
        )
        build = self.setup["build"]
        build.__globals__["bpy"].app = SimpleNamespace(version_string="test")
        # Transform math is covered separately. This checks the refresh lifecycle.
        with patch.dict(build.__globals__, {"add_reference": Mock(), "add_camera": Mock()}):
            first = build(config, views)
            body = self.data.collections.get("10_BODY_WORKSPACE")
            body_object = self.data.objects.new("UserBody", None)
            body.objects.link(body_object)
            old_ref = self.data.objects.get("REF_FRONT")
            second = build(config, views)
        self.assertEqual(first, second)
        self.assertEqual(len(self.data.collections), 4)
        self.assertEqual(len(self.data.objects), 9)
        self.assertIsNot(self.data.objects.get("REF_FRONT"), old_ref)
        self.assertIs(body.objects.get("UserBody"), body_object)

    def test_unrelated_reserved_name_is_rejected_before_loading(self):
        ref = self.owned_reference()
        ref.clear()
        with self.assertRaisesRegex(ReferenceError, "unrelated or in use"):
            self.setup["build"]({}, {})
        self.data.images.load.assert_not_called()
        self.assertIs(self.data.objects["REF_FRONT"], ref)

    def test_shared_collection_is_rejected(self):
        ref = self.owned_reference()
        ref.users_collection[0].users = 2
        with self.assertRaisesRegex(ReferenceError, "unrelated or shared"):
            self.setup["check_targets"](self.scene)

    def test_blender_decode_failure_preserves_prior_references(self):
        ref = self.owned_reference()
        image = MagicMock(size=(100, 200), has_data=True, packed_file=object())
        self.data.images.load.side_effect = [image, RuntimeError("cannot decode")]
        view = SimpleNamespace(path=Path("/blender/front.png"), width_px=100, height_px=200)
        with self.assertRaisesRegex(ReferenceError, "cannot decode/pack back PNG"):
            self.setup["build"]({}, {"front": view, "back": view})
        self.data.images.remove.assert_called_once_with(image, do_unlink=True)
        self.assertIs(self.data.objects["REF_FRONT"], ref)

    def test_existing_output_and_source_are_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.blend"
            source.write_bytes(b"existing")
            check_output = self.setup["check_output"]
            with self.assertRaisesRegex(ReferenceError, "open Blender file"):
                check_output(source, str(source), True)
            with self.assertRaisesRegex(ReferenceError, "Existing output"):
                check_output(source, "", False)
            self.assertEqual(source.read_bytes(), b"existing")

    def test_existing_manifest_is_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "copy.blend"
            output.with_suffix(".manifest.json").write_text("{}")
            with self.assertRaisesRegex(ReferenceError, "Existing output"):
                self.setup["check_output"](output, "", False)
