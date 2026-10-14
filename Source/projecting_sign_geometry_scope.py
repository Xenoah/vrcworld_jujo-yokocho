"""Actual added-triangle component coverage, envelopes and oblique diagnostics."""
import numpy as np
import projecting_sign_contract as c
TOLERANCE=3e-5 # Diagnostic float32 tolerance only; production admission is exact.
ENVELOPES={'S01': {'sign': [[-3.2, 2.55, 2.3], [-2.96, 3.37, 2.85]]},
 'S02': {'pennant': [[-2.43, 2.68, 2.3], [-2.0, 3.39, 2.76]], 'sign': [[-3.2, 2.56, 2.3], [-2.96, 3.38, 2.67]]},
 'S03': {'sign': [[-2.62, 2.55, 2.3], [-2.36, 3.37, 2.83]]},
 'S04': {'pennant': [[-2.6, 2.68, 2.3], [-2.2, 3.3, 2.76]], 'sign': [[-3.2, 2.56, 2.3], [-2.96, 3.38, 2.81]]},
 'S05': {'sign': [[-3.79, 2.86, 2.3], [-3.56, 3.72, 2.81]]},
 'S06': {'sign': [[-3.21, 2.56, 2.3], [-2.96, 3.38, 2.83]]},
 'S07': {'sign': [[-3.18, 2.56, 2.3], [-2.96, 3.37, 2.82]]},
 'S08': {'pennant': [[1.97, 2.67, 2.32], [2.41, 3.03, 2.94]], 'sign': [[-3.2, 2.56, 2.3], [-2.96, 3.36, 2.82]]}}
COMPONENTS={'S01': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('DragonEmberShield', 'dimensional_emblem')],
 'S02': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('NoodleGuildBowl', 'dimensional_emblem'),
         ('GuildPennant', 'static_cloth_pennant')],
 'S03': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('TravelerPotLantern', 'dimensional_emblem')],
 'S04': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('WitchMoonHat', 'dimensional_emblem'),
         ('GuildPennant', 'static_cloth_pennant')],
 'S05': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('MoonTeaTimber', 'dimensional_emblem')],
 'S06': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('StarDistilleryBottle', 'dimensional_emblem')],
 'S07': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('BardOpenLyre', 'dimensional_emblem')],
 'S08': [('PostBracket', 'structural_support'),
         ('Suspension', 'suspension_hardware'),
         ('FairyConfectionCrest', 'dimensional_emblem'),
         ('GuildPennant', 'static_cloth_pennant')]}
CLOTH_MATERIALS={'S02':'Noren3','S04':'Night_WineUpholstery','S08':'Noren1'}
VENUE_FIELDS={'version','shop','motif','coordinates','root','localBounds','dimensions','triangleCount','sourceVertexCount','batchCount','keys','parts','static','collisionApplied','addedLights','addedMaterials','testedInUnity','testedInVRChat','consolidation'}
PART_FIELDS={'group','role','localBounds','dimensions','triangles','sourceVertexCount','materials','components'}
COMPONENT_FIELDS={'role','localBounds','dimensions','triangles','sourceVertexCount','semantic','ranges'}
RANGE_FIELDS={'key','vertexStart','vertexCount','triangleStart','triangleCount'}

def recovered_component(component,lookup,origin,axes,coverage):
    """Native triangle order survives UV corner splitting and vertex compaction.

    Source vertex ranges are bookkeeping only, never used to address native
    vertices after remapping. Every declared triangle slice is accounted once.
    """
    errors=[];triangles=[];slices=[];vertices=0
    if set(component)!=COMPONENT_FIELDS:return [],[],[dict(reason='Component fields differ from exact source ledger')]
    for r in component['ranges']:
        if set(r)!=RANGE_FIELDS or any(type(r[f]) is not int or r[f]<0 for f in RANGE_FIELDS-{'key'}):
            errors.append(dict(reason='Invalid literal component range schema'));continue
        k=tuple(r['key']);b=lookup.get(k);start=r['triangleStart'];stop=start+r['triangleCount'];vertices+=r['vertexCount']
        if k not in coverage or b is None or r['triangleCount']<=0 or r['vertexCount']<=0 or stop>len(b['faces']):
            errors.append(dict(reason='Component range escapes enumerated added batch',key=k));continue
        coverage[k][start:stop]+=1;points=(b['vertices']-origin)@axes.T;f=b['faces'][start:stop];triangles.extend(points[f]);slices.append((k,points,f,b['uv']))
    if component['triangles']!=len(triangles) or component['sourceVertexCount']!=vertices:errors.append(dict(reason='Component source/triangle counters differ from exact declared ranges'))
    return np.asarray(triangles),slices,errors

def cloth_diagnostic(points,faces,uv):
    import trimesh
    mesh=trimesh.Trimesh(points,faces,process=True)
    # Union-find avoids optional graph packages and never fills missing faces.
    parent=list(range(len(mesh.faces)));owners={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,f in enumerate(mesh.faces):
        for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):
            edge=tuple(sorted((int(a),int(b))))
            if edge in owners:parent[find(i)]=find(owners[edge])
            else:owners[edge]=i
    components={}
    for i in range(len(mesh.faces)):components.setdefault(find(i),[]).append(i)
    volumes=[]
    for ids in components.values():
        t=mesh.vertices[mesh.faces[ids]];volumes.append(float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6))
    q=points[faces];u=uv[faces];normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);area=np.linalg.norm(normal,axis=1)/2
    e=np.stack([q[:,1]-q[:,0],q[:,2]-q[:,0]],axis=2);du=np.stack([u[:,1]-u[:,0],u[:,2]-u[:,0]],axis=2);density=np.linalg.norm(du@np.linalg.pinv(e),axis=2)
    keep=(density.min(axis=1)>1e-8)&(np.abs(normal[:,1])>np.linalg.norm(normal,axis=1)*.75)&(area>1e-7)
    def median(values,weights):
        order=np.argsort(values);return float(np.interp(.5,np.cumsum(weights[order])/weights.sum(),values[order]))
    medians=[median(density[keep,k],area[keep]) for k in (0,1)] if keep.any() else [0.,0.]
    return dict(closed=bool(mesh.is_watertight),consistentWinding=bool(mesh.is_winding_consistent),allComponentsOutward=bool(volumes) and all(v>0 for v in volumes),closedComponents=len(volumes),volumeM3=float(mesh.volume),sampledBroadFaceTriangles=int(keep.sum()),sampledBroadFaceAreaM2=float(area[keep].sum()),uvRepeatsPerMetreMedians=medians,weave96PeriodMmMedians=[1000/(96*d) if d else None for d in medians])

def audit(batches,m):
    errors=[];lookup={c.key(b):b for b in batches};shopmap={s['id']:s for s in m['shopPersonality']['shops']};evidence=[]
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    for i,v in enumerate(m[c.METADATA]['venues']):
        sid=v['shop'];frame=shopmap[sid]['frame'];axes=np.asarray([frame['right'],frame['front'],frame['up']],float);origin=np.asarray(frame['origin'],float)
        keys=[k for k in c.KEYS if k[0].split('/')[1]==sid];owned=[lookup[k] for k in keys];coverage={k:np.zeros(len(lookup[k]['faces']),np.int16) for k in keys}
        check(set(v)==VENUE_FIELDS and v['version']=='venue-projecting-signs-3' and v['coordinates']=='shop-local Z-up metres' and v['root']=='Shops/'+sid+'/ProjectingSigns','Venue source ledger schema/version changed',shop=sid)
        check(v.get('static') is True and v.get('collisionApplied') is False and v.get('testedInUnity') is False and v.get('testedInVRChat') is False and type(v.get('addedLights')) is int and v['addedLights']==0 and type(v.get('addedMaterials')) is int and v['addedMaterials']==0,'Sign must remain static with no collider/light/material/runtime additions',shop=sid)
        world=np.concatenate([b['vertices'] for b in owned]);local=(world-origin)@axes.T;lo,hi=local.min(0),local.max(0)
        check(np.isfinite(local).all() and lo[2]>2.2,'Actual added vertices enter protected 2.2 m clearance volume or are non-finite',shop=sid)
        check(np.allclose(v['localBounds'],[lo,hi],rtol=0,atol=TOLERANCE) and np.allclose(v['dimensions'],hi-lo,rtol=0,atol=TOLERANCE),'Reported venue dimensions/bounds differ from actual native',shop=sid)
        groups=list(dict.fromkeys(k[0] for k in keys));check(len(v['parts'])==1 and [p['group'] for p in v['parts']]==groups,'Exactly one actual consolidated assembly group required',shop=sid)
        emblem=[];cloth=[];component_evidence=[]
        for part in v['parts']:
            check(set(part)==PART_FIELDS and part['role']==c.PART_ROLES[part['group']],'Assembly source-ledger fields/role changed',shop=sid)
            check(part['materials']==[k[1] for k in keys] and part['triangles']==sum(len(b['faces']) for b in owned) and part['sourceVertexCount']==v['sourceVertexCount'],'Assembly source/material/triangle counters differ',shop=sid)
            check(np.allclose(part['localBounds'],[lo,hi],rtol=0,atol=TOLERANCE) and np.allclose(part['dimensions'],hi-lo,rtol=0,atol=TOLERANCE),'Assembly reported dimensions/bounds differ',shop=sid)
            check([(q['semantic'],q['role']) for q in part['components']]==COMPONENTS[sid],'Exact semantic component inventory changed',shop=sid)
            check(sum(q['sourceVertexCount'] for q in part['components'])==part['sourceVertexCount'],'Semantic component source vertex sum differs from assembly',shop=sid)
            original=sum(len(q['ranges']) for q in part['components'])
            check(v['consolidation']==dict(method='exact_same_material_concatenation',originalBatchCount=original,removedBatchCount=original-len(keys),geometryWelded=False,sourceComponentRanges=True),'Exact consolidation provenance changed',shop=sid)
            source_counts={k:[] for k in keys}
            for component in part['components']:
                t,slices,issues=recovered_component(component,lookup,origin,axes,coverage);errors.extend(issues)
                if not len(t):continue
                p=t.reshape(-1,3);pl,ph=p.min(0),p.max(0);slot=np.asarray(ENVELOPES[sid]['pennant' if component['role']=='static_cloth_pennant' else 'sign'],float)
                check(np.all(pl>=slot[0]-TOLERANCE) and np.all(ph<=slot[1]+TOLERANCE),'Actual semantic component escapes its literal frontage slot',shop=sid,component=component['semantic'])
                check(np.allclose(component['localBounds'],[pl,ph],rtol=0,atol=TOLERANCE) and np.allclose(component['dimensions'],ph-pl,rtol=0,atol=TOLERANCE),'Semantic component reported bounds/dimensions differ from actual triangles',shop=sid,component=component['semantic'])
                for r in component['ranges']:source_counts[tuple(r['key'])].append((r['vertexStart'],r['vertexCount']))
                if component['role']=='dimensional_emblem':emblem.extend(t)
                if component['role']=='static_cloth_pennant':
                    selected=[q for q in slices if q[0][1]==CLOTH_MATERIALS[sid]];check(len(selected)==1,'Exact cloth material range missing or duplicated',shop=sid)
                    if len(selected)==1:
                        k,points,f,uv=selected[0];d=cloth_diagnostic(points,f,uv)
                        check(d['closed'] and d['consistentWinding'] and d['allComponentsOutward'],'Actual cloth shell is not closed and consistently outward',shop=sid)
                        check(all(3.8<x<4.2 for x in d['uvRepeatsPerMetreMedians']),'Actual broad cloth face UV repeats differ from reviewed four-per-metre weave',shop=sid)
                        active_weave=k[1] in ('Noren1','Noren3')
                        if not active_weave:d['weave96PeriodMmMedians']=None
                        cloth.append(dict(material=k[1],triangles=len(f),shaderRoute='Cloth',weaveStrength=.045 if active_weave else 0.,**d,shaderNote='Noren1/Noren3 retain their existing Cloth weave; Night_WineUpholstery retains existing Cloth routing with weave strength zero. No shader/profile change.'))
                component_evidence.append(dict(semantic=component['semantic'],role=component['role'],actualTriangles=len(t),actualLocalBounds=[pl.tolist(),ph.tolist()]))
            for k,ranges in source_counts.items():
                cursor=0
                for start,count in sorted(ranges):check(start==cursor,'Source vertex range ledger has a gap or overlap',key=k);cursor=start+count
        for k,b in zip(keys,owned):
            check(np.all(coverage[k]==1),'Every actual added triangle must be owned by exactly one semantic component',key=k)
            check(len(np.unique(b['faces']))==len(b['vertices']),'Added batch contains hidden unused vertices',key=k)
            check(np.isfinite(b['uv']).all(),'Non-finite added UV',key=k)
        t=np.asarray(emblem);a=t.reshape(-1,3);extent=np.ptp(a,axis=0);check(np.all(extent>=[.02,.15,.15]),'Dimensional emblem must retain real depth and readable dimensions',shop=sid)
        cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])/2;areas=[float(np.maximum(cross@d,0).sum()) for d in (np.asarray([.8660254038,.5,0]),np.asarray([-.8660254038,.5,0]))]
        check(min(areas)>.015,'Emblem has insufficient front-facing projected area from a street-oblique side',shop=sid)
        evidence.append(dict(shop=sid,actualLocalBounds=[lo.tolist(),hi.tolist()],minimumHeightAboveShopFloor=float(lo[2]),actualAddedTriangles=sum(len(b['faces']) for b in owned),oppositeObliqueFrontFacingAreaSquareMetres=areas,components=component_evidence,cloth=cloth))
    return dict(status='FAIL' if errors else 'PASS',errors=errors,venues=evidence,geometryToleranceMetres=TOLERANCE,scope='Actual native component triangles after UV repair/compaction, complete nonoverlapping component coverage, separate literal sign/pennant frontage slots, closed outward cloth topology/UV scale, and opposite street-oblique projected areas. Not rendered occlusion/art approval. Every added triangle remains in separate complete 208-probe access audit. No runtime claim.')
