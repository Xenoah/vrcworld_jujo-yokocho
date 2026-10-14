"""Audit actual manifest/native/GLB fixture routing against an explicit prior build.

The prior build must be a reviewed source (normally v2.16, or the identity-only
variant). This audit does not approve unrelated identity/geometry edits; the
outer exact revision gate owns those. No production admission exemptions.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import numpy as np
from pygltflib import GLTF2
from peer_culling_contract import read_visual, summarize
from visual_transport import read_visual_transport
import venue_lighting as vl


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def area(batch):
    t=batch['vertices'][batch['faces']]
    return float(np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1).sum()/2)

def proxy(fixtures, point, revised):
    result=np.zeros(3)
    for fixture in fixtures:
        d=float(np.linalg.norm(np.asarray(fixture['localPosition'])-point));r=fixture['range']*1.25
        attenuation=max(0,1-(d/r)**4)**2/max(d*d,.16)
        color=fixture['color'] if revised else [1,.52,.18]
        mult=fixture['intensityMultiplier'] if revised else 1
        result+=np.asarray(color)*fixture['strength']*1.65*mult*attenuation
    return result


def audit(before, after):
    before=Path(before);after=Path(after);errors=[]
    old=json.loads((before/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    current=json.loads((after/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    profile=vl.load_profile(after/vl.PROFILE_RELATIVE)
    def check(value, label):
        if not value:errors.append(label)
    try:vl.validate_manifest(current,profile)
    except (ValueError,KeyError,TypeError) as e:errors.append('Manifest admission: '+str(e))
    indices={f['manifestIndex'] for s in profile['shops'] for f in s['fixtures']}
    check(len(old['lights'])==len(current['lights'])==374,'374 existing light records must be retained')
    unrelated=[]
    for index,(a,b) in enumerate(zip(old['lights'],current['lights'])):
        if index in indices:
            check(a=={k:v for k,v in b.items() if k!='venueLighting'},'Fixture base layout/range/strength changed: '+str(index))
        else:
            check(a==b,'Unrelated walkway/stage/safety light changed: '+str(index));unrelated.append(b)
    originals={m['name']:m for m in old['materials']};materials={m['name']:m for m in current['materials']}
    for name,spec in originals.items():check(materials.get(name)==spec,'Old material descriptor changed: '+name)
    check([m['name'] for m in current['materials'] if m['name'] in originals]==list(originals),'Original material relative order changed')
    check(sha(before/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes')==sha(after/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes'),'Collision bytes changed')
    for field in ['stations','solidBoxes','floorTests','wallTests','guards','spawns','teleports']:
        check(old[field]==current[field],'Interaction/safety layout changed: '+field)
    # Validate actual packaged native transport instead of trusting stale unpacked convenience files.
    for root in (before,after):
        check(read_visual_transport(root/'Assets/TreeTopYokocho/Data')==(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes(),'Native vs packaged shards differ: '+root.name)
    before_rows=read_visual(before/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
    after_rows=read_visual(after/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
    prior={(b['group'],b['material']):b for b in before_rows};actual={(b['group'],b['material']):b for b in after_rows}
    check(len(actual)==len(after_rows),'Duplicate actual native batch key')
    check(len(before_rows)==len(after_rows),'Native batch count changed (requires separate reviewed identity justification)')
    gltf=GLTF2().load(str(after/'Source/TreeTopYokocho.glb'))
    meshes={m.name:m for m in gltf.meshes};fixture_reports=[]
    for shop in profile['shops']:
        old_emit=0.;new_emit=0.;bindings=[]
        for binding in shop['emitters']:
            previous=(binding['group'],binding['sourceMaterial']);key=(binding['group'],binding['material'])
            check(previous in prior and key in actual,'Missing semantic emitter fixture: '+str(key))
            if previous not in prior or key not in actual:continue
            a=prior[previous];b=actual[key]
            aa=summarize(a);bb=summarize(b);bb['material']=binding['sourceMaterial']
            check(aa==bb,'Emitter geometry/UV/color/index payload changed: '+str(key))
            old_index=next(i for i,row in enumerate(before_rows) if (row['group'],row['material'])==previous)
            new_index=next(i for i,row in enumerate(after_rows) if (row['group'],row['material'])==key)
            check(old_index==new_index,'Emitter batch insertion order changed: '+str(key))
            native_area=area(a);old_spec=originals[binding['sourceMaterial']];new_spec=materials[binding['material']]
            old_emit+=native_area*old_spec['emission']*vl.luminance(old_spec['color'])
            new_emit+=native_area*new_spec['emission']*vl.luminance(new_spec['color'])
            meshname=binding['group']+'__'+binding['material'];mesh=meshes.get(meshname)
            check(mesh is not None and len(mesh.primitives)==1,'Missing actual GLB emitter mesh: '+meshname)
            if mesh and len(mesh.primitives)==1:
                material=gltf.materials[mesh.primitives[0].material]
                check(material.name==binding['material'],'GLB emitter wrong material route: '+meshname)
                check(np.allclose(material.emissiveFactor,np.asarray(binding['color'])*binding['emission'],rtol=0,atol=1e-7),'GLB bounded emission differs from source: '+meshname)
                check(max(material.emissiveFactor)<=1,'GLB emitter factor clipping risk: '+meshname)
            bindings.append(dict(group=binding['group'],sourceMaterial=binding['sourceMaterial'],material=binding['material'],geometryAndAttributesSha256=aa['attributesAndIndicesSha256'],areaSquareMetres=native_area,emission=binding['emission'],color=binding['color']))
        # This is a mesh-area*RGB/emission proxy, not measured emitted flux or bake brightness.
        ratio=new_emit/max(old_emit,1e-8)
        check(ratio<=1.8,'Emissive fixture area-weighted source proxy exceeds1.8 baseline: '+shop['id'])
        old_shop=next(s for s in old['shopPersonality']['shops'] if s['id']==shop['id'])
        face_ratios=[];source_channels=[]
        for seat in old_shop['local']['stations']:
            sample=np.asarray(seat['position'])+[0,0,.67]
            a=proxy(shop['fixtures'],sample,False);b=proxy(shop['fixtures'],sample,True)
            ratio_face=vl.luminance(b)/max(vl.luminance(a),1e-8);face_ratios.append(ratio_face)
            source_channels.append(float(min(b)/max(max(b),1e-8)))
        check(min(face_ratios)>=.5 and max(face_ratios)<=1.8,'Seat source proxy outside bounded reference band: '+shop['id'])
        fixture_reports.append(dict(id=shop['id'],theme=shop['theme'],fixtures=[dict(id=f['id'],role=f['role'],worldPosition=f['worldPosition'],range=f['range'],sourceStrength=f['strength'],unityIntensityBefore=f['strength']*1.65,unityIntensityAfter=f['strength']*1.65*f['intensityMultiplier'],previewEnergyAfter=f['strength']*110*f['intensityMultiplier'],color=f['color']) for f in shop['fixtures']],emitterBindings=bindings,emissiveAreaWeightedProxyRatio=ratio,seatedFaceSourceProxyRatioRange=[min(face_ratios),max(face_ratios)],minimumSeatedFaceRgbRatio=min(source_channels)))
    return dict(schema=1,passed=not errors,errors=errors,sourceVersion=current['version'],profileSha256=profile['_sourceSha256'],beforeManifestSha256=sha(before/'Assets/TreeTopYokocho/Data/WorldManifest.json'),afterManifestSha256=sha(after/'Assets/TreeTopYokocho/Data/WorldManifest.json'),actualGlbSha256=sha(after/'Source/TreeTopYokocho.glb'),fixtureCount=15,unchangedUnrelatedLightCount=len(unrelated),unchangedUnrelatedLightSha256=digest(unrelated),unchangedFixtureLayout=True if not any('layout/range/strength' in e for e in errors) else False,oldMaterialDescriptorsPreserved=len(originals),nativeBatchCount=len(after_rows),cloneCount=12,shops=fixture_reports,limitations=['Unity C#/shader compilation, light bake, runtime FPS and headset glare remain untested.','RGB-weighted source budgets and softened inverse-square/range point proxies are not illuminance, CRI, bake output or perceptual exposure certification.','Cycles preview uses live point-light energy strength*110*multiplier, camera-only emissive surfaces and its own BRDF/AgX; Unity uses Baked point intensity strength*1.65*multiplier, range*1.25 and emissive bake/probes.','S04 has one pearl-lavender point and a low plum emissive shade, not an additional neutral fill; S06 legacy rear accent point has no separately authored visible diffuser.','Shared diffuser batches use the arithmetic mean of their explicitly listed fixture palettes; no coordinate-based assignment or geometry split.'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args()
    result=audit(args.before,args.after);args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'errors':result['errors'],'fixtures':result['fixtureCount'],'unrelatedLights':result['unchangedUnrelatedLightCount']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
