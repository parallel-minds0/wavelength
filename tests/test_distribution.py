import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import distribution as scatter


class DistributionTests(unittest.TestCase):
    def test_density_preserves_survivor_positions(self):
        dense={v[0]:v for v in scatter.candidates((-10,-10,10,10),4,.7,93)}
        sparse={v[0]:v for v in scatter.candidates((-10,-10,10,10),4,.12,93)}
        self.assertTrue(sparse)
        self.assertLess(len(sparse),len(dense))
        self.assertTrue(all(dense[key]==value for key,value in sparse.items()))

    def test_adjacent_bounds_do_not_duplicate_candidates(self):
        full=list(scatter.candidates((-10,-10,10,10),4,.2,10))
        split=list(scatter.candidates((-10,-10,0,10),4,.2,10))+list(scatter.candidates((0,-10,10,10),4,.2,10))
        self.assertEqual(sorted(full),sorted(split))

    def test_seed_and_palette_validation(self):
        self.assertNotEqual(list(scatter.candidates((0,0,10,10),2,.5,1)),
                            list(scatter.candidates((0,0,10,10),2,.5,2)))
        self.assertEqual(scatter.choose(2,'a',[0,1,0]),1)
        for weights in ([],[0,0],[-1,1],[math.nan]):
            with self.assertRaises(ValueError):scatter.choose(2,'a',weights)
        with self.assertRaises(ValueError):list(scatter.candidates((0,0,1,1),0,1,1))
        with self.assertRaises(ValueError):list(scatter.candidates((0,0,math.inf,1),1,1,1))


if __name__=='__main__':unittest.main()
