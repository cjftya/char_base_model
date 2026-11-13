"""Local geometric diagnostics, not proof of anatomical or global mesh validity."""
import math
from reference_common import ReferenceError


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def normal(points):
    result = [0., 0., 0.]
    for a, b in zip(points, points[1:]+points[:1]):
        c = cross(a, b)
        result = [x+y for x, y in zip(result, c)]
    return result


def quad_quality(points):
    """Check both triangulations; detect concave/bow-tie/degenerate folded quads.

    Nonplanarity alone is allowed. Values are scale-relative; opposing triangle
    normals are rejected instead of silently choosing the convenient diagonal.
    """
    scale = max(math.dist(a, b) for a in points for b in points)
    epsilon = max(scale**4 * 1e-12, 1e-30)
    cosines = []
    for a, b, c, d in (points, points[1:]+points[:1]):
        n1, n2 = cross(sub(b,a), sub(c,a)), cross(sub(c,a), sub(d,a))
        product = math.sqrt(dot(n1,n1)*dot(n2,n2))
        if product <= epsilon:
            return {"folded": True, "min_normal_cosine": -1.0}
        cosines.append(dot(n1,n2)/product)
    return {"folded": min(cosines) <= 0, "min_normal_cosine": min(cosines)}


def segment_distance(a, b, c, d):
    """Minimum distance of finite 3D segments, including parallel segments."""
    u, v, w = sub(b,a), sub(d,c), sub(a,c)
    aa, bb, cc, dd, ee = dot(u,u), dot(u,v), dot(v,v), dot(u,w), dot(v,w)
    if aa == 0 or cc == 0:
        return 0.0  # collapsed correspondence is invalid anyway
    denom = aa*cc-bb*bb
    s = max(0., min(1., (bb*ee-cc*dd)/denom)) if denom > aa*cc*1e-12 else 0.
    t = (bb*s+ee)/cc
    if t < 0:
        t, s = 0., max(0., min(1., -dd/aa))
    elif t > 1:
        t, s = 1., max(0., min(1., (bb-dd)/aa))
    return math.sqrt(sum((w[i]+s*u[i]-t*v[i])**2 for i in range(3)))


def correspondence(host, root, offset=0):
    """Inspect, never auto-reverse/mirror. Offset rotates every branch ring."""
    if len(host) != len(root) or len(host) < 4:
        raise ReferenceError("Junction boundaries need equal sample counts >=4")
    n = len(host)
    if type(offset) is not int or not 0 <= offset < n:
        raise ReferenceError("boundary_offset must be a valid cyclic sample index")
    costs = [sum(math.dist(host[i], root[(i+k)%n])**2 for i in range(n)) for k in range(n)]
    best = min(range(n), key=costs.__getitem__)
    aligned = root[offset:]+root[:offset]
    normals = (normal(host), normal(aligned))
    lengths = [math.dist(a,b) for a,b in zip(host,aligned)]
    scale = max(math.dist(a,b) for a in host for b in host)
    tolerance = max(scale*1e-8, 1e-12)
    folds = [i for i in range(n) if quad_quality(
        [host[i],host[(i+1)%n],aligned[(i+1)%n],aligned[i]])['folded']]
    crossings = [[i,j] for i in range(n) for j in range(i+1,n)
                 if segment_distance(host[i],aligned[i],host[j],aligned[j]) <= tolerance]
    return {'offset': offset, 'suggested_offset': best,
            'mapping_distance_squared': costs[offset], 'best_distance_squared': costs[best],
            'nonminimal_mapping': costs[offset] > costs[best]+max(costs[best]*1e-6, tolerance**2),
            'reversed_winding': dot(*normals) <= 0,
            'folded_quads': folds, 'crossing_bridge_edges': crossings,
            'min_bridge_length': min(lengths), 'max_bridge_length': max(lengths),
            'collapsed_bridge': min(lengths) <= tolerance,
            'visual_continuity': 'UNVERIFIED'}


def require_correspondence(report, *, explicit_mapping=False):
    if (report['reversed_winding'] or report['folded_quads'] or
            report['crossing_bridge_edges'] or report['collapsed_bridge']):
        raise ReferenceError('Invalid junction winding/fold/crossing: ' + str(report))
    if report['nonminimal_mapping'] and not explicit_mapping:
        raise ReferenceError('Nonminimal boundary mapping; measure/replan an explicit boundary_offset and mapping_note: ' + str(report))
