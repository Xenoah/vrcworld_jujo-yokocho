"""Build the complete Tree-top Yokocho visual asset and independent collision data.
Run from the supplied Source folder; output is ../Assets and ../Preview.
Uses bundled CC0 PBR scans. Regeneration is offline; Unity or Blender is not required.
"""
import json, math, sys, random, wave, shutil
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box as rect
from shapely.ops import unary_union
from world_geometry import Geometry,poly_mesh
from create_textures import make_textures
from fantasy_landscape import landscape
from tree_infrastructure import add_infrastructure
from high_crown_stairs import add_crown_stairs,crown_attachment_openings
from altitude_profile import apply_altitude_profile
from cloud_sea import add_cloud_sea
from booster_pumps import add_booster_pumps
from scenery_detail import add_scenery_detail
from noh_stage import stage_layout,add_noh_stage
from high_detail import detailed_textures,roof_tiles,noren,shop_details,detailed_crown,detailed_deck,leaf,foliage_cluster

VERSION='2.6.0'
FEATURES={'infrastructure':True,'crown_stairs':True,'noh_stage':True,'high_altitude':True,'scenery_detail':True}

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
SOURCE=ROOT/'Source';ASSET=ROOT/'Assets/TreeTopYokocho';DATA=ASSET/'Data';TEX=ASSET/'Textures'
for p in [SOURCE,DATA,TEX,ROOT/'Preview',ASSET/'Audio']:p.mkdir(parents=True,exist_ok=True)
layout=json.loads((SOURCE/'layout.reference.json').read_text())
# Keep the reference intact. A verified navigation fix routes W05 around the
# east/start end of R03 instead of diagonally through its continuous side wall.
for route in layout['paths']:
    if route['id']=='W04':
        route['points']=[[13.416,-12],[19.5,-13.4],[21,-13.4],[21,-12]]
    if route['id']=='W05':
        route['points']=[[-16,-18],[-23,0],[-18,14],[-8.2,20],[-8.2,22],[-10,22]]

font=Path(sys.argv[2]) if len(sys.argv)>2 else SOURCE/'NotoSansCJKjp-Regular.otf'
if font.exists():
    make_textures(TEX,font)
    detailed_textures(TEX,font)
elif not (TEX/'signs.png').exists():raise FileNotFoundError('Supply a Japanese font as second argument for first generation.')
rng=np.random.default_rng(12040);random.seed(12040)
g=Geometry();c=Geometry()
def mat(name,col,tex='',em=0,rough=.8,**pbr):return g.material(name,col,tex,em,rough,**pbr)
def scan(asset,scale=1):
    return dict(normal=f'PBR/{asset}_nor_gl_2k.jpg',arm=f'PBR/{asset}_arm_2k.jpg',height=f'PBR/{asset}_disp_2k.jpg',uvScale=scale,normalScale=1,parallax=.014)
def procedural(prefix,**kwargs):return dict(normal=prefix+'_normal.png',arm=prefix+'_arm.png',**kwargs)
wood=mat('Cedar',(.94,.76,.57),'PBR/wood_planks_grey_diff_4k.jpg',rough=1,**scan('wood_planks_grey',.65))
dark=mat('DarkTimber',(.56,.42,.29),'PBR/wood_planks_grey_diff_4k.jpg',rough=1,**scan('wood_planks_grey',.65))
lightwood=mat('Counter',(.91,.83,.70),'PBR/wood_table_001_diff_4k.jpg',rough=.90,**scan('wood_table_001',.75))
trim=mat('Bronze',(.40,.30,.17),rough=.43,metallic=.80)
wall=mat('Plaster',(.91,.83,.71),'plaster.png',rough=1,**procedural('plaster'))
tile=mat('Kawara',(.67,.72,.77),'tile_clay.png',rough=1,**procedural('tile_clay'))
bark=mat('Bark',(.90,.86,.77),'PBR/bark_brown_02_diff_4k.jpg',rough=1,**scan('bark_brown_02',.36))
moss=mat('Moss',(.26,.37,.14),'PBR/rocky_terrain_02_diff_4k.jpg',rough=1,**scan('rocky_terrain_02',.6))
leafs=[mat('Foliage'+str(i),col,'leaf.png',rough=.83,normal='leaf_detail_normal.png',arm='leaf_detail_arm.png',shader='Foliage') for i,col in enumerate([(.72,.82,.52),(.77,.90,.58),(.87,.93,.62),(.62,.82,.54)])]
cloth=[mat('Noren'+str(i),col,'woven.png',rough=1,**procedural('woven')) for i,col in enumerate([(.085,.14,.23),(.76,.66,.46),(.35,.17,.12),(.12,.24,.16),(.23,.28,.15),(.075,.105,.19),(.39,.10,.065),(.75,.66,.47)])]
paper=mat('PaperLight',(1,.68,.27),'lantern.png',2.0);red=mat('RedLantern',(.89,.13,.04),'lantern.png',1.3)
window=mat('WarmWindow',(1,.56,.19),'',2.1);signmat=mat('SignAtlas',(1,.96,.87),'signs.png',0,rough=.90)
iron=mat('Iron',(.12,.14,.15),rough=.42,metallic=.72);ceramic=mat('Ceramic',(.64,.71,.67),rough=.20)
green=mat('BottleGreen',(.045,.15,.075),rough=.13,metallic=.12);amber=mat('BottleAmber',(.22,.08,.015),rough=.16,metallic=.12)
food=mat('Food',(.58,.25,.075),rough=.33);black=mat('Grout',(.045,.035,.025))
stone=mat('Stone',(.65,.69,.67),'PBR/rocky_terrain_02_diff_4k.jpg',rough=1,**scan('rocky_terrain_02',.65))
lake=mat('Lake',(.038,.10,.15),'',rough=.15,metallic=.5,normal='water_normal.png',shader='Water')
city=mat('TownLights',(1,.58,.18),'',2.1)
terrain=mat('Terrain',(.23,.32,.19),'PBR/rocky_terrain_02_diff_4k.jpg',rough=1,**scan('rocky_terrain_02',1))
menu=mat('MenuAtlas',(1,.96,.83),'menus.png',rough=.91)
noodle=mat('Noodles',(.81,.65,.33),rough=.54);sweet=mat('MatchaSweets',(.38,.48,.18),rough=.67);tea=mat('Tea',(.16,.10,.02),rough=.12);soy=mat('Soy',(.08,.035,.017),rough=.20)
forest=[mat('ForestCanopy'+str(i),col,'leaf.png',rough=.94,uvScale=6) for i,col in enumerate([(.057,.099,.054),(.069,.121,.068),(.09,.14,.075)])]
townwalls=[]
for i,col in enumerate([(.52,.48,.38),(.43,.43,.37),(.31,.32,.28)]):
    if i==1:townwalls.append(mat('TownPlaster'+str(i),col,'plaster.png',rough=1,**procedural('plaster')))
    else:townwalls.append(mat('TownTimber'+str(i),col,'PBR/wood_planks_grey_diff_4k.jpg',rough=1,**scan('wood_planks_grey',.5)))

spraymat=mat('FoliageSpray',(.88,.92,.80),'foliage_spray.png',rough=.85,shader='Foliage',alphaClip=.4)
forestSpray=mat('ForestSpray',(.29,.36,.27),'foliage_spray.png',rough=.95,shader='Foliage',alphaClip=.4)
road=mat('Road',(.16,.18,.17),'tile_clay.png',rough=1)
M=dict(wood=wood,dark=dark,counter=lightwood,trim=trim,wall=wall,tile=tile,bark=bark,leafs=leafs,window=window,iron=iron,ceramic=ceramic,food=food,red=red,city=city,stone=stone,lake=lake,terrain=terrain,menu=menu,tea=tea,soy=soy,noodle=noodle,sweet=sweet,forest=forest,townwalls=townwalls,road=road,forestSpray=forestSpray)
c.material('collision',(1,1,1))
steam=[];lights=[];stations=[];teleports=[];solidBoxes=[];floorTests=[];wallTests=[];guards=[];routes=[]

def box(cen,size,material,axes=None):g.box(cen,size,material,axes)
def collbox(name,cen,size,axes=None):
    if axes is None:axes=np.eye(3)
    solidBoxes.append({'name':name,'center':np.asarray(cen).tolist(),'size':list(size),'axes':np.asarray(axes).reshape(-1).tolist()})

def sign(center,right,normal,width,height,slot):
    p=np.array(center);u=np.array(right);up=np.array([0,0,1]);n=np.array(normal)
    g.box(p-n*.045,(width,.085,height),dark,[u,n,up])
    q=[p-u*width/2-up*height/2,p+u*width/2-up*height/2,p+u*width/2+up*height/2,p-u*width/2+up*height/2]
    low=1-(slot+1)/16;high=1-slot/16
    g.quad(q,signmat,[(0,low),(1,low),(1,high),(0,high)])

def lantern(pos,redpaper=False,scale=1,record=True):
    p=np.array(pos);r=.22*scale;h=.55*scale
    g.sphere(p,[r,r,h/2],red if redpaper else paper,20,12)
    for zz in np.linspace(-h*.41,h*.41,13):
        rr=r*math.sqrt(max(.02,1-(zz/(h/2))**2))
        points=[p+[rr*math.cos(a),rr*math.sin(a),zz] for a in np.linspace(0,math.tau,21)]
        g.tube(points,[.0035*scale]*len(points),trim,4)
    for dz in [-h*.43,h*.43]:g.cylinder(p+[0,0,dz],r*.64,.07*scale,iron,10)
    g.beam(p+[0,0,h/2],p+[0,0,h/2+.24*scale],.018,iron)
    if record:lights.append({'position':(p-[0,0,.3]).tolist(),'range':4.8*scale,'strength':1.4})

def lamp(pos):
    p=np.array(pos);box(p+[0,0,.23],[.23,.23,.46],dark)
    box(p+[0,0,.26],[.24,.24,.28],window)
    for dx in [-.12,.12]:
        for dy in [-.12,.12]:box(p+[dx,dy,.24],[.03,.03,.42],dark)
    box(p+[0,0,.48],[.32,.32,.055],dark)
    lights.append({'position':(p+[0,0,.38]).tolist(),'range':2.2,'strength':.7})

def bottle(pos,index=0):
    p=np.array(pos);m=green if index%2 else amber
    zs=[.005,.017,.035,.235,.26,.285,.327,.35,.365];rs=[.045,.065,.068,.068,.060,.031,.029,.030,.033]
    g.tube([p+[0,0,z] for z in zs],rs,m,24)
    g.cylinder(p+[0,0,.37],.033,.025,trim,20)
    g.cylinder(p+[0,0,.16],.0685,.10,ceramic,24)

def bowl(pos,r=.13):
    p=np.array(pos)
    profile=[(r*.30,0),(r*.39,.013),(r*.62,.024),(r*.88,.061),(r,.092),(r*.92,.096),(r*.81,.061),(r*.55,.028),(r*.25,.022)]
    v=[];uv=[];f=[];n=28
    for i,(rad,z) in enumerate(profile):
        for j in range(n+1):
            a=j*math.tau/n;v.append(p+[rad*math.cos(a),rad*math.sin(a),z]);uv.append((j/n,i/len(profile)))
            if i and j:k=i*(n+1)+j;f.extend([(k-n-2,k-n-1,k),(k-n-2,k,k-1)])
    g.add(v,f,ceramic,uv);g.cylinder(p+[0,0,.038],r*.50,.008,food,28)

def plant(pos,size=.8):
    p=np.array(pos);g.cylinder(p+[0,0,.14*size],.20*size,.28*size,food,24,r2=.24*size)
    for j in range(10):
        a=j*math.tau/10;tip=p+np.array([math.cos(a)*.24,math.sin(a)*.24,.48+rng.random()*.28])*size
        g.tube([p+[0,0,.25*size],tip],[.013*size,.003*size],dark,6)
        for k in range(3):
            q=p+[0,0,.25*size]+(tip-p-[0,0,.25*size])*(.5+k*.22)
            leaf(g,q,[math.sin(a)*.065*size,-math.cos(a)*.065*size,0],[math.cos(a)*.19*size,math.sin(a)*.19*size,.02],leafs[j%4])

def branch(points,radii,segments=16):
    """Catmull-Rom centerline removes the angular joins of support branches."""
    p=np.asarray(points,dtype=float);r=np.asarray(radii);fine=[];rr=[]
    for i in range(len(p)-1):
        p0=p[max(0,i-1)];p1=p[i];p2=p[i+1];p3=p[min(len(p)-1,i+2)]
        for t in np.linspace(0,1,7,endpoint=False):
            fine.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
            rr.append(r[i]+(r[i+1]-r[i])*t)
    fine.append(p[-1]);rr.append(r[-1]);g.tube(fine,rr,bark,segments,.035)

def shape(center,width,depth,normal):
    n=np.array(normal[:2]);t=np.array([n[1],-n[0]]);o=np.array(center[:2])
    return Polygon([o+t*x+n*y for x,y in [(-width/2,-depth/2),(width/2,-depth/2),(width/2,depth/2),(-width/2,depth/2)]])

levels={l['id']:l['z'] for l in layout['levels']};pieces={k:[] for k in levels}
pieces['G0']=[rect(-26,-37,-6,-21),rect(-19,-23,-13,-15)]
for p in layout['platforms']:pieces[p['level']].append(rect(p['x']-p['width']/2,p['y']-p['depth']/2,p['x']+p['width']/2,p['y']+p['depth']/2))
pieces['L2'].append(Point(0,0).buffer(19.5,quad_segs=64).difference(Point(0,0).buffer(16.5,quad_segs=64)))
if FEATURES['noh_stage']:pieces['L2'].append(Polygon(stage_layout()['deckUnionPolygon']))
for path in layout['paths']:
    # Extend joins 35 cm into their landing. W03 starts at a circle tangent;
    # without this overlap its rectangular floor would touch at one point only.
    pts=np.array(path['points'],dtype=float);d0=pts[1]-pts[0];d0/=np.linalg.norm(d0);d1=pts[-1]-pts[-2];d1/=np.linalg.norm(d1)
    pts[0]-=d0*.35;pts[-1]+=d1*.35
    pieces[path['level']].append(LineString(pts).buffer(path['width']/2,cap_style=2,join_style=2))
for lev in ['G0','L1','L2','L3']:pieces[lev].append(rect(-17.8,-19.8,-14.2,-16.2))
for s in layout['shops'][:4]:
    a=math.radians(s['front_deg']);n=np.array([math.cos(a),math.sin(a)])
    center=np.array([s['x'],s['y']])+n*.67
    pieces[s['level']].append(shape(center,s['width']+.36,s['depth']+1.7,n))

stairs=[]
for st in layout['stairs']:
    a=np.array(st['start']);b=np.array(st['end']);d=(b-a)[:2];length=np.linalg.norm(d);d/=length;t=np.array([d[1],-d[0]])
    poly=shape((a+b)/2,st['width'],length,[*d,0])
    st=dict(st,dir=d.tolist(),side=t.tolist(),polygon=poly)
    stairs.append(st)
    for end,lev in [(a,st['from']),(b,st['to'])]:pieces[lev].append(shape(end,2.4,1.0,[*d,0]))

floors={k:unary_union(v).buffer(0) for k,v in pieces.items()}
for st in stairs:
    a=np.array(st['start'][:2]);b=np.array(st['end'][:2]);d=np.array(st['dir']);t=np.array(st['side'])
    # Notch upper floors so the head does not collide with a deck before reaching
    # the stair top. Leave the final join closed by the actual endpoint landing.
    half=st['width']/2
    cut=Polygon([a-t*half,a+t*half,b-d*.015+t*half,b-d*.015-t*half])
    floors[st['to']]=floors[st['to']].difference(cut).buffer(0)

def stair_height(st,xy):
    s=float(np.dot(np.array(xy)-st['start'][:2],st['dir']))
    if s<-.06 or s>13.26:return None
    cross=abs(np.dot(np.array(xy)-st['start'][:2],st['side']))
    if cross>st['width']/2+.015:return None
    s=np.clip(s,0,13.2)
    h=(s/5.7*3 if s<5.7 else (3 if s<7.5 else 3+(s-7.5)/5.7*3))
    return st['start'][2]+h

def floor_geometry(lev,poly):
    z=levels[lev];g.group='Decks/'+lev;c.group='Floors/'+lev
    v,f=poly_mesh(poly,z,.3);g.add(v,f,wood,np.array(v)[:,:2]);c.add(v,f,'collision')
    detailed_deck(g,poly,z,wood,black)
    # Visible plank seams are visual only. The physical slab is continuous.
    lo=poly.bounds;xx=np.arange(math.floor(lo[0]*4)/4,lo[2],.28)
    for x in xx:
        line=LineString([(x,lo[1]-1),(x,lo[3]+1)]).intersection(poly)
        geoms=list(line.geoms) if line.geom_type=='MultiLineString' else [line]
        for ln in geoms:
            if ln.geom_type!='LineString' or ln.length<.03:continue
            a,b=list(ln.coords)[0],list(ln.coords)[-1]
            g.quad([(a[0]-.006,a[1],z+.002),(b[0]-.006,b[1],z+.002),(b[0]+.006,b[1],z+.002),(a[0]+.006,a[1],z+.002)],black)
    # Structural bearers; deck corners are supported independently from the tree.
    for p in list(poly.geoms) if poly.geom_type=='MultiPolygon' else [poly]:
        coords=list(p.exterior.coords)
        for j,(a,b) in enumerate(zip(coords,coords[1:])):
            if np.linalg.norm(np.array(a)-b)>.5:g.beam([*a,z-.42],[*b,z-.42],.22,dark,.34)

for lev,p in floors.items():floor_geometry(lev,p)

# Open legacy barriers only over the full-width physically supported new joins.
# New stair/bridge floors own their protection outside the existing deck.
attachment_openings=crown_attachment_openings() if FEATURES['crown_stairs'] else []
attachment_masks={lev:unary_union([LineString(np.asarray(o['centerline'])[:,:2]).buffer(o['width']/2+.10,cap_style=2) for o in attachment_openings if o['level']==lev]) for lev in floors}
def open_edge(edge,lev):
    remainder=edge.difference(attachment_masks[lev])
    return [part for part in (list(remainder.geoms) if hasattr(remainder,'geoms') else [remainder]) if part.geom_type=='LineString' and part.length>.002]


def guard_box(lev,a,b,z0,top,name):
    a=np.array(a);b=np.array(b);delta=b-a;ln=np.linalg.norm(delta)
    if ln<.002 or top-z0<.06:return
    d=delta/ln;t=np.array([-d[1],d[0],0]);along=np.array([d[0],d[1],0]);up=np.array([0,0,1])
    c.group='Safety/'+lev
    center=[*(a+b)/2,(z0+top)/2];size=[ln+.10,.24,top-z0]
    c.box(center,size,'collision',[along,t,up])
    guards.append({'level':lev,'a':a.tolist(),'b':b.tolist(),'base':z0,'top':top,'thickness':.24,'name':name})
    # Independent side-crossing test rays for the Unity physics audit.
    if top>z0+.9:
        for h in [z0+.7,min(z0+1.7,top-.15)]:
            mid=(a+b)/2
            wallTests.append({'start':[mid[0]-t[0]*.55,mid[1]-t[1]*.55,h], 'end':[mid[0]+t[0]*.55,mid[1]+t[1]*.55,h]})

def railing(a,b,z0,z1=None):
    a=np.array([*a,z0]);b=np.array([*b,z0 if z1 is None else z1]);length=np.linalg.norm(b-a)
    for h in [.53,1.17]:g.beam(a+[0,0,h],b+[0,0,h],.085,dark)
    n=max(1,int(math.ceil(length/1.5)))
    for k in range(n+1):
        p=a+(b-a)*k/n;g.beam(p,p+[0,0,1.23],.13,wood)
    for k in range(1,max(2,int(length/.34))):
        p=a+(b-a)*k/max(2,int(length/.34));g.beam(p+[0,0,.08],p+[0,0,.52],.045,wood)

for lev,p in floors.items():
    z=levels[lev];g.group='Railings/'+lev
    for pg in list(p.geoms) if p.geom_type=='MultiPolygon' else [p]:
        for ring in [pg.exterior,*pg.interiors]:
            coords=list(ring.coords)
            for i,(a,b) in enumerate(zip(coords,coords[1:])):
                a=np.array(a);b=np.array(b);ln=np.linalg.norm(b-a)
                n=max(1,int(math.ceil(ln/.6)))
                for j in range(n):
                    aa=a+(b-a)*j/n;bb=a+(b-a)*(j+1)/n;mid=(aa+bb)/2
                    top=z+8
                    # Levels are 6 m apart. An 8 m wall on a lower deck must
                    # never project through an upper walking surface (notably
                    # the lift landings and the arrival deck under the ring).
                    edge=LineString([aa,bb])
                    for other_level,other_floor in floors.items():
                        oz=levels[other_level]
                        if z+.5<oz<top+.4 and other_floor.distance(edge)<.4:
                            top=min(top,oz-.38)
                    for st in stairs:
                        # A lower-deck edge directly below a stair must stop at
                        # its underside, instead of cutting through the stair.
                        h=stair_height(st,mid)
                        if h is not None and h>=z-.12:top=min(top,h-.22)
                    for part in open_edge(edge,lev):
                        coords=list(part.coords);guard_box(lev,coords[0],coords[-1],z-.35,top,f'{lev}_{i}_{j}')
                # Keep handrails off every stair opening / under-stair overlap.
                intersect=any(LineString([a,b]).intersects(st['polygon'].buffer(.08)) for st in stairs)
                if not intersect and ln>.03:
                    for part in open_edge(LineString([a,b]),lev):
                        coords=list(part.coords);railing(coords[0],coords[-1],z)
    # Footlights around the accessible outer rim.
    boundary=p.exterior if p.geom_type=='Polygon' else max(p.geoms,key=lambda q:q.area).exterior
    for i in range(0,int(boundary.length),7):
        pp=boundary.interpolate(i);near=np.array([pp.x,pp.y]);inside=p.representative_point();tow=np.array([inside.x,inside.y])-near;tow/=np.linalg.norm(tow)
        loc=near+tow*.30
        if not attachment_masks[lev].buffer(.3).covers(Point(loc)) and not any(st['polygon'].buffer(.6).covers(Point(loc)) for st in stairs):lamp([*loc,z])

for st in stairs:
    g.group='Stairs/'+st['id'];c.group='Ramps/'+st['id']
    a=np.array(st['start']);d=np.r_[st['dir'],0];t=np.r_[st['side'],0];w=st['width'];z=a[2]
    prof=[(0,0),(5.7,3),(7.5,3),(13.2,6)]
    for fl in range(2):
        offset=0 if fl==0 else 7.5
        for i in range(19):
            cen=a+d*(offset+i*.3+.15)+[0,0,fl*3+(i+1)*.15-.07]
            box(cen,[w,.3,.14],wood,[t,d,[0,0,1]])
    box(a+d*6.6+[0,0,2.9],[w,1.8,.2],wood,[t,d,[0,0,1]])
    for (s0,h0),(s1,h1) in zip(prof,prof[1:]):
        pa=a+d*s0+[0,0,h0];pb=a+d*s1+[0,0,h1]
        # Closed non-convex static ramp mesh; exact 0 m / 6 m joins.
        vv=[pa-t*w/2,pa+t*w/2,pb+t*w/2,pb-t*w/2,pa-t*w/2-[0,0,.30],pa+t*w/2-[0,0,.30],pb+t*w/2-[0,0,.30],pb-t*w/2-[0,0,.30]]
        ff=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
        c.add(vv,ff,'collision')
        for side in [-1,1]:
            p0=pa+t*(w/2+.02)*side;p1=pb+t*(w/2+.02)*side
            g.beam(p0-[0,0,.2],p1-[0,0,.2],.22,dark,.35)
            railing(p0[:2],p1[:2],p0[2],p1[2])
            c.group='Safety/'+st['id']
            # Closed wall prism follows each slope, with 8 m vertical clearance.
            corners=[p0-t*.12,p0+t*.12,p1+t*.12,p1-t*.12]
            vv=[p-[0,0,.35] for p in corners]+[p+[0,0,8] for p in corners]
            ff=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
            c.add(vv,ff,'collision');c.group='Ramps/'+st['id']
            for s in np.arange(s0+.15,s1,.5):
                p=a+d*s+[0,0,h0+(h1-h0)*(s-s0)/(s1-s0)+1]
                p+=t*side*(w/2+.02)
                wallTests.append({'start':(p-t*.5).tolist(),'end':(p+t*.5).tolist()})
    for s in np.linspace(0,13.2,68):
        xy=(a+d*s)[:2];h=stair_height(st,xy);floorTests.append({'position':[*xy,h],'id':st['id']})
    routes.append({'name':st['id'],'points':[st['start'],st['end']],'type':'stair'})

# Eight distinct shops at the authoritative reference centers.
for idx,s in enumerate(layout['shops']):
    g.group='Shops/'+s['id']
    a=math.radians(s['front_deg']);n=np.array([math.cos(a),math.sin(a),0]);t=np.array([n[1],-n[0],0]);up=np.array([0,0,1]);base=np.array([s['x'],s['y'],s['z']]);w=s['width'];dep=s['depth'];axes=[t,n,up]
    def P(x,y,z):return base+t*x+n*y+up*z
    def B(x,y,z,ww,dd,hh,ma,solid=False):
        box(P(x,y,z),(ww,dd,hh),ma,axes)
        if solid:collbox(s['id']+'_solid',P(x,y,z),(ww,dd,hh),axes)
    B(0,-dep/2,1.30,w,.16,2.6,dark,True)
    B(0,-dep/2+.1,1.85,w-.35,.06,1.18,wall)
    for side in [-1,1]:
        B(side*w/2,-.65,1.3,.14,dep-1.30,2.6,wood,True)
        for yy in [-dep/2,dep/2]:B(side*(w/2-.1),yy,1.4,.20,.20,2.8,dark,True)
        for yy in np.arange(-dep/2+.1,dep/2-1.4,.32):B(side*(w/2+.08),yy,1.2,.065,.06,2.25,dark)
    B(0,dep/2,2.64,w+.3,.20,.22,dark)
    B(0,0,2.60,w+.3,.17,.2,dark)
    roof_tiles(g,P,w,dep,tile,dark)
    # Counter leaves an open route around each end.
    B(0,dep/2-.20,.965,w-1.3,.58,.13,lightwood,True)
    B(0,dep/2-.21,.48,w-1.45,.40,.84,wood,True)
    for y in [-dep/2+.5,-dep/2+1.1]:B(0,y,.8,w-1,.45,.10,lightwood)
    for h in [1.40,2.05]:
        B(0,-dep/2+.32,h,w-.8,.45,.08,lightwood)
        for j in range(int(w/.38)-2):bottle(P(-w/2+.65+j*.37,-dep/2+.31,h+.04),j+idx)
    # Warm shoji panel and wood lattice.
    B(-w*.34,-dep/2+.15,1.75,w*.20,.03,.78,window)
    for j in range(5):B(-w*.44+j*w*.05,-dep/2+.19,1.75,.035,.025,.83,dark)
    B(-w*.34,-dep/2+.19,1.75,w*.23,.03,.045,dark)
    noren(g,P,w,dep,cloth[idx],dark)
    sign(P(0,dep/2+.28,2.91),-t,n,min(w-1,4.5),.56,idx)
    for side in [-1,1]:lantern(P(side*(w/2-.38),dep/2+.35,2.16),idx in [0,2,6],1.12)
    lantern(P(0,-.45,2.26),False,1.0)
    # Stool interaction count matches the brief, including eight tea-house seats.
    count=s['seats'];spread=min(w-1.5,(count-1)*.70)
    for j in range(count):
        x=-spread/2+spread*j/(count-1);y=dep/2+.65;pos=P(x,y,0)
        g.cylinder(pos+[0,0,.66],.23,.08,lightwood,32)
        for dx in [-.135,.135]:
            for dy in [-.135,.135]:g.beam(pos+t*dx+n*dy+[0,0,.03],pos+t*dx+n*dy+[0,0,.63],.055,dark)
        stations.append({'name':s['id']+'_Seat_'+str(j+1),'position':(pos+[0,0,.70]).tolist(),'exit':(pos+n*.70+[0,0,.06]).tolist(),'forward':(-n).tolist(),'shop':s['id']})
        bowl(P(x,dep/2-.16,1.045));g.beam(P(x+.20,dep/2-.40,1.05),P(x+.20,dep/2-.15,1.055),.011,lightwood)
    # Shop-specific preparation surfaces and utensils.
    if idx==0:
        B(.9,-.3,.86,1.45,.65,.24,iron);B(.9,-.3,1.005,1.28,.51,.028,red)
        for j in range(7):
            g.beam(P(.30+j*.20,-.65,1.05),P(.30+j*.20,.10,1.05),.025,lightwood)
            for yy in [-.3,-.13]:g.sphere(P(.30+j*.20,yy,1.09),[.08,.065,.055],food,6,4)
        B(.9,-.3,2.15,1.5,.78,.23,iron);B(.9,-.5,3.07,.35,.35,1.65,iron)
    elif idx in [1,2,6]:
        for j in range(3):
            g.cylinder(P((j-1)*.52,-.45,.96),.22,.36,iron,12)
            g.cylinder(P((j-1)*.52,-.45,1.15),.22,.035,ceramic,12)
        for j in range(5):bowl(P(-1,-.9,1.0+j*.035))
    elif idx in [3,5]:
        for j in range(7):bottle(P((j-3)*.35,-.10,.92),j)
    elif idx==4:
        for side in [-1,1]:
            B(side*2.5,.2,.50,1.05,1.2,.10,lightwood)
            g.sphere(P(side*2.5,.2,.67),[.15,.15,.13],ceramic,12,7)
            bowl(P(side*2.5+.30,.2,.56),.08)
    else:
        for j in range(7):g.sphere(P((j-3)*.20,-.1,.99),[.08,.065,.045],food,7,4)
    shop_details(g,P,B,w,dep,idx,M,rng)
    lights.append({'position':P(0,dep/2-.7,2.24).tolist(),'range':5.8,'strength':2.1})
    lights.append({'position':P(0,-dep/2+1.2,2.24).tolist(),'range':4.8,'strength':1.9})
    if idx in [0,1,2,4,6]:steam.append({'position':P(.8 if idx==0 else 0,-.45,1.18).tolist(),'id':s['id']})
    # Side door is navigable; decorations stay off the main lane.
    plant(P(w/2-.3,dep/2+.3,0),.65)
    for xx in np.arange(-w/2,w/2,.9):g.beam(P(xx,-dep/2,-.35),P(xx,dep/2+.9,-.35),.17,dark)

# Arrival sign, practical wayfinding, utilities and benches.
g.group='Wayfinding'
for x in [-2.8,2.8]:box([x,-30,35.6],[.25,.25,3.2],dark)
box([0,-30,37.3],[6.4,.30,.25],dark)
sign([0,-30.18,36.85],[1,0,0],[0,-1,0],4.6,.65,8)
for x in [-2.3,-1.4,1.4,2.3]:lantern([x,-30,36.7],x<0,.85)
for x,y,z,slot in [(19.6,-11.7,40,10),(-11,22.8,46,9),(23,-3,40,4),(-8.3,-27,34,11)]:
    box([x,y,z+1.1],[.10,.10,2.2],dark);sign([x,y-.09,z+1.8],[1,0,0],[0,-1,0],2.0,.34,slot)
g.group='Arrival/Utility'
box([5,-22,35.35],[6,5.4,2.7],wood);collbox('Utility',[5,-22,35.35],[6,5.4,2.7])
box([5,-22,36.8],[6.6,6,.26],tile)
sign([5,-24.74,36.0],[1,0,0],[0,-1,0],3.4,.47,15)
for x in [3.6,5.8]:box([x,-24.73,35.2],[1.1,.06,2.3],dark);box([x,-24.79,35.6],[.76,.02,.8],window)
for p in [[-26,25,52],[32,-4,40],[4,-31,34]]:
    box(np.array(p)+[0,0,.46],[2.7,.55,.13],lightwood)
    for dx in [-1,1]:box(np.array(p)+[dx,0,.22],[.16,.42,.44],dark)
    box(np.array(p)+[0,.23,.86],[2.7,.08,.50],wood)

# Static lift landings use local Udon teleport controls, not a moving physics cabin.
# This avoids motion sickness and keeps floor edges closed during travel.
g.group='Lift'
for dx in [-1.62,1.62]:
    for dy in [-1.62,1.62]:box([-16+dx,-18+dy,23.7],[.27,.27,47.4],dark)
for z in np.arange(3,48,4):
    for side in [-1,1]:
        g.beam([-17.62,-18+side*1.62,z-3],[-14.38,-18+side*1.62,z],.12,iron)
for lev in ['G0','L1','L2','L3']:
    z=levels[lev]
    box([-16,-17.0,z+2.9],[3.7,1.6,.18],tile)
    sign([-16,-16.8,z+2.15],[1,0,0],[0,-1,0],2.45,.44,14)
    lantern([-17.25,-17.7,z+2],False,.75)
    # Floor selection plate is in reach from the middle of the landing.
    for k,dest in enumerate(['G0','L1','L2','L3']):
        if dest==lev:continue
        py=-16.85;px=-17.0+k*.64
        box([px,py,z+1.25],[.53,.12,.45],trim)
        sign([px,py-.073,z+1.25],[1,0,0],[0,-1,0],.50,.23,13-(['G0','L1','L2','L3'].index(dest)))
        teleports.append({'name':lev+'_To_'+dest,'position':[px,py-.15,z+1.25],'size':[.58,.30,.50],'destination':[-16,-18.55,levels[dest]+.08],'forward':[0,-1,0],'label':dest})

# Ancient tree: buttressed, ridged trunk, branching crown and lower supporting limbs.
g.group='Tree/Trunk'
points=[];radii=[]
for z in np.linspace(-1,119,180):
    x=.9*math.sin(z*.075);y=1.5*math.sin(z*.047)
    r=np.interp(z,[-1,0,20,40,60,85,108,119],[13.8,13,9.6,8,6.4,3.8,1.7,.15])
    points.append([x,y,z]);radii.append(r)
g.tube(points,radii,bark,144,.040)
for i in range(11):
    a=i*math.tau/11
    g.tube([[math.cos(a)*5,math.sin(a)*5,13],[math.cos(a)*11,math.sin(a)*11,4],[math.cos(a)*21,math.sin(a)*21,-.8]],[3.6,2.9,.15],bark,12,.06)
branches=[([[4,0,28],[13,1,33],[22,1,36],[34,0,38]],[4.5,3.8,2.5,.65]),([[-3,3,29],[-5,13,37],[-3,24,42],[8,30,44]],[4.6,3.3,2.9,.5]),([[-4,-3,17],[-4,-14,27],[0,-25,31.0],[6,-33,33]],[4.8,3.8,2.5,.5]),([[-5,3,36],[-15,14,44],[-26,22,49],[-32,25,48]],[3.7,2.8,1.8,.18])]
g.group='Tree/SupportingBranches'
for pp,rr in branches:branch(pp,rr,20)
detailed_crown(g,branch,leafs,bark,rng,spraymat)

# A string of lights connects the shops while staying above walking clearance.
g.group='LanternStrings'
for i in range(24):
    a=i*math.tau/24;b=(i+1)*math.tau/24
    if any(st['polygon'].buffer(1).covers(Point(18.7*math.cos(a),18.7*math.sin(a))) for st in stairs):continue
    p0=np.array([18.8*math.cos(a),18.8*math.sin(a),43.1]);p1=np.array([18.8*math.cos(b),18.8*math.sin(b),43.1])
    g.beam(p0-[0,0,3.1],p0,.085,dark)
    mid=(p0+p1)/2-[0,0,.23]
    g.beam(p0,mid,.016,iron);g.beam(mid,p1,.016,iron)
    lantern(mid-[0,0,.2],i%3==0,.67)

# Bracing below the main ring, decks and long branch paths.
g.group='Structure'
for a in np.linspace(0,math.tau,32,endpoint=False):
    n=np.array([math.cos(a),math.sin(a),0]);g.beam(n*9+[0,0,36],n*19.4+[0,0,39.5],.33,dark)
    g.beam(n*15+[0,0,38.2],n*19.4+[0,0,39.5],.16,wood)
for path in layout['paths']:
    z=levels[path['level']]
    for a,b in zip(path['points'],path['points'][1:]):g.beam([*a,z-.6],[*b,z-.6],.34,dark)
for p in layout['platforms']:
    z=levels[p['level']]
    for dx in [-p['width']/2+1,p['width']/2-1]:
        for dy in [-p['depth']/2+1,p['depth']/2-1]:
            top=np.array([p['x']+dx,p['y']+dy,z-.3]);bot=np.array([p['x']+dx*.4,p['y']+dy*.4,z-4]);g.beam(bot,top,.28,dark)

# Forest, distant circular city, snow range and opposite sea are visual-only.
# Ground-to-crown circulation is authored independently of distant landscape.
landscape_stats=landscape(g,M,rng)
landscape_stats.update(add_scenery_detail(g,M,rng))
infrastructure=add_infrastructure(g,M,rng,layout=layout) if FEATURES["infrastructure"] else None
if infrastructure:lights.extend(infrastructure["lights"])
stage=add_noh_stage(g,M,rng) if FEATURES['noh_stage'] else None
if stage:
    solidBoxes.extend(stage['solidBoxes']);floorTests.extend(stage['floorTests'])
    g.group='Stage/Noh/Lighting'
    for side in [-1,1]:
        p=np.array(stage['center'])+np.array(stage['right'])*side*1.1-np.array(stage['front'])*1.55+[0,0,2.96]
        g.beam(p+[0,0,.18],p+[0,0,.56],.012,iron);lantern(p,False,.65)


# A subtle, seamless ambience synthesized from noise; no voices or music.
rate=22050;secs=24;rg=np.random.default_rng(31);tt=np.arange(rate*secs)/rate
freq=np.fft.rfftfreq(len(tt),1/rate);spectrum=(rg.normal(size=len(freq))+1j*rg.normal(size=len(freq)))
spectrum*=np.exp(-freq/1900)/np.maximum(freq,35)**.58;spectrum[0]=0
waveform=np.fft.irfft(spectrum,n=len(tt));waveform/=np.max(np.abs(waveform));waveform*=.12*(.8+.2*np.sin(tt*math.tau/secs))
stereo=np.column_stack([waveform,np.roll(waveform,139)])
with wave.open(str(ASSET/'Audio/CanopyWind.wav'),'wb') as out:
    out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);out.writeframes((stereo*32767).astype('<i2').tobytes())

# Independent floor samples include full route centerlines, spawns and every exit.
for path in layout['paths']:
    ln=LineString(path['points']);z=levels[path['level']]
    for s in np.arange(0,ln.length+.01,.45):
        p=ln.interpolate(s);floorTests.append({'position':[p.x,p.y,z],'id':path['id']})
for a in np.linspace(0,math.tau,240,endpoint=False):floorTests.append({'position':[18*math.cos(a),18*math.sin(a),40],'id':'MainRing'})
spawns=[[-1,-28,34.08],[1,-28,34.08],[-1,-26.4,34.08],[1,-26.4,34.08]]
for p in spawns:floorTests.append({'position':[p[0],p[1],34],'id':'Spawn'})

# Ground stays fixed; near-world decks, colliders and interaction positions lift together.
# New circulation is independently regenerated rather than vertically stretching treads.
altitude_report=apply_altitude_profile(g,c,dict(levels=levels,stairs=stairs,spawns=spawns,
    lights=lights,steam=steam,stations=stations,teleports=teleports,solidBoxes=solidBoxes,
    floorTests=floorTests,wallTests=wallTests,guards=guards,routes=routes,
    infrastructure=infrastructure,stage=stage))
crown=add_crown_stairs(g,c,M,rng) if FEATURES['crown_stairs'] else None
if crown:
    lights.extend(crown['lights']);floorTests.extend(crown['floorTests']);wallTests.extend(crown['wallTests']);routes.extend(crown['routes'])
    # Close the independently measured 0.144m diagonal guard seam at the
    # L4/outer-bridge corner. Overlap both solids; retain the walking corridor.
    a=np.array([-28.4237422943,26.1380939484,152.])
    b=np.array([-28.2810096741,26.1200008392,152.])
    d=b-a;length=np.linalg.norm(d);d/=length;n=np.array([-d[1],d[0],0.])
    center=(a+b)/2
    c.group='Safety/Crown/LookoutCornerClosure'
    c.box(center+[0,0,3.825],[length+.26,.24,8.35],'collision',[d,n,[0,0,1]])
    joint={'name':'L4_CrownLookoutGuardCorner','position':center.tolist(),'measuredOriginalGap':float(length),'overlapEachEnd':.13,'thickness':.24,'base':151.65,'top':160.}
    crown['cornerClosure']=joint
    wallTests.append({'start':(center+n*.6+[0,0,1]).tolist(),'end':(center-n*.6+[0,0,1]).tolist()})
boosters=add_booster_pumps(g,M,infrastructure)
clouds=add_cloud_sea(g,M,rng)

print('Writing geometry...',flush=True)
g.compact();normal_uv_repairs=g.repair_normal_uvs();g.bake_mood(lights);c.compact()
g.save_binary(DATA/'VisualMeshes.bytes');c.save_binary(DATA/'CollisionMeshes.bytes')
g.save_glb(SOURCE/'TreeTopYokocho.glb',TEX)
# Gzip is authoring transport only; the scene uses generated native Unity meshes.
import gzip
for source in [DATA/'VisualMeshes.bytes', DATA/'CollisionMeshes.bytes']:
    with open(source,'rb') as input_file, gzip.GzipFile(str(source)+'.gz','wb',compresslevel=9,mtime=0) as output_file:
        shutil.copyfileobj(input_file,output_file)
manifest={'version':VERSION,'features':FEATURES,'title':'樹上横丁','coordinates':'X=east Y=north Z=up; Unity=(x,z,y)','materials':list(g.materials.values()),'spawns':[{'position':p} for p in spawns],'lights':lights,'steam':steam,'stations':stations,'teleports':teleports,'solidBoxes':solidBoxes,'floorTests':floorTests,'wallTests':wallTests,'guards':guards,'safetyHeight':8.0,'safetyThickness':.24,'respawnHeight':-8,'floors':[{ 'level':k,'z':levels[k],'wkt':v.wkt} for k,v in floors.items()],'stairs':[{k:v for k,v in st.items() if k!='polygon'} for st in stairs], 'visualMeshCount':len(g.batches),'visualTriangles':sum(len(b['f']) for b in g.batches.values()),'collisionMeshCount':len(c.batches),'collisionTriangles':sum(len(b['f']) for b in c.batches.values()),'altitudeProfile':altitude_report,'cloudSea':clouds,'boosterPumps':boosters,'nohStage':stage,'crownStairs':crown,'infrastructure':infrastructure,'detail':landscape_stats,'navigationPaths':[dict(path,z=levels[path['level']]) for path in layout['paths']],'normalUvRepairs':normal_uv_repairs,'pbrScanSets':4,'albedoResolution':2048,'testedInUnity':False,'testedInVRChat':False}
(DATA/'WorldManifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'),default=lambda x: x.item() if isinstance(x,np.generic) else (_ for _ in ()).throw(TypeError(type(x).__name__))),encoding='utf8')
(ROOT/'Docs/build_stats.json').write_text(json.dumps({k:manifest[k] for k in ['version','visualMeshCount','visualTriangles','collisionMeshCount','collisionTriangles','safetyHeight','safetyThickness','testedInUnity','testedInVRChat']},indent=2),encoding='utf8')
print(json.dumps({'visualMeshes':len(g.batches),'triangles':manifest['visualTriangles'],'stations':len(stations),'teleportControls':len(teleports),'safetySegments':len(guards),'floorSamples':len(floorTests)},indent=2),flush=True)
