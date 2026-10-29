; SPDX-License-Identifier: Apache-2.0
; Real FPA client. Every case begins in SVC26; user cases change mode themselves.
        AREA Client, CODE, READONLY
        KEEP
status
        MOV R5,#&70000
        CMP R5,R5
        WFSEQ R5
        RFS R6
        STR R6,[R10]
        B done
arithmetic
        MOV R0,#7
        MOV R1,#3
        FLTD F0,R0
        FLTD F1,R1
        ADFD F2,F0,F1
        MUFD F3,F0,F1
        DVFD F4,F0,F1
        STFD F2,[R10]
        STFD F3,[R10,#8]
        STFD F4,[R10,#16]
        FIXZ R2,F4
        STR R2,[R10,#24]
        B done
user_arithmetic
        MOV R0,PC
        BIC R0,R0,#3
        TEQP PC,R0
        NOP
user_body
        MOV R2,PC
        STR R2,[R10,#252]
        B arithmetic
save_restore
        MOV R0,#1
        FLTE F0,R0
        MOV R0,#2
        FLTE F1,R0
        MOV R0,#3
        FLTE F2,R0
        MOV R0,#4
        FLTE F3,R0
        MOV R0,#5
        FLTE F4,R0
        MOV R0,#6
        FLTE F5,R0
        MOV R0,#7
        FLTE F6,R0
        MOV R0,#8
        FLTE F7,R0
        ; Match the original Wimp's exact FPA opcodes and 100-byte block.
        MOV R2,R10
        RFS R1
        STR R1,[R2]
        MOV R1,#&70000
        WFS R1
        STFE F0,[R2,#4]
        STFE F1,[R2,#16]
        STFE F2,[R2,#28]
        STFE F3,[R2,#40]
        STFE F4,[R2,#52]
        STFE F5,[R2,#64]
        STFE F6,[R2,#76]
        STFE F7,[R2,#88]
        MVFE F0,#0
        MVFE F1,#0
        MVFE F2,#0
        MVFE F3,#0
        MVFE F4,#0
        MVFE F5,#0
        MVFE F6,#0
        MVFE F7,#0
        MOV R4,R10
        MOV R5,#0
        WFS R5
        LDFE F0,[R4,#4]
        LDFE F1,[R4,#16]
        LDFE F2,[R4,#28]
        LDFE F3,[R4,#40]
        LDFE F4,[R4,#52]
        LDFE F5,[R4,#64]
        LDFE F6,[R4,#76]
        LDFE F7,[R4,#88]
        LDR R5,[R4]
        WFS R5
        ADD R4,R10,#128
        STFE F0,[R4],#12
        STFE F1,[R4],#12
        STFE F2,[R4],#12
        STFE F3,[R4],#12
        STFE F4,[R4],#12
        STFE F5,[R4],#12
        STFE F6,[R4],#12
        STFE F7,[R4],#12
        RFS R5
        STR R5,[R10,#224]
        B done
transcendentals
        MVFD F0,#1
        DVFD F0,F0,#2
        SIND F1,F0
        SQTD F2,#4
        LGND F3,#1
        EXPD F4,#0
        STFD F1,[R10]
        STFD F2,[R10,#8]
        STFD F3,[R10,#16]
        STFD F4,[R10,#24]
        B done
masked_zero_divide
        MOV R5,#0
        WFS R5
        MVFD F0,#1
        DVFD F0,F0,#0
        STFD F0,[R10]
        RFS R5
        STR R5,[R10,#8]
        B done
context_read
        STFE F0,[R10]
        RFS R5
        STR R5,[R10,#12]
        B done
context_write
        FLTE F0,R0
        WFS R1
        B done
trapped_zero_divide
        MOV R5,#&20000 ; enable genuine divide-by-zero exception
        WFS R5
        MVFD F0,#1
        DVFD F0,F0,#0
        B unexpected_return
unsupported_coprocessor
        MCR p3,0,R0,c0,c0,0
        B unexpected_return
uninstalled_fpa
        RFS R0
        B unexpected_return
error_handler
        ; A test application's real error handler: record arrival and return
        ; to SVC solely so the host can inspect the kernel-filled error buffer.
        STR R0,[R0]
        B done
unexpected_return
        B unexpected_return
done
        SWI &16 ; OS_EnterOS: restore SVC26 following user-mode tests
stop
        B stop
        END
