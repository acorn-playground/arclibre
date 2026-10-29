; SPDX-License-Identifier: Apache-2.0
; Real USR26 application. The busy loop deliberately makes no SWIs.
        AREA TaskServiceChild,CODE,READONLY
        KEEP
start
        MOV r0,#0
        SWI &63380
        BVS fail
        CMP r0,#0
        BEQ fail
        ADR r0,ready
        SWI &2
        SWI &4
        CMP r0,#"K"
        BNE fail
        MOV r0,#37
        FLTE f0,r0
        ADD r0,r0,#1
        FLTE f1,r0
        ADD r0,r0,#1
        FLTE f2,r0
        ADD r0,r0,#1
        FLTE f3,r0
        ADD r0,r0,#1
        FLTE f4,r0
        ADD r0,r0,#1
        FLTE f5,r0
        ADD r0,r0,#1
        FLTE f6,r0
        ADD r0,r0,#1
        FLTE f7,r0
        ADR r0,busy
        SWI &2
        MOV r8,#&AB000000
        MOV r9,#&CD000000
        MOV r10,#&EF000000
        MOV r4,#&800000
loop
        ADD r5,r5,#1
        SUBS r4,r4,#1
        BNE loop
        CMP r8,#&AB000000
        CMPEQ r9,#&CD000000
        CMPEQ r10,#&EF000000
        BNE fail
        MOV r0,pc
        TST r0,#3
        BNE fail
        FIX r0,f0
        CMP r0,#37
        BNE fail
        FIX r0,f1
        CMP r0,#38
        BNE fail
        FIX r0,f2
        CMP r0,#39
        BNE fail
        FIX r0,f3
        CMP r0,#40
        BNE fail
        FIX r0,f4
        CMP r0,#41
        BNE fail
        FIX r0,f5
        CMP r0,#42
        BNE fail
        FIX r0,f6
        CMP r0,#43
        BNE fail
        FIX r0,f7
        CMP r0,#44
        BNE fail
        ADR r0,done
        SWI &2
        MOV r0,#0
        SWI &11
fail
        ADR r0,failed
        SWI &2
        MOV r0,#0
        SWI &11
ready DCB "READY",13,10,0
busy DCB "BUSY",13,10,0
done DCB "DONE",13,10,0
failed DCB "CHILD FAIL",13,10,0
        ALIGN
        END
