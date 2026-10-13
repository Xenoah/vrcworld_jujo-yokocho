"""Capture the actual bundled Three.js viewer in a local cloud Chromium browser.
Screenshots are NOT Unity/VRChat runtime captures.
"""
from pathlib import Path
import threading, functools, json, time
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parent.parent
handler=functools.partial(SimpleHTTPRequestHandler,directory=str(root/'Preview'))
server=ThreadingHTTPServer(('127.0.0.1',0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1600,'height':1000},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/TreeTopYokocho_Preview.html',wait_until='load',timeout=180000)
 page.wait_for_function('window.worldReady===true',timeout=180000)
 page.evaluate('window.captureClean()')
 records=[]
 for name,view in [('01_World','overview'),('02_Shop','alley'),('03_DistantScenery','canopy'),('04_WholeTree','whole')]:
  state=page.evaluate('(v)=>window.renderStill(v)',view);page.wait_for_timeout(1800)
  out=root/'Preview'/('ThreeJS_'+name+'.png');page.screenshot(path=str(out));records.append({'file':out.name,'view':view,'state':state})
 # Expose actual invisible-wall geometry for inspection only.
 page.evaluate("window.renderStill('overview'); document.getElementById('barriers').checked=true;document.getElementById('barriers').dispatchEvent(new Event('change'))")
 page.wait_for_timeout(1500);page.screenshot(path=str(root/'Preview/ThreeJS_05_SafetyWalls.png'))
 stats=page.evaluate('window.worldStats');browser.close()
server.shutdown()
(root/'Preview/ThreeJS_capture.json').write_text(json.dumps({'renderer':'Three.js WebGL in cloud Chromium','source_version':'2.1.0','scope':'Actual browser rendering of the generated GLB; NOT Unity or VRChat runtime','stats':stats,'errors':errors,'views':records},ensure_ascii=False,indent=2))
print(json.dumps({'stats':stats,'errors':errors,'screenshots':len(records)+1}))
if errors:raise SystemExit(1)
