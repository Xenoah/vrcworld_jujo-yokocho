"""Recreate renamed OFL authoring subsets from pinned installed Noto JP faces.
Optional maintenance tool: requires fonttools; not used by normal world builds.
"""
from pathlib import Path
import hashlib,json
from fontTools.ttLib import TTFont
from fontTools import subset
import fontTools
if fontTools.__version__ != "4.61.1":raise RuntimeError("Subset reproduction requires fonttools==4.61.1")
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'fonts';OUT.mkdir(exist_ok=True)
pinned=json.loads((OUT/'rpg-fonts.json').read_text())
text=(ROOT/'rpg_shop_identities.py').read_text()+''.join(chr(i) for i in range(32,127))
manifest=dict(format=1,license='SIL Open Font License 1.1',upstream='https://github.com/notofonts/noto-cjk',sourceLicenseUrls=['https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE','https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/LICENSE'],modification='Japanese collection face 0 subset to authored sign characters; primary and PostScript names changed to Yokocho Sign. Original glyph outlines preserved.',faces={})
for family in ['Sans','Serif']:
 for weight in ['Regular','Bold']:
  key=family+'-'+weight;source=Path('/usr/share/fonts/opentype/noto')/('Noto'+family+'CJK-'+weight+'.ttc')
  if hashlib.sha256(source.read_bytes()).hexdigest()!=pinned['faces'][key]['sourceSha256']:
   raise ValueError('Pinned Noto source hash mismatch: '+str(source))
  f=TTFont(source,fontNumber=0,recalcTimestamp=False)
  original={str(n.nameID):n.toUnicode() for n in f['name'].names if n.platformID==3 and n.nameID in [0,1,2,3,4,5,6,13,14]}
  cmap=f.getBestCmap();chars={ord(c) for c in text if c in '\n\r\t' or ord(c) in cmap}
  required={ord(c) for c in text if ord(c)>127 and not c.isspace()}
  missing=required-set(cmap)
  if missing:raise ValueError('Missing characters: '+''.join(map(chr,sorted(missing))))
  opts=subset.Options();opts.name_IDs=['*'];opts.name_legacy=True;opts.name_languages=['*'];opts.recalc_timestamp=False
  sub=subset.Subsetter(options=opts);sub.populate(unicodes=chars);sub.subset(f)
  names={1:'Yokocho Sign '+family,2:weight,3:'YokochoSign-'+key+'-1',4:'Yokocho Sign '+family+' '+weight,6:'YokochoSign-'+key,16:'Yokocho Sign '+family,17:weight}
  for n in f['name'].names:
   if n.nameID in names:n.string=names[n.nameID].encode(n.getEncoding())
  if 'CFF ' in f:
   c=f['CFF '].cff;c.fontNames=['YokochoSign-'+key]
   c.topDictIndex[0].FamilyName=names[1];c.topDictIndex[0].FullName=names[4]
  f['head'].created=f['head'].modified=2082844800
  dest=OUT/('YokochoSign-'+key+'.otf');f.save(dest)
  manifest['faces'][key]=dict(file=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),sourceFile=source.name,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),collectionFace=0,originalMetadata=original,codepoints=sorted(f.getBestCmap()))
(OUT/'rpg-fonts.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
license=Path('/usr/share/doc/fonts-noto-cjk/copyright').read_text().split('License: SIL-1.1\n',2)[-1].split('\nLicense: GPL-3+')[0]
license='\n'.join('' if line.strip()=='.' else line.removeprefix(' ') for line in license.splitlines())
(OUT/'OFL.txt').write_text('Noto Sans CJK JP: © 2014–2021 Adobe (http://www.adobe.com/).\nNoto Serif CJK JP: © 2017–2024 Adobe (http://www.adobe.com/).\n\nYokocho Sign is a renamed subset derivative.\n\n'+license+'\n')
print({k:v['sha256'] for k,v in manifest['faces'].items()})
