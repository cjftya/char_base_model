"""Synthetic topology fixtures only. Never use these proportions for a character."""
import copy
import math

from phase1_geometry import Mesh, loft, remove_patch
from phase1_contract import LANDMARKS
from reference_common import VIEWS


def rings():
    return [[(.3*math.cos(i*math.tau/16), .25*math.sin(i*math.tau/16), z)
             for i in range(16)] for z in (.2,.4,.6,.8,1.,1.2)]


def branch(mesh, face_index, region):
    face = mesh.faces[face_index]
    points = [mesh.vertices[i] for i in face]
    center = tuple(sum(p[j] for p in points)/len(points) for j in range(3))
    direction = (center[0], center[1], 0)
    length = math.sqrt(sum(x*x for x in direction))
    direction = tuple(x/length for x in direction)
    profile = [[tuple(center[j]+(p[j]-center[j])*scale+direction[j]*distance for j in range(3))
                for p in points] for scale,distance in ((.8,.03),(.65,.1),(.4,.2))]
    feature = {"region": region, "patch_faces": [face_index], "rings": profile}
    # Follow exactly the same evolving face indices as the actual constructor.
    edge = remove_patch(mesh, [face_index])
    ids = loft(mesh, profile, region, cap_start=False)
    mesh.bridge(edge,ids[0],region+":junction")
    return feature


def contract():
    profile = rings()
    body = {"torso": profile, "limbs": [], "source_notes": "synthetic topology fixture",
            "bounds": [[-2,2],[-2,2],[0,2]]}
    mesh = Mesh()
    loft(mesh,profile,"torso")
    for region in ("arm_left","arm_right","leg_left","leg_right"):
        body["limbs"].append(branch(mesh, 16, region))
    head = {"rings": copy.deepcopy(profile), "features": [], "source_notes": "synthetic fixture",
            "bounds": [[-2,2],[-2,2],[0,2]], "nose_vertices": [12,28,44], "nose_base": [0,-.2,.5]}
    mesh = Mesh()
    loft(mesh,head["rings"],"skull")
    for region in ("eye_left","eye_right","mouth","ear_left","ear_right"):
        head["features"].append(branch(mesh, 32, region))
    return {"schema_version":1, "height_m":1.6,
            "axes":{"up":"+Z","front":"-Y","sole_z":0},
            "neck":{"center":[0,0,1],"width_m":.1,"depth_m":.1},
            "body":body,"head":head}


def landmarks(hashes):
    return {"schema_version":1,"source_hashes":hashes,"inconsistencies":[],"views":{
        v:{"mirrored":False,"direction_evidence":"synthetic only",**{
            n:{"world":[0,0,.5],"confidence":"estimated","note":"test fixture"} for n in LANDMARKS
        }} for v in VIEWS}}
