"""Optional real Blender API smoke test using synthetic geometry, never likeness.

blender --background --factory-startup --python-exit-code 2 --python tests/blender_midpoly_smoke.py
"""
import sys, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root/'scripts'),str(root/'tests')]
import bpy
from phase1_fixtures import contract
from phase1_geometry import body_mesh, head_mesh, require_mesh_health
from phase1_regions import capture
from phase1_blender import validate_scene, OWNER
from phase1_budget import summarize, policy
from reference_common import ReferenceError
for region, builder in [('body',body_mesh),('head',head_mesh)]:
    spec = contract()[region]
    if region == 'body':
        for limb in spec['limbs']:
            a,b = limb['rings'][:2]
            # Explicit synthetic intermediate ring; production coordinates must
            # come from observed references, not generic interpolation.
            middle = [tuple((x+y)/2 for x,y in zip(p,q)) for p,q in zip(a,b)]
            limb['transition_rings'] = [a, middle]
            limb['rings'] = limb['rings'][1:]
            limb['transition_note'] = 'Synthetic API smoke fixture'
    geom = builder(spec)
    data = bpy.data.meshes.new(region)
    data.from_pydata(geom.vertices, [], geom.faces)
    data.update()
    obj = bpy.data.objects.new('P1_'+region.upper(), data)
    bpy.context.scene.collection.objects.link(obj)
    obj[OWNER] = region
    obj['semantic_face_map'] = json.dumps(capture(geom.faces, geom.regions))
    obj['semantic_face_order'] = json.dumps(geom.faces)
    obj['junction_plan'] = json.dumps(geom.junctions)
stats = validate_scene()
for item in stats.values(): require_mesh_health(item)
assert len(stats['P1_BODY']['junctions']) == 4
assert all(s['original']['triangles'] == sum(s['region_triangles'].values()) for s in stats.values())
assert summarize(stats,policy())['status'] == 'PASS'
print('SYNTHETIC_BLENDER_SMOKE_PASS',bpy.app.version_string,{k:v['evaluated']['triangles'] for k,v in stats.items()})

obj = bpy.data.objects['P1_BODY']
faces = json.loads(obj['semantic_face_order'])
labels = json.loads(obj['semantic_face_map'])
from phase1_regions import resolve
face = next(f for f,r in zip(faces,resolve(faces,labels)) if r.endswith(':junction'))
obj.data.vertices[face[3]].co = obj.data.vertices[face[0]].co
obj.data.update()
try:
    require_mesh_health(validate_scene()['P1_BODY'])
except ReferenceError:
    print('SYNTHETIC_POST_EDIT_REJECTION_PASS')
else:
    raise AssertionError('Collapsed current seam was accepted')
