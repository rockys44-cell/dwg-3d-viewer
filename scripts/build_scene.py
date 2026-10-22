"""Create a source-linked visualization; geometric candidates are not certified pipes."""
from __future__ import annotations
import json, re, math, hashlib, struct
from collections import Counter,defaultdict
from pathlib import Path
import ezdxf
from ezdxf import path as dp, bbox
ROOT=Path(__file__).resolve().parents[1]
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'),default=str),encoding='utf8')
def kind(name):
 if re.search('闸门|闸阀|对夹阀|^DN\\d',name):return '阀门'
 if re.search('缓冲罐|吨袋|缓冲仓',name):return '储料'
 if re.search('螺旋输送机|^NE50|^B[46]00X',name,re.I):return '输送'
 if re.search('振动筛',name):return '筛分'
 if re.search('对辊机|^PE[X-]?\\d|^2PG',name,re.I):return '破碎'
 if re.search('混合机',name):return '混合'
 if re.search('收尘器|^DMC',name):return '除尘'
 if re.search('^SCNZ|^LFHBF',name):return '型号待核'
 return None

def main():
 doc=ezdxf.readfile(ROOT/'converted.dxf');audit=doc.audit();m=doc.modelspace()
 skipped=Counter(); sampled=Counter(); layer_paths=defaultdict(list); text_instances=[]
 def walk(e, inherited='0',depth=0):
  if depth>24:skipped['depth_limit']+=1;return
  layer=e.dxf.get('layer','0');layer=inherited if layer=='0' else layer
  typ=e.dxftype()
  if typ in {'INSERT','DIMENSION','POLYLINE'}:
   if typ=='POLYLINE' and not e.is_poly_face_mesh and not e.is_polygon_mesh:
    yield e,layer;return
   try:
    for child in e.virtual_entities():yield from walk(child,layer,depth+1)
    if typ=='INSERT':
     for a in e.attribs:yield a,layer
   except Exception as exc:skipped[f'{typ}:{type(exc).__name__}']+=1
   return
  yield e,layer
 def points(e):
  typ=e.dxftype()
  if typ=='LINE':return [list(e.dxf.start),list(e.dxf.end)]
  if typ in {'ARC','CIRCLE','ELLIPSE','SPLINE','LWPOLYLINE','POLYLINE','SOLID','TRACE','3DFACE'}:
   try:
    p=dp.make_path(e)
    return [list(v) for v in p.flattening(distance=100,segments=4)]
   except Exception as exc:skipped[f'{typ}:{type(exc).__name__}']+=1
  elif typ not in {'TEXT','MTEXT','ATTRIB','ATTDEF','POINT'}:skipped[typ]+=1
  return []
 # Device symbols: top-level INSERTs with explicit semantic/model-name evidence.
 # Record physical dimensions from symbol bbox in drawing units, never real device height.
 devices=[];cache=bbox.Cache()
 for e in m.query('INSERT'):
  category=kind(e.dxf.name)
  if not category:continue
  try:
   bb=bbox.extents([e],cache=cache)
   lo=list(bb.extmin);hi=list(bb.extmax)
   if not bb.has_data:raise ValueError('empty')
  except Exception:
   p=list(e.dxf.insert);lo=p;hi=p
  devices.append({'id':e.dxf.handle,'name':e.dxf.name,'category':category,'layer':e.dxf.layer,'position':list(e.dxf.insert),'bounds':[lo,hi],'confidence':'型号待核' if category=='型号待核' else '块名识别','foundation':bool(re.search('基础|底座',e.dxf.name))})
 # Only direct model-space paths on equipment-outline layer are candidates.
 # Keep each CAD entity separate: never claim physical pipes or connected circuits.
 candidates=[]
 for e in m:
  if e.dxftype() in {'LINE','LWPOLYLINE','POLYLINE'} and e.dxf.layer=='1-设备轮廓':
   pp=points(e)
   if len(pp)>1:candidates.append({'id':e.dxf.handle,'type':e.dxftype(),'layer':e.dxf.layer,'points':pp,'status':'设备轮廓线，未确认管线'})
 for source in m:
  for e,layer in walk(source):
   t=e.dxftype(); sampled[t]+=1
   if t in {'TEXT','MTEXT','ATTRIB','ATTDEF'}:
    try:text=e.plain_text() if hasattr(e,'plain_text') else e.dxf.text
    except Exception:text=''
    text=re.sub(r'\\U\+([0-9A-Fa-f]{4})',lambda m:chr(int(m[1],16)),text)
    if text:text_instances.append({'text':text,'position':list(e.dxf.get('insert',(0,0,0))),'height':e.dxf.get('char_height',100) if t=='MTEXT' else e.dxf.get('height',100),'layer':layer,'source':source.dxf.handle,'type':t})
   pp=points(e)
   if len(pp)>1:
    # Reduce JSON precision only for browser drawing, not the full DXF inventory.
    layer_paths[layer].append([[round(p[0],3),round(p[1],3),round(p[2],3)] for p in pp])
 coords=[p for paths in layer_paths.values() for path in paths for p in path]
 bounds=[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]]
 titles=[t for t in text_instances if any(w in t['text'] for w in ['层面布置','层面布局','剖面图','基础定位','基础开挖']) and len(t['text'])<65]
 directtypes=dict(Counter(e.dxftype() for e in m))
 defs=json.loads((ROOT/'analysis/texts.json').read_text())
 summary={'layers':len(doc.layers),'blocks':len(doc.blocks),'modelEntities':len(m),'entityDatabase':len(json.loads((ROOT/'analysis/entities.json').read_text())),'blockReferences':len(m.query('INSERT')),'deviceSymbols':len(devices),'namedDeviceSymbols':sum(d['category']!='型号待核' for d in devices),'modelCodeSymbols':sum(d['category']=='型号待核' for d in devices),'foundationSymbols':sum(d['foundation'] for d in devices),'candidatePaths':len(candidates),'confirmedPipelines':None,'directTexts':len(m.query('TEXT MTEXT ATTRIB')),'textDefinitions':len(defs),'expandedTexts':len(text_instances),'auditFixes':len(audit.fixes),'auditErrors':len(audit.errors),'proxyEntities':directtypes.get('ACAD_PROXY_ENTITY',0),'units':'mm','dxfVersion':doc.dxfversion,'types':directtypes,'categories':dict(Counter(d['category'] for d in devices)),'skipRender':dict(skipped),'renderedTypes':dict(sampled),'linePaths':sum(len(v) for v in layer_paths.values()),'zRange':[bounds[0][2],bounds[1][2]],'originalSha256':hashlib.sha256(next(ROOT.glob('*.dwg')).read_bytes()).hexdigest()}
 layerdata=[{'name':l.dxf.name,'color':abs(l.dxf.color),'originallyOff':l.is_off(),'frozen':l.is_frozen(),'paths':layer_paths[l.dxf.name]} for l in doc.layers]
 cx=(bounds[0][0]+bounds[1][0])/2;cy=(bounds[0][1]+bounds[1][1])/2
 scale=200/max(bounds[1][0]-bounds[0][0],bounds[1][1]-bounds[0][1],1)
 geometry=bytearray()
 for layer in layerdata:
  layer['offset']=len(geometry)//12
  seen=set();duplicates=0
  for path in layer.pop('paths'):
   for a,b in zip(path,path[1:]):
    av=(round((a[0]-cx)*scale,6),round(-(a[1]-cy)*scale,6))
    bv=(round((b[0]-cx)*scale,6),round(-(b[1]-cy)*scale,6))
    key=(av,bv) if av<bv else (bv,av)
    if av==bv or key in seen:duplicates+=1;continue
    seen.add(key)
    geometry.extend(struct.pack('<6f',av[0],0.02,av[1],bv[0],0.02,bv[1]))
  layer['vertices']=len(geometry)//12-layer['offset']
  layer['deduplicatedSegments']=duplicates
 (ROOT/'web/public/geometry.bin').write_bytes(geometry)
 summary['geometryBytes']=len(geometry)
 summary['browserCurveToleranceMm']=100
 summary['browserSegments']=len(geometry)//24
 summary['deduplicatedSegments']=sum(l['deduplicatedSegments'] for l in layerdata)
 scene={'transform':{'center':[cx,cy],'scale':scale},'summary':summary,'bounds':bounds,'layers':layerdata,'devices':devices,'texts':text_instances,'candidates':candidates,'views':titles}
 save(ROOT/'web/public/drawing.json',scene);save(ROOT/'analysis/summary.json',summary);save(ROOT/'analysis/devices.json',devices);save(ROOT/'analysis/pipeline_candidates.json',candidates);save(ROOT/'analysis/expanded_texts.json',text_instances)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
