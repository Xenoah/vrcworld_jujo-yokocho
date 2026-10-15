"""Read-only v2.19 scene comparison via map overrides, not a published scene.

Usage: blender -b -t 4 --python Source/render_world_texture_study.py -- authored
       --views deck_walk crafted_alley --width 1280 --samples 32
All geometry, materials IDs, tints, cameras and scene settings stay baseline.
Only the selected maps change. No new GLB or baseline files are written.
"""
from pathlib import Path
import sys,json,hashlib
_STUDY_ROOT=Path(__file__).resolve().parents[1]
_BASE=_STUDY_ROOT if (_STUDY_ROOT/'Source/TreeTopYokocho.glb').is_file() and (_STUDY_ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').is_file() else _STUDY_ROOT.parent/'tree-baseline-v219/TreeTopYokocho'
_WRAPPER_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_args=sys.argv[sys.argv.index('--')+1:]
_MODE=_args.pop(0)
assert _MODE in ('baseline','authored')
_OUT=_STUDY_ROOT/'Preview'/('world_'+_MODE)
_OUT.mkdir(exist_ok=True)
sys.argv=sys.argv[:sys.argv.index('--')+1]+_args+['--output-dir',str(_OUT)]
_script=_BASE/'Source/render_preview.py'
_s=_script.read_text()
_injection='''
# Authored-PBR read-only comparison hook, after imported scene setup.
if _MODE == 'authored':
 _origin=json.loads((_STUDY_ROOT/'Docs/authored_pbr_origin.json').read_text())
 _mapping=_origin['replacementMapping']
 _replaced=[]
 for _spec in manifest['materials']:
  _old=next((k for k in _mapping if k in _spec.get('texture','')),None)
  if _old is None:continue
  _mat=bpy.data.materials.get(_spec['name'])
  if not _mat or not _mat.use_nodes:continue
  for _node in _mat.node_tree.nodes:
   if _node.type!='TEX_IMAGE':continue
   _channel={'BASE COLOR':'albedo','NORMAL MAP':'normal','METALLIC ROUGHNESS':'arm','OCCLUSION':'arm'}.get(_node.label)
   if not _channel:continue
   _path=_STUDY_ROOT/'Assets/TreeTopYokochoOriginalPbr/Textures'/_mapping[_old][_channel]
   if not _path.exists():continue
   _node.image=bpy.data.images.load(str(_path),check_existing=True)
   _node.image.colorspace_settings.name='sRGB' if _channel=='albedo' else 'Non-Color'
   _replaced.append([_spec['name'],_node.label,str(_path.relative_to(_STUDY_ROOT)),hashlib.sha256(_path.read_bytes()).hexdigest()])
 (_OUT/'texture_override_evidence.json').write_text(json.dumps({'scope':'Actual v2.19 GLB geometry with authored maps in Blender only; not Unity/VRChat runtime','originalGeometrySha256':geometry_sha256,'sourceScriptSha256':_WRAPPER_SHA,'coreRenderScriptSha256':hashlib.sha256(_script.read_bytes()).hexdigest(),'originSha256':hashlib.sha256((_STUDY_ROOT/'Docs/authored_pbr_origin.json').read_bytes()).hexdigest(),'overrides':_replaced},indent=2)+'\\n')
'''
_marker='# Only camera-visible lantern emission; explicit lights illuminate the preview.'
assert _marker in _s
_s=_s.replace(_marker,_injection+'\n'+_marker)
__file__=str(_script)
exec(compile(_s,str(_script),'exec'),globals())

# Bind each new rendered image metadata to this exact overlay wrapper and origin.
for _proof_json in _OUT.glob('Blender_*.json'):
 _proof=json.loads(_proof_json.read_text())
 _proof['originalPbrSourceScriptSha256']=_WRAPPER_SHA
 _proof['originalPbrOriginSha256']=hashlib.sha256((_STUDY_ROOT/'Docs/authored_pbr_origin.json').read_bytes()).hexdigest()
 _proof['originalPbrMode']=_MODE
 _proof_json.write_text(json.dumps(_proof,indent=2)+'\n')
