import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import draw_geometry as g,tool_snap


def point(co):return dict(co=co,left=co,right=co)


class DrawingTests(unittest.TestCase):
    def test_curve_samples_preserve_endpoints_and_plane(self):
        a=point((0,0,7));b=point((4,0,7));a['right']=(1,2,7);b['left']=(3,2,7)
        samples=g.sample(a,b,16)
        self.assertEqual(samples[0],a['co']);self.assertEqual(samples[-1],b['co'])
        self.assertTrue(all(abs(p[2]-7)<1e-8 for p in samples))

    def test_straight_corner_segment_stays_on_line(self):
        values=g.sample(point((0,2,0)),point((4,2,0)),12)
        self.assertTrue(all(abs(p[1]-2)<1e-8 and abs(p[2])<1e-8 for p in values))
        self.assertTrue(all(a[0]<b[0] for a,b in zip(values,values[1:])))

    def test_handles_control_curve_interior(self):
        a=point((0,0,0));b=point((4,0,0));a['right']=(1,2,0);b['left']=(3,2,0)
        self.assertAlmostEqual(g.sample(a,b,2)[1][1],1.5)
        a['right']=(1,-2,0);b['left']=(3,-2,0)
        self.assertAlmostEqual(g.sample(a,b,2)[1][1],-1.5)

    def test_closed_face_validation_accepts_concave_but_not_flat_outline(self):
        self.assertTrue(g.simple_polygon([(0,0,0),(3,0,0),(3,3,0),(1,1,0),(0,3,0)],(0,0,1)))
        self.assertFalse(g.simple_polygon([(0,0,0),(1,0,0),(2,0,0)],(0,0,1)))

    def test_self_intersection_rejected(self):
        self.assertFalse(g.simple_polygon([(0,0,0),(2,2,0),(0,2,0),(2,0,0)],(0,0,1)))
        self.assertTrue(g.simple_polygon([(0,0,0),(2,0,0),(2,2,0),(0,2,0)],(0,0,1)))

    def test_native_snap_toggle_ctrl_and_target_are_authoritative(self):
        ts=NS(use_snap=False,use_snap_translate=True,snap_elements={'INCREMENT'})
        context=NS(scene=NS(tool_settings=ts))
        self.assertFalse(tool_snap.enabled(context))
        self.assertTrue(tool_snap.grid_enabled(context,NS(ctrl=True)))
        ts.use_snap=True
        self.assertTrue(tool_snap.grid_enabled(context))
        self.assertFalse(tool_snap.enabled(context,NS(ctrl=True)))
        ts.snap_elements={'VERTEX'}
        self.assertTrue(tool_snap.enabled(context));self.assertFalse(tool_snap.grid_enabled(context))
        ts.use_snap_translate=False
        self.assertFalse(tool_snap.enabled(context))
