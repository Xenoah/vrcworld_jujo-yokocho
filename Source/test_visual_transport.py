"""Portable shard-only transport tests; never regenerate a missing gzip file."""
import copy,gzip,hashlib,json,sys,tempfile
from pathlib import Path
from visual_transport import read_visual_transport
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
n=0
def sha(b):return hashlib.sha256(b).hexdigest()
def expect_error(path):
    global n
    try:read_visual_transport(path)
    except ValueError:n+=1
    else:raise AssertionError('Invalid transport admitted')
raw=b'JYWM'+bytes(range(256))*20;compressed=gzip.compress(raw,mtime=0);cut=len(compressed)//3;parts=[compressed[:cut],compressed[cut:2*cut],compressed[2*cut:]]
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);desc=dict(source='JYWM v1, gzip',sha256=sha(compressed),uncompressed_bytes=len(raw),shards=[dict(name=f'VisualMeshes.bytes.gz.part{i:03}',bytes=len(b),sha256=sha(b)) for i,b in enumerate(parts)])
    def reset():
        for p in d.iterdir():p.unlink()
        for r,b in zip(desc['shards'],parts):(d/r['name']).write_bytes(b)
        (d/'GeometryShards.json').write_text(json.dumps(desc))
    reset();assert read_visual_transport(d)==raw;assert not(d/'VisualMeshes.bytes.gz').exists();n+=1
    (d/'VisualMeshes.bytes.gz').write_bytes(compressed);assert read_visual_transport(d)==raw;n+=1
    (d/'VisualMeshes.bytes.gz').write_bytes(compressed+b'bad');expect_error(d)
    for mode in ['missing','corrupt','truncate','swap_files','reorder_descriptor','duplicate_descriptor','wrong_size','wrong_shard_hash','wrong_combined_hash','wrong_raw_length','traversal','bool_size','invalid_descriptor','invalid_gzip']:
        reset();m=copy.deepcopy(desc)
        if mode=='missing':(d/m['shards'][1]['name']).unlink();(d/'VisualMeshes.bytes.gz').write_bytes(compressed)
        elif mode=='corrupt':(d/m['shards'][1]['name']).write_bytes(bytes([parts[1][0]^1])+parts[1][1:])
        elif mode=='truncate':(d/m['shards'][1]['name']).write_bytes(parts[1][:-1])
        elif mode=='swap_files':
            (d/m['shards'][0]['name']).write_bytes(parts[1]);(d/m['shards'][1]['name']).write_bytes(parts[0])
        elif mode=='reorder_descriptor':m['shards'][0],m['shards'][1]=m['shards'][1],m['shards'][0]
        elif mode=='duplicate_descriptor':m['shards'][1]=m['shards'][0]
        elif mode=='wrong_size':m['shards'][0]['bytes']+=1
        elif mode=='wrong_shard_hash':m['shards'][0]['sha256']='0'*64
        elif mode=='wrong_combined_hash':m['sha256']='0'*64
        elif mode=='wrong_raw_length':m['uncompressed_bytes']+=1
        elif mode=='traversal':m['shards'][0]['name']='../'+m['shards'][0]['name']
        elif mode=='bool_size':m['shards'][0]['bytes']=True
        elif mode=='invalid_descriptor':m=[]
        elif mode=='invalid_gzip':
            bad=b'not gzip';m['shards']=[dict(name='VisualMeshes.bytes.gz.part000',bytes=len(bad),sha256=sha(bad))];m['sha256']=sha(bad);(d/'VisualMeshes.bytes.gz.part000').write_bytes(bad)
        (d/'GeometryShards.json').write_text(json.dumps(m));expect_error(d)
    for field,value in [('shards',None),('shards',{}),('shards',[]),('uncompressed_bytes',True),('uncompressed_bytes','5124'),('sha256',1),('source',None)]:
        reset();m=copy.deepcopy(desc);m[field]=value;(d/'GeometryShards.json').write_text(json.dumps(m));expect_error(d)
    for row in [None,[],1,{'name':'VisualMeshes.bytes.gz.part000','bytes':1,'sha256':False}]:
        reset();m=copy.deepcopy(desc);m['shards'][0]=row;(d/'GeometryShards.json').write_text(json.dumps(m));expect_error(d)
# Actual shipped descriptor+shards in fresh folder, no combined gzip/raw native.
data=ROOT/'Assets/TreeTopYokocho/Data';desc=json.loads((data/'GeometryShards.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);(d/'GeometryShards.json').write_bytes((data/'GeometryShards.json').read_bytes())
    for r in desc['shards']:(d/r['name']).symlink_to((data/r['name']).resolve())
    result=read_visual_transport(d);assert result==(data/'VisualMeshes.bytes').read_bytes();assert not (d/'VisualMeshes.bytes.gz').exists();n+=1
    # Existing combined file is accepted only if byte-identical to actual shards.
    combined=b''.join((data/r['name']).read_bytes() for r in desc['shards']);(d/'VisualMeshes.bytes.gz').write_bytes(combined);assert read_visual_transport(d)==result;n+=1
print(json.dumps(dict(status='PASS',assertions=n,actualNativeSha256=sha(result),actualShards=len(desc['shards']),combinedGzipCreatedByHelper=False),indent=2))
