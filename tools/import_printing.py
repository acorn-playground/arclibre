#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Import and pin the original printing sources for the printing disc (maintainer tool).

PDriver, PDriverDP and PDriverPS (PDModules), PDumperSupport, PDumperDM and
PDumperLJ (PDumpers) at their cleaned-3.60 import revisions, !Printers with
its dot-matrix, LaserJet and PostScript classes, three printer definitions,
and the printer registration headers from Programmer/HdrSrc (and MakePSFont's,
which PDriverPS reads); modes as tools/import_network.py. Normal builds use
src/, manifests/printing-inputs.json and patches/printing.
"""
import sys
import import_network
CORE=['ColTrans','Colour','Constants','Device','Draw','Error','FontSWI','Header','Intercept','JPEGSWI','JobManager','MsgCode','OSByte','PDriver','SWIs','Sprite','Vdu5','Workspace','Wrch']
DP=['Colour','Configure','Constants','Draw','Font','GlobalWS','JPEG','JobWS','Macros','ManageJob','MiscOp','PageBox','Picture','Plot','Private','Private2','ScreenDump','Sprite','TranSprite','Vdu5']
GENERIC=['24Bit','AbortJob','BranchCode','ColourSet','EndPage','Header','Macros','MiscOp','OutputDump','SendExtra','SetDriver','StartJob']
PS=['Colour','Configure','Constants','Draw','Font','GlobalWS','JPEG','JobWS','Macros','ManageJob','MiscOp','PageBox','Picture','Plot','Private','ScreenDump','Sprite','TranSprite','Vdu5']
LJ=['24Bit','AbortJob','BranchCode','ColourSet','EndPage','Header','Macros','MiscOp','OutputDump','SetDriver','StartJob','StartPage','Version','Workspace']
DM=['24Bit','AbortJob','BranchCode','ColourSet','DumpIX','DumpJX','EndPage','Header','Macros','MiscOp','OutputDump','SetDriver','StartJob','StartPage','Version','Workspace']
COMPONENTS={
 'PDriver':('Printing/Modules/PDriver','de4185f8a1dcdb7ce57ef9e6a7fbad8a4c8a2d71',
  ['LICENSE','Makefile','Version','Resources/UK/Messages','hdr/PDriver','s/PDriver','s/MsgCode','s/StandAlone']),
 'PDModules':('Printing/Modules/PDModules','d5db212e15135c64e3d7fc215d4a31ab93a6585d',
  ['LICENSE','Makefile','Version','s/PrinterDP']+['s/Core/'+f for f in CORE]+['s/PDriverDP/'+f for f in DP]+['s/PrinterPS']+['s/PDriverPS/'+f for f in PS]),
 'PDumperSpt':('Printing/Modules/PDumperSpt','0748768b18f559be1731fbc8a6be231bdbf5c4f3',
  ['LICENSE','Makefile','Version']+['s/'+f for f in ['CTrans','Colour','Error','FullRGB','Halftone','Manipulate','MsgCode','PDumperSpt']]),
 'PDumpers':('Printing/PDumpers','45c309a19b63e8137ab401fd22c127658668af11',
  ['LICENSE','Makefile','Version','hdr/PDumper','PDumperDM/Makefile']+['Generic/s/'+f for f in GENERIC]+['PDumperDM/s/'+f for f in DM]+['PDumperLJ/Makefile']+['PDumperLJ/s/'+f for f in LJ]),
 # PDriverPS reads Hdr:MakePSFont for its one (error-tolerant) MakePSFont call.
 'MakePSFont':('Printing/Modules/MakePSFont','3a303276d3fc5ec6c8d7294a7f9ba63d8874250a',['LICENSE','hdr/MakePSFont']),
 'HdrSrc':('Programmer/HdrSrc','403c6dd8bce92d0629634cbf57f68f43b2f30d38',['hdr/PDriverReg','hdr/PDumperReg']),
 # !Printers: the disc version's sources and its three printer classes, dot
 # matrix (dp), LaserJet (lj) and PostScript (ps), as in RISC OS 3.11.
 'PrinterManager':('Printing/PrinterManager','8b91b0070ad814d5fd35c078c3dfa0c8391bcda3',
  ['LICENSE','Makefile','sources/RunImage','sources/SupportDP','sources/SuppSrc','sources/Export','sources/Sparrow','h/Values','h/Trace','h/ConstVals','s/SetPrint','crunch/RunImage,ffe','crunch/SupportDP,ffe',
   'UK/!Help','UK/!Run,feb','UK/!Sprites,ff9','UK/!Sprites22,ff9','UK/!Sprites23,ff9','UK/Messages','UK/PaperRO,fc6','UK/Templates,fec','UK/Template3D,fec',
   'UK/dp/Resources/Messages','UK/dp/Resources/Templates,fec','UK/dp/Resources/Template3D,fec',
   'DataFiles/!Boot,feb','DataFiles/Palettes/0','DataFiles/Palettes/1','DataFiles/Palettes/2','DataFiles/dp/PrData,fc6','DataFiles/dp/Template,fc6',
   'DataFiles/dp/Resources/!Sprites,ff9','DataFiles/dp/Resources/!Sprites22,ff9','DataFiles/dp/Resources/!Sprites23,ff9','DataFiles/dp/Resources/PaperRO,fc6']
  +[x for c in ['lj','ps'] for x in ['sources/Support'+c.upper(),'crunch/Support'+c.upper()+',ffe','UK/%s/Resources/Messages'%c,'UK/%s/Resources/Templates,fec'%c,'UK/%s/Resources/Template3D,fec'%c,
   'DataFiles/%s/PrData,fc6'%c,'DataFiles/%s/Template,fc6'%c]+['DataFiles/%s/Resources/%s'%(c,f) for f in ['!Sprites,ff9','!Sprites22,ff9','!Sprites23,ff9','PaperRO,fc6']]]
  # The PostScript class's font encodings and prologues (installed as ps.PSFiles).
  +['DataFiles/ps/Adobe/Special','DataFiles/ps/Adobe/Standard']+['prolog/'+f for f in ['OldLatin1','PSepilog','PSprolog','PSprolog2','PStprolog','Selwyn','Sidney']]),
 # An Epson FX-80 printer definition, for the gate and as an example: the
 # tagged (cl:) form !Printers 1.46 reads, as restored to PrintDefs in 2003
 # (the 1996 PrintDefs files are an older, NCOS format). Squash-compressed.
 # The same for a PostScript printer (the original Apple LaserWriter) and a
 # LaserJet (the HP LaserJet II).
 'PrintDefs':('Printing/PrintDefs','763f4cabce7972b2ee10f5a2d23574d620600553',['LICENSE','Resources/NonSTB/Epson/FX-80,fc6','Resources/NonSTB/Apple/LW,fc6','Resources/NonSTB/HP/LasJet-II,fc6']),
}
if __name__=='__main__':import_network.main(sys.argv[1] if len(sys.argv)>1 else 'check',COMPONENTS,'printing-inputs.json','printing')
