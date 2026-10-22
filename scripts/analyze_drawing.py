"""Lossless entity inventory plus a conservative, reviewable scene projection."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json, math, re
import ezdxf
from ezdxf.lldxf.tagwriter import TagCollector
from ezdxf.disassemble import recursive_decompose
from ezdxf import path as dxfpath

ROOT=Path(__file__).resolve().parents[1]
def json_default(value):
    if isinstance(value,bytes): return {'encoding':'hex','value':value.hex()}
    if hasattr(value,'__iter__'): return list(value)
    return str(value)
def write_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,default=json_default,separators=(',',':')),encoding='utf-8')
def text_value(e):
    if e.dxftype() in {'TEXT','MTEXT','ATTRIB','ATTDEF'}:
        return e.plain_text() if hasattr(e,'plain_text') else e.dxf.get('text','')
    return None

def main():
    doc=ezdxf.readfile(ROOT/'converted.dxf')
    # Extract before audit, since ezdxf's auditor may repair the in-memory document.
    entities=[]; failures=[]
    for handle,e in doc.entitydb.items():
        if not e.is_alive: continue
        try:
            collector=TagCollector(dxfversion=doc.dxfversion)
            e.export_dxf(collector)
            entities.append({'handle':handle,'type':e.dxftype(),'attributes':e.dxf.all_existing_dxf_attribs(),'text':text_value(e),'tags':[(t.code,t.value) for t in collector.tags]})
        except Exception as exc:
            failures.append({'handle':handle,'type':e.dxftype(),'error':str(exc)})
    layers=[{'name':l.dxf.name,'attributes':l.dxf.all_existing_dxf_attribs(),'off':l.is_off(),'frozen':l.is_frozen()} for l in doc.layers]
    blocks=[{'name':b.name,'base_point':list(b.block.dxf.base_point),'entities':[e.dxf.handle for e in b],'types':dict(Counter(e.dxftype() for e in b))} for b in doc.blocks]
    layouts=[{'name':l.name,'entities':[e.dxf.handle for e in l],'types':dict(Counter(e.dxftype() for e in l))} for l in doc.layouts]
    write_json(ROOT/'analysis/entities.json',entities)
    write_json(ROOT/'analysis/layers.json',layers)
    write_json(ROOT/'analysis/blocks.json',blocks)
    write_json(ROOT/'analysis/layouts.json',layouts)
    texts=[{'handle':e['handle'],'type':e['type'],'text':e['text'],'layer':e['attributes'].get('layer'),'position':e['attributes'].get('insert')} for e in entities if e['text'] is not None]
    write_json(ROOT/'analysis/texts.json',texts)
    audit=doc.audit()
    write_json(ROOT/'analysis/audit.json',{'errors':[{'code':int(e.code),'message':e.message,'handle':e.entity.dxf.get('handle') if e.entity is not None else None} for e in audit.errors],'fixes':[{'code':int(e.code),'message':e.message,'handle':e.entity.dxf.get('handle') if e.entity is not None else None} for e in audit.fixes],'export_failures':failures})
    print(json.dumps({'entities':len(entities),'layers':len(layers),'blocks':len(blocks),'texts':len(texts),'audit_errors':len(audit.errors),'audit_fixes':len(audit.fixes),'export_failures':len(failures)},ensure_ascii=False))

if __name__=='__main__': main()
