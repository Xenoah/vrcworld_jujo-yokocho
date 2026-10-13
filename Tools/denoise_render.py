"""Standard OIDN ray-tracing noise filter for Blender preview output.
Preserves raw renders in Preview/Raw. No image synthesis or geometry edits.
Requires the optional PyPI package oidn==0.2.1.
"""
from pathlib import Path
import sys,json,shutil
import numpy as np
from PIL import Image
import oidn

for filename in sys.argv[1:]:
 path=Path(filename);raw=path.parent/'Raw'/path.name;raw.parent.mkdir(exist_ok=True)
 shutil.copy2(path,raw)
 color=np.ascontiguousarray(np.asarray(Image.open(raw).convert('RGB'),dtype=np.float32)/255)
 out=np.empty_like(color);h,w,_=color.shape
 device=oidn.NewDevice(oidn.DEVICE_TYPE_CPU);oidn.CommitDevice(device)
 filt=oidn.NewFilter(device,'RT')
 oidn.SetSharedFilterImage(filt,'color',color,oidn.FORMAT_FLOAT3,w,h)
 oidn.SetSharedFilterImage(filt,'output',out,oidn.FORMAT_FLOAT3,w,h)
 oidn.CommitFilter(filt);oidn.ExecuteFilter(filt)
 error=oidn.GetDeviceError(device)
 oidn.ReleaseFilter(filt);oidn.ReleaseDevice(device)
 if error:raise RuntimeError(error)
 assert np.isfinite(out).all()
 Image.fromarray(np.uint8(np.clip(out*255,0,255))).save(path)
 meta=path.with_suffix('.json');m=json.loads(meta.read_text()) if meta.exists() else {}
 m['denoising']='Intel Open Image Denoise RT, color-only LDR; raw retained in Raw/'
 meta.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 print(path)
