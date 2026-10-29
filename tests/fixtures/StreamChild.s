; SPDX-License-Identifier: Apache-2.0
; One real file-loaded child image for both ends of a pipe. Argument R/W
; selects the endpoint; both tasks execute identical bytes at &10000.
        AREA StreamChild,CODE,READONLY
        KEEP
start
        MOV     r0,#0
        SWI     &63380
        BVS     fail
        CMP     r0,#0
        BEQ     fail
        SWI     &20010
        BVS     fail
        MOV     r8,#0
parse
        LDRB    r1,[r0],#1
        CMP     r1,#32
        MOVHI   r8,r1
        BCS     parse
        CMP     r8,#"S"
        BEQ     sleeper
        CMP     r8,#"R"
        MOVEQ   r9,#0
        BEQ     open
        CMP     r8,#"W"
        BNE     fail
        MOV     r9,#1
open
        CMP     r9,#0
        MOVEQ   r0,#&40
        MOVNE   r0,#&80
        ADRL    r1,pipe
        MOV     r2,#0
        SWI     &2000D
        BVS     fail
        CMP     r0,#0
        BEQ     fail
        MOV     r7,r0
        CMP     r9,#0
        ADRLEQ   r0,readerReady
        ADRLNE   r0,writerReady
announce
        SWI     &2
        ; Publish our real FileSwitch handle to the owning test parent.
        ; Handles are global: forced TaskWindow death does not close these.
        MOV     r4,#28
handleHex
        MOV     r0,r7,LSR r4
        AND     r0,r0,#15
        CMP     r0,#10
        ADDCC   r0,r0,#"0"
        ADDCS   r0,r0,#("A"-10)
        SWI     &0
        SUBS    r4,r4,#4
        BPL     handleHex
        ADRL    r0,readyEnd
        SWI     &2
        CMP     r9,#2
        BEQ     sleepLoop
        MOV     r4,#0
        MOV     r6,#768
        ADD     r6,r6,#1
loop
        RSB     r5,r4,r4,LSL #3
        ADD     r5,r5,#3
        AND     r5,r5,#255
        MOV     r1,r7
        CMP     r9,#0
        BNE     write
        SWI     &2000A
        BVS     fail
        BCS     fail
        CMP     r0,r5
        BNE     fail
        B       next
write
        MOV     r0,r5
        SWI     &2000B
        BVS     fail
next
        ADD     r4,r4,#1
        CMP     r4,r6
        BNE     loop
        CMP     r9,#0
        BNE     close
        MOV     r1,r7
        SWI     &2000A
        BVS     fail
        BCC     fail
        MOV     r1,r7
        SWI     &2000A
        BVC     fail
        LDR     r0,[r0]
        CMP     r0,#223                 ; documented read-past-EOF error
        BNE     fail
close
        MOV     r0,#0
        MOV     r1,r7
        SWI     &2000D
        BVS     fail
        MOV     r0,pc
        TST     r0,#3
        BNE     fail
        CMP     r9,#0
        ADRLEQ   r0,readerDone
        ADRLNE   r0,writerDone
        SWI     &2
        MOV     r0,#0
        SWI     &11
sleeper
        MOV     r0,#6
        MOV     r3,#4
        SWI     &2001E
        BVS     fail
        MOV     r7,r2
        MOV     r0,#0
        STR     r0,[r7]
        MOV     r9,#2
        ADR     r0,sleepReady
        B       announce
sleepLoop
        MOV     r0,#6                 ; public UpCall_Sleep
        MOV     r1,r7
        SWI     &20033
        BVS     fail
        CMP     r0,#0                 ; UpCall_Claimed
        BNE     fail
        LDR     r0,[r7]
        CMP     r0,#0
        BEQ     sleepLoop
        MOV     r0,#7
        MOV     r2,r7
        SWI     &2001E
        BVS     fail
        ADR     r0,sleepDone
        SWI     &2
        MOV     r0,#0
        SWI     &11
fail
        ADR     r0,failed
        SWI     &2
        MOV     r0,#0
        SWI     &11
sleepReady  DCB "SLEEP READY ",0
sleepDone   DCB "SLEEP PASS",13,10,0
pipe        DCB "Pipe:ArcBlock",0
readerReady DCB "READER READY ",0
writerReady DCB "WRITER READY ",0
readyEnd    DCB " END",13,10,0
readerDone  DCB "READER PASS",13,10,0
writerDone  DCB "WRITER PASS",13,10,0
failed      DCB "PIPE CHILD FAIL",13,10,0
        ALIGN
        END
