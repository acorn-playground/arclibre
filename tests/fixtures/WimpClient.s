; SPDX-License-Identifier: Apache-2.0
; Original diagnostic task helper. All floating point is executed by ARM2 traps.
        AREA WimpClient,CODE,READONLY
        EXPORT seed
        EXPORT capture
        EXPORT stop
seed
        MOV R1,#&70000
        WFS R1
        MOV R0,#11
        FLTE F0,R0
        MOV R0,#12
        FLTE F1,R0
        MOV R0,#13
        FLTE F2,R0
        MOV R0,#14
        FLTE F3,R0
        MOV R0,#15
        FLTE F4,R0
        MOV R0,#16
        FLTE F5,R0
        MOV R0,#17
        FLTE F6,R0
        MOV R0,#18
        FLTE F7,R0
        B capture
capture
        RFS R1
        STR R1,[R10]
        STFE F0,[R10,#4]
        STFE F1,[R10,#16]
        STFE F2,[R10,#28]
        STFE F3,[R10,#40]
        STFE F4,[R10,#52]
        STFE F5,[R10,#64]
        STFE F6,[R10,#76]
        STFE F7,[R10,#88]
stop
        B stop
        END
