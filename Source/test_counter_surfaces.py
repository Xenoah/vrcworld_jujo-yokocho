"""Pinned, offline counter-surface regression contract; no full-world build.

Run: python Source/test_counter_surfaces.py
The adjacent JSON is reviewed reference data, never generated or updated by
this test. Only temporary textures/native exports are written. Baseline source
provenance and hash conventions are recorded in that JSON; no old code is needed.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import random
import struct
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np
from PIL import Image

BASELINE_NAME = 'counter_surfaces.baseline.json'
PINNED_BASELINE_SHA256 = '243a7ad8e5bba3d29c65556618635b1e2e156807bae4a7b11a00f611700b1dad'
CHANNELS = ('.png', '_arm.png', '_normal.png')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def load_baseline(raw):
    require(sha(raw) == PINNED_BASELINE_SHA256,
            'Counter baseline checksum changed; review provenance and explicitly repin it')
    data = json.loads(raw)
    require(data['schema_version'] == 1, 'Unsupported counter baseline schema')
    return data


def function_hashes(path):
    return {node.name: sha(ast.dump(node, include_attributes=False).encode())
            for node in ast.parse(path.read_text()).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def rng_snapshot():
    state = np.random.get_state()
    return (random.getstate(), (state[0], state[1].copy(), *state[2:]))


def rng_equal(a, b):
    return (a[0] == b[0] and a[1][0] == b[1][0] and
            np.array_equal(a[1][1], b[1][1]) and a[1][2:] == b[1][2:])


def fixture(mod, geometry_type, shop, staff_entry):
    g = geometry_type()
    g.group = 'Shops/' + shop['id'] + '/CounterCraft'
    materials = {key: g.material('Audit_' + key, (.4, .3, .2))
                 for key in ('wood', 'dark', 'counter', 'iron', 'trim', 'menu')}
    group = g.group
    caller_rng = np.random.default_rng(12541)
    caller_state = canonical(caller_rng.bit_generator.state)
    state = rng_snapshot()
    furniture_calls = []
    result = mod.add_counter_craft(
        g, lambda x, y, z: np.array([x, y, z]),
        lambda *args: furniture_calls.append(args),
        shop['width'], shop['depth'], shop['index'], materials, caller_rng,
        staff_entry=staff_entry)
    require(not furniture_calls, shop['id'] + ': unexpected furniture callback')
    require(g.group == group, shop['id'] + ': global group changed')
    require(canonical(caller_rng.bit_generator.state) == caller_state,
            shop['id'] + ': caller Generator state changed')
    require(rng_equal(state, rng_snapshot()), shop['id'] + ': global RNG changed')
    return g, result


def geometry_digest(g):
    h = hashlib.sha256(canonical(g.materials))
    for key, batch in sorted(g.batches.items()):
        h.update(canonical(key))
        for name, dtype in (('v', '<f8'), ('uv', '<f8'), ('f', '<i8')):
            h.update(np.asarray(batch[name], dtype=dtype).tobytes())
    return h.hexdigest()


def inspect_batches(batches, material_specs, label):
    all_v = []
    triangles = 0
    for (group, material), batch in batches.items():
        v = np.asarray(batch['v'], dtype=float)
        uv = np.asarray(batch['uv'], dtype=float)
        f = np.asarray(batch['f'], dtype=np.int64)
        where = label + ' / ' + group + ' / ' + material
        require(v.ndim == 2 and v.shape[1] == 3 and len(v) > 0, where + ': vertex shape')
        require(f.ndim == 2 and f.shape[1] == 3 and len(f) > 0, where + ': face shape')
        require(uv.shape == (len(v), 2), where + ': UV count/shape')
        require(np.isfinite(v).all() and np.isfinite(uv).all(), where + ': non-finite data')
        require(f.min() >= 0 and f.max() < len(v), where + ': invalid face index')
        q = v[f]
        area = np.linalg.norm(np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]), axis=1)
        require(np.all(area > 1e-11), where + ': degenerate triangle')
        if material_specs[material].get('normal'):
            require(np.all((uv >= 0) & (uv <= 1)), where + ': atlas UV outside [0,1]')
            u = uv[f]
            a, b = u[:, 1]-u[:, 0], u[:, 2]-u[:, 0]
            require(np.all(np.abs(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]) > 1e-12),
                    where + ': collapsed atlas tangent')
        # Exercise source micro-detail at the world's raised float32 altitude.
        raised = v.copy()
        raised[:, 2] += 100
        q32 = raised.astype(np.float32).astype(float)[f]
        area32 = np.linalg.norm(np.cross(q32[:, 1]-q32[:, 0], q32[:, 2]-q32[:, 0]), axis=1)
        require(np.all(area32 > 1e-12), where + ': triangle collapses at +100 m float32')
        all_v.append(v)
        triangles += len(f)
    require(bool(all_v), label + ': no geometry')
    points = np.concatenate(all_v)
    return {'triangles': triangles, 'bounds': [points.min(0).tolist(), points.max(0).tolist()]}


def check_envelope(bounds, expected, label):
    actual = np.asarray(bounds)
    old = np.asarray(expected)
    require(np.all(actual[0] >= old[0]-1e-8) and np.all(actual[1] <= old[1]+1e-8),
            label + ': expanded pinned v2.8 placement envelope')


def read_native(path):
    """Read the actual small Geometry.save_binary output, not a mock exporter."""
    raw = path.read_bytes()
    offset = 0
    def take(n):
        nonlocal offset
        require(0 <= n <= len(raw)-offset, 'Truncated native counter export')
        result = raw[offset:offset+n]
        offset += n
        return result
    def u32():
        return struct.unpack('<I', take(4))[0]
    def string():
        return take(u32()).decode('utf-8')
    require(take(4) == b'JYWM' and u32() == 1, 'Native export header/version changed')
    count = u32()
    batches = {}
    for _ in range(count):
        key = (string(), string())
        require(key not in batches, 'Duplicate native export batch')
        nv, ni = u32(), u32()
        require(ni % 3 == 0, 'Native export index count is not triangular')
        v = np.frombuffer(take(nv*12), '<f4').reshape(-1, 3)
        uv = np.frombuffer(take(nv*8), '<f4').reshape(-1, 2)
        colors = take(nv*4)
        require(colors == bytes([255])*(nv*4), 'Unexpected counter vertex-color export')
        f = np.frombuffer(take(ni*4), '<u4').reshape(-1, 3)
        batches[key] = {'v': v, 'uv': uv, 'f': f}
    require(offset == len(raw), 'Unexpected trailing native export data')
    return batches


def check_structure(g, reference, baseline, label):
    require(g.materials == baseline['material_specs'], label + ': material set/spec changed')
    expected = {(reference['group'], m) for m in reference['batch_materials']}
    require(set(g.batches) == expected, label + ': batch set changed')


def rejection_checks(g, reference, baseline):
    """Small adversarial checks prove that the important guards are exercised."""
    count = 0
    def rejects(label, function):
        nonlocal count
        try:
            function()
        except AssertionError:
            count += 1
        else:
            raise AssertionError('Regression guard accepted mutation: ' + label)
    rejects('baseline edit', lambda: load_baseline(b'{}'))
    for mutation in ('nan', 'bad_index', 'degenerate', 'collapsed_uv'):
        changed = copy.deepcopy(g.batches)
        key = next(k for k in changed if k[1] == 'CraftSurfaces')
        b = changed[key]
        if mutation == 'nan': b['v'][0][0] = float('nan')
        if mutation == 'bad_index': b['f'][0][0] = len(b['v'])
        if mutation == 'degenerate': b['f'][0] = [b['f'][0][0]]*3
        if mutation == 'collapsed_uv':
            for i in b['f'][0]: b['uv'][i] = [0.5, 0.5]
        rejects(mutation, lambda b=changed: inspect_batches(b, g.materials, mutation))
    bounds = copy.deepcopy(reference['bounds'])
    bounds[1][0] += .001
    rejects('expanded bounds', lambda: check_envelope(bounds, reference['bounds'], 'mutation'))
    changed = copy.deepcopy(g)
    changed.materials['Unapproved'] = {'name': 'Unapproved'}
    rejects('extra material', lambda: check_structure(changed, reference, baseline, 'mutation'))
    changed = copy.deepcopy(g)
    changed.batches[('Unapproved', 'CraftSurfaces')] = next(iter(changed.batches.values()))
    rejects('extra batch', lambda: check_structure(changed, reference, baseline, 'mutation'))
    return count


def run_tests(source_dir=None, texture_dir=None):
    started = time.monotonic()
    source_dir = Path(source_dir or Path(__file__).resolve().parent)
    baseline = load_baseline(Path(__file__).with_name(BASELINE_NAME).read_bytes())
    sys.path.insert(0, str(source_dir))
    spec = importlib.util.spec_from_file_location('counter_surfaces_under_test', source_dir/'counter_craft.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from world_geometry import Geometry
    global_rng = rng_snapshot()
    actual_functions = function_hashes(source_dir/'counter_craft.py')
    for name, expected in baseline['untouched_function_ast_sha256'].items():
        require(actual_functions.get(name) == expected, 'Protected counter function changed: ' + name)
    for name, expected in baseline['public_signatures'].items():
        require(str(inspect.signature(getattr(mod, name))) == expected, 'Counter API changed: ' + name)
    layout = json.loads((source_dir/'layout.reference.json').read_text())['shops']
    layout_inputs = [{'id': s['id'], 'width': s['width'], 'depth': s['depth'], 'index': i}
                     for i, s in enumerate(layout)]
    require(layout_inputs == baseline['shop_inputs'], 'Pinned shop IDs/dimensions changed')
    report = {'passed': True, 'scope': 'Isolated source and native binary exports; no full-world build or Unity run',
              'baseline_sha256': PINNED_BASELINE_SHA256,
              'source_sha256': sha((source_dir/'counter_craft.py').read_bytes()), 'fixtures': []}
    with tempfile.TemporaryDirectory(prefix='yokocho-counter-check-') as tmp:
        tmp = Path(tmp)
        for mode, staff_entry in (('standard', False), ('staff_entry', True)):
            for shop, reference in zip(layout_inputs, baseline['fixtures'][mode]):
                label = mode + '/' + shop['id']
                g, result = fixture(mod, Geometry, shop, staff_entry)
                again, result2 = fixture(mod, Geometry, shop, staff_entry)
                require(result == result2 and geometry_digest(g) == geometry_digest(again),
                        label + ': nondeterministic source generation')
                require(result['settings'] == reference['service_settings'], label + ': service layout changed')
                require(result['shop'] == shop['id'] and result['collision_changes'] is False,
                        label + ': service identity/collision report changed')
                check_structure(g, reference, baseline, label)
                stats = inspect_batches(g.batches, g.materials, label)
                check_envelope(stats['bounds'], reference['bounds'], label)
                require(stats['triangles'] == reference['reviewed_triangles'], label + ': reviewed triangle count changed')
                if mode == 'standard' and shop['index'] == 0:
                    report['rejected_adversarial_mutations'] = rejection_checks(g, reference, baseline)
                for candidate, filename in ((g, 'first.bytes'), (again, 'second.bytes')):
                    candidate.compact()
                    candidate.save_binary(tmp/filename)
                raw = (tmp/'first.bytes').read_bytes()
                require(raw == (tmp/'second.bytes').read_bytes(), label + ': nondeterministic native export')
                exported = read_native(tmp/'first.bytes')
                require(set(exported) == set(g.batches), label + ': exported batch set changed')
                for key, batch in exported.items():
                    for field in ('v', 'uv', 'f'):
                        require(np.array_equal(batch[field], g.batches[key][field]),
                                label + ': native export differs from compact source ' + field)
                inspect_batches(exported, g.materials, label + '/export')
                report['fixtures'].append({'shop': shop['id'], 'mode': mode, **stats,
                                           'native_export_sha256': sha(raw), 'native_bytes': len(raw)})
        first, second = tmp/'textures_a', tmp/'textures_b'
        a = mod.counter_craft_textures(first)
        b = mod.counter_craft_textures(second)
        expected_names = ['counter_craft' + suffix for suffix in CHANNELS]
        for result in (a, b):
            require(sorted(Path(p).name for p in result['files']) == sorted(expected_names), 'Texture set changed')
            require(result['size'] == [1024, 512], 'Atlas dimensions changed')
        require(sorted(p.name for p in first.iterdir()) == sorted(expected_names), 'Unreported atlas file added')
        for channel, suffix in enumerate(CHANNELS):
            p, q = first/('counter_craft'+suffix), second/('counter_craft'+suffix)
            require(p.read_bytes() == q.read_bytes(), 'Nondeterministic PNG export: ' + suffix)
            if texture_dir is not None:
                require((Path(texture_dir)/p.name).read_bytes() == p.read_bytes(), 'Actual exported PNG differs from deterministic source: '+p.name)
            pixels = np.asarray(Image.open(p))
            require(pixels.shape == (512, 1024, 3), 'Atlas RGB dimensions changed: ' + suffix)
            for slot, hashes in baseline['unchanged_tile_rgb_sha256'].items():
                tile = int(slot)
                cell = pixels[tile//8*128:(tile//8+1)*128, tile%8*128:(tile%8+1)*128]
                require(sha(cell.tobytes(order='C')) == hashes[channel], 'Unapproved tile change: ' + slot + suffix)
        report['textures'] = {'atlas_count': 3, 'dimensions': [1024, 512],
                              'unchanged_tiles': len(baseline['unchanged_tile_rgb_sha256']),
                              'png_bytes': sum((first/n).stat().st_size for n in expected_names),
                              'actual_exported_pngs_verified': texture_dir is not None}
    require(rng_equal(global_rng, rng_snapshot()), 'Tested source/export pipeline changed global RNG')
    report['protected_functions'] = len(baseline['untouched_function_ast_sha256'])
    report['seconds'] = round(time.monotonic()-started, 3)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, help='Optional source directory for staging verification')
    parser.add_argument('--texture-dir', type=Path, help='Compare the three actual exported PNG files')
    parser.add_argument('--report', type=Path, help='Optional JSON result path')
    args = parser.parse_args()
    result = run_tests(args.source_dir, args.texture_dir)
    if args.report: args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
