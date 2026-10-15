"""Controlled 4-family studio / tiling proof. No geometry or original file writes.
Blender -b -t 4 --python Source/render_material_proofs.py -- authored [studio|tile]
"""
import bpy, math, json, sys, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'tree-baseline-v219/TreeTopYokocho'
args=sys.argv[sys.argv.index('--')+1:];kind=args[0];proof=args[1] if len(args)>1 else 'studio'
assert kind in ('authored','baseline') and proof in ('studio','tile')
ORIGIN=json.loads((ROOT/'Docs/authored_pbr_origin.json').read_text())
fams=ORIGIN['families'];old=['bark_brown_02','wood_planks_grey','wood_table_001','rocky_terrain_02'];used={}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=False;s.cycles.seed=0;s.cycles.max_bounces=4
s.render.resolution_x=1600;s.render.resolution_y=1050;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.35,.35,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35

def material(i):
 f=fams[i];m=bpy.data.materials.new(f['family']);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
 maps={}
 for channel,suffix,color in [('albedo','diff_4k.jpg','sRGB'),('normalGL','nor_gl_2k.jpg','Non-Color'),('arm','arm_2k.jpg','Non-Color')]:
  path=ROOT/f['maps'][channel]['path'] if kind=='authored' else BASE/'Assets/TreeTopYokocho/Textures/PBR'/f'{old[i]}_{suffix}'
  used[str(path)]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'channel':channel}
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path));t.image.colorspace_settings.name=color;t.extension='REPEAT';maps[channel]=t
 l.new(maps['albedo'].outputs['Color'],p.inputs['Base Color']);norm=n.new('ShaderNodeNormalMap');l.new(maps['normalGL'].outputs['Color'],norm.inputs['Color']);l.new(norm.outputs['Normal'],p.inputs['Normal'])
 sep=n.new('ShaderNodeSeparateColor');l.new(maps['arm'].outputs['Color'],sep.inputs['Color']);l.new(sep.outputs['Green'],p.inputs['Roughness']);l.new(sep.outputs['Blue'],p.inputs['Metallic'])
 return m
mats=[material(i) for i in range(4)]

def area(name,loc,energy,size,color=(1,1,1)):
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler();return o
key=area('neutral key',(-3,-4,6),1100,4);area('neutral fill',(4,-1,4),300,3);area('neutral rim',(0,3,4),550,3)
c=bpy.data.cameras.new('Proof camera');camera=bpy.data.objects.new('Proof camera',c);s.collection.objects.link(camera);s.camera=camera

def render(name,extra):
 p=ROOT/'Preview'/f'{name}_{kind}.png';s.render.filepath=str(p);bpy.ops.render.render(write_still=True)
 p.with_suffix('.json').write_text(json.dumps({'scope':'Controlled Blender Cycles material proof; not Unity or VRChat runtime','mode':kind,'proof':proof,'samples':s.cycles.samples,'maps':used,'sourceScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'camera':list(camera.location),'cameraRotation':list(camera.rotation_euler),'viewTransform':'AgX Medium High Contrast','exposure':0,'denoising':'none',**extra},indent=2)+'\n')
if proof=='studio':
 # Four cylinders show uninterrupted roughness at grazing angles. UV dimensions
 # are metres scaled with each family's dominant material density.
 for i in range(4):
  bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.36,depth=1.35,location=(-1.5+i,0,.73))
  ob=bpy.context.object;ob.name=fams[i]['family']+' cylinder';ob.data.materials.append(mats[i])
  for p in ob.data.polygons:
   p.use_smooth=len(p.vertices)==4
   if len(p.vertices)==4:
    angles=[math.atan2(ob.data.vertices[ob.data.loops[li].vertex_index].co.y,ob.data.vertices[ob.data.loops[li].vertex_index].co.x)/(2*math.pi)%1 for li in p.loop_indices]
    if max(angles)-min(angles)>.5:angles=[x+1 if x<.5 else x for x in angles]
    for li,u in zip(p.loop_indices,angles):
     v=ob.data.vertices[ob.data.loops[li].vertex_index].co.z+.675
     ob.data.uv_layers.active.data[li].uv=(u*(2*math.pi*.36)/fams[i]['physicalTileMeters'][0],v/fams[i]['physicalTileMeters'][1])
 # Actual world's unchanged bevelled timber construction / UVs are included.
 sys.path.insert(0,str(BASE/'Source'));from timber_craft import timber_box_mesh
 for idx in (1,2):
  v,f,uv=timber_box_mesh((-.5+(idx-1)*1.0,-.65,.17),(.85,.45,.14),bevel=.007)
  mesh=bpy.data.meshes.new('Original bevelled timber');mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update();ob=bpy.data.objects.new('Actual timber UV '+str(idx),mesh);s.collection.objects.link(ob);ob.data.materials.append(mats[idx]);layer=mesh.uv_layers.new(name='UVMap')
  for loop in mesh.loops:layer.data[loop.index].uv=uv[loop.vertex_index]*(.65 if idx==1 else .75)
 bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object
 m=bpy.data.materials.new('Neutral floor');m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.14,.16,.17,1);p.inputs['Roughness'].default_value=.95;floor.data.materials.append(m)
 camera.location=(3.4,-7.9,3.6);camera.rotation_euler=(Vector((0,-.1,.65))-camera.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=4.6
 render('material_studio',{'familiesLeftToRight':[f['family'] for f in fams],'geometry':'Test cylinders plus unchanged original timber_box_mesh; cylinder caps are generic UVs, not endgrain claim'})
else:
 s.render.resolution_x=1200;s.render.resolution_y=1200
 for i,fam in enumerate(fams):
  size=fam['physicalTileMeters'][0]*2
  bpy.ops.mesh.primitive_plane_add(size=size);plane=bpy.context.object;plane.data.materials.append(mats[i]);plane.name='2x2 material repeat'
  for uv in plane.data.uv_layers.active.data:uv.uv*=2
  camera.location=(0,-size*.18,size*1.55);camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=size*1.025
  key.location=(-size*.5,-size*.8,size);key.rotation_euler=(-key.location).to_track_quat('-Z','Y').to_euler()
  render(fam['family']+'_tile',{'uvRepeat':[2,2],'planeSizeMeters':size,'family':fam['family'],'heightDisplacement':False})
  bpy.data.objects.remove(plane,do_unlink=True)
