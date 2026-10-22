import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = (s) => document.querySelector(s);
const palette = {'储料':0x8fbeae,'输送':0x799eaf,'筛分':0xd0b47e,'破碎':0x9bacc2,'混合':0x92c9c6,'除尘':0xa5b990,'阀门':0xc2a885,'型号待核':0x6d8292};
const icons = {'储料':'▥','输送':'⇢','筛分':'▤','破碎':'◇','混合':'◉','除尘':'▧','阀门':'⋈','型号待核':'□'};
let data, mode='drawing', tab='devices', selected=null, labelsOn=false, flowOn=false;
let scene, camera, renderer, controls, drawingGroup, processGroup, raycaster;
const layerGroups=new Map(),pickables=[], deviceObjects=new Map(), flowDots=[],processLabels=[];
const host=$('#canvas-host');
const labelHost=document.createElement('div');labelHost.className='labels';host.append(labelHost);
let textLabels=[], activeRoot=null, tween=null, dirty=true;
const metrics={ready:false,frame:0,drawCalls:0,geometryVertices:0,mode:'drawing',error:null};
window.__viewer=metrics;
const v=(x=0,y=0,z=0)=>new THREE.Vector3(x,y,z);
function pos(p,height=0.03){return v((p[0]-data.transform.center[0])*data.transform.scale,height,-(p[1]-data.transform.center[1])*data.transform.scale);}
function toast(message){$('#toast').textContent=message;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',2800);}
function go(target,distance,top=false){
 const offset=top?v(0.001,distance,0):v(distance*.65,distance*.8,distance*.78);
 tween={time:performance.now(),from:camera.position.clone(),to:target.clone().add(offset),fromTarget:controls.target.clone(),target:target.clone()};
}
function reset(top=false){document.querySelector('.details').classList.remove('open');if(mode==='drawing')go(v(),220,top);else go(v(0,1,0),42,top);}
function material(color,extra={}){return new THREE.MeshStandardMaterial({color,metalness:.35,roughness:.48,...extra});}
function mesh(geo,mat,root,x=0,y=0,z=0){const o=new THREE.Mesh(geo,mat);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;root.add(o);return o;}
function equipment(category,size=1){
 const root=new THREE.Group(),mat=material(palette[category]??0x98b8b2),steel=material(0x3c5960),dark=material(0x253c44);
 const box=(w,h,d,x=0,y=h/2,z=0,m=mat)=>mesh(new THREE.BoxGeometry(w,h,d),m,root,x,y,z);
 const cyl=(rt,rb,h,x=0,y=h/2,z=0,m=mat)=>mesh(new THREE.CylinderGeometry(rt,rb,h,32),m,root,x,y,z);
 if(category==='储料'){
  cyl(1,1,2.9,0,3);cyl(1,0.26,1.5,0,.85);cyl(1.05,1.05,.15,0,4.5,0,steel);
  for(const x of [-.78,.78])for(const z of [-.78,.78])box(.1,1.8,.1,x,.9,z,steel);
 }else if(category==='输送'){
  box(4,.5,1.1,0,1.15,0,steel);box(3.8,.12,.9,0,1.45,0,dark);
  for(let x=-1.6;x<2;x+=.45){const r=cyl(.15,.15,1.15,x,1.25,0,mat);r.rotation.x=Math.PI/2;}
  for(const x of [-1.4,1.4])for(const z of [-.45,.45])box(.12,1,.12,x,.5,z,steel);
 }else if(category==='筛分'){
  box(2.7,.8,1.6,0,1.8,0);box(2.5,.08,1.4,0,2.24,0,dark);
  for(let x=-1.2;x<1.3;x+=.25)box(.04,.05,1.3,x,2.3,0,steel);
  for(const x of [-1,1])for(const z of [-.6,.6])cyl(.12,.12,1.4,x,.7,z,steel);
 }else if(category==='破碎'){
  box(2.4,1.7,1.8,0,1.5);box(1.9,.5,1.3,0,2.6,0,steel);
  const r=cyl(.75,.75,.22,1.35,1.5,0,dark);r.rotation.z=Math.PI/2;
  box(2.9,.25,2.2,0,.35,0,steel);
 }else if(category==='混合'){
  cyl(1.2,1.2,1.8,0,1.9);cyl(1.25,1.25,.14,0,2.85,0,steel);
  box(.7,.5,.5,0,3.15,0,steel);cyl(.12,.12,1,0,.5,0,steel);
  for(const x of [-.9,.9])for(const z of [-.6,.6])box(.15,1.1,.15,x,.55,z,steel);
 }else if(category==='除尘'){
  box(2.4,2.6,1.6,0,2.5);for(let x=-.85;x<1;x+=.55)cyl(.18,.18,2.3,x,2.5,.86,steel);
  cyl(1.0,.3,1,0,.7);box(.8,.5,.6,0,4.05,0,steel);
 }else if(category==='阀门'){
  const pipe=cyl(.45,.45,1.6,0,1,0);pipe.rotation.z=Math.PI/2;
  cyl(.15,.15,1.0,0,1.8,0,steel);const ring=mesh(new THREE.TorusGeometry(.5,.07,8,32),mat,root,0,2.35,0);ring.rotation.x=Math.PI/2;
  box(2,.15,1,0,.15,0,steel);
 }else{box(1.6,2,1.6);box(1.8,.12,1.8,0,2.1,0,steel);}
 root.scale.setScalar(size);return root;
}
function outline(obj){const edges=new THREE.LineSegments(new THREE.EdgesGeometry(obj.geometry),new THREE.LineBasicMaterial({color:0xbed8cf,transparent:true,opacity:.35}));obj.add(edges);}
async function buildDrawing(){
 const response=await fetch('./geometry.bin');if(!response.ok)throw new Error('几何数据读取失败');const array=new Float32Array(await response.arrayBuffer());
 for(const layer of data.layers){
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(array.subarray(layer.offset*3,(layer.offset+layer.vertices)*3),3));geo.computeBoundingSphere();
  const color=layer.name.includes('设备')?0x99cbb9:layer.name.includes('钢构')?0x6c909d:layer.name.includes('标注')?0x60827d:0x53747e;
  const lines=new THREE.LineSegments(geo,new THREE.LineBasicMaterial({color,transparent:true,opacity:layer.name.includes('设备')?.8:.55}));
  drawingGroup.add(lines);layerGroups.set(layer.name,lines);metrics.geometryVertices+=layer.vertices;
 }
 for(const d of data.devices){
  const a=pos(d.bounds[0]),b=pos(d.bounds[1]);const w=Math.max(.10,Math.min(8,Math.abs(b.x-a.x))),depth=Math.max(.10,Math.min(8,Math.abs(b.z-a.z)));
  const h=Math.min(1.5,Math.max(.14,Math.min(w,depth)*.5));
  const o=mesh(new THREE.BoxGeometry(w,h,depth),material(palette[d.category],{transparent:true,opacity:.6}),drawingGroup,(a.x+b.x)/2,h/2+.05,(a.z+b.z)/2);
  outline(o);o.userData={device:d};pickables.push(o);deviceObjects.set(d.id,o);
 }
}
function buildProcess(){
 const categories=['储料','输送','筛分','破碎','混合','除尘','阀门'];
 const points=[[-12,0,-4],[-4,0,-4],[4,0,-4],[12,0,-4],[12,0,5],[3,0,5],[-6,0,5]];
 for(let i=0;i<categories.length;i++){
  const c=categories[i],members=data.devices.filter(d=>d.category===c&&!d.foundation);if(!members.length)continue;
  const root=equipment(c,.82);root.position.fromArray(points[i]);processGroup.add(root);
  root.traverse(o=>{if(o.isMesh){o.userData={device:members[0],category:c};pickables.push(o);}});
  const plate=mesh(new THREE.CylinderGeometry(2.3,2.3,.1,64),material(0x203b40),processGroup,points[i][0],0,points[i][2]);plate.receiveShadow=true;
  const label=document.createElement('div');label.className='drawing-label process-label';label.textContent=c;
  const small=document.createElement('small');small.textContent=`${members.length} 个符号 · ${members[0].name}`;label.append(small);labelHost.append(label);
  processLabels.push({element:label,position:v(points[i][0],4.6,points[i][2])});
 }
 for(let i=0;i<points.length-1;i++){
  const a=v(...points[i]);a.y=.35;const b=v(...points[i+1]);b.y=.35;
  const elbow=v(b.x,.35,a.z);const route=[a];if(elbow.distanceTo(a)>.01&&elbow.distanceTo(b)>.01)route.push(elbow);route.push(b);
  const curve=new THREE.CurvePath();for(let j=1;j<route.length;j++)curve.add(new THREE.LineCurve3(route[j-1],route[j]));
  const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(route),new THREE.LineDashedMaterial({color:0x7a9b91,dashSize:.35,gapSize:.22,transparent:true,opacity:.7}));line.computeLineDistances();processGroup.add(line);
  for(let n=0;n<3;n++){
   const dot=mesh(new THREE.SphereGeometry(.10,8,8),new THREE.MeshBasicMaterial({color:0xb3f4d3}),processGroup);dot.visible=false;flowDots.push({dot,curve,phase:n/3});
  }
 }
}
function makeLabels(){
 for(const t of data.views.slice(0,60)){const element=document.createElement('div');element.className='drawing-label';element.textContent=t.text;labelHost.append(element);textLabels.push({element,position:pos(t.position,.2),layer:t.layer});}
}
function renderLabels(){
 for(const label of [...textLabels,...processLabels]){
  const process=processLabels.includes(label),enabled=process?mode==='process':mode==='drawing'&&labelsOn&&layerGroups.get(label.layer)?.visible;
  const p=label.position.clone().project(camera);const visible=enabled&&p.z<1&&p.z>-1&&Math.abs(p.x)<1.1&&Math.abs(p.y)<1.1;
  label.element.hidden=!visible;if(visible){label.element.style.left=`${(p.x+1)*host.clientWidth/2}px`;label.element.style.top=`${(-p.y+1)*host.clientHeight/2}px`;}
 }
}
function inspect(d){
 dirty=true;
 if(activeRoot)activeRoot.material.emissive?.setHex(0);selected=d;
 activeRoot=mode==='drawing'?deviceObjects.get(d.id):null;if(activeRoot)activeRoot.material.emissive?.setHex(0x305745);
 $('.details').classList.add('open');$('#detail-category').textContent=`${d.category} · ${d.confidence}`;$('#detail-name').textContent=d.name;
 $('#detail-description').textContent=d.foundation?'该块为基础图或底座视图，不代表新增设备。':'块名与原始位置来自 DXF；三维高度和简化外形仅用于交互示意。';
 const fields=[['源图元句柄',d.id],['所属图层',d.layer],['坐标 X',`${d.position[0].toFixed(1)} mm`],['坐标 Y',`${d.position[1].toFixed(1)} mm`],['类别来源','块名规则'],['当前显示',mode==='drawing'?'原图坐标投影':'类别代表设备示意']];
 showFields(fields);$('#focus-selected').disabled=false;renderInventory();
}
function showFields(fields){const dl=$('#detail-fields');dl.replaceChildren();for(const [key,value]of fields){const row=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;row.append(dt,dd);dl.append(row);}}
function focusDevice(d){setMode('drawing');inspect(d);const a=pos(d.bounds[0]),b=pos(d.bounds[1]),center=a.clone().add(b).multiplyScalar(.5);go(center,Math.max(3,Math.min(30,a.distanceTo(b)*2.1)));}
function setMode(next){
 dirty=true;mode=next;metrics.mode=mode;drawingGroup.visible=mode==='drawing';processGroup.visible=mode==='process';
 $('#mode-drawing').classList.toggle('active',mode==='drawing');$('#mode-process').classList.toggle('active',mode==='process');
 $('#scene-caption').textContent=mode==='drawing'?'原始坐标 / 符号高度仅作示意':'类别代表设备 / 外形与连线均为示意';
 $('#scene-status').textContent=mode==='drawing'?`${data.summary.linePaths.toLocaleString()} 条几何路径`:'7 类设备 · 推演连接';
 $('#process-note').hidden=mode!=='process';$('#toggle-flow').disabled=mode!=='process';$('#toggle-labels').disabled=mode!=='drawing';
 for(const {dot} of flowDots)dot.visible=mode==='process'&&flowOn;reset();
}
function renderInventory(){
 const list=$('#inventory');list.replaceChildren();const query=$('#search').value.trim().toLowerCase();
 if(tab==='layers'){
  const layers=data.layers.filter(l=>l.name.toLowerCase().includes(query));$('#list-count').textContent=layers.length;$('#list-label').textContent='原始图层关闭，当前展示全部图层';
  for(const layer of layers){const row=document.createElement('label');row.className='layer-item';const input=document.createElement('input');input.type='checkbox';input.checked=layerGroups.get(layer.name).visible;input.dataset.layer=layer.name;
   input.addEventListener('change',()=>{dirty=true;layerGroups.get(layer.name).visible=input.checked;for(const d of data.devices)if(d.layer===layer.name)deviceObjects.get(d.id).visible=input.checked;});
   const name=document.createElement('span');name.textContent=layer.name;const small=document.createElement('small');small.textContent=(layer.vertices/2).toLocaleString()+' 段';row.append(input,name,small);list.append(row);}
  return;
 }
 const items=tab==='texts'?data.texts.filter(t=>t.text.toLowerCase().includes(query)):data.devices.filter(d=>(d.name+' '+d.category+' '+d.id).toLowerCase().includes(query));
 $('#list-count').textContent=items.length;$('#list-label').textContent=tab==='texts'?'含块展开与尺寸文字':'符号实例 · 包含重复视图';
 for(const item of items.slice(0,250)){
  const row=document.createElement('button');row.className='item'+(item.id&&selected?.id===item.id?' selected':'');
  const icon=document.createElement('span');icon.className='item-icon';icon.textContent=tab==='texts'?'T':icons[item.category];
  const copy=document.createElement('span');copy.className='item-copy';const name=document.createElement('span');name.className='item-name';name.textContent=tab==='texts'?item.text:item.name;
  const meta=document.createElement('span');meta.className='item-meta';meta.textContent=tab==='texts'?`${item.layer} · ${item.type}`:`${item.category} / #${item.id}`;
  copy.append(name,meta);const arrow=document.createElement('span');arrow.className='item-arrow';arrow.textContent='↗';row.append(icon,copy,arrow);
  row.addEventListener('click',()=>{
   if(tab==='devices')focusDevice(item);else{setMode('drawing');go(pos(item.position),6);$('#detail-category').textContent='原图文字';$('#detail-name').textContent=item.text;$('#detail-description').textContent='此文字的位置已由块变换映射到模型空间。';showFields([['图层',item.layer],['类型',item.type],['来源句柄',item.source]]);$('#focus-selected').disabled=true;$('.details').classList.add('open');}
  });list.append(row);
 }
 if(!items.length){const empty=document.createElement('p');empty.className='empty';empty.textContent='没有匹配结果';list.append(empty);}
 if(items.length>250){const note=document.createElement('p');note.className='empty';note.textContent=`当前显示前 250 条，共 ${items.length} 条；输入关键词缩小范围。`;list.append(note);}
}
function pick(event){
 if(!metrics.ready)return;const rect=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
 const hits=raycaster.intersectObjects(pickables.filter(o=>{let p=o;while(p){if(!p.visible)return false;p=p.parent;}return true;}),false);
 if(hits.length&&hits[0].object.userData.device)inspect(hits[0].object.userData.device);else $('.details').classList.remove('open');
}
function initThree(){
 scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x142028,.0016);
 camera=new THREE.PerspectiveCamera(42,host.clientWidth/host.clientHeight,.01,2000);camera.position.set(100,125,120);
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.setSize(host.clientWidth,host.clientHeight);renderer.setClearColor(0x152028,0);renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
 host.prepend(renderer.domElement);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.09;controls.minDistance=.3;controls.maxDistance=500;controls.maxPolarAngle=Math.PI*.49;
 controls.addEventListener('start',()=>tween=null);controls.addEventListener('change',()=>dirty=true);
 scene.add(new THREE.HemisphereLight(0xc4e9e6,0x223947,2.6));const light=new THREE.DirectionalLight(0xe2f4eb,3);light.position.set(-15,45,25);scene.add(light);
 const grid=new THREE.GridHelper(240,80,0x37535a,0x243a43);grid.material.transparent=true;grid.material.opacity=.35;grid.position.y=-.05;scene.add(grid);
 drawingGroup=new THREE.Group();processGroup=new THREE.Group();processGroup.visible=false;scene.add(drawingGroup,processGroup);raycaster=new THREE.Raycaster();
 let down;renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',e=>{if(down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])<5)pick(e);});
 new ResizeObserver(()=>{if(!host.clientWidth)return;dirty=true;renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();}).observe(host);
 const animate=(time)=>{
  requestAnimationFrame(animate);if(tween){const t=Math.min((time-tween.time)/650,1),ease=1-(1-t)**3;camera.position.lerpVectors(tween.from,tween.to,ease);controls.target.lerpVectors(tween.fromTarget,tween.target,ease);if(t===1)tween=null;}
  controls.update();if(flowOn&&mode==='process')for(const {dot,curve,phase}of flowDots)dot.position.copy(curve.getPoint((time*.00012+phase)%1));
  if(dirty||(flowOn&&mode==='process')){renderer.render(scene,camera);metrics.renders=(metrics.renders||0)+1;dirty=false;}metrics.camera=camera.position.toArray();metrics.target=controls.target.toArray();metrics.viewport=[host.clientWidth,host.clientHeight];metrics.frame++;metrics.drawCalls=renderer.info.render.calls;renderLabels();
 };requestAnimationFrame(animate);
}
function wire(){
 for(const t of ['devices','texts','layers'])$(`#tab-${t}`).addEventListener('click',()=>{tab=t;for(const other of ['devices','texts','layers'])$(`#tab-${other}`).classList.toggle('active',t===other);renderInventory();});
 $('#search').addEventListener('input',renderInventory);
 $('#mode-drawing').addEventListener('click',()=>setMode('drawing'));$('#mode-process').addEventListener('click',()=>setMode('process'));
 $('#reset').addEventListener('click',()=>reset());$('#top-view').addEventListener('click',()=>reset(true));
 $('#focus-selected').addEventListener('click',()=>{if(selected)focusDevice(selected);});
 $('#toggle-labels').addEventListener('click',()=>{labelsOn=!labelsOn;$('#toggle-labels').classList.toggle('active',labelsOn);$('#toggle-labels').setAttribute('aria-pressed',String(labelsOn));if(labelsOn)toast('显示视图标题；全部文字可在“文字标注”中搜索定位。');});
 $('#toggle-flow').addEventListener('click',()=>{dirty=true;flowOn=!flowOn;$('#toggle-flow').classList.toggle('active',flowOn);$('#toggle-flow').setAttribute('aria-pressed',String(flowOn));for(const {dot}of flowDots)dot.visible=flowOn;});
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();$('#search').focus();}if(e.key==='Escape')$('.details').classList.remove('open');});
}
async function main(){
 try{
  const res=await fetch('./drawing.json');if(!res.ok)throw new Error('找不到解析数据');data=await res.json();metrics.summary=data.summary;
  $('#device-count').textContent=data.summary.deviceSymbols;$('#text-count').textContent=data.summary.directTexts;$('#layer-count').textContent=data.summary.layers;
  $('#quality-status').textContent='转换含修复';$('#quality-note').textContent=`${data.summary.auditFixes} 项审计修复；${data.summary.proxyEntities} 个代理图元未渲染。管线数量待确认。`;
  initThree();$('#loading').textContent='构建图纸几何…';await buildDrawing();buildProcess();makeLabels();wire();renderInventory();setMode('drawing');
  $('#loading').hidden=true;metrics.ready=true;
 }catch(error){metrics.error=String(error);$('#loading').textContent=`加载失败：${error.message}`;$('#scene-status').textContent='加载失败';console.error(error);}
}
main();
