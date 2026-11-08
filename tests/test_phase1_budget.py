"""Budget boundaries, contract preflight, and Blender evaluation cleanup."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase1_budget import policy, summarize, require_budget
from phase1_geometry import Mesh, mesh_stats, body_mesh
from phase1_contract import validate_contract
from phase1_fixtures import contract, landmarks
from reference_common import ReferenceError, VIEWS


def entry(n, **kwargs):
    counts = dict(vertices=10, edges=20, faces=5, triangles=n)
    return dict(original=counts, evaluated=counts,
                render_evaluation_verified=True, **kwargs)


class BudgetTests(unittest.TestCase):
    def test_warning_limit_and_excess_boundaries(self):
        rules = policy()
        limit = rules['max_total_triangles']
        warning = int(limit * rules['warning_ratio'])
        for n, expected in ((0, 'PASS'), (warning-1, 'PASS'), (warning, 'WARNING'),
                            (limit, 'WARNING'), (limit+1, 'FAIL')):
            result = summarize({'body': entry(n)}, rules)
            self.assertEqual(result['status'], expected)
            if n > limit:
                with self.assertRaises(ReferenceError): require_budget(result)
            else:
                require_budget(result)

    def test_evaluated_total_counts_separate_mesh_and_excludes_hidden(self):
        body = entry(100)
        body['evaluated'] = dict(body['original'], triangles=29999)
        result = summarize({'body': body, 'eyes': entry(2),
                            'hidden': entry(50000, hide_render=True)}, policy())
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['totals']['evaluated']['triangles'], 30001)
        self.assertEqual(result['totals']['original']['triangles'], 102)
        self.assertEqual(result['objects'][0]['modifier_growth'], 29899)
        self.assertEqual(result['excluded_objects'], ['hidden'])

    def test_unverified_render_cannot_pass_even_with_low_viewport_count(self):
        data = entry(5); data['render_evaluation_verified'] = False
        with self.assertRaises(ReferenceError):
            require_budget(summarize({'body': data}, policy()))

    def test_overrides_require_reason_and_validate_numbers(self):
        for overrides in ({'max_total_triangles': True}, {'warning_ratio': float('nan')},
                          {'warning_ratio': 0}, {'target_triangle_range': [5, 1]},
                          {'unknown': 1}, {'max_total_triangles': 60000}):
            with self.assertRaises(ReferenceError): policy(overrides)
        rules = policy({'max_total_triangles': 60000, 'exception_reason': 'Measured facial detail'})
        self.assertEqual(summarize({'body': entry(40000)}, rules)['status'], 'PASS')

    def test_ngon_and_duplicate_faces(self):
        mesh = Mesh([(0,0,0),(1,0,0),(2,1,0),(1,2,0),(0,1,0)], [(0,1,2,3,4)])
        self.assertEqual(mesh_stats(mesh)['triangles'], 3)
        mesh.faces.append((4,3,2,1,0))
        self.assertEqual(mesh_stats(mesh)['duplicate_faces'], 1)

    def test_dense_input_rejected_before_allocating_geometry(self):
        spec = copy.deepcopy(contract()['body'])
        spec['torso'] = [spec['torso'][0]] * (policy()['max_loft_rings']+1)
        with self.assertRaisesRegex(ReferenceError, 'excessive ring density'):
            body_mesh(spec)
        spec['torso'] = [[(0,0,0)] * (policy()['max_ring_samples']+1)] * 2
        with self.assertRaisesRegex(ReferenceError, 'excessive ring density'):
            body_mesh(spec)

    def test_aggregate_contract_budget_and_explicit_exception(self):
        c = contract(); sources = dict(zip(VIEWS, VIEWS))
        c['polygon_policy'] = {'max_total_triangles': 1, 'exception_reason': 'Boundary test'}
        with self.assertRaisesRegex(ReferenceError, 'budget blocks acceptance'):
            validate_contract(c, landmarks(sources), sources)
        c['polygon_policy']['max_total_triangles'] = 60000
        validate_contract(c, landmarks(sources), sources)
