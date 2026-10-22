"""Quick inventory of the converted drawing; read-only."""
from collections import Counter
import ezdxf, json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
doc=ezdxf.readfile(p/'converted.dxf')
audit=doc.audit()
print('VERSION',doc.dxfversion,'ENCODING',doc.encoding,'AUDIT',len(audit.errors),'ERRORS',len(audit.fixes),'FIXES')
print('LAYERS',[(x.dxf.name,x.dxf.color) for x in doc.layers])
print('LAYOUTS',[(x.name,len(x),dict(Counter(e.dxftype() for e in x))) for x in doc.layouts])
print('BLOCKS',[(b.name,len(b)) for b in doc.blocks])
m=doc.modelspace()
print('INSERTS',Counter(e.dxf.name for e in m.query('INSERT')))
print('LAYER TYPES', {l:dict(Counter(e.dxftype() for e in m if e.dxf.layer==l)) for l in {e.dxf.layer for e in m}})
for e in list(m.query('TEXT MTEXT ATTRIB'))[:180]:
 print('TEXT',e.dxf.layer, e.plain_text() if hasattr(e,'plain_text') else e.dxf.text)
