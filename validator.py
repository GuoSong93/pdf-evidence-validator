# Deterministic evidence checks; candidates are untrusted.
from __future__ import annotations
import io
import argparse
import hashlib
import html
import json
import re
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROW=re.compile(r'^(BASE|UPSIDE)\s*\|\s*(\d+)\s*\|\s*(\d+\.\d{2})\s*\|\s*(\d+\.\d{2})$')
SPEC={'principal':'1000.00','currency':'USD','scenario':'BASE','years':[1,2,3,4,5], 'template':'synthetic-v1'}

def extract_source(path: Path,data=None):
    data=path.read_bytes() if data is None else data
    if len(data)>10*1024*1024:raise ValueError('PDF exceeds 10 MiB demo limit')
    reader=PdfReader(io.BytesIO(data))
    if reader.is_encrypted:raise ValueError('encrypted PDF not supported')
    if len(reader.pages)>20:raise ValueError('PDF exceeds 20 pages demo limit')
    return [{'page':page_no,'line':line_no,'text':text.strip()}
            for page_no,page in enumerate(reader.pages,1)
            for line_no,text in enumerate((page.extract_text() or '').splitlines(),1) if text.strip()]

def candidate_rows(source):
    rows=[]
    for line in source:
        match=ROW.fullmatch(line['text'])
        if match:
            scenario,year,value,ratio=match.groups()
            rows.append({'scenario':scenario,'year':int(year),'value':value,'ratio':ratio,
                         'evidence':dict(line)})
    return rows

def validate(path: Path,candidates=None):
    data=path.read_bytes()
    source=extract_source(path,data)
    if not any(line['text']=='Principal: 1000.00 USD | Scenario: BASE | Years: 1-5' for line in source):
        raise ValueError('unsupported template: required principal/currency/scenario header missing')
    extracted=candidate_rows(source)
    rows=extracted if candidates is None else candidates
    if not isinstance(rows,list) or len(rows)>1000:raise ValueError('candidate JSON must be an array of at most 1000 rows')
    lookup={(x['page'],x['line']):x['text'] for x in source}
    errors=[];checked=[];seen=[];covered=[]
    for i,row in enumerate(rows):
        problems=[]
        try:
            if not isinstance(row,dict):raise ValueError('candidate must be an object')
            e=row['evidence']
            if not isinstance(e,dict):raise ValueError('evidence must be an object')
            actual=lookup.get((e['page'],e['line']))
            if actual is None or actual!=e['text']:problems.append('EVIDENCE_NOT_FOUND')
            match=ROW.fullmatch(actual or '')
            if match is None:problems.append('SOURCE_NOT_A_DATA_ROW')
            else:
                scenario,year,value,ratio=match.groups()
                if (row['scenario'],str(row['year']),str(row['value']),str(row['ratio']))!=(scenario,year,value,ratio):
                    problems.append('FIELDS_DO_NOT_MATCH_SOURCE')
                covered.append((e['page'],e['line']))
            if type(row['year']) is not int:raise ValueError('year must be integer')
            seen.append(row['year'])
            if row['scenario']!=SPEC['scenario']:problems.append('MIXED_SCENARIO')
            if not all(isinstance(row[k],str) and re.fullmatch(r'\d+\.\d{2}',row[k]) for k in ('value','ratio')):
                raise ValueError('money and ratio must be two-decimal strings')
            value=Decimal(row['value']);ratio=Decimal(row['ratio'])
            expected=(Decimal(SPEC['principal'])*ratio/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            if value!=expected:problems.append(f'ARITHMETIC_MISMATCH: expected {expected}, got {value}')
        except (KeyError,TypeError,ValueError,InvalidOperation) as exc:
            problems.append('INVALID_CANDIDATE: '+str(exc))
        checked.append({'candidate':row,'valid':not problems,'errors':problems})
        errors.extend(f'row {i+1}: {p}' for p in problems)
    if sorted(seen)!=SPEC['years']:errors.append('YEAR_COVERAGE: expected exactly 1,2,3,4,5')
    # A plausible but incomplete candidate set must not hide contradictory source rows.
    source_keys=[(r['evidence']['page'],r['evidence']['line']) for r in extracted]
    if sorted(covered)!=sorted(source_keys):errors.append('SOURCE_COVERAGE: each source data row must be used exactly once')
    if not extracted:errors.append('NO_TEXT_ROWS: scanned documents require OCR (not implemented)')
    return {'schemaVersion':1,'document':path.name,'sha256':hashlib.sha256(data).hexdigest(),
            'provider':'deterministic-template' if candidates is None else 'offline-candidate-fixture',
            'spec':SPEC,'valid':not errors,'reviewStatus':'PENDING_REVIEW' if not errors else 'REJECTED',
            'errors':errors,'rows':checked,'source':source}

def approve(result,path:Path,reviewer:str):
    if not result['valid']:raise ValueError('cannot approve failed validation')
    if not reviewer.strip():raise ValueError('reviewer name required')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=result['sha256']:raise ValueError('document changed since validation')
    result['reviewStatus']='APPROVED';result['reviewer']=reviewer
    result['reviewedAt']=datetime.now(timezone.utc).isoformat()
    return result

def write_report(result,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    esc=lambda x:html.escape(str(x))
    cards=''.join('<section><h3>Candidate '+str(i+1)+'</h3><pre>'+esc(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></section>' for i,r in enumerate(result['rows']))
    source='\n'.join(f"p{x['page']}:L{x['line']}  {x['text']}" for x in result['source'])
    report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PDF evidence review</title><style>body{font:15px/1.6 system-ui;background:#eef2f6;color:#183046;margin:0}main{max-width:1100px;margin:40px auto;padding:24px}header{background:#142d45;color:white;border-radius:18px;padding:28px}section{background:white;padding:22px;margin:16px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{margin:5px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style><main><header><small>PORTFOLIO / 03 · EVIDENCE LAB</small><h1>PDF evidence review</h1><p>'''+esc(result['reviewStatus'])+' · '+esc(result['document'])+'</p></header><section><strong>SHA-256</strong><pre>'+esc(result['sha256'])+'</pre><p>Provider: '+esc(result['provider'])+'</p><p>Validation success is pending human review until explicitly approved.</p><pre>'+esc('\n'.join(result['errors']) or 'All deterministic checks passed.')+'</pre></section><div class="grid"><div>'+cards+'</div><section><h2>Extracted source (page / line)</h2><pre>'+esc(source)+'</pre></section></div></main></html>'
    (out/'review.html').write_text(report,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf',type=Path);parser.add_argument('--candidates',type=Path)
    parser.add_argument('--out',type=Path,default=Path('artifacts/review'))
    parser.add_argument('--confirm',metavar='REVIEWER')
    args=parser.parse_args()
    try:
        candidates=json.loads(args.candidates.read_text(encoding='utf-8')) if args.candidates else None
        result=validate(args.pdf,candidates)
        if args.confirm:approve(result,args.pdf,args.confirm)
        write_report(result,args.out)
        print(json.dumps({k:result[k] for k in ('valid','reviewStatus','sha256','errors')},indent=2))
        return 0 if result['valid'] else 2
    except (ValueError,OSError,PdfReadError) as exc:
        print('ERROR:',exc);return 2
if __name__=='__main__':raise SystemExit(main())
