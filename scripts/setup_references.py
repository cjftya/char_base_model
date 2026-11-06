"""Create a clean Blender .blend scene with four calibrated orthographic references.

Run with Blender in background mode. This script never modifies an existing blend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

from reference_common import ReferenceError, VIEWS, load_references

ROOT = Path(__file__).resolve().parent.parent
# Coordinates: front camera=-Y, back=+Y, left=-X, right=+X.
# Local image X points camera-right; local Y points up (+Z).
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


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def add_reference(name, view, config, target_collection):
    from math import radians

    image = bpy.data.images.load(str(view.path), check_existing=False)
    image.pack()
    obj = bpy.data.objects.new(f"REF_{name.upper()}", None)
    target_collection.objects.link(obj)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = view.world_width_m
    obj.empty_image_offset = (-0.5, -0.5)
    obj.empty_image_depth = "BACK"
    obj.empty_image_side = "FRONT"
    obj.show_empty_image_orthographic = True
    obj.show_empty_image_perspective = False
    obj.color = (1, 1, 1, float(config["opacity"]))
    obj.hide_select = True
    obj.hide_render = True
    obj.rotation_euler = Euler(tuple(radians(v) for v in VIEW_ROTATIONS[name]), "XYZ")
    outward = Vector(VIEW_DIRECTIONS[name])
    image_offset = Vector((view.offset_x_m, view.offset_z_m, 0))
    obj.location = outward * float(config["plane_offset_m"]) + obj.rotation_euler.to_matrix() @ image_offset
    obj["reference_view"] = name
    return obj


def add_camera(name, config, target_collection):
    height = float(config["character_height_m"])
    camera_data = bpy.data.cameras.new(f"CAM_{name.upper()}")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.30
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    target_collection.objects.link(camera)
    camera.location = Vector(VIEW_DIRECTIONS[name]) * max(float(config["plane_offset_m"]) + 4, height * 4)
    camera.location.z = height / 2
    camera.rotation_euler = (Vector((0, 0, height / 2)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.hide_select = True
    return camera


def build(config, views):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.render.resolution_percentage = 100
    references = collection("00_REFERENCES_LOCKED")
    collection("10_BODY_WORKSPACE")
    collection("20_HEAD_WORKSPACE")
    cameras = collection("90_REVIEW_CAMERAS")
    output = {"references": {}, "cameras": {}}
    for name in VIEWS:
        obj = add_reference(name, views[name], config, references)
        camera = add_camera(name, config, cameras)
        output["references"][name] = {
            "input": config["images"][name],
            "size_px": [views[name].width_px, views[name].height_px],
            "world_size_m": [views[name].world_width_m, views[name].world_height_m],
            "object": obj.name,
            "location": list(obj.location),
            "rotation_deg": VIEW_ROTATIONS[name],
        }
        output["cameras"][name] = camera.name
    bpy.context.scene.camera = bpy.data.objects["CAM_FRONT"]
    bpy.context.scene["model_status"] = "REFERENCES_READY_NO_MESH"
    bpy.context.scene["character_height_m"] = float(config["character_height_m"])
    return output


def main() -> int:
    if not bpy.app.background:
        print("ERROR: Run this setup with blender --background to protect open projects.")
        return 2
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/reference_setup.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output/reference_stage.blend")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.suffix.lower() != ".blend":
        print("ERROR: Output must have a .blend extension")
        return 2
    if output.exists() and not args.overwrite:
        print(f"ERROR: Existing file not modified: {output} (use --overwrite if intended)")
        return 2
    try:
        config, views = load_references(args.config)
    except ReferenceError as exc:
        print(f"ERROR: {exc}")
        return 2
    manifest = build(config, views)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    manifest["character_height_m"] = config["character_height_m"]
    manifest["blend_file"] = output.name
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"READY: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
