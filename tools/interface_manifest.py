#!/usr/bin/env python3
"""Record individual consumed public interface definitions and their callers.
Apache-2.0. This is provenance evidence, not an automatic semantic proof.
"""
import collections,csv,hashlib,json,pathlib,re
from inspect_image import ROOT,load_symbols
from paths import REPO
symbols=load_symbols();definitions={}
for file in (ROOT/'work/PublicInterfaces').iterdir():
    if file.name=='LICENSE' or not file.is_file():continue
    for number,line in enumerate(file.read_bytes().decode('latin1').splitlines(),1):
        code=line.partition(';')[0]
        m=re.match(r'([A-Za-z_][\w]*)\s+(?:\*|EQU\b|#|SETS\b|SETL\b|SETA\b)',code)
        if m:definitions[m[1]]=dict(header=file.name,line=number,definition=line)
        m=re.match(r'\s*AddError\s+([\w]+)\s*,',code)
        if m:
            for prefix in ['ErrorNumber_','ErrorString_']:definitions[prefix+m[1]]=dict(header=file.name,line=number,definition=line)
uses=collections.defaultdict(set)
for line in (ROOT/'artifacts/symbol-lookups.tsv').read_text().splitlines():
    name,file,number,caller,caller_line=line.split('\t')
    if name not in definitions:continue
    # Exclude own definitions and aliases within the public registration set.
    path=pathlib.Path(file)
    if pathlib.Path(caller).name in {p.name for p in (ROOT/'work/PublicInterfaces').iterdir()}:continue
    if name in ('OldOpt',):continue
    uses[name].add((str(pathlib.Path(caller).relative_to(ROOT)),int(caller_line)))
rows=[]
review={r['name']:r for r in json.loads((REPO/'manifests/public-interface-review.json').read_text())}
for name,locations in sorted(uses.items()):
    if name not in symbols:continue
    symbol=symbols[name]
    rows.append(dict(name=name,**definitions[name],value=symbol['string'] if symbol['tag']==8 else symbol['value'],type=symbol['tag'],references=[dict(file=f,line=n) for f,n in sorted(locations)],revision='403c6dd8bce92d0629634cbf57f68f43b2f30d38'))
    accepted=review[name]
    assert all(rows[-1][key]==accepted[key] for key in ('name','header','value')),name
    rows[-1].update(contract=accepted['contract'],decision=accepted['decision'])
assert {r['name'] for r in rows}==set(review),'consumption changed: review new definitions'
(ROOT/'artifacts/public-interface-consumption.json').write_text(json.dumps(rows,indent=2)+'\n')
with (ROOT/'artifacts/public-interface-consumption.csv').open('w') as stream:
    writer=csv.writer(stream);writer.writerow(['header','name','value','definition_line','reference_count'])
    for r in rows:writer.writerow([r['header'],r['name'],r['value'] if r['type']==8 else hex(r['value']),r['line'],len(r['references'])])
print(collections.Counter(r['header'] for r in rows))
print('Total',len(rows))
