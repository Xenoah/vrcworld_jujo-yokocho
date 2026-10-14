"""Uniformly downsample and label actual source-render frames; no scene editing."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
from rpg_shop_identities import IDENTITIES
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
# Presentation-only labels do not affect reproducible baked scene typography.
f=ImageFont.truetype(font,25);small=ImageFont.truetype(font,18);title=ImageFont.truetype(font,31)
width=1600;cw=800;ch=541;header=94;footer=64
canvas=Image.new('RGB',(width,header+4*ch+footer),(21,24,29));d=ImageDraw.Draw(canvas)
d.text((24,15),'樹上横丁 · RPGの店名と、それぞれの灯り',font=title,fill=(244,235,216))
d.text((24,61),'実モデルの Blender プレビュー / Unity・VRChat 実機映像ではありません',font=small,fill=(188,201,210))
rows=[];geometry=set()
for i in range(8):
 sid=f'S{i+1:02d}';p=a.input/f'Blender_survey_{sid}.png'
 preferred=a.input/f'Blender_rpg_{sid}_front.png'
 if preferred.exists():p=preferred
 meta=p.with_suffix('.json');m=json.loads(meta.read_text())
 if m.get('denoising','none')=='none':raise ValueError('Use reviewed guide-denoised image: '+str(p))
 im=Image.open(p).convert('RGB');assert im.size==(1120,700)
 x=(i%2)*cw;y=header+(i//2)*ch;canvas.paste(im.resize((cw,500),Image.Resampling.LANCZOS),(x,y))
 d.text((x+14,y+504),sid+'  '+IDENTITIES[i]['name'],font=f,fill=(242,233,217));geometry.add(m['geometry_sha256'])
 rows.append(dict(shop=sid,image=p.name,imageSha256=hashlib.sha256(p.read_bytes()).hexdigest(),metadataSha256=hashlib.sha256(meta.read_bytes()).hexdigest(),geometrySha256=m['geometry_sha256'],camera=m['camera'],target=m['target'],lens=m['lens_mm'],lightingProfileSha256=m['source_sha256']['Assets/TreeTopYokocho/Data/VenueLighting.json']))
assert len(geometry)==1
assert len({x['lightingProfileSha256'] for x in rows})==1
d.text((24,header+4*ch+12),'露出・空気感は共通。既存の店内照明だけを各店の配色へ変更。実際のUnityベイクは未検証。',font=small,fill=(188,201,210))
a.output.parent.mkdir(parents=True,exist_ok=True);canvas.save(a.output)
report=dict(scope='Contact sheet of actual-model Blender source previews. Uniform downsampling and labels only, no scene synthesis or repaint.',outputSha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),inputs=rows,approximation='Cycles live point lights and camera-only emission differ from Unity baked lights/probes; no runtime validation.')
a.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(a.output)
