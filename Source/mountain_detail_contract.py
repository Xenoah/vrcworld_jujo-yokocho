"""Exact, separately gated 12-record mountain admission. No inverse fixtures.

The caller must compose this AFTER the older eight snow-color substitutions.
This module never changes the v2.8 peer baseline or any optimization pin.
"""
import hashlib,json
from pathlib import Path

FEATURE='mountain_detail'
ORACLE_NAME='mountain_detail_oracle_v1.json'
ORACLE_SHA256='9b07dd45205c0a6c0f262dd75fa809fa6a5c0a4f02d39a34d8b2ceb23e923280'
KEYS=tuple(('Landscape/SnowRange_%d'%i,m) for i in range(4) for m in ('AlpineRock','AlpineSnow','AlpineSnowShade'))


def load_oracle():
    raw=(Path(__file__).resolve().parent/'testdata'/ORACLE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORACLE_SHA256:raise ValueError('Frozen mountain oracle changed')
    oracle=json.loads(raw)
    if tuple(map(tuple,oracle['keys']))!=KEYS:raise ValueError('Invalid exact mountain roster')
    for records in oracle['variants'].values():
        if len(records)!=12 or tuple((r['group'],r['material']) for r in records)!=KEYS:
            raise ValueError('Invalid mountain variant schema')
    return oracle


def flags(features):
    if not isinstance(features,dict):raise ValueError('Feature manifest must be an object')
    for name in (FEATURE,'snow_deposition'):
        if name in features and type(features[name]) is not bool:raise ValueError(name+' must be a literal Boolean')
    return features.get(FEATURE,False),features.get('snow_deposition',False)


def expected_records(features):
    detail,snow=flags(features);variant=('after' if detail else 'before')+('_snow' if snow else '_plain')
    return {(r['group'],r['material']):r for r in load_oracle()['variants'][variant]}


def compose_expected_records(expected,features):
    """Return a copied expected map, replacing exactly twelve gated records.

    Exact pre-pass records must already match the applicable old snow variant.
    This guards ordering errors and prevents this feature from approving a
    previously unapproved payload through an unrelated contract substitution.
    """
    detail,snow=flags(features)
    if not detail:return dict(expected)
    oracle=load_oracle();before=oracle['variants']['before_snow' if snow else 'before_plain']
    if any({field:expected.get(k,{}).get(field) for field in r}!=r for k,r in zip(KEYS,before)):
        raise ValueError('Mountain expectation is not exact approved pre-pass payload')
    out=dict(expected)
    for key,record in expected_records(features).items():
        out[key]=dict(record)
    return out


def validate_native_mountains(batches,features):
    # Imported inside function, avoiding a peer <-> mountain import cycle.
    from peer_culling_contract import summarize
    expected=expected_records(features);actual={};errors=[]
    for b in batches:
        key=(b['group'],b['material'])
        if not key[0].startswith('Landscape/SnowRange_'):continue
        if key in actual:errors.append('Duplicate mountain record: '+str(key))
        actual[key]=summarize(b)
    if set(actual)!=set(KEYS):errors.append('Mountain roster differs from exact twelve keys')
    for key in KEYS:
        if actual.get(key)!=expected[key]:errors.append('Unapproved mountain payload: '+str(key))
    return {'passed':not errors,'errors':errors,'expectedBatches':12,'mountainDetail':flags(features)[0],'snowDeposition':flags(features)[1]}
