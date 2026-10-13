"""Keep the Assets-only handoff's existing documentation current."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent.parent
out=root/'Assets/TreeTopYokocho/Documentation'
for current in out.glob('*.md'):
 source=root/'Docs'/current.name
 if current.name=='PolyHaven.md':source=root/'Docs/ThirdParty/PolyHaven.md'
 if source.exists():current.write_bytes(source.read_bytes())
for name in ['IndependentReview_2.10.0.md','RELEASE_NOTES_2.10.0.md','HerbPlanters.md','peer_contract_validation.json','RELEASE_NOTES_2.9.0.md','IndependentReview_2.9.0.md','SurfaceRefinement.md','menu_orientation_validation.json','peer_culling_validation.json','roof_surface_validation.json','counter_surface_validation.json','git_binary_validation.json','AuthoringEnvironment.json','RELEASE_NOTES_2.8.0.md','IndependentReview_2.8.0.md','DeckAndAccess.md','staff_access_validation.json','deck_surface_validation.json','deck_module_validation.json','foliage_runtime_validation.json','visual_route_validation.json','RELEASE_NOTES_2.7.0.md','IndependentReview_2.7.0.md','ShopCraft.md','shop_detail_validation.json','RELEASE_NOTES_2.6.0.md','IndependentReview_2.6.0.md','AltitudePumps.md','HighCrownStairs.md','CloudSea.md','SceneryDetail.md','validation.json','navigation_validation.json','crown_validation.json','infrastructure_validation.json','stage_validation.json','altitude_validation.json','bark_clearance_validation.json','WindowsProfile.json']+[str(p.relative_to(root/'Docs')) for p in sorted((root/'Docs/baselines').glob('*')) if p.is_file()]:
 source=root/'Docs'/name;target=out/name
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.parent!=out:
  folder_meta=target.parent.with_name(target.parent.name+'.meta')
  if not folder_meta.exists():folder_meta.write_text('fileFormatVersion: 2\nguid: '+hashlib.md5(str(target.parent.relative_to(root)).encode()).hexdigest()+'\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n')
 text=source.read_text()
 if name.endswith('.md'):text=text.replace('../Preview/','../../../Preview/')
 target.write_text(text)
 meta=target.with_name(target.name+'.meta')
 if not meta.exists():
  guid=hashlib.md5(str(target.relative_to(root)).encode()).hexdigest()
  meta.write_text('fileFormatVersion: 2\nguid: '+guid+'\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
print('Synchronized Assets-only documentation; repository Docs remains canonical.')
