"""Source-authored entrance furniture. Never mutates the immutable core.
Usage: python Source/build_entry_plaza.py BASELINE_ROOT [OUTPUT_ROOT]
"""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
BASE=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/'Source'))
from world_geometry import Geometry
from timber_craft import timber_box_mesh
A=OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza';D=A/'Data';T=A/'Textures'
for p in [D,T,OUT/'Docs',OUT/'Preview']:p.mkdir(parents=True,exist_ok=True)
g=Geometry();FLOOR=134.0
materials={}
def mat(name,color,texture='',rough=.85):
 materials[name]=dict(name=name,color=list(color),texture=texture,roughness=rough)
 return g.material(name,color,texture,roughness=rough)
wood=mat('EntryHeartwood',[.74,.56,.34],'EntryTimber.png');bark=mat('EntryBark',[.34,.23,.14],'EntryTimber.png');cut=mat('EntryEndgrain',[.79,.63,.42],'EntryEndgrain.png');dark=mat('EntryDarkTimber',[.27,.19,.12],'EntryTimber.png');brass=mat('EntryPatinatedBrass',[.44,.34,.19],rough=.72);ink=mat('EntryCarvedInk',[.105,.15,.13]);guide=mat('EntryGuidePrint',[1,1,1],'EntryGuideboard.png');header=mat('EntryControlPrint',[1,1,1],'EntryControls.png');control_title=mat('EntryControlHeader',[1,1,1],'EntryControlsHeader.png')
for i,label in enumerate(['根元','中層','上層']):mat('EntryWarp'+str(i),[1,1,1],'EntryWarp'+str(i)+'.png')
# Deterministic authored timber, not a downloaded image.
n=1024;y,x=np.mgrid[:n,:n];grain=np.sin(x*.11+2.2*np.sin(y*.008)+np.sin(x*.021))*3+np.sin(x*.47+y*.004)*1.2;grain+=np.sin(x*.026+np.sin(y*.014))*7
arr=np.stack([154+grain,114+grain*.82,68+grain*.60],axis=-1).clip(0,255).astype('uint8');Image.fromarray(arr).save(T/'EntryTimber.png')
r=np.sqrt((x-n*.51)**2+(y-n*.49)**2);ang=np.arctan2(y-n*.49,x-n*.51);rings=np.sin(r*.16+np.sin(ang*5)*.6+np.sin(r*.03))*6
arr=np.stack([188+rings,148+rings*.85,97+rings*.7],axis=-1).clip(0,255).astype('uint8');Image.fromarray(arr).save(T/'EntryEndgrain.png')
font=BASE/'Source/fonts/upstream/kleeone/KleeOne-Regular.ttf';bold=BASE/'Source/fonts/upstream/kleeone/KleeOne-SemiBold.ttf'
def ff(size,strong=False):return ImageFont.truetype(str(bold if strong else font),size)
def centered(d,xy,text,size,fill='#173126',strong=False):d.text(xy,text,font=ff(size,strong),fill=fill,anchor='mm')
def paper(size):
 w,h=size;im=Image.new('RGB',size,'#d7c49b');dr=ImageDraw.Draw(im);dr.rounded_rectangle((20,20,w-20,h-20),30,outline='#5d6b52',width=4);dr.rounded_rectangle((34,34,w-34,h-34),24,outline='#9d8b62',width=2);return im,dr
im,d=paper((2048,1280));centered(d,(1024,148),'樹上横丁',160,strong=True);centered(d,(1024,290),'雲の上で、ひとやすみ。',62);d.line((160,375,1888,375),fill='#7a8265',width=3)
# Small authored tree / branching wayfinding pictogram.
d.line((430,865,430,480),fill='#4a6050',width=20);d.line((430,625,290,555),fill='#4a6050',width=13);d.line((430,720,590,640),fill='#4a6050',width=13)
for xx,yy,r in [(430,480,75),(280,535,65),(590,625,70)]:d.ellipse((xx-r,yy-r,xx+r,yy+r),outline='#647758',width=8)
centered(d,(430,985),'現在地  一層・入口',46,strong=True)
for yy,a,b in [(492,'一層  134 m','甘味処・横丁の入口'),(650,'二層  140 m','お店を巡る、小さな寄り道'),(808,'三層  146 m','上層の横丁へ'),(966,'根元  0 m','大樹の足もとへ')]:
 d.text((820,yy),a,font=ff(62,True),fill='#2b443b',anchor='lm');d.text((820,yy+77),b,font=ff(43,True),fill='#20372b',anchor='lm')
centered(d,(1024,1178),'下の木札に触れると、各階の昇降口へ移動できます。',43,strong=True)
im.save(T/'EntryGuideboard.png')
im,d=paper((1536,1024));im.save(T/'EntryControls.png')
im,d=paper((1536,192));centered(d,(768,95),'環境のしつらえ',108,strong=True);im.save(T/'EntryControlsHeader.png')
for i,label in enumerate(['根元へ','二層へ','三層へ']):
 im,d=paper((512,384));centered(d,(256,170),label,96,strong=True);centered(d,(256,286),'木札に触れて移動',30,strong=True);im.save(T/f'EntryWarp{i}.png')
occupied=[]
def box(name,c,size,material,bevel=.012,collision=True):
 g.group='EntryPlaza/'+name;v,f,uv=timber_box_mesh(c,size,None,bevel=min(bevel,min(size)*.2));g.add(v,f,material,uv)
 if collision:occupied.append(dict(name=name,center=list(c),size=list(size),axes=[1,0,0,0,1,0,0,0,1]))
def plane(name,x,y,z,w,h,material):
 # Front faces +sourceY, UV right = source-X as viewed from north.
 g.group='EntryPlaza/'+name;g.quad([[x+w/2,y,z-h/2],[x-w/2,y,z-h/2],[x-w/2,y,z+h/2],[x+w/2,y,z+h/2]],material)
def log(name,a,b,r,material=bark):
 g.group='EntryPlaza/'+name;a=np.array(a,float);b=np.array(b,float);g.tube([a,b],[r,r*.96],material,segments=20,rough=.035)
 # Detailed separate pale cut surfaces with radial UVs and rings baked into caps.
 axis=(b-a)/np.linalg.norm(b-a);ref=np.array([0,0,1.]) if abs(axis[2])<.9 else np.array([1.,0,0]);u=np.cross(axis,ref);u/=np.linalg.norm(u);v=np.cross(axis,u)
 for end,sign in [(a,-1),(b,1)]:
  center=end+axis*sign*.002;verts=[center]+[center+r*.94*(math.cos(t)*u+math.sin(t)*v) for t in np.linspace(0,math.tau,21)];uv=[(.5,.5)]+[(.5+.48*math.cos(t),.5+.48*math.sin(t)) for t in np.linspace(0,math.tau,21)];faces=[(0,j+2,j+1) if sign<0 else (0,j+1,j+2) for j in range(20)];g.add(verts,faces,cut,uv)
 # Conservative shape envelope for runtime collision and independent occupancy audit.
 lo=np.minimum(a,b)-r;hi=np.maximum(a,b)+r
 if abs(axis[2])>.99:lo[2]=min(a[2],b[2]);hi[2]=max(a[2],b[2])
 occupied.append(dict(name=name,center=((lo+hi)/2).tolist(),size=(hi-lo).tolist(),axes=[1,0,0,0,1,0,0,0,1]))
def board(name,x,y,width,top,base,printmat):
 # Feet terminate precisely at native floor; visual floor contact audited separately.
 for dx in [-width/2+.14,width/2-.14]:
  box(name+'/Post',(x+dx,y,FLOOR+(top-FLOOR)/2),(.15,.20,top-FLOOR),dark)
  box(name+'/Foot',(x+dx,y,FLOOR+.035),(.28,.40,.07),brass)
 height=top-base
 box(name+'/Back',(x,y,(top+base)/2),(width,.16,height),wood)
 plane(name+'/Print',x,y+.086,(top+base)/2,width-.18,height-.18,printmat)
 box(name+'/Crown',(x,y-.01,top+.10),(width+.30,.30,.18),dark)
 for zz in [base+.04,top-.04]:box(name+'/FrameRail',(x,y+.105,zz),(width+.06,.10,.10),wood)
 for dx in [-width/2+.04,width/2-.04]:box(name+'/FrameStile',(x+dx,y+.105,(base+top)/2),(.10,.10,height),wood)
 # Small wooden weather cap, hand-built low pitch and brass pegs.
 for side in [-1,1]:
  for dx in [-width/2+.14,width/2-.14]:
   g.group='EntryPlaza/'+name+'/Peg';g.cylinder((x+dx,y+.163,top-.12),.022,.024,brass,n=10)
board('Guideboard',-5.1,-32.3,3.0,136.72,135.12,guide)
board('SystemsFrame',-8,-31.8,1.65,136.05,134.80,header)
plane('SystemsFrame/Header',-8,-31.635,136.15,1.60,.15,control_title)
# Three restrained hanging wayfinding plaques. No glow, particles or added lights.
warps=[]
for i,(x,level,z,label) in enumerate([(-6.05,'G0',0,'根元へ'),(-5.1,'L2',140,'二層へ'),(-4.15,'L3',146,'三層へ')]):
 for dx in [-.18,.18]:box('WarpPlaques/Tie'+str(i),(x+dx,-32.19,135.105),(.035,.035,.25),dark,bevel=.003,collision=False)
 box('WarpPlaques/Tablet'+str(i),(x,-32.18,134.90),(.70,.10,.42),wood,bevel=.026)
 plane('WarpPlaques/Print'+str(i),x,-32.122,134.90,.65,.37,'EntryWarp'+str(i))
 warps.append(dict(id='Entry_To_'+level,label=label,position=[x,-32.09,134.90],size=[.74,.16,.46],destination=[-16,-18.55,z+.08],forward=[0,-1,0],approach=[x,-30.95,134],range=2.2))
# A pair of sculpted log benches and a low tree-ring table make a small gathering nook.
# These are ordinary static furniture, NOT additional VRCStation seats.
for i,(x,y,length) in enumerate([(-6.15,-27.95,2.55),(-8.65,-29.75,1.55)]):
 for dx in [-length*.34,length*.34]:
  log(f'LogBench{i}/Leg{dx}',(x+dx,y-.24,134.13),(x+dx,y+.24,134.13),.13)
 log(f'LogBench{i}/Heart',(x-length/2,y,134.34),(x+length/2,y,134.34),.20)
 box(f'LogBench{i}/HandplanedSeat',(x,y,134.52),(length+.08,.42,.08),wood,bevel=.025)
log('StumpTable',(-7.65,-28.90,134.01),(-7.65,-28.90,134.52),.35)
# Fine endgrain top; broad enough for a cup, not a walking destination.
g.group='EntryPlaza/StumpTableTop';g.cylinder((-7.65,-28.90,134.535),.365,.03,cut,n=32)
occupied.append(dict(name='StumpTableTop',center=[-7.65,-28.90,134.535],size=[.73,.73,.03],axes=[1,0,0,0,1,0,0,0,1]))
g.compact();g.bake_mood([]);g.save_binary(D/'EntryPlazaMeshes.bytes');g.save_glb(OUT/'Preview/EntryPlaza.glb',T,lossless_textures=['EntryGuideboard.png','EntryControls.png','EntryControlsHeader.png']+[f'EntryWarp{i}.png' for i in range(3)])
manifest=json.loads((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
config=dict(schemaVersion=1,coordinateSystem='source Z-up; Unity=(x,z,y)',ownerRoot='EntrySystems_v1',childRoot='EntryPlaza',coreRoot='TreeTopYokocho_v2',baselineVersion='2.19.0',nativeGeometry='EntryPlazaMeshes.bytes',materials=list(materials.values()),solidBoxes=occupied,warps=warps,systemsControlAnchor=dict(position=[-8,-31.8,134],forward=[0,1,0],frontY=-31.62,usableMin=[-8.70,-31.61,134.90],usableMax=[-7.30,-31.60,135.85],standing=[-8,-30.5,134],buttonCenters=[[-8+dx,-31.59,134+dz] for dz in [1.50,1.26,1.02] for dx in [.36,-.36]],buttonSize=[.60,.035,.19],reservedVolumeMin=[-8.70,-31.63,134.845],reservedVolumeMax=[-7.30,-31.55,135.85]),routes=[dict(id='SpawnToGuide',points=[[-1,-28],[-3.7,-28.6],[-4.2,-29.8],[-5.1,-30.80]],floor=134),dict(id='GuideToControls',points=[[-5.1,-30.80],[-6.5,-30.5],[-8,-30.5]],floor=134),dict(id='SpawnsThroughGate',points=[[1,-26.4],[0,-28],[0,-30],[0,-33]],floor=134),dict(id='PlazaToNook',points=[[-5.1,-30.80],[-6.2,-29.5]],floor=134)],standingPoints=[dict(id='Controls',position=[-8,-30.5,134]),dict(id='Guide',position=[-5.1,-30.80,134])]+[dict(id=w['id'],position=w['approach']) for w in warps],clearance=dict(radius=.325,headroom=2.2,footTolerance=.06),preservation=dict(stations=49,spawns=manifest['spawns'],teleports=manifest['teleports'],coreManifestSha256=hashlib.sha256((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_bytes()).hexdigest()),addedLights=0,addedStations=0,triangles=sum(len(b['f']) for b in g.batches.values()),meshCount=len(g.batches),testedInUnity=False,testedInVRChat=False)
(D/'EntryPlaza.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(triangles=config['triangles'],meshCount=len(g.batches),boxes=len(occupied),warps=len(warps),out=str(OUT))))
