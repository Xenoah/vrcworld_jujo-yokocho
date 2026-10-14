"""Five separately authored food venues. Local Z-up, metres; no global state.

This module replaces, rather than decorates, the former shared shop shell.
Shop IDs 01/02/03/05/08 only. External floor/guards and reference footprints
remain owned by the world builder. This module emits proposed local solids and
station changes for explicit integration review, never silently changes physics.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

VERSION='food-venues-v6'
SHOP_IDS=(0,1,2,4,7)
ATLAS_NAME='food_venue_signs.png'
# name, subtitle, sign background, ink, menu. Original names, no trade marks.
IDENTITIES={
 0:('炭火 梢','串焼と炭火',(48,35,24),(235,218,177),'ねぎま　つくね　砂肝'),
 1:('麺処 風待','自家製麺',(238,227,197),(35,65,64),'醤油麺　煮玉子　替え玉'),
 2:('おでん 灯','出汁の香',(111,38,28),(248,222,170),'大根　玉子　厚揚げ'),
 4:('枝先茶屋','茶と季節菓子',(202,184,134),(42,63,42),'煎茶　抹茶　季節菓子'),
 7:('木の実','季節の甘味',(233,207,151),(83,49,35),'栗羊羹　団子　甘酒'),
}

def _material_specs():
    """Material descriptors keyed by unique material name (no legacy mutation)."""
    return {
     'Food_Sign':dict(color=(1,1,1),texture=ATLAS_NAME,roughness=.9),
     'Food_Paper':dict(color=(1,.90,.69),texture='',roughness=.8,emission=.40),
     'Food_Enamel':dict(color=(.75,.84,.78),texture='',roughness=.27),
     'Food_TileCream':dict(color=(.86,.80,.65),texture='',roughness=.33),
     'Food_TileGreen':dict(color=(.10,.27,.25),texture='',roughness=.25),
     'Food_Oxblood':dict(color=(.35,.064,.038),texture='',roughness=.55),
     'Food_Charcoal':dict(color=(.075,.065,.052),texture='',roughness=.95),
     'Food_Reed':dict(color=(.58,.45,.25),texture='PBR/wood_planks_grey_diff_4k.jpg',roughness=.92,uvScale=1.0),
     'Food_PaleJoinery':dict(color=(.91,.83,.64),texture='PBR/wood_planks_grey_diff_4k.jpg',roughness=.75,uvScale=.7),
     'Food_Chestnut':dict(color=(.57,.31,.15),texture='PBR/wood_table_001_diff_4k.jpg',roughness=.77,uvScale=.7),
     'Food_Upholstery':dict(color=(.30,.35,.21),texture='woven.png',roughness=1),
     'Food_Copper':dict(color=(.52,.26,.10),texture='',roughness=.45,metallic=.7),
    }

def material_specs():
    return [dict(key=name,name=name,**spec) for name,spec in _material_specs().items()]


def bake_textures(out,font=None,*,rpg_identity=False):
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    if rpg_identity is True:
        from rpg_shop_identities import bake
        return bake(out,ATLAS_NAME)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    regular=Path(font) if font and Path(font).exists() else Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')
    sans=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    if not regular.exists():
        from rpg_shop_identities import restore_baseline
        return restore_baseline(out,ATLAS_NAME)
    # Supersampling is confined to this original 2048 atlas.
    im=Image.new('RGB',(4096,4096),(54,44,32));d=ImageDraw.Draw(im)
    for row,idx in enumerate(SHOP_IDS):
        name,sub,bg,ink,menu=IDENTITIES[idx];top=row*768
        d.rectangle((0,top,4095,top+751),fill=bg)
        ff=sans if idx==1 and sans.exists() else regular
        def centered(s,y,size,box):
            face=Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc') if idx==7 and s==name else ff
            if not face.exists():face=ff
            f=ImageFont.truetype(str(face),size,index=0)
            while d.textbbox((0,0),s,font=f)[2]>box[2]-box[0]-70:
                size-=2;f=ImageFont.truetype(str(face),size,index=0)
            b=d.textbbox((0,0),s,font=f);d.text(((box[0]+box[2]-b[2])/2,y-b[1]),s,font=f,fill=ink)
        centered(name,top+52,205,(0,0,2590,0))
        centered(sub,top+321,83,(0,0,2590,0))
        centered(menu,top+551,83,(0,0,2590,0))
        # Square emblem sign carries one meaningful, actual Japanese character.
        d.rounded_rectangle((2832,top+47,3459,top+674),radius=56,outline=ink,width=12)
        centered({0:'炭',1:'麺',2:'灯',4:'茶',7:'菓'}[idx],top+170,322,(2832,0,3459,0))
        d.line((90,top+484,2499,top+484),fill=ink,width=5)
    path=out/ATLAS_NAME
    im.resize((2048,2048),Image.Resampling.LANCZOS).save(path,optimize=True)
    return dict(atlas=ATLAS_NAME,width=2048,height=2048,bytes=path.stat().st_size)


def _rect(idx,kind='name',*,rpg_identity=False):
    if rpg_identity is True:
        from rpg_shop_identities import food_rect
        replacement=food_rect(idx,kind)
        if replacement is not None:return replacement
    y=SHOP_IDS.index(idx)*384
    rect={'name':(10,y+12,1290,y+145),'sub':(10,y+152,1290,y+225),
          'menu':(10,y+261,1290,y+346),'emblem':(1410,y+12,1742,y+348)}[kind]
    if idx==7 and kind=='name':rect=(300,y+12,997,y+145) #697:133 crop preserves2.25:.43 physical aspect.
    x0,y0,x1,y1=rect
    return (x0/2048,1-y1/2048,x1/2048,1-y0/2048)

class _Builder:
    def __init__(self,g,P,B,w,dep,idx,M,*,rpg_identity=False):
        self.rpg_identity=rpg_identity
        self.g=g;self.P=P;self.B=B;self.w=w;self.d=dep;self.i=idx;self.M=M
        self.root=g.group;self.solids=[];self.seats=[]
    def part(self,name):self.g.group=self.root+'/'+name
    def box(self,x,y,z,w,d,h,m,solid=False):
        material=self.M.get(m,m)
        if material in ('Food_PaleJoinery','Food_Chestnut','Food_Reed') and min(w,d,h)>=.025 and max(w,d,h)>=.10:
            from timber_craft import timber_box_mesh
            vv,ff,uv=timber_box_mesh((x,y,z),(w,d,h),None,bevel=min(.005,min(w,d,h)*.12))
            self.g.add([self.P(*v) for v in vv],ff,material,uv)
        else:self.B(x,y,z,w,d,h,material)
        if solid:self.solids.append(dict(name=f'Food_{self.i+1:02d}_{len(self.solids):03d}',center=[x,y,z],size=[w,d,h],yaw=0))
    def rounded_box(self,x,y,z,w,d,h,r,m):
        # Closed rounded rectangle, planar top for actual seat support.
        r=min(r,w/2-.001,d/2-.001);ring=[]
        for cx,cy,start in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
            for a in np.linspace(start,start+90,7):
                aa=math.radians(a);ring.append([x+cx+r*math.cos(aa),y+cy+r*math.sin(aa)])
        n=len(ring);vv=[];uv=[];ff=[]
        for zz in [z-h/2,z+h/2]:
            for xx,yy in ring:vv.append(self.P(xx,yy,zz));uv.append((xx-x+w/2,yy-y+d/2))
        vv.extend([self.P(x,y,z-h/2),self.P(x,y,z+h/2)]);uv.extend([(w/2,d/2)]*2)
        for j in range(n):
            k=(j+1)%n;ff.extend([(2*n,k,j),(2*n+1,n+j,n+k),(j,k,n+k),(j,n+k,n+j)])
        self.g.add(vv,ff,self.M.get(m,m),uv)
    def beam(self,a,b,width,m,depth=None):self.g.beam(self.P(*a),self.P(*b),width,self.M.get(m,m),depth)
    def tube(self,ps,r,m,n=12):self.g.tube([self.P(*p) for p in ps],[r]*len(ps),self.M.get(m,m),n)
    def cyl(self,x,y,z,r,h,m,n=16,r2=None):self.g.cylinder(self.P(x,y,z),r,h,self.M.get(m,m),n,r2)
    def front(self,x,y,z,w,h,kind='name'):
        a,b,c,d=_rect(self.i,kind,rpg_identity=self.rpg_identity)
        self.g.quad([self.P(x+w/2,y,z-h/2),self.P(x-w/2,y,z-h/2),self.P(x-w/2,y,z+h/2),self.P(x+w/2,y,z+h/2)],'Food_Sign',[(a,b),(c,b),(c,d),(a,d)])
    def panel_sign(self,x,y,z,w,h,kind='name',frame='dark',depth=.11):
        self.box(x,y-depth/2,z,w+.11,depth,h+.10,frame)
        self.front(x,y+.004,z,w,h,kind)
    def shaped_sign(self,x,y,z,w,h,shape,frame='Food_Chestnut',kind='name'):
        def outline(ww,hh):
            if shape=='capsule':
                r=hh/2;out=[]
                for cx,ang in [(ww/2-r,-90),(-ww/2+r,90)]:
                    out.extend([(cx+r*math.cos(a),r*math.sin(a)) for a in np.linspace(math.radians(ang),math.radians(ang+180),13)])
                return out
            if shape=='arch':
                # A flat base and softly shouldered arched crest form a shop seal.
                return [(-ww/2,-hh/2),(ww/2,-hh/2)]+[(ww/2*math.cos(a),hh*.05+hh*.45*math.sin(a)) for a in np.linspace(0,math.pi,17)]+[(-ww/2,-hh/2)]
            if shape=='live':
                return [(-ww/2,-hh*.42),(-ww*.3,-hh*.51),(0,-hh*.47),(ww*.32,-hh*.52),(ww/2,-hh*.38),(ww*.49,hh*.39),(ww*.25,hh*.49),(-ww*.04,hh*.46),(-ww*.28,hh*.52),(-ww/2,hh*.41)]
            if shape=='chamfer':
                q=min(.12,hh*.3)
                return [(-ww/2+q,-hh/2),(ww/2-q,-hh/2),(ww/2,-hh/2+q),(ww/2,hh/2-q),(ww/2-q,hh/2),(-ww/2+q,hh/2),(-ww/2,hh/2-q),(-ww/2,-hh/2+q)]
            raise ValueError(shape)
        def layer(points,front_y,depth,material,printed=False):
            # Drop repeated endpoint; the closed fan owns each edge exactly once.
            if np.linalg.norm(np.asarray(points[0])-points[-1])<1e-8:points=points[:-1]
            nn=len(points);vv=[];ff=[];uv=[];a,b,cc,d=_rect(self.i,kind,rpg_identity=self.rpg_identity)
            for yy in [front_y,front_y-depth]:
                for px,pz in points:
                    vv.append(self.P(x+px,yy,z+pz));u=.5-px/w;v=.5+pz/h
                    uv.append((a+(cc-a)*u,b+(d-b)*v) if printed else (px+w/2,pz+h/2))
            vv.extend([self.P(x,front_y,z),self.P(x,front_y-depth,z)])
            uv.extend([((a+cc)/2,(b+d)/2)]*2 if printed else [(w/2,h/2)]*2)
            for j in range(nn):
                k=(j+1)%nn
                ff.extend([(2*nn,k,j),(2*nn+1,nn+j,nn+k)])
                # Separate side vertices keep the printed face's normals flat.
                # Without this seam, smooth GLB normals make the sign look inflated.
                off=len(vv);ids=[j,k,nn+k,nn+j]
                vv.extend([vv[q] for q in ids]);uv.extend([uv[q] for q in ids])
                ff.extend([(off,off+1,off+2),(off,off+2,off+3)])
            self.g.add(vv,ff,self.M.get(material,material),uv)
        layer(outline(w+.10,h+.09),y-.006,.10,frame)
        layer(outline(w,h),y+.005,.012,'Food_Sign',True)
    def arch(self,cx,y,z,r,width,mat,segments=16,rise=None):
        for j in range(segments):
            a=j*math.pi/segments;b=(j+1)*math.pi/segments
            self.beam((cx+r*math.cos(a),y,z+(rise or r)*math.sin(a)),(cx+r*math.cos(b),y,z+(rise or r)*math.sin(b)),width,mat)
    def slats(self,x,y,z,w,h,spacing=.19,mat='wood'):
        for xx in np.arange(x-w/2+.025,x+w/2,spacing):self.box(xx,y,z,.040,.048,h,mat)
    def register_seat(self,j,x,y,z=.70,facing=-1):
        self.seats.append(dict(id=f'S{self.i+1:02d}_Seat_{j+1}',position=[x,y,z],exit=[x,y-facing*.70,.06],forward=[0,facing,0]))
    def counter(self,z=1.03,mat='counter',front='wood'):
        # Original left staff portal remains .735 m clear; no hidden full-width base.
        ww=self.w-1.6;cy=self.d/2-.20
        self.box(.15,cy,z-.065,ww,.62,.13,mat,True)
        self.box(.15,cy-.05,(z-.13)/2,ww-.15,.42,z-.13,front,True)
        return cy
    def back(self,cladding='wall'):
        self.box(0,-self.d/2,1.3,self.w,.16,2.6,'dark',True)
        self.box(0,-self.d/2+.105,1.4,self.w-.26,.05,2.27,cladding)
    def posts(self,mat='dark',top=2.80):
        for side in [-1,1]:
            for yy in [-self.d/2,self.d/2]:self.box(side*(self.w/2-.10),yy,top/2,.18,.18,top,mat,True)
    def rear_work(self,finish='wood',shelves=True):
        self.box(.10,-self.d/2+.65,.425,self.w-1.0,.72,.85,finish,True)
        self.box(0,-self.d/2+1.10,.80,self.w-1,.46,.10,'counter')
        if shelves:
            for z in [1.40,2.05]:self.box(0,-self.d/2+.32,z,self.w-.8,.45,.08,'counter')
    def flat_roof(self,z=2.91,mat='dark'):
        self.box(0,0,z,self.w+.48,self.d+.55,.14,mat)
        for x in np.linspace(-self.w/2,self.w/2,7):self.beam((x,-self.d/2-.25,z-.12),(x,self.d/2+.3,z-.12),.075,mat)
    def stool(self,x,y,kind='timber',seat=.65):
        if kind=='timber':
            self.box(x,y,seat-.01,.47,.43,.12,'Food_Chestnut')
            for sx in [-1,1]:
                for sy in [-1,1]:self.beam((x+sx*.145,y+sy*.12,seat-.05),(x+sx*.205,y+sy*.18,.035),.074,'dark')
            for sy in [-1,1]:self.beam((x-.18,y+sy*.16,.22),(x+.18,y+sy*.16,.22),.048,'wood')
            self.beam((x,y-.17,.22),(x,y+.17,.22),.046,'wood')
        elif kind=='metal':
            self.cyl(x,y,seat,.215,.08,'Food_Oxblood',24)
            self.cyl(x,y,seat-.044,.21,.027,'iron',24)
            for sx in [-1,1]:
                for sy in [-1,1]:self.tube([(x+sx*.15,y+sy*.15,.04),(x+sx*.115,y+sy*.115,seat-.06)],.018,'iron',8)
            pts=[(x+.20*math.cos(a),y+.20*math.sin(a),.23) for a in np.linspace(0,math.tau,25)]
            self.tube(pts,.014,'trim',8)
        elif kind=='pedestal':
            self.cyl(x,y,.04,.235,.06,'Food_Chestnut',24)
            self.cyl(x,y,.31,.065,.54,'Food_Chestnut',16)
            self.cyl(x,y,seat,.24,.085,'Food_TileCream',32)
            self.cyl(x,y,seat-.06,.185,.032,'Food_Copper',24)
    def tea_chair(self,x,y,forward):
        # A visible three-rung back, curved crest rail and tapered square legs.
        z=.44;back=y-forward*.34
        self.box(x,y,z,.49,.67,.065,'Food_PaleJoinery')
        self.box(x,y,z+.041,.43,.60,.035,'Food_Upholstery')
        for sx in [-1,1]:
            for sy in [-1,1]:self.beam((x+sx*.17,y+sy*.16,z-.02),(x+sx*.21,y+sy*.20,.025),.038,'Food_PaleJoinery')
            self.beam((x+sx*.205,back,.37),(x+sx*.21,back+.015,.97),.035,'Food_PaleJoinery')
        for z1 in [.65,.77,.89]:self.beam((x-.205,back,z1),(x+.205,back,z1),.025,'Food_PaleJoinery')
        self.tube([(x-.23,back,.96),(x,back-forward*.032,1.00),(x+.23,back,.96)],.030,'Food_PaleJoinery',10)


def _charcoal(c,seat_specs):
    c.part('CharcoalHall');c.back('Food_Charcoal');c.posts(top=3.12)
    # Broad, visible king-post roof, unlike the shallow diner canopy.
    for yy in [-c.d/2,c.d/2+.24]:
        c.beam((-c.w/2-.18,yy,2.85),(0,yy,3.63),.14,'dark')
        c.beam((0,yy,3.63),(c.w/2+.18,yy,2.85),.14,'dark')
        c.beam((-c.w/2-.16,yy,2.84),(c.w/2+.16,yy,2.84),.18,'dark')
    for side in [-1,1]:
        xx=side*(c.w/2+.18);y0=-c.d/2-.25;y1=c.d/2+.38
        # Continuous sloping surfaces, closed fascia and no floating staircase ends.
        vv=[c.P(0,y0,3.64),c.P(xx,y0,2.86),c.P(xx,y1,2.86),c.P(0,y1,3.64)]
        c.g.quad(vv,'Food_Charcoal',double=True)
        c.beam((xx,y0,2.83),(xx,y1,2.83),.10,'Food_Chestnut',.13)
        for yy in np.arange(y0,y1+.01,.48):
            c.beam((0,yy,3.66),(xx,yy,2.88),.025,'iron',.034)
        for xx1 in np.linspace(0,xx,7):
            zz=3.61-abs(xx1)*.78/(c.w/2+.18)
            c.beam((xx1,y0,zz-.06),(xx1,y1,zz-.06),.050,'wood',.085)
    c.beam((0,-c.d/2-.28,3.67),(0,c.d/2+.42,3.67),.12,'Food_Copper',.07)
    c.rear_work('Food_Charcoal')
    for x in np.linspace(-c.w/2+.6,c.w/2-.6,6):
        c.box(x,-c.d/2+1.023,.45,.70,.038,.62,'Food_Chestnut')
        c.beam((x-.12,-c.d/2+1.05,.56),(x+.12,-c.d/2+1.05,.56),.019,'iron')
    cy=c.counter(front='Food_Charcoal',mat='Food_Chestnut')
    for xx in np.arange(-c.w/2+1.12,c.w/2-.60,.29):c.box(xx,cy+.175,.43,.22,.055,.70,'Food_Chestnut')
    # Asymmetric substantial hood and open vent fins, not a generic shoji wall.
    c.box(.68,.05,1.99,1.56,.93,.34,'iron')
    c.box(.68,.05,2.33,1.18,.72,.40,'Food_Charcoal')
    c.box(.68,.05,3.15,.34,.35,1.26,'iron')
    for xx in np.arange(.1,1.3,.16):c.box(xx,.525,1.99,.035,.023,.23,'trim')
    # No side infill: the grill hall reads as an open workshop.
    c.part('CharcoalSigns');c.shaped_sign(.35,c.d/2+.44,2.54,3.75,.45,'live')
    c.panel_sign(c.w/2-.5,c.d/2+.17,1.78,.54,.59,'emblem',frame='Food_Charcoal')
    for x in [-1.1,.1,1.3]:
        c.beam((x,c.d/2+.05,2.81),(x,c.d/2+.35,2.81),.04,'iron')
        c.box(x,c.d/2+.29,2.75,.22,.19,.06,'iron')
    from lantern_craft import add_washi_lantern
    add_washi_lantern(c.g,c.P(c.w/2-.45,c.d/2+.32,2.16),'PaperLight',c.M['red'],c.M['trim'],c.M['iron'],1.03)
    c.part('CharcoalSeats')
    for j,s in enumerate(seat_specs):
        x,y,_=s['position'];c.stool(x,y);c.register_seat(j,x,y)
    return dict(style='open charcoal hall',counter='thick slab and charred vertical blocks',chair='splayed timber joinery stool',roof='king-post pitched roof and projecting ridge')


def _ramen(c,seat_specs):
    c.part('NoodleDiner');c.back('Food_TileCream');c.posts('iron',top=2.72)
    c.flat_roof(2.87,'Food_TileGreen')
    # Shallow cantilever canopy, stepped fascia and exposed orderly service pipes.
    c.box(0,c.d/2+.24,2.74,c.w+.45,.63,.23,'Food_Enamel')
    for xx in np.arange(-c.w/2-.15,c.w/2+.2,.27):c.box(xx,c.d/2+.57,2.68,.19,.07,.12,'Food_TileGreen')
    c.rear_work('Food_Enamel');cy=c.counter(mat='Food_Enamel',front='Food_TileGreen')
    # Real low-poly tile faces separated by recessed grout, no texture-only grid.
    for yy,zz,ww,hh in [(cy+.17,.46,c.w-1.82,.81),(-c.d/2+.14,1.67,c.w-.35,1.34)]:
        for x in np.arange(-ww/2+.12,ww/2,.255):
            for z in np.arange(zz-hh/2+.10,zz+hh/2,.19):c.box(x+( .15 if yy>0 else 0),yy+.025,z,.239,.027,.175,'Food_TileCream')
    for xx in [-1.7,-.6,.6,1.7]:
        c.box(xx,-c.d/2+.29,2.28,.44,.14,.36,'Food_Enamel')
        c.box(xx,-c.d/2+.38,2.28,.29,.028,.22,'Food_TileGreen')
    for xx in [-.75,.35,1.45]:
        c.tube([(xx,-c.d/2+.40,.9),(xx,-c.d/2+.40,1.28),(xx,-c.d/2+.62,1.28)],.023,'iron',10)
        c.cyl(xx,-c.d/2+.77,.91,.20,.11,'iron',24)
    c.box(c.w/2-.42,c.d/2-.40,1.31,.48,.37,.76,'Food_TileGreen',True)
    for rr in range(4):
        for cc in range(2):c.box(c.w/2-.54+cc*.19,c.d/2-.205,1.08+rr*.15,.13,.02,.10,'Food_Paper')
    c.part('NoodleSigns');c.shaped_sign(0,c.d/2+.72,2.85,3.30,.48,'capsule','Food_TileGreen')
    # Two off-centre short banners leave the staff portal fully open.
    for j,x in enumerate([-.95,.95]):c.panel_sign(x,c.d/2+.02,2.38,1.60,.22,'sub' if j==0 else 'menu',frame='Food_Enamel',depth=.025)
    c.part('NoodleSeats')
    for j,s in enumerate(seat_specs):
        x,y,_=s['position'];c.stool(x,y,'metal');c.register_seat(j,x,y)
    return dict(style='tiled noodle diner',counter='enamel slab on real tile grid',chair='tubular metal stool and circular foot ring',roof='flat stepped cantilever')


def _oden(c,seat_specs):
    c.part('OdenNook');c.back('Food_Oxblood');c.posts('Food_Chestnut',top=2.64)
    # Barrel canopy made as a connected curved surface with proud seam ribs.
    ww=c.w+.32;dd=c.d+.50;v=[];f=[];uv=[];ns=18
    for j in range(ns+1):
        xx=-ww/2+ww*j/ns;zz=2.72+.57*math.sqrt(max(0,1-(xx/(ww/2))**2))
        v.extend([c.P(xx,-dd/2,zz),c.P(xx,dd/2,zz)]);uv.extend([(j/ns,0),(j/ns,1)])
        if j:
            k=j*2;f.extend([(k-2,k-1,k+1),(k-2,k+1,k)])
    c.g.add(v,f,'Food_Oxblood',uv)
    c.g.add(v,[q[::-1] for q in f],'Food_Oxblood',uv)
    for yy in [-dd/2,dd/2]:
        pts=[(-ww/2+ww*j/ns,yy,2.72+.57*math.sqrt(max(0,1-((-ww/2+ww*j/ns)/(ww/2))**2))) for j in range(ns+1)]
        c.tube(pts,.047,'Food_Chestnut',8)
    c.rear_work('Food_Chestnut');cy=c.counter(.87,'Food_Chestnut','Food_Oxblood')
    # Two large shoji-backed windows, horizontal rails and small intimate soffit.
    for x in [-1.20,1.20]:
        c.box(x,-c.d/2+.18,1.77,.86,.07,1.00,'Food_Paper')
        c.slats(x,-c.d/2+.23,1.77,.87,.99,.20,'Food_Chestnut')
        for z in [1.29,1.62,1.95,2.28]:c.box(x,-c.d/2+.25,z,.95,.05,.045,'Food_Chestnut')
    c.box(0,c.d/2-.21,2.56,c.w-.30,.66,.12,'Food_Chestnut')
    for xx in np.arange(-1.25,1.5,.46):c.box(xx,cy+.183,.40,.40,.04,.63,'Food_Chestnut')
    c.part('OdenSigns')
    c.shaped_sign(.30,c.d/2+.27,2.51,2.70,.43,'chamfer','Food_Oxblood')
    # Offset lantern with square meaningful emblem, not another long cloth row.
    from lantern_craft import add_washi_lantern
    add_washi_lantern(c.g,c.P(c.w/2-.44,c.d/2+.22,2.12),'PaperLight',c.M['red'],c.M['trim'],c.M['iron'],.90)
    c.front(c.w/2-.44,c.d/2+.435,2.12,.23,.29,'emblem')
    c.part('OdenBenches')
    xs=[s['position'][0] for s in seat_specs];y=seat_specs[0]['position'][1]
    for ids in [[0,1],[2,3,4]]:
        cx=(xs[ids[0]]+xs[ids[-1]])/2;ww=xs[ids[-1]]-xs[ids[0]]+.54
        c.rounded_box(cx,y,.46,ww,.44,.10,.18,'Food_Chestnut')
        c.rounded_box(cx,y,.524,ww-.04,.39,.05,.175,'Food_Upholstery')
        for sx in [-1,1]:
            c.box(cx+sx*(ww/2-.15),y,.23,.13,.36,.46,'Food_Chestnut')
        c.beam((cx-ww/2+.10,y,.22),(cx+ww/2-.10,y,.22),.085,'dark')
    for j,x in enumerate(xs):c.register_seat(j,x,y,.58)
    return dict(style='warm oden nook',counter='low copper-pot service ledge',chair='two split upholstered timber benches',roof='arched barrel canopy')


def _tea(c,seat_specs,*,pendant_refinement=False):
    c.part('TeaPavilion');c.back('Food_Reed');c.posts('Food_PaleJoinery',top=2.79)
    # Clerestory has its own lightweight roof and reveals the thin cross beams.
    c.flat_roof(2.83,'Food_PaleJoinery')
    c.box(0,-.32,3.04,c.w*.64,c.d*.62,.40,'Food_Paper')
    c.box(0,-.32,3.29,c.w*.70,c.d*.68,.12,'Food_Reed')
    for yy in [-c.d*.31-.32,c.d*.31-.32]:
        for xx in np.arange(-c.w*.32,c.w*.32+.1,.34):c.box(xx,yy,3.05,.025,.035,.43,'Food_PaleJoinery')
    for side in [-1,1]:
        # Open side screens terminate before the front opening.
        x=side*(c.w/2-.15)
        c.solids.append(dict(name=f'tea_side_screen_{side}',center=[x,-.53,1.40],size=[.085,4.32,2.50],yaw=0))
        for yy in np.arange(-c.d/2+.12,1.80,.21):c.box(x,yy,1.40,.06,.027,2.50,'Food_PaleJoinery')
        for zz in [.18,.63,1.08,1.53,1.98,2.44]:c.box(x,-.53,zz,.085,4.32,.026,'Food_PaleJoinery')
    c.box(0,-c.d/2+.40,.43,c.w-1.0,.57,.86,'Food_Reed',True)
    c.box(0,-c.d/2+.43,.885,c.w-1.0,.67,.05,'Food_PaleJoinery')
    # Tokonoma-like central niche, asymmetric cabinet and refined interlock lattice.
    c.box(.85,-c.d/2+.13,1.70,1.50,.09,1.32,'wall')
    c.box(.85,-c.d/2+.26,1.10,1.65,.39,.07,'Food_PaleJoinery')
    for xx in np.arange(-c.w/2+.44,-.20,.27):
        c.box(xx,-c.d/2+.22,1.82,.024,.036,1.12,'Food_PaleJoinery')
        c.beam((xx,-c.d/2+.23,1.35),(xx+.24,-c.d/2+.23,1.59),.018,'Food_PaleJoinery')
        c.beam((xx,-c.d/2+.23,1.59),(xx+.24,-c.d/2+.23,1.35),.018,'Food_PaleJoinery')
    c.part('TeaFurniture')
    for side in [-1,1]:
        cx=side*1.77;cy=.40
        c.box(cx,cy,.718,1.50,1.43,.065,'Food_PaleJoinery',True)
        for sx in [-1,1]:
            for sy in [-1,1]:c.beam((cx+sx*.60,cy+sy*.54,.68),(cx+sx*.64,cy+sy*.58,.04),.062,'Food_PaleJoinery')
        for facing,y in [(-1,1.60),(1,-.80)]:
            for dx in [-.43,.43]:
                j=len(c.seats);x=cx+dx;c.tea_chair(x,y,facing);c.register_seat(j,x,y,.53,facing)
                c.seats[-1]['exit']=[x+(.70 if dx>0 else -.70),y,.06]
    c.part('TeaSigns');c.shaped_sign(.05,c.d/2+.39,2.60,3.55,.32,'chamfer','Food_PaleJoinery')
    c.panel_sign(c.w/2-.35,c.d/2+.43,2.68,.40,.65,'emblem',frame='Food_PaleJoinery')
    for xx in [-1.77,1.77]:
        c.beam((xx,.4,2.81),(xx,.4,2.46),.012,'trim')
        c.box(xx,.4,2.35,.70,.47,.21,'Food_Paper')
        if pendant_refinement:
            # Keep the existing four chamfered caps exactly, changing only their
            # opaque timber material. Going through box('dark') would lose the
            # original 44-triangle chamfer and its member-oriented UV payload.
            from timber_craft import timber_box_mesh
            for z in [2.24,2.45]:
                vv,ff,uv=timber_box_mesh((xx,.4,z),(.75,.51,.025),None,bevel=.003)
                c.g.add([c.P(*v) for v in vv],ff,c.M['dark'],uv)
            # Six genuinely solid stiles per pendant: corner posts and a single
            # divider on each broad washi face. All fit inside the old caps;
            # 12 plain cuboids add 144 triangles without a dense lattice.
            for sy in [-1,1]:
                for sx in [-1,1]:
                    c.box(xx+sx*.361,.4+sy*.244,2.345,.028,.020,.210,'dark')
                c.box(xx,.4+sy*.244,2.345,.0175,.020,.210,'dark')
        else:
            for z in [2.24,2.45]:c.box(xx,.4,z,.75,.51,.025,'Food_PaleJoinery')
    return dict(style='open tea pavilion',counter='two four-place low tables and rear tea cabinet',chair='tapered lattice-backed dining chair',roof='luminous raised clerestory')


def _sweets(c,seat_specs):
    c.part('Confectioner');c.back('wall');c.posts('Food_Chestnut',top=2.85)
    # Hipped-looking stepped canopy and a deep arched shopfront display frame.
    c.flat_roof(2.91,'Food_Chestnut')
    c.box(0,-.2,3.06,c.w-.7,c.d-.8,.15,'Food_Reed')
    c.box(0,-.2,3.17,c.w-1.5,c.d-1.5,.10,'Food_Chestnut')
    c.arch(0,c.d/2+.20,2.30,1.64,.095,'Food_Chestnut',22,rise=.44)
    for x in [-1.64,1.64]:c.box(x,c.d/2+.20,1.87,.095,.12,.86,'Food_Chestnut')
    c.rear_work('Food_Chestnut');cy=c.counter(mat='Food_PaleJoinery',front='Food_Chestnut')
    # Low drawer apothecary, broad shadow gaps and round pulls.
    for xx in np.arange(-c.w/2+.68,c.w/2-.5,.53):
        for zz in [.22,.49,.73]:
            c.box(xx,-c.d/2+1.03,zz,.48,.045,.22,'Food_PaleJoinery')
            c.cyl(xx,-c.d/2+1.055,zz,.027,.022,'Food_Copper',10) # carved knob base
            c.box(xx,-c.d/2+1.078,zz,.05,.025,.045,'Food_Copper')
    for side in [-1,1]:
        x=side*(c.w/2-.57)
        c.box(x,-c.d/2+.26,1.81,.69,.17,1.06,'Food_Chestnut')
        for z in [1.39,1.72,2.05]:c.box(x,-c.d/2+.39,z,.74,.36,.045,'Food_PaleJoinery')
    # Glass-free open display cubbies. No fake transparent shader promise.
    c.box(.15,cy-.20,1.18,2.02,.30,.24,'Food_Chestnut')
    for xx in [-.81,-.33,.15,.63,1.11]:c.box(xx,cy-.02,1.18,.024,.08,.20,'Food_PaleJoinery')
    c.box(.15,cy-.02,1.325,2.06,.43,.038,'Food_PaleJoinery')
    c.part('ConfectionerSigns');c.shaped_sign(0,c.d/2+.38,2.52,2.25,.43,'arch','Food_Chestnut')
    c.panel_sign(c.w/2-.45,c.d/2+.13,2.02,.55,.66,'emblem',frame='Food_Chestnut')
    c.part('ConfectionerSeats')
    for j,s in enumerate(seat_specs):
        x,y,_=s['position'];c.stool(x,y,'pedestal');c.register_seat(j,x,y)
    return dict(style='arrival confectioner',counter='open confection display and drawer apothecary',chair='turned pedestal stool',roof='stepped canopy with arched frontage')


def _finish(c):
    """Purposeful hand-scale joinery and fixtures; none project into portals."""
    c.part('JoineryFinish')
    # Visible timber post feet, mortise pegs and haunches are specific to timber shops.
    if c.i!=1:
        for side in [-1,1]:
            x=side*(c.w/2-.10)
            for y in [-c.d/2,c.d/2]:
                c.box(x,y,.12,.205,.205,.18,'iron')
                for z in [.18,2.40]:
                    for dx in [-.047,.047]:
                        c.g.sphere(c.P(x+dx,y+.105,z),[.012,.006,.012],c.M['trim'],8,4)
                c.beam((x,y,2.31),(x-side*.36,y,2.65),.055,'Food_PaleJoinery' if c.i==4 else 'Food_Chestnut')
    if c.i==0:
        # Pinned countertop seams, two real knee braces and hood-mounted task lights.
        cy=c.d/2-.20
        for x in [-1.5,0,1.6]:
            for y in [cy-.18,cy+.16]:c.cyl(x,y,1.032,.009,.006,'dark',8)
        for x in [-1.55,1.55]:c.beam((x,cy-.02,.67),(x,cy-.27,.91),.060,'Food_Chestnut')
        for x in [.17,1.18]:c.box(x,.05,1.81,.24,.39,.027,'Food_Paper')
        c.box(.68,.05,.41,3.18,1.06,.82,'Food_Charcoal',True)
        c.box(.68,.05,.835,3.26,1.12,.030,'iron')
        for xx in [-.73,.21,1.15,2.08]:c.box(xx,.60,.40,.86,.035,.64,'Food_Chestnut')
        # Two squared end-grain caps articulate the thick butcher slab.
        for x in [-c.w/2+.975,c.w/2-.675]:c.box(x,cy,.965,.052,.60,.12,'counter')
    elif c.i==1:
        # Stainless side return makes a practical L-shaped noodle-prep kitchen.
        c.box(c.w/2-.49,-.38,.405,.70,2.76,.81,'Food_Enamel',True)
        c.box(c.w/2-.49,-.38,.835,.78,2.83,.034,'iron')
        for yy in [-1.20,-.40,.40]:
            c.box(c.w/2-.856,yy,.43,.034,.70,.61,'Food_Enamel')
            c.beam((c.w/2-.884,yy-.16,.53),(c.w/2-.884,yy+.16,.53),.016,'iron')
        c.box(c.w/2-.49,-.65,.856,.52,.64,.015,'Food_Charcoal')
        c.tube([(c.w/2-.29,-.8,.85),(c.w/2-.29,-.8,1.12),(c.w/2-.49,-.8,1.18),(c.w/2-.49,-.8,1.09)],.019,'iron',10)
        # Two long metal-and-opal luminaires, enamel backsplash edge and pipe clips.
        for x in [-1.15,1.15]:
            c.box(x,.25,2.65,.36,2.35,.065,'iron')
            c.box(x,.25,2.610,.27,2.23,.017,'Food_Paper')
            for y in [-.72,1.22]:c.beam((x,y,2.73),(x,y,2.88),.012,'iron')
        for z in [1.12,2.37]:c.box(0,-c.d/2+.18,z,c.w-.27,.034,.027,'Food_TileGreen')
        c.panel_sign(c.w/2-.42,c.d/2-.19,1.79,.40,.13,'menu',frame='Food_TileGreen',depth=.03)
    elif c.i==2:
        # A small freestanding hotpot preparation island replaces empty middle space.
        c.box(.48,.07,.405,1.20,.72,.81,'Food_Chestnut',True)
        c.box(.48,.07,.832,1.26,.78,.036,'Food_Copper')
        for x in [-.02,.98]:c.box(x,.453,.40,.048,.032,.69,'Food_Copper')
        c.box(.48,.457,.52,.36,.03,.036,'Food_Copper')
        c.beam((.48,.07,2.67),(.48,.07,2.27),.013,'trim')
        c.cyl(.48,.07,2.20,.19,.10,'Food_Paper',24)
        c.cyl(.48,.07,2.25,.26,.035,'Food_Copper',24)
        for y in [-c.d/2,c.d/2]:
            c.box(0,y,2.65,c.w-.1,.13,.095,'Food_Chestnut')
    elif c.i==4:
        # Cabinet finger pulls, woven-panel framing and thin roof drip edge.
        for x in np.arange(-c.w/2+.60,c.w/2-.45,.73):
            c.box(x,-c.d/2+.701,.44,.66,.024,.68,'Food_PaleJoinery')
            c.box(x+.20,-c.d/2+.72,.52,.018,.024,.11,'dark')
        for side in [-1,1]:
            c.beam((side*(c.w/2+.20),-c.d/2-.24,2.78),(side*(c.w/2+.20),c.d/2+.24,2.78),.038,'Food_Copper')
        # Low lattice-back chairs remain individually readable even without color.
    else:
        # Shadow gaps and restrained copper shelf brackets, not unrelated bar clutter.
        for y in [-c.d/2+.33]:
            for x in [-1.7,-.5,.7,1.9]:
                for z in [1.38,2.03]:c.beam((x,y-.15,z-.16),(x,y+.13,z),.018,'Food_Copper')
        for x in [-1.30,1.30]:
            c.box(x,-.25,2.61,.38,.38,.19,'Food_Paper')
            for z in [2.50,2.72]:c.box(x,-.25,z,.43,.43,.025,'Food_Chestnut')
            c.beam((x,-.25,2.73),(x,-.25,2.87),.018,'Food_Copper')


def _props(c):
    """Reuse authored food meshes, but not their old furniture or shared shell."""
    from counter_craft import (add_counter_craft,_Craft,_teapot,_dango,_tea_whisk,
       TENMOKU,INDIGO,IVORY,MATCHA,BAMBOO,SWEET_RED,CHESTNUT,LACQUER,_oden_pot)
    c.part('SpecialtyService')
    if c.i==7:
        cc=_Craft(c.g,c.P,c.B,c.M,45699);cy=c.d/2-.20
        for j,s in enumerate(c.seats):
            x=s['position'][0];z=cc.tray((x,cy,1.032),.38,.27)
            cc.plate((x-.05,cy,z),.10,IVORY)
            if j%2:_dango(cc,(x-.05,cy,z+.023))
            else:
                cc.slab((x-.05,cy,z+.045),(.077,.083,.058),SWEET_RED,.005)
                cc.pebble((x-.05,cy+.042,z+.047),(.018,.002,.015),CHESTNUT,10,5)
            cc.cup((x+.18,cy-.03,1.032),.033,.060,INDIGO)
        # Each display cubby contains one intentional seasonal confection tray.
        for j,x in enumerate([-.57,-.09,.39,.87]):
            z=cc.tray((x,cy-.015,1.345),.38,.28)
            for k in range(2):
                xx=x-.075+k*.15
                cc.slab((xx,cy-.03,z+.045),(.09,.08,.059),SWEET_RED,.006)
                cc.pebble((xx,cy+.011,z+.048),(.022,.002,.014),CHESTNUT,10,5)
        for z in [1.44,2.09]:
            for j,x in enumerate([-1.8,-1.2,-.6,.0,.6,1.2,1.8]):
                if j%3==0:cc.canister((x,-c.d/2+.32,z),.09,.19,BAMBOO)
                else:
                    cc.slab((x,-c.d/2+.32,z+.064),(.34,.25,.12),BAMBOO,.009)
                    cc.slab((x,-c.d/2+.32,z+.130),(.36,.27,.016),LACQUER,.005)
                    cc.slab((x,-c.d/2+.32,z+.146),(.023,.28,.012),IVORY,.001)
        _teapot(cc,(.72,-c.d/2+1.10,.85),.09,TENMOKU)
        return dict(shop='S08',purpose='original wagashi trays, paper-tied gift boxes and tea tins',seed=45699)
    if c.i!=4:
        oldP=c.P;oldB=c.B
        def shift(x,y,z):return -.16 if c.i==2 and y>c.d/2-.9 else 0
        def shift_y(x,y,z):return c.d/2-1.05 if c.i==0 and (-c.d/2+.70)<y<(-c.d/2+1.45) else 0
        pp=lambda x,y,z:oldP(x,y+shift_y(x,y,z),z+shift(x,y,z))
        bb=lambda x,y,z,w,d,h,m:oldB(x,y+shift_y(x,y,z),z+shift(x,y,z),w,d,h,m)
        result=add_counter_craft(c.g,pp,bb,c.w,c.d,c.i,c.M,staff_entry=True)
        if c.i==2:
            p2=lambda x,y,z:oldP(x,y+c.d/2-1.03,z)
            b2=lambda x,y,z,w,d,h,m:oldB(x,y+c.d/2-1.03,z,w,d,h,m)
            _oden_pot(_Craft(c.g,p2,b2,c.M,9281),c.w,c.d)
        return result
    cc=_Craft(c.g,c.P,c.B,c.M,45692)
    for side in [-1,1]:
        x=side*1.77;y=.40;z=.752
        _teapot(cc,(x,y,z),.095,TENMOKU)
        for dx in [-.43,.43]:
            for yy in [-.07,.87]:
                tz=cc.tray((x+dx,yy,z),.36,.29)
                cc.bowl((x+dx-.075,yy,tz),.072,.060,INDIGO)
                cc.disk((x+dx-.075,yy,tz+.041),.054,MATCHA,18)
                cc.plate((x+dx+.09,yy,tz),.075,IVORY)
                _dango(cc,(x+dx+.09,yy,tz+.026))
    _teapot(cc,(.85,-c.d/2+.30,1.14),.12,TENMOKU)
    _tea_whisk(cc,(-.35,-c.d/2+.50,.91))
    for xx in [-1.7,-1.3,-.9]:cc.canister((xx,-c.d/2+.42,.91),.12,.23,BAMBOO)
    return dict(shop='S05',purpose='tea services on two lower tables',seed=45692)


def _routes(c):
    front=c.d/2+1.35
    routes=[dict(name='customer_front',role='customer',centerline=[[-c.w/2+.5,front],[c.w/2-.5,front]],radius=.25,headroom=1.9)]
    if c.i==4:
        routes.append(dict(name='tea_central_entrance',role='entrance',centerline=[[0,front],[0,-1.60]],radius=.25,headroom=1.9))
        for side in [-1,1]:
            path=([[0,front],[0,2.35],[2.95,2.35],[2.95,-1.60],[0,-1.60]] if side>0 else [[-2.95,front],[-2.95,-1.60],[0,-1.60]])
            routes.append(dict(name=f'tea_side_{side}',role='customer',centerline=path,radius=.25,headroom=2.2))
        for j,s in enumerate(c.seats):
            ex,ey,_=s['exit'];target=0 if abs(ex)<1 else (2.95 if ex>0 else -2.95)
            routes.append(dict(name=f'tea_seat_exit_{j+1}',role='exit',centerline=[[ex,ey],[target,ey]],radius=.25,headroom=1.9))
    else:
        from staff_access import staff_entry_plan
        routes.append(dict(name='staff_entry',role='entrance',centerline=[list(q) for q in staff_entry_plan(c.i,c.w,c.d)['centerline']],radius=.25,headroom=1.9))
    if c.i==4:
        routes.append(dict(name='tea_rear_cabinet_service',role='staff',centerline=[[0,front],[0,-1.75],[-2.50,-1.75],[2.50,-1.75]],radius=.25,headroom=2.2))
    else:
        routes.append(dict(name='counter_working_aisle',role='staff',centerline=[[-c.w/2+.70,1.45],[c.w/2-.80,1.45]],radius=.25,headroom=2.2))
        routes.append(dict(name='rear_prep_access',role='staff',centerline=[[0,1.45],[-c.w/2+.70,1.45],[-c.w/2+.70,-c.d/2+1.80],[0,-c.d/2+1.80]],radius=.25,headroom=2.2))
    for route in routes:
        if route['role'] in ('entrance','staff'):route.update(radius=.325,headroom=2.2)
        route['points']=[[x,y,0] for x,y in route['centerline']]
    return routes


def build_venue(g,P,B,w,dep,idx,M,*,seat_specs,lantern=None,rpg_identity=False,pendant_refinement=False):
    if type(pendant_refinement) is not bool:raise ValueError("pendant_refinement must be a literal Boolean")
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    if idx not in SHOP_IDS:raise ValueError('food venue index must be 0, 1, 2, 4 or 7')
    expected={0:6,1:6,2:5,4:8,7:6}[idx]
    if len(seat_specs)!=expected:raise ValueError(f'S{idx+1:02d} requires {expected} station specs')
    missing=set(_material_specs())-set(g.materials)
    if missing:raise ValueError('register material_specs before build: '+', '.join(sorted(missing)))
    start=sum(len(b['f']) for b in g.batches.values());root=g.group
    g.group=root+'/Personality' if not root.endswith('/Personality') else root
    c=_Builder(g,P,B,w,dep,idx,M,rpg_identity=rpg_identity)
    design=(_tea(c,seat_specs,pendant_refinement=pendant_refinement) if idx==4 else
            {0:_charcoal,1:_ramen,2:_oden,7:_sweets}[idx](c,seat_specs))
    _finish(c)
    props=_props(c)
    # Functional seat overrides are explicit local coordinates, not visual offsets.
    g.group=root
    routes=_routes(c)
    result=dict(version=VERSION,completeVisualReplacement=True,shop=f'S{idx+1:02d}',theme=design['style'],design=design,props=props,routes=routes,
        triangles=sum(len(b['f']) for b in g.batches.values())-start,
        seatOverrides=c.seats,solids=c.solids,
        lights=[dict(position=p,range=4.8,strength=strength) for p,strength in {
            0:[([.68,.05,1.69],1.0),([w/2-.45,dep/2+.32,1.88],1.2)],
            1:[([-1.15,.25,2.49],1.15),([1.15,.25,2.49],1.15)],
            2:[([.48,.07,2.04],1.2),([w/2-.44,dep/2+.22,1.87],1.0)],
            4:[([-1.77,.4,2.13],1.2),([1.77,.4,2.13],1.2)],
            7:[([-1.30,-.25,2.37],1.1),([1.30,-.25,2.37],1.1)],
        }[idx]],
        steam=[] if idx in [4,7] else [dict(position=({0:[.68,.05,1.13],1:[.36,-dep/2+1.10,1.17],2:[.48,.07,1.13]}[idx]),id=f'S{idx+1:02d}')],
        boundsPolicy='Local shop shell plus previous front seating; no floor or guard edits',
        textureAtlas=ATLAS_NAME)
    if rpg_identity is True:
        from rpg_shop_identities import IDENTITIES as RPG_IDENTITIES
        result['displayName']=RPG_IDENTITIES[idx]['name']
    return result
