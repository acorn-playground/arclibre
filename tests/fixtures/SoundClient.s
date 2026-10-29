; SPDX-License-Identifier: Apache-2.0
; Original user-mode sound API probe, launched from a real floppy application.
        AREA SoundClient,CODE,READONLY
        KEEP
start
        SWI &20000+&40144       ; Sound_Mode is unsupported on VIDC1a
        BVC fail
        LDR r1,[r0]
        SUB r1,r1,#&100
        CMP r1,#&E6
        BNE fail
        MOV r0,#2
        SWI &40141             ; enable sound DMA
        MOV r0,#0
        SWI &40141             ; query enabled state
        CMP r0,#2
        BNE fail
        MOV r0,#1
        MOV r1,#127
        SWI &40142             ; channel 1 full right
        MOV r0,#1
        MOV r1,#&100           ; query, out-of-range position
        SWI &40142
        CMP r1,#127
        BNE fail
        MOV r0,#1
        MOV r1,#0
        SWI &40142             ; centre again
        ; Configure real channel/rate combinations, then expose two observation
        ; points separated by guest monotonic time. No hardware/workspace writes.
        ADR r5,rates
ratecase
        LDMIA r5!,{r6,r7}
        CMP r6,#0
        BEQ ratedone
        MOV r0,r6
        MOV r1,#208
        MOV r2,r7
        MOV r3,#0
        MOV r4,#0
        SWI &40140
        MOV r0,#0
        MOV r1,#0
        MOV r2,#0
        MOV r3,#0
        MOV r4,#0
        SWI &40140
        CMP r0,r6
        BNE fail
        CMP r2,r7
        BNE fail
        MOV r9,r2
        SWI &42
        ADD r8,r0,#10          ; let the two-buffer rate pipeline settle
ratesettle
        SWI &42
        CMP r0,r8
        BLO ratesettle
        ADRL r0,ratestart
        SWI &2
        SWI &42
        ADD r8,r0,#20
ratewait
        SWI &42
        CMP r0,r8
        BLO ratewait
        ADRL r0,rateend
        SWI &2
        B ratecase
ratedone
        MOV r0,#1
        MOV r1,#208
        MOV r2,#48
        MOV r3,#0
        MOV r4,#0
        SWI &40140
        ADRL r0,voice
        SWI &20005
        BVS apierror
        MOV r0,#1
        MVN r1,#14             ; BBC amplitude -15
        MOV r2,#100
        MOV r3,#80
        SWI &40189             ; genuine Sound_Control
        ADRL r0,playing
        SWI &2
        SWI &42
        ADD r8,r0,#150         ; allow real DMA/IRQ refill for 1.5 seconds
wait
        SWI &42
        CMP r0,r8
        BLO wait
        ADRL r0,percussion
        SWI &20005
        BVS apierror
        MOV r0,#0
        MOV r1,#0
        MOV r2,#&10000
        SUB r2,r2,#15
        MOV r2,r2,LSL #16
        ORR r2,r2,#1
        MOV r3,#40
        MOV r3,r3,LSL #16
        ORR r3,r3,#100
        SWI &401C1             ; Sound_QSchedule, packed control event
        CMP r0,#0
        BNE fail
        SWI &42
        ADD r8,r0,#100
wait2
        SWI &42
        CMP r0,r8
        BLO wait2
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
rates   DCD 1,48,2,48,4,48,8,48,1,80,2,80,4,80,8,80,0,0
ratestart DCB "ARCLIBRE SOUND RATE START",13,10,0
rateend DCB "ARCLIBRE SOUND RATE END",13,10,0
voice   DCB "ChannelVoice 1 WaveSynth-Beep",0
percussion DCB "ChannelVoice 1 Percussion-Snare",0
playing DCB "ARCLIBRE SOUND PLAYING",13,10,0
success DCB "ARCLIBRE SOUND API PASS",13,10,0
failure DCB "ARCLIBRE SOUND API FAIL",13,10,0
        ALIGN
        END
