"""Opt-in, collider-free noren construction in shop-local metres / Z-up.

Only the ordinary hanging panels, their two supports, and the common pole are
replaced. The caller's _rolled_entry_noren function is used unchanged. All
arithmetic is analytic: this module imports or consumes no random generator.

The rod uses the already authored BAMBOO tile and existing CraftSurfaces
material. The normal build defines that material later in add_counter_craft;
standalone callers must supply its existing definition before export. No new
material, texture, shader, animation, physics or external dependency is added.
"""
import math
import numpy as np

TAU = math.tau
BODY_THICKNESS = .00065
HEM_THICKNESS = .00150
TAB_WIDTH = .015
TAB_THICKNESS = .00065
ROD_RADIUS = .0144
NODE_RADIUS = .0169


def _smoothstep(a, b, x):
    t = min(1., max(0., (x-a)/(b-a)))
    return t*t*(3-2*t)


def _old_panel_bounds(x0, x1, phase, panel):
    """Exact original 16x5 sheet limits, before source float32 serialization."""
    samples=[]
    for j in range(6):
        t=j/5
        for k in range(17):
            u=k/16
            fold=(.023*math.sin(u*TAU*1.8+panel*.6+phase)+
                  .010*math.sin(u*TAU*4.0))*(1-.48*t)
            bottom=2.10+.019*math.cos(u*TAU+phase)+.007*math.sin(panel*1.7)
            samples.append((x0+(x1-x0)*u,fold,bottom+(2.59-bottom)*t))
    a=np.asarray(samples)
    return a.min(axis=0),a.max(axis=0)


def _surface_point(u, t, x0, x1, y, panel, phase, bounds):
    """Quiet gravity drape with the two actual tab locations pinned at the top."""
    lo,hi=bounds
    x=x0+(x1-x0)*u
    # Two broad unequal folds, rather than a dense identical sine-wave curtain.
    # Every component vanishes at u=.10/.90, where a tab meets the upper edge.
    q=(u-.10)/.80
    broad=.0184*math.sin(TAU*q)+.0068*math.sin(TAU*2*q)
    broad*=.94+.06*math.cos(panel*1.31+phase)
    # The cloth falls smoothly from the supports; mild lower billow is not wind
    # animation. No lower/lateral silhouette exceeds the old panel envelope.
    yy=broad*(1-.57*t)
    # Shallow paired gravity creases immediately beside the two sewn tabs.
    # The signed lobes pin each actual anchor and decay before the emblem.
    # They are resolved by dedicated columns, rather than inflating the panel.
    shoulder=sum(.58*(u-anchor)*math.exp(-((u-anchor)/.046)**2)
                 for anchor in (.10,.90))
    yy += shoulder*t**1.7
    side=min(u,1-u)*(x1-x0)
    lower_hem=1-_smoothstep(.017,.029,t)
    side_hem=1-_smoothstep(.005,.012,side)
    hem=max(lower_hem,side_hem)
    thickness=BODY_THICKNESS+(HEM_THICKNESS-BODY_THICKNESS)*hem
    # A sub-millimetre rounded fold line, not a brown cord or painted border.
    # The new close-spaced mesh rows/columns resolve this physical seam relief.
    yy += .00080*math.exp(-((t-.022)/.009)**2)
    yy += .00050*math.exp(-((side-.006)/.003)**2)
    # Leave space for the rear shell. Clamp to measured old depths, not a broad
    # world-level exemption. This also protects especially shallow end panels.
    yy=float(np.clip(yy,lo[1]+thickness+.00004,hi[1]-.00004))
    # Reuse the original scallop function, but clamp to its discrete old mesh
    # extrema because inserting a new U sample can otherwise undershoot it.
    bottom=2.10+.019*math.cos(u*TAU+phase)+.007*math.sin(panel*1.7)
    bottom=float(np.clip(bottom,lo[2],hi[2]))
    sag=.0075*math.sin(math.pi*min(1.,max(0.,q)))**2
    top=2.590-sag
    z=bottom+(top-bottom)*t
    return np.array([x,y+yy,z]),thickness


def _panel(g,P,x0,x1,y,width,panel,phase,rect,material,uvmap):
    bounds=_old_panel_bounds(x0,x1,phase,panel)
    # Seventeen columns include an actual narrow side hem. Eight rows resolve
    # the folded lower edge without multiplying geometry across the whole body.
    edge=.006/(x1-x0);end=.014/(x1-x0)
    us=[0.,edge,end,.07,.10,.13,.30,.42,.50,.58,.70,.87,.90,.93,1-end,1-edge,1.]
    ts=[0.,.012,.022,.032,.14,.40,.71,1.]
    nx=len(us);ny=len(ts);front=[];back=[];uv=[];faces=[];local_front=[];thicknesses=[]
    for t in ts:
        for u in us:
            p,thickness=_surface_point(u,t,x0,x1,y,panel,phase,bounds)
            if t==0:p[2]+=thickness*.5
            local_front.append(p.copy());thicknesses.append(thickness)
            front.append(P(*p));back.append(P(*(p-[0,thickness,0])))
            su=(p[0]+width/2)/width
            uv.append(uvmap(rect,1-su,t))
    n=len(front)
    for j in range(ny-1):
        for k in range(nx-1):
            p=j*nx+k;q=p+nx
            faces.extend([(p,q+1,p+1),(p,q,q+1)])
    g.add(front,faces,material,uv)
    g.add(back,[f[::-1] for f in faces],material,uv)
    # Closed perimeter has independent edge normals, avoiding rounded-looking
    # pillow shading across the thin cloth. UVs use a blank strip of this shop's
    # textile so the ink does not wrap into a false embroidered border.
    perimeter=list(range(nx))
    perimeter += [j*nx+nx-1 for j in range(1,ny)]
    perimeter += list(range((ny-1)*nx+nx-2,(ny-1)*nx-1,-1))
    perimeter += [j*nx for j in range(ny-2,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):
        if a<nx and b<nx:continue  # Bottom is the true folded turn below.
        verts=[front[a],front[b],back[b],back[a]]
        # The front perimeter traverses the lower edge left-to-right. Joining
        # it to the rear in this order gives outward (e.g. downward) edges.
        u0=.025;u1=.039
        edgeuv=[uvmap(rect,u0,.945),uvmap(rect,u1,.945),
                uvmap(rect,u1,.957),uvmap(rect,u0,.957)]
        g.add(verts,[(0,1,2),(0,2,3)],material,edgeuv)
    # A real half-round turn joins front to rear below the seam. It is only
    # 0.75 mm in radius and entirely flush with the cloth, never face piping.
    # Front/back rows were lifted by the radius; the arc touches the original
    # lower silhouette, preserving the exact old minimum-height envelope.
    arc_sides=4;arc_n=arc_sides+1;av=[];au=[];af=[]
    for k,u in enumerate(us):
        p=local_front[k];r=thicknesses[k]*.5
        for j in range(arc_n):
            a=math.pi*j/arc_sides
            q=p+np.array([0,-r*(1-math.cos(a)),-r*math.sin(a)])
            av.append(P(*q));su=(p[0]+width/2)/width
            au.append(uvmap(rect,1-su,.003*math.sin(a)))
            if k and j:
                q=k*arc_n+j;p0=q-arc_n
                af.extend([(p0-1,q-1,q),(p0-1,q,p0)])
    g.add(av,af,material,au)
    # Close the tiny semicircular fold at each slit edge. This is the actual
    # cross-section, not an unclosed ribbon or detached decorative stitch line.
    for k,reverse in [(0,False),(nx-1,True)]:
        vv=av[k*arc_n:(k+1)*arc_n]
        ff=[(0,j,j+1) for j in range(1,arc_sides)]
        if reverse:ff=[f[::-1] for f in ff]
        uu=[uvmap(rect,.028+.010*j/arc_sides,.950+.006*math.sin(math.pi*j/arc_sides))
            for j in range(arc_n)]
        g.add(vv,ff,material,uu)
    return {'oldBounds':{'min':bounds[0].tolist(),'max':bounds[1].tolist()}}


def _tab(g,P,x,y,width,rect,material,uvmap):
    """Narrow doubled fabric ribbon over the rod, stitched back onto the sheet.

    Cross-section stays inside the old support/35 mm pole union. The tab's
    narrow 15 mm span also fits the old beam's 16 mm transverse dimension.
    """
    r=ROD_RADIUS+.00070
    # Start and end are separated by the cloth thickness at the stitched base.
    # The broad band is a continuous folded ribbon, never separate floating bars.
    path=[(.00035,2.559),(.0033,2.589),(r,2.625)]
    path += [(r*math.cos(a),2.625+r*math.sin(a)) for a in np.linspace(math.pi/6,math.pi,6)]
    path += [(-.0030,2.589),(-.00035,2.559)]
    verts=[];uv=[];faces=[];su=(x+width/2)/width
    for i,(yy,zz) in enumerate(path):
        # Offset in the local path normal, with bounded end mitres.
        prev=np.array(path[max(0,i-1)]);nxt=np.array(path[min(len(path)-1,i+1)])
        tangent=nxt-prev;tangent/=np.linalg.norm(tangent)
        normal=np.array([-tangent[1],tangent[0]])*TAB_THICKNESS*.5
        for side,layer in [(-1,-1),(1,-1),(1,1),(-1,1)]:
            q=np.array([yy,zz])+normal*layer
            verts.append(P(x+side*TAB_WIDTH*.5,y+q[0],q[1]))
            # Keep U running across the band; sample quiet upper-edge dye.
            uv.append(uvmap(rect,1-su-side*TAB_WIDTH/(width*2)+layer*.00020,
                            .946+.024*i/(len(path)-1)+layer*.0020))
        if i:
            a=(i-1)*4;b=i*4
            for j in range(4):
                k=(j+1)%4;faces.extend([(a+j,a+k,b+k),(a+j,b+k,b+j)])
    # End caps prevent an open ribbon cross-section at grazing view angles.
    faces.extend([(0,2,1),(0,3,2)])
    a=(len(path)-1)*4;faces.extend([(a,a+1,a+2),(a,a+2,a+3)])
    g.add(verts,[f[::-1] for f in faces],material,uv)


def _bamboo_rod(g,P,x0,x1,y,z):
    """Thin round bamboo with muted nodes and hollow ends, <= old 35 mm box.

    Reuses counter_craft's existing tile; no new material definition is made.
    UV V follows cane length (the BAMBOO tile's authored grain direction).
    """
    from counter_craft import _uv,BAMBOO
    length=x1-x0
    # Nodes introduce a functional cane silhouette without repeated dark bands.
    nodes=np.arange(x0+.29,x1-.12,.64)
    profile=[(x0,ROD_RADIUS),(x0+.006,ROD_RADIUS)]
    for x in nodes:
        profile.extend([(x-.009,ROD_RADIUS),(x-.003,NODE_RADIUS),
                        (x+.003,NODE_RADIUS),(x+.009,ROD_RADIUS)])
    profile.extend([(x1-.006,ROD_RADIUS),(x1,ROD_RADIUS)])
    n=16;v=[];uv=[];f=[]
    for i,(x,r) in enumerate(profile):
        for j in range(n+1):
            a=TAU*j/n
            v.append(P(x,y+r*math.cos(a),z+r*math.sin(a)))
            # V repeats per internode and U around the circumference. Tile
            # sampling remains inside the atlas gutters, never wraps whole atlas.
            vv=((x-x0)/.64)%1
            uv.append(_uv(BAMBOO,j/n,vv))
            if i and j:
                k=i*(n+1)+j;p=k-(n+1)
                f.extend([(p-1,p,k),(p-1,k,k-1)])
    g.add(v,f,'CraftSurfaces',uv)
    # Hollow rings at both ends: a small inset cavity, not a dark flat disk.
    for x,sign in [(x0,1),(x1,-1)]:
        # Split cut-end and cavity vertices: their real UV directions differ.
        # This avoids relying on the generic normal-UV repair to add corners.
        for cavity in [False,True]:
            verts=[];u=[];faces=[]
            rings=([(x,ROD_RADIUS),(x,ROD_RADIUS*.72)] if not cavity else
                   [(x,ROD_RADIUS*.72),(x+sign*.008,ROD_RADIUS*.72)])
            for row,(xx,r) in enumerate(rings):
                for j in range(n+1):
                    a=TAU*j/n;verts.append(P(xx,y+r*math.cos(a),z+r*math.sin(a)))
                    if cavity:u.append(_uv(BAMBOO,j/n,.25+.40*row))
                    else:u.append(_uv(BAMBOO,.5+.44*r/ROD_RADIUS*math.cos(a),
                                     .5+.44*r/ROD_RADIUS*math.sin(a)))
            for j in range(n):
                q=j+n+1;faces.extend([(j,j+1,q+1),(j,q+1,q)])
            if sign==1:faces=[f[::-1] for f in faces]
            g.add(verts,faces,'CraftSurfaces',u)


def add_crafted_noren(g,P,B,w,dep,idx,M,materials,staff_entry=False):
    """Replacement for _folded_noren, only under a literal True feature gate."""
    from shopfront_identity import IDENTITIES,_rect,_uv,_rolled_entry_noren
    count=IDENTITIES[idx]['panels'];width=w-.90;y=dep/2+.135
    rect=_rect(idx,'cloth');phase=idx*.27
    for panel in range(count):
        lo=panel/count;hi=(panel+1)/count
        x0=-width/2+width*lo+.014;x1=-width/2+width*hi-.014
        if staff_entry and panel==0:
            _rolled_entry_noren(g,P,x0,x1,y,width,idx,M,materials,rect)
            continue
        _panel(g,P,x0,x1,y,width,panel,phase,rect,materials['cloth'],_uv)
        for u in [.10,.90]:_tab(g,P,x0+(x1-x0)*u,y,width,rect,materials['cloth'],_uv)
    _bamboo_rod(g,P,-width/2-.065,width/2+.065,y,2.625)
    # These two original pole-to-lintel ties stay exactly unchanged.
    for x in [-width/2-.02,width/2+.02]:
        g.beam(P(x,y-.035,2.627),P(x,y-.035,2.735),.014,M['dark'])
