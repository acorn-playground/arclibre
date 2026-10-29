; SPDX-License-Identifier: Apache-2.0
; Public Wimp 2.00 client: deliberately no ArcLibre message/header definitions.
        AREA MenuClient,CODE,READONLY
        KEEP
start
        MOV r0,#200
        LDR r1,taskmagic
        ADRL r2,name
        MOV r3,#0
        SWI &400C0
        MOV r10,r1
        MOV r11,#0
        ADRL r0,child
        ADRL r1,parent
        STR r0,[r1,#56]         ; second item's actual submenu pointer
openmain
        ADRL r1,parent
        MOV r2,#512
        MOV r3,#700
        SWI &400D4
poll
        MOV r0,#0
        ADRL r1,block
        SWI &400C7
        CMP r0,#17
        BEQ message
        CMP r0,#18
        BEQ message
        CMP r0,#9
        BNE poll
        LDR r0,[r1]
        CMP r0,r11             ; first warning item, then direct item
        BNE fail
        LDR r0,[r1,#4]
        CMP r0,#0
        BNE fail
        LDR r0,[r1,#8]
        CMN r0,#1
        BNE fail
        ADD r11,r11,#1
        CMP r11,#1
        BEQ openmain
        MOV r1,#-1
        SWI &400D4
        MOV r0,r10
        LDR r1,taskmagic
        SWI &400DD
        ADRL r0,success
        SWI &2
        SWI &11
message
        LDR r0,[r1,#16]
        LDR r2,badwarning
        CMP r0,r2
        BEQ fail
        LDR r2,warning
        CMP r0,r2
        BNE poll
        CMP r11,#0
        BNE fail
        LDR r0,[r1,#20]
        CMP r0,#&8000          ; dynamic placeholder used by classic clients
        BNE fail
        LDR r0,[r1,#32]
        CMP r0,#0
        BNE fail
        LDR r0,[r1,#36]
        CMN r0,#1
        BNE fail
        LDR r2,[r1,#24]
        LDR r3,[r1,#28]
        ADRL r1,child
        SWI &400E8             ; genuine Wimp_CreateSubMenu
        B poll
fail
        ADRL r0,failure
        SWI &2
        SWI &11
        ALIGN
warning DCD &400C0
badwarning DCD &800C0
taskmagic DCD &4B534154
name DCB "ArcMenuTest",0
success DCB "ARCLIBRE MENU CONTRACT PASS",13,10,0
failure DCB "ARCLIBRE MENU CONTRACT FAIL",13,10,0
        ALIGN
parent DCB "Menu ABI",0,0,0,0
        DCB 7,2,7,0
        DCD 256,44,0
        DCD 8,&8000,&07000001
        DCB "Warning",0,0,0,0,0
        DCD 128,0,&07000001
        DCB "Direct",0,0,0,0,0,0
child DCB "Submenu",0,0,0,0,0
        DCB 7,2,7,0
        DCD 192,44,0
        DCD 128,-1,&07000001
        DCB "Select",0,0,0,0,0,0
block   SPACE 256
        END
