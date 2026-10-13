"""Blender material/geometry preview, NOT a Unity or VRChat runtime capture.
blender -b --python Source/render_preview.py -- --view alley --samples 24
"""
import bpy, math, json, sys, argparse, hashlib
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--view',default='alley');p.add_argument('--samples',type=int,default=24);p.add_argument('--width',type=int,default=1440);p.add_argument('--save-blend',action='store_true');p.add_argument('--engine',default='CYCLES')
a=p.parse_args(args);root=Path(__file__).resolve().parent.parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'Source/TreeTopYokocho.glb'))
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
scene.render.engine=a.engine;scene.cycles.samples=a.samples;scene.cycles.use_denoising=False
scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2;scene.cycles.sample_clamp_indirect=2.0;scene.cycles.blur_glossy=1.0
scene.cycles.transparent_max_bounces=24;scene.cycles.volume_bounces=0
scene.render.resolution_x=a.width;scene.render.resolution_y=round(a.width*10/16);scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.2
world=bpy.data.worlds.new('Blue hour atmosphere');scene.world=world;world.use_nodes=True
n=world.node_tree.nodes;l=world.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputWorld');bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=2.8
tex=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');ramp=n.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=0;ramp.color_ramp.elements[0].color=(.11,.15,.23,1)
ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.009,.022,.065,1)
l.new(tex.outputs['Normal'],sep.inputs[0]);l.new(sep.outputs['Z'],ramp.inputs[0]);l.new(ramp.outputs[0],bg.inputs['Color']);l.new(bg.outputs[0],out.inputs['Surface'])
# Keep a blue-hour visible horizon while preserving readable indirect fill.
# This is preview lighting only; Unity uses the bundled procedural sky/bake.
cam_bg=n.new('ShaderNodeBackground');cam_bg.inputs['Strength'].default_value=.38
l.new(ramp.outputs[0],cam_bg.inputs['Color']);ray=n.new('ShaderNodeLightPath');mix=n.new('ShaderNodeMixShader')
l.new(ray.outputs['Is Camera Ray'],mix.inputs[0]);l.new(bg.outputs[0],mix.inputs[1]);l.new(cam_bg.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
def light(name,kind,pos,energy,color,size=0.15):
 d=bpy.data.lights.new(name,kind);d.energy=energy;d.color=color
 if kind=='POINT':d.shadow_soft_size=size
 ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=pos;return ob
sun=light('Blue-hour broad moon','SUN',(0,0,120),.85,(.47,.62,1));sun.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-35));sun.data.angle=.18
warm=light('Last sunset','SUN',(0,0,120),.17,(1,.48,.19));warm.rotation_euler=(math.radians(76),math.radians(15),math.radians(110));warm.data.angle=.35
manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
for i,x in enumerate(manifest['lights']):
 light('Lantern_%03d'%i,'POINT',x['position'],x['strength']*110,(1,.48,.16),.2)
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type=='BSDF_PRINCIPLED':
   if mat.name.startswith(('PaperLight','RedLantern','WarmWindow')):node.inputs['Emission Strength'].default_value=3.0
   if mat.name.startswith('TownLights'):node.inputs['Emission Strength'].default_value=4.0

# Only camera-visible lantern emission; explicit lights illuminate the preview.
# This avoids noise from thousands of tiny emissive triangles in Cycles.
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in list(mat.node_tree.nodes):
  if node.type=='BSDF_PRINCIPLED' and node.inputs['Emission Strength'].default_value>0:
   strength=node.inputs['Emission Strength'].default_value
   ray=mat.node_tree.nodes.new('ShaderNodeLightPath');mul=mat.node_tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=strength
   mat.node_tree.links.new(ray.outputs['Is Camera Ray'],mul.inputs[0]);mat.node_tree.links.new(mul.outputs[0],node.inputs['Emission Strength'])

# Thin atmospheric volume is limited to distant landscape; keep the near walk legible.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-35));mist=bpy.context.object;mist.name='Preview-only distance atmosphere';mist.scale=(6200,6200,90)
mat=bpy.data.materials.new('Preview mist');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();vol=nodes.new('ShaderNodeVolumeScatter');vol.inputs['Color'].default_value=(.38,.52,.72,1);vol.inputs['Density'].default_value=.00028;vol.inputs['Anisotropy'].default_value=.2;out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(vol.outputs[0],out.inputs['Volume']);mist.data.materials.append(mat)
views={
 'alley':([-12.4,-17.8,42.2],[-5.7,-9.5,41.6],34),
 'overview':([47,-63,55],[0,1,43],52),
 'arrival':([9,-39,37.5],[-1,-24,36],48),
 'lookout':([-24.5,23.4,53.75],[-110,137,23],48),
 'forest_city':([-24.5,35,62],[0,740,30],30),
 'snow_city':([-24.5,35,62],[0,740,60],65),
 'sea_islands':([-30,-50,60],[0,-1450,12],30),
 'utilities':([-42,-50,16],[-14,-14,15],28),
 'telecom':([40,-65,115],[-2.9,-4.7,109.5],40),
 'crown_ascent':([167,-188,121],[0,0,60],42),
 'crown_landing':([26,-61,49],[0,-37,35],34),
 'crown_observatory':([49,-56,137],[0,0,108],36),
 'noh_stage':([17.2,4,41.65],[10.1,10.1,41.35],32),
 'noh_reverse':([3,17.5,41.65],[10.1,10.1,41.35],32),
 'whole':([125,-156,92],[0,0,56],52)
}
pos,target,lens=views[a.view]
data=bpy.data.cameras.new('Preview camera');camera=bpy.data.objects.new('Preview camera',data);scene.collection.objects.link(camera);camera.location=pos
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;data.clip_start=.08;data.clip_end=6000;scene.camera=camera
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();rl=nodes.new('CompositorNodeRLayers');glow=nodes.new('CompositorNodeGlare');glow.glare_type='FOG_GLOW';glow.threshold=1.6;glow.quality='MEDIUM';glow.mix=-.94;out=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(rl.outputs['Image'],glow.inputs['Image']);scene.node_tree.links.new(glow.outputs['Image'],out.inputs['Image'])
scene.render.filepath=str(root/'Preview'/('Blender_'+a.view+'.png'))
if a.save_blend:bpy.ops.wm.save_as_mainfile(filepath=str(root/'Source/TreeTopYokocho.blend'),compress=True)
bpy.ops.render.render(write_still=True)
(root/'Preview'/('Blender_'+a.view+'.json')).write_text(json.dumps({'renderer':'Blender '+bpy.app.version_string+' '+a.engine,'scope':'Geometry and PBR material preview; NOT Unity/VRChat runtime','camera':pos,'target':target,'samples':a.samples,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'source_version':manifest['version'],'geometry_sha256':hashlib.sha256((root/'Source/TreeTopYokocho.glb').read_bytes()).hexdigest(),'transparent_bounces':scene.cycles.transparent_max_bounces},indent=2))
