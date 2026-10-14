import json,math,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]

def ribbon(angle,y,t,height=.5,width=24,speed=.012):
    drift=t*min(.025,max(0,speed))
    wave=math.sin(angle*3+drift)*.032+math.sin(angle*7-drift*.61)*.015
    band=math.exp(-abs(y-height-wave)*width)
    ribs=.66+.34*math.sin(angle*31+math.sin(angle*5)*2+drift)
    return band*ribs
class AuroraBounds(unittest.TestCase):
    def test_longitude_periodic(self):
        for t in (0,1,100,3600):
            for y in (.15,.5,.65):self.assertAlmostEqual(ribbon(-math.pi,y,t),ribbon(math.pi,y,t),places=12)
    def test_no_brightness_excursions(self):
        for t in range(0,720,13):
            for i in range(81):
                v=ribbon(i/80*math.tau,.5,t)
                self.assertGreaterEqual(v,0)
                self.assertLessEqual(v,1)
    def test_slow_temporal_change(self):
        # Global Lipschitz bound: derivative of exp(-abs)*ribs, including cusp.
        speed=.012;width=24
        bound=width*(.032+.015*.61)*speed+.34*speed
        self.assertLess(bound,.016)
        for t in range(0,720,17):
            for i in range(61):
                a=i/60*math.tau
                self.assertLessEqual(abs(ribbon(a,.5,t+1/90)-ribbon(a,.5,t)),bound/90+1e-12)
    def test_profile_within_shader_controls(self):
        p=json.loads((HERE/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text());f={v['name']:v['value'] for v in p['sky']['floats']};v={x['name']:x['value'] for x in p['sky']['vectors']}
        self.assertLessEqual(f['_AuroraStrength'],.15)
        self.assertTrue(.15<=f['_AuroraHeight']<=.65)
        self.assertTrue(16<=f['_AuroraWidth']<=60)
        self.assertTrue(all(0<=c<=1 for c in v['_AuroraColor']))
        self.assertLessEqual(f['_AuroraStrength']*max(v['_AuroraColor']),.12+1e-12)
if __name__=='__main__':unittest.main()
