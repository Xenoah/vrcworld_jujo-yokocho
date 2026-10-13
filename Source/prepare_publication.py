"""Build bounded Git-data upload manifests without publishing or credentials."""
from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent.parent
out=root.parent/'tree-publish';out.mkdir(exist_ok=True)
files=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=root).decode().split('\0')
files=sorted(set(x for x in files if x and (root/x).is_file()))
binaries=[];texts=[]
for name in files:
 p=root/name;raw=p.read_bytes();sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 # Large UTF-8 JSON uses a blob too; tree requests stay below100KB.
 try:content=raw.decode('utf8')
 except UnicodeDecodeError:content=None
 if content is None or len(raw)>70000:
  binaries.append(dict(path=name,size=len(raw),sha=sha))
 else:texts.append(dict(path=name,mode='100644',type='blob',content=content))
(out/'binaries.json').write_text(json.dumps(binaries))
groups=[];part=[];length=0
for x in texts:
 size=len(json.dumps(x).encode())
 if part and length+size>85000:groups.append(part);part=[];length=0
 part.append(x);length+=size
groups.append(part)
for p in out.glob('texts-*.json'):p.unlink()
for i,x in enumerate(groups):(out/f'texts-{i:02}.json').write_text(json.dumps(x))
(out/'file-list.json').write_text(json.dumps(files))
print(json.dumps(dict(files=len(files),binary=len(binaries),binary_bytes=sum(x['size'] for x in binaries),text_groups=len(groups),group_bytes=[len(json.dumps(x)) for x in groups])))
