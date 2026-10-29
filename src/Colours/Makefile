# Copyright 1996 Acorn Computers Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Makefile for Colour Translation module
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name         Description
# ----       ----         -----------
# 25-May-94  AMcC         Created.
# 10-Mar-95  GPS          Changed method for building ROM tables.
#

#
# Paths
#
EXP_HDR = <export$dir>

#
# Generic options:
#
MKDIR   = cdir
AS      = aasm
CP      = copy
CC      = cc
RM      = remove
CCFLAGS = -c -depend !Depend -IC:
ASFLAGS = -depend !Depend -Stamp -quit -module -To $@ -From
CPFLAGS = ~cfr~v
CLIB    = CLIB:o.stubs
#
# Program specific options:
#
COMPONENT = Colours
SOURCE    = MakeNew
TARGET    = rm.Colours
EXPORTS   = ${EXP_HDR}.ColourTran

#
# Generic rules:
#
rom: ${TARGET}
	@echo ${COMPONENT}: rom module built

export: ${EXPORTS}
	@echo ${COMPONENT}: export complete

install_rom: ${TARGET}
	${CP} ${TARGET} ${INSTDIR}.${COMPONENT} ${CPFLAGS}
	@echo ${COMPONENT}: rom module installed

clean:
	${RM} ${TARGET}
	@echo ${COMPONENT}: cleaned

resources: Palettes.8desktop
	${MKDIR} ${RESDIR}.${COMPONENT}
	${CP} Resources.${LOCALE}.Messages  ${RESDIR}.${COMPONENT}.Messages ${CPFLAGS}
	${CP} Palettes ${RESDIR}.${COMPONENT}.Palettes ${CPFLAGS}
	${CP} Tables   ${RESDIR}.${COMPONENT}.Tables   ${CPFLAGS}
	@echo ${COMPONENT}: resource files copied

${TARGET}: ${SOURCE}
	${AS} ${ASFLAGS} ${SOURCE}

${EXP_HDR}.ColourTran: hdr.ColourTran
	${CP} hdr.ColourTran $@ ${CPFLAGS}

Colours200: MakeOld
	${AS} ${ASFLAGS} MakeOld
	@echo ${COMPONENT}: Colours200 built

MkTables.o.maketables: MkTables.c.maketables
	${CC} $(ccflags) -o $@ MkTables.c.maketables

MkTables.maketables:   MkTables.o.maketables ${CLIB} 
	link $(linkflags) -o $@ MkTables.o.maketables ${CLIB}

Palettes.8desktop: MkTables.maketables rm.Colours
	rmload rm.Colours
	MkTables.maketables @  
	settype Tables.8greys text
	settype Tables.4greys text
	MkTables.dosqueeze
	
# Dynamic dependencies:
