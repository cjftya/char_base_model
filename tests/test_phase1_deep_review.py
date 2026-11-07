"""Adversarial review and interrupted-publication regression cases."""
import copy
from pathlib import Path
import tempfile
import unittest
from phase1_contract import write_new, ensure_json, digest, validate_contract
from phase1_evidence import REQUIRED, review_context, validate_evidence
from phase1_geometry import boundary, head_mesh
from phase1_fixtures import contract, landmarks
from phase1_workflow import transition, VISUAL_CHECKS
from reference_common import ReferenceError, VIEWS

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.state = dict(state='BODY_BLOCKOUT', history=[], contract_sha256='contract', landmarks_sha256='landmarks')
        for name in REQUIRED:
            (self.folder/name).write_bytes(b'evidence')
        (self.folder/'review_context.json').unlink()
        write_new(self.folder/'review_context.json', review_context(self.state))
        self.binding = {name: digest(self.folder/name) for name in REQUIRED}
        self.binding.update(contract_sha256='contract', landmarks_sha256='landmarks')
    def publish(self):
        write_new(self.folder/'evidence.json', self.binding)
    def test_current_complete_attempt(self):
        self.publish()
        self.assertEqual(validate_evidence(self.folder,self.state),self.binding)
    def test_missing_oblique_cannot_be_omitted_from_binding(self):
        del self.binding['oblique_back.png'];self.publish()
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)
    def test_previous_stage_same_geometry_rejected(self):
        self.publish();self.state['state']='HEAD_BLOCKOUT'
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)
    def test_previous_rework_same_geometry_rejected(self):
        self.publish();self.state['history'].append({'verdict':'REWORK'})
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)
    def test_tampered_image_rejected(self):
        self.publish();(self.folder/'front.png').write_bytes(b'changed')
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)
    def test_landmark_binding_required(self):
        del self.binding['landmarks_sha256'];self.publish()
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)
    def test_cross_platform_traversal_rejected(self):
        self.binding['..\\outside']='hash';self.publish()
        with self.assertRaises(ReferenceError): validate_evidence(self.folder,self.state)

class ContractFailureTests(unittest.TestCase):
    def test_invalid_serialization_does_not_create_immutable_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'new.json'
            with self.assertRaises(ValueError): write_new(p, {'x':float('nan')})
            self.assertFalse(p.exists())
    def test_identical_immutable_retry_succeeds_but_different_content_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'new.json'
            ensure_json(p,{'x':1});ensure_json(p,{'x':1})
            with self.assertRaises(ReferenceError): ensure_json(p,{'x':2})
    def test_infinite_workspace_rejected(self):
        c=contract();c['head']['bounds'][0][0]=-float('inf')
        hashes={v:v for v in VIEWS}
        with self.assertRaises(ReferenceError): validate_contract(c,landmarks(hashes),hashes)
    def test_repeated_nose_index_rejected(self):
        c=contract()['head'];c['nose_vertices']=[12,12,12]
        with self.assertRaises(ReferenceError): head_mesh(c)
    def test_disk_plus_closed_component_rejected(self):
        with self.assertRaises(ReferenceError):
            boundary([(0,1,2,3),(4,6,5),(4,5,7),(5,6,7),(6,4,7)])
    def test_unknown_severity_cannot_hide_error_in_pass(self):
        state=dict(state='BODY_BLOCKOUT',status='ACTIVE',history=[],reworks={})
        finding=dict(region='torso',severity='ERROR',evidence='front',expected='narrow',observed='wide',
                     suggested_action='fix',preserve_regions=[],attempt=1)
        review=dict(role='Reviewer',reviewer='reviewer',verdict='PASS',evidence={'file':'hash'},
                    checks=dict.fromkeys(VISUAL_CHECKS,'PASS'),findings=[finding])
        with self.assertRaises(ReferenceError):
            transition(state,'BODY_SHAPE_REVIEW',review=review,evidence=review['evidence'])
