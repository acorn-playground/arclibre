; SPDX-License-Identifier: Apache-2.0
; Public test-only buffered device. The guest copies this position-independent
; handler to RMA before registration. RX/TX bytes use the real DeviceFS SWIs.
        AREA |ArcStreamDevice|, CODE, READONLY
        EXPORT ArcStreamDeviceStart
        EXPORT ArcStreamDeviceEnd
ArcStreamDeviceStart
        STMFD   sp!, {r9,lr}
        CMP     r0,#11
        BHI     unknown
        ADD     r9,r12,#32
        LDR     lr,[r9,r0,LSL #2]
        ADD     lr,lr,#1
        STR     lr,[r9,r0,LSL #2]
        CMP     r0,#0
        BEQ     initialise
        CMP     r0,#2
        MOVEQ   r0,#0                  ; dormant TX, drained explicitly by test
        BEQ     good
        CMP     r0,#10
        LDREQ   r3,[r12,#8]            ; explicit test endpoint EOF state
        BEQ     good
        CMP     r0,#11
        SUBEQ   r9,r2,#1
        ADDEQ   r9,r12,r9,LSL #2
        STREQ   r3,[r9,#16]            ; actual buffer handles
        B       good
initialise
        AND     r9,r3,#1               ; current public driver ABI: direction in r3
        STR     r2,[r12,r9,LSL #2]     ; external RX/TX handle
        ADD     r2,r9,#1               ; nonzero internal handle 1/2
        MVN     r5,#0                 ; default buffer threshold
        B       good
unknown
        ADD     r0,r12,#128            ; real unsupported-operation error
        LDMFD   sp!,{r9,lr}
        ORRS    pc,lr,#&10000000
good
        LDMFD   sp!,{r9,lr}
        BICS    pc,lr,#&10000000
ArcStreamDeviceEnd
        END
