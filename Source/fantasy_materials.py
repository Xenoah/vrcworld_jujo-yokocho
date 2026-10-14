"""Strict editor-profile validation and material routing, no geometry mutation.
Blender approximations may share profile inputs, but cannot validate Unity output.
"""
from pathlib import Path
import json,math

PROFILE_RELATIVE=Path('Assets/TreeTopYokocho/Data/FantasyMaterials.json')
SHADERS={'Surface','Cloth','LanternPaper','Water','Glaze'}
KEYWORDS={'_YOKOCHO_CRAFT','_YOKOCHO_FANTASY_SKY'}

def _settings(settings):
    if not isinstance(settings,dict):raise ValueError('Missing fantasy settings')
    seen=set()
    for field in ('floats','vectors','keywords'):
        if not isinstance(settings.get(field,[]),list):raise ValueError('Fantasy '+field+' must be an array')
    for entry in settings.get('floats',[]):
        if not isinstance(entry,dict):raise ValueError('Invalid fantasy float entry')
        name=entry.get('name');value=entry.get('value')
        if not isinstance(name,str) or not name or name in seen or type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Invalid or duplicate fantasy float')
        seen.add(name)
    for entry in settings.get('vectors',[]):
        if not isinstance(entry,dict):raise ValueError('Invalid fantasy vector entry')
        name=entry.get('name');value=entry.get('value')
        if not isinstance(name,str) or not name or name in seen or not isinstance(value,list) or len(value)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):
            raise ValueError('Invalid or duplicate fantasy vector')
        seen.add(name)
    keywords=settings.get('keywords',[])
    if any(not isinstance(value,str) for value in keywords):raise ValueError('Invalid fantasy keyword entry')
    if len(keywords)!=len(set(keywords)) or not set(keywords)<=KEYWORDS:raise ValueError('Unknown or duplicate fantasy keyword')

def validate_profile(profile, materials):
    if not isinstance(profile,dict) or type(profile.get('schema')) is not int or profile['schema']!=1:
        raise ValueError('Unsupported fantasy profile schema')
    groups=profile.get('materialGroups')
    if not isinstance(groups,list) or not groups:raise ValueError('Missing fantasy material groups')
    known={m['name'] for m in materials};seen=set()
    for group in groups:
        if not isinstance(group,dict) or not isinstance(group.get('shader'),str) or group['shader'] not in SHADERS:raise ValueError('Invalid fantasy shader group')
        names=group.get('names')
        if not isinstance(names,list) or not names:raise ValueError('Missing fantasy material names')
        _settings(group)
        if 'textureKeywords' in group and type(group['textureKeywords']) is not bool:raise ValueError('textureKeywords must be literal boolean')
        for name in names:
            if not isinstance(name,str) or name not in known or name in seen:raise ValueError('Unknown or duplicate fantasy material: '+str(name))
            seen.add(name)
    _settings(profile.get('sky'))
    return profile

def load_profile(root, materials):
    return validate_profile(json.loads((Path(root)/PROFILE_RELATIVE).read_text()),materials)

def groups_by_name(profile):
    return {name:group for group in profile['materialGroups'] for name in group['names']}

def float_values(settings):return {entry['name']:entry['value'] for entry in settings.get('floats',[])}
def vector_values(settings):return {entry['name']:entry['value'] for entry in settings.get('vectors',[])}
