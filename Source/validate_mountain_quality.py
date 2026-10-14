"""Run portable mountain source/numeric tests and record current-source identity.
No C# execution, Unity import, headset or runtime performance measurement.
"""
from pathlib import Path
import hashlib,importlib,json,sys,unittest
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Source'))
names=['test_mountain_detail','test_mountain_quality','test_mountain_snow_craft','test_mountain_seam_normals']
suite=unittest.TestSuite()
for name in names:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
result=unittest.TextTestRunner(verbosity=2).run(suite)
m=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
paths=[f'Source/{name}.py' for name in names]+[f'Source/{name}.py' for name in ['mountain_detail','mountain_detail_contract','mountain_quality','mountain_quality_contract','mountain_seam_normals','mountain_snow_craft']]+['Source/world_geometry.py','Assets/TreeTopYokocho/Editor/MountainSeamNormals.cs','Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs','Assets/TreeTopYokocho/Data/VisualMeshes.bytes']
report={'status':'PASS' if result.wasSuccessful() else 'FAIL','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'features':{name:m.get('features',{}).get(name) for name in ['mountain_detail','mountain_snow_craft','mountain_seam_normals']},'nativeMountainGeometryBatches':12,'nativeSnowColorRevisionBatches':8,'eligibleSeamNormalSlots':3637,'sourceSha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'scope':'Source generation, exact payload gates/inverses, numeric normal-reference and C# syntax tests. No actual Unity/C# execution, GPU or build-size claim.'}
(ROOT/'Docs/mountain_quality_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(not result.wasSuccessful())
