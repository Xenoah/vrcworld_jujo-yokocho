"""Independent before/after GLB semantic preservation on exact 815 nonshop keys."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np


def access(g,index):
    a=g.accessors[index];v=g.bufferViews[a.bufferView];d={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a.componentType];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a.type];size=np.dtype(d).itemsize*n
    if v.byteStride not in (None,0,size):raise ValueError('Unexpected GLB interleave')
    return np.frombuffer(g.binary_blob(),d,count=a.count*n,offset=(v.byteOffset or 0)+(a.byteOffset or 0)).reshape(a.count,n)

def image_fingerprints(gl):
    blob=gl.binary_blob();result=[]
    for im in gl.images:
        v=gl.bufferViews[im.bufferView];raw=blob[(v.byteOffset or 0):(v.byteOffset or 0)+v.byteLength];result.append(dict(mimeType=im.mimeType,sha256=hashlib.sha256(raw).hexdigest()))
    return result

def semantic_material(gl,material):
    value=json.loads(material.to_json());images=image_fingerprints(gl)
    def walk(obj,key=None):
        if isinstance(obj,dict):
            if key and (key.endswith('Texture') or key=='occlusionTexture') and 'index' in obj:
                t=gl.textures[obj['index']];obj=dict(obj);obj['image']=images[t.source];obj['sampler']=json.loads(gl.samplers[t.sampler].to_json()) if t.sampler is not None else None;del obj['index']
            return {k:walk(v,k) for k,v in obj.items()}
        if isinstance(obj,list):return [walk(v) for v in obj]
        return obj
    return walk(value)



def identity_scene_errors(gl,label):
    """Authenticate the frozen exporter's one identity leaf node per mesh."""
    errors=[];names=[m.name for m in gl.meshes]
    def fail(reason,**detail):errors.append(dict(reason=reason,artifact=label,**detail))
    if any(not isinstance(n,str) or not n for n in names) or len(names)!=len(set(names)):fail('GLB mesh names must be unique nonempty strings')
    material_names=[m.name for m in gl.materials]
    if any(not isinstance(n,str) or not n for n in material_names) or len(material_names)!=len(set(material_names)):fail('GLB material names must be unique nonempty strings')
    if gl.scene!=0 or len(gl.scenes)!=1:fail('GLB must retain its single selected scene')
    elif gl.scenes[0].nodes!=list(range(len(gl.nodes))):fail('GLB scene must include every identity node exactly once in export order')
    if len(gl.nodes)!=len(gl.meshes):fail('GLB must retain exactly one node per mesh')
    for index,node in enumerate(gl.nodes):
        if (index>=len(gl.meshes) or node.mesh!=index or node.name!=names[index] or node.children or node.matrix is not None
            or node.translation is not None or node.rotation is not None or node.scale is not None or node.skin is not None
            or node.camera is not None or node.extensions or node.extras):fail('GLB identity node placement/mesh binding changed',node=index)
    for index,mesh in enumerate(gl.meshes):
        if len(mesh.primitives)!=1 or mesh.weights or mesh.extensions or mesh.extras:fail('GLB static mesh export structure changed',mesh=index)
        for primitive in mesh.primitives:
            if primitive.mode!=4 or primitive.targets or primitive.extensions or primitive.extras:fail('GLB primitive must remain static unextended triangles',mesh=index)
    if gl.animations or gl.skins or gl.extensions or gl.extensionsRequired or gl.extensionsUsed:fail('GLB acquired unreviewed animation/skin/extension semantics')
    return errors

def audit_frozen(root):
    """Portable whole-artifact admission, independent of the large old GLB."""
    import shop_personality_contract as c
    errors=[];manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    import rpg_identity_contract as rpg
    if rpg.requested(manifest):
        from audit_rpg_identity_glb import audit as rpg_audit
        return rpg_audit(root,manifest,strict=True)
    errors.extend(c.validate_gate(manifest))
    if not c.enabled(manifest):errors.append(dict(reason='Frozen redesigned GLB requires literal shop personality feature'))
    if errors:return dict(status='FAIL',errors=errors,scope='Exact separately approved editable GLB bytes; not native-only runtime admission.')
    oracle=c.load_oracle(root);expected=oracle.get('approvedGlbSha256')
    actual=hashlib.sha256((root/'Source/TreeTopYokocho.glb').read_bytes()).hexdigest()
    if not isinstance(expected,str) or len(expected)!=64 or actual!=expected:errors.append(dict(reason='Editable GLB is not the exact visually approved artifact',expected=expected,actual=actual))
    return dict(status='FAIL' if errors else 'PASS',errors=errors,approvedGlbSha256=expected,actualGlbSha256=actual,
                scope='Whole editable GLB byte pin from independently accepted art. No old GLB or native-only runtime dependency.')

def audit(before_root,after_root):
    from pygltflib import GLTF2
    import shop_personality_contract as c
    pin=c.load_before();before_path=before_root/'Source/TreeTopYokocho.glb';after_path=after_root/'Source/TreeTopYokocho.glb'
    if hashlib.sha256(before_path.read_bytes()).hexdigest()!=pin['glbSha256']:raise ValueError('Not the independently pinned baseline GLB')
    old=GLTF2().load(str(before_path));new=GLTF2().load(str(after_path));ob={m.name:m for m in old.meshes};nb={m.name:m for m in new.meshes};old_keys=set(map(tuple,pin['shopKeys']));rows=[r for r in pin['rows'] if c.key(r) not in old_keys];errors=identity_scene_errors(old,'baseline')+identity_scene_errors(new,'current');used_materials=set();checked=0
    for row in rows:
        name='__'.join(c.key(row));a=ob.get(name);b=nb.get(name)
        if a is None or b is None:errors.append(dict(reason='Nonshop GLB mesh missing',name=name));continue
        if len(a.primitives)!=1 or len(b.primitives)!=1:errors.append(dict(reason='Unexpected nonshop primitive count',name=name));continue
        p=a.primitives[0];q=b.primitives[0]
        for attr in ('POSITION','NORMAL','TEXCOORD_0','COLOR_0','TANGENT'):
            i=getattr(p.attributes,attr,None);j=getattr(q.attributes,attr,None)
            if (i is None)!=(j is None) or (i is not None and (old.accessors[i].componentType!=new.accessors[j].componentType or old.accessors[i].normalized!=new.accessors[j].normalized or not np.array_equal(access(old,i),access(new,j)))):errors.append(dict(reason='Nonshop GLB accessor changed',name=name,attribute=attr))
        if not np.array_equal(access(old,p.indices),access(new,q.indices)):errors.append(dict(reason='Nonshop GLB indices changed',name=name))
        if old.materials[p.material].name!=new.materials[q.material].name:errors.append(dict(reason='Nonshop GLB material binding changed',name=name))
        used_materials.add(old.materials[p.material].name);checked+=1
    old_m={m.name:m for m in old.materials};new_m={m.name:m for m in new.materials}
    for name in sorted(used_materials):
        if name not in new_m or semantic_material(old,old_m[name])!=semantic_material(new,new_m[name]):errors.append(dict(reason='Nonshop GLB material/embedded texture semantics changed',material=name))
    return dict(status='FAIL' if errors else 'PASS',errors=errors,comparedNonshopMeshes=checked,exactNonshopMeshes=checked if not errors else None,requiredNonshopMeshes=815,materialBindingsChecked=len(used_materials),beforeGlbSha256=pin['glbSha256'],afterGlbSha256=hashlib.sha256(after_path.read_bytes()).hexdigest(),scope='Exact unique static triangle-mesh roster, single selected identity-leaf scene placement, and nonshop GLB position/normal/UV/Color32/tangent/index arrays and resolved material/embedded image bytes. Material numeric table indexes may differ but bindings and semantics may not. No Unity runtime claim.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path);p.add_argument('--after',type=Path,required=True);p.add_argument('--strict',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args();sys.path.append(str(a.after/'Source'))
    if a.before is None and not a.strict:p.error('Use --before for independent preservation or --strict for portable frozen-artifact admission')
    r=audit(a.before,a.after) if a.before is not None else audit_frozen(a.after)
    if a.strict and a.before is not None:
        frozen=audit_frozen(a.after);r['frozenGlbAdmission']=frozen;r['errors'].extend(frozen['errors'])
        if frozen['status']!='PASS':r['status']='FAIL'
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));return r['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
