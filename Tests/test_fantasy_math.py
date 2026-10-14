"""Numerical guards on resolved analytic math, not shader/render verification."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fantasy_preview',ROOT/'Source/fantasy_preview.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FantasyMath(unittest.TestCase):
    def test_analytic_normal_is_unit_and_upward(self):
        for t in (0,1,12.5,30,120,3600):
            for x,y in ((0,0),(-6300,-7100),(6300,-8000),(42,-333),(-.0001,.0001)):
                n=m.analytic_water_normal(x,y,t)
                self.assertAlmostEqual(sum(v*v for v in n),1,places=12)
                self.assertGreater(n[2],.9996)

    def test_removed_displacement_global_bound(self):
        maximum=0
        for t in range(0,300,3):
            for x in range(-6300,6301,210):
                d=m.old_water_displacement(x,-3456,t)
                self.assertLessEqual(abs(d),.043+1e-12)
                maximum=max(maximum,abs(d))
        self.assertGreater(maximum,.042)

    def test_tangent_frame_handles_mirrors(self):
        w=m.analytic_water_normal(140,-930,13)
        for angle in (0,.1,1,2,3):
            for sign in (-1,1):
                t=(math.cos(angle),math.sin(angle),0)
                b=(-math.sin(angle)*sign,math.cos(angle)*sign,0)
                n=(0,0,1)
                local=[sum(a*c for a,c in zip(w,v)) for v in (t,b,n)]
                world=[sum(local[j]*(t,b,n)[j][i] for j in range(3)) for i in range(3)]
                for a,c in zip(w,world):self.assertAlmostEqual(a,c,places=12)

    def test_normal_does_not_depend_on_mesh_vertices_or_uv(self):
        # Fragment world position drives normal; changing topology or UV does
        # not enter analytic evaluation, including across sector boundaries.
        for x in (-3150,0,3150):
            left=m.analytic_water_normal(x-1e-8,-3500,5)
            right=m.analytic_water_normal(x+1e-8,-3500,5)
            self.assertLess(max(abs(a-b) for a,b in zip(left,right)),1e-8)

if __name__=='__main__':unittest.main()
