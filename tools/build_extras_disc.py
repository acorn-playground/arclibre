#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the 2 MB ROM's one distributable floppy (arclibre-extras.adf).

The 2 MB ROM leaves DOSFS, !Alarm and printing (!Printers and PrintDefs) on
disc. Each has its own built and gated floppy (tools/build_dosfs.py,
build_alarm_disc.py, build_printing_disc.py); this disc holds exactly their
files, read back from those images, with one ReadMe for all three
(src/ArcLibre/extras/ReadMe) in place of theirs. File data, types and
attributes are unchanged; directories and datestamps are this disc's. It
also holds !System and !Scrap (tools/system_apps.py), which RISC OS 3.11
users got on the Applications disc, for either ROM: copy them to a hard
disc.
"""
import datetime,hashlib,json,sys
from paths import REPO,SRC
from adfs_image import File,image
import system_apps
sys.path.insert(0,str(REPO/'tests'))
from verify_filer_disc import read_directory
ROOT=REPO/'build/extras-disc';ROOT.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
SOURCES={'dosfs':'build/dosfs','alarm':'build/alarm-disc','printing':'build/printing-disc'}
IMAGES={'dosfs':'arclibre-dosfs.adf','alarm':'arclibre-alarm.adf','printing':'arclibre-printing.adf'}
def tree(b,address):
 out={}
 for name,e in read_directory(b,address).items():
  if e['attributes']&8:out[name]=tree(b,e['address'])
  else:
   assert e['load']>>20==0xfff,name
   out[name]=File(b[e['address']*256:e['address']*256+e['length']],(e['load']>>8)&0xfff,e['attributes'])
 return out
def files(node,prefix='$'):
 for name,v in sorted(node.items()):
  if isinstance(v,dict):yield from files(v,prefix+'.'+name)
  else:yield prefix+'.'+name,v
combined={};sources={}
for part,folder in SOURCES.items():
 b=(REPO/folder/IMAGES[part]).read_bytes();record=json.loads((REPO/folder/'disc.json').read_text())
 assert record.get('status','PASS')=='PASS' and record['sha256']==sha(b),part
 t=tree(b,4);t.pop('ReadMe')
 assert not set(t)&set(combined),(part,set(t)&set(combined))
 combined.update(t);sources[part]=dict(image=f'{folder}/{IMAGES[part]}',sha256=sha(b),entries=sorted(t))
system=system_apps.tree();assert not set(system)&set(combined);combined.update(system)
readme=(SRC/'ArcLibre/extras/ReadMe').read_bytes();combined['ReadMe']=File(readme,0xfff,0x11)
release=json.loads((REPO/'manifests/release.json').read_text())
stamp=int((datetime.datetime.strptime(release['date'],'%d %b %Y')-datetime.datetime(1900,1,1)).total_seconds())*100
disc,rows=image(combined,'ArcLibre',b'EX',stamp)
# Read the result back: every file is its source disc's, byte for byte.
back=dict(files(tree(disc,4)))
assert back==dict(files(combined)),'read-back differs'
for r in rows:r['sha256']=sha(back[r['path']].data)
(ROOT/'arclibre-extras.adf').write_bytes(disc)
# The gate's negative control: the same disc without !Printers, !System and !Scrap.
negative,_=image({k:v for k,v in combined.items() if k not in ('!Printers','!System','!Scrap')},'ArcLibre',b'EX',stamp)
(ROOT/'negative-without-printers.adf').write_bytes(negative)
(ROOT/'disc.json').write_text(json.dumps(dict(status='PASS',image='build/extras-disc/arclibre-extras.adf',sha256=sha(disc),bytes=len(disc),format='ADFS D (old map) 800K',disc_name='ArcLibre',
 version=release['version'],sources=sources,files=rows,free_bytes=int.from_bytes(disc[256:259],'little')*256,negative_without_printers_sha256=sha(negative),system_applications=sorted(system)),indent=2)+'\n')
print('floppy:',ROOT/'arclibre-extras.adf',sha(disc),int.from_bytes(disc[256:259],'little')*256,'bytes free',flush=True)
