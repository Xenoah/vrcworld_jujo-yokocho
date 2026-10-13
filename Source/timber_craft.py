"""Hand-finished near architecture, in source metres / Z up.

Chamfered timber is a visual replacement only. The existing full box remains
the collision envelope, so these rounded edges cannot open a walking hole.
The UV grain follows the member's long axis, instead of turning 90 degrees
between a post and a lintel. No new textures or shader variants are needed.
"""
import itertools
import math
import numpy as np


def timber_box_mesh(center, size, axes=None, bevel=.006):
    """Return a closed 44-triangle, flat-face chamfered cuboid and metre UVs."""
    center = np.asarray(center, float)
    size = np.asarray(size, float)
    basis = np.eye(3) if axes is None else np.asarray(axes, float).T
    extent = size * .5
    bevel = min(float(bevel), float(extent.min()) * .30)
    inner = extent - bevel
    grain = int(np.argmax(size))
    phase = (math.sin(float(center @ [1.179, 2.337, 3.711])) * 43758.5453) % 1
    vertices, faces, uv = [], [], []

    def face(points, outward):
        points = np.asarray(points, float)
        outward = np.asarray(outward, float)
        normal = np.cross(points[1]-points[0], points[2]-points[0])
        if normal @ outward < 0:
            points = points[::-1]
        # A single board is selected across the scan's width; the longitudinal
        # direction remains measured in metres. End faces use the two end axes.
        dominant = int(np.argmax(np.abs(outward)))
        longitudinal = grain if dominant != grain else (grain+1) % 3
        cross = next(a for a in range(3) if a not in (dominant, longitudinal)) if dominant != longitudinal else (longitudinal+1) % 3
        n = len(vertices)
        vertices.extend(points @ basis.T + center)
        for p in points:
            uv.append((p[cross] + .025 + phase*.10,
                       p[longitudinal] + phase*2.7))
        for j in range(1, len(points)-1):
            faces.append((n, n+j, n+j+1))

    # Six planar faces retain independent normals across the twelve bevels.
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for sign in (-1, 1):
            points = []
            for u, v in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                p = np.zeros(3); p[axis] = sign*extent[axis]
                p[others[0]] = u*inner[others[0]]
                p[others[1]] = v*inner[others[1]]
                points.append(p)
            normal = np.zeros(3); normal[axis] = sign
            face(points, normal)
    for a, b in itertools.combinations(range(3), 2):
        along = next(i for i in range(3) if i not in (a,b))
        for sa, sb in itertools.product((-1,1), repeat=2):
            points=[]
            for end, edge in [(-1,0),(-1,1),(1,1),(1,0)]:
                p=np.zeros(3); p[along]=end*inner[along]
                p[a]=sa*(extent[a] if edge == 0 else inner[a])
                p[b]=sb*(inner[b] if edge == 0 else extent[b])
                points.append(p)
            normal=np.zeros(3); normal[a]=sa; normal[b]=sb
            face(points, normal)
    for signs in itertools.product((-1,1), repeat=3):
        signs=np.asarray(signs); points=[]
        for axis in range(3):
            p=signs*inner; p[axis]=signs[axis]*extent[axis]; points.append(p)
        face(points, signs)
    if np.linalg.det(basis) < 0:
        faces=[f[::-1] for f in faces]
    return np.asarray(vertices), np.asarray(faces), np.asarray(uv)


def _half_round_channel(g,P,x0,x1,y,z0,z1,radius,thickness,material,segments=10):
    """Closed thin shell with an open top; source-local X is the run axis."""
    v=[];uv=[];faces=[];n=segments+1
    for surface,r in enumerate((radius,radius-thickness)):
        for row,(x,z) in enumerate(((x0,z0),(x1,z1))):
            for k in range(n):
                a=k*math.pi/segments
                v.append(P(x,y+r*math.cos(a),z-r*math.sin(a)))
                uv.append((x,r*a))
                if row and k:
                    i=surface*2*n+k-1;j=i+n
                    q=[(i,i+1,j+1),(i,j+1,j)]
                    faces.extend([f[::-1] for f in q] if surface==0 else q)
    g.add(v,faces,material,uv)
    # End caps cover only the thin half-annulus, never the channel opening.
    for end in (0,1):
        for k in range(segments):
            ids=[end*n+k,end*n+k+1,(2+end)*n+k+1,(2+end)*n+k]
            q=[v[i] for i in ids];u=[(k*radius/segments,0),((k+1)*radius/segments,0),
                                  ((k+1)*radius/segments,thickness),(k*radius/segments,thickness)]
            if end==1:q=q[::-1];u=u[::-1]
            g.quad(q,material,u)
    for edge in (0,segments):
        ids=[edge,n+edge,3*n+edge,2*n+edge];q=[v[i] for i in ids]
        u=[(x0,0),(x1,0),(x1,thickness),(x0,thickness)]
        if edge==0:q=q[::-1];u=u[::-1]
        g.quad(q,material,u)


def _gutter_end_stop(g,P,x0,x1,y,z,radius,material,segments=10):
    """Thin semicircular stop end: seals the trough end, leaves its top open."""
    v=[];uv=[];faces=[];n=segments+1
    for x in (x0,x1):
        for k in range(n):
            a=k*math.pi/segments;yy=radius*math.cos(a);zz=-radius*math.sin(a)
            v.append(P(x,y+yy,z+zz));uv.append((yy,zz))
    for k in range(1,n-1):
        faces.append((0,k,k+1));faces.append((n,n+k+1,n+k))
    g.add(v,faces,material,uv)
    for k in range(n):
        j=(k+1)%n;q=[v[k],v[n+k],v[n+j],v[j]]
        distance=np.linalg.norm(np.asarray(v[j])-np.asarray(v[k]))
        g.quad(q,material,[(0,0),(x1-x0,0),(x1-x0,distance),(0,distance)])


def add_shop_joinery(g, P, B, w, dep, idx, m, staff_entry=False):
    """Real fastening and drainage detail only where a viewer can inspect it."""
    original=g.group; g.group=original+'/Joinery'
    dark,wood,iron,bronze=m['dark'],m['wood'],m['iron'],m['trim']
    black=m.get('jointShadow',iron)
    # Housed knee braces, tenon ends and dowels. The braces stay above 2.2m
    # and behind the front post line, away from the walk and seated heads.
    for side in (-1,1):
        x=side*(w/2-.10)
        g.beam(P(x,dep/2-.06,2.21),P(x-side*.43,dep/2-.06,2.60),.085,wood,.13)
        B(x,dep/2+.014,2.64,.25,.044,.24,dark)
        B(x+side*.125,dep/2-.025,2.63,.025,.17,.10,wood)
        for z in (2.31,2.61):
            # Wooden pegs are non-emissive, low-gloss and only 18mm across.
            g.tube([P(x,dep/2+.017,z),P(x,dep/2+.048,z)],[.009,.009],wood,8)
        for z in (.18,.39):
            B(x,dep/2+.018,z,.225,.022,.065,iron)
            for dx in (-.072,.072):
                g.tube([P(x+dx,dep/2+.029,z),P(x+dx,dep/2+.041,z)],[.012,.012],bronze,6)
        # The foot has an actual thin stone isolator instead of timber sinking
        # directly into another member; no footprint enlargement beyond post.
        B(x,dep/2,.041,.195,.195,.067,m['stone'])
    # Drawer fronts have a 3mm reveal, a raised inset and curved drop handles.
    for j in range(max(2,int((w-1.5)/.8))):
        x=-w/2+.9+j*.79
        if x>w/2-.65:break
        y=-dep/2+.969
        B(x,y,.50,.70,.018,.42,black)
        B(x,y+.012,.50,.674,.02,.394,wood)
        B(x,y+.026,.50,.58,.016,.295,dark)
        for xx in (-.082,.082):
            g.tube([P(x+xx,y+.029,.59),P(x+xx,y+.055,.59)],[.009,.009],bronze,8)
        points=[P(x+.082*math.cos(a),y+.059,.59-.040*math.sin(a)) for a in np.linspace(0,math.pi,13)]
        g.tube(points,[.006]*len(points),bronze,6)
    # Jointed counter end caps protect exposed end grain; hand wear follows
    # the edge rather than a uniformly glossy plastic finish over every face.
    half=(w-1.3)/2
    for side in (-1,1):
        end=side*(half-.035)+(.30 if staff_entry and side<0 else 0)
        B(end,dep/2-.20,.974,.070,.573,.099,wood)
        for yy in (dep/2-.38,dep/2-.02):
            g.cylinder(P(end,yy,1.025),.007,.0018,dark,8)
    # An actual open half-round copper gutter, seated below the clay drip.
    # Its outer lip stays inside the former eave-cap bound (dep/2 + .7607m).
    # All new drainage surfaces remain above 2.60m; lower pipe is unchanged.
    copper="RoofCopper"
    if copper not in g.materials:
        g.material(copper,(.27,.21,.135),roughness=.72,metallic=.65)
    gutter_y=dep/2+.705; z=2.770
    x0,x1=-w/2-.47,w/2+.47
    _half_round_channel(g,P,x0,x1,gutter_y,z,z-.012,.050,.004,copper)
    _gutter_end_stop(g,P,x0,x0+.004,gutter_y,z,.050,copper)
    _gutter_end_stop(g,P,x1-.004,x1,gutter_y,z-.012,.050,copper)
    # Rolled rims and cradle straps explain how the thin trough is supported.
    for side in (-1,1):
        g.tube([P(x0,gutter_y+side*.048,z),P(x1,gutter_y+side*.048,z-.012)],
               [.0035,.0035],copper,6)
    for x in np.arange(-w/2-.38,w/2+.39,.67):
        zz=z-.012*(x-x0)/(x1-x0)
        _half_round_channel(g,P,x-.007,x+.007,gutter_y,zz,zz,.055,.004,iron,8)
        g.beam(P(x,gutter_y-.092,zz+.011),P(x,gutter_y-.049,zz-.004),.010,iron)
    x=-w/2-.06
    # Short high-level offset into the original fixed side downpipe. Collars
    # mask the plumbing joint while its below-eave route remains identical.
    old_y=dep/2+.61
    pts=[P(x,gutter_y-.018,2.704),P(x,gutter_y-.040,2.688),
         P(x,old_y+.020,2.662),P(x,old_y,2.640)]
    g.tube(pts,[.031]*len(pts),copper,8)
    g.tube([P(x,old_y,2.639),P(x,old_y,2.653)],[.036,.036],copper,10)
    pts=[P(x,old_y,2.640),P(x,old_y,2.53),P(x,dep/2-.20,2.39),P(x,dep/2-.20,.13)]
    g.tube(pts,[.030]*len(pts),bronze,10)
    for zc in (.39,1.30,2.25):
        B(x,dep/2-.239,zc,.087,.018,.039,iron)
    g.group=original
    return {'shop':idx+1,'timberEdgeBevelMetres':.006,'rainGutter':True,'kneeBraces':2}


def add_bar_stool(g,P,x,y,m):
    """Turned timber seat with explicit grain and mortised stretchers.

    Top remains at the existing .70m station height and within its .23m radius.
    It is a visual replacement; interaction coordinates are not modified.
    """
    wood,dark,iron=m['wood'],m['dark'],m['iron']
    n=36;v=[];uv=[];faces=[]
    rings=[(0,.696),(.11,.696),(.202,.700),(.224,.696),(.230,.684),(.230,.649),(.218,.631)]
    # Split the smooth turned edge from the dished top to retain a clean rim.
    for i,(r,z) in enumerate(rings):
        for j in range(n+1):
            a=j*math.tau/n;xx=x+r*math.cos(a);yy=y+r*math.sin(a)
            v.append(P(xx,yy,z));uv.append((xx*.50+.046,yy*.50+.29))
            if i and j:
                k=i*(n+1)+j
                if i>1:faces.append((k-n-2,k-n-1,k))
                faces.append((k-n-2,k,k-1))
    # The profile runs center -> rim -> underside, clockwise from outside.
    g.add(v,[f[::-1] for f in faces],wood,uv)
    g.cylinder(P(x,y,.633),.203,.026,dark,24)
    feet={}
    for dx in (-1,1):
        for dy in (-1,1):
            foot=P(x+dx*.165,y+dy*.165,.024)
            head=P(x+dx*.129,y+dy*.129,.633)
            g.beam(foot,head,.051,wood,.056)
            feet[(dx,dy)]=P(x+dx*.149,y+dy*.149,.286)
            g.tube([P(x+dx*.165,y+dy*.165,.015),P(x+dx*.165,y+dy*.165,.030)],[.029,.029],iron,8)
    for side in (-1,1):
        g.beam(feet[(-1,side)],feet[(1,side)],.037,dark,.032)
        g.beam(feet[(side,-1)],feet[(side,1)],.037,dark,.032)


if __name__=='__main__':
    import trimesh
    for axes in (None,[[0,-1,0],[1,0,0],[0,0,1]],[[1,0,0],[0,-1,0],[0,0,1]]):
        v,f,uv=timber_box_mesh([1,2,3],[4,.20,.24],axes)
        mesh=trimesh.Trimesh(v,f,process=True)
        assert len(f)==44 and mesh.is_watertight and mesh.is_winding_consistent
        assert mesh.volume>0 and np.isfinite(uv).all()
    print('Timber chamfer: closed, outward winding, finite UVs; 44 triangles/member')
