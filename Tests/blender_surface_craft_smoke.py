"""Real imported-node guard. Run with Blender, -- --asset-root PROJECT."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--asset-root',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);root=a.asset_root.resolve()
sys.path.insert(0,str(root/'Source'));sys.path.insert(0,str(HERE))
from surface_craft_preview import configure_surface_craft
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'Source/TreeTopYokocho.glb'))
profile=json.loads((root/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text());manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
def signature(socket):return [(l.from_node.name,l.from_socket.name) for l in socket.links],str(socket.default_value)
def snapshot():
 result={}
 for mat in bpy.data.materials:
  if not mat.use_nodes:continue
  for node in mat.node_tree.nodes:
   if node.type=='BSDF_PRINCIPLED':result[mat.name]={key:signature(node.inputs[key]) for key in ('Base Color','Normal','Emission Color','Emission Strength')}
 return result
before=snapshot();images=sum(n.type=='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes)
report=configure_surface_craft(bpy,profile,manifest['materials'])
assert snapshot()==before,'Protected material links changed'
assert sum(n.type=='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes)==images,'Added image samples'
assert not report['omitted'],report['omitted']
assert {'Cedar','Counter','Bronze','CityLimestone'} <= {x['name'] for x in report['materials']}
nodecount=sum(len(m.node_tree.nodes) for m in bpy.data.materials if m.use_nodes)
again=configure_surface_craft(bpy,profile,manifest['materials'])
assert not again['materials'],'Repeated call compounded craft'
assert sum(len(m.node_tree.nodes) for m in bpy.data.materials if m.use_nodes)==nodecount,'Repeated call added nodes'
fixture=bpy.data.materials.new('MissingFactorFixture');fixture.use_nodes=True
fixture.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.2,.3,.4,1)
fixture_nodes=len(fixture.node_tree.nodes)
fixture_profile={'materialGroups':[{'names':['MissingFactorFixture'],'shader':'Surface','keywords':['_YOKOCHO_CRAFT'],'floats':[{'name':'_GrainRoughness','value':.11}]}]}
fixture_report=configure_surface_craft(bpy,fixture_profile,[{'name':'MissingFactorFixture','color':[.2,.3,.4],'texture':'','roughness':.8}])
assert not fixture_report['materials'] and len(fixture_report['omitted'])==1
assert 'Nonwhite' in fixture_report['omitted'][0]['reason']
assert len(fixture.node_tree.nodes)==fixture_nodes
report['validation']={'missingNonwhiteFactorFailsClosed':True,'protectedLinksUnchanged':True,'imageNodeCountUnchanged':True,'idempotent':True,'appliedCount':len(report['materials'])}
report['blenderVersion']=bpy.app.version_string
report['sourceSha256']={rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in ['Source/TreeTopYokocho.glb','Source/surface_craft_preview.py','Assets/TreeTopYokocho/Data/FantasyMaterials.json','Assets/TreeTopYokocho/Data/WorldManifest.json','Tests/blender_surface_craft_smoke.py']}
output=a.report or root/'Docs/surface_craft_preview_validation.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['validation'],indent=2))
