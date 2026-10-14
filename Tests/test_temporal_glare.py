import math,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"Source"))
import numpy as np
from temporal_glare_audit import paper_factor,aurora,glaze_f0,water_normal

class TemporalGlare(unittest.TestCase):
 def test_paper_selected_and_extreme_ranges(self):
  t=np.linspace(-1000,100000,100001)
  for b in (-1,0,.012,.03,1):
   x=paper_factor(t,b);self.assertTrue(np.isfinite(x).all());self.assertGreaterEqual(x.min(),.97-1e-12);self.assertLessEqual(x.max(),1.03+1e-12)
 def test_paper_repeat_and_no_resets(self):
  t=np.linspace(0,1000,1001)
  self.assertLess(np.max(np.abs(paper_factor(t)-paper_factor(t+math.tau/.31))),1e-12)
 def test_aurora_long_common_phase_repeat(self):
  # 0.61 drift ratio:100 primary cycles and61 secondary cycles.
  period=math.tau*100/.012
  for angle in np.linspace(-math.pi,math.pi,15):
   for y in (.45,.5,.55):self.assertAlmostEqual(float(aurora(angle,y,123)),float(aurora(angle,y,123+period)),places=11)
 def test_float32_time_is_finite_and_small_step_through_24h(self):
  for start in (0,3600,36000,86400):
   t=np.asarray(start+np.arange(1801)/90,dtype=np.float32)
   self.assertLess(np.max(np.abs(np.diff(paper_factor(t)))),.0001)
   for angle in np.linspace(-math.pi,math.pi,15):self.assertLess(np.max(np.abs(np.diff(aurora(angle,.5,t))))*.12,.00004)
 def test_water_long_wave_repeat_and_no_growth(self):
  # Wave frequencies .4,.28,.07,.05 share common period2pi/.01.
  # Texture scrolling has a different period; no whole-water-loop claim.
  for x,y in ((0,0),(-6300,-7100),(6300,-8000)):
   a=water_normal(x,y,np.linspace(0,600,1001));b=water_normal(x,y,np.linspace(0,600,1001)+math.tau/.01)
   self.assertLess(np.abs(a-b).max(),1e-12)
   self.assertTrue(np.isfinite(a).all());self.assertGreater(a[:,2].min(),.9999)
 def test_water_float32_time_through_24h(self):
  for start in (0,36000,86400):
   t=np.asarray(start+np.arange(1801)/90,dtype=np.float32)
   for x,y in ((0,0),(-6300,-7100),(6300,-8000)):
    n=water_normal(x,y,t);self.assertTrue(np.isfinite(n).all());self.assertLess(np.linalg.norm(np.diff(n,axis=0),axis=1).max(),.0002)
 def test_glaze_extremes_stay_finite_bounded(self):
  ndv=np.linspace(0,1,1001)
  for metal in (0,.12,.5,1):
   for strength in (0,.18,.25):
    for color in ([0,0,0],[1,1,1],[.045,.15,.075]):
     x=glaze_f0(color,metal,ndv,strength);self.assertTrue(np.isfinite(x).all());self.assertGreaterEqual(x.min(),0);self.assertLessEqual(x.max(),1)
 def test_glaze_film_continuity_and_selected_dielectric_bound(self):
  x=glaze_f0([.64,.71,.67],0,np.linspace(0,1,10001))
  self.assertGreaterEqual(x.min(),.04*(1-.072)-1e-12);self.assertLessEqual(x.max(),.04*(1+.072)+1e-12)
  self.assertLess(np.max(np.abs(np.diff(x,axis=0))),.000004)
 def test_surface_craft_bounds_without_changing_colour(self):
  for grain in (0,.5,1):
   for ao in (0,.5,1):
    for rough in (0,.5,1):
     for metal in (0,.5,1):
      pat=(1-ao)*.35;before=1-rough;after=np.clip(before+(grain-.5)*.25-pat*.25,0,1)
      self.assertGreaterEqual(after,0);self.assertLessEqual(after,1)
      self.assertGreaterEqual(metal*(1-pat),0);self.assertLessEqual(metal*(1-pat),metal)
if __name__=='__main__':unittest.main()
