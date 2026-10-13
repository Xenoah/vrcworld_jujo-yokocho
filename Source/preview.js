import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
const container=document.getElementById('view');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.10;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#283a57');scene.fog=new THREE.FogExp2('#53627b',.00085);
const camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.04,2800);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.09;
controls.minDistance=2;controls.maxDistance=700;controls.maxPolarAngle=Math.PI*.86;
scene.add(new THREE.HemisphereLight('#88a6d2','#756249',1.05));
const sun=new THREE.DirectionalLight('#95b1e4',1.45);sun.position.set(70,110,60);sun.target.position.set(0,44,0);scene.add(sun.target);scene.add(sun);
sun.castShadow=true;sun.shadow.mapSize.set(4096,4096);Object.assign(sun.shadow.camera,{left:-65,right:65,top:65,bottom:-65,near:1,far:250});sun.shadow.bias=-.0003;sun.shadow.normalBias=.035;
const fill=new THREE.DirectionalLight('#e8a46d',.32);fill.position.set(-30,50,10);scene.add(fill);
// Atmospheric blue-hour sky, with a sunset band and non-repeating cloud detail.
const skyVertex=`varying vec3 v;void main(){v=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
const skyFragment=`varying vec3 v;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=noise(p)*a;p=p*2.07+17.3;a*=.5;}return v;}
void main(){vec3 d=normalize(v);float y=max(d.y,0.);float t=pow(y,.46);vec3 c=mix(vec3(.17,.23,.34),vec3(.012,.034,.085),t);
float sunset=pow(max(dot(normalize(d.xz+vec2(.00001)),normalize(vec2(-.8,-.6))),0.),6.);c+=vec3(.26,.085,.033)*exp(-pow((d.y-.035)*12.,2.))*sunset;
vec2 p=d.xz/max(.11,d.y+.2)*2.5;float cloud=smoothstep(.48,.70,fbm(p*vec2(1.,3.2)));c=mix(c,c*.55+vec3(.007,.008,.012),cloud*smoothstep(0.,.14,d.y)*.75);
gl_FragColor=vec4(c,1.);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
const sky=new THREE.Mesh(new THREE.SphereGeometry(2550,40,24),new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,vertexShader:skyVertex,fragmentShader:skyFragment}));scene.add(sky);
const environment=new THREE.Scene();environment.add(sky.clone());
const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(environment,.07,.1,2800).texture;scene.environmentIntensity=.62;pmrem.dispose();
const composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));
// Reject non-finite HDR samples before multi-scale bloom can spread them.
// The real material remains HDR; a finite ceiling protects low precision targets.
const finiteHDR=new ShaderPass({uniforms:{tDiffuse:{value:null}},vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,fragmentShader:`uniform sampler2D tDiffuse;varying vec2 vUv;float finiteValue(float v){return v>=0.?min(v,32.):0.;}void main(){vec4 c=texture2D(tDiffuse,vUv);gl_FragColor=vec4(finiteValue(c.r),finiteValue(c.g),finiteValue(c.b),1.);}`});composer.addPass(finiteHDR);
const bloom=new UnrealBloomPass(new THREE.Vector2(innerWidth,innerHeight),.22,.65,1.10);composer.addPass(bloom);composer.addPass(new OutputPass());
const presets={
  overview:{p:[47,55,63],t:[0,43,-1]},
  alley:{p:[-12.4,42.2,17.8],t:[-5.7,41.6,9.5]},
  arrival:{p:[9,37.5,39],t:[-1,36,24]},
  canopy:{p:[-24.5,53.75,-23.4],t:[-110,23,-137]},
  whole:{p:[125,92,156],t:[0,56,0]},
};
function setView(id){const v=presets[id]||presets.overview;camera.position.fromArray(v.p);controls.target.fromArray(v.t);controls.update();if(window.worldReady)updateLights();document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===id));}
window.setView=setView;setView('overview');
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
const compressed=Uint8Array.from(atob(document.getElementById('model-data').textContent.trim()),c=>c.charCodeAt(0));
let animatedWater=null;
(async()=>{
 const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
 const bytes=await new Response(stream).arrayBuffer();
 new GLTFLoader().parse(bytes,'',gltf=>{
  scene.add(gltf.scene);let triangles=0;
  gltf.scene.traverse(obj=>{if(obj.isMesh){
   obj.frustumCulled=true;obj.castShadow=!obj.name.startsWith('Landscape');obj.receiveShadow=true;
   const m=obj.material;if(m.map)m.map.anisotropy=16;
   if(m.normalMap)m.normalMap.anisotropy=8;
   if(m.name==='PaperLight')m.emissiveIntensity=2.6;
   if(m.name==='RedLantern')m.emissiveIntensity=2.2;
   if(m.name==='WarmWindow'||m.name==='TownLights')m.emissiveIntensity=2.1;
   if(m.name.startsWith('Foliage')){m.side=THREE.DoubleSide;m.emissive=new THREE.Color('#1f2c0b');m.emissiveIntensity=.045;}
   if(m.name==='Lake'){
    m.roughness=.14;m.metalness=.5;m.envMapIntensity=1.25;
    m.onBeforeCompile=shader=>{shader.uniforms.waterTime={value:0};animatedWater=shader;
     shader.vertexShader='uniform float waterTime;\n'+shader.vertexShader;
     shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ntransformed.y+=sin(position.x*.13+waterTime*.4)*.025+sin(position.z*.19-waterTime*.28)*.018;');
     shader.fragmentShader='uniform float waterTime;\n'+shader.fragmentShader;
     shader.fragmentShader=shader.fragmentShader.replace('texture2D( normalMap, vNormalMapUv )','texture2D( normalMap, vNormalMapUv + vec2(waterTime*.003,waterTime*.002) )');
    };
   }
   triangles+=obj.geometry.index?obj.geometry.index.count/3:obj.geometry.attributes.position.count/3;
  }});
  document.getElementById('loading').style.display='none';window.worldReady=true;window.worldStats={triangles};
 },error=>{document.getElementById('loading').textContent='モデルの読込に失敗しました';console.error(error);});
})().catch(console.error);
const lamps=JSON.parse(document.getElementById('lights-data').textContent).filter(x=>x.range>3);
const warmLights=Array.from({length:16},()=>{const light=new THREE.PointLight('#ffae62',45,9.5,2);scene.add(light);return light;});
const steamSources=JSON.parse(document.getElementById('steam-data').textContent);
const steamCanvas=document.createElement('canvas');steamCanvas.width=steamCanvas.height=128;
const ctx=steamCanvas.getContext('2d');const pixels=ctx.createImageData(128,128);
for(let y=0;y<128;y++)for(let x=0;x<128;x++){const k=(y*128+x)*4;const r=((x-64)/64)**2+((y-64)/64)**2;const n=.65+.35*Math.sin(x*.37+Math.sin(y*.21)*2)*Math.sin(y*.43);pixels.data[k]=230;pixels.data[k+1]=221;pixels.data[k+2]=206;pixels.data[k+3]=255*Math.max(0,1-r)**2*n;}
ctx.putImageData(pixels,0,0);const steamTexture=new THREE.CanvasTexture(steamCanvas);const steamParticles=[];
steamSources.forEach((source,k)=>{for(let j=0;j<16;j++){
 const material=new THREE.SpriteMaterial({map:steamTexture,color:'#e9d9c3',opacity:.09,transparent:true,depthWrite:false,blending:THREE.NormalBlending});const sprite=new THREE.Sprite(material);scene.add(sprite);steamParticles.push({sprite,source:source.position,phase:j/16,sway:k*1.7+j*2.4});
}});
function animateSteam(time){steamParticles.forEach(({sprite,source,phase,sway})=>{const t=(time*.29+phase)%1;const size=.16+t*.46;sprite.scale.set(size,size,1);sprite.position.set(source[0]+Math.sin(t*6+sway)*t*.12,source[2]+t*.85,-source[1]+Math.cos(t*7+sway)*t*.10);sprite.material.opacity=.11*Math.sin(t*Math.PI);});}
let nextLightUpdate=0;
const barrierRoot=new THREE.Group();barrierRoot.visible=false;scene.add(barrierRoot);
const data=Uint8Array.from(atob(document.getElementById('collision-data').textContent.trim()),c=>c.charCodeAt(0));
const dv=new DataView(data.buffer);let pos=8;const u32=()=>{const v=dv.getUint32(pos,true);pos+=4;return v;};const str=()=>{const n=u32();const t=new TextDecoder().decode(data.subarray(pos,pos+n));pos+=n;return t;};
const count=u32();
for(let b=0;b<count;b++){
 const group=str();str();const vc=u32(),ic=u32();let offset=pos;pos+=vc*12;pos+=vc*8;pos+=vc*4;let indexOffset=pos;pos+=ic*4;
 if(!group.startsWith('Safety/'))continue;
 const vertices=new Float32Array(vc*3);for(let j=0;j<vc;j++){vertices[j*3]=dv.getFloat32(offset+j*12,true);vertices[j*3+1]=dv.getFloat32(offset+j*12+8,true);vertices[j*3+2]=-dv.getFloat32(offset+j*12+4,true);}
 const indices=new Uint32Array(ic);for(let j=0;j<ic;j++)indices[j]=dv.getUint32(indexOffset+j*4,true);
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(vertices,3));geometry.setIndex(new THREE.BufferAttribute(indices,1));geometry.computeVertexNormals();
 const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:'#65d6db',transparent:true,opacity:.14,side:THREE.DoubleSide,depthWrite:false}));barrierRoot.add(mesh);
}
document.getElementById('barriers').onchange=e=>{barrierRoot.visible=e.target.checked;document.getElementById('barrier-note').hidden=!e.target.checked;};
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);composer.setSize(innerWidth,innerHeight);});
function updateLights(){
 const nearest=lamps.slice().sort((a,b)=>{const dist=x=>(x.position[0]-camera.position.x)**2+(x.position[2]-camera.position.y)**2+(-x.position[1]-camera.position.z)**2;return dist(a)-dist(b)});
 warmLights.forEach((light,i)=>{const p=nearest[i].position;light.position.set(p[0],p[2],-p[1]);light.intensity=nearest[i].strength*16;light.distance=nearest[i].range*1.8;});
}
window.renderStill=(id)=>{if(id)setView(id);updateLights();composer.render();return {camera:camera.position.toArray(),lamps:warmLights.slice(0,4).map(l=>({p:l.position.toArray(),i:l.intensity}))};};
function frame(){requestAnimationFrame(frame);controls.update();if(performance.now()>nextLightUpdate){nextLightUpdate=performance.now()+500;updateLights();}if(animatedWater)animatedWater.uniforms.waterTime.value=performance.now()*.001;animateSteam(performance.now()*.001);composer.render();}frame();
window.captureClean=()=>{document.querySelectorAll('.chrome').forEach(x=>x.style.display='none');window.renderStill();};
