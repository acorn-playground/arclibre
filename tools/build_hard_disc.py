#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Opt-in original A440 ST506 ADFS, retaining the exact baseline build."""
import hashlib,json,os,shutil,subprocess,sys
from paths import REPO,SRC,HOST
from module_image import load_aof
root=REPO/'build/hard-disc'; work=root/'work/ADFS';out=root/'artifacts/modules/ADFS'
if work.exists():shutil.rmtree(work)
shutil.copytree(SRC/'ADFS',work);out.mkdir(parents=True,exist_ok=True)
headers=REPO/'build/desktop-baseline/build/Hdr'
env=dict(os.environ,HDR_PATH=str(headers),MACHINE='A440',IMAGESIZE='2048K')
subprocess.run([str(HOST/'bin/tokenise'),str(headers/'Tokens'),'HelpText','s/TokenHelp'],cwd=work,env=env,check=True)
hashes=[]
for attempt in ['normal-1','normal-2','observer']:
 observer=attempt=='observer';e=dict(env)
 if observer:
  for n in ['emissions.tsv','symbols.tsv']:(out/n).unlink(missing_ok=True)
  e.update(ASASM_TRACE=str(out/'emissions.tsv'),ASASM_SYMBOLS=str(out/'symbols.tsv'))
 cmd=[HOST/'bin'/('asasm-observer' if observer else 'asasm'),'-PreDefine=ArcLibreST506 SETL {TRUE}','-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof','s/ADFS',out/'module.aof']
 with (out/(attempt+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=work,env=e,stdout=f,stderr=subprocess.STDOUT,check=True)
 hashes.append(hashlib.sha256((out/'module.aof').read_bytes()).hexdigest())
assert len(set(hashes))==1
b=load_aof(out/'module.aof')['data'];(out/'module.bin').write_bytes(b)
subprocess.run([sys.executable,str(REPO/'tools/audit_modules.py')],env=dict(os.environ,ARCLIBRE_OUTPUT=str(root)),check=True)
(root/'result.json').write_text(json.dumps(dict(status='PASS',sha256=hashlib.sha256(b).hexdigest(),aof_hashes=hashes,bytes=len(b)),indent=2)+'\n')
