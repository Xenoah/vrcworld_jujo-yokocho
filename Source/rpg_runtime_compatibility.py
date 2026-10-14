"""Separately reviewed v2.17 runtime-source compatibility, before art approval.

This does not approve any atlas, mesh, light palette or final world. It accepts
only one frozen complete C# shader/material/light route; original shader and
precision/shadow guards remain exact. An unfrozen checkpoint fails closed.
"""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path

ORACLE_NAME = 'rpg_runtime_compatibility_2_17.json'
ORACLE_SHA256 = '7140031774a751392b6e40bdc25421d72af1b0383b9d569b9eb70ba02e8394fb'
BEFORE_NAME = 'rpg_identity_before_2_16.json.gz'
BEFORE_SHA256 = 'a19dc9018be31e778652134706f177edf1d43510828f4ff0ed3051b9a2c2bd6f'
BUILDER = 'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs'
LEGACY_BUILDER_SHA256 = 'b1457615342413a2f099308920883169ec5aec88c39b932511a4e8fd0a10c119'
ADDED_RUNTIME = ('Assets/TreeTopYokocho/Editor/VenueLightingProfile.cs',)
RUNTIME_PREFIXES = ('Assets/TreeTopYokocho/Editor/', 'Assets/TreeTopYokocho/Shaders/')
PROFILE = 'Assets/TreeTopYokocho/Data/FantasyMaterials.json'
LEGACY_SHOP_PROFILE_SHA256 = '9986ae06f773d436a175ec47c6af1e627082352fd59634014e59c72e29351cd2'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _fixture(name, expected, root=None):
    source = Path(root) / 'Source' if root is not None else Path(__file__).resolve().parent
    raw = (source / 'testdata' / name).read_bytes()
    if sha(raw) != expected:
        raise ValueError('Frozen runtime compatibility evidence changed: ' + name)
    return raw


def baseline_runtime(root=None):
    before = json.loads(gzip.decompress(_fixture(BEFORE_NAME, BEFORE_SHA256, root)))
    result = {p: h for p, h in before['dependencies'].items() if p.startswith(RUNTIME_PREFIXES)}
    if result.get(BUILDER) != LEGACY_BUILDER_SHA256:
        raise ValueError('Invalid immutable v2.16 builder provenance')
    return result


def load_oracle(root=None):
    if ORACLE_SHA256.startswith('UNFROZEN'):
        raise ValueError('Runtime compatibility has not been independently source-reviewed and frozen')
    pin = json.loads(_fixture(ORACLE_NAME, ORACLE_SHA256, root))
    before = baseline_runtime(root)
    if set(pin) != {'schema', 'version', 'beforeBuilderSha256', 'dependencies', 'scope'}:
        raise ValueError('Unexpected runtime compatibility schema fields')
    if (type(pin['schema']) is not int or pin['schema'] != 1 or pin['version'] != '2.17.0'
            or pin['beforeBuilderSha256'] != LEGACY_BUILDER_SHA256
            or set(pin['dependencies']) != set(before) | set(ADDED_RUNTIME)):
        raise ValueError('Invalid exact runtime compatibility roster')
    for rel, old in before.items():
        if rel != BUILDER and pin['dependencies'][rel] != old:
            raise ValueError('Unrelated runtime shader/loader change is forbidden: ' + rel)
    if any(not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h)
           for h in pin['dependencies'].values()):
        raise ValueError('Invalid runtime dependency hash')
    return pin


def verify_runtime(root, *, oracle=None):
    """Check exact current source; never invoke the unapproved visual oracle."""
    root = Path(root)
    pin = load_oracle(root) if oracle is None else oracle
    expected = pin['dependencies']
    actual_roster = set()
    for prefix in RUNTIME_PREFIXES:
        actual_roster.update(str(p.relative_to(root)) for p in (root / prefix).rglob('*')
                             if p.is_file() and p.suffix != '.meta')
    if actual_roster != set(expected):
        raise ValueError('Unreviewed runtime shader/loader file roster')
    for rel, expected_sha in expected.items():
        if sha((root / rel).read_bytes()) != expected_sha:
            raise ValueError('Exact source-reviewed runtime dependency changed: ' + rel)
    # The venue runtime extends only its own named clones in memory. The stored
    # old/global material profile remains byte-identical to its reviewed value.
    if sha((root / PROFILE).read_bytes()) != LEGACY_SHOP_PROFILE_SHA256:
        raise ValueError('Original/global fantasy material profile changed')
    return expected[BUILDER]


def approved_builder_sha(root):
    """Original source is unchanged, or every v2.17 runtime source is reviewed."""
    root = Path(root)
    actual = sha((root / BUILDER).read_bytes())
    if actual == LEGACY_BUILDER_SHA256 and not any((root / p).exists() for p in ADDED_RUNTIME):
        return actual
    return verify_runtime(root)
