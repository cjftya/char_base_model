"""Reference-driven mesh construction, independent of Blender.

Coordinates are Blender world metres. Rings contain explicit 3D samples; there
are no hard-coded body proportions. Faces retain semantic region names.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math

from reference_common import ReferenceError
from phase1_budget import policy, check_lofts


def point(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or any(isinstance(x, bool) or not isinstance(x, (int, float))
                   or not math.isfinite(x) for x in value)):
        raise ReferenceError("Expected a finite 3D coordinate")
    return tuple(float(x) for x in value)


@dataclass
class Mesh:
    vertices: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    regions: list = field(default_factory=list)

    def face(self, indices, region):
        self.faces.append(tuple(indices))
        self.regions.append(region)

    def ring(self, coordinates):
        start = len(self.vertices)
        self.vertices.extend(point(p) for p in coordinates)
        return list(range(start, len(self.vertices)))

    def bridge(self, a, b, region):
        if len(a) != len(b) or len(a) < 3:
            raise ReferenceError("Bridged boundaries must have equal sample counts >=3")
        for j in range(len(a)):
            k = (j + 1) % len(a)
            self.face((a[j], a[k], b[k], b[j]), region)


def boundary(faces):
    """Return the ordered boundary of a connected, disk-shaped face patch."""
    counts = Counter(tuple(sorted((a, b))) for f in faces
                     for a, b in zip(f, f[1:] + f[:1]))
    vertices = {v for f in faces for v in f}
    if any(n > 2 for n in counts.values()) or len(vertices)-len(counts)+len(faces) != 1:
        raise ReferenceError("Attachment patch must be a manifold disk")
    adjacency = defaultdict(set)
    for a, b in counts:
        adjacency[a].add(b)
        adjacency[b].add(a)
    remaining = set(vertices)
    if not remaining:
        raise ReferenceError("Empty attachment patch")
    pending = [remaining.pop()]
    while pending:
        for v in adjacency[pending.pop()] & remaining:
            remaining.remove(v)
            pending.append(v)
    if remaining:
        raise ReferenceError("Attachment patch is disconnected")
    edges = [(a, b) for f in faces for a, b in zip(f, f[1:] + f[:1])
             if counts[tuple(sorted((a, b)))] == 1]
    following = {}
    for a, b in edges:
        if a in following:
            raise ReferenceError("Attachment patch is not a single disk")
        following[a] = b
    if not following:
        raise ReferenceError("Attachment patch has no boundary")
    result = [edges[0][0]]
    while following.get(result[-1]) != result[0]:
        nxt = following.get(result[-1])
        if nxt is None or nxt in result:
            raise ReferenceError("Attachment boundary is disconnected")
        result.append(nxt)
    if len(result) != len(edges):
        raise ReferenceError("Attachment patch has multiple boundaries")
    return result


def loft(mesh, rings, region, *, cap_start=True, cap_end=True):
    if not isinstance(rings, list) or len(rings) < 2:
        raise ReferenceError(f"{region}: supply at least two measured rings")
    if any(len(r) != len(rings[0]) or len(r) < 4 for r in rings):
        raise ReferenceError(f"{region}: rings need equal sample counts >=4")
    ids = [mesh.ring(r) for r in rings]
    for a, b in zip(ids, ids[1:]):
        mesh.bridge(a, b, region)
    if cap_start:
        mesh.face(tuple(reversed(ids[0])), region)
    if cap_end:
        mesh.face(ids[-1], region)
    return ids


def remove_patch(mesh, indices):
    if (not isinstance(indices, list) or not indices or len(set(indices)) != len(indices)
            or any(type(i) is not int or not 0 <= i < len(mesh.faces) for i in indices)):
        raise ReferenceError("Invalid attachment face indices")
    edge = boundary([mesh.faces[i] for i in indices])
    selected = set(indices)
    mesh.faces, mesh.regions = map(list, zip(*[
        (f, r) for i, (f, r) in enumerate(zip(mesh.faces, mesh.regions)) if i not in selected
    ])) if len(selected) < len(mesh.faces) else ([], [])
    return edge


def compact(mesh):
    used = sorted({v for f in mesh.faces for v in f})
    remap = {v: i for i, v in enumerate(used)}
    mesh.vertices = [mesh.vertices[v] for v in used]
    mesh.faces = [tuple(remap[v] for v in f) for f in mesh.faces]
    return mesh


def body_mesh(spec, *, polygon_policy=None):
    """Loft torso; replace measured surface patches with bridged limb branches.

    Patch indices refer to the current mesh after previous attachments. The
    first limb ring's ordering must match the host boundary; never auto-mirror.
    """
    check_lofts(spec, "body", policy(polygon_policy))
    mesh = Mesh()
    loft(mesh, spec["torso"], "torso")
    expected = {"arm_left", "arm_right", "leg_left", "leg_right"}
    limbs = spec.get("limbs", [])
    if {x.get("region") for x in limbs} != expected or len(limbs) != 4:
        raise ReferenceError("Body needs both arms and both legs")
    for limb in limbs:
        edge = remove_patch(mesh, limb["patch_faces"])
        rings = loft(mesh, limb["rings"], limb["region"], cap_start=False)
        # Winding follows the deleted host patch, so every seam edge is shared.
        mesh.bridge(edge, rings[0], limb["region"] + ":junction")
    return compact(mesh)


def head_mesh(spec, *, polygon_policy=None):
    """Loft a measured skull and replace facial patches with concentric loops.

    Each feature contains two or more explicit 3D rings (outer eyelid/lip rim,
    inner rim, socket/oral inset) and an optional closed centre. Nose and cheeks
    belong to the measured skull samples, not detached primitive decorations.
    Ears use the same integrated patch/bridge operation.
    """
    check_lofts(spec, "head", policy(polygon_policy))
    mesh = Mesh()
    loft(mesh, spec["rings"], "skull")
    features = spec.get("features", [])
    required = {"eye_left", "eye_right", "mouth", "ear_left", "ear_right"}
    if {x.get("region") for x in features} != required or len(features) != 5:
        raise ReferenceError("Head needs left/right eye, mouth and left/right ear patches")
    for feature in features:
        edge = remove_patch(mesh, feature["patch_faces"])
        rings = loft(mesh, feature["rings"], feature["region"], cap_start=False)
        mesh.bridge(edge, rings[0], feature["region"] + ":rim")
    nose = spec.get("nose_vertices", [])
    if len(nose) < 3 or len(set(nose)) != len(nose) or any(type(i) is not int or not 0 <= i < len(mesh.vertices) for i in nose):
        raise ReferenceError("Mark at least three integrated nose vertices")
    # World -Y is forward. A genuine nose must project beyond its supplied base.
    used = {v for f in mesh.faces for v in f}
    if any(i not in used for i in nose):
        raise ReferenceError("Nose samples were removed by a facial patch")
    for i, face in enumerate(mesh.faces):
        if mesh.regions[i] == "skull" and any(v in nose for v in face):
            mesh.regions[i] = "nose"
    base = point(spec["nose_base"])
    projection = base[1] - min(mesh.vertices[i][1] for i in nose)
    if projection <= 0:
        raise ReferenceError("Nose must project forward from its measured base")
    return compact(mesh)


def mesh_stats(mesh):
    """Topological checks. Self-intersections and visual quality need Blender/review."""
    vertices = [point(p) for p in mesh.vertices]
    edges = defaultdict(list)
    bad_faces = []
    used = set()
    for i, f in enumerate(mesh.faces):
        if len(f) < 3 or len(set(f)) != len(f) or any(type(v) is not int or not 0 <= v < len(vertices) for v in f):
            bad_faces.append(i)
            continue
        used.update(f)
        # Newell normal catches collinear/zero-area faces without triangulation.
        normal = [0., 0., 0.]
        for a, b in zip(f, f[1:] + f[:1]):
            p, q = vertices[a], vertices[b]
            normal[0] += (p[1]-q[1])*(p[2]+q[2])
            normal[1] += (p[2]-q[2])*(p[0]+q[0])
            normal[2] += (p[0]-q[0])*(p[1]+q[1])
            edges[tuple(sorted((a, b)))].append((a, b))
        if sum(n*n for n in normal) < 1e-24:
            bad_faces.append(i)
    adjacency = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    remaining = set(used)
    components = 0
    while remaining:
        components += 1
        pending = [remaining.pop()]
        while pending:
            for v in adjacency[pending.pop()] & remaining:
                remaining.remove(v)
                pending.append(v)
    return {
        "vertices": len(vertices), "edges": len(edges), "faces": len(mesh.faces),
        "triangles": sum(len(f)-2 for i, f in enumerate(mesh.faces) if i not in bad_faces),
        "duplicate_faces": len(mesh.faces)-len({tuple(sorted(f)) for f in mesh.faces}),
        "boundary_edges": sum(len(e) == 1 for e in edges.values()),
        "nonmanifold_edges": sum(len(e) > 2 for e in edges.values()),
        "inconsistent_winding_edges": sum(len(e) == 2 and e[0] == e[1] for e in edges.values()),
        "invalid_faces": bad_faces, "isolated_vertices": len(vertices)-len(used),
        "duplicate_vertices": len(vertices)-len(set(vertices)), "components": components,
        "bounds": [[min(p[j] for p in vertices), max(p[j] for p in vertices)] for j in range(3)] if vertices else [],
        "self_intersections": "UNVERIFIED", "visual_quality": "UNVERIFIED",
    }


def silhouette_metrics(reference, model, *, alignment_verified=False):
    """Compare binary row masks only after calibration/background confidence checks."""
    if not alignment_verified:
        return {"status": "UNVERIFIED", "reason": "Alignment/background not verified"}
    if (not reference or len(reference) != len(model) or not reference[0]
            or any(len(r) != len(reference[0]) for r in reference + model)):
        raise ReferenceError("Masks must have identical nonempty rectangular dimensions")
    if any(type(x) not in (bool, int) or x not in (0, 1) for row in reference + model for x in row):
        raise ReferenceError("Masks must be binary")
    intersection = sum(bool(a and b) for r, m in zip(reference, model) for a, b in zip(r, m))
    union = sum(bool(a or b) for r, m in zip(reference, model) for a, b in zip(r, m))
    if not union:
        return {"status": "UNVERIFIED", "reason": "Empty silhouettes"}
    return {"status": "MEASURED", "iou": intersection/union,
            "missing_pixels": sum(bool(a and not b) for r, m in zip(reference, model) for a, b in zip(r, m)),
            "excess_pixels": sum(bool(b and not a) for r, m in zip(reference, model) for a, b in zip(r, m)),
            "row_width_error_px": [sum(m)-sum(r) for r, m in zip(reference, model)]}

