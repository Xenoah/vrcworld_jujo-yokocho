"""Verify the exported deck triangles, rather than only the authoring helper.

The continuous bed is visual only. Existing floor colliders remain authoritative.
Source XY footprint and raised Z heights are checked after float32 encoding.
"""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon
from shapely.ops import unary_union
from validate_crown import read_collision

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
data=root/'Assets/TreeTopYokocho/Data';started=time.time()
m=json.loads((data/'WorldManifest.json').read_text())
batches=read_collision(data/'VisualMeshes.bytes')
checks=[];failures=[];floors=[]
def check(name,ok,detail=None):
    result={'name':name,'passed':bool(ok)}
    if detail is not None:result['detail']=detail
    checks.append(result)
    if not ok:failures.append(result)

for spec in m['floors']:
    name=spec['level'];z=spec['z'];poly=wkt.loads(spec['wkt'])
    prefix='Decks/'+name
    selected=[b for b in batches if b['group'] in (prefix+'/Planks',prefix+'/JointBed')]
    check(name+'_crafted_meshes_present',len(selected)>=3)
    if not selected:continue
    vertices=np.concatenate([b['vertices'] for b in selected])
    check(name+'_unchanged_top_and_bottom',abs(vertices[:,2].max()-z)<2e-5
          and abs(vertices[:,2].min()-(z-.30))<2e-5)
    bed=np.concatenate([b['triangles'] for b in selected if b['group'].endswith('/JointBed')])
    bed=bed[np.max(np.abs(bed[:,:,2]-(z-.0038)),axis=1)<2e-5]
    bed_normals=np.cross(bed[:,1]-bed[:,0],bed[:,2]-bed[:,0])
    check(name+'_exported_bed_top_winding_and_area',len(bed)>0 and np.all(bed_normals[:,2]>1e-12))
    bed2d=unary_union([Polygon(t[:,:2]) for t in bed])
    # Float32 storage moves the perimeter by a few micrometres. Test its full
    # coverage and confinement with a 30 um geometric tolerance, not pixel rays.
    missing=poly.difference(bed2d.buffer(3e-5)).area
    escaped=bed2d.difference(poly.buffer(3e-5)).area
    check(name+'_continuous_bed_covers_footprint',missing<1e-7,{'missingSquareMetres':missing})
    check(name+'_bed_respects_edges_and_holes',escaped<1e-7,{'escapedSquareMetres':escaped})
    plank=np.concatenate([b['triangles'] for b in selected if b['group'].endswith('/Planks')])
    normals=np.cross(plank[:,1]-plank[:,0],plank[:,2]-plank[:,0])
    check(name+'_upward_valid_plank_faces',np.all(normals[:,2]>1e-12))
    check(name+'_shallow_recess_only',plank[:,:,2].min()>=z-.0038-2e-5
          and plank[:,:,2].max()<=z+2e-5)
    projected=unary_union([Polygon(t[:,:2]) for t in plank])
    escaped=projected.difference(poly.buffer(3e-5)).area
    overlap=sum(Polygon(t[:,:2]).area for t in plank)-projected.area
    check(name+'_planks_confined_to_footprint',escaped<1e-7)
    check(name+'_no_layered_duplicate_surfaces',overlap<max(1e-6,poly.area*1e-8),{'overlapSquareMetres':overlap})
    check(name+'_old_seam_batches_replaced',not any(b['group']==prefix and b['material'] in ('Cedar','Grout') for b in batches))
    floors.append({'level':name,'visualTriangles':sum(len(b['faces']) for b in selected),
                   'footprintArea':poly.area,'minimumZ':float(vertices[:,2].min()),
                   'maximumZ':float(vertices[:,2].max()),'bedTriangles':len(bed)})

base=json.loads((root/'Docs/baselines/verified_layout_2.6.0.json').read_text())
check('deck_changes_preserve_collision_payload',hashlib.sha256((data/'CollisionMeshes.bytes').read_bytes()).hexdigest()==base['collisionSha256'])
image_fields=('texture','normal','arm','height')
cedar=next(x for x in m['materials'] if x['name']=='Cedar')
shared_images={cedar.get(channel) for channel in image_fields if cedar.get(channel)}
check('shared_existing_scan_images',all(not x.get(channel) or x[channel] in shared_images
      for x in m['materials'] if x['name'].startswith('Deck') for channel in image_fields))
report={'version':m['version'],'status':'PASS' if not failures else 'FAIL','checks':checks,
        'failures':failures,'floors':floors,'seconds':round(time.time()-started,2),
        'scope':'Exported float32 visual decks and unchanged floor collision payload; 30 micrometre perimeter tolerance. Not Unity/VRChat execution.'}
(root/'Docs/deck_surface_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));raise SystemExit(bool(failures))
