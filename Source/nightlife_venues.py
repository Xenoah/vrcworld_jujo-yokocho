"""Three complete, distinct nightlife venue replacements; deterministic Z-up metres.

Ownership: S04 snack, S06 cocktail/whisky, S07 music/listening. This replaces,
not decorates, the legacy generic visual shell. No floor/path/guard writes.
All proposed colliders are explicit local records, never B(solid=True).
The owner must replace obsolete counter collision and station records using
proposedSolids / seatOverrides. Rendering alone does not establish runtime QA.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box as rect
from shapely.ops import unary_union
from world_geometry import poly_mesh

VERSION='nightlife-design-1'
IDS={3:'S04',5:'S06',6:'S07'}
NAMES={3:'スナック 根っこ',5:'宵葉',6:'山椒'}
ATLAS='nightlife_signs.png'

def material_specs():
    """Mapping M-key to existing mat(name,col,tex,em,rough,**pbr) descriptors."""
    specs = {
      'night_print':dict(name='Night_Print',color=(1,1,1),texture=ATLAS,roughness=.86),
      'night_walnut':dict(name='Night_Walnut',color=(.40,.27,.19),texture='PBR/wood_table_001_diff_4k.jpg',roughness=.56,normal='PBR/wood_table_001_nor_gl_2k.jpg',uvScale=.8),
      'night_wine':dict(name='Night_WineUpholstery',color=(.28,.048,.071),texture='woven.png',roughness=.82,normal='woven_normal.png',normalScale=.25),
      'night_leather':dict(name='Night_TobaccoLeather',color=(.24,.105,.042),roughness=.66),
      'night_indigo':dict(name='Night_IndigoUpholstery',color=(.045,.097,.105),texture='woven.png',roughness=.92,normal='woven_normal.png',normalScale=.3),
      'night_glass':dict(name='Night_SmokyGlass',color=(.16,.20,.14),roughness=.19,metallic=.25),
      'night_speaker':dict(name='Night_SpeakerCone',color=(.032,.035,.031),roughness=.96),
      'night_roof':dict(name='Night_StandingSeam',color=(.16,.22,.21),roughness=.72,metallic=.32),
    }
    return [dict(key=k,**v) for k,v in specs.items()]

def bake_textures(out,font=None,*,rpg_identity=False):
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    if rpg_identity is True:
        from rpg_shop_identities import bake
        return bake(out,ATLAS)
    """Original restrained printed artwork. 2x AA, one 2048px lossless atlas."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True);font=Path(font) if font else Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if not font.exists():
        from rpg_shop_identities import restore_baseline
        return restore_baseline(out,ATLAS)
    ss=2;im=Image.new('RGB',(2048*ss,2048*ss),(29,36,35));d=ImageDraw.Draw(im)
    def ft(n):return ImageFont.truetype(str(font),n*ss,index=0)
    def drawcell(i,bg,title,sub,mark):
        x=(i%4)*512*ss;y=(i//4)*512*ss
        d.rectangle((x,y,x+512*ss,y+512*ss),fill=bg)
        d.rounded_rectangle((x+22*ss,y+22*ss,x+490*ss,y+490*ss),radius=22*ss,outline=(172,142,83),width=3*ss)
        if mark=='roots':
            for shift in [-1,0,1]:
                p=[(x+(256+shift*34)*ss,y+91*ss),(x+256*ss,y+143*ss),(x+(256+shift*65)*ss,y+170*ss)]
                d.line(p,fill=(193,151,94),width=5*ss)
        elif mark=='moon':
            d.ellipse((x+207*ss,y+70*ss,x+305*ss,y+168*ss),fill=(212,184,117));d.ellipse((x+232*ss,y+60*ss,x+310*ss,y+143*ss),fill=bg)
        elif mark=='record':
            for r in [55,47,38,17]:d.ellipse((x+(256-r)*ss,y+(120-r)*ss,x+(256+r)*ss,y+(120+r)*ss),outline=(186,167,107),width=(3 if r==17 else 2)*ss)
            d.ellipse((x+252*ss,y+116*ss,x+260*ss,y+124*ss),fill=(186,167,107))
        fs=60 if len(title)<6 else 47
        ink=(52,45,34) if i>=4 else (238,216,167)
        subink=(85,66,45) if i>=4 else (195,171,132)
        d.text((x+256*ss,y+258*ss),title,font=ft(fs),anchor='mm',fill=ink)
        d.text((x+256*ss,y+350*ss),sub,font=ft(26),anchor='mm',fill=subink)
        d.line((x+94*ss,y+403*ss,x+418*ss,y+403*ss),fill=(126,102,69),width=2*ss)
    drawcell(0,(56,25,34),'スナック 根っこ','スナック • 樹上の夜', 'roots')
    drawcell(1,(31,38,38),'宵葉','COCKTAIL & WHISKY','moon')
    drawcell(2,(36,45,43),'山椒','音楽と珈琲と酒','record')
    drawcell(3,(91,51,37),'ボトルキープ','いつもの一杯','roots')
    labels=[('今夜のおすすめ','ハイボール　梅酒'),('宵葉の一杯','柚子　焙じ茶　季節果実'),('今夜のうた','ひと息、ひと歌'),('SNACK MENU','水割り　小さなおつまみ')]
    for k,(a,b) in enumerate(labels,4):drawcell(k,(202,186,148),a,b,'none')
    # Tiny fictitious labels / record jackets: graphic art only, no brands.
    colors=[(68,83,75),(119,66,44),(56,76,99),(164,123,77),(87,66,98),(62,103,102),(175,130,101),(91,90,59)]
    for i,col in enumerate(colors,8):
        x=i%4*512*ss;y=i//4*512*ss;d.rectangle((x,y,x+512*ss,y+512*ss),fill=col)
        for j in range(9):
            y0=y+(76+j*42)*ss
            d.line((x+50*ss,y0,x+462*ss,y0-int(math.sin(j*.7)*48)*ss),fill=tuple(min(255,c+42) for c in col),width=(4+j%3)*ss)
        d.ellipse((x+147*ss,y+111*ss,x+365*ss,y+329*ss),outline=(221,197,149),width=5*ss)
        d.text((x+256*ss,y+404*ss),['樹音','夜航','木漏れ日','漂流','月影','風紋','枝先','余韻'][i-8],font=ft(39),anchor='mm',fill=(231,214,178))
    im.resize((2048,2048),Image.Resampling.LANCZOS).save(out/ATLAS)
    return dict(texture=ATLAS,rebaked=True,size=[2048,2048],antialias=2)


class Venue:
    def __init__(self,g,P,B,w,dep,idx,M,*,rpg_identity=False):
        self.rpg_identity=rpg_identity
        self.g,self.P,self.B,self.w,self.dep,self.idx,self.M=g,P,B,w,dep,idx,M
        self.group=g.group+'/Personality';self.solids=[];self.seats=[];self.components=[];self.lights=[]
        self.axes=[P(1,0,0)-P(0,0,0),P(0,1,0)-P(0,0,0),P(0,0,1)-P(0,0,0)]
    def section(self,name):self.g.group=self.group+'/'+name;self.components.append(name)
    def box(self,p,s,mat,solid=None,angle=0):
        c,s=tuple(p),tuple(s);co,si=math.cos(angle),math.sin(angle)
        axes=[self.axes[0]*co+self.axes[1]*si,-self.axes[0]*si+self.axes[1]*co,self.axes[2]]
        material=self.M.get(mat,mat)
        if material in [self.M.get(k) for k in ['night_wine','night_leather','night_indigo']]:
            from timber_craft import timber_box_mesh
            vv,ff,uv=timber_box_mesh(self.P(*c),s,axes,bevel=min(.035,min(s)*.20))
            self.g.add(vv,ff,material,uv)
        else:self.g.box(self.P(*c),s,material,axes)
        if solid:self.solid(solid,c,s,math.degrees(angle))
    def solid(self,name,center,size,yaw=0):
        count=sum(x['name']==name or x['name'].startswith(name+'_') for x in self.solids)
        self.solids.append(dict(name=name if not count else name+'_'+str(count+1),center=list(center),size=list(size),yaw=yaw))
    def beam(self,a,b,width,mat,depth=None):self.g.beam(self.P(*a),self.P(*b),width,self.M.get(mat,mat),depth)
    def sphere(self,p,scale,mat,n=16,rings=8):
        # Parametrize in LOCAL space so elliptical padding rotates with shops.
        v=[];f=[];uv=[]
        for k in range(rings+1):
            a=math.pi*k/rings
            for j in range(n+1):
                b=math.tau*j/n;q=np.array(p)+np.array(scale)*[math.sin(a)*math.cos(b),math.sin(a)*math.sin(b),math.cos(a)]
                v.append(self.P(*q));uv.append((j/n,k/rings))
                if k and j:
                    i=k*(n+1)+j
                    if k>1:f.append((i-n-2,i,i-n-1))
                    if k<rings:f.append((i-n-2,i-1,i))
        self.g.add(v,f,self.M.get(mat,mat),uv)
    def cyl(self,p,r,h,mat,n=20,r2=None):self.g.cylinder(self.P(*p),r,h,self.M.get(mat,mat),n,r2)
    def prism(self,poly,top,thickness,mat):
        v,f=poly_mesh(poly,top,thickness);uv=v[:,:2].copy();v=np.array([self.P(*p) for p in v]);self.g.add(v,f,self.M.get(mat,mat),uv)
    def panel(self,center,size,slot,mat='night_print',angle=0):
        x,y,z=center;w,h=size;c,s=math.cos(angle),math.sin(angle)
        def point(u,v):return self.P(x+c*u,y+s*u,z+v)
        q=[point(-w/2,-h/2),point(w/2,-h/2),point(w/2,h/2),point(-w/2,h/2)]
        # Local +Y face, flipped U agrees with viewing from street / front.
        col,row=slot%4,slot//4;lo=(col+.02)/4;hi=(col+.98)/4;vl=1-(row+.98)/4;vh=1-(row+.02)/4
        if slot<4 and w/h>2.1:
            span=min(.96,.96*h/w);mid=258/512
            vl=1-(row+mid+span/2)/4;vh=1-(row+mid-span/2)/4
        if self.rpg_identity is True:
            from rpg_shop_identities import night_rect
            replacement=night_rect(slot,size)
            if replacement is not None:lo,vl,hi,vh=replacement
        uv=[(hi,vl),(lo,vl),(lo,vh),(hi,vh)]
        self.g.quad(q[::-1],self.M.get(mat,mat),uv[::-1])
    def bottle(self,x,y,z,kind=0):
        # Same audited shelf envelope and three heights; modest shoulder and
        # glass-tint variety avoids a factory row without new material draws.
        h=.23+(kind%3)*.045;r=.043+(kind%2)*.01
        style=kind%4;shoulder=[.60,.74,.68,.80][style]
        neck=[.39,.46,.36,.43][style]
        mat=self.M['night_glass'];key=(self.g.group,mat)
        first=len(self.g.batches.get(key,{}).get('v',[]))
        pts=[self.P(x,y,z+t) for t in [0,.02,h*shoulder,h*(shoulder+.13),h,h+.04]]
        self.g.tube(pts,[r*.8,r,r,r*neck,r*neck,r*neck],mat,16)
        tint=[(.95,1,.78),(1,.63,.39),(.55,.74,.58),(.74,.88,1)][style]
        batch=self.g.batches[key];batch.setdefault('authored_tints',[]).append((first,len(batch['v']),tint))
        self.cyl((x,y,z+h+.045),r*.46,.025,'trim',12)
        # Wrap the label around the cylinder; no floating rectangular plaque.
        col,row=(8+kind%8)%4,(8+kind%8)//4
        verts=[];uv=[];faces=[];rad=r*1.008
        for j in range(9):
            a=-.67+1.34*j/8
            for zz,v in [(z+h*.325,1-(row+.98)/4),(z+h*.575,1-(row+.02)/4)]:
                verts.append(self.P(x+rad*math.sin(a),y+rad*math.cos(a),zz));uv.append(((col+.98-.96*j/8)/4,v))
            if j:
                i=(j-1)*2;faces.extend([(i,i+1,i+3),(i,i+3,i+2)])
        self.g.add(verts,faces,self.M['night_print'],uv)
    def tumbler(self,x,y,z,r=.042):
        self.cyl((x,y,z+.055),r,.11,'night_glass',16)
        self.cyl((x,y,z+.108),r*.84,.003,'tea',16)
        for k in range(8):
            a=math.tau*k/8;self.beam((x+r*.97*math.cos(a),y+r*.97*math.sin(a),z+.012),(x+r*.97*math.cos(a),y+r*.97*math.sin(a),z+.09),.004,'ceramic')
    def stemglass(self,x,y,z):
        self.cyl((x,y,z+.008),.046,.008,'night_glass',16)
        self.cyl((x,y,z+.07),.006,.12,'trim',10)
        self.cyl((x,y,z+.16),.010,.06,'night_glass',20,r2=.058)
        self.cyl((x,y,z+.192),.055,.005,'tea',20)
    def seat(self,x,y,height,kind,angle=0,exit=None):
        """Chair front points local -Y at angle zero. Seat datum is cushion top."""
        previous_group=self.g.group
        i=len(self.seats)+1;co,si=math.cos(angle),math.sin(angle)
        def Q(a,b,z):return(x+co*a-si*b,y+si*a+co*b,z)
        def C(p,s,m,solid=None):self.box(Q(*p),s,m,solid,angle)
        stool=height>.6;wide=.57 if kind=='club' else .49
        fabric={'snack':'night_wine','cocktail':'night_leather','listening':'night_indigo','club':'night_leather'}[kind]
        self.section('Seating/'+str(i)+'_'+kind)
        # Seat base is boxed for honest static clearance, with pillowed top.
        C((0,0,height-.050),(wide,.51,.10),fabric)
        # Slightly rounded, low-poly segmented cushion with tailored welt.
        for a in [-1,1]:
            for b in [-1,1]:
                base=Q(a*wide*.40,b*.19,.045);top=Q(a*wide*.34,b*.16,height-.12)
                self.beam(base,top,.031 if kind=='cocktail' else .052,'trim' if kind=='cocktail' else 'night_walnut')
        if stool:
            for a in [-1,1]:self.beam(Q(a*wide*.40,-.19,.30),Q(a*wide*.40,.19,.30),.016,'trim')
            self.beam(Q(-wide*.40,-.19,.30),Q(wide*.40,-.19,.30),.018,'trim')
        backh=.32 if kind=='cocktail' else .42
        if kind=='snack':
            C((0,.36,height+.17),(wide,.075,.34),fabric)
            self.sphere(Q(0,.36,height+.32),(wide/2,.052,.14),fabric,20,8)
            for a in [-.14,.14]:self.sphere(Q(a,.309,height+.20),(.014,.009,.014),'trim',8,5)
        elif kind=='club':
            C((0,.38,height+.22),(.63,.14,.48),fabric)
            for a in [-1,1]:
                C((a*.365,.005,height+.11),(.11,.52,.24),fabric)
                self.beam(Q(a*.365,-.2,height+.23),Q(a*.365,.2,height+.23),.026,'trim')
        elif kind=='cocktail':
            for a in [-1,1]:self.beam(Q(a*.20,.27,height-.05),Q(a*.20,.38,height+.36),.023,'trim')
            C((0,.36,height+.23),(.47,.075,.22),fabric)
            self.beam(Q(-.225,.36,height+.355),Q(.225,.36,height+.355),.019,'trim')
        else:
            for a in [-1,1]:self.beam(Q(a*.23,.29,height-.07),Q(a*.23,.40,height+.44),.036,'night_walnut')
            C((0,.37,height+.27),(.49,.08,.32),fabric)
            for a in [-1,1]:C((a*.33,.0,height+.17),(.050,.48,.065),'night_walnut')
        fp_width,fp_depth,fp_shift={'snack':(.52,.70,.08),'cocktail':(.52,.69,.07),'listening':(.74,.71,.08),'club':(.86,.73,.10)}[kind]
        pos=[x,y,height];ex=exit or [x-si*.82,y+co*.82,.06]
        self.seats.append(dict(id=f'{IDS[self.idx]}_Seat_{i}',position=pos,exit=list(ex),forward=[si,-co,0],seatType=kind,cushionTop=height,footprint=dict(center=list(Q(0,fp_shift,0)[:2]),size=[fp_width,fp_depth],angle=angle)))
        self.g.group=previous_group
    def banquette(self):
        self.section('Seating/Banquette')
        # Left-wall three-seat bench. Back / buttons / separate cushions.
        self.box((-2.43,-.72,.56),(.20,2.78,.99),'night_wine','BanquetteBack')
        self.box((-2.10,-.72,.22),(.90,2.72,.37),'night_walnut','BanquetteBase')
        for j,y in enumerate([-1.57,-.72,.13]):
            self.box((-1.99,y,.4275),(.66,.80,.105),'night_wine')
            self.sphere((-1.99,y,.444),(.335,.39,.036),'night_wine')
            self.box((-2.36,y,.78),(.13,.80,.46),'night_wine')
            for yy in [y-.18,y+.18]:self.sphere((-2.277,yy,.83),(.012,.018,.018),'trim',8,5)
            self.seats.append(dict(id=f'{IDS[self.idx]}_Seat_{len(self.seats)+1}',position=[-1.97,y,.48],exit=[-1.18,y,.06],forward=[1,0,0],seatType='snack_banquette',cushionTop=.48,footprint=dict(center=[-1.99,y],size=[.68,.82],angle=0)))
        for y in [-2.12,.68]:self.box((-2.02,y,.63),(.73,.10,.34),'night_wine','BanquetteArm')
    def shelf_bottles(self,x,y,z,width,levels,spacing=.23):
        for row in range(levels):
            zz=z+row*.45;self.box((x,y,zz),(width,.29,.055),'night_walnut')
            for j,xx in enumerate(np.arange(x-width/2+.16,x+width/2-.1,spacing)):self.bottle(float(xx),y+.015,zz+.03,j+row)
    def shell(self,kind):
        self.section('Architecture')
        w,d=self.w,self.dep
        self.box((0,-d/2,1.3),(w,.16,2.6),'dark','RearWall')
        self.box((0,-d/2+.1,1.69),(w-.32,.05,1.66),'wall')
        # Same outer side walls / posts as baseline, no change to deck or guards.
        for side in [-1,1]:
            self.box((side*w/2,-.65,1.3),(.14,d-1.30,2.6),'wood','SideWall'+str(side))
            for y in [-d/2,d/2]:self.box((side*(w/2-.1),y,1.4),(.20,.20,2.8),'dark','Post'+str(side)+'_'+str(y))
        self.box((0,d/2,2.64),(w+.3,.20,.22),'dark','Header')
        # Timber skirting adds human-scale joinery, not noisy exterior clutter.
        self.box((0,-d/2+.15,.17),(w-.25,.10,.27),'night_walnut')
        for x in [-2.52,2.52]:self.box((x,-d/2+.17,1.32),(.09,.09,2.53),'dark')
        if kind=='snack':
            from high_detail import roof_tiles
            roof_tiles(self.g,self.P,w,d,self.M['tile'],self.M['dark'])
            # Bay-specific upholstered valance, not the old full-width noren.
            for j in range(8):
                x=-2.4+j*.25
                self.sphere((x,d/2+.05,2.39),(.155,.05,.11),'night_wine',12,6)
            self.box((-1.54,d/2+.02,2.46),(2.1,.08,.23),'night_wine')
            # Discrete right glazed-style bay: real frame, open center.
            self.box((1.67,d/2-.02,.39),(2.30,.12,.78),'night_walnut','FrontBaySill')
            for x in [.50,2.79]:self.box((x,d/2-.02,1.71),(.065,.12,1.86),'trim')
            self.box((1.64,d/2-.02,2.25),(2.35,.12,.065),'trim')
            for x in [.78,2.49]:self.box((x,d/2-.02,1.55),(.055,.04,1.33),'trim')
            # Opaque narrow reeded strips, not a fake transparent plane.
            for x in np.arange(2.51,2.73,.055):self.box((x,d/2-.01,1.51),(.025,.05,1.4),'night_glass')
        else:
            # Cocktail = two unequal copper-like roof planes; music = low
            # mono-pitch with visible seam ribs, genuinely distinct silhouettes.
            ridge=-.50 if kind=='cocktail' else -d/2-.55
            half=d/2+.62;left=-w/2-.55;right=w/2+.55
            def h(y):
                if kind=='cocktail':return 3.63-(abs(y-ridge)/(half+abs(ridge)))*.73
                return 3.35-(y+half)/(2*half)*.49
            ys=[-half,ridge,half] if kind=='cocktail' else [-half,half]
            for ya,yb in zip(ys,ys[1:]):
                roof=[(left,ya,h(ya)),(right,ya,h(ya)),(right,yb,h(yb)),(left,yb,h(yb))]
                top=[self.P(*q) for q in roof];bottom=[self.P(x,y,z-.035) for x,y,z in roof]
                self.g.quad(top,self.M['night_roof'])
                self.g.quad(bottom[::-1],self.M['night_roof'])
                for j in range(4):
                    k=(j+1)%4;self.g.quad([top[j],bottom[j],bottom[k],top[k]],self.M['night_roof'])
                for x in np.arange(left,right,.32):self.beam((x,ya,h(ya)+.013),(x,yb,h(yb)+.013),.027,'night_roof',.045)
            for side in [-1,1]:
                y=side*half;self.beam((left,y,h(y)-.05),(right,y,h(y)-.05),.16,'dark',.16)
            for x in [-2.7,-1.35,0,1.35,2.7]:
                self.beam((x,-d/2,2.7),(x,d/2+.48,2.7),.10,'night_walnut',.14)
            if kind=='cocktail':
                for x in [2.43,2.66]:self.box((x,d/2,1.34),(.10,.13,2.52),'night_walnut')
                self.box((-2.50,d/2,1.36),(.47,.15,2.48),'night_walnut','PortalLeft')
            else:
                for x in np.arange(-2.62,2.7,.20):self.box((x,d/2,2.42),(.055,.12,.30),'night_walnut')
                self.box((-2.42,d/2,.45),(.66,.14,.9),'night_walnut','AcousticFrontEnd')
    def close_roof(self,kind):
        self.section('RoofEndJoinery')
        d=self.dep;w=self.w
        if kind=='snack':profile=[(float(y),3.80-1.13*(abs(y)/(d/2+.65))**.83+.075*(abs(y)/(d/2+.65))**6) for y in np.linspace(-d/2,d/2,13)]
        elif kind=='cocktail':profile=[(-d/2,3.16),(-.50,3.57),(d/2,2.97)]
        else:profile=[(-d/2,3.27),(d/2,2.89)]
        for side in [-1,1]:
            x=side*(w/2-.035);points=[(x,-d/2,2.60),(x,d/2,2.60)]+[(x,y,z) for y,z in profile[::-1]]
            vv=[self.P(*p) for p in points];faces=[(0,j,j+1) for j in range(1,len(vv)-1)]
            if side<0:faces=[f[::-1] for f in faces]
            self.g.add(vv,faces,self.M['dark'],[(p[1],p[2]) for p in points])
            inside=[self.P(px-side*.08,py,pz) for px,py,pz in points]
            self.g.add(inside,[f[::-1] for f in faces],self.M['dark'],[(p[1],p[2]) for p in points])
            for j in range(len(vv)):
                k=(j+1)%len(vv);self.g.quad([vv[j],inside[j],inside[k],vv[k]],self.M['dark'])
            self.beam((x,-d/2,2.65),(x,d/2,2.65),.105,'dark',.16)
            for y in [-1.8,-.9,0,.9,1.8]:
                z=float(np.interp(y,[p[0] for p in profile],[p[1] for p in profile]))
                self.beam((x,y,2.65),(x,y,z),.055,'night_walnut')
        for y,h in [(profile[0][0],profile[0][1]),(profile[-1][0],profile[-1][1])]:
            self.box((0,y,(2.73+h)/2),(w,.10,max(.02,h-2.73)),'dark')
    def sign(self,kind):
        self.section('Signage')
        if kind=='snack':
            # Shaped oval sign assembled as actual ellipse, inset face.
            self.sphere((.30,3.48,2.60),(1.30,.080,.38),'night_walnut',40,12)
            self.box((.30,3.558,2.60),(1.93,.012,.48),'trim')
            self.panel((.30,3.568,2.60),(1.85,.44),0)
            for x in [-.65,1.25]:self.beam((x,2.775,2.85),(x,3.46,2.93),.025,'trim')
        elif kind=='cocktail':
            self.box((-.30,3.47,2.57),(2.06,.105,.56),'night_walnut')
            self.panel((-.30,3.527,2.57),(1.99,.49),1)
            for x in [-1.15,.55]:self.beam((x,2.775,2.91),(x,3.47,2.86),.019,'trim')
            for x in [-1.15,.55]:self.box((x,2.755,2.91),(.10,.03,.10),'trim')
            self.box((-2.48,2.88,1.72),(.38,.085,.76),'night_walnut')
            self.panel((-2.48,2.928,1.72),(.32,.69),1)
        else:
            self.box((-.15,3.45,2.60),(2.73,.08,.47),'night_walnut')
            self.panel((-.15,3.50,2.60),(2.63,.40),2)
            for x in [-1.05,.78]:self.beam((x,2.775,2.83),(x,3.45,2.84),.020,'trim')
            # Framed disc hanging at right-hand edge, within existing eave.
            for x in [2.12,2.77]:self.beam((x,3.44,2.78),(x,3.44,3.49),.032,'trim')
            for z in [2.78,3.49]:self.beam((2.12,3.44,z),(2.77,3.44,z),.032,'trim')
            self.sphere((2.445,3.46,3.14),(.295,.041,.295),'night_speaker',32,12)
            self.panel((2.445,3.508,3.14),(.30,.30),2)
    def snack(self):
        self.shell('snack');self.close_roof('snack');self.sign('snack');self.banquette()
        self.section('BentSnackCounter')
        poly=unary_union([rect(-.57,.34,2.22,.98),rect(1.63,-1.60,2.22,.78)]).buffer(.09,join_style=1).buffer(-.09,join_style=1)
        self.prism(poly,1.045,.105,'night_walnut')
        self.solid('SnackTopFront',(.825,.66,.9925),(2.79,.64,.105))
        self.solid('SnackTopReturn',(1.925,-.63,.9925),(.59,1.94,.105))
        self.box((.825,.66,.47),(2.62,.45,.88),'night_wine','SnackCounterFront')
        self.box((1.93,-.54,.47),(.43,2.04,.88),'night_wine','SnackCounterReturn')
        for x in np.arange(-.39,2.1,.17):self.box((x,.898,.50),(.018,.018,.69),'trim')
        self.beam((-.40,1.095,.25),(2.04,1.095,.25),.025,'trim')
        for j,x in enumerate([-.39,.75,1.89]):
            self.seat(x,1.54,.70,'snack',exit=[x+.57,1.54,.06])
            self.cyl((x,.76,1.049),.066,.005,'wall',20)
            self.tumbler(x,.76,1.05)
        self.section('BoothTable')
        self.box((-.55,-.67,.67),(.42,1.66,.075),'night_walnut','BoothTable')
        for y in [-1.35,-.1]:self.box((-.55,y,.34),(.10,.10,.62),'trim','TableLeg')
        for y in [-1.38,-.71,-.08]:self.tumbler(-.55,y,.714,.037)
        self.section('BottleKeepWall')
        self.box((.12,-2.53,1.68),(4.3,.035,1.36),'night_wine')
        self.shelf_bottles(.13,-2.345,.91,3.75,3,.26)
        self.solid('BottleKeepShelves',(.13,-2.345,1.59),(3.75,.29,1.42))
        for x in [-1.81,-.54,.73,2.0]:self.box((x,-2.35,1.58),(.053,.28,1.39),'trim')
        self.panel((.14,-2.195,2.29),(1.42,.30),3)
        # Wallpaper brass diamonds, bounded behind the bench.
        for y in np.arange(-1.98,.66,.28):
            for z in [1.35,1.65,1.95,2.25]:
                for a,b in [((y-.10,z),(y,z+.11)),((y,z+.11),(y+.10,z)),((y+.10,z),(y,z-.11)),((y,z-.11),(y-.10,z))]:self.beam((-2.915,*a),(-2.915,*b),.008,'trim')
        self.section('SnackService')
        cx,cy,zz=.20,.54,1.047;profile=[(.032,0),(.090,.007),(.106,.032),(.098,.036),(.073,.018),(.024,.014)]
        vv=[];uu=[];ff=[]
        for row,(rad,z0) in enumerate(profile):
            for j in range(17):
                a=j*math.tau/16;vv.append(self.P(cx+rad*math.cos(a),cy+rad*math.sin(a),zz+z0));uu.append((j/16,row/5))
                if row and j:
                    i=row*17+j;ff.extend([(i-18,i-17,i),(i-18,i,i-1)])
        self.g.add(vv,ff,self.M['ceramic'],uu)
        self.cyl((cx,cy,zz+.002),.032,.004,'ceramic',16)
        self.cyl((cx,cy,zz+.012),.024,.004,'ceramic',16)
        for j in range(5):
            a=j*2.399;rr=.034+.008*(j%2);self.sphere((cx+rr*math.cos(a),cy+rr*math.sin(a),zz+.027),(.014,.010,.012),'food',10,5)
        self.section('KaraokeConsoleAndFlowers')
        self.box((2.02,-1.45,1.20),(.32,.34,.23),'iron')
        self.panel((2.02,-1.272,1.23),(.27,.13),6)
        for x in [1.94,2.05]:self.sphere((x,-1.258,1.12),(.015,.011,.015),'trim',8,4)
        self.cyl((1.92,-.95,1.12),.055,.15,'night_walnut',16)
        for xx,yy in [(1.895,-.955),(1.95,-.93)]:
            self.beam((xx,yy,1.14),(xx+.026,yy,1.34),.022,'iron')
            self.sphere((xx+.028,yy,1.357),(.033,.033,.042),'night_speaker',16,8)
            self.cyl((xx+.026,yy,1.321),.025,.02,'trim',12)
        self.cyl((1.30,.48,1.15),.065,.20,'ceramic',20,r2=.044)
        for k in range(5):
            a=k*2.399;dx=.12*math.cos(a);dy=.11*math.sin(a)
            self.beam((1.3,.48,1.19),(1.3+dx,.48+dy,1.43+k*.018),.009,'night_glass')
            self.sphere((1.3+dx,.48+dy,1.43+k*.018),(.045,.045,.025),'night_wine',12,6)
        self.section('MedallionCeiling')
        self.cyl((-.35,-.1,2.55),.44,.06,'night_walnut',32)
        self.cyl((-.35,-.1,2.50),.34,.045,'trim',32)
        for k in range(5):
            a=math.tau*k/5;xy=(-.35+.45*math.cos(a),-.1+.45*math.sin(a))
            self.beam((-.35,-.1,2.48),(*xy,2.32),.018,'trim')
            self.cyl((*xy,2.28),.085,.11,'ceramic',16,r2=.13)
            self.cyl((*xy,2.217),.078,.012,'window',16)
        self.lights.append(dict(position=[-.35,-.1,2.12],range=3.4,strength=1.4))
    def cocktail(self):
        self.shell('cocktail');self.close_roof('cocktail');self.sign('cocktail')
        self.section('SteppedWalnutCounter')
        poly=Polygon([(-1.23,.70),(1.69,.70),(1.69,.38),(2.36,.38),(2.36,1.30),(1.96,1.52),(-1.23,1.52)])
        self.prism(poly,1.08,.12,'night_walnut')
        self.solid('CocktailTopMain',(.23,1.11,1.02),(2.92,.82,.12))
        self.solid('CocktailTopStep',(2.025,.84,1.02),(.67,.92,.12))
        self.solid('CocktailTopCorner',(1.825,1.41,1.02),(.27,.22,.12))
        self.box((.505,1.11,.48),(3.32,.55,.91),'night_walnut','CocktailCounter')
        self.box((2.02,.87,.48),(.51,.90,.91),'night_walnut','CocktailStep')
        self.box((.365,1.405,.60),(3.12,.013,.024),'trim')
        for x in np.arange(-1.08,2.06,.15):self.box((x,1.395,.48),(.033,.019,.72),'dark')
        self.beam((-1.14,1.64,.27),(1.98,1.64,.27),.023,'trim')
        for x in [-.99,.05,1.09,2.13]:
            self.seat(x,2.07,.75,'cocktail',exit=[x-.52,2.07,.06]);self.stemglass(x,1.22,1.085)
        for x in [-1.89,-.80]:self.seat(x,-1.29,.48,'club',math.pi,exit=[x,-.39,.06])
        self.section('LoungeTable')
        self.cyl((-1.35,-.57,.52),.22,.06,'night_walnut',28)
        self.solid('LoungeTable',(-1.35,-.57,.52),(.44,.44,.06))
        self.cyl((-1.35,-.57,.28),.035,.43,'trim',16)
        self.cyl((-1.35,-.57,.045),.16,.04,'trim',20)
        self.tumbler(-1.42,-.57,.555,.035)
        self.section('GeometricBackbar')
        self.box((.65,-2.48,1.60),(3.99,.12,1.64),'night_glass')
        for x in [-1.36,-.36,.64,1.64,2.64]:self.box((x,-2.28,1.56),(.06,.39,1.71),'night_walnut')
        for z in [.71,1.26,1.81,2.39]:self.box((.64,-2.28,z),(4.06,.40,.065),'night_walnut')
        for r,z in enumerate([.75,1.30,1.85]):
            for j,x in enumerate([-.99,-.71,.03,.32,.99,1.29,1.99,2.28]):self.bottle(x,-2.2,z,j+r)
        # Quiet cabinets and original framed menu behind lounge.
        self.box((1.0,-2.25,.36),(3.3,.50,.63),'night_walnut','BackbarCabinet')
        for x in [-.13,.96,2.07]:self.box((x,-1.99,.39),(.98,.025,.45),'dark');self.box((x,-1.965,.56),(.19,.015,.014),'trim')
        self.panel((-2.12,-2.48,1.72),(.63,.88),5)
        self.section('MixologyTools')
        self.cyl((1.97,.90,1.22),.055,.26,'iron',20,r2=.040)
        self.cyl((1.97,.90,1.37),.033,.045,'trim',16)
        self.cyl((1.66,.94,1.13),.038,.075,'trim',16,r2=.019)
        self.cyl((1.66,.94,1.196),.019,.057,'trim',16,r2=.033)
        self.box((1.84,.61,1.153),(.36,.21,.045),'night_glass')
        for j in range(3):self.sphere((1.75+j*.07,.59,1.186),(.031,.031,.026),'sweet',12,6)
        self.section('PendantCeiling')
        for x in [-.48,.62,1.72]:
            self.beam((x,1.10,2.80),(x,1.10,2.27),.012,'iron')
            self.cyl((x,1.10,2.24),.21,.18,'night_walnut',32,r2=.075)
            self.cyl((x,1.10,2.145),.19,.012,'window',28)
            for k in range(16):
                a=math.tau*k/16;self.beam((x+.20*math.cos(a),1.1+.20*math.sin(a),2.16),(x+.08*math.cos(a),1.1+.08*math.sin(a),2.32),.010,'trim')
        self.lights.extend([dict(position=[.6,1.1,2.02],range=3.7,strength=1.5),dict(position=[-.8,-1.5,2.18],range=2.2,strength=.7)])
    def speaker(self,x,y,z):
        self.box((x,y,z),(.52,.38,.78),'night_walnut')
        self.box((x,y+.198,z),(.47,.022,.73),'night_speaker')
        # Driver axes face local front, not global Z. Open concentric meshes.
        for zz,r in [(z-.11,.167),(z+.23,.068)]:
            for rad,depth,mat in [(r,.21,'iron'),(r*.84,.218,'night_speaker'),(r*.35,.239,'night_speaker')]:
                v=[];uv=[];faces=[]
                for j in range(33):
                    a=math.tau*j/32;v.append(self.P(x+rad*math.cos(a),y+depth,zz+rad*math.sin(a)));uv.append((.5+.5*math.cos(a),.5+.5*math.sin(a)))
                v.append(self.P(x,y+depth-.012,zz));uv.append((.5,.5))
                for j in range(32):faces.append((33,j,j+1))
                self.g.add(v,faces,self.M[mat],uv)
    def music(self):
        self.shell('music');self.close_roof('music');self.sign('music')
        self.section('RightAngleListeningBar')
        poly=unary_union([rect(1.56,-.53,2.10,1.96),rect(.77,-.97,2.10,-.41)])
        self.prism(poly,1.0,.095,'night_walnut')
        self.solid('MusicTopLong',(1.83,.715,.9525),(.54,2.49,.095))
        self.solid('MusicTopReturn',(1.435,-.69,.9525),(1.33,.56,.095))
        self.box((1.80,.705,.46),(.46,2.29,.87),'night_walnut','MusicCounterLong')
        self.box((1.445,-.69,.46),(1.13,.35,.87),'night_walnut','MusicCounterReturn')
        for y in np.arange(-.37,1.83,.16):self.box((1.562,y,.48),(.019,.035,.74),'dark')
        self.beam((1.59,-.37,.25),(1.59,1.81,.25),.025,'iron')
        for y in [.04,.86,1.68]:
            self.seat(.72,y,.70,'listening',math.pi/2,exit=[1.27,y,.06]);self.tumbler(1.72,y,1.005)
        for x in [-1.84,-.86,.12]:self.seat(x,-1.15,.47,'listening',exit=[x,-1.74,.06])
        self.section('RecordLibrary')
        for x in [-2.55,2.45]:self.speaker(x,-2.31,1.44)
        self.box((-.25,-2.35,.68),(3.59,.43,.12),'night_walnut','RecordCabinet')
        self.box((-.25,-2.44,.33),(3.59,.26,.57),'night_walnut','RecordCabinetBase')
        # Distinct twelve-inch sleeves lean in real shelf bins.
        for j,x in enumerate(np.arange(-1.85,1.46,.14)):
            self.box((x,-2.21,.94),(.032,.28,.42),'night_walnut')
            if j%3==0:self.panel((x+.07,-2.035,1.03),(.25,.32),8+j%8)
        for z in [1.37,2.05]:self.box((-.22,-2.40,z),(3.54,.29,.055),'night_walnut')
        for j,x in enumerate([-1.55,-.80,-.05,.70,1.35]):
            self.box((x,-2.46,1.71),(.56,.045,.54),'night_walnut');self.panel((x,-2.425,1.71),(.49,.49),8+j)
        self.section('TurntableAndAmplifier')
        self.box((1.49,-.69,1.075),(.55,.39,.08),'iron')
        self.cyl((1.43,-.69,1.121),.152,.012,'night_speaker',32)
        self.cyl((1.43,-.69,1.129),.044,.006,'trim',20)
        self.cyl((1.43,-.69,1.135),.004,.007,'iron',8)
        self.beam((1.72,-.80,1.14),(1.64,-.60,1.14),.012,'trim')
        self.beam((1.64,-.60,1.14),(1.56,-.63,1.137),.010,'trim')
        self.box((1.93,-.66,1.106),(.25,.29,.15),'iron')
        for j,x in enumerate([1.84,1.93,2.01]):self.sphere((x,-.505,1.11),(.014,.008,.014),'trim',8,4)
        self.section('AcousticSlatCeiling')
        for x in np.arange(-2.54,2.50,.145):self.box((x,-.37,2.56),(.055,3.85,.085),'night_walnut')
        for x in [-1.66,.1,1.98]:
            self.box((x,-.55,2.47),(.74,.10,.075),'iron')
            self.box((x,-.55,2.427),(.62,.065,.008),'window')
        self.lights.extend([dict(position=[-1.0,-.4,2.25],range=3.6,strength=1.25),dict(position=[1.85,1.0,2.20],range=2.7,strength=.8)])


def build_venue(g,P,B,w,dep,idx,M,*,seat_specs=None,lantern=None,rpg_identity=False):
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    if idx not in IDS:raise ValueError('Nightlife module owns only original indices 3, 5 and 6')
    if abs(w-6)>1e-8 or abs(dep-5.4)>1e-8:raise ValueError('Review geometry before changing authorized 6 x 5.4 m footprint')
    if seat_specs is not None and len(seat_specs)!=6:raise ValueError('Nightlife requires exactly six station IDs per venue')
    if seat_specs is not None and [s.get('id') for s in seat_specs]!=[f'{IDS[idx]}_Seat_{i}' for i in range(1,7)]:raise ValueError('Station IDs/order differ from authorized venue contract')
    before=sum(len(b['f']) for b in g.batches.values());old=g.group
    v=Venue(g,P,B,w,dep,idx,M,rpg_identity=rpg_identity)
    {'S04':v.snack,'S06':v.cocktail,'S07':v.music}[IDS[idx]]()
    g.group=old
    assert len(v.seats)==6
    routes={3:[dict(name='entrance',points=[[-1.55,3.7,.06],[-1.55,2.35,.06],[-1.55,1.05,.06]],targetClearWidth=.8),dict(name='booth_aisle',points=[[-1.55,1.05,.06],[-1.18,.85,.06],[-1.18,-1.8,.06]],targetClearWidth=.5),dict(name='counter_customer',points=[[-1.55,2.28,.06],[1.6,2.28,.06]],targetClearWidth=.5),dict(name='staff',points=[[-1.55,3.7,.06],[-1.55,1.15,.06],[-1.18,.90,.06],[-1.18,-1.85,.06],[.7,-1.85,.06],[.7,-.45,.06]],targetClearWidth=.5)],5:[dict(name='entrance',points=[[-1.91,3.7,.06],[-1.91,1.8,.06],[-1.91,-.35,.06]],targetClearWidth=.8),dict(name='customer',points=[[-1.91,2.92,.06],[1.74,2.92,.06]],targetClearWidth=.8),dict(name='staff',points=[[-1.91,3.7,.06],[-1.91,1.8,.06],[-1.91,.05,.06],[.3,.05,.06],[.3,-1.5,.06],[1.8,-1.5,.06],[1.8,.0,.06],[.8,.27,.06]],targetClearWidth=.8)],6:[dict(name='entrance',points=[[-1.25,3.7,.06],[-1.25,1.6,.06],[-1.25,-.72,.06]],targetClearWidth=.8),dict(name='customer',points=[[-1.84,-.72,.06],[-.12,-.72,.06],[-.12,1.68,.06]],targetClearWidth=.5),dict(name='staff',points=[[1.45,3.7,.06],[1.45,2.31,.06],[2.45,2.31,.06],[2.45,-1.6,.06]],targetClearWidth=.5)]}[idx]
    if idx==5:
        routes.append(dict(name='public_lounge',points=[[-1.91,3.7,.06],[-1.91,.05,.06],[-.80,.05,.06],[-.80,-.39,.06]],targetClearWidth=.5))
    if idx==6:
        routes=[r for r in routes if r['name']!='customer']
        routes.append(dict(name='counter_customer',points=[[1.27,.04,.06],[1.27,2.40,.06],[-1.25,2.40,.06]],targetClearWidth=.5))
        routes.append(dict(name='listening_customer',points=[[-1.25,1.6,.06],[-1.25,-.25,.06],[-2.55,-.25,.06],[-2.55,-1.74,.06],[.12,-1.74,.06]],targetClearWidth=.5))
        for r in routes:
            if r['name']=='entrance':r['points']=[[-1.25,3.7,.06],[-1.25,1.6,.06],[-1.25,-.25,.06]]
    for route in routes:
        route['role']='staff' if route['name']=='staff' else ('entrance' if route['name']=='entrance' else 'customer')
        route['requiredRadius']=.325 if route['role'] in ['entrance','staff'] else .25
        route['requiredHeight']=2.2
        if route['role']=='staff':route['servicePoint']={3:[.7,-.45,.06],5:[.8,.27,.06],6:[2.45,.8,.06]}[idx]
    design=dict(version=VERSION,components=v.components,seatCount=6,structuralEnvelopePreserved=True)
    result=dict(design=design,routes=routes,version=VERSION,shop=IDS[idx],name=NAMES[idx],theme={3:'retro_snack',5:'cocktail_whisky',6:'music_listening'}[idx],completeVisualReplacement=True,triangleCount=sum(len(b['f']) for b in g.batches.values())-before,components=v.components,seatOverrides=v.seats,solids=v.solids,lights=v.lights,steam=[],stationCount=6,coordinates='shop-local Z-up, metres',collisionApplied=False,testedInUnity=False,testedInVRChat=False)
    if rpg_identity is True:
        from rpg_shop_identities import IDENTITIES as RPG_IDENTITIES
        result['name']=result['displayName']=RPG_IDENTITIES[idx]['name']
    return result
