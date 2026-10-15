"""Build a deterministic material-only overlay plan. Never authorizes art or installs it.

The immutable v2.19 manifest and geometry stay untouched. A separate reviewed
literal plan hash in the Unity installer admits the final original maps.
"""
from pathlib import Path
import argparse, hashlib, json, struct, gzip, io
from collections import Counter

MANIFEST = 'Assets/TreeTopYokocho/Data/WorldManifest.json'
MANIFEST_SHA = 'aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466'
ROOT = 'Assets/TreeTopYokochoOriginalPbr'
FAMILIES = {
 'bark_brown_02': ('yokocho_bark', .008),
 'wood_planks_grey': ('yokocho_weathered_timber', .0018),
 'wood_table_001': ('yokocho_counter_timber', .0006),
 'rocky_terrain_02': ('yokocho_mineral_rock', .006),
}
SLOTS = {
 'texture': ('_MainTex', 'diff_4k.jpg', 'albedo.png'),
 'normal': ('_BumpMap', 'nor_gl_2k.jpg', 'normalGL.png'),
 'arm': ('_ARM', 'arm_2k.jpg', 'arm.png'),
 'height': ('_HeightMap', 'disp_2k.jpg', 'height.png'),
}
def sha(data): return hashlib.sha256(data).hexdigest()
def encode(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()

def material_rows(manifest):
 rows=[]
 for material in manifest['materials']:
  slots=[]; family=None
  for field,(prop,old_suffix,new_suffix) in SLOTS.items():
   for old,(new,parallax) in FAMILIES.items():
    if material.get(field)==f'PBR/{old}_{old_suffix}':
     if family is not None and family != old: raise ValueError('Mixed family: '+material['name'])
     family=old
     slots.append(dict(property=prop,originalPath=f'Assets/TreeTopYokocho/Textures/PBR/{old}_{old_suffix}',replacementPath=f'{ROOT}/Textures/PBR/{new}_{new_suffix}'))
  if slots:
   p=material.get('parallax',0)
   if p not in (0,.014): raise ValueError('Unreviewed parallax: '+material['name'])
   rows.append(dict(name=material['name'],slots=slots,calibrateParallax=p!=0,originalParallax=p,replacementParallax=FAMILIES[family][1] if p else 0))
 if len(rows)!=31 or len({r['name'] for r in rows})!=31: raise ValueError('Exact 31 target materials required')
 if sum(r['calibrateParallax'] for r in rows)!=10: raise ValueError('Exact 10 nonzero parallax fields required')
 return rows

def material_counts(root):
 data=Path(root)/"Assets/TreeTopYokocho/Data"
 parts=sorted(data.glob("VisualMeshes.bytes.gz.part[0-9][0-9][0-9]"))
 raw=gzip.decompress(b"".join(p.read_bytes() for p in parts))
 if sha(raw)!="5c747087ae2327374123be906bdcc5139909c9a30ad89487ade275fb4839674a": raise ValueError("Immutable native geometry changed")
 stream=io.BytesIO(raw);counts=Counter()
 if stream.read(4)!=b"JYWM": raise ValueError("Native header")
 version,n=struct.unpack("<II",stream.read(8))
 for _ in range(n):
  names=[stream.read(struct.unpack("<I",stream.read(4))[0]).decode() for _ in range(2)]
  nv,ni=struct.unpack("<II",stream.read(8));stream.seek(nv*24+ni*4,1);counts[names[1]]+=1
 if stream.tell()!=len(raw): raise ValueError("Native byte extent")
 return counts

def build(root):
 root=Path(root)
 raw=(root/MANIFEST).read_bytes()
 if sha(raw)!=MANIFEST_SHA: raise ValueError('Immutable core manifest changed')
 m=json.loads(raw); rows=material_rows(m); counts=material_counts(root)
 for row in rows: row['expectedRendererCount']=counts[row['name']]
 if [r['name'] for r in rows if not r['expectedRendererCount']]!=['Moss']: raise ValueError('Unexpected inactive material')
 core_compat=json.loads((root/'Assets/TreeTopYokochoEntrySystems/Data/CoreCompatibility.json').read_text())
 baseline=set(r['path'] for r in core_compat['files'])
 baseline.update(r['originalPath'] for row in rows for r in row['slots'])
 baseline.update(str(p.relative_to(root)) for p in (root/'Assets/TreeTopYokocho/Editor').glob('*.cs'))
 baseline.update(str(p.relative_to(root)) for p in (root/'Assets/TreeTopYokocho/Shaders').glob('*.shader'))
 maps=[f'{ROOT}/Textures/PBR/{new}_{suffix[2]}' for new,_ in FAMILIES.values() for suffix in SLOTS.values()]
 return dict(schema=1,baselineManifestSha256=MANIFEST_SHA,
  baselineFiles=[dict(path=p,sha256=sha((root/p).read_bytes())) for p in sorted(baseline)],
  maps=[dict(path=p,sha256=sha((root/p).read_bytes())) for p in maps],materials=rows)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();data=encode(build(args.root));args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(data)
 print(json.dumps({'output':str(args.output),'sha256':sha(data),'sourceOnly':True,'artApproved':False}))
