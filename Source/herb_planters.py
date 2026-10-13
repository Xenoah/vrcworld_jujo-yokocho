"""Eight modest shop-corner planters. Source units are metres, Z-up.

No layout, collision, station or texture writes. The supplied RNG is advanced
exactly ten scalar draws, matching legacy plant(); all craft uses a private RNG.
Static leaf materials deliberately avoid the large canopy's global wind shader:
short potted herbs remain wholly inside the legacy plant's static footprint.
"""
import math
import re
import numpy as np

SPECIES = ('shiso', 'chives', 'mitsuba', 'sansho', 'shiso', 'mitsuba', 'chives', 'sansho')


def _materials(g):
    # Every image already ships with the world. No additional texture files.
    clay = []
    for name, color in [('HerbClayOchre', (.62, .36, .20)),
                        ('HerbClayUmber', (.38, .30, .23))]:
        if name not in g.materials:
            g.material(name, color, roughness=.94,
                       normal='tile_clay_normal.png', arm='tile_clay_arm.png',
                       normalScale=.45)
        clay.append(name)
    if 'HerbSoil' not in g.materials:
        g.material('HerbSoil', (.22, .17, .105),
                   'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1,
                   uvScale=3, normal='PBR/rocky_terrain_02_nor_gl_2k.jpg',
                   normalScale=.40)
    leaves = []
    for name, color in [('HerbLeafDeep', (.48, .61, .39)),
                        ('HerbLeafYoung', (.66, .73, .45))]:
        if name not in g.materials:
            g.material(name, color, 'leaf.png', roughness=.87,
                       normal='leaf_detail_normal.png', arm='leaf_detail_arm.png',
                       normalScale=.35)
        leaves.append(name)
    return clay, leaves


def _pot(g, p, size, material, phase):
    # Continuous cross-section travels under the foot, up the outside, over the
    # rolled lip and down the inside. The opening is genuinely hollow.
    profile = [(0, 0), (.134, 0), (.146, .017), (.146, .034),
               (.151, .042), (.190, .175), (.210, .235), (.211, .250),
               (.229, .253), (.235, .265), (.232, .278), (.216, .283),
               (.207, .276), (.207, .261), (.193, .239), (.177, .168),
               (.140, .055), (0, .055)]
    v, f, uv = [], [], []
    n = 28
    for row, (radius, z) in enumerate(profile):
        for j in range(n+1):
            a = j*math.tau/n
            # Subtle hand-thrown wobble, no chipped or broken silhouette.
            wobble = (1+.012*math.sin(3*a+phase)+.006*math.sin(7*a-phase))
            wobble *= 1+.024*math.sin(phase)*math.sin(math.pi*z/.283)
            dz = (.0018*math.sin(2*a+phase)*min(radius/.15, 1)) if z>.01 else 0
            v.append(p+size*np.array([radius*wobble*math.cos(a),
                                     radius*wobble*math.sin(a), z+dz]))
            uv.append((j/n, z*2))
            if row and j:
                k=row*(n+1)+j
                if profile[row-1][0] == 0:
                    f.append((k-n-2, k, k-1))
                elif radius == 0:
                    f.append((k-n-2, k-n-1, k))
                else:
                    f.extend([(k-n-2, k-n-1, k), (k-n-2, k, k-1)])
    g.add(v, f, material, uv)
    # Slightly settled, granular soil stays visibly below the rolled rim.
    v = [p+size*np.array([0, 0, .234])]
    uv = [(.5, .5)]
    f=[]
    for ring in range(1,4):
        rad=.193*ring/3
        for j in range(n):
            a=j*math.tau/n
            z=.232+.0024*math.sin(5*a+phase+ring)*math.sin(ring*1.1)
            v.append(p+size*np.array([rad*math.cos(a),rad*math.sin(a),z]))
            uv.append((.5+rad/.386*math.cos(a),.5+rad/.386*math.sin(a)))
            k=1+(ring-1)*n+j;nxt=1+(ring-1)*n+(j+1)%n
            if ring==1:f.append((0,k,nxt))
            else:f.extend([(k-n,k,nxt),(k-n,nxt,nxt-n)])
    g.add(v,f,'HerbSoil',uv)
    # Twelve tiny porous aggregates, same material and existing scan. These
    # catch grazing light without a carpet of expensive stones or a new atlas.
    for j in range(12):
        a=phase+j*2.399963;r=.06+.095*(.5+.5*math.sin(j*5.7+phase))
        c=p+size*np.array([math.cos(a)*r,math.sin(a)*r,.234])
        s=(.004+.004*(.5+.5*math.sin(j*3.8+phase)))*size
        q=np.array([[-1,0,0],[0,-.8,0],[1,0,0],[0,1,0],[0,0,.75],[0,0,-.5]])*s+c
        faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4),
               (1,0,5),(2,1,5),(3,2,5),(0,3,5)]
        g.add(q,faces,'HerbSoil',[(0,0),(.3,0),(.3,.3),(0,.3),(.15,.15),(.15,.15)])



def _lamina(g, v, f, material, uv):
    # Both faces exist with independent normals. This does not rely on the
    # importer honoring glTF-only doubleSided metadata for Surface materials.
    n=len(v)
    g.add(list(v)+list(v), list(f)+[(c+n,b+n,a+n) for a,b,c in f],
          material, list(uv)+list(uv))


def _leaf(g, base, tip, width, material, serration=0, lobes=0):
    """Curved lamina with restrained shared-texture veins and shaped silhouette."""
    d=tip-base;length=float(np.linalg.norm(d));along=d/length
    side=np.cross(along, [0, 0, 1.])
    if np.linalg.norm(side)<.05: side=np.array([1., 0, 0])
    side/=np.linalg.norm(side)
    normal=np.cross(side, along)
    if normal[2]<0:normal=-normal
    v=[];uv=[];faces=[];steps=8 if serration or lobes else 6
    # Single vertices at the tips avoid the old collapsed end triangles.
    for i in range(steps+1):
        t=i/steps
        mid=base+d*t+normal*(math.sin(math.pi*t)*length*.085)
        if i in (0, steps):
            v.append(mid);uv.append((.5, .04+.92*t))
            continue
        w=width*math.sin(math.pi*t)**(.74 if lobes else 1.05)
        w*=1+serration*(-1)**i+lobes*math.cos(t*math.pi*6)
        for k in (-1, 0, 1):
            v.append(mid+side*w*k-normal*abs(k)*length*.045)
            uv.append((.5+k*.46, .04+.92*t))
    faces.extend([(0, 1, 2), (0, 2, 3)])
    for i in range(steps-2):
        k=1+i*3
        faces.extend([(k, k+3, k+4), (k, k+4, k+1),
                      (k+1, k+4, k+5), (k+1, k+5, k+2)])
    k=1+(steps-2)*3;end=len(v)-1
    faces.extend([(k, end, k+1), (k+1, end, k+2)])
    # Independent front/back vertices keep the thin folded leaves visible.
    _lamina(g, v, faces, material, uv)


def _herbs(g, p, size, species, leaves, rng, phase):
    def pt(x): return p+np.asarray(x)*size
    def stem(points, r=.004):
        g.tube([pt(x) for x in points], [r*size*(1-.7*i/(len(points)-1))
               for i in range(len(points))], 'DarkTimber' if species=='sansho' else leaves[0], 5)
    def blade(b, t, w, material, serration=0, lobes=0):
        _leaf(g, pt(b), pt(t), w*size, material, serration, lobes)
    if species == 'chives':
        # Eighteen upright narrow allium blades, gently bent tips; no flowers.
        for j in range(18):
            a=j*2.399963+phase;rad=.034+.045*rng.random()
            root=np.array([rad*math.cos(a), rad*math.sin(a), .227])
            h=.30+.23*rng.random();lean=.065+.055*rng.random()
            mid=root+np.array([math.cos(a)*lean*.40, math.sin(a)*lean*.40, h*.63])
            tip=root+np.array([math.cos(a)*lean, math.sin(a)*lean, h])
            # Folded strap blade rather than round spaghetti tube.
            side=np.array([-math.sin(a), math.cos(a), 0])*.008
            v=[];uv=[];ff=[]
            for k in range(6):
                t=k/5;q=(1-t)**2*root+2*(1-t)*t*mid+t*t*tip
                w=(1-t*.91)*(.65+.35*math.sin(t*math.pi))
                for s in (-1,0,1):
                    v.append(pt(q+side*w*s+np.array([0,0,.0025*(1-abs(s))])))
                    uv.append((.5+s*.46, t))
                if k:
                    q0=(k-1)*3
                    ff.extend([(q0,q0+3,q0+4),(q0,q0+4,q0+1),
                               (q0+1,q0+4,q0+5),(q0+1,q0+5,q0+2)])
            _lamina(g, v, ff, leaves[j%2], uv)
        return
    count={'shiso':5, 'mitsuba':5, 'sansho':4}[species]
    for j in range(count):
        a=phase+j*2.399963;rad=.035+.027*rng.random()
        h=.33+.13*rng.random();spread=.07+.035*rng.random()
        root=np.array([math.cos(a)*rad, math.sin(a)*rad, .227])
        top=root+np.array([math.cos(a)*spread, math.sin(a)*spread, h])
        mid=root+(top-root)*.48+np.array([-.014*math.sin(a),.014*math.cos(a),0])
        stem([root,mid,top], .0045 if species=='sansho' else .0055)
        if species=='sansho':
            # Pinnate sprigs with opposite small oval leaflets and one tip leaf.
            for level in (.49, .83):
                b=root+(top-root)*level
                aa=a+(.65 if level<.6 else -.55)
                axis=np.array([math.cos(aa)*.135, math.sin(aa)*.135, .038])
                stem([b,b+axis],.0024)
                side=np.array([-math.sin(aa),math.cos(aa),.18])
                for t in (.26,.51,.74):
                    for sign in (-1,1):
                        q=b+axis*t
                        end=q+side*sign*(.045-.011*t)+axis*.08
                        blade(q,end,.014,leaves[(j+int(t*10))%2],.07)
                blade(b+axis*.83,b+axis*1.13,.016,leaves[j%2])
        elif species=='mitsuba':
            for level in (.58,.94):
                b=root+(top-root)*level
                for k in (-1,0,1):
                    aa=a+k*.80
                    reach=.092 if k else .116
                    q=b+np.array([math.cos(aa)*.02,math.sin(aa)*.02,.018])
                    end=q+np.array([math.cos(aa)*reach,math.sin(aa)*reach,.025])
                    stem([b,q],.0022)
                    blade(q,end,.034,leaves[(j+1)%2],.08,.14)
        else:
            for li,level in enumerate((.38,.67,1.0)):
                b=root+(top-root)*level
                for sign in (-1,1):
                    aa=a+li*1.55+(0 if sign>0 else math.pi)
                    reach=(.12-.022*li)*(1+.12*rng.random())
                    petiole=np.array([math.cos(aa)*.021,math.sin(aa)*.021,.007])
                    q=b+petiole
                    end=q+np.array([math.cos(aa)*reach,math.sin(aa)*reach,.041 if li==2 else .029-.014*li])
                    stem([b,q],.0025)
                    blade(q,end,reach*.37,leaves[(j+li)%2],.12)


def add_herb_planter(g, pos, size=.8, rng=None):
    """Drop-in plant geometry; g.group and all non-plant state are preserved."""
    # Preserve not just count but exact scalar call behavior of old plant().
    if rng is not None:
        for _ in range(10): rng.random()
    p=np.asarray(pos,dtype=float)
    match=re.search(r'(?:^|/)S(\d{2})(?:/|$)', g.group)
    idx=(int(match.group(1))-1)%8 if match else 0
    local=np.random.default_rng(87441+idx*7919)
    clay, leaves=_materials(g)
    phase=float(local.random()*math.tau)
    _pot(g,p,size,clay[(idx//2)%2],phase)
    _herbs(g,p,size,SPECIES[idx],leaves,local,phase)
