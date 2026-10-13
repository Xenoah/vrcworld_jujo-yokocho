"""Crafted walking decks: bevelled boards, clean scan crops, recessed fasteners.

Source coordinates are X east / Y north / Z up, before the altitude profile.
This module replaces the VISUAL slab and both historical seam passes. Keep the
original poly_mesh(poly, z, .3) collision mesh unchanged. All visual vertices
remain inside the exact footprint and within [z-.3, z]. No new images are used.
"""
import hashlib
import math
import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from world_geometry import poly_mesh

PITCH = .280
BOARD_LENGTH = 2.40
GAP = .0018
BEVEL = .0028
GROOVE_DEPTH = .0038
SLAB_THICKNESS = .30
# Measured interior regions of the bundled Poly Haven Wood Planks Grey image.
# Image V is inverted at export. The screws lie near UV v=.845, so .04-.77
# selects only wood. Each crop stays inside one of the five scanned boards.
SCAN_U = ((.022,.181),(.219,.379),(.422,.581),(.621,.781),(.822,.981))


def _parts(geom):
    if geom.is_empty:
        return
    if geom.geom_type == 'Polygon':
        yield geom
    elif hasattr(geom, 'geoms'):
        for child in geom.geoms:
            yield from _parts(child)


def _hash(a, b=0, c=0):
    """Platform-stable 32-bit mixer; never advances the world's RNG stream."""
    n = ((a * 0x9e3779b1) ^ (b * 0x85ebca77) ^ (c * 0xc2b2ae3d)) & 0xffffffff
    n ^= n >> 16; n = (n * 0x7feb352d) & 0xffffffff
    n ^= n >> 15; n = (n * 0x846ca68b) & 0xffffffff
    return n ^ (n >> 16)


def _material(g, source, name, **changes):
    if name in g.materials:
        return name
    spec = dict(g.materials[source]); spec.pop('name', None)
    spec.update(changes)
    return g.material(name, **spec)


def _materials(g, materials):
    source = materials['wood']
    # Restrained board-to-board weathering, not a random multicolour patchwork.
    tints = ((.94,.76,.57),(.87,.714,.55),(.965,.798,.61),(.90,.753,.60))
    boards = [_material(g,source,'DeckCedar'+str(i),color=color,uvScale=1.,
                        normalScale=.62,parallax=0.,roughness=1.)
              for i,color in enumerate(tints)]
    repair = _material(g,source,'DeckRepair',color=(1.,.88,.70),uvScale=1.,
                       normalScale=.50,parallax=0.,roughness=1.)
    bed = _material(g,source,'DeckJointBed',color=(.24,.19,.135),uvScale=.65,
                    normalScale=.4,parallax=0.,roughness=1.)
    nail = _material(g,materials.get('iron',materials.get('dark',source)),
                     'DeckForgedNail',color=(.085,.072,.055),texture='',normal='',
                     arm='',height='',normalScale=0.,parallax=0.,roughness=.82,
                     metallic=.46,uvScale=1.)
    return boards, repair, bed, nail


def _add_polygon(g, poly, height, material, uv_map):
    """Triangulate concavity/holes, explicitly maintaining positive Z winding."""
    vertices, faces, uvs = [], [], []
    indexed={}
    for p in _parts(poly):
        for tri in constrained_delaunay_triangles(p).geoms:
            q = np.asarray(tri.exterior.coords, float)[:3,:2]
            e1,e2=q[1]-q[0],q[2]-q[0]
            cross = e1[0]*e2[1]-e1[1]*e2[0]
            if abs(cross) < 1e-12:
                continue
            if cross < 0:
                q = q[::-1]
            z = [height(x,y) if callable(height) else height for x,y in q]
            positions=np.column_stack((q,z))
            # Clipped curved boundaries occasionally produce sub-micron CDT
            # slivers. Do not export triangles that collapse after float32
            # storage; the unchanged continuous bed covers their projection.
            packed=positions.astype(np.float32).astype(float)
            packed_cross=np.cross(packed[1]-packed[0],packed[2]-packed[0])
            if packed_cross[2] <= 1e-12:
                continue
            # Reuse vertices inside a single coplanar facet, while keeping
            # independent normals across the bevel edges. This avoids turning
            # every triangulated nail hole into a large unindexed vertex fan.
            normal=np.cross(positions[1]-positions[0],positions[2]-positions[0])
            normal=tuple(np.round(normal/np.linalg.norm(normal),7))
            corner_uv=uv_map(q)
            face=[]
            for position,tex in zip(positions,corner_uv):
                key=(tuple(position),tuple(tex),normal)
                index=indexed.get(key)
                if index is None:
                    index=len(vertices);indexed[key]=index
                    vertices.append(position.tolist());uvs.append(tex.tolist())
                face.append(index)
            faces.append(tuple(face))
    if faces:
        g.add(vertices,faces,material,uvs)
    return len(faces)


def _nail(g, center, radius, rotation, z, wood, metal, uv_map):
    """A five-sided, gently irregular forged head below an actual surface hole.

    Top rim is at z, head at z-.00055. No overlay or z-fighting. The 8-9mm
    heads are intentionally quiet at standing eye height, without 3D bolts.
    """
    angles = np.arange(5)*math.tau/5+rotation
    profile = np.array([1.,.92,1.025,.955,.985])
    outer = np.asarray(center)+np.column_stack((np.cos(angles),np.sin(angles)))*(radius*profile[:,None])
    inner = np.asarray(center)+(outer-np.asarray(center))*.78
    # Share the small recess rim around the head for a softly worn dent;
    # the independent metal cap keeps its flat forged face. Ten rim vertices
    # replace twenty without changing any triangle, height or footprint.
    vertices=np.vstack((np.column_stack((outer,np.full(5,z))),
                        np.column_stack((inner,np.full(5,z-.00055)))))
    faces=[]
    for i in range(5):
        j=(i+1)%5
        faces.extend([(i,j,5+j),(i,5+j,5+i)])
    g.add(vertices,faces,wood,uv_map(vertices[:,:2]))
    g.add([[*xy,z-.00055] for xy in inner],[(0,i,i+1) for i in range(1,4)],
          metal,uv_map(inner))
    return Polygon(outer)


def add_deck_surface(g, poly, z, materials):
    """Replace one near-deck visual slab; return compact build/audit metadata.

    ``poly`` may be a Polygon/MultiPolygon, concave, perforated, or clipped to
    narrow tips. ``materials`` uses the existing build_world M mapping and must
    contain ``wood`` (optional ``dark`` and ``iron``). The current group is
    preserved, with surfaces emitted into /Planks and /JointBed subgroups.

    The bed covers the entire polygon at z-.0038, with original slab bottom
    z-.30 and exact perimeter/holes. Board tops stay exactly z. Inset bevels
    never expand the footprint, and tiny cut slivers fall back to the bed.
    This function never touches any collider, global RNG, image or layout.
    """
    if not math.isfinite(z):
        raise ValueError('Deck height must be finite')
    if poly.is_empty:
        return {'boards':0,'nails':0,'repairBoards':0,'triangles':0,'footprintArea':0.}
    if not poly.is_valid:
        raise ValueError('Deck footprint must be a valid Polygon/MultiPolygon')
    if poly.geom_type not in ('Polygon','MultiPolygon'):
        raise TypeError('Deck footprint must be a Polygon or MultiPolygon')
    if not np.isfinite(poly.bounds).all():
        raise ValueError('Deck footprint coordinates must be finite')
    original = g.group
    start_triangles = sum(len(b['f']) for b in g.batches.values())
    boards,repair,bed,nail = _materials(g,materials)
    seed = int.from_bytes(hashlib.sha256((original+'|'+format(z,'.9f')).encode()).digest()[:4],'little')
    counts = {'boards':0,'nails':0,'repairBoards':0,'clippedBoards':0,
              'narrowSlivers':0,'bevelTriangles':0,'surfaceTriangles':0}
    try:
        g.group = original+'/JointBed'
        v,f = poly_mesh(poly,z-GROOVE_DEPTH,SLAB_THICKNESS-GROOVE_DEPTH)
        # Preserve the exact source polygon; discard only triangles collapsed
        # by the final float32 vertex encoding (e.g. redundant collinear cuts).
        packed=v.astype(np.float32).astype(float)[f]
        cross=np.cross(packed[:,1]-packed[:,0],packed[:,2]-packed[:,0])
        f=f[np.linalg.norm(cross,axis=1)>1e-12]
        bed_uv=np.asarray(v)[:,:2].copy()
        for face in f:
            q=v[face];normal=np.cross(q[1]-q[0],q[2]-q[0])
            if abs(normal[2]) < 1e-12:
                # Finite tangents on the continuous perimeter and hole walls.
                edge=max((q[1]-q[0],q[2]-q[0]),key=lambda a:np.linalg.norm(a[:2]))[:2]
                length=np.linalg.norm(edge)
                if length>1e-12:bed_uv[face]=np.column_stack((q[:,:2]@(edge/length),q[:,2]))
        g.add(v,f,bed,bed_uv)
        g.group = original+'/Planks'
        minx,miny,maxx,maxy = poly.bounds
        for row in range(math.floor(minx/PITCH),math.ceil(maxx/PITCH)):
            x0,x1=row*PITCH,(row+1)*PITCH
            # Standard support-grid offsets. Avoid the old mismatched .26/.28m
            # grids and four successive end joints marching diagonally forever.
            phase = (0.,1.20,.60,1.80,.60,0.,1.80,1.20)[row % 8]
            for joint in range(math.floor((miny-phase)/BOARD_LENGTH)-1,
                               math.ceil((maxy-phase)/BOARD_LENGTH)+1):
                # Occasional half-joist variation gives real stock lengths
                # 1.8/2.4/3.0m, yet every joint still rests on a .6m support grid.
                def cut(k):
                    h=_hash(row,k,seed ^ 0x613c)
                    return k*BOARD_LENGTH+phase+(.60 if h%13 == 0 else 0.)
                y0,y1=cut(joint),cut(joint+1)
                cell=box(x0,y0,x1,y1)
                clipped=cell.intersection(poly)
                h=_hash(row,joint,seed)
                u0,u1=SCAN_U[(h>>6)%len(SCAN_U)]
                # Crop below the scanned screw row. Translate/flip each complete
                # board crop; neither nails nor painted seams can repeat in it.
                span=min(.61,(y1-y0)*(.173+(h%7)*.004))
                v0=.045+((h>>12)%997)/996*(.735-span-.045)
                flip_u=-1 if (h>>23)&1 else 1
                flip_v=-1 if (h>>24)&1 else 1
                def uv_map(q):
                    q=np.asarray(q)
                    u=(q[:,0]-x0)/(x1-x0);v=(q[:,1]-y0)/(y1-y0)
                    if flip_u < 0:u=1-u
                    if flip_v < 0:v=1-v
                    return np.column_stack((u0+(u1-u0)*u,v0+span*v))
                mat=repair if h%53==0 else boards[(h>>3)%len(boards)]
                for piece in _parts(clipped):
                    if piece.area < 1e-12:
                        continue
                    footprint=piece.buffer(-GAP/2,join_style='mitre',mitre_limit=2.)
                    for outer in _parts(footprint):
                        top=outer.buffer(-BEVEL,join_style='mitre',mitre_limit=2.)
                        if top.is_empty or top.area < 1e-10:
                            counts['narrowSlivers']+=1
                            continue
                        counts['boards']+=1
                        if mat==repair:counts['repairBoards']+=1
                        if piece.area<cell.area-1e-9:counts['clippedBoards']+=1
                        # Exact ring triangulation also handles split inset tips
                        # and hole boundaries, unlike a rectangular-only bevel.
                        ring=outer.difference(top)
                        def bevel_z(x,y):
                            from shapely.geometry import Point
                            d=outer.boundary.distance(Point(x,y))
                            return z-GROOVE_DEPTH+GROOVE_DEPTH*min(1.,d/BEVEL)
                        counts['bevelTriangles']+=_add_polygon(g,ring,bevel_z,mat,uv_map)
                        holes=[]
                        mode=h%100
                        # ~one pair on half the boards, plus rare doubled fixings
                        # on replaced boards. No dense repeated raised bolt rows.
                        ends=([0,1] if mat==repair else ([((h>>18)&1)] if mode<46 else []))
                        for end in ends:
                            yy=y0+.058 if end==0 else y1-.058
                            for side in (0,1):
                                xx=x0+.047 if side==0 else x1-.047
                                nh=_hash(row*3+side,joint*3+end,seed ^ 0x8721)
                                xx+=((nh%17)/16-.5)*.006
                                yy1=yy+(((nh>>5)%17)/16-.5)*.006
                                radius=.0041+((nh>>10)%11)/10*.0005
                                angles=np.arange(5)*math.tau/5+((nh>>15)%628)/100
                                shape=Polygon(np.asarray([xx,yy1])+np.column_stack((np.cos(angles),np.sin(angles)))*radius*1.04)
                                if top.contains(shape.buffer(.005)):
                                    holes.append(_nail(g,(xx,yy1),radius,((nh>>15)%628)/100,z,mat,nail,uv_map))
                                    counts['nails']+=1
                        for hole in holes:top=top.difference(hole)
                        counts['surfaceTriangles']+=_add_polygon(g,top,z,mat,uv_map)
    finally:
        g.group = original
    counts.update(triangles=sum(len(b['f']) for b in g.batches.values())-start_triangles,
                  footprintArea=round(poly.area,6),perimeter=round(poly.length,6),
                  plankWidth=PITCH,nominalPlankLength=BOARD_LENGTH,
                  jointGap=GAP,edgeBevel=BEVEL,grooveDepth=GROOVE_DEPTH,
                  maximumTop=z,slabBottom=z-SLAB_THICKNESS,newTextureBytes=0)
    return counts
