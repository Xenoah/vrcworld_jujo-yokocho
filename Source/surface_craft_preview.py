"""Opt-in bounded Surface craft formula on existing Blender material samples.

No image nodes, texture fetch inputs, base colour, normal or emission links are
created/changed. Blender BSDF/filtering, glTF tint quantization and absence of
Unity parallax remain explicit differences. Call once, after import, before fog.
"""


def craft_response(roughness,metallic,grain,ao,grain_strength,patina_strength):
    """Scalar reference for testing the node graph's exact bounded modulation."""
    sat=lambda v:min(1.,max(0.,v))
    patina=sat(1-ao)*min(.35,max(0,patina_strength))
    smooth=sat(1-sat(roughness)+(grain-.5)*min(.25,max(0,grain_strength))-.25*patina)
    return 1-smooth,sat(metallic)*(1-patina)


def _active_rgba(node,name):
    return next((s for s in node.inputs if s.name==name and s.type=='RGBA' and s.enabled),None)

def _socket_or_value(socket):
    return socket.links[0].from_socket if socket.is_linked else socket.default_value


def configure_surface_craft(bpy,profile,materials):
    from dusk_atmosphere import _Nodes
    specs={m['name']:m for m in materials}
    selected={name:g for g in profile['materialGroups'] if g['shader']=='Surface' and '_YOKOCHO_CRAFT' in g.get('keywords',[]) for name in g['names']}
    report={'scope':'Bounded source-formula approximation, NOT Unity BRDF/texture/parallax parity',
            'materials':[],'omitted':[],'newImageNodes':0,'baseNormalEmissionLinksChanged':False,
            'inputs':'Reused glTF linear base image and imported pre-vertex colour factor; packed AO when manifest ARM is present.',
            'differences':['Imported glTF tint is quantized versus manifest/Unity material tint.','Unity parallax, normal import/compression and texture mip filtering are not reproduced.','Blender Principled roughness/metallic response differs from Unity Standard even for equal scalar values.']}
    for mat in bpy.data.materials:
        key=mat.name if mat.name in selected else mat.name.rsplit('.',1)[0]
        if key not in selected or not mat.use_nodes:continue
        if mat.get('_yokocho_surface_craft_preview_applied'):
            report['omitted'].append({'name':mat.name,'reason':'Already applied; no duplicate modulation'});continue
        g=selected[key];spec=specs[key];p={x['name']:x['value'] for x in g.get('floats',[])}
        tree=mat.node_tree;nodes=list(tree.nodes)
        base_images=[n for n in nodes if n.type=='TEX_IMAGE' and n.label=='BASE COLOR']
        factors=[n for n in nodes if n.type=='MIX' and n.label=='Color Factor' and n.blend_type=='MULTIPLY']
        bsdfs=[n for n in nodes if n.type=='BSDF_PRINCIPLED']
        if len(bsdfs)!=1 or len(factors)>1 or (spec.get('texture') and len(base_images)!=1):
            report['omitted'].append({'name':mat.name,'reason':'Unexpected imported graph; preserve baseline rather than guess'});continue
        factor=(1.,1.,1.)
        if factors:
            socket=_active_rgba(factors[0],'B')
            if socket is None or socket.is_linked:
                report['omitted'].append({'name':mat.name,'reason':'Colour-factor graph not a plain imported constant'});continue
            factor=tuple(socket.default_value[:3])
        elif any(abs(float(c)-1.0)>1e-6 for c in spec.get('color',(1,1,1))[:3]):
            report['omitted'].append({'name':mat.name,'reason':'Nonwhite material lacks an explicit imported colour factor; refuse white assumption'})
            continue
        ao=1.0
        if spec.get('arm'):
            packed=[n for n in nodes if n.type=='TEX_IMAGE' and n.label=='METALLIC ROUGHNESS']
            if len(packed)!=1:
                report['omitted'].append({'name':mat.name,'reason':'Manifest ARM lacks unique existing packed image output'});continue
            # Reuse existing red-separation when present; otherwise arithmetic
            # channel separation only, still no additional image node.
            red=None
            for link in packed[0].outputs['Color'].links:
                if link.to_node.type=='SEPARATE_COLOR':red=link.to_node.outputs['Red'];break
            if red is None:
                separate=tree.nodes.new('ShaderNodeSeparateColor');separate.mode='RGB';tree.links.new(packed[0].outputs['Color'],separate.inputs['Color']);red=separate.outputs['Red']
            ao=red
        bsdf=bsdfs[0];b=_Nodes(tree)
        rough_before=_socket_or_value(bsdf.inputs['Roughness']);metal_before=_socket_or_value(bsdf.inputs['Metallic'])
        # Grain excludes vertex AO/tint exactly as Surface.surf does.
        base=base_images[0].outputs['Color'] if spec.get('texture') else (1.,1.,1.)
        multiply=tree.nodes.new('ShaderNodeVectorMath');multiply.operation='MULTIPLY';b.set(multiply.inputs[0],base);b.set(multiply.inputs[1],factor)
        dot=tree.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';tree.links.new(multiply.outputs[0],dot.inputs[0]);dot.inputs[1].default_value=(.2126,.7152,.0722)
        grain=b.math('MULTIPLY',b.math('SUBTRACT',dot.outputs['Value'],.5),min(.25,max(0,p.get('_GrainRoughness',0))))
        patina=b.math('MULTIPLY',b.sat(b.math('SUBTRACT',1,ao)),min(.35,max(0,p.get('_Patina',0))))
        # R' = 1 - saturate(1 - saturate(R) + grain - .25*patina).
        smooth=b.sat(b.math('SUBTRACT',b.math('ADD',b.math('SUBTRACT',1,b.sat(rough_before)),grain),b.math('MULTIPLY',patina,.25)))
        rough=b.math('SUBTRACT',1,smooth);metal=b.math('MULTIPLY',b.sat(metal_before),b.math('SUBTRACT',1,patina))
        tree.links.new(rough,bsdf.inputs['Roughness']);tree.links.new(metal,bsdf.inputs['Metallic'])
        mat['_yokocho_surface_craft_preview_applied']=True
        report['materials'].append({'name':mat.name,'grainRoughness':p.get('_GrainRoughness',0),'patina':p.get('_Patina',0),'patinaEffective':bool(spec.get('arm')) and p.get('_Patina',0)>0,'importedTint':list(factor),'parallaxNotEmulated':spec.get('parallax',0)>0})
    report['modulationSummary']={
        'grainControlNonzeroMaterialCount':sum(x['grainRoughness']>0 for x in report['materials']),
        'patinaControlNonzeroMaterialCount':sum(x['patina']>0 for x in report['materials']),
        'patinaCanBeNonzeroGivenARMCount':sum(x['patinaEffective'] for x in report['materials']),
        'note':'Enabled control is not proof of a nonzero output after clamps or a visible image difference. No substitute AO/weathering mask is generated.'}
    return report
