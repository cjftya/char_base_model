"""Failure injection at the model/state commit boundary."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from phase1_checkpoint import publish, checkpoint_path, materialize
from phase1_contract import load, write_new, validate_contract
from phase1_regions import capture, resolve
from phase1_fixtures import contract, landmarks
from reference_common import ReferenceError, VIEWS

class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.old={'state':'BODY_BLOCKOUT','status':'ACTIVE'}
        write_new(self.root/'state.json',self.old)
        self.old=publish(self.root,self.old,lambda p:p.write_bytes(b'old model'),expected_state=self.old)
    def test_model_save_failure_preserves_committed_pair(self):
        def fail(p): p.write_bytes(b'partial');raise OSError('save failed')
        with self.assertRaises(OSError): publish(self.root,dict(self.old,state='HEAD_BLOCKOUT'),fail,expected_state=self.old)
        self.assertEqual(load(self.root/'state.json'),self.old)
        self.assertEqual(checkpoint_path(self.root,self.old).read_bytes(),b'old model')
    def test_state_publication_failure_keeps_previous_model(self):
        with patch('phase1_checkpoint.replace_json',side_effect=OSError('state failed')):
            with self.assertRaises(OSError):
                publish(self.root,dict(self.old,state='HEAD_BLOCKOUT'),lambda p:p.write_bytes(b'new'),expected_state=self.old)
        self.assertEqual(load(self.root/'state.json'),self.old)
        self.assertEqual(materialize(self.root,self.old).read_bytes(),b'old model')
    def test_success_selects_new_model_and_state_together(self):
        new=publish(self.root,dict(self.old,state='HEAD_BLOCKOUT'),lambda p:p.write_bytes(b'new'),expected_state=self.old)
        self.assertEqual(load(self.root/'state.json'),new)
        self.assertEqual(materialize(self.root,new).read_bytes(),b'new')
    def test_corrupt_checkpoint_blocks_recovery(self):
        checkpoint_path(self.root,self.old).write_bytes(b'corrupt')
        with self.assertRaises(ReferenceError): materialize(self.root,self.old)
    def test_uncommitted_final_cannot_materialize(self):
        with self.assertRaises(ReferenceError): materialize(self.root,self.old,'phase1_final.blend')
    def test_stale_writer_cannot_commit(self):
        with self.assertRaises(ReferenceError): publish(self.root,self.old,lambda p:p.write_bytes(b'new'),expected_state={})
    def test_derived_failure_does_not_undo_commit(self):
        new=publish(self.root,dict(self.old,state='PHASE1_COMPLETE'),lambda p:p.write_bytes(b'final'),expected_state=self.old)
        with patch('phase1_checkpoint.shutil.copyfile',side_effect=OSError('copy failed')):
            with self.assertRaises(OSError): materialize(self.root,new,'phase1_final.blend')
        self.assertEqual(load(self.root/'state.json'),new)
        self.assertEqual(materialize(self.root,new,'phase1_final.blend').read_bytes(),b'final')

class StagedContractTests(unittest.TestCase):
    def test_body_contract_does_not_require_detailed_head(self):
        c=contract();del c['head'];hashes={v:v for v in VIEWS}
        validate_contract(c,landmarks(hashes),hashes,require_head=False)
        with self.assertRaises(ReferenceError): validate_contract(c,landmarks(hashes),hashes)
    def test_face_reorder_and_winding_preserve_regions(self):
        mapping=capture([(0,1,2),(2,3,0)],['nose','skull'])
        self.assertEqual(resolve([(0,3,2),(2,1,0)],mapping),['skull','nose'])
    def test_same_count_topology_change_is_detected(self):
        mapping=capture([(0,1,2)],['nose'])
        with self.assertRaises(ReferenceError): resolve([(0,1,3)],mapping)

class WriterLockTests(unittest.TestCase):
    def test_second_writer_is_blocked(self):
        from phase1_checkpoint import writer_lock
        with tempfile.TemporaryDirectory() as d:
            with writer_lock(d):
                with self.assertRaises(ReferenceError):
                    with writer_lock(d): pass
            self.assertFalse((Path(d)/'.checkpoint.lock').exists())
