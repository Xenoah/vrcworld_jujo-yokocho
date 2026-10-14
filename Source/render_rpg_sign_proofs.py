"""Blender actual mesh/UV typography proof. Neutral inspection, not world lighting."""
import bpy,math,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'Preview/rpg-sign-model-proofs'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(OUT/'actual-signs.glb'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False
scene.render.resolution_x=1400;scene.render.resolution_y=520;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.world.color=(.3,.3,.3)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
# Base-color emission is an explicit neutral inspection mode to reveal exact ink.
# Mesh silhouettes and production UVs are unchanged; this is not light-look QA.
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 nodes=mat.node_tree.nodes;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');p=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
 if p:
  e=nodes.new('ShaderNodeEmission');e.inputs['Strength'].default_value=1
  if p.inputs['Base Color'].is_linked:mat.node_tree.links.new(p.inputs['Base Color'].links[0].from_socket,e.inputs['Color'])
  else:e.inputs['Color'].default_value=p.inputs['Base Color'].default_value
  mat.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
cam_data=bpy.data.cameras.new('Typography verification');cam=bpy.data.objects.new('Typography verification',cam_data);scene.collection.objects.link(cam);scene.camera=cam;cam_data.type='ORTHO'
proof=[]
for i in range(8):
 sid=f'S{i+1:02d}'
 for ob in scene.objects:
  if ob.type=='MESH':ob.hide_render=not ob.name.startswith('Shops/'+sid+'/')
 target={0:(.35,3.14,2.54),1:(0,3.42,2.85),2:(.30,2.97,2.51),3:(.30,3.568,2.60),4:(.05,3.39,2.60),5:(-.30,3.527,2.57),6:(-.15,3.50,2.60),7:(0,3.08,2.52)}[i]
 cam.location=(target[0],target[1]+8,target[2]);cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.ortho_scale={0:4.1,1:3.7,2:3.1,3:3.0,4:4.0,5:2.5,6:3.15,7:2.7}[i]
 path=OUT/(sid+'-actual-model.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
 proof.append(dict(shop=sid,path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),camera=list(cam.location),target=target,orthoScale=cam_data.ortho_scale))
(OUT/'renders.json').write_text(json.dumps(dict(mode='Neutral albedo emission inspection of actual production sign mesh and UV; not Unity or integrated lighting',glbSha256=hashlib.sha256((OUT/'actual-signs.glb').read_bytes()).hexdigest(),renders=proof),indent=2))
