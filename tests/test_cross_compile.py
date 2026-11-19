import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import cross_compile as cross


class CrossCompileTests(unittest.TestCase):
    def test_spawn_properties_and_review(self):
        pairs=[('classname','info_player_terrorist'),('targetname','spawn'),('priority','2'),('StartDisabled','1'),('unknown','keep-in-report')]
        result=cross.convert_entity('source_hl2_windows','source2_cs2_windows',pairs)
        self.assertEqual(result['status'],'converted')
        self.assertEqual(result['properties']['enabled'],'0')
        self.assertNotIn('unknown',result['properties'])
        self.assertEqual(result['source_pairs'],pairs)
        self.assertTrue(result['warnings'])

    def test_brush_mapping_and_io_stub(self):
        result=cross.source1_to_source2([('classname','func_buyzone'),('TeamNum','3')],'brush')
        self.assertEqual(result['properties']['TeamNum'],'3')
        io=cross.source1_to_source2([('classname','info_target'),('__vmf_output__OnUser1','a,b,,0,-1')])
        self.assertEqual(io['status'],'manual')

    def test_unknown_entity_and_backend_stubs(self):
        result=cross.source1_to_source2([('classname','prop_static'),('model','models/a.mdl')])
        self.assertEqual(result['status'],'manual')
        self.assertEqual(dict(result['source_pairs'])['model'],'models/a.mdl')
        self.assertEqual(cross.convert_entity('goldsrc','godot4',[('classname','test')])['status'],'stub')
        with self.assertRaisesRegex(ValueError,'stub'):
            cross.compile_level(None,'never-written','goldsrc','source2_cs2_windows')

    def test_detail_geometry_has_explicit_nonstructural_mapping(self):
        detail=cross.source1_to_source2([('classname','func_detail')],'brush')
        self.assertEqual(detail['status'],'converted')
        self.assertEqual(detail['geometry_mode'],'detail')
        self.assertTrue(detail['warnings'])
        door=cross.source1_to_source2([('classname','func_door')],'brush')
        self.assertEqual(door['status'],'manual')
        self.assertNotIn('geometry_mode',door)
        io=cross.source1_to_source2([('classname','func_detail'),('__vmf_output__OnUser1','a,b,,0,-1')],'brush')
        self.assertEqual(io['status'],'manual')

    def test_backend_registration_dispatch(self):
        key=('goldsrc','source2');previous=cross.LEVEL_BACKENDS.get(key)
        try:
            cross.register_backend(*key,level=lambda context,path,source,target,**options:(path,options))
            result=cross.compile_level(None,'example.vmap','goldsrc','source2_cs2_windows',selected=True)
            self.assertEqual(result,('example.vmap',{'selected':True}))
        finally:cross.LEVEL_BACKENDS[key]=previous


if __name__=='__main__':unittest.main()
