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
# Makefile for BASIC
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name   Description
# ----       ----   -----------
# 08-Jun-94  AMcC   Created.
# 08-Nov-94  AMcC   Updated to install BASIC64 (non ROM)

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
RM      = remove
CCFLAGS = -c -depend !Depend -IC:
ASFLAGS = -depend !Depend -Stamp -quit -module -To $@ -From
CPFLAGS = ~cfr~v

TOKENISE = tokenise
TOKENS   = Hdr:Tokens

#
# Program specific options:
#
COMPONENT = BASIC
EXPORTS   = ${EXP_HDR}.BASICTrans
TARGETS   = rm.BASIC105 \
            rm.BASICTrans

#
# Generic rules:
#
all: rm.BASIC64
	@echo ${COMPONENT}: BASIC64 module built

rom: ${TARGETS}
	@echo ${COMPONENT}: rom module built

export: ${EXPORTS}
	@echo ${COMPONENT}: export complete

install: rm.BASIC64
	${CP} rm.BASIC64 ${INSTDIR}.BASIC64 ${CPFLAGS}
	Access ${INSTDIR}.BASIC64 WR/r
	@echo ${COMPONENT}: BASIC64 installed (Disc)

install_rom: ${TARGETS}
	${CP} rm.BASIC105 ${INSTDIR}.BASIC105 ${CPFLAGS}
	${CP} rm.BASICTrans ${INSTDIR}.BASICTrans ${CPFLAGS}
	@echo ${COMPONENT}: rom module installed

clean:
	${RM} rm.BASIC64
	${RM} rm.BASIC105
	${RM} rm.BASICTrans
	@echo ${COMPONENT}: cleaned

resources:
	${MKDIR} ${RESDIR}.${COMPONENT}
	${CP} Resources.${LOCALE}.Messages  ${RESDIR}.${COMPONENT}.Messages  ${CPFLAGS}
	@echo ${COMPONENT}: resource files copied

rm.BASIC105: ModuleAB
	${AS} ${ASFLAGS} ModuleAB

rm.BASIC64: ModuleAB64
	${AS} ${ASFLAGS} ModuleAB64

rm.BASICTrans: TransSrc
	${AS} ${ASFLAGS} TransSrc

${EXP_HDR}.BASICTrans: hdr.BASICTrans
	${CP} hdr.BASICTrans $@ ${CPFLAGS}

# Dynamic dependencies:
