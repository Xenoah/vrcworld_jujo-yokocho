"""Authenticate current shop-access evidence before publishing source summaries."""
import hashlib,json
from pathlib import Path

def checked_shop_access_counts(root, report):
    root=Path(root); data=root/'Assets/TreeTopYokocho/Data'
    expected={name:hashlib.sha256((data/name).read_bytes()).hexdigest() for name in ('WorldManifest.json','VisualMeshes.bytes','CollisionMeshes.bytes')}
    if report.get('status')!='PASS' or report.get('inputSha256')!=expected:
        raise ValueError('Access report is not a PASS for the exact current inputs')
    manifest=json.loads((data/'WorldManifest.json').read_text())
    station_names={x['name'] for x in manifest['stations']}
    probes=report.get('probes');diagnostics=report.get('diagnostics');connections=report.get('connection')
    if not all(isinstance(x,list) for x in (probes,diagnostics,connections)):
        raise ValueError('Malformed access result collections')
    if len(probes)!=208 or any(p.get('passed') is not True for p in probes) or len({p.get('name') for p in probes})!=208:
        raise ValueError('Expected 208 unique passing required probes')
    if len(connections)!=8 or {x.get('shop') for x in connections}!={f'S{i:02}' for i in range(1,9)}:
        raise ValueError('Expected eight unique shop connections')
    seats=[]
    for row in connections:
        if row.get('disconnectedSeats')!=[]:raise ValueError('Disconnected seat in access report')
        entrance=set(row.get('entranceComponents',[]))
        mapping=row.get('seatExitComponents')
        if not isinstance(mapping,dict):raise ValueError('Malformed exit components')
        expected_names={name for name in station_names if name.startswith(row['shop']+'_Seat_')}
        if set(mapping)!=expected_names:raise ValueError('Exit IDs differ from actual shop station roster')
        for name,components in mapping.items():
            if not entrance.intersection(components):raise ValueError('Seat exit has no entrance component')
            seats.append(name)
    if len(seats)!=49 or len(set(seats))!=49 or report.get('actualStationCount')!=49:
        raise ValueError('Expected 49 unique connected station exits')
    if len(diagnostics)!=70 or any(type(x.get('passed')) is not bool for x in diagnostics):
        raise ValueError('Malformed optional diagnostics')
    return dict(requiredProbes=len(probes),connectedExits=len(seats),largerGuestContacts=sum(not x['passed'] for x in diagnostics),largerGuestDiagnostics=len(diagnostics))
