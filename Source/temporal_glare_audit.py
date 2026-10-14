"""Selected source-formula audit. Not GPU execution, photometry or VR comfort certification."""
from pathlib import Path
import argparse,importlib.util,json,math
import numpy as np

ROOT=Path(__file__).resolve().parent

def values(entries):return {e['name']:e['value'] for e in entries}
def load(project):
 p=json.loads((project/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text())
 m={x['name']:x for x in json.loads((project/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())['materials']}
 return p,m

def paper_factor(t,breath=.012):return 1+min(.03,max(0,breath))*np.sin(np.asarray(t)*.31)
def aurora(angle,y,t,height=.50,width=24,speed=.012):
 drift=np.asarray(t)*min(.025,max(0,speed))
 wave=np.sin(angle*3+drift)*.032+np.sin(angle*7-drift*.61)*.015
 return np.exp(-np.abs(y-height-wave)*width)*(.66+.34*np.sin(angle*31+np.sin(angle*5)*2+drift))
def glaze_f0(color,metal,ndv,iridescence=.18,cycles=.75):
 ndv=np.asarray(ndv)[...,None];phase=(1-ndv)*min(2,max(.2,cycles))*math.tau
 film=.5+.5*np.cos(phase+np.array([0,2.0943951,4.1887902]))
 base=.04*(1-metal)+np.clip(color,0,1)*metal
 return np.clip(base*(1+((.6+.8*film)-1)*min(.25,max(0,iridescence))*(1-ndv)**2*(1-metal)),0,1)

def water_normal(x,y,t,slope=.010):
 t=np.asarray(t)
 wa=(-.6*x+.8*y)*.021+t*.07;wb=(.8*x+.6*y)*.017-t*.05
 pa=(.8*x+.6*y)*.13+t*.4+1.1*np.sin(wa)
 pb=(-.6*x+.8*y)*.19-t*.28+.8*np.sin(wb)
 ga0=.8-.6*(.021*1.1/.13)*np.cos(wa);ga1=.6+.8*(.021*1.1/.13)*np.cos(wa)
 gb0=-.6+.8*(.017*.8/.19)*np.cos(wb);gb1=.8+.6*(.017*.8/.19)*np.cos(wb)
 nx=-(ga0*np.cos(pa)*.65+gb0*np.cos(pb)*.35)*slope
 ny=-(ga1*np.cos(pa)*.65+gb1*np.cos(pb)*.35)*slope
 n=np.stack([nx,ny,np.ones_like(nx)],axis=-1)
 return n/np.linalg.norm(n,axis=-1,keepdims=True)

def report(project):
 p,m=load(project);out={'scope':'Source-formula/CPU samples; no Unity shader execution, display glare or VR comfort measurement','materials':{},'temporal':{}}
 for g in p['materialGroups']:
  f=values(g.get('floats',[]))
  for name in g['names']:
   a=m[name];r={'shader':g['shader']}
   if g['shader']=='LanternPaper':
    e=a.get('emission',0);b=f.get('_Breath',.015);r|={'baseEmission':e,'emissionMultiplierRange':[1-b,1+b],'perChannelRadianceUpperBound':(np.array(a['color'][:3])*e*(1+b)).tolist(),'periodSeconds':math.tau/.31,'maximumRelativeChangePerSecond':b*.31,'smoothnessCannotExceedBaseline':True}
   elif g['shader']=='Glaze':
    metal=a.get('metallic',0);x=glaze_f0(a['color'][:3],metal,np.linspace(0,1,10001),f['_Iridescence'],f['_FilmCycles'])
    r|={'f0MinRGB':x.min(axis=0).tolist(),'f0MaxRGB':x.max(axis=0).tolist(),'smoothness':min(.92,max(.08,1-a['roughness'])),'baselineSmoothness':1-a['roughness'],'emission':0,'temporalInputs':False}
   elif g['shader']=='Cloth':r|={'f0Range':[.025,.025+f.get('_Sheen',.055)],'smoothnessRange':[.04,.28],'emission':0,'temporalInputs':False,'weaveFadesBeforeHalfCyclePerPixel':True}
   elif g['shader']=='Surface':
    grain=f.get('_GrainRoughness',0);pat=f.get('_Patina',0);has=bool(a.get('arm'))
    r|={'craftSmoothnessChangeConservative':[-.5*grain-.25*pat if has else -.5*grain,.5*grain],'patinaActive':has and pat>0,'baseTintAndEmissionUnchanged':True}
   else:continue
   out['materials'][name]=r
 # Dense float32 time samples include the requested10h work horizon and24h.
 for start in (0,3600,36000,86400):
  t=np.asarray(start+np.arange(1801)/90,dtype=np.float32)
  v=paper_factor(t)
  maxsky=0
  for angle in np.linspace(-math.pi,math.pi,31):
   for height in (.45,.50,.55):maxsky=max(maxsky,float(np.max(np.abs(np.diff(aurora(angle,height,t))))))
  maxwater=max(float(np.max(np.linalg.norm(np.diff(water_normal(x,y,t),axis=0),axis=1))) for x,y in [(0,0),(-6300,-7100),(6300,-8000),(300,-900)])
  out['temporal'][str(start)]={'waterAnalyticMax90HzNormalAngleDegrees':math.degrees(2*math.asin(maxwater/2)),'paperMultiplierMin':float(v.min()),'paperMultiplierMax':float(v.max()),'paperMax90HzStep':float(np.abs(np.diff(v)).max()),'auroraMax90HzRibbonStep':maxsky,'auroraMaxGreenRadianceStep':maxsky*.15*.80}
 out['notes']=['Aurora samples exclude stars (static), independent sky gradient, and advected cloud masks; they bound the added ribbon signal only.','Water normal samples exclude texture filtering and source image lookup; only the resolved analytic wave component is checked.', 'Material/texture exposure, bloom, light count, display and eye comfort need Unity/VR testing.','Existing AviationRed Beacon still flashes as a safety light; it was not added or changed by this shader task.','Uniform ranges do not enforce arbitrary external-script inputs; selected profile/manifest inputs are audited.']
 return out

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--project',type=Path,default=ROOT.parent);a.add_argument('--output',type=Path,default=ROOT.parent/'Docs/temporal_glare_report.json');args=a.parse_args()
 result=report(args.project)
 import hashlib
 sources=list((args.project/'Assets/TreeTopYokocho/Shaders').glob('*.shader'))+[args.project/'Assets/TreeTopYokocho/Data/FantasyMaterials.json',args.project/'Assets/TreeTopYokocho/Data/WorldManifest.json']
 result['sourceSHA256']={str(path.relative_to(args.project)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['temporal'],indent=2))
