"""Actual new printed surfaces: facing, UV glyph parity and lossless GLB pixels."""
import argparse
import io
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

PRINT_MATERIALS={'Food_Sign':'food_venue_signs.png','Night_Print':'nightlife_signs.png'}

def validate(root):
    from peer_culling_contract import read_visual
    from pygltflib import GLTF2
    import shop_personality_contract as contract
    data=root/'Assets/TreeTopYokocho/Data';m=json.loads((data/'WorldManifest.json').read_text());batches=read_visual(data/'VisualMeshes.bytes');checks=[];failures=[]
    def check(name,passed,detail=None):
        row=dict(name=name,passed=bool(passed))
        if detail is not None:row['detail']=detail
        checks.append(row)
        if not passed:failures.append(row)
    check('literal_shop_personality_gate',contract.enabled(m))
    rows=m.get('shopPersonality',{}).get('shops',[]);check('eight_shop_frames',len(rows)==8)
    for shop in rows:
        sid=shop['id'];right=np.asarray(shop['frame']['right']);front=np.asarray(shop['frame']['front']);selected=[b for b in batches if b['group'].startswith('Shops/'+sid+'/Personality/') and b['material'] in PRINT_MATERIALS]
        front_triangles=0;wrong=[]
        for b in selected:
            vertices=b['vertices'].astype(float);q=vertices[b['faces']];n=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);length=np.linalg.norm(n,axis=1);mask=(n@front)>.99*length;mask &=length>1e-10
            # Closed shaped boards can also carry back/edge faces. Test every
            # actual guest-facing printed triangle, never an invented quad.
            for index in np.flatnonzero(mask):
                tri=q[index];uv=b['uv'][b['faces'][index]].astype(float);xy=np.column_stack([tri@right,tri[:,2],np.ones(3)])
                if abs(np.linalg.det(xy))<1e-12:continue
                gradients=np.linalg.solve(xy,uv);du_dx,du_dz=gradients[0,0],gradients[1,0];dv_dx,dv_dz=gradients[0,1],gradients[1,1];front_triangles+=1
                if not (du_dx<-1e-7 and dv_dz>1e-7 and abs(du_dz)<max(abs(du_dx)*.002,2e-5) and abs(dv_dx)<max(abs(dv_dz)*.002,2e-5)):
                    wrong.append(dict(group=b['group'],triangle=int(index),gradients=gradients[:2].tolist()))
        check(sid+'_printed_front_surface_present',bool(selected) and front_triangles>0,dict(batches=len(selected),guestFacingTriangles=front_triangles))
        check(sid+'_actual_glyph_horizontal_vertical_parity',not wrong,wrong)
    material_by_name={r['name']:r for r in m['materials']}
    gl=GLTF2().load(str(root/'Source/TreeTopYokocho.glb'));blob=gl.binary_blob();gl_m={mat.name:mat for mat in gl.materials}
    for name,texture in PRINT_MATERIALS.items():
        descriptor=material_by_name.get(name,{});check(name+'_owned_atlas_descriptor',descriptor.get('texture')==texture)
        mat=gl_m.get(name);ref=mat.pbrMetallicRoughness.baseColorTexture if mat is not None else None
        check(name+'_actual_glb_texture_present',ref is not None)
        if ref is None:continue
        im=gl.images[gl.textures[ref.index].source];view=gl.bufferViews[im.bufferView];raw=blob[(view.byteOffset or 0):(view.byteOffset or 0)+view.byteLength]
        decoded=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'));source=np.asarray(Image.open(root/'Assets/TreeTopYokocho/Textures'/texture).convert('RGBA'))
        check(name+'_explicit_png_lossless_encoding',im.mimeType=='image/png',dict(mimeType=im.mimeType,bytes=len(raw)))
        check(name+'_lossless_glb_pixels_equal_authored_atlas',decoded.shape==source.shape and np.array_equal(decoded,source),dict(decodedShape=list(decoded.shape),sourceShape=list(source.shape)))
    return dict(status='FAIL' if failures else 'PASS',version=m['version'],checks=checks,failures=failures,scope='Actual current shop print-material front triangles and UV parity; exact decoded PNG pixels in editable GLB. Japanese wording, composition and legibility need visual inspection. No Unity compression/runtime claim.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();sys.path.append(str(args.root/'Source'));result=validate(args.root);args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));return result['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
