"""Exact v2.16 GLB position/normal/Color32/index preservation and owned deltas."""
import copy
import json
from pathlib import Path
import rpg_identity_contract as c
GLB_BEFORE_NAME='rpg_identity_glb_before_2_16.json.gz'
GLB_BEFORE_SHA256='0058a99495b1ce3359e84f4d60e9c09c1a09bcf4924486497a8f5d4413942af2'

def audit(root,manifest=None,*,strict=False):
    from pygltflib import GLTF2
    from audit_shop_personality_glb import access,semantic_material,identity_scene_errors,image_fingerprints
    root=Path(root)
    if manifest is None:manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    import projecting_sign_contract as signs
    if signs.requested(manifest):
        from audit_projecting_sign_glb import audit as sign_audit
        return sign_audit(root,manifest,strict=strict)
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):
        from audit_s05_pendant_glb import audit as pendant_audit
        return pendant_audit(root,manifest,strict=strict)
    errors=c.validate_gate(manifest)
    if errors:return dict(status='FAIL',errors=errors)
    before=c._load(GLB_BEFORE_NAME,GLB_BEFORE_SHA256)
    flags=manifest['features'];identity,lighting=(flags[f] for f in c.FLAGS)
    path=root/'Source/TreeTopYokocho.glb';g=GLTF2().load(str(path))
    errors.extend(identity_scene_errors(g,'v2.17'))
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    def record(index):
        if index is None:return None
        a=g.accessors[index]
        return dict(componentType=a.componentType,normalized=a.normalized,type=a.type,count=a.count,sha256=c.sha(access(g,index).tobytes()),minimum=a.min,maximum=a.max,sparse=None if a.sparse is None else json.loads(a.sparse.to_json()),extensions=a.extensions,extras=a.extras)
    remap={'__'.join((a,b)):('__'.join((a,d)),d) for a,b,d in c.BINDINGS} if lighting else {}
    signs={'__'.join(k) for k in c.SIGN_KEYS} if identity else set()
    check(len(g.meshes)==len(before['meshes']),'GLB exact mesh roster count changed')
    for old,mesh in zip(before['meshes'],g.meshes):
        name,material=remap.get(old['name'],(old['name'],old['material']))
        check(mesh.name==name,'GLB exact mesh order/name changed',name=old['name'])
        if len(mesh.primitives)!=1:continue
        p=mesh.primitives[0]
        check(g.materials[p.material].name==material,'GLB owned material routing changed',name=name)
        actual={k:record(v) for k,v in vars(p.attributes).items()}
        wanted=copy.deepcopy(old['attributes'])
        if old['name'] in signs:
            a=actual.get('TEXCOORD_0');b=wanted['TEXCOORD_0']
            check(a is not None and {k:v for k,v in a.items() if k not in ('sha256','minimum','maximum')}=={k:v for k,v in b.items() if k not in ('sha256','minimum','maximum')},'Sign UV accessor format/count changed',name=name)
            uv=access(g,p.attributes.TEXCOORD_0)
            check(a['minimum']==uv.min(axis=0).tolist() and a['maximum']==uv.max(axis=0).tolist(),'Owned UV bounds must equal actual UV data',name=name)
            actual.pop('TEXCOORD_0',None);wanted.pop('TEXCOORD_0',None)
        check(actual==wanted,'GLB non-UV attributes including normals changed',name=name)
        check(record(p.indices)==old['indices'],'GLB indices changed',name=name)
    mats={m.name:semantic_material(g,m) for m in g.materials}
    extra={dst for _,_,dst in c.BINDINGS} if lighting else set()
    check(set(mats)==set(before['materials'])|extra,'GLB exact material roster changed')
    replacements={}
    if identity:
        for material in ('Food_Sign','Night_Print'):
            try:
                old=before['materials'][material]['pbrMetallicRoughness']['baseColorTexture']['image']['sha256']
                new=mats[material]['pbrMetallicRoughness']['baseColorTexture']['image']['sha256']
                replacements[old]=new
            except (KeyError,TypeError):errors.append(dict(reason='Missing owned atlas reference',material=material))
    def replace_images(value):
        if isinstance(value,list):return [replace_images(v) for v in value]
        if isinstance(value,dict):return {k:(replacements.get(v,v) if k=='sha256' else replace_images(v)) for k,v in value.items()}
        return value
    for name,old in before['materials'].items():
        check(mats.get(name)==replace_images(old),'Original GLB material/texture semantic changed',material=name)
    # Clones may change only authored visible RGB/emission, never texture or PBR routing.
    for _,src,dst in c.BINDINGS if lighting else ():
        if dst not in mats:continue
        old=copy.deepcopy(before['materials'][src]);new=copy.deepcopy(mats[dst])
        old['name']=dst;old['emissiveFactor']=new.get('emissiveFactor')
        old['pbrMetallicRoughness']['baseColorFactor']=new['pbrMetallicRoughness'].get('baseColorFactor')
        check(old==new,'GLB fixture clone changed unrelated material/texture fields',material=dst)
    check(image_fingerprints(g)==replace_images(before['images']),'GLB embedded image roster or unowned bytes changed')
    actual_sha=c.sha(path.read_bytes())
    if strict:
        oracle=c.load_oracle(root)
        check(actual_sha==oracle['variants'][c.variant_key(manifest)]['glbSha256'],'Editable GLB differs from frozen reviewed artifact')
    return dict(status='FAIL' if errors else 'PASS',errors=errors,glbSha256=actual_sha,exactMeshCount=len(before['meshes']),scope='Exact positions, normals, colors, indices and scene placement; only eight owned sign UVs, two atlas images and twelve fixture material bindings may differ. No Unity bake/runtime claim.')
