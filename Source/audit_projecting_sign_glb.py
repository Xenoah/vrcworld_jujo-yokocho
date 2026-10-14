"""Exact complete v2.18 GLB complement plus native-corresponding added signs."""
import copy,json
from collections import Counter
from pathlib import Path
import numpy as np
import projecting_sign_contract as c
BEFORE_NAME='projecting_sign_glb_before_2_18.json.gz'
BEFORE_SHA256='cc683100485b17bf3869c876b88ce63719cd68537a97f92c9f7c9b7e6c204554'
ACTIVATED_MATERIALS=('Noren1','Noren3')
WOVEN_ARM_IMAGE=dict(mimeType='image/jpeg',sha256='9d401fa95699878b1f1c7b1b823bfac1d8648dbcef2ae6a70f0bb020e960313a')

def activated_material(name,old):
    # Exact existing source descriptors, not new material creation. They share
    # baseline woven albedo/normal and activate the existing woven ARM asset.
    result=copy.deepcopy(old['materials']['Night_WineUpholstery']);result['name']=name
    color={'Noren1':(.76,.66,.46),'Noren3':(.12,.24,.16)}[name]
    p=result['pbrMetallicRoughness'];p['baseColorFactor']=[int(v*255)/255 for v in color]+[1.]
    p['roughnessFactor']=1.;result['normalTexture']['scale']=1.
    p['metallicRoughnessTexture']=dict(extensions={},extras={},texCoord=0,image=WOVEN_ARM_IMAGE,sampler=None)
    result['occlusionTexture']=dict(extensions={},extras={},texCoord=None,strength=1.,image=WOVEN_ARM_IMAGE,sampler=None)
    return result

def texture_semantics(textures,images,samplers):
    out=[]
    for t in textures:
        v=dict(t);source=v.pop('source');sampler=v.pop('sampler',None);v['image']=images[source];v['sampler']=None if sampler is None else samplers[sampler];out.append(v)
    return out

def audit(root,manifest=None,*,strict=False):
    from pygltflib import GLTF2
    from audit_shop_personality_glb import access,semantic_material,identity_scene_errors,image_fingerprints
    from peer_culling_contract import read_visual
    root=Path(root)
    if manifest is None:manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    errors=c.validate_gate(manifest)
    if errors:return dict(status='FAIL',errors=errors)
    old=c._load(BEFORE_NAME,BEFORE_SHA256);path=root/'Source/TreeTopYokocho.glb';g=GLTF2().load(str(path));errors.extend(identity_scene_errors(g,'current v2.19 signs'))
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    def record(index):
        if index is None:return None
        a=g.accessors[index]
        return dict(componentType=a.componentType,normalized=a.normalized,type=a.type,count=a.count,sha256=c.sha(access(g,index).tobytes()),minimum=a.min,maximum=a.max,sparse=None if a.sparse is None else json.loads(a.sparse.to_json()),extensions=a.extensions,extras=a.extras)
    def view_record(v):
        value=json.loads(v.to_json());offset=value.pop('byteOffset',None) or 0;value['sha256']=c.sha(g.binary_blob()[offset:offset+v.byteLength]);return value
    def image_record(im):
        value=json.loads(im.to_json());index=value.pop('bufferView');v=g.bufferViews[index];value['sha256']=c.sha(g.binary_blob()[(v.byteOffset or 0):(v.byteOffset or 0)+v.byteLength]);return value
    byname={m.name:m for m in g.meshes};prior={m['name']:m for m in old['meshes']};new={'__'.join(k) for k in c.KEYS}
    check(bool(new) and len(g.meshes)==len(byname)==len(prior)+len(new) and set(byname)==set(prior)|new,'GLB exact additive mesh roster changed')
    check([m.name for m in g.meshes if m.name not in new]==[r['name'] for r in old['meshes']],'Existing GLB mesh/node order changed')
    for name,pin in prior.items():
        mesh=byname.get(name)
        if mesh is None or len(mesh.primitives)!=1:continue
        p=mesh.primitives[0]
        check(g.materials[p.material].name==pin['material'],'Existing GLB material binding changed',mesh=name)
        check({k:record(v) for k,v in vars(p.attributes).items()}==pin['attributes'] and record(p.indices)==pin['indices'],'Existing GLB position/normal/UV/Color32/index arrays or accessor semantics changed',mesh=name)
    mats={m.name:semantic_material(g,m) for m in g.materials}
    check(len(g.materials)==len(mats)==len(old['materials'])+2 and set(mats)==set(old['materials'])|set(ACTIVATED_MATERIALS),'GLB allows only exact existing Noren1/Noren3 activation')
    for name,pin in old['materials'].items():check(mats.get(name)==pin,'Existing GLB material/texture semantics changed',material=name)
    for name in ACTIVATED_MATERIALS:check(mats.get(name)==activated_material(name,old),'Activated existing cloth material differs from unchanged descriptor/texture semantics',material=name)
    images=image_fingerprints(g);expected_images=old['images']+[WOVEN_ARM_IMAGE]
    check(Counter(map(c.digest,images))==Counter(map(c.digest,expected_images)),'Embedded images changed beyond one existing woven ARM activation')
    image_descriptors=[image_record(im) for im in g.images]
    extra_image=dict(extensions={},extras={},mimeType=WOVEN_ARM_IMAGE['mimeType'],name=None,sha256=WOVEN_ARM_IMAGE['sha256'],uri=None)
    check(Counter(map(c.digest,image_descriptors))==Counter(map(c.digest,old['imageDescriptors']+[extra_image])),'Embedded image descriptors/extensions changed')
    samplers=[json.loads(s.to_json()) for s in g.samplers]
    check(samplers==old['samplers'],'GLB sampler semantics changed')
    textures=[json.loads(t.to_json()) for t in g.textures]
    old_tex=texture_semantics(old['textures'],old['images'],old['samplers']);current_tex=texture_semantics(textures,images,samplers)
    expected_tex=list(old_tex)
    for name in ACTIVATED_MATERIALS:
        mat=activated_material(name,old)
        for item in (mat['pbrMetallicRoughness']['baseColorTexture'],mat['normalTexture'],mat['occlusionTexture'],mat['pbrMetallicRoughness']['metallicRoughnessTexture']):
            expected_tex.append(dict(extensions={},extras={},name=None,image=item['image'],sampler=item['sampler']))
    check(Counter(map(c.digest,current_tex))==Counter(map(c.digest,expected_tex)),'GLB texture tables changed beyond exact activated cloth references')
    raw=json.loads(g.to_json());header={k:v for k,v in raw.items() if k not in ('accessors','bufferViews','buffers','images','materials','meshes','nodes','samplers','scenes','textures')}
    scene=json.loads(g.scenes[0].to_json()) if len(g.scenes)==1 else {};scene.pop('nodes',None)
    check(header==old['header'] and scene==old['scene'],'GLB header/scene semantics changed beyond exact added identity nodes')
    # Table indices may shift/deduplicate. Every old accessor, even an unused
    # historical normal accessor, survives with exact metadata and array bytes.
    current_accessors=[record(i) for i in range(len(g.accessors))]
    before_counts=Counter(map(c.digest,old['allAccessors']));current_counts=Counter(map(c.digest,current_accessors))
    check(not(before_counts-current_counts),'An original GLB accessor payload/descriptor was lost or mutated')
    added_indices=set()
    for name in new:
        mesh=byname.get(name)
        if mesh is None:continue
        for p in mesh.primitives:
            added_indices.add(p.indices);added_indices.update(v for v in vars(p.attributes).values() if v is not None)
    allowed_extra=Counter(c.digest(current_accessors[i]) for i in added_indices)
    check(not((current_counts-before_counts)-allowed_extra),'GLB acquired an unowned hidden accessor')
    views=[view_record(v) for v in g.bufferViews];old_views=Counter(map(c.digest,old['allBufferViews']));current_views=Counter(map(c.digest,views))
    check(not(old_views-current_views),'An original GLB raw buffer view or descriptor was lost/modified')
    new_view_ids={g.accessors[i].bufferView for i in added_indices}|{im.bufferView for im,desc in zip(g.images,image_descriptors) if desc==extra_image}
    allowed_views=Counter(c.digest(views[i]) for i in new_view_ids)
    check(not((current_views-old_views)-allowed_views),'An extra GLB buffer view has no enumerated sign/image owner')
    used_views={a.bufferView for a in g.accessors}|{im.bufferView for im in g.images}
    check(used_views==set(range(len(g.bufferViews))) and len(g.buffers)==1,'GLB acquired an unowned hidden buffer view or buffer')
    check(len(g.buffers)==1 and g.buffers[0].uri is None and not g.buffers[0].extensions and not g.buffers[0].extras and g.buffers[0].byteLength==len(g.binary_blob()),'GLB embedded-buffer storage semantics changed')
    native={c.key(b):b for b in read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')};materials={m['name']:m for m in manifest['materials']}
    for key in c.KEYS:
        name='__'.join(key);mesh=byname.get(name)
        if mesh is None or len(mesh.primitives)!=1:continue
        p=mesh.primitives[0];batch=native.get(key)
        if batch is None:check(False,'Added GLB key missing from native',mesh=name);continue
        arrays={k:access(g,v) for k,v in vars(p.attributes).items() if v is not None};faces=access(g,p.indices).reshape(-1,3)
        check(set(arrays)=={'POSITION','NORMAL','TEXCOORD_0','COLOR_0'},'Added GLB attribute inventory changed',mesh=name)
        if set(arrays)!={'POSITION','NORMAL','TEXCOORD_0','COLOR_0'}:continue
        expected=batch['vertices'][:,[0,2,1]].copy();expected[:,2]*=-1
        check(np.array_equal(arrays['POSITION'],expected) and np.array_equal(faces,batch['faces']),'Added GLB geometry/index does not match actual native',mesh=name)
        check(np.array_equal(arrays['COLOR_0'],batch['colors']),'Added GLB Color32 does not match actual native',mesh=name)
        uv=batch['uv']*materials[key[1]].get('uvScale',1);uv[:,1]=1-uv[:,1]
        check(np.allclose(arrays['TEXCOORD_0'],uv,rtol=0,atol=2e-6),'Added GLB UV differs from unchanged material scale/V convention',mesh=name)
        check(g.materials[p.material].name==key[1],'Added GLB material binding changed',mesh=name)
        normal=arrays['NORMAL'];check(np.isfinite(normal).all() and np.allclose(np.linalg.norm(normal,axis=1),1,rtol=0,atol=2e-5),'Added GLB normals are not finite unit vectors',mesh=name)
        position=g.accessors[p.attributes.POSITION]
        check(position.min==arrays['POSITION'].min(0).tolist() and position.max==arrays['POSITION'].max(0).tolist(),'Added GLB bounds do not match actual arrays',mesh=name)
    actual=c.sha(path.read_bytes())
    if strict:check(actual==c.load_oracle(root)['glbSha256'],'Editable GLB differs from exact independently approved artifact')
    return dict(status='FAIL' if errors else 'PASS',errors=errors,glbSha256=actual,preservedMeshes=len(prior),preservedAccessors=len(old['allAccessors']),preservedBufferViews=len(old['allBufferViews']),addedMeshes=len(new),nativeMaterialDefinitions=130,glbMaterialCount=len(g.materials),activatedExistingMaterials=list(ACTIVATED_MATERIALS),activatedExistingImages=[WOVEN_ARM_IMAGE],scope='All 1107 old position/normal/UV/Color32/index arrays, accessor bounds, identity node placement, material/texture semantics and scene placement exact; table indices may reorder. Exactly existing Noren1/Noren3 and their existing woven ARM texture become used. Only enumerated added meshes are admitted. Added native correspondence and unit normals checked; strict mode pins full GLB. No Unity/VRChat runtime claim.')
