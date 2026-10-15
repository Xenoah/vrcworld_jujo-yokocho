"""Render exact authored/native mesh triangles, not a concept image.
Blender: blender -b -t 4 -P render_entry_preview.py -- BASELINE_ROOT OUTPUT_ROOT
Shows local entry geometry; remote scenery intentionally omitted for review.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];BASE=Path(args[0]).resolve();OUT=Path(args[1]).resolve();sys.path.insert(0,str(OUT/'Source'))
from entry_geometry_io import read_geometry,parse_geometry
cfg=json.loads((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlaza.json').read_text());base=json.loads((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials={}
for prefix,specs,texroot in [('core',base['materials'],BASE/'Assets/TreeTopYokocho/Textures'),('entry',cfg['materials'],OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Textures')]:
 for s in specs:
  m=bpy.data.materials.new(prefix+'_'+s['name']);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');col=s['color'];bs.inputs['Base Color'].default_value=(*col[:3],1);bs.inputs['Roughness'].default_value=s.get('roughness',.8);bs.inputs['Metallic'].default_value=s.get('metallic',0)
  tex=s.get('texture','')
  if tex and (texroot/tex).exists():
   im=bpy.data.images.load(str(texroot/tex),check_existing=True);node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=im
   if all(abs(c-1)<1e-4 for c in col[:3]):m.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
   else:
    mix=m.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*col[:3],1);m.node_tree.links.new(node.outputs['Color'],mix.inputs[1]);m.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
  materials[(prefix,s['name'])]=m
sources=[('core',read_geometry(BASE,'Visual')),('entry',parse_geometry((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlazaMeshes.bytes').read_bytes()))]
counts={}
for prefix,ms in sources:
 count=0
 for m in ms:
  v=m['vertices'];f=m['faces']
  if prefix=='core':
   tri=v[f];keep=np.all(tri.max(axis=1)>[-12,-35,133.50],axis=1)&np.all(tri.min(axis=1)<[10,-25.55,138],axis=1);f=f[keep]
  if not len(f):continue
  used,flat=np.unique(f,return_inverse=True);f=flat.reshape(-1,3);v=v[used];uv=m['uv'][used]
  mesh=bpy.data.meshes.new(m['group']);mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update();ob=bpy.data.objects.new(m['group'],mesh);bpy.context.collection.objects.link(ob);ob.data.materials.append(materials[(prefix,m['material'])])
  layer=mesh.uv_layers.new(name='UVMap')
  for p in mesh.polygons:
   for vi,li in zip(p.vertices,p.loop_indices):layer.data[li].uv=uv[vi]
  count+=len(f)
 counts[prefix]=count
control_proof=None
if len(args)>2:
 controlroot=Path(args[2]).resolve();atlas=controlroot/'Assets/TreeTopYokochoEntrySystems/Textures/entry_control_labels.png';installer=controlroot/'Assets/TreeTopYokochoEntrySystems/Editor/EntrySystemsInstaller.cs';code=installer.read_text()
 # Match exact owner installer U orientation and source-X order, never silently fix.
 flip='new Vector2(1,low), new Vector2(0,low)' in code
 left_first='index % 2 == 0 ? .36f : -.36f' in code
 assert '135.50f - (index / 2) * .24f' in code, 'Control row pitch differs from final reviewed source'
 assert flip and left_first, 'Expected owner-reviewed source-readable control layout is not present yet'
 material=bpy.data.materials.new('Owner control atlas (unlit approximation)');material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');emit=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(atlas));material.node_tree.links.new(tex.outputs['Color'],emit.inputs['Color']);material.node_tree.links.new(emit.outputs[0],output.inputs[0])
 for i,(x,y,z) in enumerate(cfg['systemsControlAnchor']['buttonCenters']):
  y+=.019;verts=[(x-.30,y,z-.095),(x+.30,y,z-.095),(x+.30,y,z+.095),(x-.30,y,z+.095)];low=1-(i+1)/6;high=1-i/6;uv=[(1,low),(0,low),(0,high),(1,high)]
  mesh=bpy.data.meshes.new('OwnerControl'+str(i));mesh.from_pydata(verts,[],[(0,2,1),(0,3,2)]);mesh.update();ob=bpy.data.objects.new('OwnerControl'+str(i),mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material);layer=mesh.uv_layers.new(name='UVMap')
  for face in mesh.polygons:
   for vi,li in zip(face.vertices,face.loop_indices):layer.data[li].uv=uv[vi]
 control_proof=dict(scope='Static installer label-layout approximation. Not Udon runtime or dynamic clock/status. All six button centers and face dimensions match owner source.',atlasSha256=hashlib.sha256(atlas.read_bytes()).hexdigest(),installerSha256=hashlib.sha256(installer.read_bytes()).hexdigest(),sourcePositiveYReadableUFlip=flip,viewerLeftColumnFirst=left_first)

world=bpy.data.worlds.new('Review soft dusk environment');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.31,.37,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;bpy.context.scene.world=world
# Review-only lighting. Nothing here enters Unity runtime.
for name,loc,energy,size,col in [('Warm sky',(-5,-28,145),2100,10,(1,.87,.66)),('Fill',(-1,-24,140),1200,8,(.69,.84,1))]:
 light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;light.color=col;ob=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((-6,-30,135))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Entry review');obj=bpy.data.objects.new('Entry review',cam);bpy.context.collection.objects.link(obj);bpy.context.scene.camera=obj
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.render.resolution_x=1440;scene.render.resolution_y=960;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
views=[('entry-plaza-native-oblique.png',(-3.5,-25.8,138.7),(-6.2,-30.2,135.2),28),('entry-plaza-native-eye.png',(-3.7,-28.6,135.70),(-6.1,-31.7,135.45),22),('entry-guideboard-interaction-distance.png',(-5.1,-30.8,135.65),(-5.1,-32.3,135.67),16)]
if control_proof:views.append(('entry-controls-static-layout.png',(-8,-30.5,135.65),(-8,-31.8,135.45),20))
for name,loc,target,lens in views:
 obj.location=loc;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();cam.lens=lens;scene.render.filepath=str(OUT/'Preview'/name);bpy.ops.render.render(write_still=True)
(OUT/'Docs/entry-preview-provenance.json').write_text(json.dumps(dict(source='Exact v2.19 native triangle excerpt + exact EntryPlazaMeshes.bytes',entryConfigSha256=hashlib.sha256((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlaza.json').read_bytes()).hexdigest(),entryNativeSha256=hashlib.sha256((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlazaMeshes.bytes').read_bytes()).hexdigest(),triangleCounts=counts,contextClip=[[-12,-35,133.5],[10,-25.55,138]],lighting='Review-only soft area lights; not runtime Unity lighting. Addon adds zero Unity lights.',scope='Local entrance context only. Remote scenery not rendered.',views=[dict(file=v[0],camera=v[1],target=v[2],lens=v[3]) for v in views],eyeCameraRoute='SpawnToGuide vertex (-3.7,-28.6), 1.70 m above floor',samples=32,controlProof=control_proof),indent=2)+'\n')
