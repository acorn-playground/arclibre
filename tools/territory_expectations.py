#!/usr/bin/env python3
"""Parse public literal tables independently of AsAsm output. Apache-2.0."""
import json,pathlib,re,struct
from paths import ROOT,REPO
tables={};name=None
for line in (ROOT/'sources/UK/s/Tables').read_text(encoding='latin1').split('\n'):
 if re.fullmatch(r'\w+',line):name=line;tables[name]=[]
 elif name and re.match(r'\s+DCB\s',line):
  content=line.split('DCB',1)[1]
  for t in re.findall(r'"[^\"]*"|&[0-9a-fA-F]+|\d+',content):
   tables[name].extend(t[1:-1].encode('latin1') if t.startswith('"') else [int(t[1:],16) if t.startswith('&') else int(t)])
 elif name and re.match(r'\s+DCD\s+2_',line):tables[name].extend(struct.pack('<I',int(re.search(r'2_([01]+)',line)[1],2)))
props=['ControlTable','UppercaseTable','LowercaseTable','AlphaTable','PunctuationTable','SpaceTable','DigitTable','XDigitTable','AccentedTable','ForwardFlowTable','BackwardFlowTable']
conversion=['ToLowerTable','ToUpperTable','ToControlTable','ToPlainTable','ToValueTable','ToRepresentationTable']
rows=[]
for i,n in enumerate(props):
 assert len(tables[n])==32
 rows.append(dict(name=n,swi=0x43056,property=i,bytes=tables[n]))
for i,n in enumerate(conversion):
 assert len(tables[n])==(16 if i==5 else 256)
 rows.append(dict(name=n,swi=0x43057+i,bytes=tables[n]))
assert tables['ToLowerTable'][65]==97 and tables['ToUpperTable'][233]==201 and tables['ToLowerTable'][92]==92
(ROOT/'artifacts/territory-tables.json').write_text(json.dumps(dict(tables=rows,sort=tables['SortValueTable']),indent=2)+'\n')
