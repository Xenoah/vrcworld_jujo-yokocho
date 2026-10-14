import importlib.util,math,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('candidate',HERE/'Source/fantasy_preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def height(x,y,t,slope):
    wa=(-.6*x+.8*y)*.021+t*.07;wb=(.8*x+.6*y)*.017-t*.05
    pa=(.8*x+.6*y)*.13+t*.4+1.1*math.sin(wa)
    pb=(-.6*x+.8*y)*.19-t*.28+.8*math.sin(wb)
    return slope*(.65/.13*math.sin(pa)+.35/.19*math.sin(pb))
class WarpedWater(unittest.TestCase):
    def test_gradients_match_finite_difference(self):
        for x,y,t in [(0,0,0),(-3200,-6500,12),(130,-800,63),(5000,-7900,1200)]:
            h=.001;n=m.analytic_water_normal(x,y,t,slope=.01)
            dx=(height(x+h,y,t,.01)-height(x-h,y,t,.01))/(2*h)
            dy=(height(x,y+h,t,.01)-height(x,y-h,t,.01))/(2*h)
            self.assertAlmostEqual(-n[0]/n[2],dx,places=8)
            self.assertAlmostEqual(-n[1]/n[2],dy,places=8)
    def test_inverse_rotation_preserves_unit_and_direction(self):
        for angle in range(0,360,7):
            x,y=math.cos(math.radians(angle)),math.sin(math.radians(angle))
            u,v=.8*x-.6*y,.6*x+.8*y
            self.assertAlmostEqual(.8*u+.6*v,x,places=12)
            self.assertAlmostEqual(-.6*u+.8*v,y,places=12)
    def test_same_fetch_count_and_static_vertices(self):
        s=(HERE/'Assets/TreeTopYokocho/Shaders/YokochoWater.shader').read_text()
        self.assertEqual(s.count('tex2D('),3)
        self.assertIn('YOKOCHO_STATIC_PLANAR_SEA',s)
        self.assertNotRegex(s,r'\bvertex\s*:')
        self.assertNotRegex(s,r'\.vertex\s*[+*/-]?=')
        self.assertIn('fwidth(phase)',s)
        self.assertIn('bWorld',s)
    def test_wave_slope_bound(self):
        bound=.65*math.sqrt(1+(.021*1.1/.13)**2)+.35*math.sqrt(1+(.017*.8/.19)**2)
        self.assertLess(bound,1.012)
        for i in range(1000):
            n=m.analytic_water_normal(i*17.3,-i*9.77,i*.33,slope=.014)
            self.assertLessEqual(math.hypot(n[0]/n[2],n[1]/n[2]),bound*.014+1e-12)
if __name__=='__main__':unittest.main()
