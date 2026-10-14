"""Color-only snow-retention invariants; selected soft admission is separate v2."""
import copy,unittest
from unittest.mock import patch
import numpy as np
from test_snow_deposition import geometry,fields,raw
from mountain_detail import apply_mountain_detail,KEYS
from fantasy_landscape import apply_snow_deposition
import mountain_snow_craft as snow

class SnowCraftStudyTests(unittest.TestCase):
 def test_both_studies_change_only_eight_snow_color_records(self):
  g=geometry();apply_mountain_detail(g);baseline=copy.deepcopy(g);apply_snow_deposition(baseline);baseline.compact();baseline.bake_mood([])
  for strength in ('balanced','strong','soft'):
   after=copy.deepcopy(g);materials=copy.deepcopy(after.materials);stats=snow.apply_mountain_snow_craft(after,strength);after.compact();after.bake_mood([])
   self.assertEqual(materials,after.materials);self.assertEqual(list(baseline.batches),list(after.batches));changed=[]
   for k in KEYS:
    b,a=fields(baseline.batches[k]),fields(after.batches[k])
    for f in ('v','uv','f'):self.assertEqual(b[f],a[f],(strength,k,f))
    if b['colors']!=a['colors']:changed.append(k)
    self.assertTrue(np.all(after.batches[k]['colors'][:,3]==1))
    self.assertTrue(np.isfinite(after.batches[k]['colors']).all())
   self.assertEqual(changed,[k for k in KEYS if k[1]!='AlpineRock']);self.assertEqual(stats['trianglesAdded'],0)

 def test_all_dark_sublevel_components_touch_rock(self):
  # Verify all distinct coverage thresholds, not just a chosen cutoff.
  for strength in ('balanced','strong','soft'):
   g=geometry();apply_mountain_detail(g);capture={};original=snow.connected_cover
   def record(raw,faces,boundary,**kwargs):
    cover=original(raw,faces,boundary,**kwargs);capture.update(raw=raw,faces=faces,boundary=boundary,cover=cover);return cover
   with patch.object(snow,'connected_cover',record):snow.apply_mountain_snow_craft(g,strength)
   raw,faces,boundary,cover=(capture[k] for k in ('raw','faces','boundary','cover'));neighbors=[set() for _ in cover]
   for a,b,c in faces:neighbors[a].update((b,c));neighbors[b].update((a,c));neighbors[c].update((a,b))
   parent=np.arange(len(cover));seed=np.zeros(len(cover),bool);seed[boundary]=True;active=np.zeros(len(cover),bool);bad=0
   def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
   for value in np.unique(cover):
    ids=np.flatnonzero(cover==value)
    for i in ids:active[i]=True;bad+=int(not seed[i])
    for i in ids:
     for j in neighbors[i]:
      if not active[j]:continue
      a,b=find(i),find(j)
      if a==b:continue
      bad-=int(not seed[a])+int(not seed[b]);parent[b]=a;seed[a]=seed[a] or seed[b];bad+=int(not seed[a])
    self.assertEqual(bad,0,(strength,float(value)))
   self.assertTrue(np.all(cover[np.asarray(boundary)]==0));self.assertTrue(np.all(cover>=np.where(np.isin(np.arange(len(raw)),boundary),0,raw)-1e-10))

 def test_unrelated_tints_untouched_and_double_application_rejected(self):
  g=geometry();apply_mountain_detail(g);g.group='Unrelated';g.material('Other',(.5,.5,.5));g.add([(0,0,0),(1,0,0),(0,1,0)],[(0,1,2)],'Other');g.batches[('Unrelated','Other')]['authored_tints']=[(0,3,[.4,.5,.6])];before=copy.deepcopy(g.batches[('Unrelated','Other')]);snow.apply_mountain_snow_craft(g)
  self.assertEqual(before,g.batches[('Unrelated','Other')]);
  with self.assertRaises(ValueError):snow.apply_mountain_snow_craft(g)

if __name__=='__main__':unittest.main(verbosity=2)
