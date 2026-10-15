"""Unchanged v2.19 trunk geometry + exact AI albedo, no paired normal/height.
This isolates the actual giant tree for scale/repetition evaluation. It is not
an admitted world, Unity runtime, a PBR proof, or a photo/scan claim.
"""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'tree-baseline-v219/TreeTopYokocho'
args=sys.argv[sys.argv.index('--')+1:];kind=args[0]
origin=json.loads((ROOT/'Docs/authored_pbr_origin.json').read_text())
fam=origin['families'][0]
src=ROOT/fam['maps']['albedo']['path']
geom=BASE/'Source/TreeTopYokocho.glb';bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(geom))
kept=[]
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and ob.name.startswith('Tree/Trunk__Bark'):kept.append(ob)
 else:bpy.data.objects.remove(ob,do_unlink=True)
assert len(kept)==1,[ob.name for ob in kept]
mat=bpy.data.materials['Bark'];nodes=mat.node_tree.nodes;links=mat.node_tree.links
used=[]
if kind=='authored':
 for n in nodes:
  if n.type!='TEX_IMAGE':continue
  ch={'BASE COLOR':'albedo','NORMAL MAP':'normalGL','METALLIC ROUGHNESS':'arm','OCCLUSION':'arm'}.get(n.label)
  if ch:
   path=ROOT/fam['maps'][ch]['path'];n.image=bpy.data.images.load(str(path),check_existing=True);n.image.colorspace_settings.name='sRGB' if ch=='albedo' else 'Non-Color';used.append({'channel':ch,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.seed=0;s.cycles.use_denoising=False;s.cycles.max_bounces=3
s.render.resolution_x=1200;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.35,.35,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
for name,pos,energy,size in [('neutral key',(6,-20,154),6000,14),('neutral fill',(-18,-8,148),2500,18)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,143))-o.location).to_track_quat('-Z','Y').to_euler()
c=bpy.data.cameras.new('Actual trunk scale camera');o=bpy.data.objects.new('Actual trunk scale camera',c);s.collection.objects.link(o);s.camera=o;c.clip_start=.05;c.clip_end=1000
for name,pos,target,lens in [('close',(4,-11,143),(3,-6,142),48),('mid',(25,-30,156),(0,0,143),46)]:
 o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.lens=lens
 out=ROOT/'Preview'/f'actual_trunk_{kind}_{name}.png';s.render.filepath=str(out);bpy.ops.render.render(write_still=True)
 out.with_suffix('.json').write_text(json.dumps({'scope':'Actual immutable v2.19 giant trunk isolated for PBR artistic scale/repetition proof, not Unity runtime','mode':kind,'maps':used,'geometrySha256':hashlib.sha256(geom.read_bytes()).hexdigest(),'objects':[x.name for x in kept],'geometryChanged':False,'uvChanged':False,'materialIdsChanged':False,'uvScale':.36,'normalMapping':'Original GLB tangent/normal bindings retained; images only replaced','lighting':'identical neutral studio on actual trunk geometry, not world lighting','camera':pos,'target':target,'lens':lens,'samples':48,'denoising':'none','denoising_scene_passes':False,'sourceScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
