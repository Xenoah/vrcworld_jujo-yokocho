"""Verify binary payloads survive Git clean/smudge with Windows-style CRLF.
This runs installed Git in a temporary isolated index, not Unity or Windows.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
data=root/'Assets/TreeTopYokocho/Data';shards=json.loads((data/'GeometryShards.json').read_text())
paths=['Assets/TreeTopYokocho/Data/'+row['name'] for row in shards['shards']]
paths+=['Assets/TreeTopYokocho/Data/CollisionMeshes.bytes.gz']
with tempfile.TemporaryDirectory(prefix='yokocho-git-binary-') as tmp:
    repository=Path(tmp)/'repo';repository.mkdir()
    shutil.copy2(root/'.gitattributes',repository/'.gitattributes')
    for name in paths:
        destination=repository/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/name,destination)
    env=dict(os.environ)
    for key in ('GIT_INDEX_FILE','GIT_DIR','GIT_WORK_TREE'):env.pop(key,None)
    def git(*args,**kwargs):return subprocess.check_output(['git','-c','core.autocrlf=true',*args],cwd=repository,env=env,**kwargs)
    git('init','--quiet')
    git('add','--','.gitattributes',*paths)
    output=Path(tmp)/'checkout';output.mkdir()
    git('checkout-index','--prefix='+str(output)+'/', '--','.gitattributes',*paths)
    checks=[]
    for name in paths:
        raw=(root/name).read_bytes();copy=(output/name).read_bytes()
        if copy!=raw:raise AssertionError('Git changed binary bytes: '+name)
        checks.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
result=dict(status='PASS',core_autocrlf=True,files=checks,scope='Git clean and checkout filters with CRLF enabled in a temporary index; no Windows or Unity execution.')
(root/'Docs/git_binary_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
