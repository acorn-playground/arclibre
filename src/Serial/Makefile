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
# Makefile for Serial
#
# ***********************************
# ***    C h a n g e   L i s t    ***
# ***********************************
# Date       Name         Description
# ----       ----         -----------
# 25-May-94  AMcC         Created.
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
RM      = remove
CCFLAGS = -c -depend !Depend -IC:
ASFLAGS = -depend !Depend -Stamp -quit -module -To $@ -From
CPFLAGS = ~cfr~v

#
# Program specific options:
#
COMPONENT  = Serial
SOURCE     = s.Serial
TARGET     = rm.Serial
TARGETSA   = rm.SerialSA
RESOURCES  = Resources.${LOCALE}.Messages
EXPORTS    = ${EXP_HDR}.Serial \
             ${EXP_HDR}.RS423

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
	${RM} ${TARGETSA}
	@echo ${COMPONENT}: cleaned

resources:
	${MKDIR} ${RESDIR}.${COMPONENT}
	${CP} Resources.${LOCALE}.Messages  ${RESDIR}.${COMPONENT}.Messages  ${CPFLAGS}
	@echo ${COMPONENT}: resource files copied

${TARGET}: ${SOURCE}
	${AS} ${ASFLAGS} ${SOURCE}

#
# Exported headers
#
${EXP_HDR}.Serial: hdr.Serial
	${CP} hdr.Serial $@ ${CPFLAGS}

${EXP_HDR}.RS423: hdr.RS423
	${CP} hdr.RS423 $@ ${CPFLAGS}

#
# Makes a stand-alone version with messages bound in
#
standalone: ${TARGETSA}
	@echo ${COMPONENT}: standalone module built

${TARGETSA}: s.StandAlone ${RESOURCES}
	${AS} ${ASFLAGS} s.StandAlone

# Dynamic dependencies:
