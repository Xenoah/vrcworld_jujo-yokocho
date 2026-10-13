"""Keep the Assets-only handoff's existing documentation current."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent.parent
out=root/'Assets/TreeTopYokocho/Documentation'
for current in out.glob('*.md'):
 source=root/'Docs'/current.name
 if current.name=='PolyHaven.md':source=root/'Docs/ThirdParty/PolyHaven.md'
 if source.exists():current.write_bytes(source.read_bytes())
for name in ['RELEASE_NOTES_2.6.0.md','IndependentReview_2.6.0.md','AltitudePumps.md','HighCrownStairs.md','CloudSea.md','SceneryDetail.md','validation.json','navigation_validation.json','crown_validation.json','infrastructure_validation.json','stage_validation.json','altitude_validation.json','bark_clearance_validation.json','WindowsProfile.json']:
 source=root/'Docs'/name;target=out/name
 text=source.read_text()
 if name.endswith('.md'):text=text.replace('../Preview/','../../../Preview/')
 target.write_text(text)
 meta=target.with_name(target.name+'.meta')
 if not meta.exists():
  guid=hashlib.md5(str(target.relative_to(root)).encode()).hexdigest()
  meta.write_text('fileFormatVersion: 2\nguid: '+guid+'\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
print('Synchronized Assets-only documentation; repository Docs remains canonical.')
