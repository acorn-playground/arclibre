REM SPDX-License-Identifier: Apache-2.0
REM PrintTest: one page through the current printer driver to a file, as an application prints
ON ERROR e$=REPORT$:e%=ERL:SYS "XPDriver_AbortJob",f%:CLOSE#f%:VDU 4:PRINT "PRINTERR ";e$;" at ";e%:END
SYS "PDriver_Info" TO type%,xres%,yres%:PRINT "DRIVER ";type%>>16;" ";xres%;" ";yres%
f%=OPENOUT "adfs::0.$.PrintOut"
SYS "PDriver_SelectJob",f%,"PrintTest" TO old%
DIM r% 16,t% 16,o% 8
r%!0=0:r%!4=0:r%!8=720:r%!12=360
t%!0=&10000:t%!4=0:t%!8=0:t%!12=&10000
o%!0=72000:o%!4=576000
SYS "PDriver_GiveRectangle",1,r%,t%,o%,&FFFFFF00
SYS "PDriver_DrawPage",1,r%,0,0 TO more%
WHILE more%
SYS "ColourTrans_SetGCOL",&00000000,,,0,0:RECTANGLE FILL 0,0,720,180
VDU 5:MOVE 0,300:PRINT "ArcLibre";
SYS "PDriver_GetRectangle",,r% TO more%
ENDWHILE
SYS "PDriver_EndJob",f%
CLOSE#f%:VDU 4
g%=OPENIN "adfs::0.$.PrintOut":PRINT "PRINTED ";EXT#g%:CLOSE#g%
