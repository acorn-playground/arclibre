/* SPDX-License-Identifier: Apache-2.0 */
/* A real file-loaded Wimp parent; all interaction uses public OS interfaces. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <kernel.h>

extern void FilterPreA(void),FilterPreB(void),FilterPostA(void),FilterPostB(void),FilterMasked(void),FilterSelf(void);
static volatile unsigned filters[16];
static int task,child,block[64],polls,dead,ego;
static char output[4096];
static unsigned used;
static void message(const char *s) { _kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r); }
static void fail(const char *s) { message(s);message("ARCLIBRE TASK SERVICES FAIL\r\n");exit(1); }
static void call(int swi,_kernel_swi_regs *r) { _kernel_oserror *e=_kernel_swi(swi,r,r);if(e)fail(e->errmess); }
static int now(void) { _kernel_swi_regs r;call(0x42,&r);return r.r[0]; }
static void filter(int reason,char *name,void (*fn)(void),int mask) {
 _kernel_swi_regs r;r.r[0]=(int)name;r.r[1]=(int)fn;r.r[2]=(int)filters;r.r[3]=task;r.r[4]=mask;call(0x42640+reason,&r);
}
static void send(int target,int action,int value) {
 _kernel_swi_regs r;int m[8];memset(m,0,sizeof(m));m[0]=28;m[4]=action;m[5]=1;m[6]=value;
 r.r[0]=17;r.r[1]=(int)m;r.r[2]=target;r.r[3]=0;call(0x400e7,&r);
}
static int poll(void) {
 _kernel_swi_regs r;r.r[0]=0;r.r[1]=(int)block;r.r[2]=now()+1;r.r[3]=0;call(0x400e1,&r);polls++;
 if(r.r[0]==17 || r.r[0]==18) {
  if(block[4]==0x808c2) {child=block[1];ego++;}
  if(block[4]==0x808c1) {
   unsigned n=block[5];if(n>232 || used+n>=sizeof(output))fail("output bounds");
   memcpy(output+used,block+6,n);used+=n;output[used]=0;
  }
  if(block[4]==0x808c3) {if(block[5]!=child)fail("wrong dead child");dead++;}
  if(block[4]==0x60001)fail("claimed filter event escaped");
 }
 return r.r[0];
}
static void wait_text(const char *s) { int limit=now()+2000;while(!strstr(output,s)){if(now()>limit)fail("child output timeout");poll();} }
static void launch(const char *command) {
 _kernel_swi_regs r;char cmd[256];used=0;output[0]=0;dead=ego=child=0;
 sprintf(cmd,"TaskWindow \"%s\" -task &%X -txt &1234 -name ArcChild -quit -ctrl -wimpslot 128K",command,task);
 r.r[0]=(int)cmd;call(0x400de,&r);
}
static void finish_child(void) {int limit=now()+2000;while(!dead){if(now()>limit)fail("child exit timeout");poll();}if(ego!=1 || dead!=1)fail("child lifecycle");}

int ArcLibre_TaskMain(void) {
 _kernel_swi_regs r;int i,t,p,before;unsigned saved[16];
 r.r[0]=310;r.r[1]=0x4b534154;r.r[2]=(int)"Task service gate";r.r[3]=-1;call(0x400c0,&r);task=r.r[1];
 r.r[0]=0;call(0x43380,&r);if(r.r[0])fail("ordinary parent is not TaskWindow");
 filter(0,"Arc pre A",FilterPreA,0);filter(0,"Arc pre B",FilterPreB,0);
 filter(1,"Arc post A",FilterPostA,0);filter(1,"Arc post B",FilterPostB,0);
 filter(1,"Arc masked",FilterMasked,~0);
 filters[11]=(unsigned)"Arc self";filters[12]=(unsigned)FilterSelf;filters[13]=task;
 filter(0,"Arc self",FilterSelf,0);
 send(task,0x60001,0);
 for(i=0;i<20;i++)poll();
  {char diagnostic[256];sprintf(diagnostic,"FILTERS %u %u %u %u %u %u %u %u\r\n",filters[0],filters[1],filters[2],filters[3],filters[4],filters[5],filters[6],filters[7]);message(diagnostic);}
 if(!filters[0] || filters[0]!=filters[1] || !filters[2] || filters[2]!=filters[3] || filters[4] || filters[5]!=1 || filters[6] || filters[7] || filters[10]!=1 || filters[14])fail("filter count/order/mask/claim/removal");
 filter(2,"Arc pre A",FilterPreA,0);filter(2,"Arc pre B",FilterPreB,0);
 filter(3,"Arc post A",FilterPostA,0);filter(3,"Arc post B",FilterPostB,0);filter(3,"Arc masked",FilterMasked,0);
 for(i=0;i<16;i++)saved[i]=filters[i];for(i=0;i<10;i++)poll();
 for(i=0;i<16;i++)if(saved[i]!=filters[i])fail("deregistered filter executed");
 r.r[0]=(int)"Arc self";r.r[1]=(int)FilterSelf;r.r[2]=(int)filters;r.r[3]=task;
 if(!_kernel_swi(0x42642,&r,&r))fail("missing filter did not report error");
 message("ARCLIBRE FILTER CONTRACT PASS\r\n");

 launch("Run ADFS::0.$.!TaskTest.Child");wait_text("READY");
 if(!child || ego!=1)fail("missing child identity");
 send(child,0x808c6,0);send(child,0x808c0,'K');
 t=now()+30;while(now()<t)poll();if(strstr(output,"BUSY"))fail("suspended child ran");
 send(child,0x808c7,0);wait_text("BUSY");p=polls;t=now();
 wait_text("DONE");if(polls-p<5 || now()-t<5)fail("no concurrent parent progress");
 finish_child();if(strstr(output,"FAIL"))fail("child state failed");
 message("ARCLIBRE TASK PREEMPT INPUT SUSPEND PASS\r\n");

 launch("Error 123 ARCLIBRE_EXPECTED_ERROR");wait_text("ARCLIBRE_EXPECTED_ERROR");finish_child();
 message("ARCLIBRE TASK ERROR RECOVERY PASS\r\n");
 launch("Run ADFS::0.$.!TaskTest.Child");wait_text("READY");send(child,0x808c4,0);finish_child();
 message("ARCLIBRE TASK KILL CLEANUP PASS\r\n");
 r.r[0]=0;call(0x43380,&r);if(r.r[0])fail("parent identity after cleanup");
 before=polls;for(i=0;i<10;i++)poll();if(polls-before!=10)fail("parent recovery");
 r.r[0]=task;r.r[1]=0x4b534154;call(0x400dd,&r);
 message("ARCLIBRE TASK SERVICES PASS\r\n");return 0;
}
