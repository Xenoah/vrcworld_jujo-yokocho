"""Shared authored dusk math and Blender equivalents, source XYZ / Z up.

No random state, textures, mesh, lights, or runtime behaviour are created here.
World radiance matches the existing Unity sky formula; diffuse illumination is
an explicit preview-only approximation of independent Unity Trilight ambient.
Exp2 fog uses camera-space surface depth, not an elevated/underground volume.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

PROFILE_RELATIVE = Path('Assets/TreeTopYokocho/Data/DuskAtmosphere.json')


def source_to_unity(v):
    return (v[0], v[2], v[1])


def _normalize(v):
    length = math.sqrt(sum(x*x for x in v))
    if length < 1.e-9:
        raise ValueError('Atmosphere direction must not be zero')
    return tuple(x/length for x in v)


def load_profile(path):
    p = json.loads(Path(path).read_text(encoding='utf-8'))
    if p.get('schema') != 1:
        raise ValueError('Unsupported dusk atmosphere schema')
    for section, fields in {
        'sky': ('horizon','zenith','sunsetDirection','sunsetColor','cloudTint'),
        'ambient': ('sky','equator','ground'), 'fog': ('color',),
        'key': ('towardLight','color'), 'fill': ('towardLight','color')}.items():
        for field in fields:
            value=p[section][field]
            if len(value)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in value):
                raise ValueError('Invalid atmosphere vector: '+section+'.'+field)
    for light in ('key','fill'):
        _normalize(p[light]['towardLight'])
    _normalize(p['sky']['sunsetDirection'][:2])
    scalar_fields={
        'sky':('strength','altitudePower','sunsetPower','sunsetHeight','sunsetWidth','cloudScale','cloudStretch','cloudHeight','cloudOpacity','cloudShade'),
        'ambient':('intensity','blenderDiffuseStrength'), 'fog':('density','comparisonDensity'),
        'key':('unityIntensity','blenderEnergy','blenderAngle'), 'fill':('unityIntensity','blenderEnergy','blenderAngle'),
        'display':('blenderExposure','unityPostExposure','unityTemperature','unitySaturation')}
    for section,fields in scalar_fields.items():
        for field in fields:
            if not isinstance(p[section][field],(int,float)) or not math.isfinite(p[section][field]):
                raise ValueError('Non-finite atmosphere value: '+section+'.'+field)
    for field in ('strength','altitudePower','sunsetPower','sunsetWidth','cloudScale','cloudStretch','cloudHeight'):
        if p['sky'][field]<=0:raise ValueError('Atmosphere sky value must be positive: '+field)
    if not 0<=p['sky']['cloudOpacity']<=1 or not 0<=p['sky']['cloudShade']<=1:
        raise ValueError('Atmosphere cloud opacity/shade must be in [0,1]')
    if not 0 <= p['fog']['density'] <= .01:
        raise ValueError('Invalid atmosphere fog density')
    if not 0 < p['sky']['altitudePower'] or not 0 < p['sky']['sunsetWidth']:
        raise ValueError('Invalid atmosphere sky shape')
    if not 0 <= p['sky']['cloudThreshold'][0] < p['sky']['cloudThreshold'][1] <= 1:
        raise ValueError('Invalid atmosphere cloud thresholds')
    return p


def profile_digest(profile):
    return hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def fog_transmission(depth, density):
    return math.exp(-(max(0.,depth)*density)**2)


def _sat(x): return min(1.,max(0.,x))
def _lerp(a,b,t): return a+(b-a)*t
def _smooth(a,b,x):
    t=_sat((x-a)/(b-a));return t*t*(3-2*t)
def _fract(x): return x-math.floor(x)
def _hash(x,y): return _fract(math.sin(x*127.1+y*311.7)*43758.5453)
def _noise(x,y):
    ix,iy=math.floor(x),math.floor(y);fx,fy=_fract(x),_fract(y)
    fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    return _lerp(_lerp(_hash(ix,iy),_hash(ix+1,iy),fx),_lerp(_hash(ix,iy+1),_hash(ix+1,iy+1),fx),fy)

def fbm(x,y):
    value=0.;amplitude=.5
    for _ in range(5):
        value+=_noise(x,y)*amplitude;x=x*2.07+17.3;y=y*2.07+17.3;amplitude*=.5
    return value


def sky_radiance(direction, profile):
    """Double-precision reference, not a GPU bit-parity claim."""
    s=profile['sky'];x,y,z=_normalize(direction)
    t=_sat(z)**s['altitudePower'];az=_normalize((x+.00001,y+.00001));sun=_normalize(s['sunsetDirection'][:2])
    sunset=_sat(sum(a*b for a,b in zip(az,sun)))**s['sunsetPower']
    band=math.exp(-((z-s['sunsetHeight'])*s['sunsetWidth'])**2)*sunset
    p=s['cloudScale']/max(.11,z+.2)
    cloud=_smooth(*s['cloudThreshold'],fbm(x*p,y*p*s['cloudStretch']))
    amount=cloud*_smooth(0,s['cloudHeight'],z)*s['cloudOpacity']
    c=[_lerp(a,b,t)+w*band for a,b,w in zip(s['horizon'],s['zenith'],s['sunsetColor'])]
    return tuple(_lerp(v,v*s['cloudShade']+w,amount)*s['strength'] for v,w in zip(c,s['cloudTint']))


class _Nodes:
    def __init__(self, tree): self.n,self.l=tree.nodes,tree.links
    def set(self, socket, value):
        if hasattr(value,'node'): self.l.new(value,socket)
        else: socket.default_value=value
    def math(self, operation, *values):
        n=self.n.new('ShaderNodeMath');n.operation=operation
        for socket,value in zip(n.inputs,values):self.set(socket,value)
        return n.outputs[0]
    def mix(self,a,b,t):return self.math('ADD',a,self.math('MULTIPLY',self.math('SUBTRACT',b,a),t))
    def sat(self,x):return self.math('MINIMUM',1.,self.math('MAXIMUM',0.,x))
    def smooth(self,a,b,x):
        t=self.sat(self.math('DIVIDE',self.math('SUBTRACT',x,a),b-a))
        return self.math('MULTIPLY',self.math('MULTIPLY',t,t),self.math('SUBTRACT',3.,self.math('MULTIPLY',2.,t)))
    def rgb(self,channels):
        node=self.n.new('ShaderNodeCombineXYZ')
        for socket,c in zip(node.inputs,channels):self.set(socket,c)
        return node.outputs[0]
    def hash(self,x,y):
        d=self.math('ADD',self.math('MULTIPLY',x,127.1),self.math('MULTIPLY',y,311.7))
        return self.math('FRACT',self.math('MULTIPLY',self.math('SINE',d),43758.5453))
    def noise(self,x,y):
        ix,iy=self.math('FLOOR',x),self.math('FLOOR',y)
        fx,fy=self.math('FRACT',x),self.math('FRACT',y)
        fx=self.math('MULTIPLY',self.math('MULTIPLY',fx,fx),self.math('SUBTRACT',3.,self.math('MULTIPLY',2.,fx)))
        fy=self.math('MULTIPLY',self.math('MULTIPLY',fy,fy),self.math('SUBTRACT',3.,self.math('MULTIPLY',2.,fy)))
        jx,jy=self.math('ADD',ix,1.),self.math('ADD',iy,1.)
        return self.mix(self.mix(self.hash(ix,iy),self.hash(jx,iy),fx),self.mix(self.hash(ix,jy),self.hash(jx,jy),fx),fy)
    def fbm(self,x,y):
        v=0.;amplitude=.5
        for octave in range(5):
            v=self.math('ADD',v,self.math('MULTIPLY',self.noise(x,y),amplitude))
            if octave<4:
                x=self.math('ADD',self.math('MULTIPLY',x,2.07),17.3)
                y=self.math('ADD',self.math('MULTIPLY',y,2.07),17.3)
            amplitude*=.5
        return v


def configure_world(bpy, profile):
    s=profile['sky'];ambient=profile['ambient'];world=bpy.data.worlds.new('Shared authored dusk')
    bpy.context.scene.world=world;world.use_nodes=True;world.node_tree.nodes.clear()
    b=_Nodes(world.node_tree);n,l=b.n,b.l
    out=n.new('ShaderNodeOutputWorld');tex=n.new('ShaderNodeTexCoord')
    neg=n.new('ShaderNodeVectorMath');neg.operation='SCALE';neg.inputs[3].default_value=-1.
    l.new(tex.outputs['Normal'],neg.inputs[0]);neg.label='Outward sky = -World Normal (verified in Cycles)'
    sep=n.new('ShaderNodeSeparateXYZ');l.new(neg.outputs[0],sep.inputs[0]);x,y,z=sep.outputs
    t=b.math('POWER',b.sat(z),s['altitudePower'])
    azx,azy=b.math('ADD',x,.00001),b.math('ADD',y,.00001)
    length=b.math('SQRT',b.math('ADD',b.math('MULTIPLY',azx,azx),b.math('MULTIPLY',azy,azy)))
    sun=_normalize(s['sunsetDirection'][:2])
    dot=b.math('DIVIDE',b.math('ADD',b.math('MULTIPLY',azx,sun[0]),b.math('MULTIPLY',azy,sun[1])),length)
    directional=b.math('POWER',b.sat(dot),s['sunsetPower'])
    height=b.math('MULTIPLY',b.math('SUBTRACT',z,s['sunsetHeight']),s['sunsetWidth'])
    band=b.math('MULTIPLY',b.math('EXPONENT',b.math('MULTIPLY',b.math('MULTIPLY',height,height),-1.)),directional)
    scale=b.math('DIVIDE',s['cloudScale'],b.math('MAXIMUM',.11,b.math('ADD',z,.2)))
    noise=b.fbm(b.math('MULTIPLY',x,scale),b.math('MULTIPLY',b.math('MULTIPLY',y,scale),s['cloudStretch']))
    amount=b.math('MULTIPLY',b.math('MULTIPLY',b.smooth(*s['cloudThreshold'],noise),b.smooth(0,s['cloudHeight'],z)),s['cloudOpacity'])
    colors=[]
    for h,zen,w,tint in zip(s['horizon'],s['zenith'],s['sunsetColor'],s['cloudTint']):
        c=b.math('ADD',b.mix(h,zen,t),b.math('MULTIPLY',w,band))
        colors.append(b.mix(c,b.math('ADD',b.math('MULTIPLY',c,s['cloudShade']),tint),amount))
    visible=n.new('ShaderNodeBackground');visible.label='Same radiance for camera, glossy and transmission rays'
    visible.inputs['Strength'].default_value=s['strength'];l.new(b.rgb(colors),visible.inputs['Color'])
    diffuse=n.new('ShaderNodeBackground');diffuse.label='Approximate independent Unity Trilight; not reflected sky'
    diffuse.inputs['Strength'].default_value=ambient['intensity']*ambient['blenderDiffuseStrength']
    up=b.sat(z);down=b.sat(b.math('MULTIPLY',z,-1.))
    col=[b.mix(b.mix(eq,hi,up),lo,down) for eq,hi,lo in zip(ambient['equator'],ambient['sky'],ambient['ground'])]
    l.new(b.rgb(col),diffuse.inputs['Color'])
    ray=n.new('ShaderNodeLightPath');mix=n.new('ShaderNodeMixShader')
    l.new(ray.outputs['Is Diffuse Ray'],mix.inputs[0]);l.new(visible.outputs[0],mix.inputs[1]);l.new(diffuse.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
    return {'worldNodes':len(n),'outwardDirection':'negative World Texture Coordinate Normal','visibleGlossyStrength':s['strength'],'diffuseStrength':diffuse.inputs['Strength'].default_value}


def configure_sun(light, spec):
    """Configure an existing Blender SUN only; source towardLight is surface→sky."""
    from mathutils import Vector
    light.data.color=spec['color'];light.data.energy=spec['blenderEnergy'];light.data.angle=spec['blenderAngle']
    light.rotation_euler=(-Vector(_normalize(spec['towardLight']))).to_track_quat('-Z','Y').to_euler()


def configure_surface_fog(bpy, profile):
    """Camera-depth Exp2 closure blend, retaining each original alpha/outer mix.

    Does not affect diffuse/glossy rays, transparency gaps, normals, base color,
    emission settings or textures. Blender view-Z vs Unity clip-depth, fog in
    reflected probes, and glTF material differences remain approximations.
    """
    fog=profile['fog'];tree=bpy.data.node_groups.new('Shared dusk camera-depth Exp2','ShaderNodeTree')
    tree.interface.new_socket(name='Amount',in_out='OUTPUT',socket_type='NodeSocketFloat')
    b=_Nodes(tree);cam=b.n.new('ShaderNodeCameraData');ray=b.n.new('ShaderNodeLightPath')
    scaled=b.math('MULTIPLY',b.math('MAXIMUM',0.,cam.outputs['View Z Depth']),fog['density'])
    transmission=b.math('EXPONENT',b.math('MULTIPLY',b.math('MULTIPLY',scaled,scaled),-1.))
    amount=b.math('MULTIPLY',b.math('SUBTRACT',1.,transmission),ray.outputs['Is Camera Ray'])
    out=b.n.new('NodeGroupOutput');b.l.new(amount,out.inputs['Amount'])
    supported=[];unsupported=[];closure_count=0
    for mat in bpy.data.materials:
        if not mat.use_nodes:continue
        n,l=mat.node_tree.nodes,mat.node_tree.links
        closures=[node for node in n if node.type=='BSDF_PRINCIPLED' and node.outputs[0].is_linked]
        if not closures:
            if any(node.type=='OUTPUT_MATERIAL' and node.inputs['Surface'].is_linked for node in n):unsupported.append(mat.name)
            continue
        factor=n.new('ShaderNodeGroup');factor.node_tree=tree
        # Every original preview emitter has already been made camera-only and
        # the preview uses explicit lantern lights. Fog emission is camera-only
        # too: exclude these artificial closures from Cycles mesh-light sampling
        # or the world gains thousands of zero-energy sampled emitters/noise.
        mat.cycles.emission_sampling='NONE'
        camera_ray=n.new('ShaderNodeLightPath')
        for node in closures:
            destinations=[link.to_socket for link in list(node.outputs[0].links)]
            emission=n.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(*fog['color'],1.);emission.inputs['Strength'].default_value=1.
            l.new(camera_ray.outputs['Is Camera Ray'],emission.inputs['Strength'])
            replacement=emission.outputs[0]
            # Imported glTF uses Principled Alpha as well as outer transparent
            # shader mixes. Preserve both, including linked texture/cutout alpha.
            alpha=node.inputs.get('Alpha')
            if alpha and (alpha.is_linked or alpha.default_value<1.):
                transparent=n.new('ShaderNodeBsdfTransparent');opacity=n.new('ShaderNodeMixShader')
                if alpha.is_linked:l.new(alpha.links[0].from_socket,opacity.inputs[0])
                else:opacity.inputs[0].default_value=alpha.default_value
                l.new(transparent.outputs[0],opacity.inputs[1]);l.new(replacement,opacity.inputs[2]);replacement=opacity.outputs[0]
            blend=n.new('ShaderNodeMixShader');blend.label='Exp2 haze, preserves original alpha and outer cutout'
            l.new(factor.outputs['Amount'],blend.inputs[0]);l.new(node.outputs[0],blend.inputs[1]);l.new(replacement,blend.inputs[2])
            for socket in destinations:l.new(blend.outputs[0],socket)
            closure_count+=1
        supported.append(mat.name)
    return {'method':'camera-only exp(-(density * max(0, View Z Depth))^2) surface closure blend','density':fog['density'],'color':fog['color'],'materials':len(supported),'closures':closure_count,'unsupportedMaterials':unsupported,'volumeObjects':0,'preservesAlpha':True,'foggedReflections':False,'emissionSampling':'NONE; preview originals and fog are camera-only, explicit lamps retained'}
