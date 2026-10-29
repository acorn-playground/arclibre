; SPDX-License-Identifier: Apache-2.0
; Original standalone ARM2 filing diagnostic. No emulator callbacks or ROM stubs.
        ORG &10000
Start
        MOV r0, #&40
        ADR r1, Filename
        SWI &2000D              ; XOS_Find: open existing file for input
        BVS Failed
        CMP r0, #0
        BEQ Failed
        MOV r8, r0
        MOV r1, r8
        MOV r0, #2
        SWI &20009              ; XOS_Args: extent
        BVS CloseFailed
        LDR r3, ExpectedLength
        CMP r2, r3
        BNE CloseFailed
        MOV r0, #4
        MOV r1, r8
        MOV r2, #&20000
        SWI &2000C              ; XOS_GBPB: sequential read
        BVS CloseFailed
        CMP r3, #0
        BNE CloseFailed
        MOV r1, r8
        SWI &2000A              ; XOS_BGet: must return EOF carry
        BVS CloseFailed
        BCC CloseFailed
        MOV r0, #0
        MOV r1, r8
        SWI &2000D
        BVS Failed
        MOV r2, #&20000
        LDR r3, ExpectedLength
        MOV r6, #0
Checksum
        LDRB r7, [r2], #1
        ADD r6, r6, r7
        SUBS r3, r3, #1
        BNE Checksum
        LDR r7, ExpectedSum
        CMP r6, r7
        BNE Failed
        ADR r0, SuccessMessage
        B PrintExit
CloseFailed
        MOV r0, #0
        MOV r1, r8
        SWI &2000D
Failed
        ADR r0, FailureMessage
PrintExit
        SWI &2                  ; OS_Write0
        MOV r0, #0
        SWI &11                 ; OS_Exit to inherited Supervisor environment
CodeEnd
ExpectedLength DCD 38895
ExpectedSum DCD 4958583
Filename DCB "ADFS::0.$.Docs.Fragment",0
SuccessMessage DCB "ARM2 FILING CLIENT PASS",13,10,0
FailureMessage DCB "ARM2 FILING CLIENT FAILED",13,10,0
        ALIGN
        END
