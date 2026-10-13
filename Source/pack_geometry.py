"""Prepare <=4 MiB contiguous Git-friendly gzip shards from generated data."""
from pathlib import Path
import hashlib, json, gzip

root=Path(__file__).resolve().parent.parent
path=root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes.gz'
data=path.read_bytes();chunk_size=4*1024*1024
for old in path.parent.glob(path.name+'.part[0-9][0-9][0-9]'):
    old.unlink()
records=[]
for i,start in enumerate(range(0,len(data),chunk_size)):
    part=path.with_name(path.name+f'.part{i:03}');payload=data[start:start+chunk_size];part.write_bytes(payload)
    records.append({'name':part.name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
joined=b''.join((path.parent/x['name']).read_bytes() for x in records)
assert joined==data
raw=gzip.decompress(joined)
assert raw==(path.parent/'VisualMeshes.bytes').read_bytes()
report={'source':'JYWM v1, gzip','sha256':hashlib.sha256(data).hexdigest(),'uncompressed_bytes':len(raw),'shards':records}
(path.parent/'GeometryShards.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'compressed_bytes':len(data),'uncompressed_bytes':len(raw),'shards':len(records)}))
