#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Import and pin the original expansion card, serial and parallel sources (maintainer tool).

Podule, SerialDeviceDriver, SerialDeviceSupport and ParallelDeviceDriver, at
their cleaned-3.60 import revisions; modes as tools/import_network.py. Normal
builds use src/, manifests/hardware-inputs.json and patches/hardware.
"""
import sys
import import_network
COMPONENTS={
 'Podule':('HWSupport/Podule','b33cb3fa32376b243c94d3870b33697f30cd9a70',
  ['LICENSE','Makefile','HelpTexts','Time+Date','Resources/UK/Messages','hdr/Podule','s/GetAll','s/Module','s/Interface','s/Commands','s/Errors','s/ROMExtend','s/MsgCode']),
 'Serial':('HWSupport/Serial','4d0e504f000ea706a6d07c69e35d82380b02c797',
  ['LICENSE','Makefile','Version','Resources/UK/Messages','hdr/RS423','hdr/Serial','s/Serial','s/Macros','s/Errors','s/Init','s/Common','s/Serial6551','s/Serial710','s/ResFiles']),
 'SerialSpt':('HWSupport/SerialSpt','36b69cb232a28bd975545ea7eff3a75132d0eef0',
  ['LICENSE','Makefile','Version','s/SerialSpt','s/Macros','s/Errors']),
 'Parallel':('HWSupport/Parallel','f9e3bcbbcc5849d4965077d5abafdd99db5954f0',
  ['LICENSE','Makefile','Version','Resources/UK/Messages','hdr/Parallel','s/Parallel','s/Errors','s/Common','s/IOC','s/IOEB','s/FastCent','s/ResFiles']),
}
if __name__=='__main__':import_network.main(sys.argv[1] if len(sys.argv)>1 else 'check',COMPONENTS,'hardware-inputs.json','hardware')
