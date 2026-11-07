"""Narrow Blender adapter safety tests; not a replacement for Blender execution."""
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase1_analysis import pixel_to_world, landmark_errors
from reference_common import ReferenceError, ReferenceView


class RuntimeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.bpy=SimpleNamespace(ops=SimpleNamespace(wm=SimpleNamespace(save_as_mainfile=Mock())))
        with patch.dict(sys.modules,{'bpy':self.bpy,'bmesh':SimpleNamespace(),
                    'mathutils':SimpleNamespace(Vector=Mock()),
                    'bpy_extras':SimpleNamespace(),
                    'bpy_extras.object_utils':SimpleNamespace(world_to_camera_view=Mock())}):
            self.api=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/phase1_blender.py'))
    def test_save_stages_sibling_to_keep_relative_assets_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            final=Path(directory)/'candidate.blend'
            def save(**kwargs):
                staged=Path(kwargs['filepath'])
                self.assertEqual(staged.parent,final.parent)
                self.assertTrue(kwargs['copy']);self.assertTrue(kwargs['relative_remap'])
                staged.write_bytes(b'blender saved copy')
                return {'FINISHED'}
            self.bpy.ops.wm.save_as_mainfile.side_effect=save
            self.api['save_copy'](final)
            self.assertEqual(final.read_bytes(),b'blender saved copy')
            self.assertEqual(list(Path(directory).iterdir()),[final])
            with self.assertRaises(ReferenceError): self.api['save_copy'](final)
    def test_failed_save_removes_only_staged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            def save(**kwargs):
                Path(kwargs['filepath']).write_bytes(b'partial')
                return {'CANCELLED'}
            self.bpy.ops.wm.save_as_mainfile.side_effect=save
            with self.assertRaises(ReferenceError): self.api['save_copy'](Path(directory)/'final.blend')
            self.assertEqual(list(Path(directory).iterdir()),[])
    def test_working_update_keeps_relative_directory_and_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);(folder/'phase1_working.blend').write_bytes(b'old')
            (folder/'phase0.blend').write_bytes(b'protected')
            def save(path):
                self.assertEqual(path.parent,folder)
                path.write_bytes(b'new')
            method=self.api['save_working']
            with patch.dict(method.__globals__,{'save_copy':save}): method(folder)
            self.assertEqual((folder/'phase1_working.blend').read_bytes(),b'new')
            self.assertEqual((folder/'phase0.blend').read_bytes(),b'protected')
    def test_pixel_conversion_respects_each_view_direction(self):
        for name,expected in [('front',[.5,0,1]),('back',[-.5,0,1]),
                              ('left',[0,-.5,1]),('right',[0,.5,1])]:
            view=ReferenceView(name,Path('/ref.png'),100,200,0,1,.5,2,4,0,0)
            self.assertEqual(pixel_to_world(view,75,150),expected)
    def test_landmark_error_does_not_merge_contradictions(self):
        errors=landmark_errors({'front':{'chin':[0,0,1]},'left':{'chin':[0,0,2]}},{'chin':[0,0,1]})
        self.assertEqual(errors,{'front':{'chin':0},'left':{'chin':1}})
