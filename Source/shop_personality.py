"""Explicit eight-venue dispatcher; source-local authoring, not runtime code."""
from pathlib import Path
import copy,hashlib,importlib,math,json,pickle
import numpy as np

MODULES=('food_venues','nightlife_venues')
OWNERS={0:'food_venues',1:'food_venues',2:'food_venues',3:'nightlife_venues',4:'food_venues',5:'nightlife_venues',6:'nightlife_venues',7:'food_venues'}
COUNTS=(6,6,5,6,8,6,6,6)
VENUE_TYPES=('charcoal_grill','ramen','oden','retro_snack','tea_salon','cocktail_whisky_bar','music_listening_bar','confectioner')

def validate_feature(features):
    if 'shop_personality' in features and type(features['shop_personality']) is not bool:
        raise ValueError('shop_personality must be a literal Boolean')

def retain_legacy_materials(g,names=None):
    path=Path(__file__).with_name('shop_personality_legacy_materials.json')
    if hashlib.sha256(path.read_bytes()).hexdigest()!='2cc0fb1f349f9196934b38a6914502a553634c89308224bdd1579137f35e327c':raise ValueError('Legacy material descriptor fixture changed')
    for descriptor in json.loads(path.read_text()):
        name=descriptor['name']
        if names is not None and name not in names:continue
        if name in g.materials:
            if g.materials[name]!=descriptor:raise ValueError('Existing material changed: '+name)
        else:g.material(**descriptor)

def batch_fingerprints(g):
    # In-process mutation sentinel, not a portable release oracle. Pickle handles
    # heterogeneous authored_tints and ndarray dtype/shape/value, without object
    # pointer hashing. No pickle is loaded or accepted from external input.
    return {key:hashlib.sha256(pickle.dumps(batch,protocol=4)).hexdigest()
            for key,batch in g.batches.items()}


def vector(v,label):
    if not isinstance(v,(list,tuple,np.ndarray)) or len(v)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float,np.number)) or not math.isfinite(float(x)) for x in v):
        raise ValueError('Invalid finite three-vector: '+label)
    return [float(x) for x in v]

def register_materials(g,M,texture_dir,font=None,*,rpg_identity=False):
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    # Food service props reuse these two exact pre-existing craft materials.
    # Other legacy descriptors are restored only after unrelated authoring so
    # its material-creation counters remain unchanged.
    retain_legacy_materials(g,('CraftSurfaces','CraftEmbers'))
    reports={}
    for name in MODULES:
        module=importlib.import_module(name)
        reports[name]=module.bake_textures(texture_dir,font if font is not None and Path(font).exists() else None,rpg_identity=rpg_identity)
        for spec in module.material_specs():
            spec=copy.deepcopy(spec);key=spec.pop('key');material=spec.pop('name')
            if key in M or material in g.materials:raise ValueError('Venue material must not replace existing identity: '+material)
            prefix='Food_' if name=='food_venues' else 'Night_'
            if not material.startswith(prefix):raise ValueError('Unowned venue material name: '+material)
            for field in ('texture','normal','arm','height'):
                if spec.get(field) and not (Path(texture_dir)/spec[field]).is_file():raise ValueError('Missing venue texture: '+spec[field])
            M[key]=g.material(material,**spec)
    return reports

def default_seats(idx,w,dep):
    count=COUNTS[idx];spread=min(w-1.5,(count-1)*.70)
    return [dict(id=f'S{idx+1:02d}_Seat_{j+1}',position=[-spread/2+spread*j/(count-1),dep/2+.65,.70],exit=[-spread/2+spread*j/(count-1),dep/2+1.35,.06],forward=[0,-1,0]) for j in range(count)]

def legacy_station_references(layout):
    """Preserve infrastructure pole keepouts independently of revised interiors."""
    records=[]
    for idx,shop in enumerate(layout['shops']):
        a=math.radians(shop['front_deg']);front=np.array([math.cos(a),math.sin(a),0]);right=np.array([front[1],-front[0],0]);base=np.array([shop['x'],shop['y'],shop['z']])
        for seat in default_seats(idx,shop['width'],shop['depth']):
            x,y,z=seat['position'];pos=base+right*x+front*y+np.array([0,0,1])*0
            records.append(dict(name=seat['id'],position=(pos+[0,0,.70]).tolist(),exit=(pos+front*.70+[0,0,.06]).tolist(),forward=(-front).tolist(),shop=shop['id']))
    return records

def consume_legacy_shop_rng(rng):
    # Exact former high_detail.shop_details scalar/vector call sequence.
    # The original outer herb planter is retained separately and consumes its
    # ten scalar draws. New modules must use private RNGs exclusively.
    for _ in range(12):
        rng.uniform(-.035,.035,2);rng.uniform(-.03,.04)

def build_shop(g,P,B,shop,idx,M,lantern,stations,solidBoxes,lights,steam,*,lighting_profile=None,rpg_identity=False,pendant_refinement=False):
    if type(rpg_identity) is not bool:raise ValueError("rpg_identity must be a literal Boolean")
    if type(pendant_refinement) is not bool:raise ValueError("pendant_refinement must be a literal Boolean")
    name=OWNERS[idx];module=importlib.import_module(name);sid=shop['id'];w=shop['width'];dep=shop['depth']
    before_keys=set(g.batches);old_group=g.group
    before_batches=batch_fingerprints(g);before_materials=copy.deepcopy(g.materials);before_mapping=copy.deepcopy(M)
    def visual_lantern(pos,redpaper=False,scale=1,record=False):
        # Modules author visible fixtures only. Every light is returned and owned.
        return lantern(pos,redpaper,scale,record=False)
    venue_options=dict(seat_specs=default_seats(idx,w,dep),lantern=visual_lantern,rpg_identity=rpg_identity)
    if pendant_refinement and name=='food_venues':venue_options['pendant_refinement']=True
    result=module.build_venue(g,P,B,w,dep,idx,M,**venue_options)
    after_batches=batch_fingerprints(g)
    if any(after_batches.get(k)!=v for k,v in before_batches.items()):raise ValueError('Venue mutated a pre-existing batch: '+sid)
    if g.materials!=before_materials or M!=before_mapping:
        changed=sorted(k for k in set(g.materials)|set(before_materials) if g.materials.get(k)!=before_materials.get(k))
        raise ValueError('Venue mutated material definitions/mapping: '+sid+' '+repr(changed))
    if g.group!=old_group:raise ValueError('Venue did not restore authoring group: '+sid)
    if result.get('shop')!=sid or result.get('completeVisualReplacement') is not True:raise ValueError('Venue must explicitly replace its assigned visual branch: '+sid)
    created=set(g.batches)-before_keys
    if any(not k[0].startswith('Shops/'+sid+'/Personality/') for k in created):raise ValueError('Venue wrote outside assigned new subgroup: '+sid)
    if lighting_profile is not None:
        from venue_lighting import apply_shop
        result=apply_shop(g,sid,result,lighting_profile,created)
    seats=copy.deepcopy(result.get('seatOverrides',default_seats(idx,w,dep)))
    expected={x['id'] for x in default_seats(idx,w,dep)}
    if len(seats)!=COUNTS[idx] or {x.get('id') for x in seats}!=expected:raise ValueError('Venue station IDs/count changed: '+sid)
    for seat in seats:
        pos=vector(seat['position'],'seat');leave=vector(seat['exit'],'exit');forward=vector(seat['forward'],'forward')
        if abs(forward[2])>1e-7 or np.linalg.norm(forward)<1e-7:raise ValueError('Station forward must be horizontal and nonzero')
        direction=np.asarray(P(*forward))-np.asarray(P(0,0,0));direction/=np.linalg.norm(direction)
        stations.append(dict(name=seat['id'],position=list(P(*pos)),exit=list(P(*leave)),forward=direction.tolist(),shop=sid))
    solid_names=[]
    for solid in result.get('solids',[]):
        local_name=solid['name'];unique=sid+'_Personality_'+local_name
        if not isinstance(local_name,str) or not local_name or unique in solid_names:raise ValueError('Duplicate/invalid venue solid name')
        center=vector(solid['center'],'solid center');size=vector(solid['size'],'solid size');yaw=float(solid.get('yaw',0))
        if min(size)<=0 or not math.isfinite(yaw):raise ValueError('Invalid solid size/yaw')
        a=math.radians(yaw);origin=np.asarray(P(0,0,0))
        basis=[np.asarray(P(math.cos(a),math.sin(a),0))-origin,np.asarray(P(-math.sin(a),math.cos(a),0))-origin,np.asarray(P(0,0,1))-origin]
        solidBoxes.append(dict(name=unique,center=list(P(*center)),size=size,axes=np.asarray(basis).reshape(-1).tolist()));solid_names.append(unique)
    light_indices=[]
    for spec in result.get('lights',[]):
        if 'color' in spec:raise ValueError('Per-venue light color requires separately reviewed runtime support')
        strength=float(spec['strength']);radius=float(spec['range'])
        if not(0<radius<=12 and 0<=strength<=3):raise ValueError('Unreviewed venue light budget')
        record=dict(position=list(P(*vector(spec['position'],'light'))),range=radius,strength=strength)
        if lighting_profile is not None:record['venueLighting']=copy.deepcopy(spec['venueLighting'])
        light_indices.append(len(lights));lights.append(record)
    steam_ids=[]
    for index,spec in enumerate(result.get('steam',[])):
        if name!='food_venues':raise ValueError('Nightlife does not add cooking steam')
        pos=spec.get('position') if isinstance(spec,dict) else spec
        identifier=sid if index==0 else sid+'_Steam_'+str(index+1)
        steam.append(dict(position=list(P(*vector(pos,'steam'))),id=identifier));steam_ids.append(identifier)
    for route in result.get('routes',[]):
        if not isinstance(route.get('name'),str) or len(route.get('points',[]))<2:raise ValueError('Invalid venue route')
        for point in route['points']:vector(point,'route point')
    base=np.asarray(P(0,0,0));right=np.asarray(P(1,0,0))-base;front=np.asarray(P(0,1,0))-base
    return dict(id=sid,displayName=(result.get('displayName',result.get('name',shop.get('name',sid))) if rpg_identity else result.get('name',shop.get('name',sid))),venueType=VENUE_TYPES[idx],theme=result['theme'],module=name,sourceSha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
        frame=dict(origin=base.tolist(),right=right.tolist(),front=front.tolist(),up=[0,0,1],floorZ=float(base[2])),
        local=dict(stations=seats,solids=copy.deepcopy(result.get('solids',[])),routes=copy.deepcopy(result.get('routes',[])),lights=copy.deepcopy(result.get('lights',[])),steam=copy.deepcopy(result.get('steam',[]))),
        ownership=dict(stationNames=sorted(expected),solidNames=solid_names,lightIndices=light_indices,steamIds=steam_ids),design=result.get('design',{}))

def finalize(records,stations,solidBoxes,lights,steam,altitude):
    output=copy.deepcopy(records)
    for shop in output:
        frame=shop['frame'];raw_origin=copy.deepcopy(frame['origin']);frame['origin'][2]=altitude(frame['origin'][2]);frame['floorZ']=frame['origin'][2]
        own=shop['ownership'];routes=[]
        for row in shop['local']['routes']:
            row=copy.deepcopy(row)
            def world_point(value):
                x,y,z=vector(value,'route coordinate')
                p=np.asarray(raw_origin)+np.asarray(frame['right'])*x+np.asarray(frame['front'])*y+[0,0,z]
                p[2]=altitude(p[2]);return p.tolist()
            row['points']=[world_point(value) for value in row['points']]
            # Local authoring shorthand is not a second world-space path.
            row.pop('centerline',None)
            if 'servicePoint' in row:row['servicePoint']=world_point(row['servicePoint'])
            routes.append(row)
        shop['world']=dict(stations=[copy.deepcopy(s) for s in stations if s['name'] in own['stationNames']],solidBoxes=[copy.deepcopy(s) for s in solidBoxes if s['name'] in own['solidNames']],routes=routes,lights=[copy.deepcopy(lights[i]) for i in own['lightIndices']],lightIndices=own['lightIndices'],steam=[copy.deepcopy(s) for s in steam if s['id'] in own['steamIds']])
    return dict(schema=1,version='2.16.0',baselineVersion='2.15.0',shops=output)
