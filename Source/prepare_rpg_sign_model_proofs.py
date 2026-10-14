"""Export actual production sign batches, not substitute preview planes."""
from pathlib import Path
import copy,json,hashlib,io
import numpy as np
from PIL import Image,ImageDraw
from test_rpg_shop_identities import make
import rpg_shop_identities as rpg
from world_geometry import Geometry
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Preview/rpg-sign-model-proofs';OUT.mkdir(exist_ok=True)
TEX=ROOT/'Assets/TreeTopYokocho/Textures'
reports={atlas:rpg.bake(TEX,atlas) for atlas in ['food_venue_signs.png','nightlife_signs.png']}
g=Geometry();changes=[];coverage=[]
for idx in range(8):
 old,_=make(idx,False);new,result=make(idx,True)
 selected={k:b for k,b in new.batches.items() if 'Signs' in k[0] or 'Signage' in k[0]}
 g.batches.update(copy.deepcopy(selected));g.materials.update(copy.deepcopy(new.materials))
 for key,b in new.batches.items():
  a=np.array(old.batches[key]['uv']);u=np.array(b['uv']);changed=np.flatnonzero(np.any(a!=u,axis=1))
  if len(changed):changes.append(dict(shop=f'S{idx+1:02d}',key=key,vertexIndices=changed.tolist(),beforeUvSha256=hashlib.sha256(a.astype('<f8').tobytes()).hexdigest(),afterUvSha256=hashlib.sha256(u.astype('<f8').tobytes()).hexdigest()))
 # Actual triangle raster coverage in texture space independently checks glyph clipping.
 mask=Image.new('L',(2048,2048),0);d=ImageDraw.Draw(mask)
 for (group,mat),b in selected.items():
  if mat not in ('Food_Sign','Night_Print'):continue
  u=np.array(b['uv']);f=np.array(b['f'])
  for tri in u[f]:d.polygon([(float(p[0]*2048),float((1-p[1])*2048)) for p in tri],fill=255)
 r=rpg.name_rect(idx);arr=np.array(Image.open(TEX/('food_venue_signs.png' if idx in rpg.FOOD_IDS else 'nightlife_signs.png')).crop(r));ink=np.array(rpg.IDENTITIES[idx]['ink'])
 lettering=np.max(np.abs(arr.astype(int)-ink),axis=2)<8
 outside=lettering & (np.array(mask.crop(r))==0)
 coverage.append(dict(shop=f'S{idx+1:02d}',inkPixels=int(lettering.sum()),clippedInkPixels=int(outside.sum())))
 if outside.any():raise AssertionError('Actual model clips title ink: '+str(coverage[-1]))
g.compact();used={k[1] for k in g.batches};g.materials={k:v for k,v in g.materials.items() if k in used}
g.save_glb(OUT/'actual-signs.glb',TEX,lossless_textures=('food_venue_signs.png','nightlife_signs.png'))
from pygltflib import GLTF2
asset=GLTF2().load(str(OUT/'actual-signs.glb'));blob=asset.binary_blob();mapping=[]
for material,atlas in [('Food_Sign','food_venue_signs.png'),('Night_Print','nightlife_signs.png')]:
 mi=next(i for i,m in enumerate(asset.materials) if m.name==material);m=asset.materials[mi]
 ti=m.pbrMetallicRoughness.baseColorTexture.index;ii=asset.textures[ti].source;image=asset.images[ii];view=asset.bufferViews[image.bufferView]
 payload=blob[(view.byteOffset or 0):(view.byteOffset or 0)+view.byteLength]
 pixels=Image.open(io.BytesIO(payload)).convert('RGB');source=Image.open(TEX/atlas).convert('RGB')
 if image.mimeType!='image/png' or pixels.tobytes()!=source.tobytes():raise AssertionError('GLB sign material is not mapped to exact lossless atlas: '+material)
 meshes=[mesh.name for mesh in asset.meshes if any(p.material==mi for p in mesh.primitives)]
 if not meshes:raise AssertionError('No actual model uses '+material)
 mapping.append(dict(material=material,atlas=atlas,mimeType=image.mimeType,pixelSha256=hashlib.sha256(pixels.tobytes()).hexdigest(),meshes=meshes))
report=dict(materialMapping=mapping,atlasReports=reports,changedUvBatches=changes,actualTriangleInkCoverage=coverage,glbSha256=hashlib.sha256((OUT/'actual-signs.glb').read_bytes()).hexdigest(),sourceHashes={n:hashlib.sha256((ROOT/'Source'/n).read_bytes()).hexdigest() for n in ['food_venues.py','nightlife_venues.py','rpg_shop_identities.py']},runtimeTested=False)
(OUT/'proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(changes=[dict(key=x['key'],changedVertices=len(x['vertexIndices'])) for x in changes],coverage=coverage),indent=2))
