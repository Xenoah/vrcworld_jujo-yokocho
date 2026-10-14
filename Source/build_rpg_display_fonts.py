"""Subset pinned, bundled upstream OFL fonts. Maintenance only; fontTools needed."""
from pathlib import Path
import json,hashlib
from fontTools.ttLib import TTFont
from fontTools import subset
import fontTools
if fontTools.__version__ != "4.61.1":raise RuntimeError("Subset reproduction requires fonttools==4.61.1")
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'fonts';manifest=json.loads((OUT/'rpg-fonts.json').read_text())
for key,folder,file,weight in [('Merchant','kleeone','KleeOne-SemiBold.ttf','SemiBold'),('Storybook','kleeone','KleeOne-Regular.ttf','Regular'),('Engraved','kaiseidecol','KaiseiDecol-Medium.ttf','Medium')]:
 source=OUT/'upstream'/folder/file
 pin=json.loads((OUT/'rpg-upstream-pins.json').read_text())[key]
 if hashlib.sha256(source.read_bytes()).hexdigest()!=pin['sourceSha256']:raise ValueError('Pinned display source hash mismatch: '+str(source))
 if hashlib.sha256((source.parent/'OFL.txt').read_bytes()).hexdigest()!=pin['licenseSha256']:raise ValueError('Pinned license hash mismatch: '+folder)
 f=TTFont(source,recalcTimestamp=False)
 text=(ROOT/'rpg_shop_identities.py').read_text()+''.join(chr(i) for i in range(32,127))
 cmap=f.getBestCmap();chars={ord(c) for c in text if ord(c) in cmap}
 missing={ord(c) for c in text if ord(c)>127 and not c.isspace()}-set(cmap)
 if missing:raise ValueError('Missing characters '+''.join(map(chr,sorted(missing))))
 original={str(n.nameID):n.toUnicode() for n in f['name'].names if n.platformID==3 and n.nameID in [0,1,2,3,4,5,6,13,14]}
 opts=subset.Options();opts.name_IDs=['*'];opts.name_legacy=True;opts.name_languages=['*'];opts.recalc_timestamp=False
 sub=subset.Subsetter(options=opts);sub.populate(unicodes=chars);sub.subset(f)
 names={1:'Yokocho '+key,2:weight,3:'Yokocho-'+key+'-1',4:'Yokocho '+key+' '+weight,6:'Yokocho-'+key,16:'Yokocho '+key,17:weight}
 for n in f['name'].names:
  if n.nameID in names:n.string=names[n.nameID].encode(n.getEncoding())
 f['head'].created=f['head'].modified=2082844800
 dest=OUT/('Yokocho-'+key+'.ttf');f.save(dest)
 manifest['faces'][key]=dict(file=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),sourceFile='upstream/'+folder+'/'+file,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceUrl='https://raw.githubusercontent.com/google/fonts/main/ofl/'+folder+'/'+file,licenseFile='upstream/'+folder+'/OFL.txt',licenseSha256=hashlib.sha256((source.parent/'OFL.txt').read_bytes()).hexdigest(),originalMetadata=original,codepoints=sorted(f.getBestCmap()))
(OUT/'rpg-fonts.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
