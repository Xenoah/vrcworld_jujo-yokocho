"""Self-contained small fixture regression: no full-world build or old module.

The baseline JSON is pinned. The fixture uses today's unchanged noh_stage,
then adds the new module separately, proving that no original payload changed.
"""
from pathlib import Path
import base64, copy, gzip, hashlib, io, json, random, struct, sys
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent.parent
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE
sys.path.insert(0,str(ROOT/'Source'))
# The script's own Source folder keeps the proposal import local during staging.
sys.path.insert(0,str(Path(__file__).resolve().parent))
BASELINE_PATH=HERE/'Docs/baselines/verified_noh_stage_2.10.0.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_fixture():
    from noh_stage import add_noh_stage
    baseline=json.loads(BASELINE_PATH.read_text())
    g=Geometry();g.materials=copy.deepcopy(baseline['fixtureMaterials'])
    M=dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',tile='Kawara')
    rng=np.random.default_rng(12040)
    metadata=add_noh_stage(g,M,rng)
    return g,M,rng,metadata


def fixture_roster(g):
    return [{'group':group,'material':mat,'triangles':len(b['f']),'vertices':len(b['v']),
             'authoring_sha256':digest(np.asarray(b['v'],'<f8').tobytes()
                 +np.asarray(b['f'],'<u4').tobytes()+np.asarray(b['uv'],'<f8').tobytes())}
            for (group,mat),b in g.batches.items()]


def native_proposal(original,new):
    # Actual source serialization convention: +100 m, float32, white Color32.
    result=copy.deepcopy(original)
    for (group,material),b in new.items():
        v=np.asarray(np.asarray(b['v'])+[0,0,100],'<f4')
        uv=np.asarray(b['uv'],'<f4');f=np.asarray(b['f'],'<u4')
        colors=np.full((len(v),4),255,dtype='u1')
        payload=v.tobytes()+uv.tobytes()+colors.tobytes()+f.tobytes()
        result.append(dict(group=group,material=material,v=v,uv=uv,f=f,payload=payload))
    return result


from noh_roof_detail import (add_noh_roof_detail, DETAIL_PREFIX, DETAIL_ROSTER,
                             _profile_tile, _cap_shell, TILE_PITCH)
from world_geometry import Geometry
from validate_crown import Rays

BASELINE_SHA256='b4d38c09be5a227ff20970133f1b1db623daf93727cbad21305151ee9d79187b'
MAX_TRIANGLES=28000
# Existing authored roof bound is 4.265 m. Exactly 6 mm extra at the cap apex.
LOCAL_MIN=np.array([-2.966847,-2.915001,2.757])
LOCAL_MAX=np.array([ 2.966847, 2.915001,4.271001])


def read_native(path):
    meshes=[]
    with (io.BytesIO(path) if isinstance(path,bytes) else path.open('rb')) as stream:
        assert stream.read(4)==b'JYWM'
        version,count=struct.unpack('<II',stream.read(8));assert version==1
        for _ in range(count):
            group,material=[stream.read(struct.unpack('<I',stream.read(4))[0]).decode() for j in range(2)]
            nv,ni=struct.unpack('<II',stream.read(8));payload=stream.read(nv*24+ni*4)
            assert len(payload)==nv*24+ni*4
            v=np.frombuffer(payload[:nv*12],'<f4').reshape(-1,3)
            uv=np.frombuffer(payload[nv*12:nv*20],'<f4').reshape(-1,2)
            f=np.frombuffer(payload[nv*24:],'<u4').reshape(-1,3)
            meshes.append({'group':group,'material':material,'v':v,'uv':uv,'f':f,'payload':payload})
        assert not stream.read(1)
    return meshes


def check_surface(b,label):
    v,f,u=np.asarray(b['v']),np.asarray(b['f']),np.asarray(b['uv'])
    assert np.isfinite(v).all() and np.isfinite(u).all(),label+' finite'
    q=v[f];e=q[:,1]-q[:,0];h=q[:,2]-q[:,0]
    area=np.linalg.norm(np.cross(e,h),axis=1)
    assert (area>1e-10).all(),label+' geometry degeneracy'
    q=u[f];e=q[:,1]-q[:,0];h=q[:,2]-q[:,0]
    uvarea=np.abs(e[:,0]*h[:,1]-e[:,1]*h[:,0])
    assert (uvarea>1e-10).all(),label+' collapsed UV'
    mesh=trimesh.Trimesh(v,f,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,label+' shell closure/winding'
    return {'triangles':len(f),'vertices':len(v),'minimumDoubleArea':float(area.min()),
            'minimumUVDoubleArea':float(uvarea.min()),'watertight':True,'consistentWinding':True}


def mouth_clearance(triangles):
    """Cast short rays into exposed tile mouths, at three cavity heights.

    Samples exclude only the two hip-covered corner tiles on each eave.
    Both the original roof and proposed tile shell are present. The 70 mm
    open depth cannot be faked by an opaque source plane behind the lip.
    """
    rays=Rays(triangles);checks=[]
    for hip in [False,True]:
        rise=1.18;run=1.45 if hip else 2.85;length=np.hypot(run,rise)
        c,s=run/length,rise/length
        offset=0.
        width=2.85 if hip else 2.9
        for side in [-1,1]:
            if hip:
                anchor=np.array([side*1.45,0,4.17]);U=np.array([0,-side,0]);D=np.array([side*c,0,-s]);N=np.array([side*s,0,c])
            else:
                anchor=np.array([0,0,4.17]);U=np.array([side,0,0]);D=np.array([0,side*c,-s]);N=np.array([0,side*s,c])
            for col in range(-12,13):
                u0=col*TILE_PITCH+offset+.0015;u1=(col+1)*TILE_PITCH+offset-.0015
                center=u0+(u1-u0)*.53
                if u0 < -width+.018 or u1 > width-.018:continue
                for h in [.012,.024,.038]:
                    p=anchor+U*center+D*(length+.010)+N*h
                    hit=rays.hit(p,-D,.080)
                    assert hit is None,('Occluded eave mouth',hip,side,col,h,hit)
                checks.append({'hip':hip,'side':side,'column':col,'centerU':center,
                               'testedOpenDepthMetres':.070,'sampleNormalHeights':[.012,.024,.038]})
    return checks



def roof_plane_clearance(g,origin,axes):
    """Test vertices and triangle interiors against the actual old four planes.

    This excludes the protected round cap cores. The new cap ceramic overlaps
    those cores intentionally, and is not presented as a hollow ridge.
    """
    results=[]
    weights=np.array([[a/5,b/5,1-(a+b)/5] for a in range(6) for b in range(6-a)])
    for (group,material),batch in g.batches.items():
        if group not in [DETAIL_PREFIX+'Courses',DETAIL_PREFIX+'Caps']:continue
        local=(np.asarray(batch['v'])-origin)@axes.T
        triangles=local[np.asarray(batch['f'])]
        samples=np.einsum('wv,tvc->twc',weights,triangles).reshape(-1,3)
        inside=(abs(samples[:,0])<=2.9)&(abs(samples[:,1])<=2.85)
        samples=samples[inside]
        roof_z=4.17-np.maximum(abs(samples[:,1])*1.18/2.85,
                              np.maximum(abs(samples[:,0])-1.45,0)*1.18/1.45)
        clearance=samples[:,2]-roof_z
        assert clearance.min()>0,group+' crosses an original opaque roof plane'
        results.append(dict(group=group,samples=len(samples),
                            minimumVerticalClearanceMetres=float(clearance.min())))
    return results


def joint_visibility(original_local_triangles):
    """All sixteen pins sit on exposed beam faces, outside the old brackets."""
    rays=Rays(original_local_triangles);samples=0;distances=[]
    for sx in [-1,1]:
        for sy in [-1,1]:
            x,y=sx*1.84,sy*1.84
            for shift in [-.040,.040]:
                for face in [0,1]:
                    if face==0:
                        p=np.array([x-sx*.40+shift,y+sy*.157,2.825]);out=np.array([0,sy,0])
                    else:
                        p=np.array([x+sx*.157,y-sy*.40+shift,2.825]);out=np.array([sx,0,0])
                    assert rays.hit(p+out*.0005,out,.35) is None,'Pin obscured by a protected bracket'
                    hit=rays.hit(p,-out,.065)
                    assert hit is not None and .0518<hit<.0522,'Pin not aligned with the protected beam face'
                    samples+=1;distances.append(float(hit))
    return dict(exposedPins=samples,minimumOldBeamDistance=min(distances),maximumOldBeamDistance=max(distances))


def run():
    baseline_path=BASELINE_PATH
    assert digest(baseline_path.read_bytes())==BASELINE_SHA256,'Pinned baseline changed'
    base=json.loads(baseline_path.read_text())
    g,M,rng,stage=source_fixture()
    assert fixture_roster(g)==base['sourceRoster'],'Original source stage drifted'
    assert stage==base['sourceStageMetadata'],'Original stage metadata drifted'
    old=copy.deepcopy(g.batches);materials=copy.deepcopy(g.materials);old_spec=copy.deepcopy(stage)
    global_random=random.getstate();numpy_random=np.random.get_state();state=copy.deepcopy(rng.bit_generator.state)
    g.group='Preserve/Caller'
    result=add_noh_roof_detail(g,M,rng)
    assert g.group=='Preserve/Caller' and stage==old_spec
    assert rng.bit_generator.state==state and random.getstate()==global_random
    after_random=np.random.get_state()
    assert numpy_random[0]==after_random[0] and np.array_equal(numpy_random[1],after_random[1]) and numpy_random[2:]==after_random[2:]
    assert g.materials==materials,'Material definitions changed'
    for key in old:assert old[key]==g.batches[key],str(key)+' original authoring payload changed'
    new={key:b for key,b in g.batches.items() if key not in old}
    assert set(new)==set(DETAIL_ROSTER) and len(new)==4
    assert sum(len(b['f']) for b in new.values())<=MAX_TRIANGLES
    origin=np.array(stage['center']);axes=np.array([stage['right'],stage['front'],[0,0,1]])
    local=np.concatenate([(np.asarray(b['v'])-origin)@axes.T for b in new.values()])
    assert (local.min(0)>=LOCAL_MIN-1e-8).all() and (local.max(0)<=LOCAL_MAX+1e-8).all(),local.max(0)
    assert (local[:,2]>=2.757).all(),'New geometry below the reviewed roof-detail minimum'
    old_roof=np.concatenate([(np.asarray(b['v'])-origin)@axes.T for key,b in old.items() if key[0]=='Stage/Noh/HipRoof'])
    assert (local.min(0)[:2]>=old_roof.min(0)[:2]-1e-9).all()
    assert (local.max(0)[:2]<=old_roof.max(0)[:2]+1e-9).all()
    frozen_top=base['sourceStageMetadata']['visualBounds']['max'][2]-base['sourceStageMetadata']['z']
    assert local[:,2].max()<=frozen_top+.0061, 'Ridge apex exceeds the exact 6.1 mm roof-only allowance'
    # Restore-the-group and reject duplicate execution without partial changes.
    after=fixture_roster(g)
    try:add_noh_roof_detail(g,M,rng)
    except ValueError:pass
    else:raise AssertionError('Duplicate pass was allowed')
    assert fixture_roster(g)==after and g.group=='Preserve/Caller'
    repeat,MM,rr,ss=source_fixture();add_noh_roof_detail(repeat,MM,rr)
    assert fixture_roster(repeat)==after,'Non-deterministic geometry'
    rows=[]
    for key,b in new.items():
        check=check_surface(b,str(key));check.update(group=key[0],material=key[1]);rows.append(check)
    # Native float32 source at final altitude is separately tested for collapse.
    frozen_native=gzip.decompress(base64.b64decode(base['nativeFixtureGzipBase64']))
    native=read_native(frozen_native);proposal=native_proposal(native,new)
    assert len(native)==15 and len(proposal)==19
    assert digest(frozen_native)==base['nativeStageSha256']
    assert [(b['group'],b['material'],digest(b['payload'])) for b in native]==[(b['group'],b['material'],digest(b['payload'])) for b in proposal[:15]],'Protected native payload changed'
    for b in proposal[15:]:check_surface(b,b['group']+' final-altitude float32')
    # Run the module itself against the frozen 15-batch payload, including
    # original lighting, rather than relying only on an assembly copy.
    native_g=Geometry();native_g.materials=copy.deepcopy(materials)
    for b in native:
        native_g.batches[(b['group'],b['material'])]={k:np.array(b[k],copy=True) for k in ('v','uv','f')}
    before_native=fixture_roster(native_g)
    add_noh_roof_detail(native_g,M)
    assert fixture_roster(native_g)[:15]==before_native,'Actual native originals mutated by the module'
    scene_center=np.array([*stage['center'][:2],140.])
    tris=np.concatenate([((b['v']-scene_center)@axes.T)[b['f']] for b in proposal])
    mouths=mouth_clearance(tris)
    original_local_triangles=np.concatenate([((b['v']-scene_center)@axes.T)[b['f']] for b in native])
    joints=joint_visibility(original_local_triangles)
    roof_clearance=roof_plane_clearance(g,origin,axes)
    # The original 12 batches include every existing vertex/face at <=2.60m,
    # and the native comparisons also cover all three lighting batches.
    output={'status':'PASS','sourceOriginalBatchesExact':12,'nativeOriginalBatchesExact':15,
            'lowHeightPayload':'All original native bytes unchanged; all added vertices strictly above 2.60 m',
            'originalStageMetadataExact':True,'randomStatesUnchanged':['passed generator','Python global','NumPy global'],
            'newMaterialDefinitions':0,'newTextures':0,'deterministic':True,
            'addedTriangles':result['addedTriangles'],'addedBatches':4,
            'localBounds':[local.min(0).tolist(),local.max(0).tolist()],
            'roofOnlyVerticalMeasuredIncreaseMetres':float(local[:,2].max()-frozen_top),
            'roofOnlyVerticalAllowanceMetres':.0061,'horizontalAllowanceMetres':0,
            'minimumReviewedHeightMetres':2.757,
            'exposedMouthsTested':len(mouths),'mouthRays':len(mouths)*3,
            'mouthSampleRecords':mouths,'surfaceChecks':rows,
            'roofPlaneClearance':roof_clearance,'jointVisibility':joints,
            'scope':'Isolated current stage + proposal geometry/UV/native regression. Unity/runtime/VR not executed.'}
    return output

if __name__=='__main__':
    report=run();(HERE/'Docs/noh_roof_detail_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='mouthSampleRecords'},indent=2))
