"""Offline source contract, literal freeze pins and C# syntax checks."""
from pathlib import Path
import hashlib,json,re,sys
from tree_sitter import Language,Parser
import tree_sitter_c_sharp
from entry_geometry_io import parse_geometry
ROOT=Path(__file__).resolve().parent.parent;A=ROOT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza';CS=ROOT/'Assets/TreeTopYokochoEntrySystems/Editor/EntryPlazaBuilder.cs';source=CS.read_text();cfg=json.loads((A/'Data/EntryPlaza.json').read_text());checks={}
checks['csharp_syntax']=not Parser(Language(tree_sitter_c_sharp.language())).parse(CS.read_bytes()).root_node.has_error
pins=re.findall(r'\{ "((?:Data|Textures)/[^\"]+)", "([0-9a-f]{64})" \}',source)
checks['literal_pins_match']=len(pins)==10 and all(hashlib.sha256((A/p).read_bytes()).hexdigest()==h for p,h in pins)
checks['literal_config_constant']=hashlib.sha256((A/'Data/EntryPlaza.json').read_bytes()).hexdigest() in re.search(r'ApprovedConfigSha256 = "(.*?)"',source).group(1)
checks['literal_native_constant']=hashlib.sha256((A/'Data/EntryPlazaMeshes.bytes').read_bytes()).hexdigest()==re.search(r'ApprovedNativeSha256 = "(.*?)"',source).group(1)
checks['no_runtime_lights_or_stations']=cfg['addedLights']==0 and cfg['addedStations']==0 and 'AddComponent<Light>' not in source and 'AddUdonSharpComponent<YokochoSeat>' not in source
checks['owned_roots_only']='root.Find("EntryPlaza")' in source and 'core.transform.SetParent' not in source and 'new GameObject("EntryPlaza")' in source and 'EditorSceneManager' not in source
checks['installer_owns_generated_dir']='Build(Transform root, string generatedAssetDirectory)' in source and 'refusing an in-place overwrite' in source
checks['exact_target_heights']={w['id']:w['destination'][2] for w in cfg['warps']}=={'Entry_To_G0':.08,'Entry_To_L2':140.08,'Entry_To_L3':146.08} and 'expectedZ' in source
anchor=cfg['systemsControlAnchor'];width,depth,height=anchor['buttonSize']
checks['button_faces_within_panel']=all(anchor['usableMin'][0] <= p[0]-width/2 and p[0]+width/2 <= anchor['usableMax'][0] and anchor['usableMin'][2] <= p[2]-height/2 and p[2]+height/2 <= anchor['usableMax'][2] for p in anchor['buttonCenters'])
checks['button_viewer_left_first']=all(anchor['buttonCenters'][i][0]>anchor['buttonCenters'][i+1][0] for i in [0,2,4])
checks['recovery_reuse']='AddUdonSharpComponent<YokochoTeleport>' in source and 'teleport.recovery = recovery' in source and 'core.GetComponentInChildren<YokochoSafety>' in source
checks['finite_axes_range']='!Finite(v) || Math.Abs(v' in source and '!Finite(w.range)' in source
ms=parse_geometry((A/'Data/EntryPlazaMeshes.bytes').read_bytes());checks['native_geometry_counts']=sum(len(m['faces']) for m in ms)==cfg['triangles'] and len(ms)==cfg['meshCount']
from fontTools.ttLib import TTFont
BASE=Path(sys.argv[1]);font=TTFont(BASE/'Source/fonts/upstream/kleeone/KleeOne-Regular.ttf');cmap=font.getBestCmap();chars={c for c in (ROOT/'Source/build_entry_plaza.py').read_text() if ord(c)>127};checks['baked_japanese_glyph_coverage']=not [c for c in chars if ord(c) not in cmap]
report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,scope='Offline syntax/contracts only. Not a Unity compiler, Udon compiler, play-mode or VRChat test.')
(ROOT/'Docs/entry-plaza-contract-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert all(checks.values())
