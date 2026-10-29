; SPDX-License-Identifier: Apache-2.0
; File-loaded public test of the original SpriteUtils command/API contract.
        AREA SpriteCommandClient,CODE,READONLY
        KEEP
start
        MOV r0,#3
        MOV r1,#32768
        SWI &2002A                    ; real system sprite dynamic area
        BVS apierror
        ADRL r9,commands
next
        MOV r0,r9
        LDRB r1,[r0]
        CMP r1,#0
        BEQ inspect
        SWI &20005
        BVS apierror
skip
        LDRB r1,[r9],#1
        CMP r1,#0
        BNE skip
        B next
inspect
        MOV r0,#8
        SWI &2002E
        BVS apierror
        CMP r3,#1
        BNE fail
        MOV r0,#40
        ADRL r2,sprite
        SWI &2002E
        BVS apierror
        CMP r3,#8
        CMPEQ r4,#2
        CMPEQ r6,#12
        BNE fail
        MOV r8,#0
pixel
        MOV r0,#41
        ADRL r2,sprite
        AND r3,r8,#7
        MOV r4,r8,LSR #3
        SWI &2002E
        BVS apierror
        CMP r5,r8
        BNE fail
        ADD r8,r8,#1
        CMP r8,#16
        BLO pixel
        ADRL r0,missing
        SWI &20005
        BVC fail
        LDR r1,[r0]
        CMP r1,#&D6                   ; genuine missing sprite FILE, not command
        BNE fail
        ADRL r0,clear
        SWI &20005
        BVS apierror
        MOV r0,#8
        SWI &2002E
        BVS apierror
        CMP r3,#0
        BNE fail
        MOV r0,#3
        MOV r1,#32768
        RSB r1,r1,#0
        SWI &2002A
        BVS apierror
        ADRL r0,success
        SWI &2
        MOV r0,#0
        SWI &11
apierror
        ADD r0,r0,#4
        SWI &2
fail
        ADRL r0,failure
        SWI &2
        MOV r0,#0
        SWI &11
commands
        DCB "SNew",0
        DCB "SLoad ADFS::0.$.!SprTest.Input",0
        DCB "SChoose fixture",0
        DCB "SCopy fixture copy",0
        DCB "SRename copy renamed",0
        DCB "SDelete renamed",0
        DCB "SFlipX fixture",0
        DCB "SFlipX fixture",0
        DCB "SFlipY fixture",0
        DCB "SFlipY fixture",0
        DCB "SList",0
        DCB "SInfo",0
        DCB "Help SLoad",0
        DCB "SSave ADFS::0.$.!SprTest.Saved",0,0
sprite  DCB "fixture",0
missing DCB "SLoad ADFS::0.$.!SprTest.Missing",0
clear   DCB "SNew",0
success DCB "ARCLIBRE SPRITE COMMANDS PASS",13,10,0
failure DCB "ARCLIBRE SPRITE COMMANDS FAIL",13,10,0
        ALIGN
        END
