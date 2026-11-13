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


def measure_section(views, observations, *, region, ring_index, note):
    """Convert four calibrated silhouette spans; retain each view independently.

    observations[view] = [left_px, right_px, row_px]. Select each leg separately
    when appropriate. `views` keys are verified camera directions, which need
    not match the original filenames. No averaging, mirroring or ellipse fit.
    """
    from reference_common import VIEWS
    if set(observations) != set(VIEWS) or set(views) != set(VIEWS):
        raise ReferenceError('A section needs four calibrated directional spans')
    result = {'region': region, 'ring_index': ring_index, 'note': note, 'views': {}}
    for name in VIEWS:
        view = views[name]
        values = observations[name]
        if (view.name != name or not isinstance(values, (list,tuple)) or len(values) != 3
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
            raise ReferenceError('Use verified camera directions and finite pixel spans')
        left, right, row = values
        if not 0 <= left < right <= view.width_px or not 0 <= row <= view.height_px:
            raise ReferenceError('Section pixels lie outside the calibrated image')
        a, b = pixel_to_world(view,left,row), pixel_to_world(view,right,row)
        axis = 0 if name in ('front','back') else 1
        result['views'][name] = {'min': min(a[axis],b[axis]), 'max': max(a[axis],b[axis]), 'z': a[2]}
    validate_section(result)
    return result


def validate_section(section):
    from reference_common import VIEWS
    if (not isinstance(section, dict) or section.get('region') not in
            ('torso','arm_left','arm_right','leg_left','leg_right')
            or type(section.get('ring_index')) is not int or section['ring_index'] < 0
            or not isinstance(section.get('note'), str) or not section['note'].strip()
            or set(section.get('views', {})) != set(VIEWS)):
        raise ReferenceError('Section needs region, ring_index, note and four views')
    for span in section['views'].values():
        if (not isinstance(span,dict) or any(type(span.get(k)) not in (int,float) or
                not math.isfinite(span[k]) for k in ('min','max','z')) or span['min'] >= span['max']):
            raise ReferenceError('Section bounds must be finite and increasing')


def section_errors(section, ring):
    """Compare measured spans with explicit ring samples; report, never auto-fix.

    For tilted rings z_min/z_max errors reveal a nonmatching slice. This is a
    sample-extents comparison, not intersection of a full surface with a plane.
    """
    from phase1_geometry import point
    validate_section(section)
    points = [point(p) for p in ring]
    if len(points) < 4:
        raise ReferenceError('Section comparison requires at least four samples')
    result = {}
    for view, span in section['views'].items():
        axis = 0 if view in ('front','back') else 1
        lo, hi = min(p[axis] for p in points), max(p[axis] for p in points)
        result[view] = {'min_error_m': lo-span['min'], 'max_error_m': hi-span['max'],
                        'span_error_m': (hi-lo)-(span['max']-span['min']),
                        'z_min_error_m': min(p[2] for p in points)-span['z'],
                        'z_max_error_m': max(p[2] for p in points)-span['z']}
    return {'views': result, 'perimeter_m': sum(math.dist(a,b) for a,b in zip(points,points[1:]+points[:1])),
            'sample_count': len(points), 'visual_silhouette': 'UNVERIFIED'}


def measured_sections(spec):
    """Validate/report optional measured plan sections; indices exclude transitions."""
    rings = {'torso': spec['torso'], **{p['region']:p['rings'] for p in spec['limbs']}}
    sections = spec.get('measured_sections', [])
    if not isinstance(sections, list):
        raise ReferenceError('measured_sections must be an array')
    result = []
    for section in sections:
        validate_section(section)
        profiles = rings[section['region']]
        if section['ring_index'] >= len(profiles):
            raise ReferenceError('Measured section ring_index is outside the selected region')
        result.append({'region': section['region'], 'ring_index': section['ring_index'],
                       **section_errors(section, profiles[section['ring_index']])})
    return result
