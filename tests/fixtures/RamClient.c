/* SPDX-License-Identifier: Apache-2.0 */
/* Public RAM-disk contract. All data are created by the guest. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <kernel.h>
static void message(const char *s){_kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r);}
static void fail(const char *s){message(s);message("ARCLIBRE RAM CONTRACT FAIL\r\n");exit(1);}
static void call(int swi,_kernel_swi_regs *r){_kernel_oserror *e=_kernel_swi(swi,r,r);if(e)fail(e->errmess);}
static int now(void){_kernel_swi_regs r;call(0x42,&r);return r.r[0];}
static void poll(void){_kernel_swi_regs r;int b[64],end=now()+100;while(now()<end){r.r[0]=0;r.r[1]=(int)b;r.r[2]=now()+1;r.r[3]=0;call(0x400e1,&r);}}
static unsigned size(void){_kernel_swi_regs r;unsigned base,n;r.r[0]=5;call(0x5c,&r);base=r.r[0];n=r.r[1];call(0x4a,&r);if(r.r[0]!=base || (unsigned)(r.r[1]-r.r[0])!=n)fail("RAM area/limits contract");return n;}
static void resize(int delta){_kernel_swi_regs r;r.r[0]=5;r.r[1]=delta;call(0x2a,&r);}
static void cli(const char *s){_kernel_swi_regs r;r.r[0]=(int)s;call(5,&r);}
static int open(const char *s,int mode){_kernel_swi_regs r;r.r[0]=mode;r.r[1]=(int)s;r.r[2]=0;call(0xd,&r);if(!r.r[0])fail("zero file handle");return r.r[0];}
static void close(int h){_kernel_swi_regs r;r.r[0]=0;r.r[1]=h;call(0xd,&r);}
static void delete_file(const char *s){_kernel_swi_regs r;r.r[0]=6;r.r[1]=(int)s;call(8,&r);}
static void checkfile(const char *s,const char *data,int n){_kernel_swi_regs r;char b[1024];int h=open(s,0x40),i;for(i=0;i<n;i+=sizeof(b)){int len=n-i<sizeof(b)?n-i:sizeof(b);r.r[0]=4;r.r[1]=h;r.r[2]=(int)b;r.r[3]=len;call(0xc,&r);if(r.r[3] || memcmp(b,data+i,len))fail("RAM file contents");}r.r[0]=5;r.r[1]=h;call(9,&r);if(!r.r[2])fail("RAM file EOF");close(h);}
static void freespace(const char *stage){_kernel_swi_regs r;char s[120];r.r[0]=(int)":0";call(0x40783,&r);sprintf(s,"ARCLIBRE RAM FREE %s %u %u\r\n",stage,r.r[0],r.r[1]);message(s);}
int ArcLibre_RamMain(void){
 _kernel_swi_regs r;int task,i,h,full=0;unsigned original;char name[40],*data=malloc(65536);_kernel_oserror *e;
 if(!data)fail("RAM test allocation");for(i=0;i<65536;i++)data[i]=(char)(i*13+7);
 r.r[0]=310;r.r[1]=0x4b534154;r.r[2]=(int)"RAM filing gate";r.r[3]=-1;call(0x400c0,&r);task=r.r[1];
 original=size();if(original)fail("cold RAM disk not empty");resize(262144);if(size()!=262144)fail("RAM disk grow");
 resize(262144);if(size()!=524288)fail("empty RAM disk second grow");resize(-262144);if(size()!=262144)fail("empty RAM disk shrink");
 r.r[0]=5;r.r[1]=(int)"RAM::0.$";call(8,&r);if(r.r[0]!=2)fail("RAM root directory");
 message("ARCLIBRE RAM EMPTY RESIZE PASS\r\n");
 resize(-262144);poll();cli("ChangeDynamicArea -RamFsSize 256K");poll();
 if(size()!=262144)fail("TaskManager RAM command");
 message("ARCLIBRE RAM UI READY\r\n");for(i=0;i<8;i++)poll();
 cli("ShowFree -FS RAM 0");poll();freespace("BEFORE");
 h=open("RAM::0.$.Payload",0x80);r.r[0]=2;r.r[1]=h;r.r[2]=(int)data;r.r[3]=65536;call(0xc,&r);if(r.r[3])fail("short RAM write");close(h);
 checkfile("RAM::0.$.Payload",data,65536);poll();freespace("AFTER");
 r.r[0]=5;r.r[1]=262144;e=_kernel_swi(0x2a,&r,&r);if(!e || e->errnum!=0x1c3)fail("nonempty RAM disk resize error");if(size()!=262144)fail("failed resize changed area");checkfile("RAM::0.$.Payload",data,65536);
 message("ARCLIBRE RAM CONTENTS RESIZE GUARD PASS\r\n");
 for(i=0;i<10;i++){
  sprintf(name,"RAM::0.$.Fill%d",i);h=open(name,0x80);r.r[0]=2;r.r[1]=h;r.r[2]=(int)data;r.r[3]=65536;e=_kernel_swi(0xc,&r,&r);
  if(e){char text[160];if(e->errnum!=0x117c6)fail("unexpected full disk error");sprintf(text,"RAM FULL ERROR %X %s\r\n",e->errnum,e->errmess);message(text);full=1;}
  close(h);if(full)break;
 }
 if(!full)fail("RAM disk never filled");checkfile("RAM::0.$.Payload",data,65536);
 for(;i>=0;i--){sprintf(name,"RAM::0.$.Fill%d",i);delete_file(name);}delete_file("RAM::0.$.Payload");poll();freespace("CLEAN");
 cli("ChangeDynamicArea -RamFsSize 0K");if(size()!=original)fail("RAM disk release");poll();
 message("ARCLIBRE RAM FULL CLEANUP PASS\r\n");
 r.r[0]=task;r.r[1]=0x4b534154;call(0x400dd,&r);free(data);message("ARCLIBRE RAM CONTRACT PASS\r\n");return 0;
}
