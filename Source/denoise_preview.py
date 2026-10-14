"""Standard Open Image Denoise pass; never synthesizes or repaints a scene.

Use only on the actual Cycles output. The raw PNG and its digest are retained.
This fallback is for Blender distributions built without a native denoiser.
Optional dependency: the official-registry Python package oidn (0.2.1 used).
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
from PIL import Image
import oidn

p=argparse.ArgumentParser();p.add_argument('images',nargs='+');a=p.parse_args()
for name in a.images:
    path=Path(name);metadata=path.with_suffix('.json')
    info=json.loads(metadata.read_text()) if metadata.exists() else {}
    if info.get('denoising','none') != 'none':
        raise SystemExit('Refusing to denoise an already processed output: '+str(path))
    raw=path.parent/'Raw'/path.name;raw.parent.mkdir(exist_ok=True)
    # Never replace retained evidence with a processed or mismatched image.
    if raw.exists():
        if hashlib.sha256(raw.read_bytes()).digest()!=hashlib.sha256(path.read_bytes()).digest():
            raise SystemExit('Existing raw differs from input; refusing to overwrite evidence: '+str(raw))
    else:shutil.copy2(path,raw)
    im=Image.open(raw).convert('RGB');data=np.asarray(im,dtype=np.float32)/255
    result=np.empty_like(data);device=oidn.NewDevice(oidn.DEVICE_TYPE_CPU)
    oidn.CommitDevice(device);filt=oidn.NewFilter(device,'RT')
    oidn.SetSharedFilterImage(filt,'color',data,oidn.FORMAT_FLOAT3,im.width,im.height)
    oidn.SetSharedFilterImage(filt,'output',result,oidn.FORMAT_FLOAT3,im.width,im.height)
    guides={}
    if info.get('denoising_scene_passes'):
        import OpenEXR
        for channel in ('albedo','normal'):
            guide=path.parent/'Raw'/(path.stem+'_'+channel+'_0001.exr')
            with OpenEXR.File(str(guide)) as source:
                channels=source.channels()
                if 'RGB' in channels:values=channels['RGB'].pixels
                elif all(k in channels for k in ('X','Y','Z')):
                    values=np.stack([channels[k].pixels for k in ('X','Y','Z')],axis=-1)
                else:raise ValueError('Unexpected EXR channels: '+str(list(channels)))
                guides[channel]=np.ascontiguousarray(values,dtype=np.float32)
            if guides[channel].shape != data.shape or not np.isfinite(guides[channel]).all():
                raise ValueError('Invalid scene denoising pass: '+str(guide))
            oidn.SetSharedFilterImage(filt,channel,guides[channel],oidn.FORMAT_FLOAT3,im.width,im.height)
    oidn.CommitFilter(filt);oidn.ExecuteFilter(filt)
    err=oidn.GetDeviceError(device)
    code=err[0] if isinstance(err,tuple) else err
    if code != oidn.ERROR_NONE:raise RuntimeError(err)
    oidn.ReleaseFilter(filt);oidn.ReleaseDevice(device)
    if not np.isfinite(result).all():raise ValueError('Non-finite denoiser output: '+str(path))
    Image.fromarray(np.uint8(np.clip(result*255+.5,0,255))).save(path)
    info['denoising']='Intel Open Image Denoise RT, LDR '+('with actual scene albedo/normal guides' if guides else 'color-only')+'; raw retained in Raw/'
    info['raw_render_sha256']=hashlib.sha256(raw.read_bytes()).hexdigest()
    info['denoised_render_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    info['denoiser_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    info['denoising_guide_sha256']={channel:hashlib.sha256((path.parent/'Raw'/(path.stem+'_'+channel+'_0001.exr')).read_bytes()).hexdigest() for channel in guides}
    metadata.write_text(json.dumps(info,indent=2))
    print(json.dumps({'path':str(path),'raw':str(raw),'pixels':[im.width,im.height]}))
