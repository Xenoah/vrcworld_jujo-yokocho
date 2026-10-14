"""Blender material/geometry preview, NOT a Unity or VRChat runtime capture.
blender -b --python Source/render_preview.py -- --view alley --samples 24
"""
import bpy, math, json, sys, argparse, hashlib
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--view',default='alley');p.add_argument('--samples',type=int,default=24);p.add_argument('--width',type=int,default=1440);p.add_argument('--save-blend',action='store_true');p.add_argument('--engine',default='CYCLES')
p.add_argument('--views',nargs='+',help='Reuse one scene import for several verified camera presets')
p.add_argument('--output-dir',type=Path,help='Optional separate study directory; does not overwrite published checkpoints')
p.add_argument('--camera',type=float,nargs=3);p.add_argument('--target',type=float,nargs=3);p.add_argument('--lens',type=float)
p.add_argument('--denoise',action='store_true',help='Standard Cycles OpenImageDenoise using scene normal/albedo passes; no image generation')
p.add_argument('--atmosphere-profile',type=Path,help='Shared authored dusk JSON; default is Assets/TreeTopYokocho/Data/DuskAtmosphere.json')
p.add_argument('--fog-density',type=float,help='Explicit comparison override, recorded in the effective profile hash')
p.add_argument('--aov',action='store_true',help='Store real scene albedo/normal EXR passes for external denoising')
p.add_argument('--fantasy-profile',type=Path,help='Explicit FantasyMaterials profile for a labelled Blender approximation')
p.add_argument('--fantasy-time',type=float,default=0,help='Fixed time snapshot in seconds, not runtime simulation')
p.add_argument('--disable-fantasy',action='store_true',help='Controlled comparison using the same geometry and camera')
a=p.parse_args(args);root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'Source'))
from dusk_atmosphere import load_profile, profile_digest, configure_world, configure_sun, configure_surface_fog, PROFILE_RELATIVE
profile_path=a.atmosphere_profile or root/PROFILE_RELATIVE
atmosphere=load_profile(profile_path)
atmosphere_profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest()
if a.fog_density is not None:
 if not 0 <= a.fog_density <= .01:raise ValueError('Fog density must be between 0 and .01')
 atmosphere['fog']['density']=a.fog_density
atmosphere_effective_sha256=profile_digest(atmosphere)
render_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
atmosphere_script_sha256=hashlib.sha256((root/'Source/dusk_atmosphere.py').read_bytes()).hexdigest()
source_hashes={str(path):hashlib.sha256((root/path).read_bytes()).hexdigest() for path in [
 Path('Assets/TreeTopYokocho/Shaders/YokochoSky.shader'),
 Path('Assets/TreeTopYokocho/Editor/DuskAtmosphereProfile.cs'),
 Path('Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs'),
 Path('Source/cloud_sea.py'),Path('Source/cloud_depth.py'),Path('Source/noren_craft.py'),Path('Source/shopfront_identity.py'),Path('Source/detail_cameras.json'),
 Path('Assets/TreeTopYokocho/Data/WorldManifest.json')]}
# Record runtime shader sources as provenance only; Blender does not execute them.
for shader_path in sorted((root/'Assets/TreeTopYokocho/Shaders').glob('*.shader')):
 source_hashes[str(shader_path.relative_to(root))]=hashlib.sha256(shader_path.read_bytes()).hexdigest()
geometry_sha256=hashlib.sha256((root/'Source/TreeTopYokocho.glb').read_bytes()).hexdigest()
manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
from venue_lighting import feature_enabled as venue_lighting_enabled,load_profile as load_venue_lighting,PROFILE_RELATIVE as VENUE_LIGHTING_RELATIVE,validate_manifest as validate_venue_lighting_manifest,preview_light,extend_fantasy_profile,configure_preview_emitters
venue_lighting_profile=load_venue_lighting(root/VENUE_LIGHTING_RELATIVE) if venue_lighting_enabled(manifest.get('features',{})) else None
validate_venue_lighting_manifest(manifest,venue_lighting_profile)
venue_lighting_report=None
if venue_lighting_profile is not None:
 source_hashes[str(VENUE_LIGHTING_RELATIVE)]=venue_lighting_profile['_sourceSha256']
 source_hashes['Source/venue_lighting.py']=hashlib.sha256((root/'Source/venue_lighting.py').read_bytes()).hexdigest()
fantasy_profile=None;fantasy_profile_sha256=None;fantasy_material_report=None;fantasy_sky_report=None;surface_craft_report=None
if not a.disable_fantasy and (a.fantasy_profile or manifest.get('features',{}).get('fantasy_materials') is True):
 from fantasy_materials import validate_profile,PROFILE_RELATIVE as FANTASY_RELATIVE
 fantasy_path=a.fantasy_profile or root/FANTASY_RELATIVE
 fantasy_profile=validate_profile(json.loads(fantasy_path.read_text()),manifest['materials'])
 if venue_lighting_profile is not None:fantasy_profile=validate_profile(extend_fantasy_profile(fantasy_profile,venue_lighting_profile),manifest['materials'])
 fantasy_profile_sha256=hashlib.sha256(fantasy_path.read_bytes()).hexdigest()
 for rel in ['Source/fantasy_preview.py','Source/surface_craft_preview.py','Source/fantasy_materials.py','Assets/TreeTopYokocho/Data/FantasyMaterials.json']:
  source_hashes[rel]=hashlib.sha256((root/rel).read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'Source/TreeTopYokocho.glb'))
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
scene.render.engine=a.engine;scene.cycles.samples=a.samples;scene.cycles.use_denoising=False
scene.cycles.seed=0;scene.cycles.use_animated_seed=False
native_denoise=False
if a.denoise:
 try:
  scene.cycles.denoiser='OPENIMAGEDENOISE';scene.cycles.use_denoising=True;native_denoise=True
 except TypeError:
  print('This Blender build has no native denoiser; raw output retained. Use Source/denoise_preview.py.',flush=True)
scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2;scene.cycles.sample_clamp_indirect=2.0;scene.cycles.blur_glossy=1.0
scene.cycles.transparent_max_bounces=24;scene.cycles.volume_bounces=0
scene.render.resolution_x=a.width;scene.render.resolution_y=round(a.width*10/16);scene.render.resolution_percentage=100
scene.view_layers[0].cycles.denoising_store_passes=a.aov
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
# Fixed display mapping for every camera; AgX is not Unity ACES pixel parity.
scene.view_settings.view_transform=atmosphere['display']['blenderTransform']
scene.view_settings.exposure=atmosphere['display']['blenderExposure']
world_atmosphere=configure_world(bpy,atmosphere)
if fantasy_profile is not None:
 from fantasy_preview import configure_sky
 fantasy_sky_report=configure_sky(bpy,atmosphere,fantasy_profile,a.fantasy_time)
def light(name,kind,pos,energy,color,size=0.15):
 d=bpy.data.lights.new(name,kind);d.energy=energy;d.color=color
 if kind=='POINT':d.shadow_soft_size=size
 ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=pos;return ob
sun=light('Blue-hour broad moon','SUN',(0,0,120),0,(1,1,1));configure_sun(sun,atmosphere['key'])
warm=light('Last sunset','SUN',(0,0,120),0,(1,1,1));configure_sun(warm,atmosphere['fill'])
sys.path.insert(0,str(root/'Source'))
if manifest.get('cloudSea'):
 from cloud_sea import configure_blender_clouds
 configure_blender_clouds(bpy,manifest)
for i,x in enumerate(manifest['lights']):
 color,energy=preview_light(x)
 light('Lantern_%03d'%i,'POINT',x['position'],energy,color,.2)
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type=='BSDF_PRINCIPLED':
   if mat.name.startswith(('PaperLight','RedLantern','WarmWindow')):node.inputs['Emission Strength'].default_value=3.0
   if mat.name.startswith('TownLights'):node.inputs['Emission Strength'].default_value=4.0

if venue_lighting_profile is not None:venue_lighting_report=configure_preview_emitters(bpy,manifest)

if fantasy_profile is not None:
 from fantasy_preview import configure_materials
 fantasy_material_report=configure_materials(bpy,fantasy_profile,root,a.fantasy_time)
 from surface_craft_preview import configure_surface_craft
 surface_craft_report=configure_surface_craft(bpy,fantasy_profile,manifest['materials'])
 applied_surface={m['name'] for m in surface_craft_report['materials']}
 fantasy_material_report['omitted']=[m for m in fantasy_material_report['omitted'] if m['name'] not in applied_surface]
 fantasy_material_report['surfaceCraftReport']='See surface_craft_approximation; unsupported graphs remain explicitly omitted.'

# Only camera-visible lantern emission; explicit lights illuminate the preview.
# This avoids noise from thousands of tiny emissive triangles in Cycles.
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in list(mat.node_tree.nodes):
  if node.type=='BSDF_PRINCIPLED' and node.inputs['Emission Strength'].default_value>0:
   strength=node.inputs['Emission Strength'].default_value
   ray=mat.node_tree.nodes.new('ShaderNodeLightPath');mul=mat.node_tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=strength
   mat.node_tree.links.new(ray.outputs['Is Camera Ray'],mul.inputs[0]);mat.node_tree.links.new(mul.outputs[0],node.inputs['Emission Strength'])

# Existing Foliage runtime ambient emission, not a new fantasy effect.
# After the general emission gate to avoid double-gating; before surface fog.
from foliage_preview import configure_foliage_emission
foliage_material_report=configure_foliage_emission(bpy,manifest['materials'])
source_hashes['Source/foliage_preview.py']=hashlib.sha256((root/'Source/foliage_preview.py').read_bytes()).hexdigest()

# Exp2 surface haze at the actual camera depth, including elevated landscapes.
# Closure-level wrapping preserves original alpha/outer transparency mixes.
surface_atmosphere=configure_surface_fog(bpy,atmosphere)
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
if manifest.get('altitudeProfile'):
 for name in ['alley','overview','arrival','lookout','telecom','crown_landing','crown_observatory','noh_stage','noh_reverse']:
  pos,target,lens=views[name];views[name]=([pos[0],pos[1],pos[2]+100],[target[0],target[1],target[2]+100],lens)
 views.update({
  'cloud_city':([-24.23946718,36.72122316,153.75],[0,740,90],30),
  'cloud_sea':([0,-40,135.75],[0,-1450,20],30),
  'cloud_world':([235,-305,235],[0,0,153],26),
  'pumps':([-28,-29,5],[-20.7,-19.5,1.5],50),
  'upper_storage':([-24,-28,163],[-7,-7,156.5],48),
  'crown_ascent':([230,-280,182],[0,0,116],38),
  'forest_city':([-24.5,35,162],[0,740,40],30),
  'snow_city':([-24.5,35,162],[0,740,60],65),
  'sea_islands':([-30,-50,160],[0,-1450,12],30),
  'whole':([250,-340,243],[0,0,130],40)})
detail_cameras=root/'Source/detail_cameras.json'
if detail_cameras.exists():
 for name,entry in json.loads(detail_cameras.read_text()).items():
  views[name]=(entry['camera'],entry['target'],entry['lens'])
names=a.views or [a.view]
if any(name not in views for name in names):raise ValueError('Unknown camera preset: '+str(names))
if a.views and (a.camera or a.target or a.lens):raise ValueError('Batch presets cannot share camera overrides')
output_dir=a.output_dir or root/'Preview';output_dir.mkdir(parents=True,exist_ok=True)
data=bpy.data.cameras.new('Preview camera');camera=bpy.data.objects.new('Preview camera',data);scene.collection.objects.link(camera)
data.clip_start=.08;data.clip_end=6000;scene.camera=camera
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();rl=nodes.new('CompositorNodeRLayers');glow=nodes.new('CompositorNodeGlare');glow.glare_type='FOG_GLOW';glow.threshold=1.6;glow.quality='MEDIUM';glow.mix=-.94;out=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(rl.outputs['Image'],glow.inputs['Image']);scene.node_tree.links.new(glow.outputs['Image'],out.inputs['Image'])
aov_files=[]
if a.aov:
 for channel,output in [('albedo','Denoising Albedo'),('normal','Denoising Normal')]:
  file=nodes.new('CompositorNodeOutputFile');file.base_path=str(output_dir/'Raw')
  file.format.file_format='OPEN_EXR';file.format.color_depth='32';file.format.color_mode='RGB'
  aov_files.append((channel,file))
  scene.node_tree.links.new(rl.outputs[output],file.inputs[0])
for name in names:
 pos,target,lens=views[name]
 if a.camera:pos=a.camera
 if a.target:target=a.target
 if a.lens:lens=a.lens
 camera.location=pos
 camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens
 for channel,file in aov_files:file.file_slots[0].path='Blender_'+name+'_'+channel+'_'
 scene.render.filepath=str(output_dir/('Blender_'+name+'.png'))
 if a.save_blend:bpy.ops.wm.save_as_mainfile(filepath=str(root/'Source/TreeTopYokocho.blend'),compress=True)
 bpy.ops.render.render(write_still=True)
 (output_dir/('Blender_'+name+'.json')).write_text(json.dumps({'renderer':'Blender '+bpy.app.version_string+' '+a.engine,'scope':'Geometry and PBR material preview; NOT Unity/VRChat runtime','camera':pos,'target':target,'lens_mm':lens,'samples':a.samples,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'source_version':manifest['version'],'fantasy_profile_sha256':fantasy_profile_sha256,'fantasy_time_seconds':a.fantasy_time,'fantasy_material_approximation':fantasy_material_report,'fantasy_sky_approximation':fantasy_sky_report,'surface_craft_approximation':surface_craft_report,'foliage_emission_approximation':foliage_material_report,'venue_lighting_approximation':venue_lighting_report,'geometry_sha256':geometry_sha256,'atmosphere_profile_sha256':atmosphere_profile_sha256,'atmosphere_effective_sha256':atmosphere_effective_sha256,'render_script_sha256':render_script_sha256,'atmosphere_script_sha256':atmosphere_script_sha256,'source_sha256':source_hashes,'display':atmosphere['display'],'world_atmosphere':world_atmosphere,'surface_atmosphere':surface_atmosphere,'cycles_seed':scene.cycles.seed,'transparent_bounces':scene.cycles.transparent_max_bounces,'denoising':'Cycles OpenImageDenoise with scene normal/albedo passes' if native_denoise else 'none','denoising_scene_passes':a.aov},indent=2))
