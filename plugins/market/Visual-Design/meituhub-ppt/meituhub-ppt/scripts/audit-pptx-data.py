#!/usr/bin/env python3
"""Read-only chart/workbook checks. Supports simple A1 references, not formula evaluation."""
import io, json, math, posixpath, re, sys, zipfile
from xml.etree import ElementTree as E
C='http://schemas.openxmlformats.org/drawingml/2006/chart'
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def readxml(z,part):
    raw=z.read(part)
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:raise ValueError('Unsupported DTD/entity declaration')
    return E.fromstring(raw)

def rels(z,part):
    parent,base=posixpath.split(part);rpart=posixpath.join(parent,'_rels',base+'.rels')
    if rpart not in z.namelist():return {}
    result={}
    for e in readxml(z,rpart):
        target=e.get('Target','');external=e.get('TargetMode')=='External'
        resolved=target if external else (target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(parent,target)))
        result[e.get('Id')]={'target':resolved,'external':external}
    return result

def workbook(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(i.file_size for i in z.infolist())>256*1024**2:raise ValueError('Workbook exceeds inspection limit')
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(e.itertext()) for e in readxml(z,'xl/sharedStrings.xml').findall('{'+S+'}si')]
        links=rels(z,'xl/workbook.xml');out={}
        for sheet in readxml(z,'xl/workbook.xml').findall('{'+S+'}sheets/{'+S+'}sheet'):
            relation=links[sheet.get('{'+R+'}id')]
            if relation['external']:continue
            cells={}
            for cell in readxml(z,relation['target']).findall('.//{'+S+'}c'):
                val=cell.findtext('{'+S+'}v');kind=cell.get('t')
                if kind=='s' and val is not None:val=shared[int(val)]
                elif kind=='inlineStr':val=''.join(t.text or '' for t in cell.findall('.//{'+S+'}t'))
                cells[cell.get('r')]={'value':val,'type':kind,'formula':cell.find('{'+S+'}f') is not None}
            out[sheet.get('name')]=cells
        return out

def refs(formula):
    match=re.fullmatch(r"(?:'((?:[^']|'')+)'|([^'!]+))!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?",formula or '')
    if not match: return None
    quoted,plain,c1,r1,c2,r2=match.groups();sheet=quoted.replace("''", "'") if quoted else plain
    if '[' in sheet:return None
    c2=c2 or c1;r2=int(r2 or r1);r1=int(r1)
    def col(c):
        n=0
        for char in c:n=n*26+ord(char)-64
        return n
    def name(n):
        v=''
        while n:n,rem=divmod(n-1,26);v=chr(65+rem)+v
        return v
    a,b=col(c1),col(c2)
    if r2<r1 or b<a or (a!=b and r1!=r2) or (r2-r1+1)*(b-a+1)>100000:return None
    return sheet,[f'{name(c)}{r}' for r in range(r1,r2+1) for c in range(a,b+1)]

def equivalent(a,b,numeric):
    if a is None or b is None:return a is b
    if not numeric:return a==b
    try:return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-12)
    except (ValueError,TypeError):return a==b

def audit(file):
    out={'charts':[],'issues':[],'review':[],'compared_cells':0,'render_verified':False,'editability_verified':False,
         'limits':'Simple A1 references only; no formula calculation, chart semantics, rendering or edit verification.'}
    with zipfile.ZipFile(file) as z:
        if sum(i.file_size for i in z.infolist())>1024**3:raise ValueError('Archive exceeds inspection limit')
        for part in z.namelist():
            if not re.fullmatch(r'ppt/charts/chart\d+\.xml',part):continue
            chart=readxml(z,part);out['charts'].append(part);external=chart.find('{'+C+'}externalData')
            def issue(reason,**fields):out['issues'].append(dict(chart=part,reason=reason,**fields))
            def review(reason,**fields):out['review'].append(dict(chart=part,reason=reason,**fields))
            if external is None:issue('No linked data workbook');continue
            relation=rels(z,part).get(external.get('{'+R+'}id'))
            if relation is None:issue('Unresolved data workbook relationship');continue
            if relation['external']:review('External workbook requires separate availability and edit check');continue
            if relation['target'] not in z.namelist():issue('Missing embedded workbook');continue
            try:data=workbook(z.read(relation['target']))
            except (KeyError,ValueError,E.ParseError,zipfile.BadZipFile,IndexError):issue('Unreadable or unsupported embedded workbook');continue
            count=0
            for ref in chart.iter():
                if ref.tag not in {'{'+C+'}numRef','{'+C+'}strRef'}:continue
                formula=ref.findtext('{'+C+'}f');addresses=refs(formula);numeric=ref.tag.endswith('numRef')
                cache=ref.find('{'+C+('}numCache' if numeric else '}strCache'))
                if addresses is None:review('Complex or unsupported chart reference',formula=formula);continue
                sheet,addresses=addresses
                if sheet not in data:issue('Referenced sheet missing',sheet=sheet);continue
                if cache is None:review('No cached data to compare',formula=formula);continue
                cached={int(p.get('idx')):p.findtext('{'+C+'}v') for p in cache.findall('{'+C+'}pt')}
                if any(i<0 or i>=len(addresses) for i in cached):issue('Cache index outside referenced range',formula=formula)
                for i,address in enumerate(addresses):
                    cell=data[sheet].get(address,{'value':None,'formula':False,'type':None})
                    if cell['formula'] or cell['type']=='e':review('Formula/error cell requires recalculation and review',cell=address);continue
                    if not equivalent(cached.get(i),cell['value'],numeric):issue('Chart cache differs from workbook',cell=address,formula=formula,cached=cached.get(i),workbook=cell['value'])
                    out['compared_cells']+=1;count+=1
            if not count:review('No simple reference cells compared')
        if not out['charts']:out['review'].append({'reason':'No standard native charts found; inspect whether charts are required or represented as images/shapes.'})
        if any(n.startswith('ppt/charts/') and n.endswith('.xml') and not re.fullmatch(r'ppt/charts/chart\d+\.xml',n) for n in z.namelist()):
            out['review'].append({'reason':'Extended chart parts require manual review'})
    return out
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: audit-pptx-data.py FILE.pptx')
    result=audit(sys.argv[1]);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(2 if result['issues'] else 0)
