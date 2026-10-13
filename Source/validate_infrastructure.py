"""Offline plumbing graph and beacon-source checks; not Unity shader execution."""
from pathlib import Path
import json, math, sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());infra=m.get('infrastructure');checks=[]
def check(name,ok,detail=''):checks.append(dict(name=name,passed=bool(ok),detail=detail))
check('Infrastructure enabled',bool(infra))
if infra:
 routes={x['id']:x for x in infra['utilityRoutes']}
 for kind,top in [('water',52),('gas',46),('electrical',94),('telecom',94)]:
  r=routes['Trunk_'+kind];check(kind+' reaches upper service elevation',abs(r['points'][-1][2]-top)<1e-6)
  check(kind+' starts at ground service riser',abs(r['points'][0][2]-1.3)<1e-6)
  check(kind+' rises continuously',all(b[2]>=a[2] for a,b in zip(r['points'],r['points'][1:])))
  check(kind+' ground-to-riser endpoints coincide',math.dist(routes['Ground_'+kind]['points'][-1],r['points'][0])<1e-6)
 mats={x['name']:x for x in m['materials']}
 for beacon in infra['beacons']:
  check(beacon['id']+' uses animated shader',mats[beacon['material']].get('shader')=='Beacon')
  check(beacon['id']+' timing contract',beacon['period']==2 and beacon['dutyCycle']==.16 and beacon['phase']==0)
  check(beacon['id']+' excluded from baked GI',beacon['excludeFromLightmap'])
 check('Three red warning lenses',len(infra['beacons'])==3)
 check('Sixty powered lamp posts for repaired layout',infra['stats']['pathPoles']==60)
 shader=(root/'Assets/TreeTopYokocho/Shaders/YokochoBeacon.shader').read_text()
 builder=(root/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
 check('Shader uses per-frame engine time',all(x in shader for x in ['_Time.y/max(_Period,0.5)+_Phase','smoothstep','UNITY_VERTEX_OUTPUT_STEREO','UNITY_APPLY_FOG']))
 check('Builder excludes beacon from static GI',all(x in builder for x in ['m.shader != "Beacon"','bool animated = foliage || beacon ||']))
 # Independent numerical timing regression of the source equation.
 def smooth(a,b,x):
  t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
 def pulse(t):
  p=(t/2)%1;e=.025;return smooth(0,e,p)*(1-smooth(.16-e,.16,p))
 check('Pulse repeats after two seconds',all(abs(pulse(t)-pulse(t+2))<1e-10 for t in [.02,.09,.25,.31,.5,1.9]))
 check('Pulse reaches peak and returns dark',pulse(.15)>.999 and pulse(.6)==0)
report=dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',scope='Offline route metadata and shader-source logic; Unity/VRChat shader compilation and actual flashing remain untested.',checks=checks)
(root/'Docs/infrastructure_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(report['status']!='PASS')
