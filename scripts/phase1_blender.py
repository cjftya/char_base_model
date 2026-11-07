"""Phase 1 operations invoked through the existing Blender MCP Python tool.

No MCP server/client is started here. Call one operation at a time, inspect its
artifacts, then obtain the read-only Reviewer result before advancing a gate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
import bmesh
from mathutils import Vector
from phase1_render import reference_overlay
from phase1_evidence import review_context, validate_evidence
from phase1_workflow import BUILD_START, BLOCKOUT, REVIEW_NEXT

from phase1_contract import (load, write_new, ensure_json, replace_json, digest, verify_sources,
                             validate_contract, transition, STATES)
from phase1_geometry import Mesh, body_mesh, head_mesh, mesh_stats
from reference_common import ReferenceError, VIEWS

OWNER = "char_base_model_phase1"
WORKSPACES = {"body": "10_BODY_WORKSPACE", "head": "20_HEAD_WORKSPACE"}


def snapshot_phase0():
    result = {}
    for view in VIEWS:
        for prefix in ("REF", "CAM"):
            name = f"{prefix}_{view.upper()}"
            obj = bpy.data.objects.get(name)
            if obj is None or obj.get("char_base_model_phase0") != name:
                raise ReferenceError(f"Missing/foreign Phase 0 object: {name}")
            if (not obj.hide_select or not all(obj.lock_location) or not all(obj.lock_rotation)
                    or not all(obj.lock_scale)):
                raise ReferenceError(f"Phase 0 lock was changed: {name}")
            data = {"matrix": [list(row) for row in obj.matrix_world],
                    "collections": sorted(c.name for c in obj.users_collection),
                    "hide_render": obj.hide_render, "type": obj.type}
            if prefix == "REF":
                if obj.type != "EMPTY" or not obj.data or not obj.data.packed_file:
                    raise ReferenceError(f"Phase 0 reference is not packed: {name}")
                data.update(image=obj.data.name, size=list(obj.data.size),
                            display_size=obj.empty_display_size, offset=list(obj.empty_image_offset),
                            packed_sha256=hashlib.sha256(bytes(obj.data.packed_file.data)).hexdigest())
            else:
                if obj.type != "CAMERA" or obj.data.type != "ORTHO":
                    raise ReferenceError(f"Phase 0 camera is not orthographic: {name}")
                data.update(scale=obj.data.ortho_scale, shift=[obj.data.shift_x, obj.data.shift_y],
                            clip=[obj.data.clip_start, obj.data.clip_end])
            result[name] = data
    scene = bpy.context.scene
    result["render"] = [scene.render.resolution_x, scene.render.resolution_y,
                        scene.render.resolution_percentage, scene.render.pixel_aspect_x,
                        scene.render.pixel_aspect_y]
    return result


def context(session):
    session = Path(session).resolve()
    verify_sources(session)
    if Path(bpy.data.filepath).resolve() != session / "phase1_working.blend":
        raise ReferenceError("Open the Phase 1 working copy through MCP before modeling")
    state = load(session / "state.json")
    if state["status"] != "ACTIVE":
        raise ReferenceError(f"Session halted: {state['status']}")
    current = snapshot_phase0()
    for view in VIEWS:
        if current["REF_" + view.upper()]["packed_sha256"] != state["sources"][view]:
            raise ReferenceError("Packed Phase 0 image differs from the landmark source: " + view)
    for obj in owned_objects():
        region = obj.get(OWNER)
        workspace = bpy.data.collections.get(WORKSPACES.get(region, ""))
        if (region not in WORKSPACES or workspace is None
                or tuple(obj.users_collection) != (workspace,) or obj.library
                or obj.data is None or obj.data.library or obj.data.users != 1):
            raise ReferenceError("Builder mesh is foreign, shared or outside its workspace")
        if (obj.type != "MESH" or obj.modifiers or obj.constraints or obj.animation_data
                or obj.data.shape_keys or obj.hide_render or obj.hide_viewport or obj.hide_get()):
            raise ReferenceError("Unsupported deformation, animation or hidden Builder object")
        if any(c.hide_render or c.hide_viewport for c in obj.users_collection):
            raise ReferenceError("Builder workspace is hidden")
    saved = session / "phase0_source/scene_snapshot.json"
    if saved.exists() and load(saved) != current:
        raise ReferenceError("Phase 0 references/cameras changed; stop and report")
    if not saved.exists():
        raise ReferenceError("Initialize the working copy from the clean Phase 0 source first")
    if state.get("contract_sha256"):
        for filename, key in (("model_contract.json", "contract_sha256"), ("landmarks.json", "landmarks_sha256")):
            if digest(session / filename) != state[key]:
                raise ReferenceError("Contract changed; replan instead of silently changing approved regions")
    return session, state


def save_copy(path):
    """Blender copy save with no-clobber publication and no active-file change."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ReferenceError(f"Preserved existing output: {path}")
    with TemporaryDirectory(dir=path.parent, prefix=".phase1-save-") as temp:
        # A sibling staging file keeps // relative dependencies valid after publication.
        staged = Path(temp).with_suffix(".blend")
        try:
            status = bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True, relative_remap=True)
            if "FINISHED" not in status:
                raise ReferenceError(f"Blender save failed: {status}")
            # Same filesystem; publish atomically without replacing another file.
            import os
            os.link(staged, path)
        finally:
            staged.unlink(missing_ok=True)


def initialize_working(session):
    """Re-save from the open, clean Phase 0 source to remap relative assets."""
    session = Path(session).resolve()
    verify_sources(session)
    records = load(session / "phase0_source/inputs.json")
    if Path(bpy.data.filepath).resolve() != Path(records["blend"]["path"]):
        raise ReferenceError("Open the reviewed Phase 0 source before initializing its copy")
    if bpy.data.is_dirty:
        raise ReferenceError("Phase 0 has unsaved changes; preserve them before initializing")
    baseline = snapshot_phase0()
    state = load(session / "state.json")
    if state["state"] != "REFERENCES_READY" or (session / "phase0_source/scene_snapshot.json").exists():
        raise ReferenceError("Working copy already initialized")
    manifest = load(records["manifest"]["path"])
    for v in VIEWS:
        ref = manifest["references"][v]
        obj = bpy.data.objects["REF_" + v.upper()]
        if (baseline[obj.name]["packed_sha256"] != state["sources"][v]
                or ref["object"] != obj.name or list(obj.data.size) != ref["size_px"]
                or any(abs(float(a)-float(b)) > 1e-5 for a,b in zip(obj.location, ref["location"]))):
            raise ReferenceError("Reviewed Phase 0 scene/source image does not match manifest")
    save_working(session)
    write_new(session / "phase0_source/scene_snapshot.json", baseline)
    bpy.ops.wm.open_mainfile(filepath=str(session / "phase1_working.blend"))
    context(session)
    return {"status": "REFERENCES_READY", "working_file": bpy.data.filepath}


def accept_landmarks(session, contract_path, landmarks_path):
    session, state = context(session)
    if state["state"] != "REFERENCES_READY":
        raise ReferenceError("Landmarks can only be accepted after REFERENCES_READY")
    contract, landmarks = load(contract_path), load(landmarks_path)
    validate_contract(contract, landmarks, state["sources"])
    manifest = load(load(session / "phase0_source/inputs.json")["manifest"]["path"])
    if abs(contract["height_m"] - manifest["character_height_m"]) > 1e-6:
        raise ReferenceError("Contract height differs from Phase 0")
    ensure_json(session / "landmarks.json", landmarks)
    ensure_json(session / "model_contract.json", contract)
    state = transition(state, "LANDMARKS_READY")
    state["contract_sha256"] = digest(session / "model_contract.json")
    state["landmarks_sha256"] = digest(session / "landmarks.json")
    replace_json(session / "state.json", state)
    return state


def owned_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get(OWNER)]


def build_region(session, region):
    session, state = context(session)
    allowed = BUILD_START
    blockout = BLOCKOUT
    if region not in allowed or state["state"] not in (allowed[region], blockout[region]):
        raise ReferenceError("Builder cannot run before its preceding gate")
    if state["state"] == blockout[region] and (not state["history"] or state["history"][-1]["verdict"] != "REWORK"):
        raise ReferenceError("Rebuild needs an explicit REWORK finding")
    contract = load(session / "model_contract.json")
    geometry = (body_mesh if region == "body" else head_mesh)(contract[region])
    collection = bpy.data.collections.get(WORKSPACES[region])
    if collection is None or collection.library or collection.get("char_base_model_phase0") != collection.name:
        raise ReferenceError("Missing or foreign Builder workspace")
    name = "P1_" + region.upper()
    old = bpy.data.objects.get(name)
    if old and (old.get(OWNER) != region or tuple(old.users_collection) != (collection,) or old.library or old.children):
        raise ReferenceError("Reserved Builder name belongs to user/shared object")
    if old:
        # A rebuild with identical immutable contract cannot fix the finding.
        raise ReferenceError("Use edit_region for local REWORK; do not regenerate approved geometry")
    data = bpy.data.meshes.new(name)
    obj = None
    try:
        data.from_pydata(geometry.vertices, [], geometry.faces)
        if data.validate():
            raise ReferenceError("Blender corrected invalid generated geometry; reject the contract")
        bm = bmesh.new()
        try:
            bm.from_mesh(data)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(data)
        finally:
            bm.free()
        data.update()
        obj = bpy.data.objects.new(name, data)
        obj[OWNER] = region
        obj["semantic_regions"] = json.dumps(geometry.regions)
        collection.objects.link(obj)
        if snapshot_phase0() != load(session / "phase0_source/scene_snapshot.json"):
            raise ReferenceError("Builder altered protected Phase 0 data")
        # Save before state advancement. A failed save leaves state unchanged.
        save_copy(session / "attempts" / (name.lower() + "_blockout.blend"))
        save_working(session)
        state = transition(state, blockout[region])
        replace_json(session / "state.json", state)
    except Exception:
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)
        raise
    return validate_scene()


def edit_region(session, region, edits):
    """Apply explicit vertex deltas only within the requested finding's region.

    edits = {vertex_index: [x,y,z]}. A passed region cannot be regenerated.
    This is the local rework path used by the Builder after visual inspection.
    """
    session, state = context(session)
    if region not in WORKSPACES:
        raise ReferenceError("Unknown Builder region")
    expected = BLOCKOUT
    if (state["state"] not in (expected.get(region), "TOPOLOGY_REFINEMENT", "INTEGRATION_REVIEW")
            or not state["history"] or state["history"][-1]["verdict"] != "REWORK"):
        raise ReferenceError("Local edits require the affected Builder's REWORK gate")
    obj = bpy.data.objects.get("P1_" + region.upper())
    if not obj or obj.get(OWNER) != region:
        raise ReferenceError("Missing owned Builder mesh")
    from phase1_geometry import point
    spec = load(session / "model_contract.json")[region]
    updates = {int(i): point(p) for i, p in edits.items()}
    if not updates or any(not 0 <= i < len(obj.data.vertices) for i in updates):
        raise ReferenceError("Invalid vertex edits")
    if any(not spec["bounds"][j][0] <= p[j] <= spec["bounds"][j][1] for p in updates.values() for j in range(3)):
        raise ReferenceError("Edits exceed workspace bounds")
    labels = json.loads(obj["semantic_regions"])
    findings = state["history"][-1]["review"]["findings"]
    preserve = {r for f in findings for r in f["preserve_regions"]}
    affected = {f["region"] for f in findings}
    if len(labels) != len(obj.data.polygons):
        raise ReferenceError("Semantic labels no longer match topology; replan")
    vertex_regions = {i: set() for i in updates}
    for polygon in obj.data.polygons:
        for index in polygon.vertices:
            if index in vertex_regions:
                vertex_regions[index].add(labels[polygon.index])
    if any(any(r.split(":")[0] in preserve or r in preserve for r in rs) or not any(
           r in affected or r.split(":")[0] in affected for r in rs) for rs in vertex_regions.values()):
        raise ReferenceError("Edit touches a preserved region or lies outside reported findings")
    before = {i: obj.data.vertices[i].co.copy() for i in updates}
    try:
        for i, p in updates.items():
            obj.data.vertices[i].co = obj.matrix_world.inverted() @ Vector(p)
        obj.data.update()
        stats = validate_scene()[obj.name]
        if stats["invalid_faces"] or stats["boundary_edges"] or stats["nonmanifold_edges"]:
            raise ReferenceError("Local edit damages mesh validity")
        n = len(list((session / "attempts").glob("edit_*.json")))
        save_copy(session / "attempts" / f"edit_{n:03d}.blend")
        write_new(session / "attempts" / f"edit_{n:03d}.json", {"region": region, "edits": edits})
        save_working(session)
    except Exception:
        for i, p in before.items():
            obj.data.vertices[i].co = p
        obj.data.update()
        raise
    return stats


def validate_scene():
    """Read-only geometry collection; no edit operators or repairs."""
    report = {}
    for obj in owned_objects():
        if obj.type != "MESH":
            continue
        mesh = Mesh([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices],
                    [tuple(p.vertices) for p in obj.data.polygons])
        stats = mesh_stats(mesh)
        stats["geometry_sha256"] = hashlib.sha256(json.dumps(
            {"vertices": mesh.vertices, "faces": mesh.faces}, sort_keys=True).encode()).hexdigest()
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            stats["nonmanifold_vertices"] = sum(not v.is_manifold for v in bm.verts)
            stats["signed_volume"] = bm.calc_volume(signed=True)
        finally:
            bm.free()
        stats.update(hide_render=obj.hide_render, hide_viewport=obj.hide_viewport,
                     scale=list(obj.scale), location=list(obj.location),
                     materials=len(obj.data.materials), modifiers=[m.type for m in obj.modifiers])
        report[obj.name] = stats
    return report


def refine_topology(session):
    session, state = context(session)
    if state["state"] != "HEAD_SHAPE_REVIEW":
        raise ReferenceError("Both shape gates must pass before topology refinement")
    for obj in owned_objects():
        if obj.type == "MESH":
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
                bm.to_mesh(obj.data)
            finally:
                bm.free()
            obj.data.update()
    # No automatic decimation/remeshing: measured ring and feature loops are retained.
    save_copy(session / "attempts/topology_refined.blend")
    save_working(session)
    state = transition(state, "TOPOLOGY_REFINEMENT")
    replace_json(session / "state.json", state)
    return validate_scene()


def save_working(session):
    """Replace only this session's working file; immutable sources are guarded."""
    session = Path(session)
    working = session / "phase1_working.blend"
    if working.is_symlink():
        raise ReferenceError("Working file symlink is forbidden")
    from uuid import uuid4
    staged = session / (".working-" + uuid4().hex + ".blend")
    try:
        save_copy(staged)
        staged.replace(working)
    finally:
        staged.unlink(missing_ok=True)


def collect_evidence(session):
    """Render isolated copies; never alter Phase 0 cameras, lights or materials."""
    session, state = context(session)
    if state["state"] not in ("BODY_BLOCKOUT", "HEAD_BLOCKOUT", "TOPOLOGY_REFINEMENT", "INTEGRATION_REVIEW"):
        raise ReferenceError("Evidence requested outside a reviewable stage")
    attempt = max((int(p.name[8:]) for p in (session / "review").glob("attempt_*")
                   if p.name[8:].isdigit()), default=-1) + 1
    folder = session / "review" / f"attempt_{attempt:03d}"
    folder.mkdir()
    save_working(session)
    save_copy(folder / "candidate.blend")
    write_new(folder / "review_context.json", review_context(state))
    write_new(folder / "metrics.json", {"meshes": validate_scene(), "silhouette": "UNVERIFIED",
              "reason": "No human-verified background masks supplied; inspect calibrated overlays"})
    manifest_path = load(session / "phase0_source/inputs.json")["manifest"]["path"]
    source_scene = bpy.context.scene
    scene = bpy.data.scenes.new("P1_review_temp")
    camera_objects = []
    try:
        scene["p1_manifest_path"] = manifest_path
        for name in ("resolution_x", "resolution_y", "resolution_percentage", "pixel_aspect_x", "pixel_aspect_y"):
            setattr(scene.render, name, getattr(source_scene.render, name))
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'SINGLE'
        scene.display.shading.single_color = (.6, .6, .6)
        for obj in owned_objects():
            scene.collection.objects.link(obj)
        alignment = {}
        for view in (*VIEWS, "oblique_front", "oblique_back"):
            if view in VIEWS:
                camera = bpy.data.objects["CAM_" + view.upper()].copy()
                camera.data = camera.data.copy()
            else:
                data = bpy.data.cameras.new("P1_oblique_data")
                camera = bpy.data.objects.new("P1_oblique", data)
                height = load(session / "model_contract.json")["height_m"]
                sign = -1 if view == "oblique_front" else 1
                camera.location = (height*2, sign*height*3, height*1.7)
                camera.rotation_euler = (Vector((0, 0, height*.5))-camera.location).to_track_quat('-Z','Y').to_euler()
                data.type = 'ORTHO'
                data.ortho_scale = height*1.5*max(1, scene.render.resolution_x/scene.render.resolution_y)
            camera_objects.append(camera)
            scene.collection.objects.link(camera)
            scene.camera = camera
            scene.render.filepath = str(folder / (view + ".png"))
            bpy.ops.render.render(write_still=True, scene=scene.name)
            if view in VIEWS:
                rendered = bpy.data.images.load(scene.render.filepath, check_existing=False)
                try:
                    alignment[view] = reference_overlay(scene, camera, view, rendered, folder / ("overlay_" + view + ".png"))
                finally:
                    bpy.data.images.remove(rendered)
        write_new(folder / "alignment.json", alignment)
    except Exception as exc:
        write_new(folder / "render_failure.json", {"status": "BLOCKED", "reason": str(exc)})
        raise
    finally:
        bpy.data.scenes.remove(scene)
        for camera in camera_objects:
            data = camera.data
            bpy.data.objects.remove(camera, do_unlink=True)
            if data.users == 0:
                bpy.data.cameras.remove(data)
    if snapshot_phase0() != load(session / "phase0_source/scene_snapshot.json"):
        raise ReferenceError("Protected Phase 0 scene changed during evidence collection")
    binding = {p.name: digest(p) for p in folder.iterdir() if p.is_file()}
    binding["contract_sha256"] = state["contract_sha256"]
    binding["landmarks_sha256"] = state["landmarks_sha256"]
    write_new(folder / "evidence.json", binding)
    return {"folder": str(folder), "evidence": binding, "state": state["state"]}


def submit_review(session, evidence_folder, review_path):
    session, state = context(session)
    folder = Path(evidence_folder).resolve()
    if folder.parent != session / "review":
        raise ReferenceError("Review evidence must belong to this session")
    binding = validate_evidence(folder, state)
    # Hash the saved current geometry too; a Reviewer cannot approve stale renders.
    metrics = load(folder / "metrics.json")["meshes"]
    if metrics != validate_scene():
        raise ReferenceError("Geometry changed after evidence collection")
    target = REVIEW_NEXT.get(state["state"])
    if target is None:
        raise ReferenceError("No pending review gate")
    review = load(review_path)
    if review.get("verdict") == "PASS":
        names = {"P1_BODY"} if state["state"] == "BODY_BLOCKOUT" else {"P1_BODY", "P1_HEAD"}
        if set(metrics) != names:
            raise ReferenceError("Required actual meshes are missing")
        for stats in metrics.values():
            if (stats["boundary_edges"] or stats["nonmanifold_edges"] or stats["invalid_faces"]
                    or stats["isolated_vertices"] or stats["duplicate_vertices"]
                    or stats["inconsistent_winding_edges"] or stats["nonmanifold_vertices"]
                    or stats["components"] != 1 or stats["signed_volume"] <= 0):
                raise ReferenceError("Mesh health blocks PASS")
    candidate = transition(state, target, review=review, evidence=binding)
    ensure_json(folder / "findings.json", review)
    if candidate["state"] == "PHASE1_COMPLETE":
        save_copy(session / "phase1_final.blend")
    replace_json(session / "state.json", candidate)
    return candidate


def report(session):
    session = Path(session).resolve()
    state = load(session / "state.json")
    text = ["# Phase 1 report", "", f"State: {state['state']}", f"Status: {state['status']}", "",
            "Actual Blender mesh statistics:", "```json", json.dumps(validate_scene(), indent=2), "```", "",
            "Head and body remain separate closed surfaces. Inspect neck contact in all six views;",
            "separate meshes are not a claim of rig-ready topology.", "", "Gate history:"]
    for item in state["history"]:
        text.append(f"- {item['gate']}: {item['verdict']}")
        for finding in item["review"]["findings"]:
            text.append(f"  - {finding['region']}: {finding['observed']} -> {finding['suggested_action']}")
    text += ["", "Silhouette measurements without verified masks: UNVERIFIED.",
             "Next priorities: resolve reported regions; inspect facial volume; inspect neck/limb junctions."]
    path = session / ("phase1_report_" + str(len(state["history"])) + ".md")
    with path.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(text) + '\n')
    return str(path)
