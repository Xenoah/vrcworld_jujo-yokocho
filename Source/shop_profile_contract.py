"""One exact additive material-profile revision; original routing stays exact."""
import copy
import hashlib
import json
from pathlib import Path

OLD_PROFILE_SHA256='6cf7669a43f2b45678057f22fcf344cc753b9b65b350e0c6b13700e3131f3c8e'
PROFILE_SHA256='9986ae06f773d436a175ec47c6af1e627082352fd59634014e59c72e29351cd2'
FIXTURE_NAME='shop_profile_additions_2_16.json'
FIXTURE_SHA256='d9b751664d079dd6ddbd82e15faa4f5fd61250ac0dacdfae246df7384df1b928'
BASELINE_CANONICAL_SHA256='2f05bbc23b604170170cb4401d57ebcc3db418909263592faeb6564fcb9c5ade'
NAMES=('Food_Paper','Food_Enamel','Food_TileCream','Food_TileGreen','Food_Upholstery','Night_WineUpholstery','Night_IndigoUpholstery','Night_SmokyGlass')

def load_fixture(root=None):
    source=Path(root)/'Source' if root else Path(__file__).resolve().parent
    raw=(source/'testdata'/FIXTURE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FIXTURE_SHA256:raise ValueError('Exact additive shop-profile fixture changed')
    result=json.loads(raw)
    if result['baselineCanonicalSHA256']!=BASELINE_CANONICAL_SHA256 or [n for g in result['additions'] for n in g['names']]!=list(NAMES):raise ValueError('Invalid additive profile roster')
    return result

def authenticate_profile(profile,root=None):
    fixture=load_fixture(root);before=copy.deepcopy(profile);groups=before.get('materialGroups',[]);n=len(fixture['additions'])
    if groups[-n:]!=fixture['additions']:raise ValueError('Exact approved additive shop material groups changed')
    before['materialGroups']=groups[:-n]
    if hashlib.sha256(json.dumps(before,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=BASELINE_CANONICAL_SHA256:raise ValueError('Original/global material routing changed under shop profile')
    return before

def verify_profile(root):
    raw=(Path(root)/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROFILE_SHA256:raise ValueError('Exact reviewed shop material profile changed')
    authenticate_profile(json.loads(raw),root=root)
    return PROFILE_SHA256
