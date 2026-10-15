#!/usr/bin/env python3
"""Original deterministic periodic material synthesis, written for TreeTopYokocho.

No source photographs, image textures, scans, generated images, external asset
packs, or downloads are read. All maps are co-authored from analytic fields and
seeded random numbers. Image APIs only encode the newly synthesised arrays.
Coordinates are a torus: period 1 in U and V. No edge blending, mirrored borders,
forced border copies or painted lighting. See authored_pbr_origin.json.
"""
from pathlib import Path
import argparse, hashlib, json, math, platform
import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw

TAU=2*np.pi
ROOT=Path(__file__).resolve().parents[1]
N=2048
Y,X=np.mgrid[:N,:N].astype(np.float32)/N


def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def wrap_delta(x,c): return (x-c+.5)%1-.5

def noise(seed,fx,fy=None,x=None,y=None):
    """Cubic random field on a periodic grid; band limits set independently."""
    fy=fx if fy is None else fy
    r=np.random.default_rng(seed)
    lattice=r.uniform(-1,1,(fy,fx)).astype(np.float32)
    if x is None:x=X
    if y is None:y=Y
    return map_coordinates(lattice, np.array([y*fy,x*fx]),order=3,mode='grid-wrap',prefilter=True).astype(np.float32)

def fbm(seed,fx,fy=None,octaves=5,gain=.52):
    fy=fx if fy is None else fy
    out=np.zeros_like(X);amp=1.;total=0
    for i in range(octaves):
        out+=noise(seed+i*83,fx*2**i,fy*2**i)*amp;total+=amp;amp*=gain
    return out/total

def voronoi(seed,nx,ny,warp=.012):
    """Distance-to-edge and random plate identity on an anisotropic torus."""
    rng=np.random.default_rng(seed)
    aspect=ny/nx
    pts=[]
    for j in range(ny):
        for i in range(nx):pts.append(((i+rng.uniform(.12,.88))/nx,(j+rng.uniform(.10,.90))/ny*aspect))
    pts=np.asarray(pts)
    xx=(X+warp*fbm(seed+31,8,6,3)+.0025*fbm(seed+34,70,43,3))%1
    yy=(Y+warp*fbm(seed+43,9,7,3)+.003*fbm(seed+47,55,47,3))%1
    q=np.stack((xx.ravel(),yy.ravel()*aspect),axis=-1)
    tree=cKDTree(pts,boxsize=[1,aspect])
    ds,ix=tree.query(q,k=2,workers=4)
    edge=(ds[:,1]-ds[:,0]).reshape(N,N).astype(np.float32)
    cell=ix[:,0].reshape(N,N)
    value=rng.uniform(-1,1,len(pts)).astype(np.float32)[cell]
    return edge,value

def bark():
    """Authored long vertical fissures and fibrous cortex on a periodic torus."""
    seed=220301;rng=np.random.default_rng(seed)
    macro=fbm(seed,7,5,4)
    # Irregular but strictly positive ribbon widths. Integer winding closes U.
    count=47
    widths=np.exp(rng.normal(0,.43,count));widths/=widths.sum()
    edges=np.r_[0,np.cumsum(widths)];edges[-1]=1
    u=(X+.009*noise(seed+11,5,3)+.0045*noise(seed+13,41,9)+.0015*fbm(seed+17,140,59,3))%1
    # Branch-scar flow deflects the same field used by every longitudinal detail.
    knots=[(.21,.32,.019,.055),(.72,.76,.012,.034),(.86,.16,.008,.026)]
    scar=np.zeros_like(X);scar_ring=np.zeros_like(X)
    for j,(cx,cy,rx,ry) in enumerate(knots):
        dx=wrap_delta(X,cx);dy=wrap_delta(Y,cy)
        r=np.sqrt((dx/rx)**2+(dy/ry)**2+1e-6)
        fall=1-smoothstep(2.,6.,r)
        u+=.030*np.tanh(dx/(rx*.9))*np.exp(-r*.48)*fall
        scar=np.maximum(scar,np.exp(-(r/.8)**3))
        ring=(.5+.5*np.cos(r*TAU*2+noise(seed+801+j,38,36)*1.4))**7
        scar_ring+=ring*np.exp(-r*.65)*fall
    u%=1
    phase=np.interp(u,edges,np.arange(count+1)).astype(np.float32)
    index=np.minimum(np.floor(phase).astype(int),count-1);f=phase-index
    distance=np.minimum(f,1-f)*widths[index]
    aperture=.0006+.0010*(.5+.5*noise(seed+21,61,9,x=u,y=Y))**2
    continuity=.20+.80*smoothstep(-.30,.40,noise(seed+27,53,7,x=u,y=Y))
    cleft=np.exp(-(distance/aperture)**1.35)*continuity
    shoulder=1-np.exp(-distance/.0019)
    fiber=noise(seed+31,370,18,x=u,y=Y)
    finefiber=noise(seed+41,850,95,x=u,y=Y)
    micro=fbm(seed+51,620,440,3)
    medium=noise(seed+53,168,36,x=u,y=Y)
    medsplit=smoothstep(.26,.65,-medium)
    # Broken secondary long splits run inside outer cortex, never pore noise.
    secondary=np.exp(-((f-.47-.05*noise(seed+59,31,5))/.018)**2)
    secondary*=smoothstep(.05,.55,noise(seed+61,51,8,x=u,y=Y))
    # Occasional cross scission terminates individual strips, with independent
    # phase per strip and sparse support. It cannot become a global brick grid.
    offsets=rng.random(count).astype(np.float32)[index]
    t=(Y*9+offsets+.13*noise(seed+71,47,15,x=u,y=Y))%1
    cross=np.exp(-((t-.5)/.020)**2)
    cross*=smoothstep(.33,.68,noise(seed+73,51,13,x=u,y=Y))*smoothstep(.1,.35,f)*(1-smoothstep(.65,.9,f))
    plate=rng.uniform(-1,1,count).astype(np.float32)[index]
    h=.57-.31*(1-shoulder)*continuity+.034*plate*shoulder+.038*fiber+.017*finefiber+.025*micro+.080*medium-.057*medsplit
    h-=.095*cleft+.085*secondary+.060*cross+.10*scar+.065*scar_ring
    h+=.020*np.sin(f*np.pi)*noise(seed+81,47,12,x=u,y=Y)
    pigment=.355+.018*macro+.020*plate*shoulder+.032*fiber+.020*finefiber+.029*micro+.054*medium-.048*medsplit
    pigment-=.175*cleft+.095*secondary+.047*cross+.10*scar+.045*scar_ring
    rgb=pigment[...,None]*np.array([1.105,1.005,.855],np.float32)
    ochre=smoothstep(.10,.51,fbm(seed+111,20,15,4))
    rgb+=ochre[...,None]*np.array([.025,.008,-.010],np.float32)
    moss=smoothstep(.18,.52,fbm(seed+141,11,16,5)+.14*fiber)*.33
    rgb=rgb*(1-moss[...,None])+np.array([.255,.295,.15],np.float32)*moss[...,None]
    lichen=smoothstep(.33,.65,fbm(seed+171,28,31,5)+.20*micro)*.18
    rgb=rgb*(1-lichen[...,None])+np.array([.46,.47,.395],np.float32)*lichen[...,None]
    # Torn mature-cortex scales occupy part of the long ridges. Pigment
    # contrast is restrained; sharp broken shoulders carry the structure.
    rng=np.random.default_rng(seed+701)
    for i in range(820):
        cx,cy=rng.random(2);rx=rng.uniform(.0035,.011);ry=rng.uniform(.016,.065)
        ix=np.arange(math.floor((cx-rx*1.6)*N),math.ceil((cx+rx*1.6)*N))
        iy=np.arange(math.floor((cy-ry*1.4)*N),math.ceil((cy+ry*1.4)*N))
        xx=(ix[None,:]/N-cx)/rx;yy=(iy[:,None]/N-cy)/ry;q=np.ix_(iy%N,ix%N)
        phase0=rng.uniform(0,TAU)
        center=.18*yy+.11*np.sin(3*yy+phase0)
        left=-.78+.12*np.sin(7*yy+phase0)+.05*np.sin(19*yy-phase0)
        right=.80+.11*np.sin(5*yy-phase0)+.05*np.sin(17*yy+phase0)
        for j in range(3):
            cut=rng.uniform(.08,.32)*np.exp(-((yy-rng.uniform(-.8,.8))/rng.uniform(.07,.19))**4)
            if j%2:left+=cut
            else:right-=cut
        uu=xx-center
        end=1-np.abs(yy+.13*np.sin(3*uu+phase0)+.025*micro[q])
        edge=np.minimum(np.minimum(uu-left,right-uu),end*.8)
        mask=smoothstep(-.015,.055,edge)*(.35+.65*shoulder[q])
        relief=rng.uniform(.070,.150)*(.45+.55*smoothstep(-1,1,yy))
        h[q]+=mask*relief
        broken=np.exp(-((edge-.045)/.035)**2)*mask
        pv=rng.uniform(-.008,.065)*mask-.050*broken
        rgb[q]+=pv[...,None]*np.array([1.08,.99,.83],np.float32)
    rough=.86+.040*fiber+.025*micro+.025*cleft
    ao=1-.18*cleft-.060*secondary-.040*cross-.036*scar_ring
    return rgb,h,rough,ao,dict(seed=seed,physicalTileMeters=[2.78,2.78],heightRangeMeters=.022,normalStrength=1,parallaxRecommendation=.008,description='Original longitudinal fibrous bark, with 47 irregular-width long cortex ribbons, narrow vertical fissures, sparse secondary splitting, occasional independently staggered transverse scission and rugged fibrous cortex shoulders, broken mature cortex laminae, branch-scar flow and quiet lichen. Explicit directional anatomy instead of porous or cellular noise. No source imagery, painted lighting, or baked scene shading.')


def wood(fine=False):
    seed=220307 if fine else 220303
    # All boards share unbroken material, rather than baking construction
    # seams or screw heads into a map used on beams and geometry-cut boards.
    macro=fbm(seed,4,3,4)
    drift=fbm(seed+43,9,5,4)
    u=X+.009*drift+.0025*noise(seed+8,4,12)
    knot_core=np.zeros_like(X);knot_rings=np.zeros_like(X)
    # Small varied branch knots bend nearby long grain. Explicit compact
    # support avoids discontinuities at the periodic shortest-distance cut.
    knots=[(.22,.29,.010,.038),(.71,.76,.006,.029)] if fine else [(.24,.27,.017,.063),(.72,.73,.010,.047),(.08,.66,.004,.040),(.93,.47,.004,.030)]
    for i,(cx,cy,rx,ry) in enumerate(knots):
        dx=wrap_delta(X,cx);dy=wrap_delta(Y,cy)
        r=np.sqrt((dx/rx)**2+(dy/ry)**2+1e-6)
        fall=1-smoothstep(1.6,6.,r)
        u+=.032*np.tanh(dx/(rx*.7))*np.exp(-r*.45)*fall
        core=np.exp(-(r/.74)**3)
        ring=(.5+.5*np.cos(r*TAU*2.2+noise(seed+301+i,20,20)*1.1))**9
        knot_core=np.maximum(knot_core,core)
        knot_rings+=ring*np.exp(-r*.8)*(1-smoothstep(.65,1.25,r))
    # Nonuniform earlywood/latewood growth boundaries and interleaved pores.
    growth=noise(seed+151,70 if fine else 85,3,x=u%1,y=Y)
    # Positive, varied annual-ring widths produce a monotone periodic growth
    # phase. Integer winding preserves the seam; all grain shares knot warp.
    widths=np.exp(gaussian_filter(np.random.default_rng(seed+155).normal(0,.85,1024),2.,mode='wrap'))
    phase=np.r_[0,np.cumsum(widths)];phase*=110/phase[-1]
    growth_coord=(np.interp((u%1)*1024,np.arange(1025),phase)/110).astype(np.float32)
    ringphase=TAU*(growth_coord*110+.60*noise(seed+153,19,3,x=u%1,y=Y))
    latewood=(.5+.5*np.sin(ringphase))**9
    annual=.48*smoothstep(.05,.68,-growth)+.52*latewood
    fiber=noise(seed+162,670 if fine else 760,30 if fine else 52,x=(u+.001*drift)%1,y=Y)
    darkfiber=smoothstep(.24,.78,-fiber)
    finefiber=noise(seed+163,1100,130,x=u%1,y=Y)
    pore=noise(seed+173,900,170 if fine else 90,x=u%1,y=Y)
    pores=smoothstep(.30,.76,-pore)
    weather=.7*noise(seed+196,77,8,x=u%1,y=Y)+.3*fbm(seed+199,31,19,3)
    # Thin longitudinal checks with interrupted ends, never thick black lines.
    split=np.exp(-((noise(seed+207,94,5,x=u%1,y=Y)-.44)/.027)**2)
    split*=smoothstep(.10,.55,noise(seed+218,42,27))
    if fine:
        v=.405+.050*macro-.092*annual-.030*darkfiber+.012*finefiber-.013*pores-.085*knot_core-.025*knot_rings
        rgb=v[...,None]*np.array([1.17,.88,.62],np.float32)
        rgb+=weather[...,None]*np.array([.008,.006,.003],np.float32)
        h=.54-.070*annual-.041*darkfiber-.018*pores-.07*knot_core-.025*knot_rings+.014*weather-.055*split
        rough=.49+.043*annual+.026*weather+.028*pores+.030*knot_core
        ao=1-.035*pores-.04*knot_core-.02*split
        physical=1.333;hr=.0013;par=.0006
    else:
        silver=smoothstep(-.05,.43,weather+.25*macro)
        v=.365+.050*macro-.094*annual-.060*darkfiber+.020*finefiber-.026*pores-.130*knot_core-.065*knot_rings-.056*split
        rgb=v[...,None]*np.array([1.055,1.014,.938],np.float32)
        rgb+=silver[...,None]*np.array([.034,.039,.045],np.float32)
        tannin=smoothstep(.18,.52,fbm(seed+391,19,13,5))
        rgb-=tannin[...,None]*np.array([.048,.050,.046],np.float32)
        bleached=smoothstep(.10,.54,noise(seed+399,55,9))
        rgb+=bleached[...,None]*np.array([.030,.032,.034],np.float32)
        h=.52-.12*annual-.068*darkfiber-.030*pores-.16*knot_core-.07*knot_rings+.022*weather-.13*split
        rough=.78+.05*annual+.045*weather+.045*pores+.025*silver
        ao=1-.055*pores-.055*knot_core-.045*split
        physical=1.538;hr=.0034;par=.0018
    return rgb,h,rough,ao,dict(seed=seed,physicalTileMeters=[physical,physical],heightRangeMeters=hr,normalStrength=1,parallaxRecommendation=par,description=('Fine oiled counter timber' if fine else 'Silver-weathered structural timber')+' with nonuniform annual growth, grain deflected around branch knots, capillary pores and restrained longitudinal checking. No baked plank gaps, nails or directional shading.')


def rock():
    seed=220311
    macro=fbm(seed,5,5,6)
    med=fbm(seed+32,27,29,5)
    fine=fbm(seed+73,180,197,4)
    micro=fbm(seed+89,590,620,3)
    edge,cell=voronoi(seed+111,17,15,.031)
    fissure=np.exp(-(edge/.00065)**1.15)
    shoulder=1-np.exp(-edge/.0023)
    # Irregular short mineral laminae. No brick grid or large rubble silhouettes.
    y=(Y+.055*fbm(seed+180,6,5,4)+.015*med)%1
    layers=noise(seed+191,19,190,x=X,y=y)
    strata=smoothstep(.08,.60,layers)
    grit=smoothstep(.29,.73,-fine)
    crystal=smoothstep(.26,.70,micro+.32*fine)
    h=.44+.13*macro+.075*med+.043*fine+.018*micro+.026*strata
    h+=.075*shoulder+.025*cell-.025*grit
    v=.310+.030*macro+.028*med+.028*fine+.018*micro+.018*cell
    v-=.038*fissure;v+=.012*strata+.017*crystal
    rgb=v[...,None]*np.array([1.0,1.03,.89],np.float32)
    oxide=smoothstep(.12,.54,fbm(seed+239,16,19,5)+.16*fine)
    rgb+=oxide[...,None]*np.array([.025,.009,-.012],np.float32)
    quartz=smoothstep(.18,.58,fbm(seed+311,47,61,4)+.25*micro)
    rgb+=quartz[...,None]*np.array([.019,.018,.016],np.float32)
    rough=.845+.052*med+.036*grit+.022*fissure-.035*crystal
    ao=1-.115*fissure-.040*grit
    # This family is also the original world terrain and canopy microtexture.
    # A subdued moss-covered stone surface preserves that existing ecological
    # role without changing material tints, scale, geometry or any old pixels.
    mossmask=smoothstep(-.24,.07,fbm(seed+411,5,6,5)+.18*med+.12*fine)
    mosspig=np.array([.287,.313,.197],np.float32)[None,None,:]*(1+.055*macro[...,None]+.070*fine[...,None]+.045*micro[...,None])
    mossbrown=smoothstep(.20,.58,fbm(seed+431,20,17,4))
    mosspig+=mossbrown[...,None]*np.array([.022,-.008,-.004],np.float32)
    rgb=rgb*(1-mossmask[...,None])+mosspig*mossmask[...,None]
    h+=mossmask*(.034+.013*fine)
    rough=rough*(1-mossmask)+(.925+.025*fine)*mossmask
    ao=ao*(1-.45*mossmask)+(1-.032*grit)*(.45*mossmask)
    return rgb,h,rough,ao,dict(seed=seed,physicalTileMeters=[1.538,1.538],heightRangeMeters=.019,normalStrength=1,parallaxRecommendation=.006,description='Original moss-covered weathered mineral rock with rough multiscale fractured stone, short mineral laminae, granular quartz, muted iron-oxide pigment and ecological moss cover for the existing shared terrain/canopy uses. No image input, scene lighting or built-in rubble silhouettes.')

FAMILIES={'yokocho_bark':bark,'yokocho_weathered_timber':wood,'yokocho_counter_timber':lambda:wood(True),'yokocho_mineral_rock':rock}
OLD=['bark_brown_02','wood_planks_grey','wood_table_001','rocky_terrain_02']

def down(a):
    # Exactly two-by-two area averaging: no image library filtering can create
    # a nonperiodic edge. All channels use the same 2K latent material field.
    return a.reshape(N//2,2,N//2,2,*a.shape[2:]).mean((1,3))

def seam_stats(a):
    if a.ndim==2:a=a[...,None]
    # A periodic sampled signal has a one-pixel step across the boundary, not
    # necessarily duplicate edge pixels. Compare to identical interior steps.
    out={}
    for axis,label in [(1,'U'),(0,'V')]:
        grad=np.abs(np.diff(a,axis=axis));seam=np.abs(np.take(a,0,axis=axis)-np.take(a,-1,axis=axis))
        mean=float(grad.mean());sm=float(seam.mean())
        out[label]={'wrapStepMean':sm,'interiorStepMean':mean,'ratio':sm/max(mean,1e-12),'wrapStepP99':float(np.percentile(seam,99)),'interiorStepP99':float(np.percentile(grad,99))}
    return out

def normal_from_height(h,meta):
    dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))*meta['heightRangeMeters']*len(h)/(2*meta['physicalTileMeters'][0])
    dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))*meta['heightRangeMeters']*len(h)/(2*meta['physicalTileMeters'][1])
    # Pixel row increases down, UV V increases up: OpenGL tangent-space +Y
    # is therefore +dH/d(image-row), while +X is -dH/d(image-column).
    n=np.stack((-dx,dy,np.ones_like(h)),axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n

def save_png(path,a,bits=8):
    path.parent.mkdir(parents=True,exist_ok=True)
    if bits==16:im=Image.fromarray(np.uint16(np.clip(a,0,1)*65535+.5))
    else:im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5))
    im.save(path,compress_level=9)
    return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'resolution':list(im.size),'bitsPerChannel':bits,'mode':im.mode}

def generate(name):
    rgb,h,rough,ao,meta=FAMILIES[name]()
    assert all(np.isfinite(x).all() for x in (rgb,h,rough,ao))
    rgb=np.clip(rgb,0,1);h=np.clip(h,0,1);rough=np.clip(rough,.04,1);ao=np.clip(ao,0,1)
    h=down(h);n=normal_from_height(h,meta)
    arm=np.stack((down(ao),down(rough),np.zeros_like(h)),axis=-1)
    arrays={'albedo':rgb,'normalGL':n*.5+.5,'arm':arm,'height':h}
    maps={}
    for channel,a in arrays.items():
        maps[channel]=save_png(ROOT/'Assets/TreeTopYokochoOriginalPbr/Textures/PBR'/f'{name}_{channel}.png',a,16 if channel=='height' else 8)
        maps[channel]['colorSpace']='sRGB' if channel=='albedo' else 'Linear'
        maps[channel]['bounds']=[float(a.min()),float(a.max())]
        maps[channel]['seam']=seam_stats(a)
    out={'family':name,**meta,'maps':maps,'roughnessRange':[float(arm[:,:,1].min()),float(arm[:,:,1].max())],'ambientOcclusionRange':[float(arm[:,:,0].min()),float(arm[:,:,0].max())],'metallicAllZero':bool((arm[:,:,2]==0).all()),'normalLengthMaxError':float(np.abs(np.linalg.norm(n,axis=-1)-1).max()),'normalZMinimum':float(n[:,:,2].min()),'albedoMeanSRGB':rgb.mean((0,1)).tolist(),'effectiveHeightSpanMeters':float((h.max()-h.min())*meta['heightRangeMeters'])}
    # Contact sheet of original output arrays, not an edited source image.
    panel=Image.new('RGB',(1536,1080),(24,26,28));d=ImageDraw.Draw(panel)
    for i,(channel,a) in enumerate(arrays.items()):
        if a.ndim==2:a=np.repeat(a[...,None],3,axis=-1)
        im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).resize((512,512),Image.Resampling.LANCZOS)
        xy=((i%3)*512,(i//3)*540+28);panel.paste(im,xy);d.text((xy[0]+10,xy[1]-20),f'{name}: {channel}',fill=(230,230,230))
    # Neutral directional illumination exists ONLY in this labelled preview,
    # never in the albedo export, and demonstrates coupled normal/height detail.
    l=np.array([.45,.55,.71]);l/=np.linalg.norm(l)
    shade=.38+.62*np.maximum(0,(n*l).sum(-1));lit=np.clip(down(rgb)*shade[...,None],0,1)
    im=Image.fromarray(np.uint8(lit*255+.5)).resize((512,512),Image.Resampling.LANCZOS)
    panel.paste(im,(512,568));d.text((522,548),'Relief preview ONLY: side light',fill=(230,230,230))
    small=Image.fromarray(np.uint8(rgb*255+.5)).resize((256,256),Image.Resampling.LANCZOS)
    for yy in range(2):
        for xx in range(2):panel.paste(small,(1024+xx*256,568+yy*256))
    d.text((1034,548),'2 x 2 unlit tiling preview',fill=(230,230,230))
    panel.save(ROOT/'Preview'/f'{name}_contact.png')
    (ROOT/'Docs'/f'{name}_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'family':name,'mean':out['albedoMeanSRGB'],'roughness':out['roughnessRange'],'heightSpan':out['effectiveHeightSpanMeters'],'normalZmin':out['normalZMinimum']}),flush=True)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--families',nargs='+',choices=list(FAMILIES),default=list(FAMILIES));a=p.parse_args()
    for n in a.families:generate(n)
    found=[]
    for n in FAMILIES:
        p=ROOT/'Docs'/f'{n}_validation.json'
        if p.exists():found.append(json.loads(p.read_text()))
    manifest={'schema':1,'status':'Procedural source maps; art acceptance recorded separately; not Unity runtime validated','authoring':'Original project-specific procedural synthesis authored for the user','externalInputs':[],'downloads':[],'imageModelUsed':False,'sourcePath':'Source/author_seamless_pbr.py','sourceSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'periodicMethod':'Toroidal cubic random fields, periodic anisotropic cellular distance fields, compact knot warps, wrapped finite-difference normals. No edge blending or duplicated border pixels.','channelContract':{'albedo':'RGB sRGB pigment only; no baked directional light or AO','normalGL':'RGB linear tangent normal, +Y OpenGL, blue positive; wrap derivatives from same height','arm':'RGB linear R=ambient occlusion, G=perceptual roughness, B=metallic=0','height':'16-bit grayscale linear; same latent field used for normals; midpoint neutral'},'dependencies':{'python':platform.python_version(),'numpy':np.__version__,'scipy':__import__('scipy').__version__,'Pillow':__import__('PIL').__version__},'replacementMapping':{old:{'albedo':f'PBR/{new}_albedo.png','normal':f'PBR/{new}_normalGL.png','arm':f'PBR/{new}_arm.png','height':f'PBR/{new}_height.png'} for old,new in zip(OLD,FAMILIES)},'families':found}
    (ROOT/'Docs/authored_pbr_origin.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
