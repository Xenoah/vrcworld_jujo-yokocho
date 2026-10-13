"""Meter-scaled washi lanterns with correctly proportioned repeat emblems."""
from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw


def make_lantern_paper(out):
    """Native material artwork: fibres and four modest floral ink crests.

    Four circumference repeats avoid wrapping one huge emblem around the
    entire globe. Ribs are real geometry, not a second moire-prone line map.
    """
    rng=np.random.default_rng(81129);h,w=512,1024
    y,x=np.mgrid[:h,:w]
    fiber=rng.normal(0,.007,(h,w))+.004*np.sin(x*.79+y*.27)
    grain=.986+fiber+.009*np.sin(x*.019)*np.sin(y*.031)
    a=np.clip(np.array([248,222,179])[None,None,:]*grain[:,:,None],0,255).astype('uint8')
    paper=Image.fromarray(a);d=ImageDraw.Draw(paper)
    ink=(86,46,31)
    for cx in (128,384,640,896):
        cy=256
        d.ellipse((cx-45,cy-45,cx+45,cy+45),outline=ink,width=3)
        for k in range(5):
            angle=math.tau*k/5-math.pi/2
            xx=cx+21*math.cos(angle);yy=cy+21*math.sin(angle)
            d.ellipse((xx-15,yy-15,xx+15,yy+15),fill=ink)
            d.line((cx,cy,xx,yy),fill=(224,191,141),width=2)
        d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=(236,207,161))
    path=Path(out)/'lantern.png';paper.save(path,optimize=True)
    return path


def add_washi_lantern(g,pos,paper,redpaper,trim,iron,scale=1):
    p=np.asarray(pos,float);r=.22*scale;h=.55*scale
    zf=np.linspace(-.445,.445,13)
    def radius(z):return r*(1-.34*(abs(z)/.445)**3.2)
    v=[];uv=[];f=[];n=24
    for i,z in enumerate(zf):
        rr=radius(z)
        for j in range(n+1):
            a=math.tau*j/n
            v.append(p+[rr*math.cos(a),rr*math.sin(a),z*h])
            uv.append((j/n,.5+z))
            if i and j:
                k=i*(n+1)+j;f.extend([(k-n-2,k-n-1,k),(k-n-2,k,k-1)])
    # The source rings ascend while turning CCW: normals point outward.
    g.add(v,f,redpaper or paper,uv)
    for z in np.linspace(-.421,.421,15):
        rr=radius(z)+.0015*scale
        points=[p+[rr*math.cos(a),rr*math.sin(a),z*h] for a in np.linspace(0,math.tau,25)]
        g.tube(points,[.0018*scale]*len(points),trim,3)
    for side in (-1,1):
        zz=side*h*.451
        g.cylinder(p+[0,0,zz],r*.674,.040*scale,iron,16)
        g.cylinder(p+[0,0,zz+side*.021*scale],r*.571,.008*scale,trim,16)
    # Forged bail, rather than a disconnected straight rod disappearing in air.
    points=[p+[.092*scale*math.cos(a),0,h*.49+.075*scale*math.sin(a)] for a in np.linspace(0,math.pi,15)]
    g.tube(points,[.005*scale]*len(points),iron,5)
    g.beam(p+[0,0,h*.49+.075*scale],p+[0,0,h/2+.24*scale],.009*scale,iron)
