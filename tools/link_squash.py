#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Link Squash at its actual ROM address and independently audit its ARM2 code."""
import hashlib,json,re,subprocess
from paths import REPO
from verify_c_desktop import verify
ROOT=REPO/'build/squash-runtime'
def link(base):
 objects=[REPO/p for p in json.loads((ROOT/'inputs.json').read_text())['objects']]
 with (ROOT/'Squash-link.log').open('w') as f:
  subprocess.run([str(REPO/'build/c-toolchain-release/install/bin/drlink'),'-bin','-base',hex(base),'-map','-symbols',str(ROOT/'Squash.symbols'),'-output',str(ROOT/'Squash.bin'),*[str(p) for p in reversed(objects)]],stdout=f,stderr=subprocess.STDOUT,check=True)
 data=(ROOT/'Squash.bin').read_bytes();row=dict(component='Squash',base=base,length=len(data),sha256=hashlib.sha256(data).hexdigest(),link_log='Squash-link.log')
 (ROOT/'linked.json').write_text(json.dumps(dict(modules=[row]),indent=2)+'\n')
 proof=verify(ROOT);assert proof[0]['software_fpa_instructions']==0
 symbols={name:int(value,16) for value,name in re.findall(r'\b([0-9a-f]{7,8})\s+(\S+)',(ROOT/'Squash.symbols').read_text())}
 start,end=symbols['Image$$RW$$Base'],symbols['Image$$RW$$Limit']
 assert symbols['MagicOffset']==symbols['hdr$statics']==start and (end-start)%4==0
 contract=dict(status='PASS',rom_base=base,template_offset=start-base,private_rma_bytes=end-start,static_base_bias=536,
  fields={n:symbols[n]-start for n in ['MagicOffset','Priv_Wsp','File_Open','MsgTrans_FileData','glob_staticbase']},
  template_sha256=hashlib.sha256(data[start-base:end-base]).hexdigest(),source='Original assembler fields and actual linked C RW template; no invented fixed kernel workspace')
 (ROOT/'workspace-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 (ROOT/'modules/Squash/symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')
 return row
if __name__=='__main__':
 import sys
 print(json.dumps(link(int(sys.argv[1],0)),indent=2))
