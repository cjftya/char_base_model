"""Prepare Phase 0 inside Blender, either via MCP or in background mode."""

from __future__ import annotations

import argparse
import json
import os
import sys
from math import radians
from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
from mathutils import Euler, Vector

from reference_common import ReferenceError, VIEWS, load_references

ROOT = Path(__file__).resolve().parent.parent
OWNER = "char_base_model_phase0"
UNVERIFIED = "UNVERIFIED"
COLLECTIONS = ("00_REFERENCES_LOCKED", "10_BODY_WORKSPACE",
               "20_HEAD_WORKSPACE", "90_REVIEW_CAMERAS")
# Local image X points camera-right, Y points up and Z points toward the camera.
VIEW_ROTATIONS = {
    "front": (90, 0, 0),
    "back": (90, 0, 180),
    "left": (90, 0, -90),
    "right": (90, 0, 90),
}
VIEW_DIRECTIONS = {
    "front": (0, -1, 0),
    "back": (0, 1, 0),
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
}


def add_reference(obj, name, view, config, image):
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = max(view.world_width_m, view.world_height_m)
    obj.empty_image_offset = (-0.5, -0.5)
    obj.empty_image_depth = "BACK"
    obj.empty_image_side = "FRONT"
    obj.show_empty_image_orthographic = True
    obj.show_empty_image_perspective = False
    obj.show_empty_image_only_axis_aligned = True
    obj.use_empty_image_alpha = True
    obj.color = (1, 1, 1, float(config["opacity"]))
    obj.hide_render = True
    obj.rotation_euler = Euler(tuple(radians(v) for v in VIEW_ROTATIONS[name]), "XYZ")
    outward = Vector(VIEW_DIRECTIONS[name])
    image_offset = Vector((view.offset_x_m, view.offset_z_m, 0))
    obj.location = outward * float(config["plane_offset_m"]) + obj.rotation_euler.to_matrix() @ image_offset
    obj["reference_view"] = name


def add_camera(camera, name, config, view, scene):
    height = float(config["character_height_m"])
    aspect = (scene.render.resolution_x * scene.render.pixel_aspect_x
              / (scene.render.resolution_y * scene.render.pixel_aspect_y))
    half_width = view.world_width_m / 2 + abs(view.offset_x_m)
    half_height = view.world_height_m / 2 + abs(view.offset_z_m - height / 2)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.1 * max(
        half_width * max(1, 1 / aspect), half_height * max(1, aspect)
    )
    distance = max(float(config["plane_offset_m"]) + 4, height * 4)
    camera.data.clip_end = distance * 2
    camera.location = Vector(VIEW_DIRECTIONS[name]) * distance
    camera.location.z = height / 2
    camera.rotation_euler = Euler(tuple(radians(v) for v in VIEW_ROTATIONS[name]), "XYZ")


def check_targets(scene):
    """Refuse name collisions and shared IDs before creating or deleting anything."""
    collections = {}
    objects = {}
    for name in COLLECTIONS:
        collection = bpy.data.collections.get(name)
        if collection is not None and (
            collection.get(OWNER) != name or collection.library
            or collection.users != 1 or scene.collection.children.get(name) != collection
        ):
            raise ReferenceError(f"Collection is unrelated or shared: {name}")
        collections[name] = collection
    for prefix, collection_name in (("REF", COLLECTIONS[0]), ("CAM", COLLECTIONS[3])):
        for view in VIEWS:
            name = f"{prefix}_{view.upper()}"
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            target = collections[collection_name]
            # The scene's active review camera may be carried over on refresh.
            expected_users = 2 if scene.camera == obj and prefix == "CAM" else 1
            if (obj.get(OWNER) != name or obj.library or obj.users != expected_users
                    or target is None or tuple(obj.users_collection) != (target,)
                    or obj.children):
                raise ReferenceError(f"Object is unrelated or in use elsewhere: {name}")
            objects[name] = obj
    return collections, objects


def build(config, views):
    """Stage a replacement set before touching any existing Phase 0 objects."""
    scene = bpy.context.scene
    collections, previous = check_targets(scene)
    created = []
    staged = {}

    def track(pool, item):
        created.append((pool, item))
        return item

    try:
        images = {}
        for name, view in views.items():
            try:
                image = track(bpy.data.images, bpy.data.images.load(str(view.path), check_existing=False))
                if tuple(image.size) != (view.width_px, view.height_px) or not image.has_data:
                    raise ReferenceError("decoded dimensions differ or pixel data is unavailable")
                image.pack()
                if image.packed_file is None:
                    raise ReferenceError("image could not be packed")
            except (OSError, RuntimeError, ReferenceError) as exc:
                raise ReferenceError(f"Blender cannot decode/pack {name} image {view.path}: {exc}") from exc
            image[OWNER] = name
            images[name] = image

        for name, collection in collections.items():
            if collection is None:
                collection = track(bpy.data.collections, bpy.data.collections.new(name))
                collection[OWNER] = name
                scene.collection.children.link(collection)
                collections[name] = collection

        for name in VIEWS:
            ref_name, cam_name = f"REF_{name.upper()}", f"CAM_{name.upper()}"
            obj = track(bpy.data.objects, bpy.data.objects.new(ref_name, None))
            add_reference(obj, name, views[name], config, images[name])
            camera_data = track(bpy.data.cameras, bpy.data.cameras.new(cam_name))
            camera_data[OWNER] = name
            camera = track(bpy.data.objects, bpy.data.objects.new(cam_name, camera_data))
            add_camera(camera, name, config, views[name], scene)
            for key, item, target in ((ref_name, obj, COLLECTIONS[0]),
                                      (cam_name, camera, COLLECTIONS[3])):
                item[OWNER] = key
                item.hide_select = True
                item.lock_location = item.lock_rotation = item.lock_scale = (True,) * 3
                collections[target].objects.link(item)
                staged[key] = item
    except Exception:
        for pool, item in reversed(created):
            pool.remove(item, do_unlink=True)
        raise

    for name, obj in previous.items():
        data = obj.data
        pool = bpy.data.cameras if obj.type == "CAMERA" else bpy.data.images
        if scene.camera == obj:
            scene.camera = staged[name]
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.get(OWNER) and data.users == 0:
            pool.remove(data)

    for name, item in staged.items():
        item.name = name
    collections[COLLECTIONS[0]].hide_select = True
    # Review cameras may be assigned to a viewport or scene after setup.
    return {
        "status": UNVERIFIED,
        "scene": scene.name,
        "blender_version": bpy.app.version_string,
        "character_height_m": config["character_height_m"],
        "collections": list(COLLECTIONS),
        "references": {
            name: {
                "input": config["images"][name],
                "size_px": [view.width_px, view.height_px],
                "world_size_m": [view.world_width_m, view.world_height_m],
                "object": f"REF_{name.upper()}",
                "location": list(staged[f"REF_{name.upper()}"].location),
                "rotation_deg": VIEW_ROTATIONS[name],
                "packed": True,
            } for name, view in views.items()
        },
        "cameras": {name: f"CAM_{name.upper()}" for name in VIEWS},
        "visual_review": {name: UNVERIFIED for name in VIEWS},
        "reopen_review": UNVERIFIED,
    }


def check_output(output, source, overwrite):
    manifest = output.with_suffix(".manifest.json")
    if output.suffix.lower() != ".blend":
        raise ReferenceError("Output must have a .blend extension")
    if source and output == Path(source).resolve():
        raise ReferenceError("Output must differ from the open Blender file")
    for path in (output, manifest):
        if path.is_symlink() or (path.exists() and (not overwrite or not path.is_file())):
            raise ReferenceError(f"Existing output was preserved: {path}")
    return manifest


def prepare_phase0(config_path, output_path, *, overwrite=False):
    """Run on the Blender host. Save a copy of the current project and a manifest."""
    output = Path(output_path).expanduser().absolute()
    if not Path(config_path).is_absolute() or not Path(output_path).is_absolute():
        raise ReferenceError("Use absolute Blender-host config and output paths")
    if output.is_symlink():
        raise ReferenceError(f"Output symlink was preserved: {output}")
    output = output.resolve()
    manifest_path = check_output(output, bpy.data.filepath, overwrite)
    config, views = load_references(Path(config_path))
    if config.get("anchors_reviewed") is False:
        raise ReferenceError("Inspect all four images and calibrate their anchors before setup")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".phase0-") as temp:
        temp_blend = Path(temp).with_suffix(".blend")
        temp_manifest = Path(temp) / manifest_path.name
        manifest = build(config, views)
        manifest["blend_file"] = output.name
        manifest["input_guidance"] = config.get("input_guidance", [])
        temp_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        try:
            # The staging file is a sibling of the final output so Blender remaps
            # the original scene's relative dependencies to the right directory.
            result = bpy.ops.wm.save_as_mainfile(
                filepath=str(temp_blend), copy=True, relative_remap=True
            )
            if "FINISHED" not in result:
                raise ReferenceError(f"Blender did not save the copy: {result}")
            if overwrite:
                os.replace(temp_blend, output)
                os.replace(temp_manifest, manifest_path)
            else:
                os.link(temp_manifest, manifest_path)
                try:
                    os.link(temp_blend, output)
                except OSError:
                    manifest_path.unlink()
                    raise
        finally:
            temp_blend.unlink(missing_ok=True)
    return manifest


def main() -> int:
    if not bpy.app.background:
        print("ERROR: Use prepare_phase0 via MCP or run Blender in background mode.")
        return 2
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/reference_setup.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output/reference_stage.blend")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = args.output.absolute()
        check_output(output, bpy.data.filepath, args.overwrite)
        if not bpy.data.filepath:
            # An isolated background process starts with Blender's default cube.
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.context.scene.unit_settings.system = "METRIC"
        manifest = prepare_phase0(args.config.absolute(), output, overwrite=args.overwrite)
    except (ReferenceError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    # Let Blender's --python-exit-code report script failure to the shell.
    if main():
        raise RuntimeError("Phase 0 setup failed; see ERROR above.")
