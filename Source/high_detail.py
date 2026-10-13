"""High-detail visual authoring. No physics changes; source coordinates are Z-up."""
import math, json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from io import BytesIO
from shapely.geometry import box as rect
from world_geometry import poly_mesh
TAU=math.tau

def detailed_textures(out,font):
    out=Path(out);n=1024;rng=np.random.default_rng(619);y,x=np.mgrid[:n,:n]/n
    def save(name,a):
        im=Image.fromarray(np.uint8(np.clip(a,0,255)));buf=BytesIO();im.save(buf,format='PNG');data=buf.getvalue()
        Image.open(BytesIO(data)).load();(out/name).write_bytes(data)
    def surface(name,h,color,rough=.8,strength=2):
        gx=(np.roll(h,-1,1)-np.roll(h,1,1))*strength;gy=(np.roll(h,-1,0)-np.roll(h,1,0))*strength
        normal=np.stack([-gx,-gy,np.ones_like(h)],axis=2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
        save(name+'_normal.png',(normal*.5+.5)*255)
        save(name+'_arm.png',np.stack([np.clip(.82+h*.22,0,1),np.clip(rough+(h-.5)*.14,.1,1),np.zeros_like(h)],axis=2)*255)
        save(name+'.png',np.clip(.76+h[:,:,None]*.40,0,1.2)*np.array(color))
    noise=rng.normal(0,.07,(n,n));h=.5+noise+.1*np.sin(x*TAU*151)*np.sin(y*TAU*179)
    surface('tile_clay',h,[103,113,119],.78,1.7)
    h=.5+noise*.45+.18*np.sin(x*TAU*192)+.16*np.cos(y*TAU*198)
    surface('woven',h,[227,220,199],.95,.8)
    h=.5+noise*.8+.08*np.sin(x*TAU*11+y*TAU*7)*np.sin(y*TAU*21)
    surface('plaster',h,[171,156,126],.96,1.3)
    h=.5+.17*np.sin(x*TAU*5+np.sin(y*TAU*7)*.65)+.10*np.sin(x*TAU*19-y*TAU*17)
    surface('water',h,[41,69,84],.22,.65)
    # Leaf veins and mottled chlorophyll, UV-aligned to the authored leaf shape.
    lateral=np.abs(x-.5)*2;vein=np.exp(-((x-.5)*n/3.2)**2)
    branch=np.exp(-(np.sin((y-lateral*.38)*TAU*10)*23)**2)*(1-lateral)
    leaf=.51+.20*(1-lateral)+noise*.45+.08*np.sin(x*TAU*11+y*TAU*6)
    col=np.stack([leaf*.62+.05*vein,leaf*.91+.11*vein+branch*.06,leaf*.26+branch*.03],axis=2)
    save('leaf.png',col*255)
    surface('leaf_detail',np.clip(.3+vein*.5+branch*.3,0,1),[255,255,255],.61,2.5)
    # Authored compound-leaf alpha texture supplements individual near leaves.
    # Native texture art: serrated silhouettes, petioles, veins and colour variation.
    sprite=Image.new('RGBA',(1024,1024),(34,56,16,0));sd=ImageDraw.Draw(sprite)
    stem=[(135,948),(270,781),(418,615),(563,447),(696,272),(815,79)]
    sd.line(stem,fill=(91,83,42,255),width=13)
    for j in range(16):
        t=.12+j*.05;cx=155+675*t;cy=955-900*t;side=-1 if j%2 else 1
        end=(cx+side*rng.uniform(135,210),cy-rng.uniform(35,115))
        sd.line([(cx,cy),end],fill=(90,87,43,255),width=5)
        leafim=Image.new('RGBA',(200,340),(44,77,26,0));ld=ImageDraw.Draw(leafim)
        outline=[]
        for k in range(31):
            t0=k/30;w0=math.sin(math.pi*t0)**.82*83*(1+(.035 if k%2 else -.035));outline.append((100-w0,8+t0*320))
        for k in range(30,-1,-1):
            t0=k/30;w0=math.sin(math.pi*t0)**.82*83*(1+(.035 if k%2 else -.035));outline.append((100+w0,8+t0*320))
        tint=(int(rng.uniform(46,71)),int(rng.uniform(79,111)),int(rng.uniform(26,40)),255)
        ld.polygon(outline,fill=tint);ld.line((100,22,100,327),fill=(110,129,60,255),width=3)
        for k in range(1,10):
            yy=31+k*27;ww=math.sin((yy-8)/320*math.pi)**.82*77
            for si in [-1,1]:ld.line((100,yy+12,100+si*ww,yy-21),fill=(tint[0]+15,tint[1]+13,tint[2]+9,255),width=2)
        leafim=leafim.rotate(-side*48+rng.uniform(-12,12),resample=Image.Resampling.BICUBIC,expand=True)
        leafim.thumbnail((255,280),Image.Resampling.LANCZOS)
        sprite.alpha_composite(leafim,(int(end[0]-leafim.width*.5),int(end[1]-leafim.height*.48)))
    save('foliage_spray.png',np.asarray(sprite))
    # Restaurant-specific paper menus and sake labels. Real Japanese glyphs.
    atlas=Image.new('RGB',(2048,2048),(212,195,153));d=ImageDraw.Draw(atlas)
    f=ImageFont.truetype(str(font),49);sm=ImageFont.truetype(str(font),25)
    menus=[['本日の炭火','ねぎま　砂肝','つくね　ししとう','炭火 梢'],['風待の一杯','醤油らーめん','煮玉子　焼豚','麺処 風待'],['おでん 灯','大根　玉子','厚揚げ　こんにゃく','出汁の香り'],['地酒のお品書き','純米　吟醸','冷酒　熱燗','酒処 根っこ'],['枝先茶屋','煎茶　ほうじ茶','抹茶と季節の菓子','ひとやすみ'],['宵葉の酒肴','梅酒　柚子酒','枝豆　冷奴','夜風と一杯'],['山椒屋','鶏と山椒','旬野菜の小皿','香りを愉しむ'],['木の実','栗ようかん','三色だんご','季節のお茶']]
    for i,lines in enumerate(menus):
        x0=(i%4)*512;y0=(i//4)*768
        d.rectangle((x0+10,y0+12,x0+502,y0+748),fill=(225-i*2,211-i*3,176-i*2),outline=(79,53,33),width=7)
        for k,ln in enumerate(lines):d.text((x0+256,y0+95+k*151),ln,font=f,anchor='mm',fill=(44,36,27))
        d.line((x0+60,y0+150,x0+452,y0+150),fill=(111,45,31),width=3)
    for i in range(16):
        x0=(i%8)*256;y0=1536+(i//8)*256
        d.rectangle((x0+4,y0+5,x0+252,y0+251),fill=(235,222,183),outline=(148,56,39),width=5)
        d.text((x0+128,y0+106),['梢','宵葉','根酒','月影','山水','純米','吟醸','木霊'][i%8],font=f,anchor='mm',fill=(44,38,30))
        d.text((x0+128,y0+189),'樹上醸造',font=sm,anchor='mm',fill=(127,57,44))
    a=np.asarray(atlas).astype(float);a*=rng.uniform(.93,1.035,a.shape[:2])[:,:,None];save('menus.png',a)
    # Weather and edge darkening on the existing sign atlas.
    im=Image.open(out/'signs.png').convert('RGB');a=np.asarray(im).astype(float);yy,xx=np.mgrid[:a.shape[0],:a.shape[1]]
    edge=np.minimum.reduce([xx/(a.shape[1]*.025),(a.shape[1]-xx)/(a.shape[1]*.025),(yy%128)/7,(128-yy%128)/7])
    a*=np.clip(.78+edge*.22,.78,1)[:,:,None]*rng.uniform(.94,1.025,a.shape[:2])[:,:,None];save('signs.png',a)


def leaf(g,p,right,length,material,scale=1):
    """Folded, slightly serrated broadleaf: actual silhouette, no billboard block."""
    p=np.array(p);r=np.array(right);l=np.array(length);normal=np.cross(r,l);normal/=max(np.linalg.norm(normal),1e-8)
    v=[];uv=[];faces=[]
    for k in range(7):
        t=k/6;width=math.sin(math.pi*t)**.82*(1+.07*(-1)**k)
        mid=p+l*(t-.5)+normal*(math.sin(math.pi*t)*.026*scale)
        for j in [-1,0,1]:
            v.append(mid+r*width*j+normal*(abs(j)*-.018*scale));uv.append(((j*width+1)/2,t))
        if k:
            b=(k-1)*3
            faces.extend([(b,b+1,b+4),(b,b+4,b+3),(b+1,b+2,b+5),(b+1,b+5,b+4)])
    g.add(v,faces,material,uv)


def roof_tiles(g,P,w,dep,tile,dark,detail=True):
    """Overlapping clay shells, with open eave mouths instead of solid beads.

    The material is already double-sided in the glTF/Unity importers. Every
    lip is therefore emitted once, with its normal facing away from the roof.
    Changes are visual only, use the existing clay PBR, and consume no RNG.
    """
    length=dep/2+.65
    def H(y):return 3.83-1.13*(abs(y)/length)**.83+.075*(abs(y)/length)**6
    cols=max(1,round((w+1.05)/.295));step=(w+1.05)/cols
    def vertex_start():return len(g.batches.get((g.group,tile),{}).get("v",[]))
    def clay_tint(first,tone,warmth=0):
        b=g.batches[(g.group,tile)]
        b.setdefault("authored_tints",[]).append(
            (first,len(b["v"]),(tone*(1+warmth),tone,tone*(1-warmth))))
    for side in [-1,1]:
        for course,yy in enumerate(np.arange(.01,length,.405)):
            end=min(length+.04,yy+.47);at_eave=end>=length+.039
            for j in range(cols):
                # Sub-millimetre seating variation and UV offsets break the
                # stamped repetition without adding materials or noisy chips.
                phase=(math.sin(j*19.19+course*7.13+side*3.1)*43758.5453)%1
                xx=-w/2-.525+j*step+.0015
                width=step-.003
                crown=.052+(phase-.5)*.003
                seat=(phase-.5)*.0015
                # Each terminal tile has a shallow, projecting drip lip.
                lip_y=end+(.025 if at_eave and detail else 0)
                first=vertex_start();v=[];uv=[];ff=[]
                # A 12 mm raised course nose sits on the tile below and
                # makes each overlapping course readable at grazing angles.
                for row,y in enumerate([yy,lip_y]):
                    for k in range(7):
                        u=k/6;arch=math.sin(u*math.pi)*crown
                        v.append(P(xx+u*width,side*y,H(y)+arch+.022+seat+row*.012))
                        uv.append((xx+u*width+phase*.41,y+phase*.37))
                        if row and k:ff.extend([(k-1,k,k+7),(k-1,k+7,k+6)])
                if side<0:ff=[f[::-1] for f in ff]
                g.add(v,ff,tile,uv)
                thickness=.019 if at_eave and detail else .022
                for k in range(6):
                    p0=np.array(v[7+k]);p1=np.array(v[8+k])
                    q=[p0,p1,p1-[0,0,thickness],p0-[0,0,thickness]]
                    lip_uv=[(k*width/6,0),((k+1)*width/6,0),
                            ((k+1)*width/6,thickness),(k*width/6,thickness)]
                    if side<0:q=q[::-1];lip_uv=lip_uv[::-1]
                    g.quad(q,tile,lip_uv)
                if at_eave and detail:
                    # A real 13 cm underside return creates the dark mouth.
                    # It has clay thickness, an open back, and two side cheeks.
                    back=lip_y-.13;under=[];under_uv=[];uf=[]
                    for row,y in enumerate([back,lip_y]):
                        for k in range(7):
                            u=k/6;arch=math.sin(u*math.pi)*crown
                            t=(y-yy)/(lip_y-yy)
                            top_z=H(yy)+(H(lip_y)-H(yy)+.012)*t+arch+.022+seat
                            under.append(P(xx+u*width,side*y,top_z-thickness))
                            under_uv.append((xx+u*width+phase*.41,y+phase*.37))
                            if row and k:uf.extend([(k-1,k+7,k),(k-1,k+6,k+7)])
                    if side<0:uf=[f[::-1] for f in uf]
                    g.add(under,uf,tile,under_uv)
                    for edge in (0,6):
                        # The shell side faces make thickness visible in an
                        # oblique view; no hidden reverse-side duplicates.
                        a=np.array(under[edge]);b=np.array(under[7+edge])
                        q=[a,b,b+[0,0,thickness],a+[0,0,thickness]]
                        uvs=[(0,0),(.13,0),(.13,thickness),(0,thickness)]
                        if (edge==0)==(side>0):q=q[::-1];uvs=uvs[::-1]
                        g.quad(q,tile,uvs)
                # Fired-clay variation belongs to each whole tile. A quiet
                # 6% tonal range adds no texture or material/draw-call split.
                clay_tint(first,.79+(phase-.5)*.10,(phase-.5)*.018)
        # Seat the fascia behind the drip edge so the gutter mouth is visible.
        g.beam(P(-w/2-.58,side*(length-.105),H(length)-.065),P(w/2+.58,side*(length-.105),H(length)-.065),.17,dark)
        for xx in np.arange(-w/2-.35,w/2+.36,.38):
            g.beam(P(xx,side*.2,3.60),P(xx,side*(length+.06),H(length)-.16),.075,dark,.13)
    # Hollow half-round ridge caps sit over the apex. The annular end faces
    # expose fired-clay thickness rather than a closed cylinder's flat disk.
    for xx in np.arange(-w/2-.64,w/2+.62,.32):
        first=vertex_start();vertices=[];uv=[];faces=[];segments=8
        for radial,radius in enumerate((.12,.101)):
            for row,x in enumerate((xx,xx+.36)):
                for k in range(segments+1):
                    a=k*math.pi/segments
                    vertices.append(P(x,radius*math.cos(a),3.90+radius*math.sin(a)))
                    uv.append((x,radius*a))
                    if row and k:
                        b=radial*2*(segments+1);i=b+k-1;n=i+segments+1
                        pair=[(i,n,n+1),(i,n+1,i+1)]
                        # Outer cross-section runs +Y -> +Z -> -Y.
                        faces.extend([f[::-1] for f in pair] if radial==0 else pair)
        g.add(vertices,faces,tile,uv)
        ring=segments+1
        for end in (0,1):
            for k in range(segments):
                ids=[end*ring+k,end*ring+k+1,(2+end)*ring+k+1,(2+end)*ring+k]
                q=[vertices[i] for i in ids]
                uvs=[(k*.025,0),((k+1)*.025,0),((k+1)*.025,.019),(k*.025,.019)]
                if end==0:q=q[::-1];uvs=uvs[::-1]
                g.quad(q,tile,uvs)
        for edge in (0,segments):
            ids=[edge,ring+edge,3*ring+edge,2*ring+edge]
            q=[vertices[i] for i in ids];uvs=[(0,0),(.36,0),(.36,.019),(0,.019)]
            if edge==segments:q=q[::-1];uvs=uvs[::-1]
            g.quad(q,tile,uvs)
        phase=(math.sin(xx*12.717)*43758.5453)%1
        clay_tint(first,.79+(phase-.5)*.06)
    for side in [-1,1]:
        for edge in [-1,1]:g.beam(P(edge*(w/2+.53),0,3.84),P(edge*(w/2+.53),side*length,H(length)),.11,dark,.19)


def noren(g,P,w,dep,material,trim):
    for j in range(5):
        x0=(j-2)*(w-.9)/5;ww=(w-.9)/5-.025;v=[];uv=[];ff=[]
        for k in range(13):
            u=k/12;x=x0-ww/2+ww*u;fold=.042*math.sin(u*TAU*2+.4*j)
            for row,z in enumerate([2.10+.023*math.cos(u*TAU),2.59]):
                v.append(P(x,dep/2+.14+fold,z));uv.append((u,row))
            if k:ff.extend([(k*2-2,k*2,k*2+1),(k*2-2,k*2+1,k*2-1)])
        g.add(v,ff,material,uv)
        g.add(v,[f[::-1] for f in ff],material,uv)
        # Hem and stitches follow the hanging cloth.
        for k in range(12):
            u=k/12;u1=(k+1)/12
            g.beam(P(x0-ww/2+ww*u,dep/2+.141+.042*math.sin(u*TAU*2+.4*j),2.115+.023*math.cos(u*TAU)),P(x0-ww/2+ww*u1,dep/2+.141+.042*math.sin(u1*TAU*2+.4*j),2.115+.023*math.cos(u1*TAU)),.007,trim)


def shop_details(g,P,B,w,dep,idx,m,rng,bespoke=False,staff_entry=False):
    dark=m['dark'];wood=m['wood'];iron=m['iron'];cer=m['ceramic'];brass=m['trim'];paper=m['menu'];win=m['window']
    # Framed wall planks and doubled lintels, shadowed rafters under the eaves.
    for x in np.arange(-w/2+.16,w/2-.1,.20):
        B(x,-dep/2+.195,.64,.174,.048,1.1,wood)
        for z in [.19,1.1]:g.sphere(P(x,-dep/2+.225,z),[.009,.007,.009],iron,6,3)
    for yy in np.arange(-dep/2+.2,dep/2+.4,.50):B(0,yy,2.62,w+.5,.08,.105,dark)
    for x in [-w/2+(.10 if staff_entry else .14),w/2-.14]:
        for z in [.34,2.34]:
            B(x,dep/2+.11,z,.23,.027,.18,iron)
            for dx in [-.07,.07]:g.sphere(P(x+dx,dep/2+.13,z),[.019,.01,.019],brass,10,5)
    # Panelled counter front and foot-rest rail.
    for x in np.arange(-(w-1.5)/2,(w-1.5)/2,.24):
        if not staff_entry or x>=-w/2+.975:B(x,dep/2+.005,.50,.018,.021,.72,dark)
    g.beam(P(-w/2+(.99 if staff_entry else .62),dep/2+.15,.27),P(w/2-.62,dep/2+.15,.27),.038,brass)
    for x in [-w/2+(1.16 if staff_entry else .85),w/2-.85]:g.beam(P(x,dep/2-.2,.22),P(x,dep/2+.15,.27),.029,iron)
    # Menu boards each have legible, distinct content on the rear wall.
    u0=(idx%4)/4;u1=u0+.25;v1=1-(idx//4)*.375;v0=v1-.375
    x=-w/2+.75;y=-dep/2+.42;z=1.68
    B(x,y-.035,z,.57,.045,.89,dark)
    # Local +X is viewer-left: reverse both corner order and horizontal UV.
    # A single front face avoids coincident backface self-shadowing; the timber
    # backing covers the unviewed rear side.
    g.quad([P(x+.265,y,z-.425),P(x-.265,y,z-.425),P(x-.265,y,z+.425),P(x+.265,y,z+.425)],paper,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
    if not bespoke:
        # Sake labels on shelf bottles face the lane; no fake alphabet glyphs.
        for h in [1.40,2.05]:
            for j in range(int(w/.38)-2):
                x=-w/2+.65+j*.37;slot=(j+idx)%16;u0=slot%8/8;v1=1-(.75+(slot//8)*.125)
                g.quad([P(x-.039,-dep/2+.383,h+.16),P(x+.039,-dep/2+.383,h+.16),P(x+.039,-dep/2+.383,h+.27),P(x-.039,-dep/2+.383,h+.27)],paper,[(u0,v1-.125),(u0+.125,v1-.125),(u0+.125,v1),(u0,v1)],True)
    # Prep cupboards, drawers, handles, faucet and sink.
    B(.18,-dep/2+.60,.39,w-1.3,.62,.75,dark)
    for x in np.arange(-w/2+.88,w/2-.48,.56):
        B(x,-dep/2+.927,.49,.52,.043,.46,wood)
        g.beam(P(x-.08,-dep/2+.96,.57),P(x+.08,-dep/2+.96,.57),.016,brass)
    B(-w*.29,-dep/2+.53,.874,.69,.47,.024,iron)
    for x in [-w*.29-.35,-w*.29+.35]:B(x,-dep/2+.53,.901,.028,.52,.028,brass)
    g.tube([P(-w*.29,-dep/2+.32,.90),P(-w*.29,-dep/2+.32,1.16),P(-w*.29,-dep/2+.47,1.23),P(-w*.29,-dep/2+.58,1.17)],[.018]*4,brass,10)
    # Wires, external conduit, tied joints, bamboo blind behind the noren.
    for yy in [-dep/2+.15,dep/2-.15]:
        g.tube([P(-w/2+.10,yy,.2),P(-w/2+.10,yy,2.6),P(w/2-.10,yy,2.6)],[.019]*3,iron,8)
    for xx in np.arange(-w/2+.2,w/2-.2,.055):g.beam(P(xx,-dep/2+.24,2.27),P(xx,-dep/2+.24,2.55),.019,wood)
    # Utensil hangers, copper pans, knives and ladles.
    for j in range(6):
        x=(j-2.5)*.31;y=-dep/2+.72
        g.beam(P(x,y,1.92),P(x,y,1.65),.015,iron)
        if j%2:g.sphere(P(x,y,1.56),[.087,.025,.09],brass,18,10)
        else:B(x,y,1.57,.045,.01,.16,iron)
    if not bespoke:
        # Counter place settings: chopstick pairs, rests, glazed tea cups, sauce pots.
        for j in range(5):
            x=(j-2)*min(.70,(w-1.7)/4);y=dep/2-.12
            for dx in [.17,.193]:g.beam(P(x+dx,y-.18,1.045),P(x+dx,y+.085,1.06),.008,wood)
            B(x+.181,y+.035,1.047,.082,.025,.018,cer)
            g.cylinder(P(x-.23,y-.10,1.115),.047,.14,cer,20,r2=.052)
            g.cylinder(P(x-.23,y-.10,1.188),.040,.004,m['tea'],18)
            if j%2==0:
                g.sphere(P(x+.32,y-.22,1.11),[.055,.055,.069],m['soy'],16,9)
                g.cylinder(P(x+.32,y-.22,1.181),.045,.026,m['red'],16)
    # Storage crate and woven basket inside the shop, away from seat exits.
    B(w/2-.57,-.72,.25,.62,.58,.46,dark)
    for z in [.10,.25,.40]:
        for side in [-1,1]:B(w/2-.57+side*.33,-.72,z,.035,.64,.09,wood)
        B(w/2-.57,-.405,z,.70,.035,.09,wood)
    # Ceiling lights and small warm shoji side lights.
    for x in [-w*.28,w*.28]:
        B(x,-.3,2.49,.48,.40,.045,iron);B(x,-.3,2.46,.40,.32,.017,win)
    # Roof gable slats fill the triangle but leave a believable ventilating gap.
    for x in np.arange(-w/2+.1,w/2,.16):
        for side in [-1,1]:
            B(x,side*(dep/2-.20),2.77,.095,.035,.34,wood)
    if not bespoke:
        # Clay dishes, cutting boards and finely modelled local specialties.
        B(.05,-.60,.94,.60,.40,.037,m['counter'])
        for j in range(5):
            x=(j-2)*.115
            if idx in [0,6]:
                for k in range(3):g.sphere(P(x,-.60+k*.10,1.00),[.043,.041,.039],m['food'],12,7)
            elif idx==1:
                for k in range(7):
                    a=np.linspace(0,TAU,17);points=[P(x+.06*math.cos(t),-.60+.06*math.sin(t),.966+k*.003) for t in a]
                    g.tube(points,[.006]*len(points),m['noodle'],5)
            elif idx==2:g.cylinder(P(x,-.60,.985),.043,.055,cer,14)
            elif idx in [4,7]:g.sphere(P(x,-.60,.985),[.05,.04,.035],m['sweet'],14,8)
    # Bamboo skewers in a ribbed ceramic holder.
    if not bespoke:g.cylinder(P(w*.28,dep/2-.26,1.14),.057,.19,cer,20)
    for j in range(12):
        # Preserve the pre-v2.7 world RNG sequence even when replacing props.
        dx,dy=rng.uniform(-.035,.035,2);tip_z=1.43+rng.uniform(-.03,.04)
        if not bespoke:g.beam(P(w*.28+dx,dep/2-.26+dy,1.1),P(w*.28+dx*1.4,dep/2-.26+dy*1.4,tip_z),.0055,wood)


def foliage_cluster(g,center,size,leafs,rng,count=250):
    center=np.array(center);size=np.array(size)
    # Clusters contain branched sprays, never opaque ellipsoid filler meshes.
    for k in range(count):
        direction=rng.normal(size=3);direction/=np.linalg.norm(direction)
        p=center+direction*size*(rng.random()**.34)
        az=rng.uniform(0,TAU);tilt=rng.uniform(-.45,.65)
        length=np.array([math.cos(az),math.sin(az),tilt])*rng.uniform(.22,.42)
        right=np.array([-math.sin(az),math.cos(az),0])*rng.uniform(.08,.15)
        leaf(g,p,right,length,leafs[k%len(leafs)])


def spray(g,p,right,up,material):
    p=np.array(p);r=np.array(right);u=np.array(up)
    g.quad([p-r-u,p+r-u,p+r+u,p-r+u],material)


def detailed_crown(g,branch,leafs,bark,rng,spraymat):
    for i in range(12):
        g.group='Tree/Crown_'+str(i)
        a=i*2.399963;z=54+(i%7)*6.1;radius=rng.uniform(26,40)
        # Keep this crown limb above the complete upper-helix walking envelope.
        if i==9:z+=8.0
        radial=np.array([math.cos(a),math.sin(a),0]);tangent=np.array([-math.sin(a),math.cos(a),0])
        root=radial*3+[0,0,z]
        first=radial*11+tangent*rng.uniform(-5,5)+[0,0,z+rng.uniform(5,10)]
        fork=radial*(radius*.75)+tangent*rng.uniform(-4,7)+[0,0,z+rng.uniform(14,20)]
        tip=radial*radius+tangent*rng.uniform(-6,6)+[0,0,z+25]
        branch([root,first,fork,tip],[3.5,2.35,1.05,.11],24)
        for j in range(9):
            ang=a+(j-4)*.16;rr=radius+rng.uniform(-7,6);pz=z+rng.uniform(17,31)
            cen=np.array([math.cos(ang)*rr,math.sin(ang)*rr,pz]);sz=[rng.uniform(3.5,5),rng.uniform(3.0,4.5),rng.uniform(1.8,3)]
            mid=fork*.45+cen*.55-[0,0,2]
            branch([first if j<2 else fork,mid,cen],[.47,.19,.012],10)
            foliage_cluster(g,cen,sz,leafs,rng,155)
            for k in range(75):
                d=rng.normal(size=3);d/=np.linalg.norm(d);p=cen+d*sz*rng.random()**.4
                az=rng.uniform(0,TAU);right=np.array([math.cos(az),math.sin(az),0])*rng.uniform(.65,1.10)
                up=np.array([-math.sin(az)*.38,math.cos(az)*.38,rng.uniform(.4,1)])*rng.uniform(.65,1.15)
                spray(g,p,right,up,spraymat)
    for i in range(27):
        g.group='Tree/Framing_'+str(i//4)
        a=i*2.4;rr=rng.uniform(24,40);z=rng.uniform(50,67);p=np.array([math.cos(a)*rr,math.sin(a)*rr,z])
        radial=np.array([math.cos(a),math.sin(a),0]);bend=np.array([-math.sin(a),math.cos(a),0])*rng.uniform(-4,4)
        branch([radial*7+[0,0,z-7],radial*rr*.6+bend+[0,0,z-3],p],[.82,.34,.008],14)
        foliage_cluster(g,p,[3.1,2.7,1.7],leafs,rng,165)
        for j in range(48):
            q=p+rng.uniform(-1,1,3)*[3.1,2.7,1.7];az=rng.uniform(0,TAU)
            spray(g,q,[math.cos(az)*.85,math.sin(az)*.85,0],[-math.sin(az)*.3,math.cos(az)*.3,.85],spraymat)


def detailed_deck(g,poly,z,wood,dark):
    # Short end joints and real 3 mm shadow grooves, continuous collision below.
    from shapely.geometry import LineString
    minx,miny,maxx,maxy=poly.bounds
    for i,x in enumerate(np.arange(math.floor(minx/.26)*.26,maxx,.26)):
        offset=(i%4)*.56
        for y in np.arange(math.floor(miny/2.25)*2.25-offset,maxy,2.25):
            seam=LineString([(x+.006,y),(x+.250,y)]).intersection(poly)
            if seam.geom_type=='LineString' and seam.length>.03:
                a,b=seam.coords[0],seam.coords[-1]
                g.quad([[*a,z+.003],[*b,z+.003],[b[0],b[1]+.003,z+.003],[a[0],a[1]+.003,z+.003]],dark)
                for xx in [a[0]+.035,b[0]-.035]:
                    if b[0]-a[0]>.10:g.cylinder([xx,y+.065,z+.005],.006,.002,dark,6)


def terrain_radius(a):return 260+29*np.sin(a*3+.8)+18*np.sin(a*5-.6)+11*np.sin(a*9)
def terrain_height(x,y):
    r=np.sqrt(x*x+y*y);a=np.arctan2(y,x);distance=r-terrain_radius(a)
    foot=np.maximum(distance,0)
    base=-4.2+(1-np.exp(-foot/28))*8+foot*.018
    ridge=np.maximum(0,foot-135)
    shape=.42+.21*np.sin(a*5+ridge*.003)+.17*np.sin(a*11+.3)+.09*np.cos(a*19)
    peaks=65*np.exp(-((r-550)/235)**2)+105*np.exp(-((r-1000)/360)**2)+185*np.exp(-((r-1680)/400)**2)
    detail=(np.sin(x*.026+y*.017)+np.sin(x*.063-y*.041)*.46+np.sin(x*.137+y*.101)*.19)
    return base+peaks*shape+detail*np.minimum(ridge*.11,11)


def landscape(g,m,rng):
    terrain=m['terrain'];stone=m['stone'];dark=m['dark'];roof=m['tile'];window=m['city'];leafs=m['leafs'];water=m['lake']
    g.group='Landscape/Lake'
    # The lake has enough tessellation for geometric wave displacement in Unity.
    verts=[];faces=[];n=101
    for j in range(n):
        for i in range(n):
            x=-1900+i*3800/(n-1);y=-1900+j*3800/(n-1);verts.append([x,y,-4.02])
            if i and j:k=j*n+i;faces.extend([(k-n-1,k-n,k),(k-n-1,k,k-1)])
    g.add(verts,faces,water,np.array(verts)[:,:2]*.045)
    # Irregular, densely sampled shore and ridges rather than overlapping spheres.
    for sector in range(12):
        g.group='Landscape/Terrain_'+str(sector);v=[];uv=[];f=[];na=49;nr=60
        for ri in range(nr):
            for ai in range(na):
                a=(sector+ai/(na-1))*TAU/12;r=float(terrain_radius(a))+(ri/(nr-1))**1.5*2000
                x=r*math.cos(a);y=r*math.sin(a);h=float(terrain_height(x,y));v.append([x,y,h]);uv.append([x*.06,y*.06])
                if ri and ai:k=ri*na+ai;f.extend([(k-na-1,k,k-na),(k-na-1,k-1,k)])
        g.add(v,f,terrain,uv)
    # Bedrock beneath the ancient root crown, with a rocky shoreline.
    g.group='Landscape/TreeIsland';n=96;v=[[0,0,-.8]];uv=[[0,0]];f=[]
    for ring in range(1,15):
        for j in range(n):
            a=j*TAU/n;r=ring/14*(52+4*math.sin(a*5)+3*math.cos(a*9));h=-.6-(r/54)**4*4+.24*math.sin(a*11)*ring/14
            v.append([r*math.cos(a),r*math.sin(a),h]);uv.append([v[-1][0]*.2,v[-1][1]*.2])
            if ring==1:f.append((0,1+j,1+(j+1)%n))
            else:
                k=1+(ring-1)*n+j;kn=1+(ring-1)*n+(j+1)%n;p=k-n;pn=kn-n;f.extend([(p,k,kn),(p,kn,pn)])
    g.add(v,f,stone,uv)
    # Lakeside roads follow the coast; two irregular residential bands.
    house_count=0;forest_count=0
    for sector in range(18):
        g.group='Landscape/Village_'+str(sector)
        center=sector*TAU/18
        for row in range(4):
            offset=18+row*17
            pts=[]
            for a in np.linspace(center-.18,center+.18,33):
                r=float(terrain_radius(a))+offset;x=r*math.cos(a);y=r*math.sin(a);pts.append([x,y,float(terrain_height(x,y))+.12])
            for a,b in zip(pts,pts[1:]):
                d=np.array(b)-a;side=np.array([-d[1],d[0],0]);side/=np.linalg.norm(side);g.quad([np.array(a)-side*2,np.array(b)-side*2,np.array(b)+side*2,np.array(a)+side*2],m['road'])
            for j in range(10):
                a=center-.165+j*.034+rng.uniform(-.007,.007);r=float(terrain_radius(a))+offset+7.5+rng.uniform(-2.5,2.5)
                x=r*math.cos(a);y=r*math.sin(a);h=float(terrain_height(x,y));w=rng.uniform(4,7);d=rng.uniform(4,6.5);height=rng.choice([3.0,4.8,5.5])
                aa=a+rng.uniform(-.17,.17);side=np.array([-math.sin(aa),math.cos(aa),0]);front=np.array([-math.cos(aa),-math.sin(aa),0]);up=np.array([0,0,1]);p=np.array([x,y,h]);axes=[side,front,up]
                def P(xx,yy,zz):return p+side*xx+front*yy+up*zz
                g.box(P(0,0,height/2),[w,d,height],m['townwalls'][house_count%3],axes)
                g.box(P(0,-d/2-.02,.55),[w,.055,1.1],dark,axes)
                for xx in [-w*.43,w*.43]:g.box(P(xx,-d/2-.04,height*.5),[.15,.06,height],dark,axes)
                for s in [-1,1]:
                    g.quad([P(-w/2-.35,0,height+1.35),P(w/2+.35,0,height+1.35),P(w/2+.35,s*(d/2+.38),height),P(-w/2-.35,s*(d/2+.38),height)],roof,[(0,0),(w,0),(w,d/2),(0,d/2)],True)
                    for jj in range(3):
                        xx=(jj-1)*w*.26
                        g.box(P(xx,s*(d/2+.018),height*.62),[w*.17,.035,.80],window if rng.random()>.25 else dark,axes)
                        g.box(P(xx,s*(d/2+.042),height*.62),[.045,.018,.83],dark,axes)
                    g.beam(P(-w/2-.3,s*(d/2+.4),height),P(w/2+.3,s*(d/2+.4),height),.14,dark)
                for sideval in [-1,1]:
                    q=[P(sideval*w/2,-d/2,height),P(sideval*w/2,d/2,height),P(sideval*w/2,0,height+1.34)]
                    g.add(q,[(0,1,2)] if sideval>0 else [(2,1,0)],m['townwalls'][house_count%3],[(0,0),(1,0),(.5,1)])
                for xx in [-w*.42,0,w*.42]:g.box(P(xx,-d/2-.09,height*.48),[.10,.10,height*.96],dark,axes)
                if house_count%4==0:
                    g.box(P(w*.38,d*.35,1.45),[w*.48,d*.55,2.9],m['townwalls'][(house_count+1)%3],axes)
                    g.box(P(w*.38,d*.35,2.93),[w*.56,d*.63,.20],roof,axes)
                g.box(P(0,0,height+1.36),[w+.8,.18,.16],roof,axes)
                if house_count%7==0:
                    pole=P(w/2+.7,-d/2-1,0);g.beam(pole,pole+[0,0,5.2],.08,dark);g.sphere(pole+[0,0,5.2],[.13,.13,.19],window,8,5)
                house_count+=1
    # Trees occupy the forest belt, not the streets; geometry varies per tree.
    for sector in range(16):
        g.group='Landscape/Forest_'+str(sector)
        for i in range(400):
            a=(sector+rng.random())*TAU/16;r=float(terrain_radius(a))+rng.uniform(84,560);x=r*math.cos(a);y=r*math.sin(a);z=float(terrain_height(x,y));height=rng.uniform(8,19);rad=height*.31
            g.cylinder([x,y,z+height*.43],height*.025,height*.86,dark,4)
            for k in range(3):
                az=k*2.4+i*.13;rr=rad*(1-k*.13)
                center=[x+math.cos(az)*rad*.32,y+math.sin(az)*rad*.32,z+height*(.63+k*.11)]
                g.sphere(center,[rr,rr*.87,height*.29],m['forest'][i%3],6,3)
            for k in range(2):
                az=k*2.4+i*.13;zz=z+height*.83
                spray(g,[x,y,zz],[math.cos(az)*rad,math.sin(az)*rad,0],[0,0,height*.26],m['forestSpray'])
            forest_count+=1
    # A lantern-lined stone bridge across the northern inlet and a hilltop temple.
    g.group='Landscape/Bridge'
    y=261
    for x in np.arange(-50,51,5):
        h=1.8+2.8*math.sin((x+50)/100*math.pi);g.box([x,y,h],[5.1,5,.8],stone)
        for sy in [-1,1]:
            g.box([x,y+sy*2.6,h+1.2],[.17,.17,2],dark)
            g.sphere([x,y+sy*2.6,h+2.3],[.15,.15,.20],window,8,5)
        if int(x)%15==0:g.box([x,y,h/2-2],[1.7,4.5,h+4],stone)
    g.group='Landscape/HillTemple';a=2.25;r=float(terrain_radius(a))+130;tx=r*math.cos(a);ty=r*math.sin(a);tz=float(terrain_height(tx,ty))
    for level in range(3):
        size=13-level*2.4;zz=tz+level*4.8
        g.box([tx,ty,zz+2],[size-2,size-2,4],dark)
        for dx in [-1,1]:g.box([tx+dx*(size/2-.8),ty-size/2+.93,zz+2],[.25,.03,1.7],window)
        for sy in [-1,1]:g.quad([[tx-size/2-1,ty,zz+6],[tx+size/2+1,ty,zz+6],[tx+size/2+1,ty+sy*(size/2+1),zz+3.8],[tx-size/2-1,ty+sy*(size/2+1),zz+3.8]],roof,double=True)
    return {'distantHouses':house_count,'forestTrees':forest_count,'terrainSectors':12,'coastRoadBands':4,'templeStoreys':3,'forestCrownSides':6,'forestCrownRings':3,'visualProfile':'Windows50'}
