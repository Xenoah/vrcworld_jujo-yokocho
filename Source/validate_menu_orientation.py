"""Check exported rear menus face guests and their lettering is not mirrored."""
from pathlib import Path
import argparse,json,math
import numpy as np
from validate_foliage_runtime_source import source_meshes


def validate(root):
    manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    if manifest.get('features',{}).get('shop_personality') is True:
        from validate_shop_personality_signs import validate as revised_signs
        return revised_signs(root)
    layout=json.loads((root/'Source/layout.reference.json').read_text())['shops']
    meshes={(group,material):(v,uv,f) for group,material,v,uv,f in source_meshes(root/'Assets/TreeTopYokocho/Data')}
    checks=[]
    for idx,shop in enumerate(layout):
        vertices,uv,faces=meshes[('Shops/'+shop['id'],'MenuAtlas')]
        a=math.radians(shop['front_deg']);normal=np.array([math.cos(a),math.sin(a),0]);right=np.array([normal[1],-normal[0],0])
        x=vertices@right;z=vertices[:,2]
        q=vertices[faces];normals=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
        expected_u0=(idx%4)/4;expected_u1=expected_u0+.25
        expected_v1=1-(idx//4)*.375;expected_v0=expected_v1-.375
        # Local +X points toward the viewer's left, so U must decrease with X.
        wanted_u=np.where(x>(x.min()+x.max())*.5,expected_u0,expected_u1)
        wanted_v=np.where(z>(z.min()+z.max())*.5,expected_v1,expected_v0)
        results=dict(single_front_quad=len(vertices)==4 and len(faces)==2,
                     outward_to_guest=bool(np.all(normals@normal>1e-6)),
                     horizontal_glyph_parity=bool(np.allclose(uv[:,0],wanted_u,rtol=0,atol=1e-7)),
                     vertical_glyph_parity=bool(np.allclose(uv[:,1],wanted_v,rtol=0,atol=1e-7)))
        checks.append(dict(shop=shop['id'],passed=all(results.values()),checks=results,triangles=len(faces)))
    return dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,
                scope='Actual exported menu triangles, one front-facing surface and atlas orientation only. Text layout and readability are also inspected in Blender; no Unity execution.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',type=Path,default=Path(__file__).resolve().parent.parent);parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=validate(args.root);(args.output or args.root/'Docs/menu_orientation_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')
