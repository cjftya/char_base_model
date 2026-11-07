"""Phase 1 contracts, immutable input fingerprints and evidence-bound gates."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from prepare_session import downloads_directory
from reference_common import ReferenceError, VIEWS
from phase1_geometry import body_mesh, head_mesh, mesh_stats, point

STATES = ("REFERENCES_READY", "LANDMARKS_READY", "BODY_BLOCKOUT", "BODY_SHAPE_REVIEW",
          "HEAD_BLOCKOUT", "HEAD_SHAPE_REVIEW", "TOPOLOGY_REFINEMENT",
          "INTEGRATION_REVIEW", "PHASE1_COMPLETE")
VISUAL_CHECKS = ("proportions", "silhouette", "volume", "connections", "mesh_validity")
LANDMARKS = ("crown", "chin", "neck", "shoulder", "chest", "waist", "pelvis", "buttock",
             "elbow", "wrist", "knee", "ankle", "toe")


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReferenceError(f"Cannot read JSON {path}: {exc}") from exc


def write_new(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def replace_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(".pending.json")
    write_new(temporary, data)
    temporary.replace(path)


def require_passes(review, checks):
    if any(review.get(key) != "PASS" for key in checks):
        raise ReferenceError("Required review checks are not PASS: " + ", ".join(checks))


def validate_contract(contract, landmarks, sources):
    if contract.get("schema_version") != 1 or landmarks.get("schema_version") != 1:
        raise ReferenceError("Unsupported contract/landmark schema")
    height = contract.get("height_m")
    if type(height) not in (int, float) or not 0 < height < 1e6:
        raise ReferenceError("height_m must be finite and positive")
    if contract.get("axes") != {"up": "+Z", "front": "-Y", "sole_z": 0}:
        raise ReferenceError("Use the unmodified Phase 0 coordinate system")
    if landmarks.get("source_hashes") != sources:
        raise ReferenceError("Landmarks must identify the exact four source image hashes")
    for view in VIEWS:
        data = landmarks.get("views", {}).get(view, {})
        for name in LANDMARKS:
            entry = data.get(name, {})
            point(entry.get("world"))
            if entry.get("confidence") not in ("measured", "estimated", "uncertain"):
                raise ReferenceError(f"Missing landmark confidence: {view}/{name}")
            if not isinstance(entry.get("note"), str):
                raise ReferenceError("Landmarks need uncertainty/source notes")
        if type(data.get("mirrored")) is not bool or not isinstance(data.get("direction_evidence"), str):
            raise ReferenceError("Record direction and mirror checks for each view")
    if not isinstance(landmarks.get("inconsistencies"), list):
        raise ReferenceError("Record cross-view inconsistencies, even when empty")
    if any(x.get("resolved") is not True for x in landmarks["inconsistencies"]):
        raise ReferenceError("Resolve cross-view contradictions before modeling")
    neck = contract.get("neck", {})
    point(neck.get("center"))
    for key in ("width_m", "depth_m"):
        if type(neck.get(key)) not in (int, float) or not 0 < neck[key] <= height:
            raise ReferenceError("Record measured neck width and depth")
    for key in ("body", "head"):
        spec = contract.get(key)
        if not isinstance(spec, dict) or not isinstance(spec.get("source_notes"), str) or not spec["source_notes"]:
            raise ReferenceError(f"Record measured profiles and uncertainty for {key}")
        bounds = spec.get("bounds")
        if not isinstance(bounds, list) or len(bounds) != 3 or any(
            not isinstance(b, list) or len(b) != 2 or any(type(n) not in (int, float) for n in b)
            or not b[0] < b[1] for b in bounds
        ):
            raise ReferenceError(f"Define {key} XYZ working bounds")
    for key, mesh in (("body", body_mesh(contract["body"])), ("head", head_mesh(contract["head"]))):
        stats = mesh_stats(mesh)
        if stats["invalid_faces"] or stats["isolated_vertices"] or stats["boundary_edges"] or stats["nonmanifold_edges"]:
            raise ReferenceError(f"{key} contract does not form a closed valid base mesh: {stats}")
        bounds = contract[key]["bounds"]
        if any(not bounds[j][0] <= p[j] <= bounds[j][1] for p in mesh.vertices for j in range(3)):
            raise ReferenceError(f"{key} samples exceed their workspace bounds")


def prepare_session(source_blend, manifest_path, phase0_review, *, destination=None):
    """Run on Blender host after MCP discovery. Never change Phase 0 artifacts.

    Explicit destination is the exact output directory; omitted uses timestamped
    host Downloads. Both modes refuse existing directories and source aliases.
    """
    source, manifest_path, review_path = (Path(p).expanduser() for p in
                                         (source_blend, manifest_path, phase0_review))
    if any(not p.is_absolute() or not p.is_file() for p in (source, manifest_path, review_path)):
        raise ReferenceError("Use existing absolute Blender-host input paths")
    source, manifest_path, review_path = (p.resolve() for p in (source, manifest_path, review_path))
    manifest, review = load(manifest_path), load(review_path)
    if manifest.get("blend_file") != source.name or source.suffix.lower() != ".blend":
        raise ReferenceError("Phase 0 manifest and source blend do not match")
    if review.get("blend_sha256") != digest(source) or review.get("manifest_sha256") != digest(manifest_path):
        raise ReferenceError("Phase 0 review is stale or belongs to different files")
    require_passes(review, (*VIEWS, "locks", "alignment", "packed", "reopen"))
    refs = manifest.get("references", {})
    if set(refs) != set(VIEWS) or set(manifest.get("cameras", {})) != set(VIEWS):
        raise ReferenceError("Phase 0 lacks four references/cameras")
    paths = {}
    for view in VIEWS:
        if refs[view].get("packed") is not True:
            raise ReferenceError("All Phase 0 images must be packed")
        p = Path(refs[view]["input"]["path"])
        p = p if p.is_absolute() else manifest_path.parent / p
        p = p.resolve()
        if not p.is_file():
            raise ReferenceError(f"Source image unavailable on Blender host: {p}")
        paths[view] = p
    if len(set(paths.values())) != 4:
        raise ReferenceError("Four distinct reference images required")
    target = (Path(destination).expanduser() if destination is not None else
              downloads_directory() / datetime.now().strftime("char_base_%Y%m%d_%H%M%S"))
    if not target.is_absolute() or not target.parent.is_dir() or target.is_symlink() or target.exists():
        raise ReferenceError("Output must be a new absolute directory with an accessible parent")
    target.mkdir()
    try:
        for folder in ("references", "phase0_source", "review", "attempts"):
            (target / folder).mkdir()
        image_hashes = {v: digest(p) for v, p in paths.items()}
        for v, p in paths.items():
            shutil.copyfile(p, target / "references" / (v + p.suffix.lower()))
        records = {"blend": {"path": str(source), "sha256": digest(source)},
                   "manifest": {"path": str(manifest_path), "sha256": digest(manifest_path)},
                   "review": {"path": str(review_path), "sha256": digest(review_path)},
                   "images": {v: {"path": str(p), "sha256": image_hashes[v]} for v, p in paths.items()}}
        write_new(target / "phase0_source/inputs.json", records)
        shutil.copyfile(source, target / "phase1_working.blend")
        write_new(target / "state.json", {"state": "REFERENCES_READY", "status": "ACTIVE",
                  "sources": image_hashes, "history": [], "reworks": {}, "contract_sha256": None})
    except Exception:
        shutil.rmtree(target)
        raise
    return target


def verify_sources(session):
    records = load(Path(session) / "phase0_source/inputs.json")
    for record in [records["blend"], records["manifest"], records["review"], *records["images"].values()]:
        if digest(record["path"]) != record["sha256"]:
            raise ReferenceError("Phase 0 source changed; stop before further writes")


def transition(state, target, *, review=None, evidence=None):
    """Pure transition; caller persists only after Blender operation/evidence save."""
    state = json.loads(json.dumps(state))
    if state["status"] != "ACTIVE":
        raise ReferenceError("Session is halted; start an explicitly replanned session")
    current = state["state"]
    if target not in STATES or STATES.index(target) != STATES.index(current) + 1:
        raise ReferenceError(f"Invalid phase transition: {current} -> {target}")
    if target.endswith("REVIEW") or target == "PHASE1_COMPLETE":
        if not isinstance(review, dict) or not isinstance(evidence, dict):
            raise ReferenceError("An independent review and bound artifacts are required")
        verdict = review.get("verdict")
        if verdict not in ("PASS", "REWORK", "REPLAN", "BLOCKED"):
            raise ReferenceError("Unknown reviewer verdict")
        if not review.get("reviewer") or review.get("role") != "Reviewer":
            raise ReferenceError("Use an independent, read-only Reviewer role")
        if review.get("evidence") != evidence or not evidence:
            raise ReferenceError("Reviewer evidence is missing or stale")
        findings = review.get("findings")
        if not isinstance(findings, list):
            raise ReferenceError("Reviewer findings must be an array")
        keys = {"region", "severity", "evidence", "expected", "observed", "suggested_action", "preserve_regions", "attempt"}
        if any(not isinstance(f, dict) or not keys <= f.keys() for f in findings):
            raise ReferenceError("Incomplete structured finding")
        if verdict == "PASS":
            require_passes(review.get("checks", {}), VISUAL_CHECKS)
            if any(f["severity"] in ("error", "critical") for f in findings):
                raise ReferenceError("PASS cannot contain unresolved errors")
        elif not findings:
            raise ReferenceError("Non-PASS verdict needs actionable findings")
        if verdict == "REWORK":
            count = state["reworks"].get(target, 0) + 1
            state["reworks"][target] = count
            if count > 2:
                verdict = "REPLAN"
        state["history"].append({"gate": target, "verdict": verdict, "review": review})
        if verdict != "PASS":
            if verdict in ("REPLAN", "BLOCKED"):
                state["status"] = verdict
            return state
    state["state"] = target
    if target == "PHASE1_COMPLETE":
        state["status"] = "COMPLETE"
    return state
