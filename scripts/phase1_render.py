"""Calibrated reference compositing, separate from modeling and review state."""
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from phase1_contract import load
from reference_common import ReferenceError

def reference_overlay(scene, camera, view, rendered, destination):
    """Align the packed reference through its actual world transform to the render.

    Nearest-neighbour reference sampling is deliberate: no silhouette/background
    is inferred. This is a visual comparison artifact, not an automatic PASS.
    """
    from array import array
    obj = bpy.data.objects["REF_" + view.upper()]
    image = obj.data
    width, height = image.size
    records = load(scene["p1_manifest_path"])
    world_width, world_height = records["references"][view]["world_size_m"]
    def project(x, y):
        return world_to_camera_view(scene, camera, obj.matrix_world @ Vector((x, y, 0)))
    p0 = project(-world_width/2, -world_height/2)
    px = project(world_width/2, -world_height/2)
    py = project(-world_width/2, world_height/2)
    if abs(px.y-p0.y) > 1e-5 or abs(py.x-p0.x) > 1e-5:
        raise ReferenceError("Reference projection is not axis aligned")
    if abs(px.x-p0.x) < 1e-8 or abs(py.y-p0.y) < 1e-8:
        raise ReferenceError("Reference projection collapsed")
    rw, rh = rendered.size
    original = array('f', [0.]) * (width*height*4)
    image.pixels.foreach_get(original)
    model = array('f', [0.]) * (rw*rh*4)
    rendered.pixels.foreach_get(model)
    output = array('f', [1.]) * (rw*rh*4)
    for y in range(rh):
        v = ((y+.5)/rh-p0.y)/(py.y-p0.y)
        for x in range(rw):
            u = ((x+.5)/rw-p0.x)/(px.x-p0.x)
            i = 4*(y*rw+x)
            backdrop = (1., 1., 1.)
            if 0 <= u < 1 and 0 <= v < 1:
                k = 4*(min(height-1,int(v*height))*width+min(width-1,int(u*width)))
                alpha = original[k+3]
                backdrop = tuple(original[k+j]*alpha + 1-alpha for j in range(3))
            alpha = .55 * model[i+3]
            for j in range(3):
                output[i+j] = backdrop[j]*(1-alpha) + model[i+j]*alpha
    composed = bpy.data.images.new("P1_overlay_temp", width=rw, height=rh, alpha=True)
    try:
        composed.pixels.foreach_set(output)
        composed.filepath_raw = str(destination)
        composed.file_format = 'PNG'
        composed.save()
    finally:
        bpy.data.images.remove(composed)
    return {"reference_origin_uv": list(p0), "reference_right_uv": list(px),
            "reference_up_uv": list(py), "render_size": [rw, rh],
            "mirroring": "preserved_from_Phase0", "mask_metrics": "UNVERIFIED"}


