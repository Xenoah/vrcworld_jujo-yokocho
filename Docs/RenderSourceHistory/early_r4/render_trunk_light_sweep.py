"""Original trunk geometry; final maps under opposed grazing key lights.
This is diagnostic lighting, not a changed world or Unity runtime capture.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'Source/render_actual_trunk.py').read_text()
s=s.replace("s.cycles.samples=48","s.cycles.samples=64")
s=s.replace("for name,pos,target,lens in [('close',(4,-11,143),(3,-6,142),48),('mid',(25,-30,156),(0,0,143),46)]:",'''for name,pos,target,lens in [('grazing_left',(4,-11,143),(3,-6,142),48),('grazing_right',(4,-11,143),(3,-6,142),48),('dim_grazing_right',(4,-11,143),(3,-6,142),48)]:
 key=bpy.data.objects['neutral key'];fill=bpy.data.objects['neutral fill'];key.location=(-16,-10,146) if name=='grazing_left' else (18,-10,146);key.rotation_euler=(Vector((3,-6,142))-key.location).to_track_quat('-Z','Y').to_euler();key.data.size=6;key.data.energy=5500 if name!='dim_grazing_right' else 700;fill.data.energy=0;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12 if name!='dim_grazing_right' else .025
''')
s=s.replace("'lighting':'identical neutral studio on actual trunk geometry, not world lighting'","'lighting':'Opposed neutral grazing light diagnostic, with a dim variant, not world lighting'")
s=s.replace("'samples':48","'samples':64")
s=s.replace("'sourceScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()","'sourceScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'baseRenderScriptSha256':hashlib.sha256((ROOT/'Source/render_actual_trunk.py').read_bytes()).hexdigest(),'keyLightPosition':list(key.location),'keyEnergy':key.data.energy,'worldStrength':s.world.node_tree.nodes['Background'].inputs['Strength'].default_value")
# __file__ deliberately remains this wrapper so metadata authenticates both.
exec(compile(s,str(ROOT/'Source/render_actual_trunk.py'),'exec'),globals())
