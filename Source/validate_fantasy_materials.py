"""Run fantasy profile/shader source guards and report actual material routing.
No Unity shader compilation, lighting bake or VR performance measurement occurs.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,unittest
from collections import Counter
from fantasy_materials import load_profile,groups_by_name,PROFILE_RELATIVE
from peer_culling_contract import read_visual

def main(root):
    root=root.resolve();manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    if manifest.get('features',{}).get('fantasy_materials') is not True:
        raise ValueError('Fantasy validator requires literal enabled feature, not an inferred profile')
    profile=load_profile(root,manifest['materials']);groups=groups_by_name(profile)
    suite=unittest.TestSuite()
    paths=['Tests/test_foliage_preview_hook.py','Source/test_fantasy_materials.py','Tests/test_fantasy_shader_contract.py','Tests/test_fantasy_math.py','Tests/test_warped_water.py','Tests/test_aurora_bounds.py','Tests/test_cloth_material_use.py','Tests/test_atlas_weave_revision.py','Tests/test_temporal_glare.py','Source/test_surface_craft_formula.py']
    for index,rel in enumerate(paths):
        spec=importlib.util.spec_from_file_location('fantasy_guard_'+str(index),root/rel)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    batches=read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
    count=Counter(b['material'] for b in batches);triangles=Counter()
    for b in batches:triangles[b['material']]+=len(b['faces'])
    rows=[]
    for m in manifest['materials']:
        group=groups.get(m['name']);shader=group['shader'] if group else m.get('shader','Surface')
        rows.append({'material':m['name'],'shader':shader,'overridden':group is not None,
                     'visualBatches':count[m['name']],'visualTriangles':triangles[m['name']]})
    hashes={rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in paths+[
        str(PROFILE_RELATIVE),'Source/fantasy_materials.py',
        'Assets/TreeTopYokocho/Editor/FantasyMaterialProfile.cs','Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs',
        'Assets/TreeTopYokocho/Data/WorldManifest.json']}
    for path in sorted((root/'Assets/TreeTopYokocho/Shaders').glob('*.shader')):
        hashes[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    report={'status':'PASS' if result.wasSuccessful() else 'FAIL','testsRun':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'sourceVersion':manifest['version'],
        'shaderAssetCount':len(list((root/'Assets/TreeTopYokocho/Shaders').glob('*.shader'))),
        'materialRouting':rows,'sourceSha256':hashes,'unityShaderCompilation':False,
        'scope':'Source/numeric tests and actual mesh material roster. No Unity compilation, bake, stereo or GPU performance claim.'}
    (root/'Docs/fantasy_material_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('materialRouting','sourceSha256')},indent=2))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    raise SystemExit(main(a.root))
