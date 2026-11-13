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
    def test_scene_counts_evaluated_triangles_and_frees_temporary_mesh(self):
        class Matrix:
            def __matmul__(self, value): return value
        def data(n):
            return SimpleNamespace(vertices=[SimpleNamespace(co=(0,0,0)),
                SimpleNamespace(co=(1,0,0)), SimpleNamespace(co=(0,1,0))],
                polygons=[SimpleNamespace(vertices=(0,1,2))], edges=[0,1,2],
                loop_triangles=list(range(n)), calc_loop_triangles=Mock(),
                materials=[], shape_keys=None)
        original, temporary = data(1), data(8)
        evaluated = SimpleNamespace(to_mesh=Mock(return_value=temporary), to_mesh_clear=Mock())
        obj = SimpleNamespace(type='MESH', name='P1_BODY', data=original,
            matrix_world=Matrix(), evaluated_get=Mock(return_value=evaluated),
            modifiers=[], constraints=[], animation_data=None, hide_render=False,
            hide_viewport=False, scale=(1,1,1), location=(0,0,0))
        class Object(SimpleNamespace):
            def __contains__(self, key): return False
        obj = Object(**vars(obj))
        bm = SimpleNamespace(from_mesh=Mock(), verts=[], calc_volume=Mock(return_value=1), free=Mock())
        method = self.api['validate_scene']
        with patch.dict(method.__globals__, {'owned_objects': lambda: [obj],
                'bpy': SimpleNamespace(context=SimpleNamespace(evaluated_depsgraph_get=Mock())),
                'bmesh': SimpleNamespace(new=lambda: bm)}):
            result = method()['P1_BODY']
            self.assertEqual(result['original']['triangles'], 1)
            self.assertEqual(result['evaluated']['triangles'], 8)
            evaluated.to_mesh_clear.assert_called_once()
            temporary.calc_loop_triangles.side_effect = RuntimeError('tessellation failed')
            with self.assertRaises(RuntimeError): method()
            self.assertEqual(evaluated.to_mesh_clear.call_count, 2)

    def test_current_junction_and_region_metrics_survive_blender_adapter(self):
        import json
        from phase1_fixtures import contract
        from phase1_geometry import body_mesh
        from phase1_regions import capture
        geometry = body_mesh(contract()['body'])
        class Matrix:
            def __matmul__(self, value): return value
        class Object(SimpleNamespace):
            def __contains__(self, key): return key in self.props
            def __getitem__(self, key): return self.props[key]
        data = SimpleNamespace(vertices=[SimpleNamespace(co=p) for p in geometry.vertices],
            polygons=[SimpleNamespace(vertices=f) for f in geometry.faces],
            edges=[], loop_triangles=[SimpleNamespace(polygon_index=i,vertices=(f[0],f[j],f[j+1]))
                for i,f in enumerate(geometry.faces) for j in range(1,len(f)-1)],
            calc_loop_triangles=Mock(),materials=[],shape_keys=None)
        evaluated = SimpleNamespace(to_mesh=Mock(return_value=data),to_mesh_clear=Mock())
        obj = Object(type='MESH',name='P1_BODY',data=data,matrix_world=Matrix(),
            evaluated_get=Mock(return_value=evaluated),modifiers=[],constraints=[],animation_data=None,
            hide_render=False,hide_viewport=False,scale=(1,1,1),location=(0,0,0),props={
                'semantic_face_map':json.dumps(capture(geometry.faces,geometry.regions)),
                'semantic_face_order':json.dumps(geometry.faces),
                'junction_plan':json.dumps(geometry.junctions)})
        bm = SimpleNamespace(from_mesh=Mock(),verts=[],calc_volume=Mock(return_value=1),free=Mock())
        method = self.api['validate_scene']
        with patch.dict(method.__globals__,{'owned_objects':lambda:[obj],
                'bpy':SimpleNamespace(context=SimpleNamespace(evaluated_depsgraph_get=Mock())),
                'bmesh':SimpleNamespace(new=lambda:bm)}):
            result = method()['P1_BODY']
            self.assertEqual(len(result['junctions']),4)
            self.assertEqual(len(result['planned_junctions']),4)
            self.assertEqual(sum(result['region_triangles'].values()),len(data.loop_triangles))
            self.assertAlmostEqual(sum(v['triangle_share'] for v in result['region_density'].values()),1)
            face = next(f for f,r in zip(geometry.faces,geometry.regions) if r.endswith(':junction'))
            data.vertices[face[3]].co = data.vertices[face[0]].co
            changed = method()['P1_BODY']
            self.assertTrue(any(j['collapsed_bridge'] for j in changed['junctions']))
            self.assertFalse(any(j['collapsed_bridge'] for j in changed['planned_junctions']))

    def test_reviewer_pass_cannot_bypass_total_budget(self):
        from phase1_budget import policy, summarize
        session = Path('/session')
        counts = dict(vertices=10, edges=20, faces=5, triangles=policy()['max_total_triangles']+1)
        meshes = {'P1_BODY': dict(original=counts, evaluated=counts, render_evaluation_verified=True)}
        payload = {'meshes': meshes, 'polygon_budget': summarize(meshes, policy())}
        def load(path):
            if Path(path).name == 'metrics.json': return payload
            if Path(path).name == 'model_contract.json': return {}
            return {'verdict': 'PASS'}
        commit = Mock()
        method = self.api['submit_review']
        with patch.dict(method.__globals__, {'context': lambda _: (session, {'state':'BODY_BLOCKOUT'}),
                'validate_evidence': lambda *_: {}, 'validate_scene': lambda: meshes,
                'load': load, 'commit_model': commit}):
            with self.assertRaisesRegex(ReferenceError, 'budget blocks acceptance'):
                method(session, session/'review/attempt_000', session/'review.json')
            commit.assert_not_called()
            payload['polygon_budget']['policy']['max_total_triangles'] += 10
            with self.assertRaisesRegex(ReferenceError, 'policy changed'):
                method(session, session/'review/attempt_000', session/'review.json')
            commit.assert_not_called()

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

