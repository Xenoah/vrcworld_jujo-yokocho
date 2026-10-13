"""Reconstruct ignored source payloads and run all offline regressions.
No Unity, network, SDK upload or VRChat action occurs.
"""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
root=Path(__file__).resolve().parent.parent
data=root/'Assets/TreeTopYokocho/Data'
shards=json.loads((data/'GeometryShards.json').read_text())
parts=[]
for entry in shards['shards']:
 payload=(data/entry['name']).read_bytes()
 if len(payload)!=entry['bytes'] or hashlib.sha256(payload).hexdigest()!=entry['sha256']:
  raise ValueError('Changed or incomplete geometry shard: '+entry['name'])
 parts.append(payload)
compressed=b''.join(parts)
if hashlib.sha256(compressed).hexdigest()!=shards['sha256']:raise ValueError('Combined geometry checksum mismatch')
raw=gzip.decompress(compressed)
if len(raw)!=shards['uncompressed_bytes']:raise ValueError('Uncompressed geometry length mismatch')
(data/'VisualMeshes.bytes').write_bytes(raw)
(data/'CollisionMeshes.bytes').write_bytes(gzip.decompress((data/'CollisionMeshes.bytes.gz').read_bytes()))
if not (root/'Source/TreeTopYokocho.glb').exists():
 raise SystemExit('The Git repository omits the editable GLB. First run python Source/build_world.py . and python Source/pack_geometry.py, or use the source release ZIP.')
for script in ['validate_world.py','validate_navigation.py','validate_crown.py','validate_infrastructure.py','validate_stage.py','validate_altitude.py','validate_bark_clearance.py','validate_shop_details.py','test_revision_contracts.py','validate_staff_access.py','validate_visual_routes.py','test_deck_surface.py','validate_deck_surfaces.py','validate_foliage_runtime_source.py','validate_menu_orientation.py','test_authored_tints.py','test_dusk_atmosphere.py','test_roof_surfaces.py','test_counter_surfaces.py','test_herb_planters.py','test_git_binary_attributes.py','validate_peer_culling.py','test_peer_culling_contract.py','write_validation_summary.py']:
 print('\nRunning '+script,flush=True)
 args=[] if script in ('test_authored_tints.py','test_herb_planters.py','test_dusk_atmosphere.py') else [str(root)]
 if script=='test_peer_culling_contract.py':args.append('--actual')
 if script=='test_dusk_atmosphere.py':args=['--report',str(root/'Docs/dusk_atmosphere_validation.json')]
 if script=='test_counter_surfaces.py':args=['--report',str(root/'Docs/counter_surface_validation.json'),'--texture-dir',str(root/'Assets/TreeTopYokocho/Textures')]
 subprocess.run([sys.executable,str(root/'Source'/script),*args],check=True,cwd=root)
print('All offline checks passed. Unity/VRChat runtime and Windows size remain unverified.')
