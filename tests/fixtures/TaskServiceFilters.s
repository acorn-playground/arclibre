; SPDX-License-Identifier: Apache-2.0
; Wimp filter ABI: R12 points to the parent's counters; preserve R1/R2.
        AREA |FilterTest$$Code|,CODE,READONLY
        EXPORT FilterPreA
        EXPORT FilterPreB
        EXPORT FilterPostA
        EXPORT FilterPostB
        EXPORT FilterMasked
        EXPORT FilterSelf
FilterPreA
        STMFD sp!,{r3,lr}
        LDR r3,[r12,#0]
        ADD r3,r3,#1
        STR r3,[r12,#0]
        LDR r3,[r12,#32]
        CMP r3,#2
        MOVNE r3,#1
        STRNE r3,[r12,#24]
        MOV r3,#0
        STR r3,[r12,#32]
        BIC r0,r0,#1
        LDMFD sp!,{r3,pc}
FilterPreB
        STMFD sp!,{r3,lr}
        LDR r3,[r12,#4]
        ADD r3,r3,#1
        STR r3,[r12,#4]
        MOV r3,#2
        STR r3,[r12,#32]
        LDMFD sp!,{r3,pc}
FilterPostA
        STMFD sp!,{r3,lr}
        LDR r3,[r12,#8]
        ADD r3,r3,#1
        STR r3,[r12,#8]
        LDR r3,[r12,#36]
        CMP r3,#2
        MOVNE r3,#1
        STRNE r3,[r12,#28]
        MOV r3,#0
        STR r3,[r12,#36]
        ; The exact custom message is &60001, compare without a literal pool.
        CMP r0,#17
        BNE postdone
        LDR r3,[r1,#16]
        SUB r3,r3,#&60000
        CMP r3,#1
        LDREQ r3,[r12,#20]
        ADDEQ r3,r3,#1
        STREQ r3,[r12,#20]
        MVNEQ r0,#0
postdone
        LDMFD sp!,{r3,pc}
FilterPostB
        STMFD sp!,{r3,lr}
        LDR r3,[r12,#12]
        ADD r3,r3,#1
        STR r3,[r12,#12]
        MOV r3,#2
        STR r3,[r12,#36]
        LDMFD sp!,{r3,pc}
FilterMasked
        STMFD sp!,{r3,lr}
        LDR r3,[r12,#16]
        ADD r3,r3,#1
        STR r3,[r12,#16]
        LDMFD sp!,{r3,pc}
FilterSelf
        STMFD sp!,{r0-r5,r12,lr}
        LDR r0,[r12,#40]
        ADD r0,r0,#1
        STR r0,[r12,#40]
        LDR r0,[r12,#44]
        LDR r1,[r12,#48]
        MOV r2,r12
        LDR r3,[r12,#52]
        SWI &62642
        MOVVS r0,#1
        STRVS r0,[r12,#56]
        LDMFD sp!,{r0-r5,r12,pc}
        END
