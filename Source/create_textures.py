from pathlib import Path
from io import BytesIO
import numpy as np, math
from PIL import Image,ImageDraw,ImageFont,ImageFilter

def make_textures(out,font_path):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(58)
    n=512;y,x=np.mgrid[0:n,0:n]/n
    noise=rng.normal(0,.025,(n,n))
    grain=(np.sin(x*math.tau*17+np.sin(y*math.tau*2)*1.2)+.35*np.sin(x*math.tau*69+np.sin(y*math.tau*4)*2))*.075
    slow=.08*np.sin(x*math.tau*5+np.sin(y*math.tau)*.2)
    w=np.clip(.77+grain+slow+noise,.3,1)
    def save(name,a):
        image=Image.fromarray(np.uint8(np.clip(a,0,255)))
        buf=BytesIO();image.save(buf,format='PNG');payload=buf.getvalue()
        Image.open(BytesIO(payload)).load()
        (out/name).write_bytes(payload)
    save('wood.png',w[:,:,None]*np.array([185,136,83]))
    warp=.35*np.sin(y*math.tau*2)+.11*np.sin(y*math.tau*7+x*8)
    cracks=np.minimum(1,((np.sin(x*math.tau*7+warp*3)+1)/2)*5)
    cells=.08*np.sin(y*math.tau*14+np.sin(x*math.tau*6)*2)
    bark=np.clip((.70+.14*np.sin(x*math.tau*3+warp)+cells+noise)*(.65+.35*cracks),.32,1)
    save('bark.png',bark[:,:,None]*[153,139,113])
    roof=np.clip(.75+noise+.10*np.sin(x*math.tau*8),.45,1)
    roof[(y*8)%1<.03]*=.6
    save('roof.png',roof[:,:,None]*[100,123,135])
    fabric=np.clip(.85+.10*np.sin(x*math.tau*180)+.035*np.sin(y*math.tau*180),.6,1)
    save('cloth.png',fabric[:,:,None]*np.ones(3)*255)
    # One 16-cell atlas; Japanese text is rendered from Noto, not AI signage.
    atlas=Image.new('RGB',(1024,2048),(234,218,179));d=ImageDraw.Draw(atlas)
    f=ImageFont.truetype(str(font_path),65);small=ImageFont.truetype(str(font_path),23)
    labels=[('炭火 梢','SUMIBI KOZUE · YAKITORI'),('麺処 風待','KAZEMACHI · RAMEN'),('おでん 灯','AKARI · ODEN'),('酒処 根っこ','NEKKO · SAKE'),('枝先茶屋','EDASAKI CHAYA · TEA'),('宵 葉','YOIBA · BAR'),('山 椒 屋','SANSHOYA · SMALL PLATES'),('木 の 実','KINOMI · SWEETS & GUIDE'),('樹 上 横 丁','TREE-TOP YOKOCHO'),('梢の見晴台','L4 · CANOPY OBSERVATORY'),('上段の枝路地','L3 · UPPER ALLEY'),('主 横 丁','L2 · MAIN YOKOCHO'),('到着デッキ','L1 · ARRIVAL DECK'),('根 元 口','G0 · ROOT ENTRANCE'),('昇降口','LIFT · SELECT A FLOOR'),('案内・お手洗い','INFORMATION & RESTROOM')]
    for i,(title,sub) in enumerate(labels):
        y0=i*128;d.rectangle((6,y0+4,1018,y0+123),outline=(101,60,35),width=3)
        d.text((512,y0+8),title,font=f,anchor='mt',fill=(52,38,30),stroke_width=0)
        d.text((512,y0+91),sub,font=small,anchor='mt',fill=(117,64,39))
    save('signs.png',np.asarray(atlas))
    # Paper lantern crest, small and repeatable; geometric flower emblem.
    p=Image.new('RGB',(256,512),(255,219,154));d=ImageDraw.Draw(p)
    for j in range(0,512,16):d.line((0,j,256,j),fill=(191,111,62),width=2)
    for k in range(5):
        a=math.tau*k/5;x0=128+34*math.sin(a);y0=256+34*math.cos(a)
        d.ellipse((x0-22,y0-22,x0+22,y0+22),fill=(92,34,25))
    d.ellipse((113,241,143,271),fill=(248,177,107));save('lantern.png',np.asarray(p))

if __name__=='__main__':
    import sys
    make_textures(sys.argv[1],sys.argv[2])
