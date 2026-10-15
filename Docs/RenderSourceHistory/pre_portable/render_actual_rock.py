"""Actual immutable ServiceBank Stone mesh and UVs under matched neutral light."""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'tree-baseline-v219/TreeTopYokocho';geom=BASE/'Source/TreeTopYokocho.glb'
origin=json.loads((ROOT/'Docs/authored_pbr_origin.json').read_text());fam=origin['families'][3]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(geom))
kept=[]
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and ob.name=='Infrastructure/Ground/ServiceBank__Stone':kept.append(ob)
 else:bpy.data.objects.remove(ob,do_unlink=True)
assert len(kept)==1
points=[kept[0].matrix_world@Vector(x) for x in kept[0].bound_box];lo=[min(v[k] for v in points) for k in range(3)];hi=[max(v[k] for v in points) for k in range(3)];center=Vector([(lo[k]+hi[k])/2 for k in range(3)])
mat=bpy.data.materials['Stone'];s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.seed=0;s.cycles.use_denoising=False;s.cycles.max_bounces=4
s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.35,.35,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
lights=[]
for name,offset,energy,size in [('key',(-4,-4,7),1000,4),('fill',(4,2,5),350,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=center+Vector(offset);o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
c=bpy.data.cameras.new('Actual rock material camera');o=bpy.data.objects.new('Actual rock material camera',c);s.collection.objects.link(o);s.camera=o;o.location=center+Vector((-4,-5,4));o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler();c.lens=44;c.clip_start=.05
for kind in ('baseline','authored'):
 used=[]
 if kind=='authored':
  for n in mat.node_tree.nodes:
   if n.type!='TEX_IMAGE':continue
   ch={'BASE COLOR':'albedo','NORMAL MAP':'normalGL','METALLIC ROUGHNESS':'arm','OCCLUSION':'arm'}.get(n.label)
   if ch:
    path=ROOT/fam['maps'][ch]['path'];n.image=bpy.data.images.load(str(path),check_existing=True);n.image.colorspace_settings.name='sRGB' if ch=='albedo' else 'Non-Color';used.append({'channel':ch,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 p=ROOT/'Preview'/f'actual_rock_{kind}.png';s.render.filepath=str(p);bpy.ops.render.render(write_still=True)
 p.with_suffix('.json').write_text(json.dumps({'scope':'Isolated actual v2.19 ServiceBank Stone geometry/UVs/tint. Blender neutral matched-light artistic proof, not world lighting or Unity runtime.','mode':kind,'maps':used,'geometrySha256':hashlib.sha256(geom.read_bytes()).hexdigest(),'object':kept[0].name,'bounds':[lo,hi],'geometryChanged':False,'uvChanged':False,'materialIdsChanged':False,'uvScale':.65,'camera':list(o.location),'cameraTarget':list(center),'lens':44,'samples':48,'denoising':'none','sourceScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
