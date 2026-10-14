import itertools,unittest
from surface_craft_preview import craft_response
class SurfaceFormula(unittest.TestCase):
 def test_extremes_match_shader_composition(self):
  sat=lambda v:min(1.,max(0.,v))
  for rough,metal,grain,ao,strength,pat in itertools.product((-.1,0,.5,1,1.1),(0,.5,1),(0,.5,1),(0,.5,1),(0,.025,.11,.25),(0,.18,.35)):
   s0=sat(1-rough);p=sat(1-ao)*min(.35,max(0,pat))
   expected_s=sat(s0+(grain-.5)*min(.25,max(0,strength))-.25*p)
   r,m=craft_response(rough,metal,grain,ao,strength,pat)
   self.assertAlmostEqual(1-r,expected_s,places=12);self.assertAlmostEqual(m,sat(metal)*(1-p),places=12)
 def test_off_is_identity_for_valid_inputs(self):
  for r,m in itertools.product((0,.2,.5,1),(0,.2,.5,1)):
   result=craft_response(r,m,.9,0,0,0)
   self.assertAlmostEqual(result[0],r);self.assertAlmostEqual(result[1],m)
 def test_ao_only_drives_patina(self):
  for ao in (0,.5,1):self.assertEqual(craft_response(.5,.8,.2,ao,.11,0),craft_response(.5,.8,.2,1,.11,0))
 def test_no_arm_patina_has_no_effect(self):
  for strength in (0,.18,.35):self.assertEqual(craft_response(.5,.8,.2,1,.025,strength),craft_response(.5,.8,.2,1,.025,0))
if __name__=='__main__':unittest.main()
