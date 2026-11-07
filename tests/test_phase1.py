"""Contract, topology, evidence-gate and source-preservation regression tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase1_geometry import Mesh, loft, body_mesh, head_mesh, mesh_stats, silhouette_metrics, boundary
from phase1_contract import (digest, prepare_session, validate_contract, transition,
                             write_new, verify_sources, VISUAL_CHECKS, STATES)
from reference_common import ReferenceError, VIEWS
from phase1_fixtures import contract, landmarks, rings


class GeometryTests(unittest.TestCase):
    def test_loft_is_single_closed_consistently_wound_surface(self):
        mesh=Mesh(); loft(mesh,rings(),'torso')
        stats=mesh_stats(mesh)
        self.assertEqual(stats['components'],1)
        for k in ('boundary_edges','nonmanifold_edges','inconsistent_winding_edges','duplicate_vertices','isolated_vertices'):
            self.assertEqual(stats[k],0,k)
        self.assertFalse(stats['invalid_faces'])

    def test_body_branches_are_connected_not_overlapping_primitives(self):
        mesh=body_mesh(contract()['body']); stats=mesh_stats(mesh)
        self.assertEqual(stats['components'],1)
        self.assertEqual(stats['boundary_edges'],0)
        self.assertEqual(stats['nonmanifold_edges'],0)
        self.assertEqual(stats['inconsistent_winding_edges'],0)
        self.assertEqual(stats['isolated_vertices'],0)
        self.assertFalse(stats['invalid_faces'])
        self.assertTrue(any('junction' in r for r in mesh.regions))

    def test_head_has_integrated_feature_rims(self):
        mesh=head_mesh(contract()['head']); stats=mesh_stats(mesh)
        self.assertEqual(stats['components'],1)
        self.assertEqual(stats['boundary_edges'],0)
        self.assertEqual(stats['nonmanifold_edges'],0)
        self.assertEqual(stats['inconsistent_winding_edges'],0)
        self.assertFalse(stats['invalid_faces'])
        for feature in ('eye_left','eye_right','mouth','ear_left','ear_right'):
            self.assertIn(feature+':rim',mesh.regions)

    def test_sphere_without_facial_features_rejected(self):
        spec=contract()['head']; spec['features']=[]
        with self.assertRaises(ReferenceError): head_mesh(spec)

    def test_flat_nose_rejected(self):
        spec=contract()['head'];spec['nose_base']=[0,-1,0]
        with self.assertRaises(ReferenceError): head_mesh(spec)

    def test_nonfinite_coordinates_rejected(self):
        spec=contract()['body'];spec['torso'][0][0]=(float('nan'),0,0)
        with self.assertRaises(ReferenceError): body_mesh(spec)

    def test_disconnected_patch_rejected(self):
        with self.assertRaises(ReferenceError): boundary([(0,1,2,3),(4,5,6,7)])

    def test_masks_require_verified_alignment_and_nonempty_foreground(self):
        self.assertEqual(silhouette_metrics([[1]],[[1]])['status'],'UNVERIFIED')
        self.assertEqual(silhouette_metrics([[0]],[[0]],alignment_verified=True)['status'],'UNVERIFIED')
        m=silhouette_metrics([[1,1,0]],[[0,1,1]],alignment_verified=True)
        self.assertAlmostEqual(m['iou'],1/3)
        self.assertEqual((m['missing_pixels'],m['excess_pixels']),(1,1))
        with self.assertRaises(ReferenceError): silhouette_metrics([[1]],[[2]],alignment_verified=True)

    def test_contract_uncertainty_and_sources_are_required(self):
        hashes={v:v for v in VIEWS}; c=contract(); l=landmarks(hashes)
        validate_contract(c,l,hashes)
        l['views']['left']['chin']['confidence']='certain'
        with self.assertRaises(ReferenceError): validate_contract(c,l,hashes)

    def test_contradictions_are_not_averaged_away(self):
        hashes={v:v for v in VIEWS};l=landmarks(hashes)
        l['inconsistencies']=[{'resolved':False,'note':'side depth differs'}]
        with self.assertRaises(ReferenceError): validate_contract(contract(),l,hashes)


class GateTests(unittest.TestCase):
    def state(self):
        return {'state':'BODY_BLOCKOUT','status':'ACTIVE','history':[],'reworks':{}}
    def review(self,verdict='PASS'):
        return {'role':'Reviewer','reviewer':'independent-review-thread','verdict':verdict,
                'evidence':{'candidate.blend':'hash'},'checks':dict.fromkeys(VISUAL_CHECKS,'PASS'),
                'findings':[] if verdict=='PASS' else [{
                    'region':'torso','severity':'error','evidence':'overlay_front.png',
                    'expected':'reference waist','observed':'too wide','suggested_action':'narrow waist',
                    'preserve_regions':['arm_left'],'attempt':1}]}
    def test_cannot_skip_gate(self):
        with self.assertRaises(ReferenceError): transition(self.state(),'PHASE1_COMPLETE')
    def test_pass_requires_visual_evidence(self):
        review=self.review();review['checks']['volume']='UNVERIFIED'
        with self.assertRaises(ReferenceError): transition(self.state(),'BODY_SHAPE_REVIEW',review=review,evidence=review['evidence'])
    def test_stale_evidence_rejected(self):
        review=self.review()
        with self.assertRaises(ReferenceError): transition(self.state(),'BODY_SHAPE_REVIEW',review=review,evidence={'candidate.blend':'other'})
    def test_rework_twice_then_replan(self):
        state=self.state();review=self.review('REWORK')
        for n in range(3):
            state=transition(state,'BODY_SHAPE_REVIEW',review=review,evidence=review['evidence'])
        self.assertEqual(state['state'],'BODY_BLOCKOUT')
        self.assertEqual(state['status'],'REPLAN')
        with self.assertRaises(ReferenceError): transition(state,'BODY_SHAPE_REVIEW',review=self.review(),evidence=review['evidence'])
    def test_blocked_does_not_advance(self):
        review=self.review('BLOCKED')
        state=transition(self.state(),'BODY_SHAPE_REVIEW',review=review,evidence=review['evidence'])
        self.assertEqual(state['status'],'BLOCKED');self.assertEqual(state['state'],'BODY_BLOCKOUT')
    def test_complete_flow_with_review_at_every_gate(self):
        state=self.state();state['state']='REFERENCES_READY'
        for target in STATES[1:]:
            r=self.review()
            state=transition(state,target,review=r,evidence=r['evidence'])
        self.assertEqual(state['state'],'PHASE1_COMPLETE')
        self.assertEqual(len(state['history']),4)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'phase0.blend';self.source.write_bytes(b'original blend')
        self.manifest=self.root/'phase0.manifest.json'
        refs={}
        for v in VIEWS:
            (self.root/(v+'.png')).write_bytes(v.encode())
            refs[v]={'input':{'path':v+'.png'},'packed':True}
        write_new(self.manifest,{'blend_file':self.source.name,'references':refs,
                                'cameras':{v:'CAM_'+v.upper() for v in VIEWS}})
        self.review=self.root/'phase0_review.json'
        self.pass_review={**dict.fromkeys((*VIEWS,'locks','alignment','packed','reopen'),'PASS'),
                          'blend_sha256':digest(self.source),'manifest_sha256':digest(self.manifest)}
        write_new(self.review,self.pass_review)
    def tearDown(self): self.temp.cleanup()
    def prepare(self,destination):
        return prepare_session(self.source,self.manifest,self.review,destination=destination)
    def test_explicit_output_is_exact_and_originals_preserved(self):
        out=self.prepare(self.root/'new')
        self.assertEqual(out,self.root/'new');verify_sources(out)
        self.assertEqual(self.source.read_bytes(),b'original blend')
        self.assertEqual((out/'phase1_working.blend').read_bytes(),b'original blend')
        with self.assertRaises(ReferenceError): self.prepare(out)
        verify_sources(out)
    def test_changed_sources_block(self):
        out=self.prepare(self.root/'new');self.source.write_bytes(b'changed')
        with self.assertRaises(ReferenceError): verify_sources(out)
    def test_stale_phase0_review_blocks_without_output(self):
        self.source.write_bytes(b'changed')
        with self.assertRaises(ReferenceError): self.prepare(self.root/'new')
        self.assertFalse((self.root/'new').exists())
    def test_unverified_phase0_blocks(self):
        self.pass_review['front']='UNVERIFIED';self.review.write_text(json.dumps(self.pass_review))
        with self.assertRaises(ReferenceError): self.prepare(self.root/'new')
    def test_missing_image_blocks(self):
        (self.root/'left.png').unlink()
        with self.assertRaises(ReferenceError): self.prepare(self.root/'new')
    def test_default_output_uses_host_downloads(self):
        with patch('phase1_contract.downloads_directory',return_value=self.root):
            out=prepare_session(self.source,self.manifest,self.review)
        self.assertEqual(out.parent,self.root);self.assertRegex(out.name,r'^char_base_\d{8}_\d{6}$')
    def test_failed_copy_rolls_back_only_new_directory(self):
        with patch('phase1_contract.shutil.copyfile',side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.prepare(self.root/'new')
        self.assertFalse((self.root/'new').exists());self.assertTrue(self.source.exists())
    def test_destination_symlink_is_rejected(self):
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ReferenceError): self.prepare(alias)
