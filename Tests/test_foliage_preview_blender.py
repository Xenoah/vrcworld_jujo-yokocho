"""Run Blender -b --python Tests/test_foliage_preview_blender.py -- --project-root ROOT.
Imports actual GLB only; no scene render. ROOT defaults to installed project.
"""
import bpy,argparse,json,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--helper-root',type=Path);p.add_argument('--report',type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=a.project_root.resolve();helpers=(a.helper_root or root).resolve();sys.path.insert(0,str(helpers/'Source'))
from foliage_preview import configure_foliage_emission
materials=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())['materials'];selected={m['name'] for m in materials if m.get('shader')=='Foliage'}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'Source/TreeTopYokocho.glb'))
def socket_state(s):
 if s.is_linked:return [(x.from_node.name,x.from_socket.name) for x in s.links]
 value=getattr(s,'default_value',None)
 try:return tuple(value)
 except TypeError:return value if isinstance(value,(str,int,float,bool,type(None))) else str(value)
def snap(m,ignore_emission=False):
 if not m.use_nodes:return {'nodes':None}
 return {n.name:{'type':n.type,'inputs':{str(i)+':'+s.name:socket_state(s) for i,s in enumerate(n.inputs) if not(ignore_emission and n.type=='BSDF_PRINCIPLED' and s.name in ('Emission Color','Emission Strength'))}} for n in m.node_tree.nodes}
before={m.name:snap(m,m.name in selected) for m in bpy.data.materials};image_count=sum(n.type=='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes)
r=configure_foliage_emission(bpy,materials);applied={x['name'] for x in r['applied']}
assert applied==selected & set(before),(applied,selected)
for m in bpy.data.materials:
 after=snap(m,m.name in selected)
 for name,old in before[m.name].items():assert after[name]==old,(m.name,name)
 if m.name not in applied:assert after==before[m.name],m.name
 else:
  assert len(after)==len(before[m.name])+2
  bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');base=bs.inputs['Base Color'];em=bs.inputs['Emission Color']
  assert socket_state(base)==socket_state(em)
  mul=bs.inputs['Emission Strength'].links[0].from_node;assert mul.operation=='MULTIPLY' and abs(mul.inputs[1].default_value-.035)<1e-7
  assert mul.inputs[0].links[0].from_socket.name=='Is Camera Ray'
assert sum(n.type=='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes)==image_count
after_all={m.name:snap(m) for m in bpy.data.materials};configure_foliage_emission(bpy,materials);assert after_all=={m.name:snap(m) for m in bpy.data.materials}
# Negative admission fixtures must preserve their graphs and report omissions.
no=bpy.data.materials.new('FixtureNoNodes');linked=bpy.data.materials.new('FixtureExistingEmission');linked.use_nodes=True;bs=next(n for n in linked.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Emission Strength'].default_value=.2
negative_before=snap(linked);neg=configure_foliage_emission(bpy,[{'name':n,'shader':'Foliage'} for n in ['FixtureAbsent','FixtureNoNodes','FixtureExistingEmission']]);assert not neg['applied'];assert len(neg['omitted'])==3;assert snap(linked)==negative_before
r['negativeFixtures']=neg['omitted'];r['tests']={'protectedOldNodesAndLinksUnchanged':True,'nonselectedGraphsUnchanged':True,'alphaUnchanged':True,'noExtraImageNodes':True,'exactCameraGateAndFactor':True,'idempotent':True,'negativeAdmissionPreserved':True};r['geometrySHA256']=hashlib.sha256((root/'Source/TreeTopYokocho.glb').read_bytes()).hexdigest();r['helperSHA256']=hashlib.sha256((helpers/'Source/foliage_preview.py').read_bytes()).hexdigest();r['blender']=bpy.app.version_string
if a.report:a.report.write_text(json.dumps(r,indent=2)+'\n')
print('FOLIAGE_PREVIEW_TEST_PASS',json.dumps(r))
