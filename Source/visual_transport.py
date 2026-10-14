"""Read and authenticate actual descriptor-listed visual shards, without writes.

Combined gzip is optional authoring convenience, never a substitute for shards.
If present it must equal the validated shard stream. Geometry admission remains
with the existing independent payload contracts, not this transport helper.
"""
import gzip,hashlib,json,re,zlib
from pathlib import Path
from typing import NamedTuple

class VisualTransport(NamedTuple):
    raw: bytes
    compressed_bytes: int
    compressed_sha256: str
    shard_count: int

def validated_visual_transport(data):
    data=Path(data)
    try:descriptor=json.loads((data/'GeometryShards.json').read_text())
    except (OSError,ValueError) as error:raise ValueError('Cannot read geometry shard descriptor') from error
    def digest(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
    if not isinstance(descriptor,dict) or descriptor.get('source')!='JYWM v1, gzip':raise ValueError('Invalid geometry shard descriptor')
    rows=descriptor.get('shards');length=descriptor.get('uncompressed_bytes')
    if not isinstance(rows,list) or not rows or type(length) is not int or length<=0 or not digest(descriptor.get('sha256')):raise ValueError('Invalid geometry shard descriptor fields')
    parts=[]
    for index,row in enumerate(rows):
        expected=f'VisualMeshes.bytes.gz.part{index:03}'
        if not isinstance(row,dict) or row.get('name')!=expected:raise ValueError('Missing, duplicate or out-of-order geometry shard name')
        if type(row.get('bytes')) is not int or row['bytes']<=0 or not digest(row.get('sha256')):raise ValueError('Invalid geometry shard size/hash')
        try:payload=(data/expected).read_bytes()
        except OSError as error:raise ValueError('Missing or unreadable geometry shard: '+expected) from error
        if len(payload)!=row['bytes'] or hashlib.sha256(payload).hexdigest()!=row['sha256']:raise ValueError('Changed or incomplete geometry shard: '+expected)
        parts.append(payload)
    compressed=b''.join(parts)
    if hashlib.sha256(compressed).hexdigest()!=descriptor['sha256']:raise ValueError('Combined geometry checksum mismatch')
    combined=data/'VisualMeshes.bytes.gz'
    if combined.exists() and combined.read_bytes()!=compressed:raise ValueError('Combined gzip differs from descriptor-listed shards')
    try:raw=gzip.decompress(compressed)
    except (OSError,EOFError,zlib.error) as error:raise ValueError('Invalid geometry gzip stream') from error
    if len(raw)!=length:raise ValueError('Uncompressed geometry length mismatch')
    return VisualTransport(raw,len(compressed),descriptor['sha256'],len(rows))

def read_visual_transport(data):
    """Return native bytes only, through the same complete transport validation."""
    return validated_visual_transport(data).raw
