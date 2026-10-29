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
# Makefile for PDriver (Printer driver)
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name         Description
# ----       ----         -----------
# 27-May-94  AMcC         Created.
#

#
# Paths
#
EXP_HDR = <export$dir>

#
# Program specific options:
#
COMPONENT  = PDriver
EXPORTS    = ${EXP_HDR}.PDriver
LDIR       = ${LOCALE}
# MODULE version has extra (standalone) code to install its Messages in Resources:
MODULE     = rm.${COMPONENT}
ROM_MODULE = rom.${COMPONENT}

#
# Generic options:
#
MKDIR   = cdir
AS      = aasm
CP      = copy
RM      = remove
CCFLAGS = -c -depend !Depend -IC:
ASFLAGS = -depend !Depend -Stamp -quit -module
CPFLAGS = ~cfr~v

#
# Generic rules:
#
all: ${MODULE}
	@echo ${COMPONENT}: all built (disc)

rom: ${ROM_MODULE}
	@echo ${COMPONENT}: all built (rom)

export: ${EXPORTS}
	@echo ${COMPONENT}: export complete

install: ${MODULE}
	${CP} ${MODULE} ${INSTDIR}.${COMPONENT} ${CPFLAGS}
	Access ${INSTDIR}.${COMPONENT} lr/r
	@echo ${COMPONENT}: installed (disc)

install_rom: ${ROM_MODULE}
	${CP} ${ROM_MODULE} ${INSTDIR}.${COMPONENT} ${CPFLAGS}
	@echo ${COMPONENT}: installed (rom)

resources:
	${MKDIR} ${RESDIR}.PDrivers
	${CP} ${LDIR}.Messages ${RESDIR}.PDrivers.Messages ${CPFLAGS}
	@echo ${COMPONENT}: resource files will be included in Messages module

clean:
	${RM} ${MODULE}
	${RM} ${ROM_MODULE}
	@echo ${COMPONENT}: cleaned

#
# Include 'StandAlone' code to install/de-install Messages
#
${MODULE}: s.StandAlone
	${AS} ${ASFLAGS} -From s.StandAlone -To $@

#
# Messages will be included in Messages module
#
${ROM_MODULE}: s.PDriver
	${AS} ${ASFLAGS} -From s.PDriver -To $@

${EXP_HDR}.PDriver: hdr.PDriver
	${CP} hdr.PDriver $@ ${CPFLAGS}

# Dynamic dependencies:
