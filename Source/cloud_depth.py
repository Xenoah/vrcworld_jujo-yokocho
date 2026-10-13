"""Optional, geometry-only cloud shoulder depth; source XYZ/Z-up.

Call apply_cloud_depth(g, clouds) once after add_cloud_sea and BEFORE compact.
Omitting this call leaves the legacy generator and every RNG stream unchanged.
Only the eight enumerated clouds' Z coordinates and explicit descriptive
metadata are changed. No shader/material appearance or topology is changed.
"""
from __future__ import annotations

import copy
import numpy as np

DEPTH_FACTOR = 2.2
ANCHOR_Z = 124.0
LEGACY_BASE_Z = 110.0
DEPTH_BASE_Z = 93.2  # Exact documented decimal for 124 - (124 - 110) * 2.2
MAX_SHADER_SWELL = .15
DEPTH_PROFILE = 'CloudShoulders_ZOnly_2p2_About124m'
MATERIAL_NAME = 'CloudSeaSilver'
CLOUD_KEYS = (
    ('Landscape/CloudSea_Near_NW', MATERIAL_NAME),
    ('Landscape/CloudSea_Near_NE', MATERIAL_NAME),
    ('Landscape/CloudSea_Near_SW', MATERIAL_NAME),
    ('Landscape/CloudSea_Near_SE', MATERIAL_NAME),
    ('Landscape/CloudSea_Far_NW', MATERIAL_NAME),
    ('Landscape/CloudSea_Far_NE', MATERIAL_NAME),
    ('Landscape/CloudSea_Far_SW', MATERIAL_NAME),
    ('Landscape/CloudSea_Far_SE', MATERIAL_NAME),
)
EXPECTED_COUNTS = {'bankCount': 28, 'billowCount': 252, 'drawBatches': 8,
                   'vertices': 20412, 'triangles': 36288}


def depth_z(z):
    """Authoring precision is float64; compact performs the sole float32 cast."""
    values = np.asarray(z, dtype=np.float64)
    return ANCHOR_Z - (ANCHOR_Z - values) * DEPTH_FACTOR


def apply_cloud_depth(g, cloud_metadata):
    """Mutate the explicit cloud scope and return the supplied metadata object.

    Validate everything before committing changes. Calling twice, calling after
    compact, unexpected cloud identities, or legacy profile drift are errors.
    Noncloud geometry/materials and non-enumerated metadata fields are untouched.
    banks[*].center[2] maps the existing rounded authored base; it is NOT the
    geometric centroid. depthRefinement documents that retained convention.
    """
    if 'depthRefinement' in cloud_metadata:
        raise ValueError('Cloud depth already applied')
    if (cloud_metadata.get('enabled') is not True
            or cloud_metadata.get('material') != MATERIAL_NAME
            or cloud_metadata.get('shader') != 'TreeTopYokocho/CloudSea'
            or any(cloud_metadata.get(k) != v for k, v in EXPECTED_COUNTS.items())):
        raise ValueError('Unexpected legacy cloud metadata/counts')
    if (cloud_metadata.get('maximumAnimatedAltitude') != 124.0
            or cloud_metadata.get('lowestDeckAltitude') != 134.0
            or cloud_metadata.get('minimumDeckClearance') != 10.0):
        raise ValueError('Unexpected cloud/deck clearance contract')
    material = g.materials.get(MATERIAL_NAME)
    if (not isinstance(material, dict) or material.get('cloudBaseZ') != LEGACY_BASE_Z
            or material.get('cloudTopZ') != ANCHOR_Z
            or material.get('shader') != 'CloudSea'):
        raise ValueError('Unexpected descriptive cloud material envelope')
    keys = set(CLOUD_KEYS)
    observed = {key for key in g.batches if key[0].startswith('Landscape/CloudSea_')}
    if observed != keys:
        raise ValueError('Cloud batch roster differs from eight explicit keys')
    banks = cloud_metadata.get('banks', [])
    if len(banks) != 28 or [x.get('id') for x in banks] != ['CloudBank%02d' % i for i in range(28)]:
        raise ValueError('Cloud bank roster/order changed')
    updated_centers = []
    for bank in banks:
        if not isinstance(bank.get('center'), list):
            raise ValueError('Cloud bank center must retain the plain-JSON mutable list contract')
        center = np.asarray(bank.get('center'), dtype=np.float64)
        if (center.shape != (3,) or not np.isfinite(center).all()
                or not 110.55 <= center[2] <= 112.35
                or (bank.get('group'), MATERIAL_NAME) not in keys):
            raise ValueError('Unexpected authored cloud bank center/group')
        updated_centers.append(round(float(depth_z(center[2])), 3))
    replacements = []
    old_low, old_high = float('inf'), -float('inf')
    low, high, vertices, triangles = float('inf'), -float('inf'), 0, 0
    for key in CLOUD_KEYS:
        batch = g.batches[key]
        raw = np.asarray(batch['v'])
        if raw.dtype != np.float64:
            raise ValueError('Cloud depth requires float64 authoring geometry before compact')
        if raw.ndim != 2 or raw.shape[1] != 3 or not len(raw) or not np.isfinite(raw).all():
            raise ValueError('Invalid cloud vertices')
        if raw[:, 2].min() < LEGACY_BASE_Z or raw[:, 2].max() >= ANCHOR_Z:
            raise ValueError('Cloud input outside unchanged legacy altitude envelope')
        faces = np.asarray(batch['f'])
        uv = np.asarray(batch['uv'])
        if (faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
                or not np.issubdtype(faces.dtype, np.integer)
                or faces.min() < 0 or faces.max() >= len(raw)
                or uv.shape != (len(raw), 2) or not np.isfinite(uv).all()):
            raise ValueError('Invalid cloud topology or UVs')
        new = raw.copy()
        new[:, 2] = depth_z(raw[:, 2])
        old_low = min(old_low, float(raw[:, 2].min()))
        old_high = max(old_high, float(raw[:, 2].max()))
        low = min(low, float(new[:, 2].min()))
        high = max(high, float(new[:, 2].max()))
        vertices += len(raw); triangles += len(faces)
        replacements.append((batch, new.tolist()))
    if vertices != EXPECTED_COUNTS['vertices'] or triangles != EXPECTED_COUNTS['triangles']:
        raise ValueError('Actual cloud geometry counts differ from unchanged budget')
    if cloud_metadata.get('altitudeBounds') != [round(old_low, 3), round(old_high, 3)]:
        raise ValueError('Legacy cloud altitude metadata does not match source')
    # A float32 rounding cannot consume the >0.24m margin here. Check the
    # actual float32 upper bound too, so export precision remains explicit.
    exported_high = float(np.float32(high))
    maximum_animated = exported_high + MAX_SHADER_SWELL
    if low < DEPTH_BASE_Z or maximum_animated >= ANCHOR_Z:
        raise ValueError('Deepened clouds exceed the fixed animated envelope')
    detail = {
        'id': DEPTH_PROFILE, 'axis': 'Z', 'anchorZ': ANCHOR_Z,
        'factor': DEPTH_FACTOR, 'altitudeEnvelope': [DEPTH_BASE_Z, ANCHOR_Z],
        'originalAltitudeBounds': copy.deepcopy(cloud_metadata['altitudeBounds']),
        'maximumShaderSwell': MAX_SHADER_SWELL,
        'conservativeAnimatedTop': round(maximum_animated, 6),
        'bankCenterZConvention': '2.2x transform of legacy rounded authored base; not mesh centroid',
        'precision': 'float64 authoring, then unchanged compact/export float32 cast',
        'shaderAppearanceUnchanged': True,
        'addedVertices': 0, 'addedTriangles': 0, 'addedBatches': 0,
        'addedTextures': 0, 'addedLights': 0, 'addedShaderPasses': 0,
    }
    # Only these enumerated assignments are permitted by this pass.
    for batch, values in replacements:
        batch['v'] = values
    for bank, z in zip(banks, updated_centers):
        bank['center'][2] = z
    cloud_metadata['altitudeBounds'] = [round(low, 3), round(high, 3)]
    cloud_metadata['depthRefinement'] = detail
    # Descriptive only: Unity MaterialSpec and the shader do not consume this.
    material['cloudBaseZ'] = DEPTH_BASE_Z
    return cloud_metadata
