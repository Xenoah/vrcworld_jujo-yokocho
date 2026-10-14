"""Run with Blender --background --factory-startup --python this.py -- --asset-root PATH.
Node graph construction only; not render parity or Unity compilation.
"""
import argparse
import sys
import json
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--asset-root',type=Path,default=HERE)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=a.asset_root.resolve()
sys.path.insert(0,str(root/'Source'))
sys.path.insert(0,str(HERE/'Source'))
from fantasy_preview import configure_materials,configure_sky
from dusk_atmosphere import configure_world
profile=json.loads((HERE/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text())
for name in ['Lake','Noren0','PaperLight','Ceramic','Cedar']:
    m=bpy.data.materials.new(name);m.use_nodes=True
result=configure_materials(bpy,profile,root,12.5)
assert {m['name'] for m in result['materials']}=={'Lake','Noren0','PaperLight','Ceramic'}
assert {m['name'] for m in result['omitted']}=={'Cedar'}
assert result['unsupported']==[]
print(json.dumps(result,indent=2))
dusk=json.loads((root/'Assets/TreeTopYokocho/Data/DuskAtmosphere.json').read_text())
dusk['sky']['strength']=2.0
configure_world(bpy,dusk)
result=configure_sky(bpy,dusk,profile,12.5)
assert result['radianceStrength']==2.0
print(json.dumps(result,indent=2))
