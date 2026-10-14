"""Selected soft-snow revision, composed atop immutable adaptive11 pins.

Production admission only. No test-only inverse or array archive imports.
Compose AFTER legacy snow substitutions, INSTEAD of detail.compose_expected.
"""
import hashlib,json
from pathlib import Path
import mountain_detail_contract as detail
KEYS=detail.KEYS
FEATURE='mountain_snow_craft'
NORMAL_FEATURE='mountain_seam_normals'
ORACLE_NAME='mountain_quality_oracle_v2.json'
ORACLE_SHA256='94d1f0155b80538bbbe1d8ec64a0f87be716a471e7b63b9a17b9a9b54999e5dd'


def flags(features):
    adaptive,snow=detail.flags(features)
    for name in (FEATURE,NORMAL_FEATURE):
        if name in features and type(features[name]) is not bool:
            raise ValueError(name+' must be a literal Boolean')
    craft=features.get(FEATURE,False);normals=features.get(NORMAL_FEATURE,False)
    if craft and not (adaptive and snow):
        raise ValueError('Selected snow craft requires mountain_detail and snow_deposition')
    if normals and not adaptive:
        raise ValueError('Mountain seam normals require exact adaptive geometry')
    return adaptive,snow,craft,normals


def load_oracle():
    raw=(Path(__file__).resolve().parent/'testdata'/ORACLE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORACLE_SHA256:raise ValueError('Frozen selected mountain oracle changed')
    oracle=json.loads(raw)
    if oracle['geometryOracleSha256']!=detail.ORACLE_SHA256 or tuple(map(tuple,oracle['keys']))!=KEYS:
        raise ValueError('Selected mountain geometry provenance differs')
    rows=oracle['selected']
    if len(rows)!=12 or tuple((r['group'],r['material']) for r in rows)!=KEYS:
        raise ValueError('Selected mountain roster differs from exact twelve')
    old=detail.load_oracle()['variants']['after_snow'];changes=[]
    for a,b in zip(old,rows):
        for field in a:
            if field!='attributesAndIndicesSha256' and a[field]!=b[field]:
                raise ValueError('Snow craft cannot revise geometry or counts')
        if a['attributesAndIndicesSha256']!=b['attributesAndIndicesSha256']:
            changes.append((b['group'],b['material']))
    expected=[k for k in KEYS if k[1] in ('AlpineSnow','AlpineSnowShade')]
    if changes!=expected:raise ValueError('Soft snow must revise exactly eight snow colors')
    return oracle


def expected_records(features):
    _,_,craft,_=flags(features)
    if not craft:return detail.expected_records(features)
    return {(r['group'],r['material']):dict(r) for r in load_oracle()['selected']}


def compose_expected_records(expected,features):
    _,_,craft,_=flags(features)
    out=detail.compose_expected_records(expected,features)
    if not craft:return out
    adaptive=detail.expected_records(features)
    if any(out.get(k)!=v for k,v in adaptive.items()):
        raise ValueError('Selected snow expected-map composition order differs')
    out.update(expected_records(features));return out


def validate_native_mountains(batches,features):
    from peer_culling_contract import summarize
    adaptive,snow,craft,normals=flags(features);expected=expected_records(features);actual={};errors=[]
    for b in batches:
        key=(b['group'],b['material'])
        if not key[0].startswith('Landscape/SnowRange_'):continue
        if key in actual:errors.append('Duplicate mountain record: '+str(key))
        actual[key]=summarize(b)
    if set(actual)!=set(KEYS):errors.append('Mountain roster differs from exact twelve keys')
    for key in KEYS:
        if actual.get(key)!=expected[key]:errors.append('Unapproved selected mountain payload: '+str(key))
    return dict(passed=not errors,errors=errors,expectedBatches=12,mountainDetail=adaptive,snowDeposition=snow,mountainSnowCraft=craft,mountainSeamNormals=normals)
