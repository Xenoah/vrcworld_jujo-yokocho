"""Reconstruct ignored source payloads and run all offline regressions.
No Unity, network, SDK upload or VRChat action occurs.
"""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
root=Path(__file__).resolve().parent.parent
data=root/'Assets/TreeTopYokocho/Data'
from visual_transport import read_visual_transport
raw=read_visual_transport(data)
(data/'VisualMeshes.bytes').write_bytes(raw)
(data/'CollisionMeshes.bytes').write_bytes(gzip.decompress((data/'CollisionMeshes.bytes.gz').read_bytes()))
if not (root/'Source/TreeTopYokocho.glb').exists():
 raise SystemExit('The Git repository omits the editable GLB. First run python Source/build_world.py . and python Source/pack_geometry.py, or use the source release ZIP.')
for script in ['validate_world.py','validate_navigation.py','validate_crown.py','validate_infrastructure.py','validate_stage.py','validate_altitude.py','validate_bark_clearance.py','validate_shop_details.py','test_revision_contracts.py','validate_staff_access.py','validate_visual_routes.py','validate_preview_cameras.py','validate_shop_preview_routes.py','test_deck_surface.py','validate_deck_surfaces.py','validate_foliage_runtime_source.py','validate_menu_orientation.py','test_authored_tints.py','test_dusk_atmosphere.py','test_roof_surfaces.py','test_counter_surfaces.py','test_herb_planters.py','test_snow_deposition.py','validate_mountain_quality.py','test_visual_import_precision.py','test_cloud_depth.py','test_noh_roof_detail.py','test_stage_wood_finish.py','test_noren_craft.py','test_git_binary_attributes.py','validate_peer_culling.py','test_peer_culling_contract.py','test_visual_mesh_optimization.py','test_visual_optimization_contract.py','test_city_roof_caps_contract.py','test_visual_transport.py','test_shop_personality_dispatcher.py','test_shop_personality_contract.py','test_shop_profile_contract.py','test_shop_access_geometry.py','test_nightlife_venues.py','test_food_venues.py','test_rpg_runtime_compatibility.py','test_rpg_identity_contract.py','test_rpg_shop_identities.py','test_venue_lighting.py','test_rpg_integration.py','test_s05_pendant_contract.py','test_projecting_sign_contract.py','test_projecting_sign_source.py','test_projecting_sign_geometry.py','test_projecting_sign_summary.py','test_venue_projecting_signs.py','audit_shop_personality_glb.py','test_shopfront_print.py','test_lossless_shopfront_preview.py','validate_fantasy_materials.py','temporal_glare_audit.py','test_package_source_candidate.py','test_validation_report_integrity.py','write_validation_summary.py']:
 print('\nRunning '+script,flush=True)
 args=[] if script in ('test_rpg_runtime_compatibility.py','test_rpg_identity_contract.py','test_rpg_shop_identities.py','test_venue_lighting.py','test_rpg_integration.py','test_s05_pendant_contract.py','test_projecting_sign_contract.py','test_projecting_sign_source.py','test_projecting_sign_geometry.py','test_projecting_sign_summary.py','test_venue_projecting_signs.py','test_food_venues.py','test_validation_report_integrity.py','test_shop_access_geometry.py','test_nightlife_venues.py','test_shop_personality_dispatcher.py','test_shop_personality_contract.py','test_shop_profile_contract.py','temporal_glare_audit.py','test_mountain_detail.py','test_mountain_quality.py','test_mountain_snow_craft.py','test_mountain_seam_normals.py','test_visual_import_precision.py','test_package_source_candidate.py','test_visual_mesh_optimization.py','test_authored_tints.py','test_herb_planters.py','test_dusk_atmosphere.py','test_snow_deposition.py','validate_mountain_quality.py','test_visual_import_precision.py','test_cloud_depth.py','test_noh_roof_detail.py','test_stage_wood_finish.py') else [str(root)]
 if script=='audit_shop_personality_glb.py':args=['--after',str(root),'--strict','--report',str(root/'Docs/shop_personality_glb_validation.json')]
 if script=='test_shopfront_print.py':args=['--project',str(root),'--report',str(root/'Docs/shopfront_print_validation.json')]
 if script=='test_lossless_shopfront_preview.py':args=['--report',str(root/'Docs/shopfront_lossless_validation.json')]
 if script=='test_peer_culling_contract.py':args.extend(['--actual','--report',str(root/'Docs/peer_contract_validation.json')])
 if script=='test_stage_wood_finish.py':args=['--report',str(root/'Docs/stage_wood_finish_validation.json')]
 if script=='test_noren_craft.py':args=['--project',str(root),'--check-current-native','--report',str(root/'Docs/noren_craft_validation.json')]
 if script=='test_cloud_depth.py':args=['--report',str(root/'Docs/cloud_depth_source_validation.json')]
 if script=='test_snow_deposition.py':args=['--report',str(root/'Docs/snow_deposition_validation.json')]
 if script=='test_dusk_atmosphere.py':args=['--report',str(root/'Docs/dusk_atmosphere_validation.json')]
 if script=='test_counter_surfaces.py':args=['--report',str(root/'Docs/counter_surface_validation.json'),'--texture-dir',str(root/'Assets/TreeTopYokocho/Textures')]
 subprocess.run([sys.executable,str(root/'Source'/script),*args],check=True,cwd=root)
print('All offline checks passed. Unity/VRChat runtime and Windows size remain unverified.')
