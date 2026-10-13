"""Source-only foliage wind/wrap regression; no Unity execution or FPS claim.

Usage: python validate_foliage_runtime_source.py /path/to/project [--output report.json]
Checks the exact supported shader formulas and builder settings, then evaluates
referenced source vertices at six times. It neither edits nor regenerates assets.
"""
from pathlib import Path
import argparse, gzip, hashlib, io, json, math, re, struct
import numpy as np


def strip_comments(text):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)


def source_meshes(data):
    path = data/'VisualMeshes.bytes'
    if path.exists():
        payload = path.read_bytes()
    elif path.with_name(path.name+'.gz').exists():
        payload = gzip.decompress(path.with_name(path.name+'.gz').read_bytes())
    else:
        shards = sorted(data.glob('VisualMeshes.bytes.gz.part[0-9][0-9][0-9]'))
        if not shards:
            raise FileNotFoundError('No visual geometry source payload or shards')
        for i, part in enumerate(shards):
            assert part.name == 'VisualMeshes.bytes.gz.part%03d' % i, 'Missing geometry shard'
        payload = gzip.decompress(b''.join(p.read_bytes() for p in shards))
    r = io.BytesIO(payload)
    assert r.read(4) == b'JYWM'
    version, count = struct.unpack('<II', r.read(8))
    assert version == 1
    for _ in range(count):
        group, material = [r.read(struct.unpack('<I', r.read(4))[0]).decode('utf-8') for i in range(2)]
        nv, ni = struct.unpack('<II', r.read(8))
        vertices = np.frombuffer(r.read(nv*12), '<f4').reshape(-1, 3)
        uv = np.frombuffer(r.read(nv*8), '<f4').reshape(-1, 2)
        r.read(nv*4)
        faces = np.frombuffer(r.read(ni*4), '<u4').reshape(-1, 3)
        yield group, material, vertices, uv, faces
    assert r.read() == b'', 'Unexpected payload trailing bytes'


def run(root):
    asset = root/'Assets/TreeTopYokocho'
    shader_path = asset/'Shaders/YokochoFoliage.shader'
    builder_path = asset/'Editor/YokochoWorldBuilder.cs'
    shader = strip_comments(shader_path.read_text())
    builder = strip_comments(builder_path.read_text())
    vert = shader.split('void vert(', 1)[1].split('void surf(', 1)[0]
    compact = re.sub(r'\s+', '', vert)
    assert 'texcoord' not in compact, 'Wind must not depend on repaired/tiled texture UVs'
    assert 'float3p=mul(unity_ObjectToWorld,v.vertex).xyz;' in compact
    assert 'floatw=sin(_Time.y*.8+p.x*.42+p.z*.31)+.4*sin(_Time.y*1.7+p.y*.73);' in compact, 'Update mathematical regression when changing the wave'
    assert 'floatamplitude=clamp(_Wind,0.0,.08);' in compact
    assert 'v.vertex.xz+=float2(w,w*.44)*amplitude;' in compact
    atlas = re.search(r'bool\s+atlas\s*=([^;]+);', builder).group(1)
    assert 'leaf.png' not in atlas and 'foliage_spray.png' not in atlas, 'Tiled foliage must use Repeat'
    assert 'importer.wrapMode=atlas?TextureWrapMode.Clamp:TextureWrapMode.Repeat;' in re.sub(r'\s+', '', builder)
    match = re.search(r'if\s*\(foliage\)\s*\{[^}]*bounds\.Expand\(new Vector3\(([^)]+)\)\)', builder)
    assert match, 'Foliage needs explicit animated bounds expansion'
    expansion = np.array([float(s.strip().rstrip('f')) for s in match.group(1).split(',')])
    max_component = np.array([1.4*.08, 0, 1.4*.08*.44])
    assert np.all(expansion/2 >= max_component), 'Bounds.Expand is total size, not extents'
    manifest = json.loads((asset/'Data/WorldManifest.json').read_text())
    foliage = {m['name'] for m in manifest['materials'] if m.get('shader') == 'Foliage'}
    times = (0., 1.25, 17., 61., 123.4, 3600.)
    records = []
    duplicate_sets = referenced_vertices = meshes = uv_outside = 0
    old_max = fixed_default_max = seam_max = default_seam_max = fixed_max = 0.
    saturated_seam_max = 0.
    for group, material, vertices, uv, faces in source_meshes(asset/'Data'):
        if material not in foliage:
            continue
        meshes += 1
        used = np.unique(faces)
        v = vertices[used].astype(np.float64)
        u = uv[used].astype(np.float64)
        referenced_vertices += len(v)
        uv_outside += int(((u < 0) | (u > 1)).any(axis=1).sum())
        # Source (X,Y,Z) maps to Unity (X,Z,Y). Builder uses identity mesh transforms.
        p = v[:, [0, 2, 1]]
        unique, inverse, counts = np.unique(p, axis=0, return_inverse=True, return_counts=True)
        duplicate = counts > 1
        duplicate_sets += int(duplicate.sum())
        lower, upper = p.min(axis=0)-expansion/2, p.max(axis=0)+expansion/2
        def seam_error(offset):
            lo = np.full(len(unique), np.inf)
            hi = np.full(len(unique), -np.inf)
            np.minimum.at(lo, inverse, offset)
            np.maximum.at(hi, inverse, offset)
            return float(np.max((hi-lo)[duplicate])) if duplicate.any() else 0.
        for t in times:
            wave = np.sin(t*.8+p[:, 0]*.42+p[:, 2]*.31)+.4*np.sin(t*1.7+p[:, 1]*.73)
            old = wave*.018*u[:, 1]
            old_max = max(old_max, float(np.max(np.abs(old)))*math.hypot(1, .44))
            saturated_seam_max = max(saturated_seam_max, seam_error(wave*.018*np.clip(u[:, 1], 0, 1))*math.hypot(1, .44))
            for amplitude_input in (-1., .018, .08, 1.):
                amplitude = np.clip(amplitude_input, 0., .08)
                dx = wave*amplitude
                delta = np.column_stack((dx, np.zeros(len(dx)), dx*.44))
                maximum = float(np.linalg.norm(delta, axis=1).max())
                assert maximum <= 1.4*amplitude*math.hypot(1, .44)+1e-12
                assert np.all(p+delta >= lower-1e-12) and np.all(p+delta <= upper+1e-12), 'Animated vertex escapes expanded bounds'
                seam = seam_error(dx)*math.hypot(1, .44)
                seam_max = max(seam_max, seam)
                fixed_max = max(fixed_max, maximum)
                if amplitude_input == .018:
                    fixed_default_max = max(fixed_default_max, maximum)
                    default_seam_max = max(default_seam_max, seam)
    assert meshes > 0 and duplicate_sets > 0, 'Actual foliage and UV-seam cases must be exercised'
    assert seam_max == 0, 'Coincident vertices must have identical motion'
    return dict(status='PASS',passed=True, scope='Offline source/math regression only; no Unity/HLSL compilation, GPU capture, rendered-frame, bake or VRChat claim',
        manifest_version=manifest['version'], foliage_meshes=meshes, referenced_vertices=referenced_vertices,
        referenced_vertices_outside_0_1_uv=uv_outside, duplicate_position_sets=duplicate_sets,
        test_times=list(times), tested_input_amplitudes=[-1, .018, .08, 1],
        analytic_default_max_displacement_m=1.4*.018*math.hypot(1, .44),
        measured_source_default_max_displacement_m=fixed_default_max,
        analytic_supported_max_displacement_m=1.4*.08*math.hypot(1, .44),
        measured_source_supported_max_displacement_m=fixed_max,
        max_duplicate_displacement_difference_m=seam_max,
        previous_uv_weight_source_max_displacement_m=old_max,
        rejected_uv_saturate_max_duplicate_difference_m=saturated_seam_max,
        bounds_size_expansion_unity_xyz=expansion.tolist(), repeat_textures=['leaf.png','foliage_spray.png'],
        shader_sha256=hashlib.sha256(shader_path.read_bytes()).hexdigest(),
        builder_sha256=hashlib.sha256(builder_path.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = run(args.root)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    output=args.output or args.root/'Docs/foliage_runtime_validation.json'
    output.write_text(text+'\n')
    print(text)
