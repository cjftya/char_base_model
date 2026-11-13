"""Shared polygon policy and pure budget checks. No geometry is repaired here."""
import json
import math
from pathlib import Path
from reference_common import ReferenceError


def policy(overrides=None):
    defaults = json.loads((Path(__file__).resolve().parents[1] /
                           'config/polygon_policy.json').read_text(encoding='utf-8'))
    if overrides is not None and not isinstance(overrides, dict):
        raise ReferenceError('polygon_policy must be an object')
    overrides = overrides or {}
    if set(overrides) - defaults.keys():
        raise ReferenceError('Unknown polygon_policy setting')
    result = {**defaults, **overrides}
    for key in ('max_total_triangles', 'max_ring_samples', 'max_loft_rings'):
        if type(result[key]) is not int or result[key] <= 0:
            raise ReferenceError('Invalid polygon_policy ' + key)
    span = result['target_triangle_range']
    if (not isinstance(span, list) or len(span) != 2 or
            any(type(n) is not int or n <= 0 for n in span) or span[0] > span[1]):
        raise ReferenceError('Invalid target_triangle_range')
    ratio = result['warning_ratio']
    if type(ratio) not in (int, float) or not math.isfinite(ratio) or not 0 < ratio <= 1:
        raise ReferenceError('Invalid warning_ratio')
    if not isinstance(result['exception_reason'], str):
        raise ReferenceError('exception_reason must be text')
    if (any(result[k] != defaults[k] for k in defaults if k != 'exception_reason')
            and not result['exception_reason'].strip()):
        raise ReferenceError('Policy changes require exception_reason')
    return result


def check_lofts(spec, region, rules):
    lofts = [(region, spec['torso' if region == 'body' else 'rings'])]
    for part in spec.get('limbs' if region == 'body' else 'features', []):
        transitions = part.get('transition_rings', []) if region == 'body' else []
        if not isinstance(transitions, list):
            raise ReferenceError('transition_rings must be an array')
        lofts.append((part['region'], transitions + part['rings']))
    for name, rings in lofts:
        if len(rings) > rules['max_loft_rings'] or any(
                len(r) > rules['max_ring_samples'] for r in rings):
            raise ReferenceError(f'{name}: excessive ring density; replan measured loops, do not Decimate')


def summarize(meshes, rules):
    included = {name: s for name, s in meshes.items() if not s.get('hide_render', False)}
    totals = {stage: {key: sum(s[stage][key] for s in included.values())
                      for key in ('vertices', 'edges', 'faces', 'triangles')}
              for stage in ('original', 'evaluated')}
    triangles = totals['evaluated']['triangles']
    verified = all(s.get('render_evaluation_verified', False) for s in included.values())
    status = ('BLOCKED' if not verified else 'FAIL' if triangles > rules['max_total_triangles']
              else 'WARNING' if triangles >= rules['max_total_triangles'] * rules['warning_ratio']
              else 'PASS')
    ranking = sorted(({'object': name, 'original_triangles': s['original']['triangles'],
                       'evaluated_triangles': s['evaluated']['triangles'],
                       'modifier_growth': s['evaluated']['triangles'] - s['original']['triangles'],
                       'modifiers': s.get('modifier_details', [])}
                      for name, s in included.items()), key=lambda x: x['evaluated_triangles'], reverse=True)
    return {'status': status, 'policy': rules, 'totals': totals, 'objects': ranking,
            'excess_triangles': max(0, triangles - rules['max_total_triangles']),
            'excluded_objects': sorted(set(meshes) - set(included)),
            'automatic_optimization': {'performed': False, 'before_after': None,
                                       'shape_damage_risk': 'No automatic geometry changes'},
            'reference_match': 'MANUAL_REVIEW_REQUIRED',
            'exported_mesh': 'NOT_EXPORTED'}


def require_budget(summary):
    if summary['status'] in ('FAIL', 'BLOCKED'):
        raise ReferenceError('Polygon budget blocks acceptance: ' + json.dumps(summary))
