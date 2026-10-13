"""Low-overdraw cloud banks for the elevated Tree-top Yokocho, source XYZ/Z-up.

Nine soft rounded billows per bank, one shared texture-free material, eight
spatial draw batches. No particles, stacked full-bank shells, screen/depth sampling,
colliders or runtime scripts. See Docs/CloudSea.md for integration.
"""
from __future__ import annotations

import math
import numpy as np

CLOUD_BASE_Z = 110.0
CLOUD_TOP_Z = 124.0
MATERIAL_NAME = 'CloudSeaSilver'

# Centre east/north, ellipse radii, rotation degrees. The north road/city and
# south sea have genuine open sightline windows, not just lower alpha.
# Unequal bank sizes prevent rings, rows and a circular "island in a pond".
BANKS = (
    (-151,  12, 118, 110, -24), (153,  31, 110, 128, 19),
    (-207, 196, 139, 123,  23), (229, 235, 144, 130, -22),
    (-231,-173, 140, 121, -32), (247,-193, 143, 131, 26),
    (-405,  61, 179, 186,  11), (442,  13, 198, 163, -12),
    (-485, 372, 216, 167, -18), (484, 409, 218, 179, 24),
    (-515,-365, 218, 177,  31), (513,-434, 227, 195, -19),
    (-271, 637, 170, 183, -16), (305, 733, 182, 211, 21),
    (-825, 148, 252, 264,  18), (852, 204, 273, 253, -27),
    (-908, 704, 297, 242, -21), (941, 775, 300, 236, 14),
    (-956,-565, 311, 240,  26), (984,-680, 307, 279, -22),
    (-501,-923, 259, 220, -11), (550,-1159,284, 249, 15),
    (-633,1258, 323, 249, -21), (691,1374, 316, 279, 26),
    (-1467,334, 404, 358,  15), (1495,401, 401, 349, -24),
    (-1491,-948,420, 348,  23), (1518,-1101,416,351, -19),
)


def _bank_mesh(spec, phase, base, height, rings=5, sides=16):
    """Nine independently rounded billows, rather than a bank-wide shallow disk.

    A compact cluster remains within the original ellipse footprint. Each
    billow has a steep, hemisphere-like shoulder and its own soft radial UVs.
    Shared material/batches keep the extra shape detail out of draw-call cost.
    """
    cx, cy, sx, sy, degrees = spec
    angle = math.radians(degrees); ca, sa = math.cos(angle), math.sin(angle)
    vertices, uvs, faces = [], [], []
    # Two central volumes and seven unequal peripheral volumes avoid a
    # symmetrical flower shape while still connecting into a larger bank.
    cells = [(0., 0., .49, .47, .92),
             (.13*math.cos(phase), .13*math.sin(phase), .39, .40, 1.)]
    for k in range(7):
        theta = k*math.tau/7 + phase*.23
        radius = .51 + .065*math.sin(k*2.1+phase)
        size = .36 + .055*math.cos(k*1.7-phase)
        cells.append((radius*math.cos(theta), radius*math.sin(theta),
                      size, size*(.91+.14*math.sin(k+phase)),
                      .62+.31*(.5+.5*math.sin(k*2.39+phase))))
    for index, (ox, oy, rx, ry, amount) in enumerate(cells):
        offset = len(vertices)
        peak = min(CLOUD_TOP_Z-.18, base+height*amount)
        bottom = CLOUD_BASE_Z+.28 + 1.25*(.5+.5*math.sin(phase+index*2.3))
        def point(r, theta):
            edge = 1+.085*math.sin(theta*3+phase+index)+.045*math.cos(theta*5-index)
            px, py = r*math.cos(theta), r*math.sin(theta)
            xx, yy = (ox+px*rx*edge)*sx, (oy+py*ry*edge)*sy
            x, y = cx+xx*ca-yy*sa, cy+xx*sa+yy*ca
            # Rounded shoulders provide real vertical normals/silhouettes;
            # bank-wide low undulation was the cause of the old plate look.
            dome = max(0., 1-r*r)**.47
            lobe = 1+.085*math.sin(px*5.1+phase+index)*math.sin(py*5.7-index)
            z = min(CLOUD_TOP_Z-.18, bottom+(peak-bottom)*dome*lobe)
            return [x,y,z], [(px+1)*.5,(py+1)*.5]
        p,t=point(0,0);vertices.append(p);uvs.append(t)
        for ring in range(1,rings+1):
            # More samples on the rounded shoulder where the silhouette bends.
            r=math.sin(ring/rings*math.pi*.5)
            for j in range(sides):
                p,t=point(r,math.tau*j/sides);vertices.append(p);uvs.append(t)
                a=offset+1+(ring-1)*sides+j
                b=offset+1+(ring-1)*sides+(j+1)%sides
                if ring==1:faces.append((offset,a,b))
                else:
                    c,d=a-sides,b-sides
                    faces.extend([(c,a,b),(c,b,d)])
    return np.asarray(vertices),np.asarray(faces,dtype=np.int32),np.asarray(uvs)


def add_cloud_sea(g, M, rng):
    """Add visual-only cloud geometry; return plain-JSON manifest metadata.

    Call after landscape generation and after any existing-world altitude
    transform. Do not pass this function a collision Geometry object.
    M is accepted for the project's scenery API; no scene materials are changed.
    The caller's RNG is only sampled for stable local phases and bank heights.
    """
    del M
    previous_group = g.group
    material = g.material(MATERIAL_NAME, (.78, .85, .95), roughness=1.,
                          shader='CloudSea', alphaMode='BLEND', doubleSided=True,
                          cloudOpacity=.86, cloudNoiseScale=.024,
                          cloudWind=[.62, .18], cloudBaseZ=CLOUD_BASE_Z,
                          cloudTopZ=CLOUD_TOP_Z)
    start_keys = set(g.batches)
    records = []
    vertices, triangles = 0, 0
    low, high = 1.e6, -1.e6
    central_opening = 1.e6
    for index, spec in enumerate(BANKS):
        x, y = spec[:2]
        distance = math.hypot(x, y)
        tier = 'Near' if distance < 680 else 'Far'
        quadrant = ('N' if y >= 0 else 'S') + ('W' if x < 0 else 'E')
        g.group = 'Landscape/CloudSea_%s_%s' % (tier, quadrant)
        phase = float(rng.uniform(0, math.tau))
        base = float(rng.uniform(110.55, 112.35))
        height = float(rng.uniform(10.7, 12.2))
        v, f, uv = _bank_mesh(spec, phase, base, height)
        g.add(v, f, material, uv)
        vertices += len(v); triangles += len(f)
        low = min(low, float(v[:, 2].min())); high = max(high, float(v[:, 2].max()))
        # Distance to actual mesh edges, not a guessed bank radius:
        # each rounded cell contributes to the central opening boundary.
        edges = np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
        boundary = v[edges[:,0],:2]
        delta = v[edges[:,1],:2]-boundary
        fraction = np.clip(-np.sum(boundary*delta,axis=1)/np.sum(delta*delta,axis=1),0,1)
        central_opening = min(central_opening,float(np.linalg.norm(boundary+fraction[:,None]*delta,axis=1).min()))
        records.append({'id': 'CloudBank%02d' % index,
                        'center': [float(x), float(y), round(base, 3)],
                        'radius': [float(spec[2]), float(spec[3])],
                        'rotationDegrees': float(spec[4]), 'group': g.group,
                        'phase': round(phase, 5)})
    g.group = previous_group
    return {
        'enabled': True,
        'profile': 'Windows_Builtin_TextureFreeCloudBanks',
        'coordinateSystem': 'X east, Y north, Z up',
        'material': MATERIAL_NAME, 'shader': 'TreeTopYokocho/CloudSea',
        'banks': records, 'bankCount': len(records), 'billowCount': len(records)*9,
        'drawBatches': len(set(g.batches)-start_keys),
        'vertices': int(vertices), 'triangles': int(triangles),
        'altitudeBounds': [round(low, 3), round(high, 3)],
        'maximumAnimatedAltitude': 124.0,
        'lowestDeckAltitude': 134.0,
        'minimumDeckClearance': 10.0,
        'collision': False, 'newTextures': 0, 'runtimeScripts': 0,
        'volumetricRaymarching': False, 'depthTextureRequired': False,
        'viewingBreaks': [
            {'name': 'North road and walled city', 'direction': 'north/+Y',
             'clearRayExample': [[-24., 30., 153.7], [0., 740., 28.]]},
            {'name': 'South sea and islands', 'direction': 'south/-Y',
             'clearRayExample': [[-24., -40., 153.7], [0., -1400., 0.]]},
            {'name': 'Root and forest glimpses', 'direction': 'down and between banks',
             'centralOpeningMinimumRadius': round(central_opening, 3)}
        ],
        'notes': 'Cloud shading is a soft mesh illusion, not true participating media. GPU/VR frame time requires Unity VRChat testing.'
    }


def configure_blender_clouds(bpy, manifest):
    """Restore the texture-free runtime cloud look after importing the real GLB.

    Blender/glTF cannot execute a Unity shader. This explicitly documented
    material equivalent uses the imported cloud geometry and the same disk
    edge fade plus procedural world-space noise. No invented render geometry,
    no volumetric cube, no external image textures. Returns JSON-safe results.
    """
    del manifest
    found = []
    for mat in bpy.data.materials:
        if not mat.name.startswith(MATERIAL_NAME):
            continue
        mat.use_nodes = True
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'DITHERED'
        mat.diffuse_color = (.78, .85, .95, .86)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        out.label = 'CloudSea preview equivalent; actual imported geometry'
        tex = nodes.new('ShaderNodeTexCoord')
        geo = nodes.new('ShaderNodeNewGeometry')
        uv_center = nodes.new('ShaderNodeVectorMath'); uv_center.operation = 'SUBTRACT'
        uv_center.inputs[1].default_value = (.5, .5, 0)
        links.new(tex.outputs['UV'], uv_center.inputs[0])
        radius = nodes.new('ShaderNodeVectorMath'); radius.operation = 'LENGTH'
        links.new(uv_center.outputs['Vector'], radius.inputs[0])
        edge = nodes.new('ShaderNodeMapRange'); edge.interpolation_type = 'SMOOTHSTEP'
        edge.clamp = True
        edge.inputs['From Min'].default_value = .15
        edge.inputs['From Max'].default_value = .49
        edge.inputs['To Min'].default_value = 1.
        edge.inputs['To Max'].default_value = 0.
        links.new(radius.outputs['Value'], edge.inputs['Value'])
        noise = nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '3D'
        noise.inputs['Scale'].default_value = .024
        noise.inputs['Detail'].default_value = 2.
        noise.inputs['Roughness'].default_value = .48
        links.new(geo.outputs['Position'], noise.inputs['Vector'])
        # Prevent perfectly concentric transparency while keeping the core full.
        detail = nodes.new('ShaderNodeMapRange'); detail.clamp = True
        detail.inputs['From Min'].default_value = .25
        detail.inputs['From Max'].default_value = .68
        detail.inputs['To Min'].default_value = .32
        detail.inputs['To Max'].default_value = 1.
        links.new(noise.outputs['Fac'], detail.inputs['Value'])
        nshift=nodes.new('ShaderNodeMath');nshift.operation='SUBTRACT';nshift.inputs[0].default_value=.5
        links.new(noise.outputs['Fac'],nshift.inputs[1])
        nscale=nodes.new('ShaderNodeMath');nscale.operation='MULTIPLY';nscale.inputs[1].default_value=.18
        links.new(nshift.outputs[0],nscale.inputs[0])
        nradius=nodes.new('ShaderNodeMath');nradius.operation='ADD'
        links.new(radius.outputs['Value'],nradius.inputs[0]);links.new(nscale.outputs[0],nradius.inputs[1])
        links.new(nradius.outputs[0],edge.inputs['Value'])
        density = nodes.new('ShaderNodeMath'); density.operation = 'MULTIPLY'
        links.new(edge.outputs['Result'], density.inputs[0])
        links.new(detail.outputs['Result'], density.inputs[1])
        opacity = nodes.new('ShaderNodeMath'); opacity.operation = 'MULTIPLY'
        opacity.inputs[1].default_value = .86
        links.new(density.outputs[0], opacity.inputs[0])
        # A soft silver-blue diffuse lobe and mild ambient scatter. The diffuse
        # geometry normals expose the real corrugation under the scene lights.
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .15
        ramp.color_ramp.elements[0].color = (.23, .32, .47, 1)
        ramp.color_ramp.elements[1].position = .82
        ramp.color_ramp.elements[1].color = (.83, .89, .98, 1)
        links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Roughness'].default_value = 1.
        bsdf.inputs['Specular IOR Level'].default_value = .08
        links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .43
        bump.inputs['Distance'].default_value = 12.
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
        links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = .16
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        links.new(opacity.outputs[0], mix.inputs[0])
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(bsdf.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs['Surface'])
        found.append(mat.name)
    object_count = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and any(m and m.name.startswith(MATERIAL_NAME) for m in obj.data.materials):
            if hasattr(obj, 'visible_shadow'): obj.visible_shadow = False
            # Smooth shading follows the real mesh curvature instead of facets.
            for polygon in obj.data.polygons: polygon.use_smooth = True
            object_count += 1
    return {'materials': found, 'meshObjects': object_count,
            'scope': 'Blender procedural material equivalent; actual generated cloud mesh. Not Unity shader/runtime validation.'}
