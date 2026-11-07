"""Convert individually calibrated image observations into world landmarks.

This assists the agent's visual measurement; it does not infer anatomy from
unobserved pixels. Supply a depth coordinate only when supported by another view.
"""
from __future__ import annotations
import math
from reference_common import ReferenceError


def pixel_to_world(view, x_px, y_px, *, hidden_axis=0.0):
    """Use Phase 0 ReferenceView. Top-left pixel origin, -Y character front."""
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x_px,y_px,hidden_axis)):
        raise ReferenceError("Pixel/depth coordinates must be finite")
    horizontal = (x_px/view.width_px-view.center_x)*view.world_width_m
    z = (view.foot_y-y_px/view.height_px)*view.world_height_m
    if view.name == 'front': return [horizontal,hidden_axis,z]
    if view.name == 'back': return [-horizontal,hidden_axis,z]
    if view.name == 'left': return [hidden_axis,-horizontal,z]
    if view.name == 'right': return [hidden_axis,horizontal,z]
    raise ReferenceError("Unknown orthographic view")


def landmark_errors(observations, expected):
    """Keep view-specific deviations; never average contradictory anatomy away."""
    result = {}
    for view, points in observations.items():
        result[view] = {}
        for key, position in points.items():
            if key not in expected:
                continue
            if len(position)!=3 or len(expected[key])!=3:
                raise ReferenceError("Landmark positions need three coordinates")
            result[view][key] = math.dist(position,expected[key])
    return result
