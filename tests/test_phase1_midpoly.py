"""Synthetic junction and measurement regressions; no Blender likeness claim."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from phase1_geometry import Mesh, loft, body_mesh, mesh_stats, require_mesh_health, junction_metrics
from phase1_junction import correspondence, require_correspondence, quad_quality, segment_distance
from phase1_analysis import measure_section, section_errors, measured_sections
from phase1_contract import write_new, load, digest, prepare_session, validate_contract
from phase1_replan import prepare_replan
from phase1_workflow import transition
from phase1_fixtures import contract, landmarks, branch, rings
from reference_common import ReferenceView, ReferenceError, VIEWS


def loop(z, radius=1):
    return [(radius*math.cos(i*math.tau/8), radius*math.sin(i*math.tau/8), z) for i in range(8)]


class JunctionTests(unittest.TestCase):
    def test_explicit_cyclic_mapping_and_reversed_winding(self):
        a, b = loop(0), loop(.2,.9)
        require_correspondence(correspondence(a,b))
        shifted = b[2:]+b[:2]
        bad = correspondence(a,shifted)
        self.assertEqual(bad['suggested_offset'],6)
        with self.assertRaises(ReferenceError): require_correspondence(bad)
        require_correspondence(correspondence(a,shifted,6))
        with self.assertRaises(ReferenceError): require_correspondence(correspondence(a,list(reversed(b))))
        for offset in (-1,8,True,.5):
            with self.assertRaises(ReferenceError): correspondence(a,b,offset)

    def test_twisted_concave_and_collapsed_geometry(self):
        self.assertFalse(quad_quality([(0,0,0),(1,0,0),(1,1,0),(0,1,0)])['folded'])
        for points in ([(0,0,0),(1,1,0),(1,0,0),(0,1,0)],
                       [(0,0,0),(1,0,0),(.2,.2,0),(0,1,0)]):
            self.assertTrue(quad_quality(points)['folded'])
        self.assertAlmostEqual(segment_distance((0,0,0),(1,1,0),(0,1,0),(1,0,0)),0)
        self.assertAlmostEqual(segment_distance((0,0,0),(1,0,0),(0,1,0),(1,1,0)),1)
        with self.assertRaises(ReferenceError): require_correspondence(correspondence(loop(0),loop(0)))
        b = loop(.1)[4:]+loop(.1)[:4]
        report = correspondence(loop(0),b)
        self.assertTrue(report['crossing_bridge_edges'])
        with self.assertRaises(ReferenceError): require_correspondence(report, explicit_mapping=True)

    def transitioned_body(self):
        spec = contract()['body']
        # Recompute evolving patch numbers as an author must after adding rings.
        mesh = Mesh(); loft(mesh,spec['torso'],'torso')
        spec['limbs'] = []
        for region in ('arm_left','arm_right','leg_left','leg_right'):
            part = branch(mesh,16,region)
            # Add a real intermediate loop between the patch and root.
            # Host vertices of each bridge quad retain the deleted patch order.
            host = [mesh.vertices[f[0]] for f in mesh.faces[-4:]]
            part['transition_rings'] = [[tuple((a+b)/2 for a,b in zip(p,q))
                                          for p,q in zip(host,part['rings'][0])]]
            part['transition_note'] = 'Synthetic measured proximal span' 
            spec['limbs'].append(part)
        return spec

    def test_measured_transitions_remain_closed_and_single_component(self):
        spec = self.transitioned_body()
        mesh = body_mesh(spec); stats = mesh_stats(mesh)
        require_mesh_health(stats)
        self.assertEqual(stats['components'],1)
        self.assertEqual([j['transition_rings'] for j in mesh.junctions],[1]*4)
        for key in ('duplicate_faces','inconsistent_winding_edges','boundary_edges','nonmanifold_edges'):
            self.assertEqual(stats[key],0)
        del spec['limbs'][0]['transition_note']
        with self.assertRaisesRegex(ReferenceError,'transition_note'): body_mesh(spec)

    def test_mapping_rotates_entire_branch_without_changing_shape(self):
        spec = self.transitioned_body(); expected = body_mesh(spec)
        for part in spec['limbs']:
            part['rings'] = [r[1:]+r[:1] for r in part['rings']]
            part['transition_rings'] = [r[1:]+r[:1] for r in part['transition_rings']]
            part['boundary_offset'] = 3
            part['mapping_note'] = 'Explicitly align rotated sample start'
        actual = body_mesh(spec)
        self.assertEqual(actual.vertices,expected.vertices)
        self.assertEqual(actual.faces,expected.faces)

    def test_transition_budget_counts_combined_rings_and_sample_counts(self):
        spec = self.transitioned_body()
        spec['limbs'][0]['transition_rings'] *= 128
        with self.assertRaisesRegex(ReferenceError,'excessive ring density'): body_mesh(spec)
        spec = self.transitioned_body()
        spec['limbs'][0]['transition_rings'][0] = spec['limbs'][0]['transition_rings'][0][:-1]
        with self.assertRaises(ReferenceError): body_mesh(spec)

    def test_transitions_do_not_replace_required_ordinary_rings(self):
        spec = self.transitioned_body()
        spec['limbs'][0]['rings'] = spec['limbs'][0]['rings'][:1]
        with self.assertRaisesRegex(ReferenceError,'two ordinary'): body_mesh(spec)

    def test_schema_accepts_transition_and_section_contract(self):
        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest('Optional JSON Schema conformance test needs jsonschema')
        c = contract(); c['body'] = self.transitioned_body()
        c['body']['measured_sections'] = [SectionTests().section()]
        schema = json.loads((Path(__file__).resolve().parents[1]/'contracts/phase1.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(json.loads(json.dumps(c)),schema)
        hashes = dict(zip(VIEWS,VIEWS))
        validate_contract(c,landmarks(hashes),hashes)

    def test_attaching_to_previous_limb_is_rejected(self):
        spec = contract()['body']
        mesh = Mesh(); loft(mesh,spec['torso'],'torso')
        branch(mesh,16,'arm_left')
        spec['limbs'][1]['patch_faces'] = [mesh.regions.index('arm_left')]
        with self.assertRaisesRegex(ReferenceError,'torso faces'): body_mesh(spec)

    def test_current_junction_metrics_detect_post_build_crossing(self):
        mesh = body_mesh(contract()['body'])
        reports = junction_metrics(mesh)
        self.assertEqual(len(reports),4)
        for report in reports: require_correspondence(report,explicit_mapping=True)
        face = next(f for f,r in zip(mesh.faces,mesh.regions) if r.endswith(':junction'))
        mesh.vertices[face[3]] = mesh.vertices[face[0]]
        self.assertTrue(any(r['collapsed_bridge'] for r in junction_metrics(mesh)))

    def test_runtime_volume_and_vertex_manifold_block_health(self):
        stats = mesh_stats(body_mesh(contract()['body']))
        for extra in ({'signed_volume':-1},{'signed_volume':0},{'nonmanifold_vertices':1}):
            with self.assertRaises(ReferenceError): require_mesh_health({**stats,**extra})

    def test_folded_quad_health_rejected(self):
        mesh = Mesh([(0,0,0),(1,1,0),(1,0,0),(0,1,0)],[(0,1,2,3)])
        self.assertTrue(mesh_stats(mesh)['folded_quads'])
        with self.assertRaises(ReferenceError): require_mesh_health(mesh_stats(mesh))


class SectionTests(unittest.TestCase):
    def section(self):
        views = {v:ReferenceView(v,Path('/'+v+'.png'),100,200,0,1,.5,2,4,0,0) for v in VIEWS}
        observations = {'front':[20,40,150], 'back':[60,80,150],
                        'left':[30,60,150], 'right':[40,70,150]}
        return measure_section(views,observations,region='leg_left',ring_index=0,note='calf rows')

    def test_world_extents_preserve_four_directions(self):
        s = self.section()
        for v in ('front','back'):
            self.assertAlmostEqual(s['views'][v]['min'],-.6)
            self.assertAlmostEqual(s['views'][v]['max'],-.2)
        for v in ('left','right'):
            self.assertAlmostEqual(s['views'][v]['min'],-.2)
            self.assertAlmostEqual(s['views'][v]['max'],.4)
        ring = [(-.6,-.2,1),(-.2,-.2,1),(-.2,.4,1),(-.6,.4,1)]
        for errors in section_errors(s,ring)['views'].values():
            for value in errors.values(): self.assertAlmostEqual(value,0)
        s['views']['right']['max'] = .5
        errors = section_errors(s,ring)['views']
        self.assertAlmostEqual(errors['right']['span_error_m'],-.1)
        self.assertAlmostEqual(errors['left']['span_error_m'],0)

    def test_plan_retains_separate_leg_measurements(self):
        spec = contract()['body']; a = self.section(); b = copy.deepcopy(a)
        b['region'] = 'leg_right'; b['views']['front']['max'] += .1
        spec['measured_sections'] = [a,b]
        results = measured_sections(spec)
        self.assertEqual([r['region'] for r in results],['leg_left','leg_right'])
        spec['measured_sections'][0]['ring_index'] = 999
        with self.assertRaises(ReferenceError): measured_sections(spec)

    def test_section_before_after_exposes_width_depth_and_density(self):
        s = self.section()
        before = [(-.7,-.3,1),(-.1,-.3,1),(-.1,.5,1),(-.7,.5,1)]
        after = [(-.6,-.2,1),(-.2,-.2,1),(-.2,.4,1),(-.6,.4,1)]
        a,b = section_errors(s,before),section_errors(s,after)
        self.assertGreater(abs(a['views']['front']['span_error_m']),abs(b['views']['front']['span_error_m']))
        self.assertGreater(a['perimeter_m'],b['perimeter_m'])
        self.assertEqual(a['sample_count'],b['sample_count'])


class ReplanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root/'source.blend'; source.write_bytes(b'phase0')
        refs = {}
        for v in VIEWS:
            p = self.root/(v+'.png'); p.write_bytes(v.encode())
            refs[v] = {'input':{'path':str(p)},'packed':True}
        manifest = self.root/'manifest.json'
        write_new(manifest,{'blend_file':source.name,'character_height_m':1.6,'references':refs,'cameras':dict.fromkeys(VIEWS,'camera')})
        review = self.root/'review.json'
        write_new(review,{**dict.fromkeys((*VIEWS,'locks','alignment','packed','reopen'),'PASS'),
                          'blend_sha256':digest(source),'manifest_sha256':digest(manifest)})
        self.parent = prepare_session(source,manifest,review,destination=self.root/'parent')
        state = load(self.parent/'state.json'); c = contract(); del c['head']
        write_new(self.parent/'model_contract.json',c)
        write_new(self.parent/'landmarks.json',landmarks(state['sources']))
        checkpoint = self.parent/'phase1_generation_test.blend'; checkpoint.write_bytes(b'failed Body')
        state.update(status='REPLAN',state='BODY_BLOCKOUT',contract_sha256=digest(self.parent/'model_contract.json'),
                     landmarks_sha256=digest(self.parent/'landmarks.json'),checkpoint={'file':checkpoint.name,'sha256':digest(checkpoint)})
        (self.parent/'state.json').write_text(__import__('json').dumps(state))
        c['body']['source_notes'] = 'Revised measurement plan'
        self.draft = self.root/'draft.json'; write_new(self.draft,c)
        self.lm = self.parent/'landmarks.json'

    def run_replan(self, **kwargs):
        return prepare_replan(self.parent,self.draft,self.lm,reason='Hip patch redesign',destination=kwargs.get('destination',self.root/'new'))

    def snapshot(self):
        return {str(p.relative_to(self.parent)):digest(p) for p in self.parent.rglob('*') if p.is_file()}

    def test_fresh_session_does_not_inherit_gates_or_mutate_parent(self):
        before = self.snapshot(); target = self.run_replan()
        self.assertEqual(before,self.snapshot())
        state = load(target/'state.json')
        self.assertEqual((state['state'],state['status']),('REFERENCES_READY','ACTIVE'))
        self.assertIsNone(state['contract_sha256']); self.assertEqual(state['history'],[])
        self.assertEqual((target/'phase1_working.blend').read_bytes(),b'phase0')
        self.assertEqual(load(target/'replan.json')['parent_hashes']['state.json'],before['state.json'])
        self.assertFalse((target/'model_contract.json').exists())
        validate_contract(load(target/'drafts/model_contract.json'),load(target/'drafts/landmarks.json'),state['sources'],require_head=False)

    def test_tampered_checkpoint_rejected(self):
        (self.parent/'phase1_generation_test.blend').write_bytes(b'changed')
        with self.assertRaises(ReferenceError): self.run_replan()
        self.assertFalse((self.root/'new').exists())

    def test_tampered_contract_rejected(self):
        (self.parent/'model_contract.json').write_text('{}')
        with self.assertRaises(ReferenceError): self.run_replan()

    def test_nested_output_and_active_session_rejected(self):
        with self.assertRaises(ReferenceError): self.run_replan(destination=self.parent/'nested')
        state = load(self.parent/'state.json'); state['status'] = 'ACTIVE'
        (self.parent/'state.json').write_text(__import__('json').dumps(state))
        with self.assertRaises(ReferenceError): self.run_replan()

    def test_failed_draft_write_cleans_new_session_only(self):
        before = self.snapshot()
        with patch('phase1_replan.write_new',side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.run_replan()
        self.assertEqual(before,self.snapshot()); self.assertFalse((self.root/'new').exists())

    def test_topology_finding_halts_without_consuming_position_retry(self):
        state = {'state':'BODY_BLOCKOUT','status':'ACTIVE','history':[],'reworks':{}}
        finding = dict(region='leg_left',severity='error',evidence='oblique_front.png',expected='smooth hip',
                       observed='shelf',suggested_action='replace patch',preserve_regions=[],attempt=1,change_type='topology')
        review = dict(role='Reviewer',reviewer='test',verdict='REWORK',evidence={'x':'hash'},findings=[finding])
        result = transition(state,'BODY_SHAPE_REVIEW',review=review,evidence=review['evidence'])
        self.assertEqual(result['status'],'REPLAN'); self.assertEqual(result['reworks'],{})
        self.assertEqual(state['status'],'ACTIVE')
