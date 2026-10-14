"""Authored pedestrian shop identities, source Z-up, visual geometry only.

Integration:
    make_shopfront_atlas(TEX, font)    # or keep the supplied baked PNG
    add_shopfront_identity(g, P, B, w, dep, idx, M, rng)

Call once per shop IN PLACE OF the old ``noren`` and facade ``sign`` calls.
This owns no colliders, stations, floor geometry, external plants, or lighting.
All low details stay behind the counter and within its horizontal extent.
The eight identities share one 2048 x 2048 RGB texture and three materials.
Fonts are read at authoring time only and are never copied into the asset.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ATLAS_NAME = 'shopfront_identity.png'
ATLAS_SIZE = 2048
TAU = math.tau

IDENTITIES = (
    dict(name='炭火 梢', subtitle='炭火串焼', color=(33, 53, 75), ink=(236, 217, 172),
         wood=(98, 66, 42), signink=(237, 218, 174), menus=('ねぎま', 'つくね', '砂肝', 'ししとう', '炭火焼', '本日仕込'),
         panels=5, kind='branch', mark='炭', width=4.18),
    dict(name='麺処 風待', subtitle='自家製麺', color=(177, 159, 112), ink=(43, 48, 45),
         wood=(52, 67, 69), signink=(237, 222, 181), menus=('醤油麺', '煮玉子', '焼豚', '替え玉', '大盛り', '湯気日和'),
         panels=5, kind='wind', mark='麺', width=4.05),
    dict(name='おでん 灯', subtitle='出汁の香', color=(117, 48, 39), ink=(241, 218, 173),
         wood=(213, 191, 144), signink=(65, 47, 32), menus=('大根', '玉子', '厚揚げ', '蒟蒻', '昆布', '仕込中'),
         panels=3, kind='light', mark='灯', width=3.42),
    dict(name='酒処 根っこ', subtitle='地酒と肴', color=(44, 70, 58), ink=(228, 212, 166),
         wood=(64, 52, 43), signink=(232, 211, 163), menus=('純米', '吟醸', '燗酒', '冷酒', '酒肴', '本日の酒'),
         panels=5, kind='root', mark='酒', width=4.28),
    dict(name='枝先茶屋', subtitle='茶と季節菓子', color=(89, 100, 57), ink=(240, 224, 180),
         wood=(182, 147, 91), signink=(48, 59, 38), menus=('煎茶', '焙じ茶', '抹茶', '甘味', 'お茶請け', 'ひと休み'),
         panels=5, kind='tea', mark='茶', width=4.40),
    dict(name='宵 葉', subtitle='夜風と一杯', color=(37, 48, 66), ink=(223, 204, 164),
         wood=(48, 51, 57), signink=(230, 211, 171), menus=('梅酒', '柚子酒', '小皿', '枝豆', '冷奴', '今宵の酒'),
         panels=4, kind='moon', mark='宵', width=3.28),
    dict(name='山椒屋', subtitle='旬の小皿', color=(115, 42, 34), ink=(238, 216, 167),
         wood=(156, 105, 65), signink=(48, 36, 26), menus=('鶏山椒', '旬野菜', '冷奴', '焼茄子', '山椒味噌', '本日入荷'),
         panels=5, kind='sansho', mark='山', width=3.84),
    dict(name='木の実', subtitle='季節の甘味', color=(177, 160, 115), ink=(71, 60, 38),
         wood=(189, 160, 109), signink=(68, 53, 34), menus=('栗羊羹', '団子', '季節茶', '甘酒', '栗菓子', 'お持帰り'),
         panels=3, kind='nut', mark='菓', width=3.70),
)


def _font(path, size):
    return ImageFont.truetype(str(path), size=size, index=0)


def _crest(d, center, radius, kind, color, bg):
    """Original botanical/lantern emblems; not a texture of fake lettering."""
    cx, cy = center
    def xy(x, y): return (cx + x * radius, cy + y * radius)
    def line(points, width=.07):
        d.line([xy(*p) for p in points], fill=color, width=max(1, round(radius * width)), joint='curve')
    def ellipse(x, y, rx, ry, fill=color, outline=None, width=1):
        d.ellipse((*xy(x-rx,y-ry), *xy(x+rx,y+ry)), fill=fill, outline=outline, width=width)
    def leaf(x, y, dx, dy, scale=.35):
        # Tapered curved botanical silhouette, authored at atlas resolution.
        dx,dy=np.array([dx,dy],float)/math.hypot(dx,dy)*scale
        p=[]
        for i in range(17):
            t=i/16; swell=math.sin(t*math.pi)*.36
            p.append(xy(x+dx*t-dy*swell,y+dy*t+dx*swell))
        for i in range(16,-1,-1):
            t=i/16; swell=math.sin(t*math.pi)*.36
            p.append(xy(x+dx*t+dy*swell,y+dy*t-dx*swell))
        d.polygon(p,fill=color)
    d.ellipse((*xy(-.93,-.93),*xy(.93,.93)), outline=color, width=max(2,round(radius*.065)))
    if kind=='wind':
        for yy,rad in [(-.35,.52),(-.04,.38),(.29,.23)]:
            points=[xy(-.58+1.08*t,yy-.12*math.sin(math.pi*t)) for t in np.linspace(0,1,30)]
            d.line(points,fill=color,width=max(2,round(radius*.08)))
            d.arc((*xy(.24-rad*.25,yy-rad*.42),*xy(.24+rad*.45,yy+rad*.3)),215,440,fill=color,width=max(2,round(radius*.065)))
    elif kind=='light':
        d.rounded_rectangle((*xy(-.42,-.56),*xy(.42,.55)),radius=radius*.24,outline=color,width=max(2,round(radius*.10)))
        line([(-.24,-.67),(.24,-.67)],.11);line([(-.23,.65),(.23,.65)],.11)
        for yy in [-.30,0,.30]:line([(-.33,yy),(.33,yy)],.045)
        ellipse(0,0,.10,.30)
    elif kind=='root':
        line([(0,-.64),(0,.13),(-.38,.59)]);line([(0,.13),(.38,.59)])
        line([(-.12,.30),(-.48,.38),(-.58,.57)],.055);line([(.12,.30),(.48,.38),(.58,.57)],.055)
        leaf(0,-.28,-1,-1,.57);leaf(.02,-.34,1,-1,.54)
    elif kind=='moon':
        ellipse(-.10,-.12,.57,.57)
        ellipse(.17,-.29,.50,.50,bg)
        line([(-.44,.56),(.39,.04)],.045);leaf(-.02,.27,1,-.12,.62);leaf(-.16,.33,-.42,-1,.46)
    elif kind=='nut':
        d.polygon([xy(-.43,.43),xy(-.52,.06),xy(-.25,-.37),xy(0,-.55),xy(.24,-.37),xy(.49,.04),xy(.41,.43)],fill=color)
        d.arc((*xy(-.42,.05),*xy(.43,.67)),182,357,fill=bg,width=max(2,round(radius*.07)))
        line([(0,-.56),(.16,-.73)],.05)
    else:
        angle={'branch':-.15,'tea':0.12,'sansho':.25}[kind]
        line([(-.3,.63),(.17,-.58)],.055)
        if kind=='tea':
            leaf(-.08,.06,-1,-.65,.65);leaf(-.06,.0,1,-.65,.68);leaf(.01,-.07,.15,-1,.64)
        elif kind=='sansho':
            for xx,yy in [(-.19,.36),(-.10,.13),(0,-.11),(.10,-.36)]:
                leaf(xx,yy,-1,-.26,.42);leaf(xx,yy,1,-.32,.40)
        else:
            for xx,yy in [(-.2,.33),(-.07,.01),(.05,-.28)]:
                leaf(xx,yy,-1,-.6,.56);leaf(xx,yy,1,-.1,.49)


def _center_text(d, pos, text, font, fill, max_width=None):
    # Choosing a font size, rather than stretching pixels, preserves readable ink.
    if max_width:
        while d.textbbox((0,0),text,font=font)[2] > max_width and font.size>12:
            font=font.font_variant(size=font.size-1)
    d.text(pos,text,font=font,anchor='mm',fill=fill,stroke_width=0)


def make_shopfront_atlas(out, font=None):
    """Bake one deterministic atlas; Noto fonts stay outside the project."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if font is None or not Path(font).exists():
        for candidate in [Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'),
                          Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]:
            if candidate.exists():font=candidate;break
        else:
            if (out/ATLAS_NAME).exists():return out/ATLAS_NAME
            raise FileNotFoundError('A Japanese OpenType/TrueType font is needed to author shopfront_identity.png')
    # A supplied sans face remains the fallback on portable regeneration.
    signfont=Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc')
    if not signfont.exists():signfont=Path(font)
    rng=np.random.default_rng(30612)
    atlas=Image.new('RGB',(ATLAS_SIZE,ATLAS_SIZE),(205,186,142))
    for idx,item in enumerate(IDENTITIES):
        row=idx*256
        # Each tile gets an eight-pixel bleed gutter. Fine irregular thread and
        # absorption are baked albedo, not painted lighting or fake geometry.
        y,x=np.mgrid[:128,:1024]
        fiber=.982+.014*np.sin(x*2.1)+.014*np.sin(y*2.7)+rng.normal(0,.009,(128,1024))
        uneven=.035*np.sin(x*.018+y*.025)+.025*np.sin(x*.067)
        cloth=np.clip(np.array(item['color'])*(fiber+uneven)[:,:,None],0,255).astype('uint8')
        tile=Image.fromarray(cloth);d=ImageDraw.Draw(tile)
        _crest(d,(512,64),46,item['kind'],item['ink'],item['color'])
        _center_text(d,(775,65),item['name'],_font(signfont,58),item['ink'],350)
        _center_text(d,(199,65),item['subtitle'],_font(font,33),item['ink'],300)
        # Discreet age repairs appear once on a single panel, not as repeated strips.
        if idx in [0,3,5]:
            d.rectangle((84,87,113,104),outline=tuple(int(c*.86) for c in item['color']),width=2)
            for xx in range(87,112,5):d.line((xx,86,xx,91),fill=item['ink'],width=1)
        atlas.paste(tile,(0,row))
        y,x=np.mgrid[:128,:1024]
        grain=.98+.035*np.sin(x*.019+np.sin(y*.17)*.7)+.027*np.sin(y*.52+x*.002)
        grain+=rng.normal(0,.009,(128,1024))
        sign=np.clip(np.array(item['wood'])*grain[:,:,None],0,255).astype('uint8')
        tile=Image.fromarray(sign);d=ImageDraw.Draw(tile)
        # Ink typography is large enough for a meter-scaled pedestrian facade.
        _center_text(d,(520,61),item['name'],_font(signfont,83),item['signink'],675)
        _crest(d,(112,63),43,item['kind'],item['signink'],item['wood'])
        seal=(144,47,33) if idx not in [0,3,5] else (197,123,79)
        d.rectangle((886,40,932,87),outline=seal,width=3)
        _center_text(d,(909,64),item['mark'],_font(font,32),seal)
        # Dark capillary marks and restrained irregular edge wear.
        for x0 in [12,1009]:d.line((x0,14,x0+3,111),fill=tuple(int(c*.66) for c in item['wood']),width=2)
        atlas.paste(tile,(0,row+128))
        # Six independently clipped vertical menu tickets, each with gutters.
        for j,text in enumerate(item['menus']):
            left=1024+j*112
            paper=np.empty((256,112,3),dtype='uint8')
            yy,xx=np.mgrid[:256,:112]
            base=np.array((225-j%2*6,212-j%3*4,175-j%2*5),float)
            shade=.985+rng.normal(0,.007,(256,112))-.05*np.maximum(0,(yy-219)/36)
            paper[:]=np.clip(base*shade[:,:,None],0,255)
            ticket=Image.fromarray(paper);d=ImageDraw.Draw(ticket)
            d.line((14,23,14,232),fill=(181,81,55),width=2)
            f=_font(font,33 if len(text)<5 else 29)
            start=43 if len(text)<5 else 31
            for k,ch in enumerate(text):_center_text(d,(58,start+k*(37 if len(text)<5 else 33)),ch,f,(55,44,31))
            # A ruled foot and small handwritten-style kitchen seal, no made-up price.
            d.line((34,220,82,220),fill=(130,91,54),width=1)
            _center_text(d,(59,235),('おすすめ' if j==0 else '一品'),_font(font,13),(138,66,43),75)
            atlas.paste(ticket,(left,row))
        # Warm paper light and a larger shop emblem share this last square cell.
        y,x=np.mgrid[:256,:256]
        paper=np.array((240,216,170))*(.985+rng.normal(0,.006,(256,256)))[:,:,None]
        tile=Image.fromarray(np.clip(paper,0,255).astype('uint8'));d=ImageDraw.Draw(tile)
        _crest(d,(128,100),65,item['kind'],(92,59,38),(240,216,170))
        _center_text(d,(128,207),item['subtitle'],_font(font,24),(104,68,42),226)
        atlas.paste(tile,(1792,row))
    path=out/ATLAS_NAME;atlas.save(path,optimize=True)
    return path


def _rect(idx, kind, slot=0):
    y=idx*256
    if kind=='cloth':r=(8,y+7,1016,y+121)
    elif kind=='sign':r=(8,y+136,1016,y+248)
    elif kind=='menu':r=(1024+slot*112+8,y+8,1024+(slot+1)*112-8,y+248)
    else:r=(1792+8,y+8,2048-8,y+248)
    return (r[0]/2048,1-r[3]/2048,r[2]/2048,1-r[1]/2048)


def _uv(rect,u,v):
    a,b,c,d=rect
    return (a+(c-a)*u,b+(d-b)*v)


def _front(g,P,x,y,z,width,height,mat,rect,double=False):
    """+Y-facing, text reads correctly from the lane (local -X is screen right)."""
    q=[P(x+width/2,y,z-height/2),P(x-width/2,y,z-height/2),
       P(x-width/2,y,z+height/2),P(x+width/2,y,z+height/2)]
    g.quad(q,mat,[_uv(rect,0,0),_uv(rect,1,0),_uv(rect,1,1),_uv(rect,0,1)],double)


def _materials(g):
    choices={
        'cloth':('ShopfrontTextile',dict(color=(1,1,1),texture=ATLAS_NAME,roughness=1)),
        'ink':('ShopfrontInkWood',dict(color=(1,1,1),texture=ATLAS_NAME,roughness=.96)),
        'lamp':('ShopfrontWashi',dict(color=(1,1,1),texture=ATLAS_NAME,roughness=.94,emission=.28)),
    }
    result={}
    for key,(name,kwargs) in choices.items():
        if name not in g.materials:g.material(name,**kwargs)
        result[key]=name
    return result


def _rolled_entry_noren(g,P,x0,x1,y,width,idx,M,materials,rect):
    """The first panel is deliberately rolled and tied above the staff entry.

    The cloth roll's lowest point is 2.343 m, above the full 2.20 m
    swept headroom envelope. Reuses the original shop's textile atlas.
    """
    verts=[];uv=[];faces=[];nx=20;ny=3
    for j in range(ny+1):
        t=j/ny
        for k in range(nx+1):
            u=k/nx;x=x0+(x1-x0)*u;su=(x+width/2)/width
            fold=.014*math.sin(u*TAU*2+idx*.27)*(1-.5*t)
            verts.append(P(x,y+fold,2.415+.175*t));uv.append(_uv(rect,1-su,.68+.32*t))
            if j and k:
                p=(j-1)*(nx+1)+k-1;q=p+nx+1
                faces.extend([(p,q+1,p+1),(p,q,q+1)])
    g.add(verts,faces,materials['cloth'],uv)
    g.add(verts,[f[::-1] for f in faces],materials['cloth'],uv)
    # Softly compressed textile, rather than a perfectly rigid bamboo cylinder.
    verts=[];uv=[];faces=[];rings=12;sides=18
    for i in range(rings+1):
        u=i/rings;x=x0+(x1-x0)*u;su=(x+width/2)/width
        sag=-.004*math.sin(math.pi*u);radius=.051+.002*math.sin(u*TAU*3+.6)
        for k in range(sides+1):
            a=TAU*k/sides;r=radius*(1+.025*math.sin(a*5+u*7))
            verts.append(P(x,y+.019+r*math.cos(a),2.400+sag+r*math.sin(a)))
            uv.append(_uv(rect,1-su,.18+.45*k/sides))
            if i and k:
                p=(i-1)*(sides+1)+k-1;q=p+sides+1
                faces.extend([(p,p+1,q+1),(p,q+1,q)])
    for ring,reverse in [(0,True),(rings,False)]:
        start=ring*(sides+1);center=len(verts)
        verts.append(P(x0 if ring==0 else x1,y+.019,2.400))
        uv.append(_uv(rect,1-((x0 if ring==0 else x1)+width/2)/width,.40))
        for k in range(sides):
            f=(center,start+k,start+k+1)
            faces.append(f[::-1] if reverse else f)
    g.add(verts,faces,materials['cloth'],uv)
    # Two visible leather ties pass under the roll and back up to the pole.
    for u in [.21,.79]:
        x=x0+(x1-x0)*u
        points=[P(x,y-.028,2.626),P(x,y-.043,2.397),P(x,y+.017,2.336),
                P(x,y+.079,2.400),P(x,y+.029,2.626)]
        for a,b in zip(points,points[1:]):g.beam(a,b,.014,M['dark'],.009)
        g.beam(P(x-.023,y+.081,2.412),P(x+.024,y+.081,2.390),.017,M['dark'],.012)


def _folded_noren(g,P,B,w,dep,idx,M,materials,staff_entry=False):
    item=IDENTITIES[idx];count=item['panels'];width=w-.90;y=dep/2+.135
    rect=_rect(idx,'cloth');phase=idx*.27
    for panel in range(count):
        lo=panel/count;hi=(panel+1)/count
        x0=-width/2+width*lo+.014;x1=-width/2+width*hi-.014
        if staff_entry and panel==0:
            _rolled_entry_noren(g,P,x0,x1,y,width,idx,M,materials,rect)
            continue
        verts=[];uv=[];faces=[];nx=16;ny=5
        for j in range(ny+1):
            t=j/ny
            for k in range(nx+1):
                u=k/nx;x=x0+(x1-x0)*u;su=(x+width/2)/width
                # Gravity-hung panels are restrained at the rod; no free-floating strips.
                fold=(.023*math.sin(u*TAU*1.8+panel*.6+phase)+.010*math.sin(u*TAU*4.0))*(1-.48*t)
                bottom=2.10+.019*math.cos(u*TAU+phase)+.007*math.sin(panel*1.7)
                z=bottom+(2.59-bottom)*t
                verts.append(P(x,y+fold,z));uv.append(_uv(rect,1-su,t))
                if j and k:
                    p=(j-1)*(nx+1)+k-1;q=p+nx+1
                    faces.extend([(p,q+1,p+1),(p,q,q+1)])
        g.add(verts,faces,materials['cloth'],uv)
        g.add(verts,[f[::-1] for f in faces],materials['cloth'],uv)
        # Narrow turned hem follows the true curved lower cloth edge.
        hem=[]
        for k in range(nx+1):
            u=k/nx;x=x0+(x1-x0)*u
            fold=.023*math.sin(u*TAU*1.8+panel*.6+phase)+.010*math.sin(u*TAU*4)
            bottom=2.10+.019*math.cos(u*TAU+phase)+.007*math.sin(panel*1.7)
            hem.append(P(x,y+fold+.001,bottom+.013))
        g.tube(hem,[.0032]*len(hem),M['counter'],4)
        for x in [x0+.10*(x1-x0),x1-.10*(x1-x0)]:
            # Small leather ties use the existing dark material, with no atlas bleed.
            g.beam(P(x,y,2.55),P(x,y,2.647),.028,M['dark'],.016)
    # Bamboo pole, end stops and a pair of real ties tucked beneath the lintel.
    g.beam(P(-width/2-.065,y,2.625),P(width/2+.065,y,2.625),.035,M['counter'])
    for x in [-width/2-.02,width/2+.02]:
        g.beam(P(x,y-.035,2.627),P(x,y-.035,2.735),.014,M['dark'])


def _fascia(g,P,B,w,dep,idx,M,materials):
    item=IDENTITIES[idx];ww=min(item['width'],w-.66);hh=.47 if idx!=2 else .50
    yy=dep/2+.56;zz=3.14
    # Slightly unequal edges make a thick timber sign, rather than a pasted strip.
    outline=[(-ww/2+.035,-hh/2),(-ww*.27,-hh/2-.009),(ww/2-.025,-hh/2+.007),
             (ww/2,hh/2-.028),(ww*.28,hh/2+.006),(-ww/2+.01,hh/2-.003)]
    rear=yy-.096
    # The board sits ahead of the sloped tiles, inside the existing eave
    # envelope, so its lower lettering stays visible from a 1.7m eye height.
    B(0,rear,zz,ww+.10,.065,hh+.105,M['dark'])
    for side in [-1,1]:
        B(side*(ww/2-.15),rear-.045,zz,.07,.036,hh+.16,M['wood'])
    for k,(x,z) in enumerate(outline):
        x1,z1=outline[(k+1)%len(outline)]
        g.quad([P(x,rear,zz+z),P(x1,rear,zz+z1),P(x1,yy,zz+z1),P(x,yy,zz+z)],M['wood'],double=True)
    # Front texture stays planar and correctly oriented; surround exposes bevels.
    _front(g,P,0,yy+.002,zz,ww-.045,hh-.035,materials['ink'],_rect(idx,'sign'))
    # Corner joinery, inset dark end-grain blocks and subdued bronze fasteners.
    for side in [-1,1]:
        B(side*(ww/2-.060),yy-.014,zz,.024,.054,hh-.025,M['dark'])
        for z in [-hh*.33,hh*.33]:
            g.tube([P(side*(ww/2-.097),yy+.003,zz+z),P(side*(ww/2-.097),yy+.014,zz+z)],[.009,.009],M['iron'],8)
    # Different framing silhouettes preserve an artisan family without copying eight signs.
    if idx in [0,3,5]:
        for z in [-hh/2-.035,hh/2+.035]:B(0,yy-.037,zz+z,ww+.15,.11,.032,M['dark'])
    elif idx in [1,6]:
        for side in [-1,1]:B(side*(ww/2+.053),yy-.028,zz,.047,.09,hh+.12,M['wood'])
    else:
        B(0,yy-.03,zz+hh/2+.040,ww+.18,.16,.038,M['counter'])


def _tickets_and_lamp(g,P,B,w,dep,idx,M,materials,staff_entry=False):
    # Paper menus are behind the counter, leaving both shop-end exits clear.
    count=3 if idx in [2,5,7] else 4
    center=(w-1.7)*.25 if idx%2==0 else -(w-1.7)*.25
    y=dep/2-.52
    g.beam(P(center-.48,y-.025,2.34),P(center+.48,y-.025,2.34),.035,M['dark'])
    for side in [-1,1]:g.beam(P(center+side*.40,y-.04,2.34),P(center+side*.40,y-.04,2.60),.012,M['iron'])
    for j in range(count):
        x=center+(j-(count-1)/2)*.23;h=.435+.018*((idx+j)%3);z=1.865-.009*(j%2)
        # A bent lower edge catches light and distinguishes tickets from a texture plane.
        rect=_rect(idx,'menu',(j+idx%2)%6);ww=.158
        points=[];uv=[];faces=[]
        for k in range(5):
            t=k/4;zz=z-h/2+h*t;bow=.016*(1-t)**2
            for side,u in [(1,0),(-1,1)]:
                points.append(P(x+side*ww/2,y+bow,zz));uv.append(_uv(rect,u,t))
            if k:
                a=(k-1)*2;faces.extend([(a,a+1,a+3),(a,a+3,a+2)])
        g.add(points,faces,materials['ink'],uv)
        g.add(points,[f[::-1] for f in faces],materials['ink'],uv)
        g.beam(P(x,y,2.34),P(x,y,z+h/2-.025),.014,M['iron'])
        B(x,y+.008,z+h/2-.014,.062,.025,.020,M['dark'])
    # A small guarded washi counter lantern rests on the existing counter.
    # It stays clear of the door route: its full width is inside the counter end.
    x=(w-1.3)/2-.18 if staff_entry else (-(w-1.3)/2+.18 if idx%2==0 else (w-1.3)/2-.18)
    y=dep/2-.30;z=1.251;ww=.21;hh=.37
    B(x,y-.045,z,.255,.19,.425,M['dark'])
    _front(g,P,x,y+.055,z,ww,hh,materials['lamp'],_rect(idx,'lamp'))
    for dx in [-ww/2,ww/2]:B(x+dx,y+.068,z,.018,.027,hh+.048,M['wood'])
    for dz in [-hh/2,hh/2]:B(x,y+.068,z+dz,ww+.027,.027,.019,M['wood'])
    B(x,y-.012,z+hh/2+.040,ww+.090,.23,.028,M['dark'])
    # A tiny access-door hinge is visibly part of the lamp body.
    B(x+ww*.39,y+.070,z-.10,.025,.015,.060,M['iron'])


def add_shopfront_identity(g,P,B,w,dep,idx,M,rng=None,staff_entry=False,noren_craft=False):
    """Replace generic fascia/noren; return measured visual-only addition counts."""
    if not 0<=idx<len(IDENTITIES):raise ValueError('shop index must be 0..7')
    before=sum(len(b['f']) for b in g.batches.values());old_group=g.group
    # A child group keeps identity geometry independently inspectable in Blender/Unity.
    g.group=old_group+'/Identity'
    materials=_materials(g)
    if noren_craft is True:
        from noren_craft import add_crafted_noren
        add_crafted_noren(g,P,B,w,dep,idx,M,materials,staff_entry=staff_entry)
    else:
        _folded_noren(g,P,B,w,dep,idx,M,materials,staff_entry=staff_entry)
    _fascia(g,P,B,w,dep,idx,M,materials)
    _tickets_and_lamp(g,P,B,w,dep,idx,M,materials,staff_entry=staff_entry)
    g.group=old_group
    return {'name':IDENTITIES[idx]['name'],'triangles':sum(len(b['f']) for b in g.batches.values())-before,
            'atlas':ATLAS_NAME,'collisionChanges':0,'stationChanges':0}


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser();parser.add_argument('texture_directory');parser.add_argument('--font')
    args=parser.parse_args();path=make_shopfront_atlas(args.texture_directory,args.font)
    print(json.dumps({'atlas':str(path),'size':[2048,2048],'bytes':path.stat().st_size,'shops':8},ensure_ascii=False))
