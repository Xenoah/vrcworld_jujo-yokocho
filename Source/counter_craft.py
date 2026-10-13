"""Hand-crafted near-view restaurant props for the eight TreeTop Yokocho shops.

The public API is ``add_counter_craft(g, P, B, w, dep, idx, M, rng)``.
Coordinates are shop-local Z-up, before the world's +100 m altitude transform.
This module creates visual geometry only. It never writes collision/navigation.

Call ``counter_craft_textures(texture_dir)`` once before exporting a world. The
three original 1024 x 512 atlases are shared by every surface in every shop.
The geometry is deterministic per shop and does not consume the world's rng.

Replacement integration (do not layer this over the old generic props):
* build_world.py: keep shelf boards but skip their bottle(...) inner loop;
  skip bowl(...) and its chopstick in the stool loop; replace the whole old
  'Shop-specific preparation surfaces and utensils' block. Retain S01's hood
  and chimney and S05's two low tables, as documented by retained_furniture().
* high_detail.shop_details: skip the shelf-label loop; the counter-place-
  settings loop; the 'Clay dishes, cutting boards ...' block; and the final
  bamboo-holder block. Retain all architecture, cupboards, sink and lights.
* The old six generic hanging utensils may remain; these props do not overlap.

No fonts, external scans, or third-party image assets are embedded here.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image

TAU = math.tau
ATLAS_NAME = 'counter_craft'
COLS, ROWS, CELL = 8, 4, 128
# Individual original painted surfaces in the shared atlas.
IVORY, INDIGO, TENMOKU, CHARCOAL, CHICKEN, NOODLE, BROTH, EGG = range(8)
MATCHA, BAMBOO, LACQUER, NORI, PORK, DAIKON, LINEN, CLAY = range(8, 16)
PINK, DANGO, LEAF_GREEN, YOLK, SAUCE, FISHCAKE, KONJAC, TOFU = range(16, 24)
GLASS_GREEN, GLASS_AMBER, CERAMIC_BLUE, TEA, SWEET_RED, CHESTNUT, MUSHROOM, SESAME = range(24, 32)


def counter_craft_textures(out):
    """Paint a compact, wrap-friendly atlas and physically restrained PBR maps.

    Labels stay in the existing Japanese menus atlas, not in this texture.
    The ARM values carry local roughness, so glazed clay, broth, ash, paper,
    bamboo and food can share a single material without a plastic response.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(812703)
    palettes = [
        (214, 215, 195), (48, 67, 68), (118, 79, 41), (38, 35, 29),
        (148, 102, 59), (218, 185, 119), (119, 77, 29), (223, 216, 189),
        (89, 119, 45), (175, 148, 85), (67, 37, 25), (40, 49, 25),
        (163, 113, 86), (211, 206, 165), (190, 189, 167), (138, 85, 47),
        (191, 135, 123), (220, 211, 177), (94, 129, 44), (214, 153, 33),
        (70, 38, 16), (208, 184, 155), (92, 85, 68), (219, 211, 174),
        (40, 64, 37), (101, 62, 25), (94, 127, 135), (74, 68, 21),
        (95, 50, 34), (160, 117, 48), (106, 79, 48), (221, 198, 138),
    ]
    roughness = [.53, .50, .55, .97, .66, .74, .36, .75,
                 .66, .83, .44, .94, .72, .72, .95, .78,
                 .76, .77, .88, .69, .29, .82, .90, .89,
                 .32, .33, .54, .28, .51, .78, .91, .90]
    base = np.zeros((ROWS*CELL, COLS*CELL, 3), dtype=np.float32)
    heights = np.zeros((ROWS*CELL, COLS*CELL), dtype=np.float32)
    arm = np.zeros_like(base)
    y, x = np.mgrid[:CELL, :CELL] / CELL
    for slot, color in enumerate(palettes):
        # u-periodic mottling avoids the obvious vertical seam on turned pots.
        noise = rng.normal(0, 1, (CELL, CELL))
        waves = np.sin(x*TAU*7 + np.sin(y*TAU*3))*np.cos(y*TAU*5)
        broad = np.sin(x*TAU*3+.5*np.sin(y*TAU*2))*.5 + np.sin(y*TAU*4)*.3
        value = 1 + noise*.026 + waves*.025 + broad*.045
        h = noise*.012 + waves*.017
        a = np.asarray(color, dtype=float)[None, None, :] * value[:, :, None]
        if slot in [IVORY, INDIGO, TENMOKU, CERAMIC_BLUE, CLAY]:
            # Fired iron flecks, potter's turning lines and uneven dipped glaze.
            specks = rng.random((CELL, CELL)) < .018
            a[specks] *= rng.uniform(.32, .68, (specks.sum(), 1))
            h += specks*.025 + np.sin(y*TAU*23)*.010
            drip = y < (.13 + .07*np.sin(x*TAU*3) + .045*np.sin(x*TAU*11))
            if slot in [INDIGO, TENMOKU]:
                a[drip] = a[drip]*.52 + np.array([101, 74, 45])*.48
            if slot == IVORY:
                ink = ((np.abs(y-.14-.007*np.sin(x*TAU*5)) < .011) |
                       (np.abs(y-.81-.009*np.sin(x*TAU*9)) < .009))
                a[ink] = np.array([52, 77, 97])
                for k in range(7):
                    brush = ((x-(k+.45)/7)**2/(.028**2) +
                             (y-.63-.015*np.sin(x*TAU*7))**2/(.072**2)) < 1
                    a[brush] = np.array([63, 84, 101]) * (1+.11*waves[brush, None])
        elif slot == CHARCOAL:
            h += np.sin(x*TAU*8 + np.sin(y*TAU*4)*1.3)*.11
            cracks = np.abs(np.sin(x*TAU*6 + np.sin(y*TAU*3)*1.6)) < .13
            a[cracks] *= .38
            ash = (waves+broad > .97)
            a[ash] = np.array([79, 77, 67]) * value[ash, None]
        elif slot == CHICKEN:
            # Broad uneven caramelisation; regular dark spots read as a
            # printed pattern rather than cooked skin in a close render.
            field=np.zeros_like(x)
            for ku,kv,amp in [(1,2,1),(2,1,.7),(3,4,.45),(5,3,.25),(7,6,.13)]:
                field+=amp*np.sin(x*TAU*ku+rng.uniform(0,TAU))*np.cos(y*TAU*kv+rng.uniform(0,TAU))
            field=(field-field.min())/max(np.ptp(field),1e-8)
            char=np.clip((field-.43)/.57,0,1)**1.7
            a *= (1-char[:, :, None]*.80)
            h += field*.021+noise*.004
        elif slot == BAMBOO:
            grain = np.sin(x*TAU*31 + np.sin(y*TAU*2)*.24)
            a *= (1+grain[:, :, None]*.09)
            h += grain*.018
        elif slot == LACQUER:
            a *= (1+.08*np.sin(x*TAU*5+y*TAU*2))[:, :, None]
            h += .006*np.sin(x*TAU*37+y*TAU*8)
        elif slot == BROTH:
            # Rendered oil droplets, not a field of shiny geometrical marbles.
            for _ in range(35):
                cx, cy = rng.random(2); rr = rng.uniform(.009, .032)
                circle = np.abs(np.sqrt((x-cx)**2+(y-cy)**2)-rr) < .0028
                a[circle] = (159, 105, 37)
                h[circle] += .013
        elif slot == NORI:
            h += np.sin(x*TAU*17+np.sin(y*TAU*5))*np.sin(y*TAU*19)*.085
            a *= (1+h[:, :, None]*1.8)
        elif slot == PORK:
            # Marbled pork with a browned perimeter; geometry supplies the curl.
            lines = np.abs(np.sin((y+.07*np.sin(x*TAU*2))*TAU*3)) < .19
            a[lines] = np.array([211, 181, 143])*value[lines, None]
        elif slot == LINEN:
            weave = np.sin(x*TAU*48)*np.sin(y*TAU*48)
            h += weave*.038
            a *= (1+weave[:, :, None]*.038)
            a[np.abs(y-.12)<.015] = (54, 70, 78)
        elif slot in [MATCHA, LEAF_GREEN]:
            h += noise*.014
            a *= (1+noise[:, :, None]*.017)
        elif slot in [GLASS_GREEN, GLASS_AMBER]:
            a *= (1+.13*np.cos(x*TAU*5))[:, :, None]
            h *= .08
        elif slot == KONJAC:
            flecks = rng.random((CELL, CELL)) < .045
            a[flecks] *= .52
            h += flecks*.02
        elif slot == SWEET_RED:
            h *= .4
            a *= (1+np.sin(x*TAU*9)*np.cos(y*TAU*7)*.08)[:, :, None]
        sl = (slice(slot//COLS*CELL, (slot//COLS+1)*CELL),
              slice(slot%COLS*CELL, (slot%COLS+1)*CELL))
        base[sl] = a
        heights[sl] = h
        arm[sl] = np.dstack([np.clip(.96+h*.13, .87, 1),
                            np.clip(roughness[slot]+noise*.009, .1, 1),
                            np.zeros_like(h)])*255
    # Derivatives are computed per tile, avoiding bleed across unrelated cells.
    normals = np.zeros_like(base)
    for slot in range(32):
        sl = (slice(slot//COLS*CELL, (slot//COLS+1)*CELL),
              slice(slot%COLS*CELL, (slot%COLS+1)*CELL))
        h = heights[sl]
        gx = (np.roll(h, -1, 1)-np.roll(h, 1, 1))*.5
        gy = (np.roll(h, -1, 0)-np.roll(h, 1, 0))*.5
        nn = np.dstack([-gx, -gy, np.ones_like(gx)])
        nn /= np.linalg.norm(nn, axis=2)[:, :, None]
        normals[sl] = (nn*.5+.5)*255
    files = []
    for suffix, arr in [('.png', base), ('_arm.png', arm), ('_normal.png', normals)]:
        path = out/(ATLAS_NAME+suffix)
        Image.fromarray(np.uint8(np.clip(arr, 0, 255)), 'RGB').save(path, optimize=True)
        files.append(path)
    return {'files': [str(p) for p in files], 'bytes': sum(p.stat().st_size for p in files),
            'size': [COLS*CELL, ROWS*CELL], 'license': 'Original procedural texture artwork'}


def _uv(tile, u, v):
    # Four-pixel gutters survive mipmapping at normal tabletop viewing distance.
    pad = 4/CELL
    return ((tile % COLS + pad + (1-2*pad)*float(u))/COLS,
            1-(tile//COLS + pad + (1-2*pad)*(1-float(v)))/ROWS)


class _Craft:
    """Small deterministic local modelling toolkit, batched into one material."""
    def __init__(self, g, P, B, M, seed):
        self.g, self.P, self.B, self.M = g, P, B, M
        self.rng = np.random.default_rng(seed)
        if 'CraftSurfaces' not in g.materials:
            g.material('CraftSurfaces', (1, 1, 1), ATLAS_NAME+'.png', roughness=1,
                       normal=ATLAS_NAME+'_normal.png', arm=ATLAS_NAME+'_arm.png',
                       normalScale=.48)
            # Restrained coals glow only through the small gaps of the grate.
            g.material('CraftEmbers', (.62, .095, .012), emission=.55, roughness=.95)
        self.mat = 'CraftSurfaces'
        self.detail = 1.0

    def mesh(self, v, f, tile, uv=None, material=None):
        if uv is None:
            v0 = np.asarray(v)
            xy = v0[:, :2]; lo = xy.min(axis=0); span = np.maximum(xy.max(axis=0)-lo, 1e-5)
            uv = (xy-lo)/span
        # Project only collapsed triangle UVs (e.g. the vertical konjac cut
        # faces) into their own plane. Curved shells keep authored seam/ring
        # continuity; tangent repair should not split glazed lips on export.
        v=list(v);f=list(f);uv=list(uv)
        for i,face in enumerate(f):
            q=np.asarray([uv[j] for j in face]);du=q[1]-q[0];dv=q[2]-q[0]
            if abs(du[0]*dv[1]-du[1]*dv[0])<1e-10:
                tri=np.asarray([v[j] for j in face]);right=tri[1]-tri[0]
                right/=max(np.linalg.norm(right),1e-12)
                normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=max(np.linalg.norm(normal),1e-12)
                up=np.cross(normal,right);flat=np.column_stack([tri@right,tri@up])
                flat-=flat.min(axis=0);flat/=(np.maximum(flat.max(axis=0),1e-8))
                start=len(v);v.extend(tri);uv.extend(flat*.8+.1);f[i]=(start,start+1,start+2)
        self.g.add([self.P(*p) for p in v], f, material or self.mat,
                   [_uv(tile, *p) for p in uv])

    def lathe(self, pos, profile, tile=IVORY, n=24, wobble=.012, phase=.0):
        """Hollow turned shell with a real foot, lip and interior wall.

        Profile points run from the underside outwards, upwards over the lip,
        then down the inside. There is no solid disk capping the opening.
        Separate end caps close the underside and inner floor; the lip stays open.
        """
        n=max(10, round(n*self.detail))
        v=[]; f=[]; uv=[]; p=np.asarray(pos)
        profile_arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(np.asarray(profile),axis=0),axis=1))]
        profile_arc/=max(profile_arc[-1],1e-8)
        for i, (r, z) in enumerate(profile):
            for j in range(n+1):
                a=j*TAU/n
                rr=r*(1+wobble*(math.sin(3*a+phase)+.35*math.sin(7*a-.7)))
                zz=z+wobble*.025*math.sin(2*a+.5)*min(1, r/.025)
                v.append(p+np.array([rr*math.cos(a), rr*math.sin(a), zz]))
                uv.append((j/n, profile_arc[i]))
                if i and j:
                    k=i*(n+1)+j
                    f.extend([(k-n-2,k-n-1,k),(k-n-2,k,k-1)])
        # Close only the underside and inner floor. Both remain flat and distinct.
        for row, up in [(0, False), (len(profile)-1, True)]:
            rad,z=profile[row]
            k=len(v); v.append(p+[0,0,z]); uv.append((.5,.5)); start=row*(n+1)
            for j in range(n):
                f.append((k,start+j,start+j+1) if up else (k,start+j+1,start+j))
        self.mesh(v,f,tile,uv)

    def tube(self, pts, radii, tile=BAMBOO, sides=6, material=None):
        """Tapered rounded rods; transported enough for these short curved props."""
        ps=np.asarray(pts,float); v=[]; f=[]; uv=[]
        for i,p in enumerate(ps):
            tangent=ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)]
            tangent/=max(np.linalg.norm(tangent),1e-9)
            ref=np.array([0,0,1.]) if abs(tangent[2])<.91 else np.array([1.,0,0])
            xx=np.cross(tangent,ref);xx/=max(np.linalg.norm(xx),1e-9); yy=np.cross(tangent,xx)
            for j in range(sides+1):
                a=j*TAU/sides;v.append(p+radii[i]*(xx*math.cos(a)+yy*math.sin(a)))
                uv.append((j/sides,i/max(1,len(ps)-1)))
                if i and j:
                    k=i*(sides+1)+j;f.extend([(k-sides-2,k-sides-1,k),(k-sides-2,k,k-1)])
        for row,up in [(0,False),(len(ps)-1,True)]:
            k=len(v);v.append(ps[row]);uv.append((.5,.5));start=row*(sides+1)
            for j in range(sides):f.append((k,start+j,start+j+1) if up else (k,start+j+1,start+j))
        self.mesh(v,f,tile,uv,material)

    def ring(self,pos,radius,thick,tile=IVORY,n=24,sides=5,start=0,end=TAU):
        p=np.asarray(pos)
        pts=[p+[radius*math.cos(a),radius*math.sin(a),0] for a in np.linspace(start,end,n+1)]
        self.tube(pts,[thick]*len(pts),tile,sides)

    def slab(self,pos,size,tile=LACQUER,bevel=.01,angle=0):
        """Bevelled eight-corner board/food block, never an unsoftened cube."""
        x,y,z=pos;w,d,h=size;bevel=min(bevel,w*.18,d*.18,h*.45)
        ca,sa=math.cos(angle),math.sin(angle)
        outline=[(-w/2+bevel,-d/2),(w/2-bevel,-d/2),(w/2,-d/2+bevel),
                 (w/2,d/2-bevel),(w/2-bevel,d/2),(-w/2+bevel,d/2),
                 (-w/2,d/2-bevel),(-w/2,-d/2+bevel)]
        v=[];f=[];uv=[]
        for k,(zz,inset) in enumerate([(-h/2,bevel),(-h/2+bevel,0),(h/2-bevel,0),(h/2,bevel)]):
            for j,(xx,yy) in enumerate(outline):
                xx*=1-inset/(w/2);yy*=1-inset/(d/2)
                v.append([x+xx*ca-yy*sa,y+xx*sa+yy*ca,z+zz])
                uv.append((j/8,(zz+h/2)/h))
                if k:
                    a=(k-1)*8+j;b=(k-1)*8+(j+1)%8;c=k*8+(j+1)%8;e=k*8+j
                    f.extend([(a,b,c),(a,c,e)])
        for row,up in [(0,False),(3,True)]:
            start=len(v)
            for j in range(8):
                q=np.asarray(v[row*8+j]);v.append(q);dx,dy=q[0]-x,q[1]-y
                uv.append(((dx*ca+dy*sa)/w+.5,(-dx*sa+dy*ca)/d+.5))
            k=len(v);v.append([x,y,z+(-h/2 if row==0 else h/2)]);uv.append((.5,.5))
            for j in range(8):f.append((k,start+j,start+(j+1)%8) if up else (k,start+(j+1)%8,start+j))
        self.mesh(v,f,tile,uv)

    def pebble(self,pos,scale,tile,n=12,rings=7,phase=0,rough=.04,exponent=1):
        """A shaped organic lump, with no pinched duplicate pole triangles."""
        v=[];f=[];uv=[];p=np.asarray(pos);scale=np.asarray(scale)
        # Rings are away from poles; cap each pole exactly once.
        for i in range(1,rings):
            t=i/rings;aa=math.pi*t
            for j in range(n+1):
                a=j*TAU/n
                deform=1+rough*(math.sin(a*3+phase)*math.sin(aa)+.35*math.sin(a*5+aa*3))
                q=np.array([math.sin(aa)*math.cos(a),math.sin(aa)*math.sin(a),math.cos(aa)])
                q=np.sign(q)*np.abs(q)**exponent
                v.append(p+scale*q*deform)
                uv.append((j/n,t))
                if i>1 and j:
                    k=(i-1)*(n+1)+j
                    f.extend([(k-n-2,k,k-n-1),(k-n-2,k-1,k)])
        for row,top in [(0,True),(rings-2,False)]:
            k=len(v);v.append(p+scale*[0,0,1 if top else -1]);uv.append((.5,0 if top else 1))
            for j in range(n):
                a=row*(n+1)+j;b=a+1
                f.append((k,a,b) if top else (k,b,a))
        self.mesh(v,f,tile,uv)

    def disk(self,pos,r,tile,n=24,ellipse=1):
        p=np.asarray(pos);v=[p];uv=[(.5,.5)];f=[]
        for j in range(n):
            a=j*TAU/n;v.append(p+[r*math.cos(a),r*math.sin(a)*ellipse,0]);uv.append((.5+.48*math.cos(a),.5+.48*math.sin(a)))
        for j in range(n):f.append((0,j+1,(j+1)%n+1))
        self.mesh(v,f,tile,uv)

    def bowl(self,pos,r=.15,h=.105,tile=IVORY,phase=0,n=18):
        # Modest asymmetry and footring avoid the perfect moulded bowl look.
        p=[(.30*r,0),(.36*r,.015),(.62*r,h*.30),(.88*r,h*.70),
           (r,h*.98),(.94*r,h),(.84*r,h*.69),(.57*r,h*.31),(.12*r,.025)]
        self.lathe(pos,p,tile,n,.016,phase)

    def plate(self,pos,r=.15,tile=INDIGO):
        self.lathe(pos,[(r*.33,0),(r*.37,.009),(r*.55,.014),(r*.89,.019),(r,.035),
                        (r*.99,.04),(r*.91,.037),(r*.81,.026),(r*.43,.019),(r*.12,.018)],tile,18,.011)

    def cup(self,pos,r=.045,h=.093,tile=IVORY,phase=0,drink=TEA):
        self.lathe(pos,[(r*.62,0),(r*.78,.009),(r*.94,h*.70),(r,h),
                        (r*.85,h-.002),(r*.76,.028),(r*.20,.024)],tile,16,.018,phase)
        if drink is not None:self.disk(np.asarray(pos)+[0,0,h-.018],r*.80,drink,20)

    def chopsticks(self,x,y,z,angle=.035,tile=BAMBOO):
        # A short rest holds the tips above the wood rather than floating sticks.
        self.slab((x,y+.061,z+.008),(.062,.021,.016),IVORY,.006,angle)
        for off in [-.009,.009]:
            a=np.array([x+off-.003,y-.150,z+.012]);b=np.array([x+off+angle*.20,y+.113,z+.019])
            self.tube([a,b],[.0033,.0018],tile,6)

    def tray(self,pos,w=.39,d=.28):
        x,y,z=pos;self.slab((x,y,z+.011),(w,d,.022),LACQUER,.007)
        for sx in [-1,1]:self.slab((x+sx*(w/2-.009),y,z+.029),(.018,d,.032),LACQUER,.006)
        for sy in [-1,1]:self.slab((x,y+sy*(d/2-.009),z+.029),(w-.03,.018,.032),LACQUER,.006)
        return z+.023

    def masu(self,pos):
        # A square cedar measure has walls and an open interior, not a cube.
        x,y,z=pos
        self.slab((x,y,z+.005),(.132,.128,.010),BAMBOO,.003)
        for side in [-1,1]:
            self.slab((x+side*.061,y,z+.043),(.010,.128,.076),BAMBOO,.002)
            self.slab((x,y+side*.059,z+.043),(.112,.010,.076),BAMBOO,.002)
        return z+.011

    def cloth(self,pos,w=.28,d=.16,angle=0):
        x,y,z=pos;v=[];uv=[];f=[];nx=12;ny=6;ca,sa=math.cos(angle),math.sin(angle)
        for j in range(ny+1):
            for i in range(nx+1):
                u=i/nx;t=j/ny;xx=(u-.5)*w;yy=(t-.5)*d
                zz=z+.005*math.sin(u*TAU*2)+.002*math.sin(t*TAU)
                v.append((x+xx*ca-yy*sa,y+xx*sa+yy*ca,zz));uv.append((u,t))
                if i and j:
                    k=j*(nx+1)+i;f.extend([(k-nx-2,k-nx-1,k),(k-nx-2,k,k-1)])
        self.mesh(v,f,LINEN,uv)

    def bottle(self,pos,tile=GLASS_GREEN,height=.34,width=.056,style=0,label=0):
        x,y,z=pos;h=height;r=width
        if style==0:prof=[(.63*r,0),(.94*r,.018),(r,.048),(r,h*.66),(.93*r,h*.75),(.47*r,h*.82),(.43*r,h*.95),(.52*r,h*.975),(.48*r,h)]
        elif style==1:prof=[(.65*r,0),(.96*r,.018),(r,h*.45),(.92*r,h*.64),(.72*r,h*.74),(.34*r,h*.83),(.32*r,h*.98),(.37*r,h)]
        else:prof=[(.61*r,0),(.89*r,.015),(1.10*r,h*.39),(.99*r,h*.61),(.56*r,h*.79),(.47*r,h*.95),(.53*r,h)]
        self.lathe((x,y,z),prof,tile,16,.009,style)
        self.lathe((x,y,z+h),[(r*.49,0),(r*.49,.018),(r*.1,.019)],CLAY if style==2 else LACQUER,14,0)
        # A curved paper label, matching the bottle rather than floating in space.
        slot=label%16;u0=slot%8/8;v1=1-(.75+(slot//8)*.125)
        zz0=h*.26;zz1=h*.55;v=[];uv=[];ff=[]
        for j in range(9):
            angle=math.pi*.5-.65+j/8*1.3
            # Silhouette 1/2 expand slightly at label height.
            radius=r*(1.015 if style<2 else 1.075)
            for k,zz in enumerate([zz0,zz1]):
                v.append(self.P(x+radius*math.cos(angle),y+radius*math.sin(angle),z+zz))
                uv.append((u0+j/8*.125,v1-.125+k*.125))
            if j:ff.extend([(j*2-2,j*2,j*2+1),(j*2-2,j*2+1,j*2-1)])
        self.g.add(v,ff,self.M['menu'],uv)

    def canister(self,pos,r=.075,h=.17,tile=CLAY):
        self.lathe(pos,[(r*.86,0),(r,.010),(r,h*.83),(r*1.015,h*.85),(r*1.015,h*.96),(r*.93,h),(r*.08,h)],tile,18,.005)
        self.ring(np.asarray(pos)+[0,0,h*.84],r*1.01,.003,LACQUER,22,4)

    def flask(self,pos,r=.062,h=.21,tile=IVORY):
        self.lathe(pos,[(r*.58,0),(r*.76,.010),(r,h*.34),(r*.92,h*.55),(r*.48,h*.76),
                        (r*.37,h*.92),(r*.44,h),(.31*r,h),(.28*r,h*.89)],tile,18,.02)

    def ramekin(self,pos,r=.049,tile=TENMOKU,liquid=SAUCE):
        self.bowl(pos,r,.030,tile)
        self.disk(np.asarray(pos)+[0,0,.022],r*.78,liquid,20)

    def rice(self,pos,r=.09):
        self.bowl(pos,r,.079,TENMOKU)
        # Low-poly grains form a broken top silhouette; no huge pile of spheres.
        for j in range(18):
            a=j*2.39996;rr=r*.67*math.sqrt((j+.5)/18)
            x,y=rr*math.cos(a),rr*math.sin(a)
            self.pebble(np.asarray(pos)+[x,y,.07+.013*(1-rr/r)],(.012,.006,.005),DANGO,6,4,j,.03)


def _grilled_skewer(c,x,y,z,angle=0,kind=0,length=.37):
    ca,sa=math.cos(angle),math.sin(angle)
    def pp(xx,yy,zz):return np.array([x+xx*ca-yy*sa,y+xx*sa+yy*ca,z+zz])
    c.tube([pp(0,-length*.58,0),pp(0,length*.52,0)],[.0032,.0021],BAMBOO,5)
    for k in range(4):
        yy=-.072+k*.053
        if kind==1:
            c.pebble(pp(0,yy,.019),(.027,.029,.026),CHICKEN,10,6,k*.7,.075)
        elif k%2==1:
            # Split scallion segments with a pale exposed center.
            c.tube([pp(0,yy-.019,.018),pp(0,yy+.019,.018)],[.019,.019],DAIKON,10)
            c.tube([pp(0,yy+.008,.018),pp(0,yy+.019,.018)],[.0194,.0194],LEAF_GREEN,10)
            c.tube([pp(0,yy+.0195,.018),pp(0,yy+.0202,.018)],[.014,.014],DAIKON,9)
        else:
            c.pebble(pp(0,yy,.020),(.030,.031,.024),CHICKEN,10,6,k*.6,.09,exponent=.66)
            for cc in [-.01,.007]:
                c.tube([pp(-.017,yy+cc,.040),pp(.016,yy+cc+.003,.039)],[.0017,.0015],CHARCOAL,4)


def _yakitori_grill(c,w,dep):
    # This working grill deliberately stays inside the original rear-prep area.
    x=.68;y=-dep/2+1.10;z=.85;ww=1.28;dd=.44
    c.slab((x,y,z+.08),(ww,dd,.16),CHARCOAL,.018)
    for sx in [-1,1]:
        c.slab((x+sx*(ww/2-.024),y,z+.18),(.043,dd,.21),CHARCOAL,.008)
    for sy in [-1,1]:c.slab((x,y+sy*(dd/2-.020),z+.18),(ww-.08,.035,.21),CHARCOAL,.008)
    # Hollow charcoal bed, ashy irregular logs with only tiny ember seams.
    for i in range(11):
        xx=x-.50+i*.095;yy=y+.055*math.sin(i*1.7)
        c.pebble((xx,yy,z+.145),(.047,.113,.039),CHARCOAL,9,5,i,.18)
        if i%3==0:
            c.tube([(xx-.015,yy-.07,z+.158),(xx+.008,yy+.06,z+.172)],[.0025,.0035],CHARCOAL,4,'CraftEmbers')
    gratez=z+.238
    for j in range(16):
        xx=x-.57+j*.076
        c.tube([(xx,y-.214,gratez),(xx,y+.214,gratez)],[.0028,.0028],CHARCOAL,5,c.M['iron'])
    for j in range(7):
        yy=y-.21+j*.07
        c.tube([(x-.58,yy,gratez+.003),(x+.58,yy,gratez+.003)],[.0028,.0028],CHARCOAL,5,c.M['iron'])
    for j in range(6):
        _grilled_skewer(c,x-.44+j*.176,y-.008,gratez+.012,(-.06 if j%2 else .04),j%3==1,.43)
    for sx in [-1,1]:
        # Loop side handles show actual metalwork and are not large block handles.
        xx=x+sx*(ww/2+.013)
        c.tube([(xx,y-.10,z+.17),(xx+sx*.055,y-.10,z+.14),
                (xx+sx*.055,y+.10,z+.14),(xx,y+.10,z+.17)],[.009]*4,CHARCOAL,6,c.M['iron'])
    # Tongs set diagonally on a little resting plate beside the brazier.
    c.plate((x-.90,y+.025,.859),.115,TENMOKU)
    for off in [-.014,.014]:
        c.tube([(x-.92+off,y-.08,.891),(x-.88+off*.6,y+.15,.885)],[.0048,.0040],CHARCOAL,5,c.M['iron'])
    # Sauce jar and a real brush: bound bristles with a flattened working end.
    c.canister((x+.88,y-.02,.85),.073,.135,TENMOKU)
    c.tube([(x+.88,y-.02,.96),(x+.96,y+.08,1.15)],[.007,.005],BAMBOO,7)
    for j in range(5):c.tube([(x+.86+j*.009,y-.02,.94),(x+.86+j*.009,y-.026,.976)],[.0028,.0028],BAMBOO,4)


def _ramen(c,pos,variant=0):
    x,y,z=pos;c.bowl(pos,.156,.112,IVORY,variant*.7,n=64)
    c.disk((x,y,z+.082),.126,BROTH,28)
    # A tangled, submerged noodle nest occupies only part of the broth surface.
    for j in range(7):
        pts=[]
        for k in range(15):
            t=k/14;aa=t*TAU*1.15+j*.73
            rr=.015+.057*t
            pts.append((x-.022+rr*math.cos(aa),y-.012+rr*.74*math.sin(aa),z+.085+.003*math.sin(t*TAU*2+j)))
        c.tube(pts,[.0032]*len(pts),NOODLE,5)
    # Pork is a thin irregular medallion, with fat spirals and a browned edge.
    px=x-.055;py=y+.030
    c.pebble((px,py,z+.094),(.055,.043,.009),PORK,16,5,1.1,.08)
    # Flattened, interrupted fat marbling follows the pork surface; it must
    # never read as a bright noodle/cord placed on top of a flat medallion.
    pts=[]
    for k in range(39):
        t=k/38;aa=t*TAU*1.58+.07*math.sin(t*TAU*3)
        rr=(.035*(1-t)+.007)*(1+.06*math.sin(t*TAU*4+.7))
        pts.append(np.array([px+rr*math.cos(aa),py+rr*.72*math.sin(aa)]))
    vv=[];uv=[];ff=[]
    for k,q in enumerate(pts):
        tangent=pts[min(k+1,len(pts)-1)]-pts[max(k-1,0)]
        tangent/=max(np.linalg.norm(tangent),1e-9);right=np.array([tangent[1],-tangent[0]])
        width=.0009*(1+.25*math.sin(k*1.1))
        for side in [-1,1]:
            xy=q+right*width*side
            height=z+.094+.009*math.sqrt(max(.05,1-((xy[0]-px)/.055)**2-((xy[1]-py)/.043)**2))+.00015
            vv.append((xy[0],xy[1],height));uv.append(((side+1)/2,k/38))
        if k and k not in [11,12,27]:
            b=k*2;ff.extend([(b-2,b+1,b),(b-2,b-1,b+1)])
    c.mesh(vv,ff,DAIKON,uv)
    # Egg half has a cut face and recessed yolk, never a whole ball on soup.
    ex=x+.061;ey=y-.025
    old=c.P
    def egg_oval(X,Y,Z):return old(X,ey+(Y-ey)*1.28,Z)
    c.P=egg_oval
    c.lathe((ex,ey,z+.084),[(.009,0),(.027,.008),(.036,.025),(.036,.039),(.031,.041),(.006,.041)],EGG,18,.012)
    c.P=old
    c.pebble((ex,ey,z+.1256),(.022,.0273,.0019),YOLK,18,5,.5,.025)
    # One crinkled nori sheet leans from the far rim.
    vv=[];uv=[];ff=[]
    for row in range(4):
        for col in range(5):
            u=col/4;t=row/3
            vv.append((x+.012+(u-.5)*.081,y-.072-t*.030,z+.083+t*.086+.004*math.sin(u*TAU*2+t)))
            uv.append((u,t))
            if row and col:
                k=row*5+col;ff.extend([(k-6,k-5,k),(k-6,k,k-1)])
    nv=len(vv)
    c.mesh(vv+vv,ff+[(a+nv,d+nv,b+nv) for a,b,d in ff],NORI,uv+uv)
    # Scallion rings are thin hollow cross-cuts rather than green spheres.
    for j in range(7):
        a=j*2.399;rr=.029*math.sqrt((j+.5)/7)
        c.ring((x+.033+rr*math.cos(a),y+.035+rr*math.sin(a),z+.094+j*.0004),.006,.0017,LEAF_GREEN,9,4)
    # Narutomaki cross-section with a continuous pink spiral.
    if variant%2==0:
        nx=x-.063;ny=y-.065
        c.pebble((nx,ny,z+.094),(.026,.022,.006),EGG,12,5,0,.1)
        pts=[]
        for k in range(20):
            t=k/19;aa=t*TAU*1.5;rr=.019*(1-t)
            pts.append((nx+rr*math.cos(aa),ny+rr*.8*math.sin(aa),z+.100))
        c.tube(pts,[.0018]*len(pts),PINK,4)


def _renge(c,x,y,z,angle=0):
    ca,sa=math.cos(angle),math.sin(angle)
    def p(xx,yy,zz):return np.array([x+xx*ca-yy*sa,y+xx*sa+yy*ca,z+zz])
    # Concave spoon bowl built as a short shell and gently arched handle.
    prof=[(.006,0),(.014,.003),(.021,.009),(.022,.015),(.019,.016),(.013,.008),(.005,.006)]
    # Slight ovalism is introduced through a transformed local modelling context.
    old=c.P
    center=p(0,0,0)
    def oval(X,Y,Z):
        q=np.array([X,Y,Z])-center
        return old(*(center+np.array([q[0],q[1]*1.42,q[2]])))
    c.P=oval;c.lathe(center,prof,IVORY,18,.0);c.P=old
    # Flattened handle has a soft oval cross-section, not a polygonal rod.
    vv=[];ff=[];uv=[];section=10
    handle=[(.016,.013,.007),(.048,.017,.006),(.091,.025,.0065),(.126,.032,.009),(.136,.033,.005)]
    for row,(yy,zz,ww) in enumerate(handle):
        for j in range(section+1):
            aa=j*TAU/section
            vv.append(p(math.cos(aa)*ww,yy,zz+math.sin(aa)*.0024))
            uv.append((j/section,row/(len(handle)-1)))
            if row and j:
                k=row*(section+1)+j
                ff.extend([(k-section-2,k,k-section-1),(k-section-2,k-1,k)])
    for row,front in [(0,False),(len(handle)-1,True)]:
        yy,zz,_=handle[row];k=len(vv);vv.append(p(0,yy,zz));uv.append((.5,.5));start=row*(section+1)
        for j in range(section):ff.append((k,start+j+1,start+j) if front else (k,start+j,start+j+1))
    c.mesh(vv,ff,IVORY,uv)


def _tea_whisk(c,pos):
    x,y,z=pos
    # Chasen is split bamboo: hollow handle, thread binding and two flared tines.
    c.lathe(pos,[(.020,0),(.021,.010),(.020,.063),(.018,.071),(.014,.071),(.014,.016),(.008,.012)],BAMBOO,20,.012)
    for zz in [.058,.061,.064]:c.ring((x,y,z+zz),.021,.0015,LACQUER,20,4)
    for j in range(20):
        a=j*TAU/20;ca,sa=math.cos(a),math.sin(a)
        pts=[]
        for rr,zz in [(.019,.066),(.028,.099),(.033,.125),(.029,.142),(.020,.148)]:
            pts.append((x+rr*ca,y+rr*sa,z+zz))
        c.tube(pts,[.0012,.0012,.0011,.0009,.0007],BAMBOO,4)
    for j in range(10):
        a=j*TAU/10+.12
        pts=[(x+r*math.cos(a),y+r*math.sin(a),z+zz) for r,zz in [(.014,.069),(.010,.100),(.006,.122),(.002,.127)]]
        c.tube(pts,[.001]*4,BAMBOO,4)


def _teapot(c,pos,r=.085,tile=TENMOKU):
    x,y,z=pos;h=r*1.42
    c.lathe(pos,[(r*.43,0),(r*.68,.009),(r*.92,h*.24),(r,h*.51),(r*.88,h*.80),(r*.63,h*.88),
                 (r*.60,h*.92),(r*.49,h*.92),(r*.47,h*.77)],tile,24,.015)
    c.lathe((x,y,z+h*.86),[(r*.12,0),(r*.64,.009),(r*.58,.019),(r*.28,.030),(r*.12,.032)],tile,20,.015)
    c.pebble((x,y,z+h*.86+.038),(.013,.013,.011),tile,12,5,.0,.02)
    # Side-handle kyusu silhouette, visibly hollow at the handle end.
    c.tube([(x+r*.70,y-.025,z+h*.46),(x+r*1.83,y-.042,z+h*.51)],[r*.25,r*.18],tile,10)
    c.tube([(x-r*.74,y+.019,z+h*.47),(x-r*1.16,y+.048,z+h*.73),(x-r*1.34,y+.071,z+h*.98)],
           [r*.24,r*.17,r*.10],tile,10)
    c.disk((x,y,z+h*.86+.010),r*.31,tile,20)


def _dango(c,pos,angle=0,colors=(PINK,DANGO,LEAF_GREEN)):
    x,y,z=pos;ca,sa=math.cos(angle),math.sin(angle)
    def p(t):return [x-t*sa,y+t*ca,z]
    c.tube([p(-.125),p(.112)],[.0026,.0017],BAMBOO,5)
    for j,tile in enumerate(colors):
        q=np.array(p(-.035+j*.048));q[2]+=.014
        c.pebble(q,(.025,.027,.024),tile,12,6,j*.4,.035)


def _oden_piece(c,pos,kind=0):
    x,y,z=pos
    if kind==0:
        c.lathe(pos,[(.044,0),(.055,.008),(.057,.048),(.049,.056),(.006,.056)],DAIKON,16,.035)
        for a in [.25,1.5]:
            c.tube([(x-.036*math.cos(a),y-.036*math.sin(a),z+.0565),(x+.036*math.cos(a),y+.036*math.sin(a),z+.0565)],[.0011,.0011],BROTH,4)
    elif kind==1:c.pebble((x,y,z+.033),(.036,.029,.042),EGG,12,7,.4,.02)
    elif kind==2:
        # A triangular konjac wedge is a recognisable silhouette at a glance.
        v=[(x-.047,y-.035,z),(x+.047,y-.035,z),(x+.009,y+.045,z),
           (x-.047,y-.035,z+.047),(x+.047,y-.035,z+.047),(x+.009,y+.045,z+.047)]
        ff=[(0,2,1),(3,4,5),(0,1,4),(0,4,3),(1,2,5),(1,5,4),(2,0,3),(2,3,5)]
        c.mesh(v,ff,KONJAC)
    elif kind==3:
        c.slab((x,y,z+.025),(.084,.059,.047),FISHCAKE,.011,.13)
    else:
        c.tube([(x,y-.041,z+.029),(x,y+.041,z+.029)],[.025,.025],FISHCAKE,12)
        c.tube([(x,y+.0415,z+.029),(x,y+.042,z+.029)],[.012,.012],CHARCOAL,10)


def _oden_pot(c,w,dep):
    x=.48;y=-dep/2+1.1;z=.85;ww=.96;dd=.44
    c.slab((x,y,z+.039),(ww,dd,.078),CHARCOAL,.016)
    for sx in [-1,1]:c.slab((x+sx*(ww/2-.015),y,z+.094),(.030,dd,.13),TENMOKU,.007)
    for sy in [-1,1]:c.slab((x,y+sy*(dd/2-.015),z+.094),(ww,.029,.13),TENMOKU,.007)
    c.slab((x,y,z+.090),(ww-.035,dd-.035,.012),BROTH,.004)
    for sx in [-1,1]:
        xx=x+sx*.16
        c.tube([(xx,y-dd/2+.02,z+.131),(xx,y+dd/2-.02,z+.131)],[.003,.003],CHARCOAL,5,c.M['iron'])
    c.tube([(x-ww/2+.02,y,z+.131),(x+ww/2-.02,y,z+.131)],[.003]*2,CHARCOAL,5,c.M['iron'])
    for i in range(6):
        cx=x-.32+(i%3)*.32;cy=y-.118+(i//3)*.236
        for j in range(2):_oden_piece(c,(cx+(j-.5)*.10,cy,z+.097),i%5)
    c.slab((x-.77,y-.02,z+.027),(.34,.43,.030),BAMBOO,.009,.07)
    # Wooden lid resting on its edge against the rear wall, small upright pull.
    c.slab((x+.80,y+.045,z+.060),(.40,.40,.022),BAMBOO,.008,.07)
    c.slab((x+.80,y+.045,z+.083),(.13,.028,.034),BAMBOO,.006,.07)


def _tea_service(c,w,dep):
    x=.15;y=-dep/2+1.10;z=.85
    top=c.tray((x,y,z),.89,.43)
    c.bowl((x-.24,y-.015,top),.106,.084,INDIGO,n=40)
    c.disk((x-.24,y-.015,top+.060),.082,MATCHA,24)
    _tea_whisk(c,(x+.006,y+.095,top))
    c.canister((x+.225,y+.080,top),.063,.123,LACQUER)
    # Chashaku curved scoop, left dry across the tray.
    c.tube([(x-.025,y-.145,top+.012),(x+.130,y-.136,top+.014),(x+.191,y-.130,top+.032)],
           [.0035,.0035,.006],BAMBOO,6)
    c.cloth((x+.205,y-.050,top+.004),.14,.10,.08)
    _teapot(c,(x-.75,y-.013,z),.092,TENMOKU)
    c.cup((x-.93,y-.085,z),.045,.065,INDIGO)
    # Tea tin order is deliberately unequal, with one low lidded natsume.
    for j in range(3):c.canister((x+.70+j*.15,y+.055,z),.058,.12+j*.037,[CLAY,INDIGO,TENMOKU][j])


def _shelf_contents(c,w,dep,idx):
    """A shop-specific shelf rhythm, with genuine negative space and variety."""
    sy=-dep/2+.32
    previous_detail=c.detail;c.detail=.62
    # Keep the shoji and the menu board readable; fewer props than the old row.
    spots=np.linspace(-w/2+.78,w/2-.66,7 if w>=6 else 6)
    for row,h in enumerate([1.44,2.09]):
        for j,x in enumerate(spots):
            if j==0 or (row==1 and j%4==1):continue
            yy=sy+.035*math.sin(j*2.1+idx)
            if idx in [1,2] and (j+row)%3!=0:
                count=2+(j%2)
                for k in range(count):c.bowl((x,yy,h+k*.025),.081 if row else .096,.064,IVORY if j%2 else INDIGO,j)
            elif idx in [4,7] and (j+row)%4!=0:
                c.canister((x,yy,h),.063+(j%2)*.009,.14+(j%3)*.025,[CLAY,INDIGO,TENMOKU][j%3])
            elif idx in [3,5] and (j+row)%4==1:
                c.flask((x,yy,h),.060,.19+(j%2)*.04,IVORY if j%2 else CERAMIC_BLUE)
            else:
                c.bottle((x,yy,h),GLASS_AMBER if j%3==0 else GLASS_GREEN,
                         .28+(j%4)*.026,.050+(j%3)*.007,(j+idx)%3,j+idx)
    # One short cup stack at each bar; no perfectly repeated high shelf columns.
    for j in range(2):
        c.cup((w/2-.51-j*.11,sy+.08,1.44),.035,.076,IVORY,j,drink=None)
    c.detail=previous_detail


def _prep_unique(c,w,dep,idx):
    y=-dep/2+1.10;z=.85
    if idx==0:_yakitori_grill(c,w,dep)
    elif idx==1:
        # Stockpot, wire noodle basket and a tidy pair of ingredient dishes.
        c.lathe((.36,y,z),[(.12,0),(.20,.025),(.205,.28),(.215,.295),(.198,.303),(.183,.273),(.183,.038),(.03,.027)],CHARCOAL,24,.003)
        # Metal lid is displaced beside the open stockpot.
        c.lathe((.88,y+.025,z),[(.014,0),(.20,.008),(.208,.020),(.16,.034),(.01,.035)],CHARCOAL,24,0)
        c.tube([(.84,y+.025,z+.035),(.84,y+.025,z+.076),(.92,y+.025,z+.076),(.92,y+.025,z+.035)],[.005]*4,CHARCOAL,6,c.M['iron'])
        c.disk((.36,y,z+.233),.18,BROTH,24)
        # A wire basket rim and concentric seams read as mesh without dense fill.
        c.ring((-.10,y,z+.15),.079,.0045,CHARCOAL,20,5)
        for j in range(14):
            a=j*TAU/14
            c.tube([(-.10+.040*math.cos(a),y+.040*math.sin(a),z+.035),
                    (-.10+.065*math.cos(a),y+.065*math.sin(a),z+.074),
                    (-.10+.078*math.cos(a),y+.078*math.sin(a),z+.15)],[.0016]*3,CHARCOAL,4,c.M['iron'])
        for hh,rr in [(.037,.042),(.078,.065),(.117,.073)]:c.ring((-.10,y,z+hh),rr,.0015,CHARCOAL,18,4)
        c.tube([(-.10,y-.07,z+.14),(-.10,y-.21,z+.36)],[.010,.008],BAMBOO,8)
        for j in range(2):
            c.plate((-0.55-j*.30,y-.025,z),.124,INDIGO)
            for k in range(3):c.pebble((-.55-j*.30+(k-1)*.038,y,z+.038),(.034,.045,.009),PORK if j==0 else EGG,12,5,k,.04)
        for k in range(4):c.bowl((1.25,y,z+k*.031),.122,.085,IVORY,k)
        c.cloth((-.84,y+.16,z+.012),.29,.11,.11)
    elif idx==2:_oden_pot(c,w,dep)
    elif idx==4:_tea_service(c,w,dep)
    elif idx==3:
        top=c.tray((.02,y,z),.78,.42)
        c.flask((-.17,y+.03,top),.066,.23,IVORY)
        c.flask((.14,y+.02,top),.072,.205,TENMOKU)
        for j in range(3):c.cup((-.24+j*.20,y-.13,top),.030,.040,IVORY,j,TEA)
        c.bottle((.76,y,z),GLASS_GREEN,.37,.067,0,5)
        c.bottle((1.02,y+.02,z),GLASS_AMBER,.31,.063,1,2)
        c.cloth((-.64,y,z+.007),.27,.18,-.16)
    elif idx==5:
        # Plum/yuzu bar: the ume jar is ceramic, with a ladle and a citrus board.
        c.canister((.12,y,z),.145,.23,TENMOKU)
        c.ring((.12,y,z+.225),.139,.012,CLAY,24,6)
        c.tube([(.12,y,z+.13),(.20,y+.08,z+.42)],[.009,.009],BAMBOO,8)
        c.slab((-.48,y,z+.025),(.46,.34,.035),BAMBOO,.01,-.05)
        for j in range(3):c.pebble((-.56+j*.08,y,z+.065),(.042,.040,.037),YOLK,12,7,j,.09)
        c.bottle((.62,y,z),GLASS_AMBER,.31,.060,1,4)
        c.bottle((.85,y,z),GLASS_GREEN,.35,.063,0,1)
        c.ramekin((1.16,y,z),.091,INDIGO,SWEET_RED)
    elif idx==6:
        # Small cast pan, sansho mortar and real ridged pestle.
        c.lathe((.18,y,z),[(.045,0),(.16,.010),(.19,.055),(.19,.071),(.178,.075),(.148,.028),(.035,.020)],CHARCOAL,24,.005)
        c.tube([(.35,y,z+.062),(.64,y-.025,z+.054)],[.019,.015],CHARCOAL,8,c.M['iron'])
        for j in range(4):c.pebble((.10+(j%2)*.13,y-.06+(j//2)*.13,z+.040),(.062,.042,.022),CHICKEN,12,6,j,.12)
        c.bowl((-.54,y,z),.114,.076,CLAY)
        for j in range(16):
            a=j*TAU/16
            c.tube([(-.54+.051*math.cos(a),y+.051*math.sin(a),z+.033),
                    (-.54+.096*math.cos(a),y+.096*math.sin(a),z+.061)],[.0013,.0013],TENMOKU,4)
        c.tube([(-.54,y,z+.045),(-.66,y+.17,z+.20)],[.017,.009],BAMBOO,10)
        c.plate((.97,y,z),.15,INDIGO)
        for j in range(3):
            xx=.90+j*.073
            c.tube([(xx,y-.051,z+.041),(xx+.014,y+.055,z+.051)],[.018,.018],LEAF_GREEN,8)
    else:
        # Seasonal sweets shop: sliced yokan shows a chestnut in the cut face.
        c.slab((.04,y,z+.020),(.89,.43,.031),BAMBOO,.01)
        c.slab((.15,y,z+.075),(.29,.13,.092),SWEET_RED,.006)
        for j in range(3):
            xx=-.29+j*.083
            c.slab((xx,y,z+.070),(.056,.127,.086),SWEET_RED,.004)
            c.pebble((xx,y+.064,z+.071),(.014,.0018,.022),CHESTNUT,10,5,j,.12)
        c.slab((.72,y,z+.013),(.40,.26,.02),LACQUER,.006)
        _dango(c,(.68,y-.014,z+.039),-.28)
        _dango(c,(.79,y-.008,z+.039),-.28)
        c.tube([(-.39,y-.10,z+.035),(-.15,y-.09,z+.035)],[.004,.0016],BAMBOO,5)


def retained_furniture(B, w, dep, idx, M):
    """Optional replacement for furniture formerly mixed into the food block.

    The existing S01 hood follows the grill onto its supported prep ledge.
    The S05 table dimensions stay unchanged. This function is not called by add_counter_craft: the integrator decides where it belongs.
    """
    if idx==0:
        B(.68,-dep/2+1.10,2.15,1.5,.78,.23,M['iron'])
        B(.68,-dep/2+.91,3.07,.35,.35,1.65,M['iron'])
    elif idx==4:
        for side in [-1,1]:B(side*2.5,.2,.50,1.05,1.2,.10,M['counter'])


def add_counter_craft(g, P, B, w, dep, idx, M, rng=None, staff_entry=False):
    """Add all shop-specific close props; return geometry/resource diagnostics.

    ``idx`` is 0..7 (S01..S08). No global group changes or global RNG mutation.
    All front-counter geometry stays within the existing countertop; rear
    work stays on the 0.85 m high prep surfaces. Shelf bases match their boards.
    """
    before=sum(len(b['f']) for b in g.batches.values())
    c=_Craft(g,P,B,M,91071+idx*317)
    cy=dep/2-.205;top=1.032
    counts=[6,6,5,6,8,6,6,6];count=counts[idx];spread=min(w-1.5,(count-1)*.70)
    settings=[]
    for j in range(count):
        x=-spread/2+spread*j/(count-1)
        # The narrow S03 end is shared with the identity module's washi lamp.
        if idx==2 and j==0:x+=.22
        if idx==4 and j==0:x+=.10
        if staff_entry and idx==2 and j==count-1:x-=.22
        if staff_entry and idx==4 and j==count-1:x-=.10
        # Every seat has an intentional service pattern; two clean open settings
        # provide breathing room instead of cloning six complete dinner plates.
        active=j in [1,count-2] or (idx in [3,5] and j==count//2)
        if idx==0:
            z=c.tray((x-.015,cy,top),.39,.28)
            if active:
                _grilled_skewer(c,x-.045,cy,z+.020,.30,j%2)
                _grilled_skewer(c,x+.040,cy,z+.020,.30,(j+1)%2)
                c.ramekin((x+.126,cy+.041,z),.033,TENMOKU,SAUCE)
            elif j%2==0:c.cloth((x-.03,cy, z+.004),.22,.12,.03)
        elif idx==1:
            if active:_ramen(c,(x-.027,cy-.012,top),j)
            else:c.bowl((x-.026,cy-.011,top),.139,.096,IVORY,j)
            _renge(c,x+.205,cy-.089,top+.01,-.055)
        elif idx==2:
            c.bowl((x-.025,cy,top),.142,.077,TENMOKU,j)
            if active:
                c.disk((x-.025,cy,top+.051),.117,BROTH,22)
                for k in range(3):_oden_piece(c,(x-.079+k*.060,cy+(.028 if k%2 else -.022),top+.047),k)
                c.ramekin((x+.190,cy+.031,top),.029,IVORY,YOLK)
        elif idx==3:
            # Cedar masu with an inner square hollow, ceramic ochoko beside it.
            zz=c.masu((x-.055,cy,top))
            c.cup((x-.055,cy,zz),.042,.081,IVORY,j,TEA)
            if active:c.flask((x+.16,cy-.026,top),.049,.18,IVORY if j%2 else TENMOKU)
            else:c.ramekin((x+.18,cy+.003,top),.056,INDIGO,SAUCE)
        elif idx==4:
            zz=c.tray((x-.01,cy,top),.43,.30)
            c.bowl((x-.096,cy+.013,zz),.079,.066,INDIGO,j)
            c.disk((x-.096,cy+.013,zz+.045),.060,MATCHA,20)
            if active:
                c.plate((x+.10,cy,zz),.078,IVORY)
                _dango(c,(x+.10,cy-.023,zz+.043),.18)
            else:c.cloth((x+.105,cy,zz+.002),.11,.13,.04)
        elif idx==5:
            c.cup((x-.079,cy,top),.047,.10,CERAMIC_BLUE,j,TEA)
            c.plate((x+.093,cy,top),.092,INDIGO)
            if active:
                # Edamame pods are tapered and bent, not loose glossy balls.
                for k in range(4):
                    yy=cy-.04+k*.025
                    pts=[(x+.054,yy,top+.039),(x+.087,yy+.016,top+.048),(x+.132,yy+.017,top+.039)]
                    c.tube(pts,[.004,.014,.002],LEAF_GREEN,7)
            elif j%2:c.ramekin((x+.093,cy,top+.030),.043,IVORY,SAUCE)
        elif idx==6:
            c.plate((x-.031,cy,top),.139,INDIGO)
            if active:
                for k in range(3):c.pebble((x-.081+k*.052,cy+.01,top+.049),(.041,.032,.025),CHICKEN,12,6,k,.1)
                for k in range(3):c.pebble((x+.027+k*.009,cy-.051,top+.040),(.018,.032,.002),LEAF_GREEN,8,4,k,.04)
            c.ramekin((x+.188,cy+.018,top),.044,TENMOKU,SAUCE)
        else:
            zz=c.tray((x-.014,cy,top),.38,.27)
            c.plate((x-.055,cy,zz),.104,IVORY)
            if active:
                c.slab((x-.066,cy,zz+.057),(.073,.079,.049),SWEET_RED,.004,.03)
                c.pebble((x-.066,cy+.039,zz+.057),(.019,.0016,.015),CHESTNUT,10,5,j,.06)
            else:_dango(c,(x-.050,cy-.024,zz+.044),.10)
            c.tube([(x+.092,cy-.10,zz+.008),(x+.097,cy+.076,zz+.008)],[.0028,.0017],BAMBOO,5)
        # Tea cups are between services rather than in the old five-wide overlay.
        if idx in [0,1,2,6,7] and not (idx in [0,2,6] and j==0) and not (staff_entry and idx==2 and j==count-1):c.cup((x-.234,cy-.083,top),.034,.066,IVORY if idx%2 else INDIGO,j)
        if idx not in [3,4,7] and not (staff_entry and idx==2 and j==count-1):c.chopsticks(x+.250,cy-.012,top,.023+(j%2)*.025)
        settings.append({'x':round(x,3),'served':active})
    _shelf_contents(c,w,dep,idx)
    _prep_unique(c,w,dep,idx)
    # One turned pottery utensil pot only where the restaurant needs one.
    if idx in [0,1,2,6]:
        x=w/2-.74;y=-dep/2+1.06;holder_base=.85
        c.lathe((x,y,holder_base),[(.035,0),(.046,.012),(.050,.13),(.048,.146),(.041,.145),(.036,.025),(.01,.02)],TENMOKU,20,.018)
        for j in range(8):
            a=j*2.399;rr=.026*math.sqrt((j+.5)/8)
            xx=x+rr*math.cos(a);yy=y+rr*math.sin(a)
            c.tube([(xx,yy,holder_base+.060),(xx+rr*.24,yy+rr*.24,holder_base+.225+(j%3)*.012)],[.0023,.0015],BAMBOO,5)
    if idx==4:
        # The two existing tea tables keep their footprints and gain tiny trays.
        for side in [-1,1]:
            x=side*2.5;z=c.tray((x,.2,.553),.54,.38)
            _teapot(c,(x-.115,.20,z),.064,TENMOKU)
            c.cup((x+.12,.13,z),.038,.055,INDIGO)
    after=sum(len(b['f']) for b in g.batches.values())
    return {'shop':f'S{idx+1:02d}','triangles':after-before,'settings':settings,
            'collision_changes':False,'texture_atlas':ATLAS_NAME,'seed':91071+idx*317}


def audit_counter_craft():
    """Small, offline QA for this module; never builds or changes the full world.

    Run ``python Source/counter_craft.py --audit``. The audit verifies finite
    non-degenerate geometry/UVs, unchanged caller RNG, deterministic generation,
    all eight shop configurations, and no placement outside a shop footprint.
    """
    import hashlib
    import json
    from world_geometry import Geometry
    layout_path=Path(__file__).with_name('layout.reference.json')
    shops=json.loads(layout_path.read_text())['shops']
    results=[]
    def fixture(idx):
        g=Geometry();g.group='Shops/'+shops[idx]['id'];m={}
        for key in ['wood','dark','counter','iron','trim','menu']:
            m[key]=g.material('Audit_'+key,(.4,.3,.2))
        p=lambda x,y,z:np.array([x,y,z])
        b=lambda x,y,z,w,d,h,mat:g.box(p(x,y,z),(w,d,h),mat)
        rng=np.random.default_rng(44821);state=json.dumps(rng.bit_generator.state,sort_keys=True)
        report=add_counter_craft(g,p,b,shops[idx]['width'],shops[idx]['depth'],idx,m,rng)
        assert state==json.dumps(rng.bit_generator.state,sort_keys=True),'Caller RNG changed'
        digest=hashlib.sha256()
        collapsed=0;degenerate=0;count=0
        all_v=[]
        for (group,mat),batch in g.batches.items():
            v=np.asarray(batch['v']);f=np.asarray(batch['f']);uv=np.asarray(batch['uv'])
            assert np.isfinite(v).all() and np.isfinite(uv).all(),'Non-finite mesh value'
            assert f.min()>=0 and f.max()<len(v),'Out-of-bounds triangle index'
            q=v[f];area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
            degenerate+=int(np.sum(area<1e-11))
            if mat=='CraftSurfaces':
                u=uv[f];e=u[:,1]-u[:,0];h=u[:,2]-u[:,0]
                collapsed+=int(np.sum(np.abs(e[:,0]*h[:,1]-e[:,1]*h[:,0])<1e-12))
                assert ((uv>=0)&(uv<=1)).all(),'Atlas UV out of bounds'
            digest.update(group.encode());digest.update(mat.encode())
            for array in [v,f,uv]:digest.update(array.tobytes())
            count+=len(f);all_v.extend(v)
        v=np.asarray(all_v);w=shops[idx]['width'];dep=shops[idx]['depth']
        assert np.min(v[:,2])>=.54,'Prop entered walking-floor height'
        assert np.max(np.abs(v[:,0]))<=w/2-.1,'Prop left the shop sides'
        assert np.min(v[:,1])>=-dep/2+.09,'Prop crossed the rear wall'
        assert np.max(v[:,1])<=dep/2+.07,'Prop left the counter front'
        assert not degenerate,'Degenerate triangles'
        assert not collapsed,'Collapsed atlas tangents'
        return {**report,'vertices':len(v),'degenerate_triangles':degenerate,
                'collapsed_uv_triangles':collapsed,'sha256':digest.hexdigest()}
    for idx in range(8):
        result=fixture(idx);second=fixture(idx)
        assert result['sha256']==second['sha256'],'Non-deterministic generated geometry'
        results.append(result)
    return {'passed':True,'shops':results,'triangles':sum(s['triangles'] for s in results),
            'caller_rng_preserved':True,'full_world_generated':False,
            'collision_or_navigation_modified':False}


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',action='store_true',help='Validate all eight shops without exporting the world')
    parser.add_argument('--textures',type=Path,help='Write the three original shared texture atlases')
    args=parser.parse_args()
    if args.textures:print(json.dumps(counter_craft_textures(args.textures),ensure_ascii=False,indent=2))
    if args.audit:print(json.dumps(audit_counter_craft(),ensure_ascii=False,indent=2))
