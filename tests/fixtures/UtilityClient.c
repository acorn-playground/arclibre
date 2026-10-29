/* SPDX-License-Identifier: Apache-2.0 */
/* Public ScreenBlanker and original StringLib contract, run from a floppy. */
#include <stdio.h>
#include <stdlib.h>
#include <kernel.h>
static void message(const char *s){_kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r);}
static void fail(const char *s){message(s);message("ARCLIBRE UTILITY FAIL\r\n");exit(1);}
static void call(int swi,_kernel_swi_regs *r){_kernel_oserror *e=_kernel_swi(swi,r,r);if(e)fail(e->errmess);}
static int now(void){_kernel_swi_regs r;call(0x42,&r);return r.r[0];}
static void wait(int cs){int end=now()+cs;while(now()<end){}}
static void cli(const char *s){_kernel_swi_regs r;r.r[0]=(int)s;call(5,&r);}
static void control(int reason,int value){_kernel_swi_regs r;r.r[0]=reason;r.r[1]=value;call(0x43100,&r);}
static int timeout(void){_kernel_swi_regs r;r.r[0]=4;call(0x43100,&r);return r.r[1];}
int ArcLibre_UtilityMain(void){
 _kernel_swi_regs r;_kernel_oserror *e;int task,i;char marker[100];
 static const char *voices[]={"StringLib-Soft","StringLib-Pluck","StringLib-Steel","StringLib-Hard"};
 r.r[0]=310;r.r[1]=0x4b534154;r.r[2]=(int)"Standard utilities gate";r.r[3]=-1;call(0x400c0,&r);task=r.r[1];
 (void)timeout();cli("BlankTime O 0");if(timeout()!=0)fail("disabled blank timeout");
 /* ModuleBadSWI (&110) is distinct from the kernel unknown-SWI error. */
 r.r[0]=99;e=_kernel_swi(0x43100,&r,&r);if(!e || e->errnum!=0x110){sprintf(marker,"BLANK ERROR %X %s",e?e->errnum:0,e?e->errmess:"no error");fail(marker);}
 wait(40);message("ARCLIBRE UTILITY SCREEN BEFORE\r\n");
 control(0,0);wait(40);message("ARCLIBRE UTILITY SCREEN BLANK\r\n");
 control(1,0);wait(40);message("ARCLIBRE UTILITY SCREEN RESTORED\r\n");
 /* Legacy reason 4 returns seconds; later reason 5 is not in this cohort. */
 control(3,1);if(timeout()!=5)fail("minimum blank timeout in legacy seconds");
 wait(550);message("ARCLIBRE UTILITY SCREEN TIMED\r\n");
 control(1,0);cli("BlankTime W 0");control(0,0);wait(40);
 message("ARCLIBRE UTILITY SCREEN WRCHBLANK\r\n");wait(40);
 message("ARCLIBRE UTILITY SCREEN WRCHRESTORED\r\n");cli("BlankTime O 0");
 /* The host supplies real keyboard-link input after observing each blank
    frame. Output wake-up is disabled here, so these markers cannot restore it. */
 control(0,0);wait(40);message("ARCLIBRE UTILITY SCREEN MOUSEBLANK\r\n");
 wait(60);message("ARCLIBRE UTILITY SCREEN MOUSERESTORED\r\n");
 control(0,0);wait(40);message("ARCLIBRE UTILITY SCREEN KEYBLANK\r\n");
 wait(60);message("ARCLIBRE UTILITY SCREEN KEYRESTORED\r\n");
 r.r[0]=2;r.r[1]=40;r.r[2]=40;r.r[3]=2;r.r[4]=0;call(0x43100,&r);
 for(i=0;i<8;i++){wait(20);sprintf(marker,"ARCLIBRE UTILITY FLASH %d\r\n",i);message(marker);}
 if(timeout()!=0)fail("flashing changed normal timeout");control(1,0);wait(40);
 message("ARCLIBRE UTILITY SCREEN FINAL\r\n");
 r.r[0]=2;call(0x40141,&r);r.r[0]=1;r.r[1]=208;r.r[2]=48;r.r[3]=0;r.r[4]=0;call(0x40140,&r);
 message("ARCLIBRE UTILITY VOICES READY\r\n");
 for(i=0;i<4;i++){
  r.r[0]=1;r.r[1]=(int)voices[i];call(0x4018a,&r);if(r.r[0]!=1)fail("named string voice missing");
  sprintf(marker,"ARCLIBRE UTILITY VOICE %d START\r\n",i);message(marker);
  r.r[0]=1;r.r[1]=-15;r.r[2]=100;r.r[3]=80;call(0x40189,&r);wait(100);
  sprintf(marker,"ARCLIBRE UTILITY VOICE %d END\r\n",i);message(marker);
 }
 r.r[0]=1;r.r[1]=0;r.r[2]=100;r.r[3]=1;call(0x40189,&r);wait(50);
 r.r[0]=task;r.r[1]=0x4b534154;call(0x400dd,&r);
 message("ARCLIBRE UTILITY PASS\r\n");return 0;
}
