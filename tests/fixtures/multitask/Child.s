; SPDX-License-Identifier: Apache-2.0
; Real relocatable-to-&8000 Absolute application, independent task data and FP.
        AREA Child,CODE,READONLY
        KEEP
start
        MOV R13,#&20000
        LDR R0,version
        LDR R1,magic
        ADR R2,title
        ADR R3,interest
        SWI &600C0
        BVS failed
        STR R1,handle
        LDR R0,identity
        MOV R1,#&10000
        STR R0,[R1]
        MOV R1,#&70000
        WFS R1
        FLTE F0,R0
        ADD R0,R0,#1
        FLTE F1,R0
        ADD R0,R0,#1
        FLTE F2,R0
        ADD R0,R0,#1
        FLTE F3,R0
        ADD R0,R0,#1
        FLTE F4,R0
        ADD R0,R0,#1
        FLTE F5,R0
        ADD R0,R0,#1
        FLTE F6,R0
        ADD R0,R0,#1
        FLTE F7,R0
        ADR R10,expected
        BL capture
poll
        MOV R0,#&1000000
        ADR R1,event
        SWI &600C7
        BVS failed
        ADR R10,actual
        BL capture
        ADR R1,expected
        ADR R2,actual
        MOV R3,#25
compare
        LDR R4,[R1],#4
        LDR R5,[R2],#4
        CMP R4,R5
        BNE badstate
        SUBS R3,R3,#1
        BNE compare
        MOV R1,#&10000
        LDR R1,[R1]
        LDR R2,identity
        CMP R1,R2
        BNE badstate
        LDR R1,count
        ADD R1,R1,#1
        STR R1,count
        STR R1,message+24
        LDR R0,identity
        STR R0,message+20
        MOV R0,#17
        ADR R1,message
        MOV R2,#0
        SWI &600E7
        BVS failed
        LDR R0,count
        CMP R0,#20
        BLT poll
        LDR R0,handle
        LDR R1,magic
        SWI &600DD
        BVS failed
        SWI &11
failed
        STR R0,error
badstate
        MOV R0,#1
        STR R0,message+28
        LDR R0,identity
        STR R0,message+20
        MOV R0,#17
        ADR R1,message
        MOV R2,#0
        SWI &600E7
        SWI &11
capture
        RFS R0
        STR R0,[R10]
        STFE F0,[R10,#4]
        STFE F1,[R10,#16]
        STFE F2,[R10,#28]
        STFE F3,[R10,#40]
        STFE F4,[R10,#52]
        STFE F5,[R10,#64]
        STFE F6,[R10,#76]
        STFE F7,[R10,#88]
        MOV PC,LR
magic DCD &4B534154
identity DCD 11
handle DCD 0
count DCD 0
error DCD 0
interest DCD &4152434C,0
message DCD 32,0,0,0,&4152434C,0,0,0
title DCB "ArcLibre child",0
        ALIGN
expected SPACE 100
actual SPACE 100
event SPACE 256
version DCD 310
        END
