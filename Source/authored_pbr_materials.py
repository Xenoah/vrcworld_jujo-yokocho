"""Pure, inactive four-family path substitution. No geometry or runtime imports.

The owner must review the generator/art and explicitly wire this helper later.
Only the owner-authorized family parallax calibration may change numerically.
"""
import copy

FAMILIES = {
    'bark_brown_02': 'yokocho_bark',
    'wood_planks_grey': 'yokocho_weathered_timber',
    'wood_table_001': 'yokocho_counter_timber',
    'rocky_terrain_02': 'yokocho_mineral_rock',
}
PARALLAX = {'bark_brown_02': .008, 'wood_planks_grey': .0018,
            'wood_table_001': .0006, 'rocky_terrain_02': .006}
SUFFIXES = {
    'texture': ('diff_4k.jpg', 'albedo.png'),
    'normal': ('nor_gl_2k.jpg', 'normalGL.png'),
    'arm': ('arm_2k.jpg', 'arm.png'),
    'height': ('disp_2k.jpg', 'height.png'),
}
PATH_MAPPING = {
    f'PBR/{old}_{suffix[0]}': f'PBR/{new}_{suffix[1]}'
    for old, new in FAMILIES.items() for suffix in SUFFIXES.values()
}
LOSSLESS_TEXTURES = tuple(
    f'PBR/{new}_{suffix[1]}' for new in FAMILIES.values()
    for field, suffix in SUFFIXES.items() if field != 'height'
)


def replace_material_paths(materials):
    """Return a new ordered dict/list; change only existing four map-path fields.

    Texture-only materials stay texture-only. No new normal/height/ARM slots,
    material IDs, tint, UV scale, roughness, or normal strength changes. Only
    the baseline .014 parallax becomes the exact selected family value; zeros
    remain zero. This is shader surface calibration, not geometric displacement.
    This intentionally accepts material descriptors, not a Geometry object.
    """
    if not isinstance(materials, (list, dict)):
        raise TypeError('Material descriptors must be an ordered dict or list')
    out = copy.deepcopy(materials)
    values = out.values() if isinstance(out, dict) else out
    for material in values:
        if not isinstance(material, dict):
            raise TypeError('Every material descriptor must be an object')
        old_texture = material.get('texture')
        for old_family in FAMILIES:
            if old_texture == f'PBR/{old_family}_diff_4k.jpg' and material.get('parallax', 0) != 0:
                if type(material['parallax']) not in (int, float) or material['parallax'] != .014:
                    raise ValueError('Only exact baseline .014 parallax may be calibrated')
                material['parallax'] = PARALLAX[old_family]
        for field in SUFFIXES:
            value = material.get(field)
            if isinstance(value, str) and value in PATH_MAPPING:
                material[field] = PATH_MAPPING[value]
    return out
