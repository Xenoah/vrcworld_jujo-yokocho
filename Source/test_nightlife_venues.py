"""Isolated design, geometry and radius-clearance tests; not a VR runtime test."""
import unittest,math,json,hashlib,random,copy
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from nightlife_venues import *
from world_geometry import Geometry
ROOT=Path(__file__).resolve().parent.parent
FIXTURE=Path(__file__).resolve().parent/'testdata/nightlife_legacy_baseline.json'
MANIFEST=json.loads(FIXTURE.read_text())
M0=dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',wall='Plaster',tile='Kawara',window='WarmWindow',iron='Iron',ceramic='Ceramic',food='Food',tea='Tea',sweet='MatchaSweets')
def make(idx,rotation=0):
 g=Geometry();g.materials={m['name']:m.copy() for m in MANIFEST['materials']};g.group=f'Shops/S{idx+1:02d}'
 M=M0.copy()
 for desc in material_specs():
  a=desc.copy();key=a.pop('key');name=a.pop('name');col=a.pop('color');tex=a.pop('texture','');rough=a.pop('roughness',.8);em=a.pop('emission',0);M[key]=g.material(name,col,tex,em,rough,**a)
 def P(x,y,z):return np.array([x*math.cos(rotation)-y*math.sin(rotation),x*math.sin(rotation)+y*math.cos(rotation),z])
 def B(*a,**kw):raise AssertionError('Must not call delegated collision writer')
 r=build_venue(g,P,B,6,5.4,idx,M,seat_specs=[dict(id=f'S{idx+1:02d}_Seat_{i+1}') for i in range(6)],lantern=None)
 return g,r

def footprint(s):
 x,y,z=s['center'];w,d,h=s['size']
 return translate(rotate(box(-w/2,-d/2,w/2,d/2),s['yaw'],origin=(0,0)),x,y)

def clearance(r,radius=.25,chairs=True):
 polys=[footprint(s) for s in r['solids'] if s['center'][2]-s['size'][2]/2 <1.65 and s['center'][2]+s['size'][2]/2>.1]
 if chairs:
  for seat in r['seatOverrides']:
   f=seat['footprint'];w,d=f['size'];polys.append(translate(rotate(box(-w/2,-d/2,w/2,d/2),math.degrees(f['angle']),origin=(0,0)),*f['center']))
 blocked=unary_union(polys);free=box(-3.48,-2.78,3.48,4.16).difference(blocked).buffer(-radius)
 parts=list(free.geoms) if free.geom_type=='MultiPolygon' else [free]
 memberships={s['id']:[i for i,p in enumerate(parts) if p.buffer(.0001).covers(Point(*s['exit'][:2]))] for s in r['seatOverrides']}
 connected=bool(set.intersection(*(set(x) for x in memberships.values())))
 violations=[]
 for route in r['routes']:
  line=LineString([p[:2] for p in route['points']]);area=line.buffer(radius).intersection(blocked).area
  if area>1e-6:violations.append(dict(name=route['name'],overlap=area))
 return dict(radius=radius,seatExitsConnected=connected,memberships=memberships,routeViolations=violations)

class NightlifeTests(unittest.TestCase):
 def test_baseline_fixture_exact(self):
  self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),'23d1533dd07e6d75c53955bf67b8eb9de9b922cd5893f92280ab1f915cbaf599')
 def test_scope(self):
  for idx in [0,1,2,4,7]:
   with self.assertRaises(ValueError):make(idx)
 def test_api_and_seats(self):
  for idx in IDS:
   g,r=make(idx);self.assertEqual(g.group,'Shops/'+IDS[idx]);self.assertEqual(len(r['seatOverrides']),6)
   self.assertEqual([s['id'] for s in r['seatOverrides']],[f'{IDS[idx]}_Seat_{i}' for i in range(1,7)])
   for s in r['seatOverrides']:
    self.assertAlmostEqual(s['position'][2],s['cushionTop']);self.assertAlmostEqual(np.linalg.norm(s['forward']),1)
   for group,mat in g.batches:self.assertTrue(group.startswith('Shops/'+IDS[idx]+'/Personality/'));self.assertIn(mat,g.materials)
   self.assertFalse(r['testedInUnity']);self.assertFalse(r['testedInVRChat'])
 def test_finite_geometry_and_bounds(self):
  for idx in IDS:
   g,r=make(idx)
   for b in g.batches.values():
    v=np.asarray(b['v']);f=np.asarray(b['f']);u=np.asarray(b['uv']);self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(u).all());self.assertLess(f.max(),len(v));self.assertEqual(len(v),len(u))
    self.assertLessEqual(abs(v[:,0]).max(),3.77);self.assertLessEqual(abs(v[:,1]).max(),3.61);self.assertLessEqual(v[:,2].max(),4.05);self.assertGreaterEqual(v[:,2].min(),-.46)
 def test_deterministic(self):
  for idx in IDS:
   a,r=make(idx);b,s=make(idx);self.assertEqual(r,s)
   for key in a.batches:
    for field in ['v','f','uv']:np.testing.assert_array_equal(a.batches[key][field],b.batches[key][field])
 def test_actual_cushion_contact_heights(self):
  for idx in IDS:
   g,r=make(idx)
   triangles=np.concatenate([np.asarray(b['v'])[np.asarray(b['f'])] for (group,mat),b in g.batches.items() if '/Seating/' in group])
   for seat in r['seatOverrides']:
    p=np.array(seat['position']);zs=[]
    for t in triangles:
     v0=t[1,:2]-t[0,:2];v1=t[2,:2]-t[0,:2];den=v0[0]*v1[1]-v0[1]*v1[0]
     if abs(den)<1e-12:continue
     v2=p[:2]-t[0,:2];a=(v2[0]*v1[1]-v2[1]*v1[0])/den;b=(v0[0]*v2[1]-v0[1]*v2[0])/den
     if a>=-1e-8 and b>=-1e-8 and a+b<=1+1e-8:
      z=t[0,2]+a*(t[1,2]-t[0,2])+b*(t[2,2]-t[0,2])
      if abs(z-p[2])<.10:zs.append(z)
    self.assertTrue(zs,seat['id']);self.assertAlmostEqual(max(zs),p[2],places=5)
 def test_actual_chair_bounds_inside_clearance_proxy(self):
  for idx in IDS:
   g,r=make(idx)
   for i,seat in enumerate(r['seatOverrides'],1):
    if seat['seatType']=='snack_banquette':continue
    prefix=f"Shops/{IDS[idx]}/Personality/Seating/{i}_{seat['seatType']}"
    vv=np.concatenate([np.asarray(b['v']) for (group,mat),b in g.batches.items() if group==prefix]);vv=vv[:,:2]-seat['footprint']['center']
    a=seat['footprint']['angle'];local=vv@np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    self.assertTrue((abs(local).max(axis=0)<=np.array(seat['footprint']['size'])/2+.0001).all(),seat['id'])
 def test_print_faces_have_visible_front_normals(self):
  for idx in IDS:
   g,_=make(idx)
   for (group,mat),b in g.batches.items():
    if mat!='Night_Print':continue
    vv=np.array(b['v']);ff=np.array(b['f']);q=vv[ff];normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);self.assertTrue((normal[:,1]>0).all(),group)
    if '/Signage' in group:
     for first in range(0,len(vv),4):
      v=vv[first:first+4];uv=np.array(b['uv'])[first:first+4];w=np.ptp(v[:,0]);h=np.ptp(v[:,2])
      if w/h>2.1:self.assertAlmostEqual(np.ptp(uv[:,0])/w,np.ptp(uv[:,1])/h,places=6)
 def test_global_random_state_unchanged(self):
  a=random.getstate();b=np.random.get_state()
  for idx in IDS:make(idx)
  self.assertEqual(a,random.getstate());c=np.random.get_state();self.assertEqual(b[0],c[0]);np.testing.assert_array_equal(b[1],c[1]);self.assertEqual(b[2:],c[2:])
 def test_safe_exit_clearance(self):
  reports=[]
  for idx in IDS:
   g,r=make(idx);a=clearance(r);reports.append(dict(shop=IDS[idx],**a));self.assertTrue(a['seatExitsConnected'],a)
 def test_route_clearance(self):
  failures=[]
  for idx in IDS:
   g,r=make(idx);a=clearance(r)
   failures.extend(dict(shop=IDS[idx],**f) for f in a['routeViolations'])
  self.assertFalse(failures,failures)
 def test_snack_is_seated_interior(self):
  _,r=make(3);self.assertTrue(all(abs(s['position'][0])<2.5 and abs(s['position'][1])<2.7 for s in r['seatOverrides']));self.assertEqual(sum(s['seatType']=='snack_banquette' for s in r['seatOverrides']),3)
 def test_three_distinct_themes(self):
  rr=[make(i)[1] for i in IDS];self.assertEqual(len(set(r['theme'] for r in rr)),3)
  self.assertEqual(len(set(tuple(r['components']) for r in rr)),3)
 def test_no_extra_emission(self):
  self.assertTrue(all(d.get('emission',0)==0 for d in material_specs()))

if __name__=='__main__':unittest.main()
