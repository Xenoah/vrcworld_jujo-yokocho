"""Eight small, static, dimensional shop signs in existing frontage envelopes.

Additive source geometry only: no fonts, textures, materials, lights, colliders,
station edits, routes, runtime code or global RNG. Local coordinates are metres,
Z up; the blade faces are local +/-X so they read along a street approach.
"""
import math
import numpy as np
from shapely.geometry import Polygon
from shapely.affinity import scale as scale_polygon
from world_geometry import poly_mesh, Geometry
from timber_craft import timber_box_mesh

VERSION = 'venue-projecting-signs-3'
MOTIFS = ('dragon_ember', 'noodle_guild', 'traveler_pot', 'witch_hat',
          'moon_tea_timber', 'star_distillery', 'bard_lyre', 'fairy_confection')
FOOTPRINTS = ((6., 5.4), (6., 5.4), (4.8, 5.4), (6., 5.4),
              (7.2, 6.), (6., 5.4), (6., 5.4), (6., 5.4))
# All values are absolute shop-local bounds, not world-space safety claims.
# A 2.30 m minimum exceeds the authored 2.2 m route envelope + .06 m datum.
MIN_Z = 2.30


def _circle(r, n=24, center=(0., 0.)):
    return Polygon([(center[0]+r*math.cos(math.tau*j/n),
                     center[1]+r*math.sin(math.tau*j/n)) for j in range(n)])


def _ellipse(rx, ry, n=24, center=(0., 0.)):
    return Polygon([(center[0]+rx*math.cos(math.tau*j/n),
                     center[1]+ry*math.sin(math.tau*j/n)) for j in range(n)])


def _ring(rx, ry, wall=.014, center=(0., 0.), n=24):
    return _ellipse(rx, ry, n, center).difference(_ellipse(rx-wall, ry-wall, n, center))


class _Sign:
    def __init__(self, g, P, idx, M, w, dep):
        self.g, self.P, self.idx, self.M = g, P, idx, M
        self.w, self.dep = w, dep
        self.root = f'Shops/S{idx+1:02d}/ProjectingSigns'
        self.part_rows = {}
        self.roles = {}
        self.before = set(g.batches)
        self.world_origin = np.asarray(P(0., 0., 0.), float)
        self.basis = np.column_stack([np.asarray(P(*q), float)-self.world_origin
                                     for q in [(1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]])
        # This API is a rigid shop frame, not a deformed or mirrored coordinate map.
        if not np.allclose(self.basis.T@self.basis, np.eye(3), atol=1e-9) or np.linalg.det(self.basis)<.999:
            raise ValueError('Projecting signs require a right-handed rigid shop frame')

    def section(self, semantic, role):
        group = self.root+'/'+semantic
        self.g.group = group
        self.roles[group] = role

    def material(self, name):
        name = self.M.get(name, name)
        if name not in self.g.materials:
            raise ValueError('Projecting sign requires existing material '+name)
        return name

    def add(self, vertices, faces, material, uv=None):
        local = np.asarray(vertices, float)
        self.g.add([self.P(*p) for p in local], faces, self.material(material), uv)

    def box(self, center, size, material, bevel=.004):
        # Existing craft UVs preserve genuine member grain on broad faces.
        v, f, uv = timber_box_mesh(center, size, bevel=bevel)
        self.add(v, f, material, uv)

    def wire(self, points, radius, material, n=6):
        # Author the polygonal tube in the shop frame, then transform it once.
        # World-up tube reference axes otherwise rotate vertical cross sections
        # differently when a venue is yawed, corrupting source-local invariants.
        temporary=Geometry()
        temporary.tube(points,[radius]*len(points),self.material(material),n)
        batch=next(iter(temporary.batches.values()))
        self.add(batch['v'],batch['f'],material,batch['uv'])

    def bar(self, a, b, radius, material, n=8):
        self.wire([a,b],radius,material,n)

    def plate(self, shape, center, thickness, material):
        """Closed true extrusion. Independent face/edge vertices retain flat faces."""
        if shape.is_empty or not shape.is_valid:
            raise ValueError('Invalid sign silhouette')
        vv, ff = poly_mesh(shape, thickness/2, thickness)
        x, y, z = center
        # A cyclic permutation preserves winding: (u, v, depth) -> (x, y, z).
        local = np.column_stack([x+vv[:, 2], y+vv[:, 0], z+vv[:, 1]])
        self.add(local, ff, material, vv[:, :2])

    def relief(self, shape, center, thickness, material, body_depth):
        x, y, z = center
        for side in (-1, 1):
            self.plate(shape, (x+side*(body_depth/2+thickness/2-.002), y, z), thickness, material)

    def bracket(self, x, y, top=2.78, reach=.51, material='iron'):
        """Post-mounted flat base, cantilever and diagonal return, all real solids."""
        self.section('PostBracket', 'structural_support')
        post_x = -self.w/2+.10
        side = -1 if x < post_x else 1
        # Base fixes through the outside face of the existing left front post.
        self.box((post_x+side*.094, y+.015, top-.135), (.028, .12, .28), material, .002)
        self.bar((post_x+side*.100, y+.015, top), (x, y+.015, top), .015, material)
        self.bar((x, y+.015, top), (x, y+reach, top), .015, material)
        self.bar((post_x+side*.100, y+.015, top-.18), (x, y+.21, top-.025), .013, material)
        for zz in (top-.235, top-.155):
            self.bar((post_x+side*.100, y+.015, zz), (post_x+side*.120, y+.015, zz), .012, 'trim', 8)

    def hangers(self, x, ys, upper, lower, material='trim'):
        self.section('Suspension', 'suspension_hardware')
        for y in ys:
            self.bar((x, y, upper), (x, y, lower), .009, material, 8)
            # Flat, closed oval eyelets show real contact at the top of a sign.
            self.plate(_ring(.025, .027, .009, n=12), (x, y, lower+.002), .020, material)

    def metadata(self):
        keys = [k for k in self.g.batches if k not in self.before]
        parts=[]
        for group in self.roles:
            owned=[k for k in keys if k[0]==group]
            if not owned:continue
            world=np.concatenate([np.asarray(self.g.batches[k]['v']) for k in owned])
            local=np.round((world-self.world_origin)@self.basis, 12)
            lo, hi = local.min(axis=0), local.max(axis=0)
            parts.append(dict(group=group, role=self.roles[group],
                localBounds=[lo.tolist(), hi.tolist()], dimensions=(hi-lo).tolist(),
                triangles=sum(len(self.g.batches[k]['f']) for k in owned),
                sourceVertexCount=sum(len(self.g.batches[k]['v']) for k in owned),
                materials=[k[1] for k in owned]))
        lo=np.min([p['localBounds'][0] for p in parts],axis=0)
        hi=np.max([p['localBounds'][1] for p in parts],axis=0)
        return dict(version=VERSION, shop=f'S{self.idx+1:02d}', motif=MOTIFS[self.idx],
            coordinates='shop-local Z-up metres', root=self.root,
            localBounds=[lo.tolist(), hi.tolist()], dimensions=(hi-lo).tolist(),
            triangleCount=sum(p['triangles'] for p in parts),
            sourceVertexCount=sum(p['sourceVertexCount'] for p in parts), batchCount=len(keys),
            keys=[list(k) for k in keys], parts=parts,
            static=True, collisionApplied=False, addedLights=0, addedMaterials=0,
            testedInUnity=False, testedInVRChat=False)


def _tea(s):
    # A framed, inset, quarter-sawn-looking blade, not a recolored print plane.
    x=-s.w/2-.10; y=s.dep/2+.385; z=2.515
    s.bracket(x, s.dep/2-.08, top=2.765, reach=.78)
    s.hangers(x, [y-.195, y+.195], 2.765, 2.716)
    s.section('MoonTeaTimber', 'dimensional_emblem')
    # Thin light timber infill is housed inside four darker proud rails.
    s.box((x,y,z),(.067,.512,.310),'Food_Chestnut',.004)
    for zz in (-.178,.178):s.box((x,y,z+zz),(.092,.608,.044),'Food_Chestnut',.004)
    for yy in (-.282,.282):s.box((x,y+yy,z),(.092,.044,.318),'Food_Chestnut',.004)
    # Four through-pegs at the mortised rail ends, readable from both sides.
    for yy in (-.276,.276):
        for zz in (-.172,.172):
            s.bar((x-.052,y+yy,z+zz),(x+.052,y+yy,z+zz),.011,'Food_PaleJoinery',8)
    # A moon hovers over a teacup. Both silhouettes are genuinely raised wood.
    moon=_circle(.088,24,(-.13,.047)).difference(_circle(.078,24,(-.098,.067)))
    s.relief(moon,(x,y,z),.016,'Food_PaleJoinery',.067)
    cup=Polygon([(-.04,.012),(.146,.012),(.124,-.072),(.105,-.086),(.005,-.086),(-.018,-.071)])
    s.relief(cup,(x,y,z),.015,'Food_PaleJoinery',.067)
    handle=_ring(.039,.034,.012,center=(.143,-.024),n=16)
    s.relief(handle,(x,y,z),.015,'Food_PaleJoinery',.067)
    saucer=Polygon([(-.036,-.100),(.165,-.100),(.143,-.113),(-.015,-.113)])
    s.relief(saucer,(x,y,z),.014,'Food_PaleJoinery',.067)
    for side in (-1,1):
        xx=x+side*.042
        s.wire([(xx,y+.050,z+.029),(xx,y+.036,z+.057),(xx,y+.049,z+.080)],.005,'Food_PaleJoinery',6)


def add_signs(g, P, idx, M, w, dep):
    """Append one venue's approved decorative addition, then restore g.group.

    Must be called once per venue, after the existing venue geometry. Existing
    batches and material descriptors remain unchanged, even on a repeated call:
    a duplicate owned namespace is rejected before it can append anything.
    """
    if type(idx) is not int or idx not in range(8):raise ValueError('idx must be integer 0..7')
    if not np.allclose((w, dep), FOOTPRINTS[idx], atol=1e-9, rtol=0):
        raise ValueError('Review sign envelope before changing venue dimensions')
    root=f'Shops/S{idx+1:02d}/ProjectingSigns'
    if any(k[0]==root or k[0].startswith(root+'/') for k in g.batches):
        raise ValueError('Projecting signs already authored for this venue')
    previous=g.group
    try:
        s=_Sign(g,P,idx,M,w,dep)
        _BUILDERS[idx](s)
        result=_consolidate(g,s.metadata())
        if result['localBounds'][0][2]<MIN_Z-1e-8:raise ValueError('Sign falls below 2.30 m')
        return result
    finally:
        g.group=previous


def _flag(s, center, width, height, kind, material):
    """A modest static folded cloth, closed 4 mm shell, never a one-sided quad."""
    x,y,top=center
    s.section('GuildPennant', 'static_cloth_pennant')
    # The bar is fastened to an existing eave/front post by a short return.
    s.bar((x-width*.63,y,top+.016),(x+width*.63,y,top+.016),.009,'trim',8)
    anchor_z=2.91 if s.idx==7 else 2.70
    s.bar((x,s.dep/2,anchor_z),(x,y,top+.016),.011,'iron',8)
    if kind=='forked':
        outline=[(-width/2,0),(-width/2,-height),(0,-height*.75),
                 (width/2,-height),(width/2,0)]
    elif kind=='pointed':
        outline=[(-width/2,0),(-width/2,-height*.79),(0,-height),
                 (width/2,-height*.79),(width/2,0)]
    elif kind=='scalloped':
        outline=[(-width/2,0),(-width/2,-height*.88)]
        for j in range(1,13):
            u=-width/2+width*j/12
            outline.append((u,-height*.88-height*.12*abs(math.sin(math.pi*j/4))))
        outline.append((width/2,0))
    else:raise ValueError(kind)
    polygon=Polygon(outline)
    vv,ff=poly_mesh(polygon,.002,.004)
    # One subdivision supplies enough interior samples for broad folds, not a
    # densely tessellated cloth or animation. Every edge is split consistently.
    subdivided=[]; triangles=[]
    for face in ff:
        a,b,c=vv[face];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
        for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):
            start=len(subdivided);subdivided.extend(tri);triangles.append((start,start+1,start+2))
    vv=np.asarray(subdivided);ff=np.asarray(triangles)
    local=[]
    for u,v,t in vv:
        fold=.017*math.sin((u/width+.5)*math.tau+.30)*(min(1,abs(v)/height)*.75+.25)
        local.append((x+u,y+fold+t,top+v))
    # (u,v,depth) -> (x,depth,z) is a reflection: reverse winding.
    # Four UV repeats per metre: fixed weave96 gives about 2.6 mm periods.
    s.add(local,ff[:,::-1],material,[(4*u,4*v) for u,v,t in vv])
    # Three stitched-looking, solid 8 mm textile loops visibly catch the bar.
    for u in (-width*.32,0,width*.32):
        v,f,uv=timber_box_mesh((x+u,y,top+.004),(.018,.027,.031),bevel=.002)
        s.add(v,f,material,uv*4)


def _dragon(s):
    x=-s.w/2-.10;y=s.dep/2+.37;z=2.51
    s.bracket(x,s.dep/2-.08,2.81,.74)
    s.hangers(x,[y-.17,y+.17],2.81,2.736)
    s.section('DragonEmberShield','dimensional_emblem')
    shield=Polygon([(-.255,.145),(-.20,.222),(.20,.222),(.255,.145),(.224,-.11),(0,-.195),(-.224,-.11)])
    s.plate(shield,(x,y,z),.075,'Food_Charcoal')
    # Carved bronze dragon: swept neck, long snout, two horns and wing, not print.
    dragon=Polygon([(-.177,-.112),(-.081,-.099),(.024,-.044),(.071,.027),(.040,.071),
        (.066,.116),(.134,.121),(.175,.103),(.166,.161),(.115,.153),(.079,.199),
        (.052,.136),(-.010,.099),(-.038,.037),(-.011,-.008),(-.046,-.039),
        (-.105,-.013),(-.177,.071),(-.155,-.050),(-.198,-.073)])
    s.relief(dragon,(x,y,z),.020,'Food_Copper',.075)
    coal=Polygon([(.11,-.034),(.141,-.008),(.153,-.055),(.134,-.095),(.098,-.089),(.081,-.061)])
    s.relief(coal,(x,y,z),.024,'Food_Oxblood',.075)


def _noodle(s):
    x=-s.w/2-.10;y=s.dep/2+.42;z=2.466
    s.bracket(x,s.dep/2-.065,2.640,.70)
    s.hangers(x,[y-.16,y+.16],2.640,2.566)
    s.section('NoodleGuildBowl','dimensional_emblem')
    bowl=Polygon([(-.243,.075),(.243,.075),(.188,-.087),(.125,-.143),(-.125,-.143),(-.188,-.087)])
    s.plate(bowl,(x,y,z),.083,'Food_Enamel')
    rim=Polygon([(-.248,.089),(.248,.089),(.242,.048),(-.242,.048)])
    s.plate(rim,(x,y,z),.102,'Food_TileGreen')
    foot=Polygon([(-.116,-.141),(.116,-.141),(.133,-.154),(-.133,-.154)])
    s.plate(foot,(x,y,z),.089,'Food_TileGreen')
    # Two raised noodles are explicit bent ceramic rods on each face.
    for side in (-1,1):
        xx=x+side*.052
        for offset in (-.055,.042):
            s.wire([(xx,y+offset-.030,z+.034),(xx,y+offset-.055,z+.089),
                    (xx,y+offset-.023,z+.124),(xx,y+offset+.004,z+.148)],.008,'Food_TileCream',6)
    _flag(s,(-s.w/2+.78,s.dep/2+.64,2.704),.30,.385,'forked','Noren3')


def _traveler(s):
    x=-s.w/2-.10;y=s.dep/2+.445;z=2.496
    s.bracket(x,s.dep/2-.08,2.79,.64)
    s.hangers(x,[y],2.79,2.736)
    s.section('TravelerPotLantern','dimensional_emblem')
    body=Polygon([(-.19,.088),(-.171,-.061),(-.115,-.128),(.115,-.128),(.171,-.061),(.19,.088)])
    s.plate(body,(x,y,z),.142,'Food_Copper')
    lid=Polygon([(-.209,.089),(-.174,.118),(-.056,.140),(.056,.140),(.174,.118),(.209,.089)])
    s.plate(lid,(x,y,z),.157,'Food_Chestnut')
    s.plate(_ring(.137,.111,.018,center=(0,.140),n=18),(x,y,z),.025,'trim')
    for side in (-1,1):
        # A tiny warm-color flame relief identifies the travelers' hearth.
        flame=Polygon([(0,-.072),(-.046,-.026),(-.015,.038),(.001,.083),(.049,.005),(.038,-.043)])
        s.plate(flame,(x+side*.083,y,z),.022,'Food_TileCream')
    # Two stout cast feet make this an actual pot form rather than a rectangle.
    for yy in (-.104,.104):s.box((x,y+yy,z-.146),(.135,.050,.035),'Food_Chestnut',.003)


def _witch(s):
    x=-s.w/2-.10;y=s.dep/2+.43;z=2.465
    s.bracket(x,s.dep/2-.07,2.77,.72)
    # A single eye catches the actual pointed hat apex, not empty silhouette.
    s.hangers(x,[y+.016*.72],2.77,2.630)
    s.section('WitchMoonHat','dimensional_emblem')
    def small(shape):return scale_polygon(shape,xfact=.72,yfact=.72,origin=(0,0))
    crescent=small(_circle(.205,28).difference(_circle(.175,28,(.066,.048))))
    s.plate(crescent,(x,y,z),.061*.72,'trim')
    hat=small(Polygon([(-.212,-.065),(.218,-.065),(.161,-.026),(.082,.163),(.016,.204),
                 (.023,.127),(-.051,.012),(-.116,-.031)]))
    s.plate(hat,(x,y,z),.101*.72,'night_walnut')
    band=small(Polygon([(-.084,-.009),(.137,-.009),(.147,-.034),(-.100,-.034)]))
    s.relief(band,(x,y,z),.014*.72,'night_wine',.101*.72)
    _flag(s,(-s.w/2+.60,s.dep/2+.57,2.600),.265,.276,'pointed','night_wine')


def _distillery(s):
    x=-s.w/2-.10;y=s.dep/2+.38;z=2.512
    s.bracket(x,s.dep/2-.07,2.79,.72)
    s.hangers(x,[y],2.79,2.748)
    s.section('StarDistilleryBottle','dimensional_emblem')
    bottle=Polygon([(-.137,-.197),(.137,-.197),(.137,.017),(.057,.093),(.057,.206),
                    (-.057,.206),(-.057,.093),(-.137,.017)])
    s.plate(bottle,(x,y,z),.125,'night_glass')
    s.box((x,y,z+.207),(.139,.125,.037),'trim',.003)
    rays=[]
    for j in range(8):
        a=math.pi/2+math.pi*j/4;r=.115 if j%2==0 else .031
        rays.append((r*math.cos(a),r*math.sin(a)-.052))
    star=Polygon(rays)
    s.relief(star,(x,y,z),.021,'Food_TileCream',.125)
    collar=_ring(.102,.102,.009,center=(0,-.052),n=24)
    s.relief(collar,(x,y,z),.012,'trim',.125)


def _bard(s):
    x=-s.w/2-.10;y=s.dep/2+.41;z=2.501
    s.bracket(x,s.dep/2-.07,2.78,.67)
    s.hangers(x,[y-.15,y+.15],2.78,2.732)
    s.section('BardOpenLyre','dimensional_emblem')
    # Open silhouette and real strings; the former printed crest is untouched.
    outer=Polygon([(-.239,.215),(-.210,-.025),(-.163,-.135),(-.078,-.192),
                   (.078,-.192),(.163,-.135),(.210,-.025),(.239,.215),(.162,.215),
                   (.137,.003),(.090,-.099),(-.090,-.099),(-.137,.003),(-.162,.215)])
    s.plate(outer,(x,y,z),.083,'night_walnut')
    s.box((x,y,z+.172),(.071,.420,.044),'trim',.003)
    for u in (-.108,-.054,0,.054,.108):
        s.bar((x,y+u,z-.108),(x,y+u,z+.182),.005,'trim',6)
    for u in (-.194,.194):s.plate(_circle(.032,12),(x,y+u,z+.194),.099,'trim')


def _fairy(s):
    x=-s.w/2-.10;y=s.dep/2+.395;z=2.522
    s.bracket(x,s.dep/2-.08,2.79,.70)
    s.hangers(x,[y-.15,y+.15],2.79,2.717)
    s.section('FairyConfectionCrest','dimensional_emblem')
    # Four pierced wings flank a softly tapered confectioner's cake emblem.
    for side in (-1,1):
        wing=_ellipse(.10,.105,18,(side*.145,.075))
        inner=_ellipse(.073,.078,18,(side*.145,.075))
        s.plate(wing.difference(inner),(x,y,z),.038,'Food_Chestnut')
        wing=_ellipse(.076,.072,16,(side*.116,-.085))
        inner=_ellipse(.052,.048,16,(side*.116,-.085))
        s.plate(wing.difference(inner),(x,y,z),.038,'Food_Chestnut')
    cake=Polygon([(-.092,.025),(.092,.025),(.073,-.141),(-.073,-.141)])
    s.plate(cake,(x,y,z),.101,'Food_Enamel')
    icing=Polygon([(-.105,.026),(-.086,.062),(-.052,.061),(-.025,.085),(.018,.083),
                   (.047,.061),(.081,.063),(.106,.026)])
    s.plate(icing,(x,y,z),.112,'Food_TileCream')
    s.plate(_circle(.021,12,(0,.114)),(x,y,z),.117,'Food_Oxblood')
    s.box((x,y,z-.162),(.12,.233,.033),'Food_Chestnut',.003)
    _flag(s,(s.w/2-.81,s.dep/2+.295,2.744),.30,.402,'scalloped','Noren1')


_BUILDERS = (_dragon, _noodle, _traveler, _witch, _tea, _distillery, _bard, _fairy)


def _consolidate(g, report):
    """Geometry-exact same-material concatenation of only this new assembly.

    A source component/range ledger retains the meaning of support, suspension,
    emblems and pennants without charging one draw per component/material pair.
    No welding, normal changes, material changes, UV edits or triangle drops.
    """
    oldkeys=[tuple(k) for k in report['keys']]
    labels=('DragonEmberAssembly','NoodleGuildAssembly','TravelerPotAssembly',
            'WitchMoonAssembly','MoonTeaTimberAssembly','StarDistilleryAssembly',
            'BardLyreAssembly','FairyConfectionAssembly')
    idx=int(report['shop'][1:])-1
    group=report['root']+'/'+labels[idx]
    combined={};ranges={}
    for oldkey in oldkeys:
        material=oldkey[1];key=(group,material);old=g.batches[oldkey]
        if set(old)!={'v','f','uv'}:raise ValueError('Unreviewed sign batch payload')
        target=combined.setdefault(key,dict(v=[],f=[],uv=[]))
        first=len(target['v']);facefirst=len(target['f'])
        target['v'].extend(old['v']);target['uv'].extend(old['uv'])
        target['f'].extend((np.asarray(old['f'],dtype=np.int64)+first).tolist())
        ranges[oldkey]=dict(key=list(key),vertexStart=first,vertexCount=len(old['v']),
                           triangleStart=facefirst,triangleCount=len(old['f']))
    components=[]
    for part in report['parts']:
        component={k:v for k,v in part.items() if k not in ('group','materials')}
        component['semantic']=part['group'].rsplit('/',1)[-1]
        component['ranges']=[ranges[(part['group'],m)] for m in part['materials']]
        components.append(component)
    for key in oldkeys:del g.batches[key]
    g.batches.update(combined)
    report['keys']=[list(k) for k in combined]
    report['batchCount']=len(combined)
    report['parts']=[dict(group=group,role='dimensional_emblem',
        localBounds=report['localBounds'],dimensions=report['dimensions'],
        triangles=report['triangleCount'],sourceVertexCount=report['sourceVertexCount'],
        materials=[k[1] for k in combined],
        components=components)]
    report['consolidation']=dict(method='exact_same_material_concatenation',
        originalBatchCount=len(oldkeys),removedBatchCount=len(oldkeys)-len(combined),
        geometryWelded=False,sourceComponentRanges=True)
    return report
