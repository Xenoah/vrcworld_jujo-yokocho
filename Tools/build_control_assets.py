"""Build original baked Japanese controls and renamed OFL ASCII status font."""
from pathlib import Path
import argparse, hashlib, json, shutil
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools import subset
ROOT=Path(__file__).resolve().parents[1]
def main(baseline):
    source=baseline/'Source/fonts/upstream/kleeone/KleeOne-SemiBold.ttf'
    expected='b031ec426c23ca1143ef1f7d58bee7a79efe119ed654152f121c922202b303fd'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
    assets=ROOT/'Assets/TreeTopYokochoEntrySystems'
    textures=assets/'Textures'; fonts=assets/'Fonts'
    textures.mkdir(parents=True,exist_ok=True);fonts.mkdir(parents=True,exist_ok=True)
    labels=[('時刻 −1h','GLOBAL  /  MANUAL'),('時刻 +1h','GLOBAL  /  MANUAL'),('JST Auto','GLOBAL  /  REAL TIME'),('速度切替','GLOBAL  /  TIME SPEED'),('BGM 入・切','LOCAL  /  ON - OFF'),('次の曲','LOCAL  /  RANDOM MP3')]
    image=Image.new('RGB',(960,304*6),(44,35,27)); draw=ImageDraw.Draw(image)
    title=ImageFont.truetype(str(source),104); small=ImageFont.truetype(str(source),36)
    for i,(jp,en) in enumerate(labels):
        y=i*304
        draw.rounded_rectangle((16,y+16,944,y+288),radius=22,fill=(53,44,34),outline=(164,135,87),width=4)
        draw.text((480,y+124),jp,font=title,anchor='mm',fill=(237,224,184))
        draw.text((480,y+234),en,font=small,anchor='mm',fill=(186,174,142))
    image.save(textures/'entry_control_labels.png')
    font=TTFont(source,recalcTimestamp=False);opts=subset.Options();opts.name_IDs=['*'];opts.name_languages=['*'];opts.recalc_timestamp=False
    sub=subset.Subsetter(options=opts);sub.populate(unicodes=range(32,127));sub.subset(font)
    for rec in font['name'].names:
        if rec.nameID in (1,2,3,4,6,16,17):
            value='Regular' if rec.nameID in (2,17) else ('YokochoEntryStatus-Regular' if rec.nameID==6 else 'Yokocho Entry Status')
            rec.string=value.encode(rec.getEncoding(),errors='replace')
    dest=fonts/'YokochoEntryStatus.ttf';font.save(dest)
    shutil.copyfile(source.parent/'OFL.txt',fonts/'OFL.txt')
    report={'source':str(source.relative_to(baseline)),'sourceSha256':expected,'license':'SIL OFL 1.1','derivedFontName':'Yokocho Entry Status','characterRange':'ASCII U+0020..U+007E','statusFontBytes':dest.stat().st_size,'labelAtlas':[960,1824],'labels':labels,'outputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [dest,fonts/'OFL.txt',textures/'entry_control_labels.png']}}
    (ROOT/'Docs/control_asset_provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('baseline',type=Path);args=parser.parse_args();main(args.baseline)
