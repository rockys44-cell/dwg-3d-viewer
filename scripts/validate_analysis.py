"""Validate the real converted DXF and exported inventories against each other."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess,math
import numpy as np
import ezdxf
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text())
s=read('analysis/summary.json');scene=read('web/public/drawing.json');entities=read('analysis/entities.json')
doc=ezdxf.readfile(R/'converted.dxf');checks=[]
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append({'name':name,'status':'passed'})
original=next(R.glob('*.dwg'))
check('Original DWG byte-for-byte unchanged from Git HEAD',subprocess.check_output(['git','hash-object','--',original.name],cwd=R)==subprocess.check_output(['git','rev-parse',f'HEAD:{original.name}'],cwd=R))
check('Source SHA256 matches scene provenance',hashlib.sha256(original.read_bytes()).hexdigest()==s['originalSha256'])
check('DXF has expected AutoCAD version and millimetre units',doc.dxfversion=='AC1018' and doc.units==4)
check('Every loaded entitydb record exported once',set(doc.entitydb.keys())=={e['handle'] for e in entities} and len(entities)==len(doc.entitydb))
check('Layer export covers DXF LAYER table',set(l.dxf.name for l in doc.layers)=={l['name'] for l in read('analysis/layers.json')})
check('Block export covers all DXF block definitions',set(b.name for b in doc.blocks)=={b['name'] for b in read('analysis/blocks.json')})
check('Every text record exported',len(read('analysis/texts.json'))==sum(e.dxftype() in {'TEXT','MTEXT','ATTRIB','ATTDEF'} for e in doc.entitydb.values()))
audit=doc.audit();m=doc.modelspace()
check('Auditor completes with no remaining errors',not audit.errors)
check('Repairs are fully logged with code/message',len(audit.fixes)==s['auditFixes'] and all(isinstance(x['code'],int) and x['message'] for x in read('analysis/audit.json')['fixes']))
check('All model-space types match source',dict(Counter(e.dxftype() for e in m))==s['types'])
check('Direct annotations are counted separately',len(m.query('TEXT MTEXT ATTRIB'))==s['directTexts']==647)
devices=read('analysis/devices.json')
check('Every classified device links to an original INSERT',all(doc.entitydb[d['id']].dxftype()=='INSERT' and doc.entitydb[d['id']].dxf.name==d['name'] for d in devices))
check('Device counts reconcile without treating all INSERTs as equipment',len(devices)==s['deviceSymbols']==s['namedDeviceSymbols']+s['modelCodeSymbols'] and len(devices)<len(m.query('INSERT')))
candidates=read('analysis/pipeline_candidates.json')
check('Candidate paths follow stated layer/type rule',len(candidates)==70 and all(doc.entitydb[c['id']].dxf.layer=='1-设备轮廓' and doc.entitydb[c['id']].dxftype() in {'LINE','LWPOLYLINE'} for c in candidates))
check('Unconfirmed pipeline count is not reported as a known zero',s['confirmedPipelines'] is None)
a=np.fromfile(R/'web/public/geometry.bin',dtype='<f4')
check('Binary geometry contains finite XYZ line segment pairs',len(a)>0 and len(a)%6==0 and bool(np.isfinite(a).all()))
check('Layer ranges completely cover binary geometry',sum(l['vertices'] for l in scene['layers'])*3==len(a) and all(l['offset']+l['vertices']<=len(a)//3 for l in scene['layers']))
check('No entity-export failures',not read('analysis/audit.json')['export_failures'])
result={'status':'passed','checks':checks,'count':len(checks),'summary':s}
(R/'logs/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(f'PASS: {len(checks)} real-data validation checks')
