"""Use one coherent existing rough-wood PBR set on the outdoor stage only.

Geometry, UV density, tint, all other materials and all RNG states are untouched.
This is a visual finish choice, not a claim about the scanned timber species.
"""
MATERIAL = 'StageCypress'
FIELDS = ('texture', 'normal', 'arm', 'height')
OLD_FILES = dict(zip(FIELDS, (
    'PBR/wood_table_001_diff_4k.jpg', 'PBR/wood_table_001_nor_gl_2k.jpg',
    'PBR/wood_table_001_arm_2k.jpg', 'PBR/wood_table_001_disp_2k.jpg')))
NEW_FILES = dict(zip(FIELDS, (
    'PBR/wood_planks_grey_diff_4k.jpg', 'PBR/wood_planks_grey_nor_gl_2k.jpg',
    'PBR/wood_planks_grey_arm_2k.jpg', 'PBR/wood_planks_grey_disp_2k.jpg')))


def apply_stage_wood_finish(g):
    """Atomic, explicit four-field update; reject drift and repeat application."""
    spec = g.materials.get(MATERIAL)
    if not isinstance(spec, dict) or any(spec.get(k) != v for k, v in OLD_FILES.items()):
        raise ValueError('StageCypress no longer has the reviewed original PBR set')
    reference = g.materials.get('Cedar')
    if not isinstance(reference, dict) or any(reference.get(k) != v for k, v in NEW_FILES.items()):
        raise ValueError('The reviewed shared rough-wood PBR set is unavailable')
    spec.update(NEW_FILES)
    return {'material': MATERIAL, 'changedFields': list(FIELDS),
            'existingTextureSet': 'wood_planks_grey', 'newTextureFiles': 0,
            'geometryAndUvUnchanged': True,
            'description': 'Outdoor unvarnished-wood appearance; scan species is not identified'}
