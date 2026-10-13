"""Run with Blender: blender --background --python Source/open_in_blender.py"""
import bpy
from pathlib import Path
folder=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(folder/'TreeTopYokocho.glb'))
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'TreeTopYokocho.blend'))
print('Saved editable visual model. Collision data remains in the Unity package.')
