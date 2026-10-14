"""Versioned, venue-owned fixture lighting. No geometry/RNG/physics changes.

The profile stores authored Unity Color API RGB. Cycles uses the same numeric
palette but its live watts are only an art preview, never a Unity bake surrogate.
Only exact semantic batch keys are remapped, never inferred from coordinates.
"""
from pathlib import Path
import copy
import hashlib
import json
import math

PROFILE_RELATIVE = Path('Assets/TreeTopYokocho/Data/VenueLighting.json')
FEATURE = 'venue_lighting_identity'
SCHEMA = 1
VERSION = 'venue-lighting-1'
SHOP_IDS = tuple(f'S{i:02d}' for i in range(1, 9))
FIXTURE_COUNTS = (2, 2, 2, 1, 2, 2, 2, 2)
ROLES = {'key', 'task', 'accent'}


def finite(value, label, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid venue lighting ' + label)
    return value


def vector(value, label, low=-1e4, high=1e4):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('Invalid venue lighting vector: ' + label)
    for component in value:
        finite(component, label, low, high)
    return value


def luminance(color):
    """Bounded RGB-weighted budget proxy, NOT lux, spectral CRI or radiance."""
    return sum(a*b for a, b in zip(color, (.2126, .7152, .0722)))


def feature_enabled(features):
    if FEATURE in features and type(features[FEATURE]) is not bool:
        raise ValueError(FEATURE + ' must be a literal Boolean')
    enabled = features.get(FEATURE) is True
    if enabled and features.get('shop_personality') is not True:
        raise ValueError('Venue lighting requires the reviewed shop personality source')
    return enabled


def validate_profile(profile):
    if not isinstance(profile, dict) or type(profile.get('schema')) is not int or profile['schema'] != SCHEMA:
        raise ValueError('Unsupported venue lighting schema')
    if profile.get('version') != VERSION or profile.get('feature') != FEATURE:
        raise ValueError('Unsupported venue lighting profile version/feature')
    # Legacy defaults are a contract, not tuning controls for non-shop lighting.
    for key, expected in [('legacyUnityColor', [1, .52, .18]), ('legacyPreviewColor', [1, .48, .16]),
                          ('unityBaseIntensity', 1.65), ('previewBaseEnergy', 110),
                          ('rangeMultiplier', 1.25), ('bounceIntensity', 1.6)]:
        if profile.get(key) != expected:
            raise ValueError('Legacy non-venue light behavior cannot be changed: ' + key)
    shops = profile.get('shops')
    if not isinstance(shops, list) or [s.get('id') for s in shops if isinstance(s, dict)] != list(SHOP_IDS):
        raise ValueError('Expected exact ordered eight-venue lighting roster')
    indices = []; names = set(); keys = set()
    for shop, count in zip(shops, FIXTURE_COUNTS):
        sid = shop['id']; fixtures = shop.get('fixtures'); emitters = shop.get('emitters')
        if not isinstance(fixtures, list) or len(fixtures) != count:
            raise ValueError('Existing fixture count changed: ' + sid)
        if not isinstance(emitters, list) or not emitters:
            raise ValueError('Missing explicit emitter bindings: ' + sid)
        ids = set()
        for j, fixture in enumerate(fixtures):
            if fixture.get('id') != f'{sid}_F{j+1:02d}' or fixture.get('role') not in ROLES:
                raise ValueError('Invalid fixture identity/role: ' + sid)
            ids.add(fixture['id'])
            index = fixture.get('manifestIndex')
            if type(index) is not int:
                raise ValueError('Fixture index must be integer')
            indices.append(index)
            vector(fixture.get('localPosition'), 'local fixture position')
            vector(fixture.get('worldPosition'), 'world fixture position')
            finite(fixture.get('range'), 'range', .1, 12)
            finite(fixture.get('strength'), 'strength', .1, 3)
            color = vector(fixture.get('color'), 'fixture RGB', 0, 1)
            if max(color) != 1 or min(color) < .10:
                raise ValueError('Fixture RGB must be bounded, normalized and not spectral-primary-only')
            finite(fixture.get('intensityMultiplier'), 'intensity multiplier', .5, 1.15)
            if fixture['role'] in ('key', 'task') and min(color) < .68:
                raise ValueError('Readable key/task light requires a neutral-ish RGB floor')
        if not any(f['role'] in ('key', 'task') for f in fixtures):
            raise ValueError('Every venue needs an existing readable key/task light')
        old = sum(f['strength'] for f in fixtures) * luminance(profile['legacyUnityColor'])
        new = sum(f['strength']*f['intensityMultiplier']*luminance(f['color']) for f in fixtures)
        if not .80 <= new / old <= 1.28:
            raise ValueError('Venue weighted RGB/intensity budget exceeded: ' + sid)
        for binding in emitters:
            key = (binding.get('group'), binding.get('sourceMaterial'))
            if not isinstance(key[0], str) or not key[0].startswith('Shops/' + sid + '/Personality/') or key in keys:
                raise ValueError('Unowned/duplicate emitter binding: ' + sid)
            keys.add(key)
            name = binding.get('material')
            if not isinstance(name, str) or not name.startswith('VenueLight_' + sid + '_') or name in names:
                raise ValueError('Unowned/duplicate emitter material: ' + sid)
            names.add(name)
            if binding.get('sourceMaterial') not in ('Food_Paper', 'RedLantern', 'WarmWindow', 'Ceramic'):
                raise ValueError('Unreviewed emitter source material')
            refs = binding.get('fixtureIds')
            if not isinstance(refs, list) or len(refs) != len(set(refs)) or not set(refs) <= ids:
                raise ValueError('Emitter refers to an unknown fixture')
            color = vector(binding.get('color'), 'emitter RGB', 0, 1)
            finite(binding.get('emission'), 'diffuser emission', .05, 1.0)
            if refs:
                selected = [f for f in fixtures if f['id'] in refs]
                expected = [sum(f['color'][c] for f in selected)/len(selected) for c in range(3)]
                if any(abs(a-b) > 1e-12 for a, b in zip(color, expected)):
                    raise ValueError('Diffuser color must follow its explicit fixture palette')
            elif binding['emission'] > .4:
                raise ValueError('Emission-only architectural accents are limited to 0.4')
            if binding.get('shader') not in ('Surface', 'LanternPaper'):
                raise ValueError('Unreviewed emitter shader')
            if binding.get('breath') != 0 or type(binding.get('breath')) is bool:
                raise ValueError('Venue lighting must remain static, without breathing/strobe')
            finite(binding.get('paperRelief'), 'paper relief', 0, .045)
    if indices != list(range(88, 103)):
        raise ValueError('Reviewed 15-fixture ownership indices changed')
    return profile


def load_profile(path):
    raw = Path(path).read_bytes()
    profile = validate_profile(json.loads(raw))
    profile['_sourceSha256'] = hashlib.sha256(raw).hexdigest()
    return profile


def light_metadata(shop, fixture):
    return dict(schema=SCHEMA, venueId=shop['id'], fixtureId=fixture['id'], role=fixture['role'],
                color=copy.deepcopy(fixture['color']), intensityMultiplier=fixture['intensityMultiplier'])


def material_descriptor(original, binding):
    result = copy.deepcopy(original)
    result.update(name=binding['material'], color=copy.deepcopy(binding['color']),
                  emission=binding['emission'], shader=binding['shader'])
    return result


def apply_shop(g, sid, result, profile, created_keys):
    """After authored-module boundary checks, before source lights are appended.

    Adds bounded material clones; changes dictionary keys only, preserving array
    objects and batch insertion order. No nearest-light or coordinate routing.
    """
    validate_profile(profile)
    shop = next(s for s in profile['shops'] if s['id'] == sid)
    old_lights = result.get('lights', [])
    if len(old_lights) != len(shop['fixtures']):
        raise ValueError('Authored fixture count drift: ' + sid)
    revised = copy.deepcopy(result)
    for spec, fixture in zip(revised['lights'], shop['fixtures']):
        if set(spec) != {'position', 'range', 'strength'}:
            raise ValueError('Unreviewed authored light fields: ' + sid)
        if spec['position'] != fixture['localPosition'] or spec['range'] != fixture['range'] or spec['strength'] != fixture['strength']:
            raise ValueError('Existing authored fixture layout/budget drift: ' + fixture['id'])
        spec['venueLighting'] = light_metadata(shop, fixture)
    mapping = {}
    # Validate the full mutation set before mutating even this source-local graph.
    for binding in shop['emitters']:
        key = (binding['group'], binding['sourceMaterial'])
        target = (binding['group'], binding['material'])
        if key not in created_keys or key not in g.batches or target in g.batches or binding['material'] in g.materials:
            raise ValueError('Missing, unowned or already-remapped emitter batch: ' + repr(key))
        if binding['sourceMaterial'] not in g.materials:
            raise ValueError('Missing emitter source material')
        mapping[key] = target
    for binding in shop['emitters']:
        g.materials[binding['material']] = material_descriptor(g.materials[binding['sourceMaterial']], binding)
    g.batches = {mapping.get(key, key): batch for key, batch in g.batches.items()}
    revised['venueLighting'] = dict(schema=SCHEMA, profileVersion=VERSION,
                                    emitterBindings=copy.deepcopy(shop['emitters']))
    return revised


def manifest_record(profile):
    return dict(schema=SCHEMA, profileVersion=VERSION, profileSha256=profile['_sourceSha256'],
                ownedLightIndices=[f['manifestIndex'] for s in profile['shops'] for f in s['fixtures']],
                emitterBindings=[copy.deepcopy(b) for s in profile['shops'] for b in s['emitters']])


def validate_manifest(manifest, profile):
    """Actual manifest admission, also used before Blender scene mutation."""
    active = feature_enabled(manifest.get('features', {}))
    tagged = [i for i, light in enumerate(manifest.get('lights', [])) if 'venueLighting' in light]
    clones = [m for m in manifest.get('materials', []) if m['name'].startswith('VenueLight_')]
    if not active:
        if tagged or clones or 'venueLighting' in manifest:
            raise ValueError('Disabled venue lighting has active payload')
        return None
    validate_profile(profile)
    if manifest.get('venueLighting') != manifest_record(profile):
        raise ValueError('Venue lighting manifest header/bindings/profile hash mismatch')
    expected_indices = [f['manifestIndex'] for s in profile['shops'] for f in s['fixtures']]
    if tagged != expected_indices or len(manifest['lights']) != 374:
        raise ValueError('Actual owned/unrelated light roster changed')
    materials = {m['name']: m for m in manifest['materials']}
    if len(materials) != len(manifest['materials']):
        raise ValueError('Duplicate manifest material')
    expected_names = []
    for shop in profile['shops']:
        for fixture in shop['fixtures']:
            actual = manifest['lights'][fixture['manifestIndex']]
            expected = dict(position=fixture['worldPosition'], range=fixture['range'], strength=fixture['strength'],
                            venueLighting=light_metadata(shop, fixture))
            if actual != expected:
                raise ValueError('Actual fixture metadata/layout drift: ' + fixture['id'])
        for binding in shop['emitters']:
            expected_names.append(binding['material'])
            if materials.get(binding['material']) != material_descriptor(materials[binding['sourceMaterial']], binding):
                raise ValueError('Actual emissive material routing mismatch: ' + binding['material'])
    if sorted(m['name'] for m in clones) != sorted(expected_names):
        raise ValueError('Unexpected or missing venue material clone')
    return manifest['venueLighting']


def preview_light(spec):
    metadata = spec.get('venueLighting')
    if metadata is None:
        return [1, .48, .16], spec['strength'] * 110
    if metadata.get('schema') != SCHEMA:
        raise ValueError('Unsupported preview light metadata')
    return metadata['color'], spec['strength'] * 110 * metadata['intensityMultiplier']


def extend_fantasy_profile(fantasy, profile):
    """In-memory-only shader routing; never edits the legacy fantasy JSON."""
    result = copy.deepcopy(fantasy)
    for shop in profile['shops']:
        for binding in shop['emitters']:
            if binding['shader'] == 'LanternPaper':
                result['materialGroups'].append(dict(names=[binding['material']], shader='LanternPaper',
                    floats=[dict(name='_Breath', value=0), dict(name='_PaperRelief', value=binding['paperRelief'])]))
    return result


def configure_preview_emitters(bpy, manifest):
    """Restore exact unclipped bounded source emission after GLB import.

    These names deliberately do not inherit the old prefix-based strength=3
    override. Imported emission textures remain in place. Camera-only masking
    runs later, so this does not claim to simulate emissive Unity bake GI.
    """
    specs = {m['name']: m for m in manifest['materials'] if m['name'].startswith('VenueLight_')}
    configured = []
    for material in bpy.data.materials:
        if material.name not in specs or not material.use_nodes:
            continue
        spec = specs[material.name]
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                # glTF carries the color*emission factor, and imported texture
                # wiring multiplies it. Strength 1 preserves that product.
                node.inputs['Emission Strength'].default_value = 1.0
        configured.append(material.name)
    if set(configured) != set(specs):
        raise ValueError('GLB is missing actual venue emitter materials')
    return dict(materials=sorted(configured), static=True, emissionOnlyVisibleToCamera=True,
                scope='Cycles approximation; shared numeric RGB, different light units and GI from Unity baked lighting')
