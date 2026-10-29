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
# Makefile for PDModules (Printer Driver Modules - Dot Matrix & PostScript)
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name         Description
# ----       ----         -----------
# 04-Jul-94  AMcC         Created.
#

#
# Program specific options:
#
COMPONENT = PDModules
TARGETS   = rm.PDriverDP \
            rm.PDriverPS

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
all: ${TARGETS}
	@echo ${COMPONENT}: all built (disc)

rom: ${TARGETS}
	@echo ${COMPONENT}: all built (rom)

export: ${EXPORTS}
	@echo ${COMPONENT}: export complete

install: ${TARGETS}
	${CP} rm.PDriverDP ${INSTDIR}.PDriverDP ${CPFLAGS}
	${CP} rm.PDriverPS ${INSTDIR}.PDriverPS ${CPFLAGS}
	Access ${INSTDIR}.PDriverDP lr/r
	Access ${INSTDIR}.PDriverPS lr/r
	@echo ${COMPONENT}: installed (disc)

install_rom: ${TARGETS}
	${CP} rm.PDriverDP ${INSTDIR}.PDriverDP ${CPFLAGS}
	${CP} rm.PDriverPS ${INSTDIR}.PDriverPS ${CPFLAGS}
	@echo ${COMPONENT}: installed (rom)

clean:
	${RM} rm.PDriverDP
	${RM} rm.PDriverPS
	@echo ${COMPONENT}: cleaned

rm.PDriverDP: s.PrinterDP
	${AS} ${ASFLAGS} -To $@ -From s.PrinterDP

rm.PDriverPS: s.PrinterPS
	${AS} ${ASFLAGS} -To $@ -From s.PrinterPS

# Dynamic dependencies:
