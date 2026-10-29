#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Record original module-private RAM filing layouts and shared SWI numbers."""
import hashlib,json
from paths import REPO

def write_contract(root):
 kernel=json.loads((REPO/'build/desktop-defaults/artifacts/symbols.json').read_text())
 fields={
  'RamFS':['BufferStart','BufferSize','ScatterPair','FileCorePrivate','message_file_block','message_file_open','WorkSize'],
  'RAMFSFiler':['mytaskhandle','iconbaricon','stackbot','stacktop','RAMFSFiler_WorkspaceSize'],
  'Free':['mytaskhandle','windows_ptr','poll_word','fs_list','stackbot','stacktop','max_running_work']}
 sizes={'RamFS':('WorkSize',40),'RAMFSFiler':('RAMFSFiler_WorkspaceSize',700),'Free':('max_running_work',2160)}
 modules={};swis={}
 for component,names in fields.items():
  symbols=json.loads((root/'modules'/component/'symbols.json').read_text())
  size,expected=sizes[component];assert symbols[size]==expected
  offsets={name:symbols[name] for name in names}
  assert all(0<=value<=expected for value in offsets.values())
  modules[component]=dict(private_workspace_bytes=expected,offsets=offsets)
  for name in ['OS_ChangeDynamicArea','OS_ReadDynamicArea','OS_ReadRAMFsLimits']:
   assert symbols[name]==kernel[name],(component,name,symbols[name],kernel[name])
   swis[name]=symbols[name]
 report=dict(status='PASS',scope='Original RMA-private module offsets and matching public SWI numbers; runtime mappings are checked by tests/run_ram_filing.py',
  kernel_sha256=hashlib.sha256((REPO/'build/desktop-defaults/artifacts/kernel.bin').read_bytes()).hexdigest(),modules=modules,public_swis=swis,
  ram_dynamic_area=5,runtime_contract='OS_ReadDynamicArea(5) base/size must equal OS_ReadRAMFsLimits start/end, across actual resize operations')
 (root/'workspace-contract.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

if __name__=='__main__':write_contract(REPO/'build/ram-filing')
