"""Adversarial one-batch gate tests, including summary-only and shard reconstruction."""
import sys,json,copy,tempfile,hashlib,gzip
from pathlib import Path
from unittest.mock import patch
import numpy as np
import peer_culling_contract as peer
import city_roof_caps_contract as c
from city_roof_caps import FEATURE,KEY,selection
from city_roof_caps_test_fixture import restore_city_caps
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
D=ROOT/'Assets/TreeTopYokocho/Data';manifest=json.loads((D/'WorldManifest.json').read_text());batches=peer.read_visual(D/'VisualMeshes.bytes');rows=[peer.summarize(b) for b in batches];baseline=peer.load_baseline(ROOT);i=next(i for i,r in enumerate(rows) if (r['group'],r['material'])==KEY);pin=c.load_oracle(ROOT);n=0

current_manifest=copy.deepcopy(manifest);current_batches=batches
if manifest.get('features',{}).get('shop_personality') is True:
    from shop_personality_test_fixture import restore_prior_shops
    assert peer.validate_peer_culling(ROOT,current_manifest)[0];n+=1
    batches,manifest=restore_prior_shops(batches,manifest);rows=[peer.summarize(b) for b in batches];i=next(i for i,r in enumerate(rows) if (r['group'],r['material'])==KEY)

def expect(rs,m,want):
    global n
    n+=1;m=copy.deepcopy(m);m.update(visualMeshCount=len(rs),visualTriangles=sum(r['triangles'] for r in rs));ok,d=peer.validate_summaries(rs,m,baseline);assert ok==want,(n,d)
expect(rows,manifest,True)
for value in [False,None,0,1,1.0,'true','True',{},[],np.bool_(True)]:
    m=copy.deepcopy(manifest);m['features'][FEATURE]=value;expect(rows,m,False)
    before=copy.deepcopy(rows);before[i]=pin['before'];expect(before,m,True)
m=copy.deepcopy(manifest);m['features'].pop(FEATURE);expect(rows,m,False)
for field in c.FIELDS:
    rs=copy.deepcopy(rows);rs[i][field]=rs[i][field]+1 if isinstance(rs[i][field],int) else 'f'*64;expect(rs,manifest,False)
for mode in ['missing','duplicate','rename']:
    rs=copy.deepcopy(rows)
    if mode=='missing':rs.pop(i)
    elif mode=='duplicate':rs.append(rs[i])
    else:rs[i]['group']+='Far'
    expect(rs,manifest,False)
for field in ['meshOptimization','features','materials']:
    for value in [None,[],1,'true']:
        m=copy.deepcopy(manifest);m[field]=value;expect(rows,m,False)
for value in [None,[],1,'true',{}]:
    m=copy.deepcopy(manifest);m['meshOptimization']['cityCaps']=value;expect(rows,m,False)
for field in ['surfaceShaderSha256','builderSha256','fantasyProfileSha256','fantasyProfileLoaderSha256']:
    m=copy.deepcopy(manifest);m['meshOptimization']['cityCaps'][field]='0'*64;expect(rows,m,False)
for field,value in [('shader','Foliage'),('alphaClip',.1),('alphaMode','BLEND'),('doubleSided',True),('color',[1,1,1,0])]:
    m=copy.deepcopy(manifest);next(m for m in m['materials'] if m['name']=='DarkTimber')[field]=value;expect(rows,m,False)
# Native admission verifies actual dependency files, not metadata alone.
assert peer.validate_peer_culling(ROOT,current_manifest)[0];n+=1
original_read=Path.read_bytes
for suffix in ['YokochoSurface.shader','YokochoWorldBuilder.cs','FantasyMaterials.json','FantasyMaterialProfile.cs',c.ORACLE_NAME]:
    def altered(path,s=suffix):
        raw=original_read(path);return raw+b'\n// mutation' if str(path).endswith(s) else raw
    with patch.object(Path,'read_bytes',altered):assert not peer.validate_peer_culling(ROOT,current_manifest)[0];n+=1
# Reassembled actual descriptor-listed shards retain the same admission requirements.
from visual_transport import read_visual_transport
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'reassembled.bytes';raw=read_visual_transport(D);path.write_bytes(raw)
    assert peer.validate_peer_culling(ROOT,current_manifest,path)[0];n+=1
    m=copy.deepcopy(current_manifest);m['features'][FEATURE]=1;assert not peer.validate_peer_culling(ROOT,m,path)[0];n+=1
# Fail-closed source proof, independent of exact hash guard.
original,_=restore_city_caps(batches,manifest);b=next(b for b in original if (b['group'],b['material'])==KEY)
keep,mask,faces,clear=selection(b['vertices'],b['faces']);assert clear>.055 and len(keep)==26688;n+=1
for mode in ['cap','winding','topology']:
    v=b['vertices'].copy();f=b['faces'].copy()
    if mode=='cap':v[3*24+4:3*24+8,2]+=1
    elif mode=='winding':f[0]=f[0,::-1]
    else:f[1,0]=2
    try:selection(v,f)
    except ValueError:n+=1
    else:raise AssertionError('Source proof admitted '+mode)
# Generator pin and material checks run before export; float source colors are
# compared using the exact existing native Color32 packing convention.
from types import SimpleNamespace
from city_roof_caps import optimize
source={'v':b['vertices'].copy(),'f':b['faces'].copy(),'uv':b['uv'].copy(),'colors':b['colors'].astype(np.float32)/255}
g=SimpleNamespace(batches={KEY:copy.deepcopy(source)},materials={'DarkTimber':copy.deepcopy(pin['material'])})
optimize(g);assert len(g.batches[KEY]['f'])==13344;n+=1
for attr in ['v','uv','colors','f','material']:
    g=SimpleNamespace(batches={KEY:copy.deepcopy(source)},materials={'DarkTimber':copy.deepcopy(pin['material'])})
    if attr=='material':g.materials['DarkTimber']['shader']='Foliage'
    elif attr=='f':g.batches[KEY][attr][0,0]+=1
    else:g.batches[KEY][attr][0,0]+=.1
    try:optimize(g)
    except ValueError:n+=1
    else:raise AssertionError('Generator admitted '+attr)
report=dict(status='PASS',assertions=n,oneExactBatch=True,literalGate=True,originalOracleUnchanged=True,builderSha256=c.BUILDER_SHA256,scope='Source/native guards; no Unity compression, lighting or runtime execution')
(ROOT/'Docs/city_roof_caps_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
