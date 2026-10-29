; SPDX-License-Identifier: Apache-2.0
; ArcLibre diagnostic parent: runs in RMA and launches genuine Absolute files.
        AREA Master,CODE,READONLY
        KEEP
module
        DCD start-module,0,0,0,modtitle-module,0,0
start
        MOV R0,PC
        BIC R0,R0,#3
        TEQP PC,R0
        MOV R0,R0
        ADRL R13,stackend
        LDR R0,version
        LDR R1,taskmagic
        ADRL R2,title
        ADR R3,interest
        SWI &600C0
        BVS failed
        STR R1,handle
        MOV R0,#1
        STR R0,stage
        MOV R0,#-1
        MOV R1,#&20000
        SWI &600EC
        BVS failed
        ADRL R0,childa
        SWI &600DE
        BVS failed
        STR R0,taska
        MOV R0,#2
        STR R0,stage
        ADRL R0,childb
        SWI &600DE
        BVS failed
        STR R0,taskb
        MOV R0,#3
        STR R0,stage
poll
        MOV R0,#0
        ADR R1,event
        SWI &600C7
        BVS failed
        CMP R0,#17
        BNE poll
        LDR R0,event+20
        LDR R1,event+24
        LDR R2,event+28
        CMP R2,#0
        BNE childfailed
        CMP R1,#20
        BNE poll
        LDR R1,finished
        CMP R0,#11
        ORREQ R1,R1,#1
        CMP R0,#29
        ORREQ R1,R1,#2
        STR R1,finished
        CMP R1,#3
        BNE poll
        LDR R0,handle
        LDR R1,taskmagic
        SWI &600DD
        BVS failed
        MOV R0,#4
        STR R0,stage
        SWI &16
stop    B stop
childfailed
        STR R0,failedchild
        MOV R0,#0
failed
        STR R0,error
        MOV R0,#&FF
        STR R0,stage
        SWI &16
        B stop
version DCD 310
taskmagic DCD &4B534154
handle DCD 0
taska DCD 0
taskb DCD 0
stage DCD 0
finished DCD 0
error DCD 0
failedchild DCD 0
interest DCD &4152434C,0
modtitle DCB "ArcTasks",0
title DCB "ArcLibre scheduler test",0
childa DCB "Resources:$.Apps.ArcTaskA",0
childb DCB "Resources:$.Apps.ArcTaskB",0
        ALIGN
event   SPACE 256
stack   SPACE 4096
stackend
        END
