"""Eight original RPG sign identities; deterministic authoring, no runtime fonts.

Only the two venue atlases' enumerated rectangles are replaced. No geometry,
lighting, menus, collision or station data is authored here. Text is rasterized
without anisotropic scaling; UV windows match each physical sign's aspect.
"""
from pathlib import Path
import hashlib, json, math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

VERSION='rpg-sign-identities-1'
BASELINE_HASHES={'food_venue_signs.png': '8b1d80cdb5e36e99909e1445fdeafc9f36d658309e859e17a3db650bb6ea38e3', 'nightlife_signs.png': '6e3f8b87834b04ac4c818b7ffb05d3dbcf7780254999e539fddaadf47fb09d48'}
FONT_DIR=Path(__file__).with_name('fonts')
FOOD_IDS=(0,1,2,4,7)
NIGHT_IDS=(3,5,6)
# Original names, each kept in full on the principal shopfront sign.
IDENTITIES={
 0:dict(name='竜の熾火亭',sub='炭火串焼',face='Serif-Bold',bg=(43,30,25),ink=(245,219,170),accent=(186,102,62),crest='dragon',tracking=.025,style='ember-carved'),
 1:dict(name='風渡りの麺工房',sub='自家製麺と旅の腹ごしらえ',face='Merchant',bg=(228,233,215),ink=(28,71,71),accent=(61,130,135),crest='wind',tracking=.00,style='wind-enamel'),
 2:dict(name='旅人の燈火亭',sub='出汁とおでん',face='Serif-Bold',bg=(96,40,35),ink=(249,225,176),accent=(196,145,84),crest='lantern',tracking=.065,style='traveler-parchment'),
 3:dict(name='宵闇の魔女',sub='夜語りと小さな一杯',face='Serif-Regular',bg=(48,24,51),ink=(242,218,239),accent=(176,124,181),crest='witch',tracking=.14,style='witch-lacquer'),
 4:dict(name='月詠みの茶房',sub='月を待つ茶と季節菓子',face='Serif-Regular',bg=(30,67,61),ink=(233,232,199),accent=(137,180,158),crest='moon',tracking=.19,style='moon-jade'),
 5:dict(name='星屑の蒸留所',sub='COCKTAIL & WHISKY',face='Engraved',bg=(19,43,57),ink=(208,239,234),accent=(127,180,180),crest='star',tracking=.105,style='stellar-deco'),
 6:dict(name='吟遊詩人の隠れ家',sub='音楽と珈琲と酒',face='Serif-Bold',bg=(30,35,55),ink=(236,220,170),accent=(176,145,86),crest='lyre',tracking=.045,style='bard-gilt'),
 7:dict(name='妖精の菓子工房',sub='季節の甘味と贈りもの',face='Storybook',bg=(241,224,190),ink=(112,49,72),accent=(171,113,122),crest='fairy',tracking=.04,style='fairy-confection'),
}
ASPECTS={0:3.75/.45,1:3.30/.48,2:2.70/.43,3:1.85/.44,4:3.55/.32,5:1.99/.49,6:2.63/.40,7:2.25/.43}


def name_rect(idx):
    """Pixel-space UV window, top-left origin; nearest integer ratio <0.4%."""
    if idx in FOOD_IDS:
        cy=FOOD_IDS.index(idx)*384+78
        h=110 if idx==4 else 120
        w=round(h*ASPECTS[idx]);cx=650
        return (cx-w//2,cy-h//2,cx-w//2+w,cy-h//2+h)
    slot=NIGHT_IDS.index(idx);w=480;h=round(w/ASPECTS[idx]);cx=slot*512+256;cy=258
    return (cx-w//2,cy-h//2,cx+w//2,cy-h//2+h)


def emblem_rect(idx):
    row=FOOD_IDS.index(idx);aspect={0:.54/.59,1:1,2:.23/.29,4:.40/.65,7:.55/.66}[idx]
    h=320;w=round(h*aspect);return (1576-w//2,row*384+20,1576-w//2+w,row*384+340)


def food_rect(idx,kind):
    if kind=='name':return uv(name_rect(idx))
    if kind=='emblem':return uv(emblem_rect(idx))
    return None


def night_rect(slot,size):
    """Dedicated portrait and crest regions avoid squeezing square artwork."""
    if slot not in (0,1,2):return None
    w,h=size
    if w/h>2.1:return uv(name_rect(NIGHT_IDS[slot]))
    if slot==1 and w/h<.7:return uv((512+213,10,512+299,195))
    if slot==2 and .9<w/h<1.1:return uv((1024+184,350,1024+328,494))
    return None


def uv(r):
    x0,y0,x1,y1=r
    return (x0/2048,1-y1/2048,x1/2048,1-y0/2048)


@lru_cache(maxsize=1)
def _font_manifest():
    p=FONT_DIR/'rpg-fonts.json'
    return json.loads(p.read_text())


@lru_cache(maxsize=64)
def font(face,size):
    spec=_font_manifest()['faces'][face];path=FONT_DIR/spec['file']
    if not path.is_file():raise FileNotFoundError('RPG sign font missing: '+str(path)+'; restore the bundled OFL fonts, never substitute a non-CJK face')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['sha256']:raise ValueError('RPG sign font hash mismatch: '+spec['file'])
    return ImageFont.truetype(str(path),size=size)


def _text(d,center,text,face,size,ink,maxwidth,tracking=0):
    """Fit by changing point size only; tracking is designed, not stretching."""
    while size>8:
        f=font(face,size);gap=round(size*tracking)
        advances=[d.textlength(c,font=f) for c in text]
        width=sum(advances)+gap*(len(text)-1)
        if width<=maxwidth:break
        size-=1
    x=center[0]-width/2
    positions=[];boxes=[]
    for ch,advance in zip(text,advances):
        positions.append(x)
        boxes.append(d.textbbox((x,center[1]),ch,font=f,anchor='lm'))
        x+=advance+gap
    # Preserve a common baseline but align the visible ink, not the font em box.
    # Different CJK families have different ascender metrics.
    dy=center[1]-(min(b[1] for b in boxes)+max(b[3] for b in boxes))/2
    boxes=[]
    for ch,x in zip(text,positions):
        pos=(x,center[1]+dy)
        boxes.append(d.textbbox(pos,ch,font=f,anchor='lm'))
        d.text(pos,ch,font=f,anchor='lm',fill=ink)
    return dict(text=text,face=face,size=size,tracking=gap,inkBounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)])


def _crest(d,c,r,kind,ink,bg):
    x,y=c
    def p(a,b):return(x+a*r,y+b*r)
    def line(pts,w=.09):d.line([p(*q) for q in pts],fill=ink,width=max(1,round(r*w)),joint='curve')
    def oval(a,b,c,e,fill=None,width=.07):d.ellipse((*p(a,b),*p(c,e)),fill=fill,outline=ink,width=max(1,round(r*width)))
    if kind=='dragon':
        line([(-.55,.6),(-.1,.50),(.22,.17),(-.12,-.14),(.12,-.45),(.53,-.40),(.34,-.72),(.04,-.64),(-.38,-.25),(-.21,.18),(-.56,.45)],.16)
        d.polygon([p(-.12,-.14),p(-.80,-.46),p(-.52,.14)],fill=ink)
        d.polygon([p(.52,-.21),p(.77,-.46),p(.73,.02),p(.45,.22)],fill=ink)
    elif kind=='wind':
        for yy in [-.43,0,.43]:
            pts=[p(-.83+i*.08,yy-.13*math.sin(i*.20)) for i in range(20)]
            d.line(pts,fill=ink,width=max(1,round(r*.10)))
    elif kind=='lantern':
        d.rounded_rectangle((*p(-.46,-.55),*p(.46,.56)),radius=r*.20,outline=ink,width=max(1,round(r*.08)))
        line([(-.30,-.70),(.30,-.70)]);line([(-.31,.71),(.31,.71)])
        line([(0,-.42),(-.17,.2),(0,.40),(.17,.2),(0,-.42)],.10)
    elif kind in ('moon','witch'):
        oval(-.66,-.70,.64,.60,ink);d.ellipse((*p(-.24,-.84),*p(.78,.36)),fill=bg)
        if kind=='witch':
            d.polygon([p(-.1,.18),p(.15,-.63),p(.47,.18)],fill=ink);line([(-.32,.2),(.66,.2)],.12)
        else:line([(-.75,.80),(.67,.80)],.07)
    elif kind=='star':
        d.polygon([p(0,-.83),p(.20,-.23),p(.81,0),p(.20,.23),p(0,.83),p(-.20,.23),p(-.81,0),p(-.20,-.23)],fill=ink)
        oval(-.35,-.35,.35,.35,None,.035)
    elif kind=='lyre':
        line([(-.59,-.62),(-.46,.25),(-.18,.65),(.18,.65),(.46,.25),(.59,-.62)],.13)
        line([(-.6,-.58),(.6,-.58)],.09)
        for xx in [-.24,0,.24]:line([(xx,-.54),(xx,.47)],.045)
    elif kind=='fairy':
        for a,b,c,e in [(-.80,-.60,-.07,.12),(.07,-.60,.80,.12),(-.60,.05,-.04,.60),(.04,.05,.60,.60)]:oval(a,b,c,e,None,.075)
        line([(0,-.43),(0,.62)],.10);oval(-.12,-.63,.12,-.39,ink)


def _sign(idx,size):
    """Author at 4x then area-downsample isotropically; no baked lighting."""
    s=4;w,h=size;W,H=w*s,h*s;item=IDENTITIES[idx];bg=item['bg'];ink=item['ink'];accent=item['accent']
    im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
    margin=H*.10
    if idx in (0,2):
        # Hammered end rules, left open so actual shaped silhouettes stay clean.
        for yy in [.15,.85]:d.line((W*.09,H*yy,W*.91,H*yy),fill=accent,width=max(2,round(H*.017)))
    elif idx==1:
        d.rounded_rectangle((H*.12,H*.10,W-H*.12,H*.90),radius=H*.30,outline=accent,width=round(H*.025))
    elif idx==3:
        for yy in [.12,.88]:d.line((W*.17,H*yy,W*.83,H*yy),fill=accent,width=round(H*.012))
        for xx in [.12,.88]:d.polygon([(W*xx,H*.45),(W*xx+H*.05,H*.5),(W*xx,H*.55),(W*xx-H*.05,H*.5)],fill=accent)
    elif idx==4:
        for yy in [.08,.92]:d.line((W*.06,H*yy,W*.94,H*yy),fill=accent,width=round(H*.014))
    elif idx==5:
        for yy in [.09,.91]:d.line((H*.22,H*yy,W-H*.22,H*yy),fill=accent,width=round(H*.018))
        for xx in [H*.22,W-H*.22]:d.line((xx,H*.09,xx,H*.91),fill=accent,width=round(H*.018))
    elif idx==6:
        for yy in [.11,.89]:d.line((W*.06,H*yy,W*.94,H*yy),fill=accent,width=round(H*.022))
    # Original crest and typography: each arrangement is authored separately.
    cr=H*(.27 if idx!=7 else .20);cx=H*(.72 if idx!=7 else .80)
    _crest(d,(cx,H*.50),cr,item['crest'],accent,bg)
    left=H*1.20;right=W-H*.44
    if idx==3:left=H*1.13;right=W-H*.65
    if idx==7:left=H*1.10;right=W-H*.72
    size0=round(H*({0:.61,1:.64,2:.57,3:.52,4:.64,5:.57,6:.53,7:.50}[idx]))
    info=_text(d,((left+right)/2,H*(.53 if idx!=7 else .59)),item['name'],item['face'],size0,ink,right-left,item['tracking'])
    info['inkBounds']=[v/s for v in info['inkBounds']];info['size']/=s;info['tracking']/=s
    return im.resize((w,h),Image.Resampling.BOX),info


def owned_rectangles(atlas):
    if atlas=='food_venue_signs.png':
        out=[name_rect(i) for i in FOOD_IDS]
        # Subtitles and existing square emblems only. Menus stay exact.
        out += [(10,r*384+152,1290,r*384+225) for r in range(5)]
        out += [(1410,r*384+12,1742,r*384+348) for r in range(5)]
        return out
    if atlas=='nightlife_signs.png':return [name_rect(i) for i in NIGHT_IDS]+[(725,10,811,195),(1208,350,1352,494),(552,700,984,826)]
    raise ValueError(atlas)


def apply_atlas(path):
    path=Path(path);im=Image.open(path).convert('RGB')
    if im.size!=(2048,2048):raise ValueError('RPG atlas requires unchanged 2048 square dimensions')
    atlas=path.name;ids=FOOD_IDS if atlas=='food_venue_signs.png' else NIGHT_IDS if atlas=='nightlife_signs.png' else ()
    if not ids:raise ValueError(atlas)
    entries=[]
    for idx in ids:
        r=name_rect(idx);tile,metric=_sign(idx,(r[2]-r[0],r[3]-r[1]));im.paste(tile,r[:2]);entries.append(dict(shop=f'S{idx+1:02d}',rect=r,**metric))
        if idx in FOOD_IDS:
            row=FOOD_IDS.index(idx);item=IDENTITIES[idx]
            subrect=(10,row*384+152,1290,row*384+225);tile=Image.new('RGB',(1280,73),item['bg']);d=ImageDraw.Draw(tile)
            _text(d,(640,37),item['sub'],'Sans-Regular',39,item['ink'],1200,.09);im.paste(tile,subrect[:2])
            # Clear the former glyph, then render an aspect-correct crest crop.
            im.paste(item['bg'],(1410,row*384+12,1742,row*384+348))
            er=emblem_rect(idx);ew,eh=er[2]-er[0],er[3]-er[1]
            tile=Image.new('RGB',(ew*4,eh*4),item['bg']);d=ImageDraw.Draw(tile)
            _crest(d,(ew*2,eh*2),min(ew,eh)*1.48,item['crest'],item['ink'],item['bg'])
            im.paste(tile.resize((ew,eh),Image.Resampling.BOX),er[:2])
    if atlas=='nightlife_signs.png':
        # Remove the obsolete cocktail name from the secondary menu header.
        tile=Image.new('RGB',(432*4,126*4),(202,186,148));d=ImageDraw.Draw(tile)
        _text(d,(864,252),'星屑の一杯','Engraved',180,(52,45,34),1580,.02)
        im.paste(tile.resize((432,126),Image.Resampling.BOX),(552,700))
        # Portrait side sign: complete name vertically, not a stretched title.
        item=IDENTITIES[5];tile=Image.new('RGB',(86*4,185*4),item['bg']);d=ImageDraw.Draw(tile)
        for k,ch in enumerate(item['name']):_text(d,(172,70+k*112),ch,item['face'],92,item['ink'],300)
        im.paste(tile.resize((86,185),Image.Resampling.BOX),(725,10))
        item=IDENTITIES[6];tile=Image.new('RGB',(576,576),item['bg']);d=ImageDraw.Draw(tile);_crest(d,(288,288),220,'lyre',item['ink'],item['bg'])
        im.paste(tile.resize((144,144),Image.Resampling.BOX),(1208,350))
    im.save(path,optimize=True)
    return dict(version=VERSION,atlas=atlas,entries=entries,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pixelSha256=hashlib.sha256(im.tobytes()).hexdigest(),fonts=_font_manifest())


def contact_sheet(out):
    canvas=Image.new('RGB',(1600,960),(20,25,33));d=ImageDraw.Draw(canvas)
    for idx in range(8):
        x=(idx%2)*800;y=(idx//2)*240;item=IDENTITIES[idx]
        _text(d,(x+400,y+24),f'S{idx+1:02d}  '+item['name'],'Sans-Regular',20,(221,225,231),760)
        w=740;h=round(w/ASPECTS[idx]);tile,_=_sign(idx,(w,h));canvas.paste(tile,(x+30,y+56+(140-h)//2))
        _text(d,(x+400,y+216),item['sub'],'Sans-Regular',17,(155,170,184),740)
    canvas.save(out)


def restore_baseline(out,atlas):
    """Restore the pinned original atlas, never mistake an RPG output for legacy."""
    import shutil
    base=Path(__file__).parent/'testdata/rpg_signs_baseline'
    hashes=json.loads((base/'manifest.json').read_text());source=base/atlas
    if hashes!=BASELINE_HASHES:raise ValueError('Legacy atlas manifest changed')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=hashes[atlas]:raise ValueError('Legacy sign atlas hash mismatch: '+atlas)
    out=Path(out);out.mkdir(parents=True,exist_ok=True);dest=out/atlas
    shutil.copyfile(source,dest)
    return dict(atlas=atlas,texture=atlas,rebaked=False,width=2048,height=2048,bytes=dest.stat().st_size,sha256=hashes[atlas],source='pinned-original-v2.16-atlas')


def bake(out,atlas):
    restore_baseline(out,atlas)
    return apply_atlas(Path(out)/atlas)
