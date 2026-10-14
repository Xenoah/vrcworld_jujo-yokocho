"""Optional Blender material approximation of FantasyMaterials profile.

Never a Unity runtime capture. Does not alter geometry, cameras, lights or fog.
Water matches world-position/phase texture-coordinate formulas, but Blender's
normal image decoding, filtering and Principled BSDF differ from Unity Standard.
"""
from pathlib import Path
import json
import math


def parameters(items):
    return {p['name']: p['value'] for p in items}


def analytic_water_normal(x, y, seconds=0, slope=.018):
    """Resolved long-wave-only normal, source XYZ/Z-up; excludes normal texture."""
    wa=(-.6*x+.8*y)*.021+seconds*.07
    wb=(.8*x+.6*y)*.017-seconds*.05
    pa=(.8*x+.6*y)*.13+seconds*.4+1.1*math.sin(wa)
    pb=(-.6*x+.8*y)*.19-seconds*.28+.8*math.sin(wb)
    ga=(.8-.6*(.021*1.1/.13)*math.cos(wa), .6+.8*(.021*1.1/.13)*math.cos(wa))
    gb=(-.6+.8*(.017*.8/.19)*math.cos(wb), .8+.6*(.017*.8/.19)*math.cos(wb))
    nx=-(ga[0]*math.cos(pa)*.65+gb[0]*math.cos(pb)*.35)*slope
    ny=-(ga[1]*math.cos(pa)*.65+gb[1]*math.cos(pb)*.35)*slope
    length=math.sqrt(nx*nx+ny*ny+1)
    return nx/length,ny/length,1/length


def old_water_displacement(x,y,seconds=0):
    return math.sin(x*.13+seconds*.4)*.025+math.sin(y*.19-seconds*.28)*.018


def configure_materials(bpy, profile, root, seconds=0):
    from dusk_atmosphere import _Nodes
    report={'scope':'Blender approximation, NOT Unity runtime parity','timeSeconds':seconds,
            'materials':[], 'omitted':[], 'unsupported':[], 'waterDerivativeFilter':'Blender texture filtering; analytic fwidth fade not emulated',
            'cloth':'Principled sheen approximation; weave normal excluded to avoid unfiltered moire',
            'glaze':'Angle film multiplier on Principled Specular Tint; different BSDF/F0 mapping and geometric instead of mapped normal. Original base color, metallic and roughness retained.',
            'geometryChanged':False}
    mapping={name:g for g in profile['materialGroups'] for name in g['names']}
    for mat in bpy.data.materials:
        # Imported glTF may add numerical .001 suffixes. Match exact first.
        key=mat.name if mat.name in mapping else mat.name.rsplit('.',1)[0]
        if key not in mapping or not mat.use_nodes: continue
        group=mapping[key];p=parameters(group.get('floats',[]))
        if group['shader'] not in ('Cloth','LanternPaper','Water','Glaze'):
            report['omitted'].append({'name':mat.name,'shader':group['shader'],'reason':'Original glTF material retained; Unity craft/film response not approximated'})
            continue
        nodes=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
        if not nodes:report['unsupported'].append(mat.name);continue
        b=_Nodes(mat.node_tree)
        applied=False
        for bsdf in nodes:
            if group['shader']=='Cloth':
                # Preserve imported atlas/base colour and roughness links.
                bsdf.inputs['Sheen Weight'].default_value=p.get('_Sheen',.055)
                bsdf.inputs['Sheen Roughness'].default_value=.8
                applied=True
            elif group['shader']=='LanternPaper':
                # Call before camera-only emission wiring in render_preview.
                strength=bsdf.inputs['Emission Strength']
                if strength.is_linked:
                    report['unsupported'].append(mat.name+': linked emission; invoke before camera-only emission masking')
                else:
                    strength.default_value*=1+p.get('_Breath',0)*math.sin(seconds*.31)
                    applied=True
            elif group['shader']=='Glaze':
                geo=b.n.new('ShaderNodeNewGeometry')
                dot=b.n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
                b.l.new(geo.outputs['Normal'],dot.inputs[0]);b.l.new(geo.outputs['Incoming'],dot.inputs[1])
                ndv=b.sat(b.math('ABSOLUTE',dot.outputs['Value']))
                edge=b.math('SUBTRACT',1,ndv);grazing=b.math('MULTIPLY',edge,edge)
                metal=bsdf.inputs['Metallic']
                metal_value=metal.links[0].from_socket if metal.is_linked else metal.default_value
                weight=b.math('MULTIPLY',b.math('MULTIPLY',grazing,min(.25,max(0,p.get('_Iridescence',.18)))),b.math('SUBTRACT',1,metal_value))
                phase=b.math('MULTIPLY',edge,min(2,max(.2,p.get('_FilmCycles',.75)))*math.tau)
                channels=[]
                for offset in (0,2.0943951,4.1887902):
                    # Equivalent to 1 + (filmColour - 1) * weight.
                    cosine=b.math('COSINE',b.math('ADD',phase,offset))
                    channels.append(b.math('ADD',1,b.math('MULTIPLY',b.math('MULTIPLY',cosine,.4),weight)))
                tint=bsdf.inputs['Specular Tint']
                original=tint.links[0].from_socket if tint.is_linked else tuple(tint.default_value[:3])
                multiply=b.n.new('ShaderNodeVectorMath');multiply.operation='MULTIPLY'
                b.set(multiply.inputs[0],original);b.l.new(b.rgb(channels),multiply.inputs[1]);b.l.new(multiply.outputs[0],tint)
                applied=True
            elif group['shader']=='Water':
                geo=b.n.new('ShaderNodeNewGeometry');sep=b.n.new('ShaderNodeSeparateXYZ');b.l.new(geo.outputs['Position'],sep.inputs[0])
                x,y,_=sep.outputs;scale=p.get('_RippleScale',.035)
                uvx=b.math('MULTIPLY',x,scale);uvy=b.math('MULTIPLY',y,scale)
                def dotxy(dx,dy):return b.math('ADD',b.math('MULTIPLY',x,dx),b.math('MULTIPLY',y,dy))
                wa=b.math('ADD',b.math('MULTIPLY',dotxy(-.6,.8),.021),seconds*.07)
                wb=b.math('SUBTRACT',b.math('MULTIPLY',dotxy(.8,.6),.017),seconds*.05)
                pa=b.math('ADD',b.math('ADD',b.math('MULTIPLY',dotxy(.8,.6),.13),seconds*.4),b.math('MULTIPLY',b.math('SINE',wa),1.1))
                pb=b.math('ADD',b.math('SUBTRACT',b.math('MULTIPLY',dotxy(-.6,.8),.19),seconds*.28),b.math('MULTIPLY',b.math('SINE',wb),.8))
                ga=[b.math('ADD',d,b.math('MULTIPLY',b.math('COSINE',wa),w*.021*1.1/.13)) for d,w in zip((.8,.6),(-.6,.8))]
                gb=[b.math('ADD',d,b.math('MULTIPLY',b.math('COSINE',wb),w*.017*.8/.19)) for d,w in zip((-.6,.8),(.8,.6))]
                slopes=[b.math('MULTIPLY',b.math('ADD',b.math('MULTIPLY',b.math('MULTIPLY',ga[i],b.math('COSINE',pa)),.65),b.math('MULTIPLY',b.math('MULTIPLY',gb[i],b.math('COSINE',pb)),.35)),-p.get('_WaveSlope',.018)) for i in range(2)]
                imagepath=Path(root)/'Assets/TreeTopYokocho/Textures/water_normal.png'
                if not imagepath.exists():raise FileNotFoundError(imagepath)
                image=bpy.data.images.load(str(imagepath),check_existing=True);image.colorspace_settings.name='Non-Color'
                # Match the two UV samples, decode RGB xy explicitly. Unity
                # import may repack normal maps; this reads original source RGB.
                for repeat,tx,ty in [(1,.003,.002),(1.7,-.002,.001)]:
                    tex=b.n.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT'
                    rx,ry=uvx,uvy
                    if repeat!=1:
                        rx=b.math('SUBTRACT',b.math('MULTIPLY',uvx,.8),b.math('MULTIPLY',uvy,.6))
                        ry=b.math('ADD',b.math('MULTIPLY',uvx,.6),b.math('MULTIPLY',uvy,.8))
                    coords=b.rgb([b.math('ADD',b.math('MULTIPLY',rx,repeat),seconds*tx),b.math('ADD',b.math('MULTIPLY',ry,repeat),seconds*ty),0])
                    b.l.new(coords,tex.inputs['Vector']);rgb=b.n.new('ShaderNodeSeparateColor');rgb.mode='RGB';b.l.new(tex.outputs['Color'],rgb.inputs[0])
                    decoded=[b.math('SUBTRACT',b.math('MULTIPLY',rgb.outputs[i],2),1) for i in range(2)]
                    if repeat!=1:
                        dx,dy=decoded
                        decoded=[b.math('ADD',b.math('MULTIPLY',dx,.8),b.math('MULTIPLY',dy,.6)),b.math('ADD',b.math('MULTIPLY',dx,-.6),b.math('MULTIPLY',dy,.8))]
                    for axis in range(2):
                        slopes[axis]=b.math('ADD',slopes[axis],b.math('MULTIPLY',decoded[axis],p.get('_RippleStrength',.12)))
                normal=b.n.new('ShaderNodeVectorMath');normal.operation='NORMALIZE';b.l.new(b.rgb([*slopes,1]),normal.inputs[0]);b.l.new(normal.outputs[0],bsdf.inputs['Normal'])
                applied=True
            else:
                # Craft roughness uses Unity-sampled linear albedo and packed AO.
                # Preserve original rather than fake equivalent BRDF in Blender.
                continue
        if applied:report['materials'].append({'name':mat.name,'shader':group['shader'],'applied':True})
    return report


def configure_sky(bpy, dusk, profile, seconds=0):
    """Add matching aurora math to the existing authored world radiance.

    Stars are deliberately omitted: Blender nodes have no matching GPU fwidth
    and an unfiltered point field would falsely claim VR-stable star previews.
    Existing diffuse-ambient branch stays unchanged, just as runtime ambient is
    independently configured. Reflections use this static time snapshot.
    """
    from dusk_atmosphere import _Nodes
    sky=profile['sky'];p=parameters(sky.get('floats',[]));v=parameters(sky.get('vectors',[]))
    if '_YOKOCHO_FANTASY_SKY' not in sky.get('keywords',[]):return {'enabled':False}
    world=bpy.context.scene.world
    if not world or not world.use_nodes:raise ValueError('Configure shared dusk world first')
    tree=world.node_tree;b=_Nodes(tree)
    backgrounds=[n for n in b.n if n.type=='BACKGROUND' and n.label=='Same radiance for camera, glossy and transmission rays']
    if len(backgrounds)!=1:raise ValueError('Expected exactly one shared dusk visible background')
    background=backgrounds[0];socket=background.inputs['Color']
    if not socket.is_linked:raise ValueError('Shared dusk colour must have an input link')
    original=socket.links[0].from_socket
    tex=b.n.new('ShaderNodeTexCoord');neg=b.n.new('ShaderNodeVectorMath');neg.operation='SCALE';neg.inputs[3].default_value=-1
    b.l.new(tex.outputs['Normal'],neg.inputs[0]);sep=b.n.new('ShaderNodeSeparateXYZ');b.l.new(neg.outputs[0],sep.inputs[0]);x,y,z=sep.outputs
    angle=b.math('ARCTAN2',x,y);drift=seconds*min(.025,max(0,p.get('_AuroraMotion',.012)))
    wave=b.math('ADD',b.math('MULTIPLY',b.math('SINE',b.math('ADD',b.math('MULTIPLY',angle,3),drift)),.032),b.math('MULTIPLY',b.math('SINE',b.math('SUBTRACT',b.math('MULTIPLY',angle,7),drift*.61)),.015))
    height=b.math('ADD',min(.65,max(.15,p.get('_AuroraHeight',.27))),wave)
    band=b.math('EXPONENT',b.math('MULTIPLY',b.math('ABSOLUTE',b.math('SUBTRACT',z,height)),-min(60,max(16,p.get('_AuroraWidth',38)))))
    ribs=b.math('ADD',.66,b.math('MULTIPLY',.34,b.math('SINE',b.math('ADD',b.math('ADD',b.math('MULTIPLY',angle,31),b.math('MULTIPLY',b.math('SINE',b.math('MULTIPLY',angle,5)),2)),drift))))
    direction=v.get('_AuroraDirection',[0,0,1,0]);length=math.hypot(direction[0]+.00001,direction[2]+.00001)
    ax,ay=(direction[0]+.00001)/length,(direction[2]+.00001)/length
    xx,yy=b.math('ADD',x,.00001),b.math('ADD',y,.00001)
    radial=b.math('SQRT',b.math('ADD',b.math('MULTIPLY',xx,xx),b.math('MULTIPLY',yy,yy)))
    facing=b.math('POWER',b.sat(b.math('DIVIDE',b.math('ADD',b.math('MULTIPLY',xx,ax),b.math('MULTIPLY',yy,ay)),radial)),3)
    value=b.math('MULTIPLY',b.math('MULTIPLY',band,ribs),b.math('MULTIPLY',facing,b.smooth(.08,.18,z)))
    # Match both pre-cloud attenuation and the baseline cloud mix response.
    s=dusk['sky'];scale=b.math('DIVIDE',s['cloudScale'],b.math('MAXIMUM',.11,b.math('ADD',z,.2)))
    cloud=b.fbm(b.math('MULTIPLY',x,scale),b.math('MULTIPLY',b.math('MULTIPLY',y,scale),s['cloudStretch']))
    cover=b.math('MULTIPLY',b.math('MULTIPLY',b.smooth(*s['cloudThreshold'],cloud),b.smooth(0,s['cloudHeight'],z)),s['cloudOpacity'])
    uncovered=b.math('SUBTRACT',1,cover)
    attenuation=b.math('MULTIPLY',uncovered,b.math('ADD',uncovered,b.math('MULTIPLY',cover,s['cloudShade'])))
    strength=min(.15,max(0,p.get('_AuroraStrength',.035)))
    value=b.math('MULTIPLY',value,b.math('MULTIPLY',attenuation,strength))
    tint=v.get('_AuroraColor',[.10,.48,.42,0]);addition=b.rgb([b.math('MULTIPLY',value,max(0,c)) for c in tint[:3]])
    combine=b.n.new('ShaderNodeVectorMath');combine.operation='ADD';b.l.new(original,combine.inputs[0]);b.l.new(addition,combine.inputs[1]);b.l.new(combine.outputs[0],socket)
    return {'enabled':True,'timeSeconds':seconds,'aurora':'Matching formula; float precision and renderer differ','stars':'Omitted, no Blender equivalent of runtime footprint filter','diffuseAmbient':'Unchanged','geometryChanged':False,'radianceStrength':background.inputs['Strength'].default_value,'strengthApplication':'Existing Background Strength multiplies original plus aurora once'}
