"""Existing Foliage emission approximation only; no new runtime effect.
Call after the preview's general emissive-camera gate and before surface fog.
"""
def configure_foliage_emission(bpy, materials):
    selected={m['name'] for m in materials if m.get('shader')=='Foliage'}
    report={'scope':'Existing runtime c * .035, camera rays only; not Unity shading parity',
            'applied':[],'omitted':[],'newImageNodes':0,
            'limitations':['No wind or exact backface TBN emulation.','No emissive indirect lighting or reflection contribution in this preview.','Imported quantized tint, normal decoding and BSDF differ from Unity.']}
    imported={mat.name for mat in bpy.data.materials}
    for name in sorted(selected-imported):
        report['omitted'].append({'name':name,'reason':'Manifest material not imported into scene'})
    for mat in bpy.data.materials:
        if mat.name not in selected:continue
        if not mat.use_nodes:
            report['omitted'].append({'name':mat.name,'reason':'Material does not use nodes'});continue
        if mat.get('_yokocho_foliage_emission_preview'):
            report['omitted'].append({'name':mat.name,'reason':'Already applied'});continue
        tree=mat.node_tree;bs=[n for n in tree.nodes if n.type=='BSDF_PRINCIPLED']
        if len(bs)!=1:
            report['omitted'].append({'name':mat.name,'reason':'Expected one imported Principled'});continue
        bs=bs[0];base=bs.inputs['Base Color'];em=bs.inputs['Emission Color'];strength=bs.inputs['Emission Strength']
        if em.is_linked or strength.is_linked or strength.default_value!=0:
            report['omitted'].append({'name':mat.name,'reason':'Existing emission preserved'});continue
        if base.is_linked:tree.links.new(base.links[0].from_socket,em)
        else:em.default_value=base.default_value
        ray=tree.nodes.new('ShaderNodeLightPath');mul=tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.035
        tree.links.new(ray.outputs['Is Camera Ray'],mul.inputs[0]);tree.links.new(mul.outputs[0],strength)
        mat['_yokocho_foliage_emission_preview']=True
        report['applied'].append({'name':mat.name,'factor':.035,'reusesImportedBaseColor':True,'cameraOnly':True})
    return report
