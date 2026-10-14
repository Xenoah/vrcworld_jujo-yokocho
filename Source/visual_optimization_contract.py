"""Narrow immutable optimization admission, preserving all older contracts.

Exact reviewed after payloads are admitted before prior summary fields are
restored for older baseline checks. This is NOT a family/prefix exemption.
Original noren Identity payloads and component slices are never normalized.
"""
import hashlib,json
from pathlib import Path
from collections import Counter

ORACLE_NAME='visual_optimization_2_15.json'
ORACLE_SHA256='22e46e78c068bfcc89a766f502e9754839b55cd0c473d5a84b1eb87fe9a0c8a8'
FEATURES=('visual_unused_compaction','static_planar_sea')
STATIC_SEA_SHADER_SHA256='a6f80b12ed3ac8c4e147d4f25a3bd659488600b018cfd273880942f5d5289e6b'

def verified_static_sea_shader(root):
    path=Path(root)/'Assets/TreeTopYokocho/Shaders/YokochoWater.shader'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=STATIC_SEA_SHADER_SHA256:raise ValueError('Static planar sea requires reviewed non-displacing Water shader')
    return digest

FIELDS=('vertices','triangles','geometrySha256','attributesAndIndicesSha256')
SEA_KEYS=tuple(('Landscape/Sea_'+str(i),'Lake') for i in range(4))

def requested(manifest):
    f=manifest.get('features',{})
    return isinstance(f,dict) and any(k in f for k in FEATURES)

def load_oracle(root=None):
    base=Path(root)/'Source' if root is not None else Path(__file__).resolve().parent
    raw=(base/'testdata'/ORACLE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORACLE_SHA256:raise ValueError('Frozen visual optimization oracle hash changed')
    oracle=json.loads(raw);rows=oracle['changes'];keys=[(r['before']['group'],r['before']['material']) for r in rows]
    if len(rows)!=132 or len(set(keys))!=132:raise ValueError('Invalid exact optimization roster')
    if any('/Identity' in k[0] for k in keys):raise ValueError('Identity optimization is not admitted')
    if {keys[i] for i,r in enumerate(rows) if r['kind']=='static-planar-sea'}!=set(SEA_KEYS):raise ValueError('Invalid sea optimization roster')
    if sum(r['before']['vertices']-r['after']['vertices'] for r in rows)!=48039:raise ValueError('Invalid optimization vertex accounting')
    return oracle

def normalize_summaries(summaries,manifest):
    if not requested(manifest):return summaries,manifest,[],None
    oracle=load_oracle();rows=oracle['changes'];features=manifest['features'];errors=[]
    enabled={name:features.get(name) is True for name in FEATURES}
    if enabled['static_planar_sea']:
        metadata=manifest.get('meshOptimization',{})
        metadata=metadata.get('sea',{}) if isinstance(metadata,dict) else {}
        if not isinstance(metadata,dict):metadata={}
        if metadata.get('waterShaderSha256')!=STATIC_SEA_SHADER_SHA256:
            errors.append(dict(reason='Static planar sea shader profile mismatch'))
    counts=Counter((r['group'],r['material']) for r in summaries)
    lookup={(r['before']['group'],r['before']['material']):r for r in rows}
    for k in lookup:
        if counts[k]!=1:errors.append(dict(reason='Optimization batch missing or duplicated',batch=k))
    for field,value in [('visualMeshCount',len(summaries)),('visualTriangles',sum(r['triangles'] for r in summaries))]:
        if manifest.get(field)!=value:errors.append(dict(reason='Manifest export count mismatch',field=field,expected=value,actual=manifest.get(field)))
    output=[];matched=0
    for summary in summaries:
        key=(summary['group'],summary['material']);row=lookup.get(key)
        if row is None:output.append(summary);continue
        flag=FEATURES[1] if row['kind']=='static-planar-sea' else FEATURES[0]
        expected=row['after'] if enabled[flag] else row['before']
        if any(summary.get(f)!=expected[f] for f in FIELDS):
            errors.append(dict(reason='Exact visual optimization payload mismatch',batch=key,feature=flag,enabled=enabled[flag]))
            output.append(summary);continue
        if enabled[flag]:
            normalized=dict(summary);normalized.update({f:row['before'][f] for f in FIELDS});output.append(normalized);matched+=1
        else:output.append(summary)
    adjusted=dict(manifest);adjusted['visualTriangles']=sum(r['triangles'] for r in output)
    return output,adjusted,errors,dict(oracleSha256=ORACLE_SHA256,enabled=enabled,exactAdmittedBatches=matched,originalIdentitySlicesRemainUnmodified=True)
