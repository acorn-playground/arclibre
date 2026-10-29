/* SPDX-License-Identifier: Apache-2.0 */
/* Public stream contracts; numeric SWIs are independent of module headers. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <kernel.h>
extern unsigned char ArcStreamDeviceStart[],ArcStreamDeviceEnd[];
static void message(const char *s) {_kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r);}
static void fail(const char *s) {message(s);message("ARCLIBRE STREAM CONTRACT FAIL\r\n");exit(1);}
static void call(int swi,_kernel_swi_regs *r) {_kernel_oserror *e=_kernel_swi(swi,r,r);if(e)fail(e->errmess);}
static int open_file(const char *name,int mode) {_kernel_swi_regs r;r.r[0]=mode;r.r[1]=(int)name;r.r[2]=0;call(0x0d,&r);if(!r.r[0])fail("open returned zero");return r.r[0];}
static void close_file(int h) {_kernel_swi_regs r;r.r[0]=0;r.r[1]=h;call(0x0d,&r);}
static void put(int h,int c) {_kernel_swi_regs r;r.r[0]=c;r.r[1]=h;call(0x0b,&r);}
static int get(int h,int *carry) {_kernel_swi_regs r;_kernel_oserror *e;r.r[1]=h;e=_kernel_swi_c(0x0a,&r,&r,carry);if(e)fail(e->errmess);return r.r[0]&255;}
static int eof(int h) {_kernel_swi_regs r;r.r[0]=5;r.r[1]=h;call(9,&r);return r.r[2];}
static void gbpb(int reason,int h,void *p,int n,int *left) {_kernel_swi_regs r;r.r[0]=reason;r.r[1]=h;r.r[2]=(int)p;r.r[3]=n;r.r[4]=0;call(0x0c,&r);*left=r.r[3];}
static void remove_file(const char *p) {_kernel_swi_regs r;r.r[0]=5;r.r[1]=(int)p;call(8,&r);if(r.r[0]){r.r[0]=6;r.r[1]=(int)p;call(8,&r);}}
static unsigned *claim(unsigned n) {_kernel_swi_regs r;r.r[0]=6;r.r[3]=n;call(0x1e,&r);return (unsigned *)r.r[2];}
static void release(void *p) {_kernel_swi_regs r;r.r[0]=7;r.r[2]=(int)p;call(0x1e,&r);}
static void devices(void) {
 _kernel_swi_regs r;unsigned *code,*state,parent;int rx,tx,i,c,carry;char path[]="ArcStream:";
 struct {int offset;unsigned flags,rf,rs,tf,ts,reserved,end;char name[16];} desc;
 unsigned size=ArcStreamDeviceEnd-ArcStreamDeviceStart;
 code=claim(size);memcpy(code,ArcStreamDeviceStart,size);state=claim(256);memset(state,0,256);
 state[32]=0x123456;strcpy((char *)(state+33),"Unknown test device operation");
 memset(&desc,0,sizeof(desc));desc.offset=(char *)desc.name-(char *)&desc;desc.flags=3;desc.rs=desc.ts=32;strcpy(desc.name,"ArcStream");
 r.r[0]=2;r.r[1]=(int)&desc;r.r[2]=(int)code;r.r[3]=0;r.r[4]=(int)state;r.r[5]=0;r.r[6]=r.r[7]=1;call(0x42740,&r);parent=r.r[0];
 rx=open_file(path,0x40);tx=open_file(path,0x80);
 {char d[160];sprintf(d,"DEVICE HANDLES %X %X INIT %u CREATED %u BUFFERS %X %X\r\n",state[0],state[1],state[8],state[19],state[4],state[5]);message(d);}
 if(!state[0] || !state[1] || state[8]!=2 || state[19]!=2)fail("device initialisation/stream callback");
 r.r[0]=0x40;r.r[1]=(int)path;r.r[2]=0;if(!_kernel_swi(0x0d,&r,&r) && r.r[0])fail("RX stream limit ignored");
 if(state[8]!=2)fail("excess RX initialised driver");
 for(i=0;i<24;i++){r.r[0]=(i*7+3)&255;r.r[1]=state[0];if(_kernel_swi_c(0x42746,&r,&r,&carry) || carry)fail("RX buffer overflow");}
 if(eof(rx))fail("buffered data reported EOF");
 for(i=0;i<24;i++){c=get(rx,&carry);if(carry || c!=((i*7+3)&255))fail("device RX data");}
 state[2]=~0U;if(!eof(rx))fail("device EOF");
 for(i=0;i<24;i++)put(tx,(i*11+5)&255);
 for(i=0;i<24;i++){
  r.r[1]=state[1];if(_kernel_swi_c(0x42747,&r,&r,&carry))fail("device TX call");
  if(carry || (r.r[0]&255)!=((i*11+5)&255))fail("device TX data");
 }
 r.r[1]=state[1];if(_kernel_swi_c(0x42747,&r,&r,&carry) || !carry)fail("empty TX buffer");
 close_file(rx);close_file(tx);if(state[9]!=2)fail("device close callbacks");
 r.r[0]=parent;call(0x42741,&r);
 r.r[0]=0x40;r.r[1]=(int)path;r.r[2]=0;if(!_kernel_swi(0x0d,&r,&r) && r.r[0])fail("deregistered device opens");
 release(state);release(code);message("ARCLIBRE DEVICE BUFFER LIFECYCLE PASS\r\n");
}
static void pseudo(void) {
 int h,i,c,carry,left;char b[8]={0};_kernel_swi_regs r;
 h=open_file("null:",0x40);if(!eof(h))fail("null EOF");c=get(h,&carry);if(!carry)fail("null byte EOF");
 gbpb(4,h,b,sizeof(b),&left);if(left!=sizeof(b))fail("null block EOF");close_file(h);
 h=open_file("null:",0x80);for(i=0;i<257;i++)put(h,i);gbpb(2,h,b,sizeof(b),&left);if(left)fail("null block write");close_file(h);
 h=open_file("rawvdu:",0x80);gbpb(2,h,"STREAM RAWVDU PASS\r\n",20,&left);if(left)fail("rawvdu write");close_file(h);
 h=open_file("vdu:",0x80);put(h,'V');close_file(h);
 /* Guest OS_Byte inserts a byte into the genuine keyboard buffer. */
 r.r[0]=138;r.r[1]=0;r.r[2]='K';call(6,&r);h=open_file("rawkbd:",0x40);c=get(h,&carry);close_file(h);if(carry || c!='K')fail("raw keyboard stream");
 message("ARCLIBRE SYSTEM STREAMS PASS\r\n");
}
static void pipes(void) {
 char data[769],back[780];int i,w,rd,left,carry;_kernel_swi_regs r;
 for(i=0;i<sizeof(data);i++)data[i]=(char)(i*7+3);
 remove_file("Pipe:ArcStream");w=open_file("Pipe:ArcStream",0x80);
 gbpb(2,w,data,sizeof(data),&left);if(left)fail("pipe block write");close_file(w);
 rd=open_file("Pipe:ArcStream",0x40);gbpb(4,rd,back,sizeof(back),&left);
 if(left!=sizeof(back)-sizeof(data) || memcmp(data,back,sizeof(data)) || !eof(rd))fail("pipe block read/EOF");
 get(rd,&carry);if(!carry)fail("pipe persistent EOF");close_file(rd);remove_file("Pipe:ArcStream");
 r.r[0]=5;r.r[1]=(int)"Pipe:ArcStream";call(8,&r);if(r.r[0])fail("pipe delete");
 message("ARCLIBRE PIPE CONTENT EOF PASS\r\n");
}
static int task,children[2],dead[2],block[64],poll_count;
static char child_output[2][1024];static unsigned output_used[2];
static int now(void) {_kernel_swi_regs r;call(0x42,&r);return r.r[0];}
static void poll(void) {
 _kernel_swi_regs r;int i;
 r.r[0]=0;r.r[1]=(int)block;r.r[2]=now()+1;r.r[3]=0;call(0x400e1,&r);poll_count++;
 if(r.r[0]==17 || r.r[0]==18){
  if(block[4]==0x808c2){for(i=0;i<2;i++)if(!children[i]){children[i]=block[1];break;}if(i==2)fail("too many pipe children");}
  if(block[4]==0x808c1){
   for(i=0;i<2 && children[i]!=block[1];i++);if(i==2)fail("unknown pipe output sender");
   if(block[5]<0 || block[5]>232 || output_used[i]+block[5]>=sizeof(child_output[i]))fail("pipe output bounds");
   memcpy(child_output[i]+output_used[i],block+6,block[5]);output_used[i]+=block[5];child_output[i][output_used[i]]=0;
   if(strstr(child_output[i],"FAIL"))fail(child_output[i]);
  }
  if(block[4]==0x808c3){for(i=0;i<2 && children[i]!=block[5];i++);if(i==2)fail("unknown pipe dead child");dead[i]++;}
 }
}
static void reset_children(void) {memset(children,0,sizeof(children));memset(dead,0,sizeof(dead));memset(output_used,0,sizeof(output_used));memset(child_output,0,sizeof(child_output));}
static void launch(char mode) {
 char command[256];_kernel_swi_regs r;
 sprintf(command,"TaskWindow \"Run ADFS::0.$.!StrTest.Child %c\" -task &%X -txt &1234 -name ArcPipe -quit -ctrl -wimpslot 128K",mode,task);
 r.r[0]=(int)command;call(0x400de,&r);
}
static void wait_text(int child,const char *s) {int t=now()+2000;while(!strstr(child_output[child],s)){if(now()>t)fail("pipe child output timeout");poll();}}
static void wait_dead(int n) {int i,t=now()+2000;for(;;){for(i=0;i<n && dead[i]==1;i++);if(i==n)return;if(now()>t)fail("pipe child exit timeout");poll();}}
static void blocked(int child) {int t=now()+30,p=poll_count;while(now()<t)poll();if(strstr(child_output[child],"PASS") || dead[child] || poll_count-p<5)fail("pipe did not block while parent progressed");}
static void blocking(void) {
 _kernel_swi_regs r;int w,i,rd,c,carry,count;char data[769];
 r.r[0]=310;r.r[1]=0x4b534154;r.r[2]=(int)"Pipe stream gate";r.r[3]=-1;call(0x400c0,&r);task=r.r[1];
 for(i=0;i<sizeof(data);i++)data[i]=(char)(i*7+3);
 reset_children();remove_file("Pipe:ArcBlock");w=open_file("Pipe:ArcBlock",0x80);
 launch('R');wait_text(0,"READER READY");blocked(0);
 for(i=0;i<sizeof(data);i++)put(w,(unsigned char)data[i]);close_file(w);
 wait_text(0,"READER PASS");wait_dead(1);remove_file("Pipe:ArcBlock");
 message("ARCLIBRE PIPE READER WAKE PASS\r\n");
 reset_children();launch('W');wait_text(0," END");blocked(0);
 r.r[0]=6;r.r[1]=(int)"Pipe:ArcBlock";if(!_kernel_swi(8,&r,&r))fail("open blocked pipe deleted");
 launch('R');wait_text(0,"WRITER PASS");wait_text(1,"READER PASS");wait_dead(2);remove_file("Pipe:ArcBlock");
 message("ARCLIBRE PIPE WRITER WAKE PASS\r\n");
 /* A caller-owned RMA poll word tests UpCall_SleepNoMore directly.
    FileSwitch may deallocate a handle even when its close returns an error,
    so a refused OS_Find close is not a handle-preservation contract. */
 reset_children();launch('S');wait_text(0," END");blocked(0);
 {unsigned address;_kernel_oserror *e;
  if(sscanf(child_output[0],"SLEEP READY %x",&address)!=1 || !address)fail("sleep word protocol");
  r.r[0]=7;r.r[1]=address;e=_kernel_swi(0x33,&r,&r);
  if(!e || e->errnum!=0xa84)fail("sleeping word removal was not rejected");
  *(volatile unsigned *)address=1;
 }
 wait_text(0,"SLEEP PASS");wait_dead(1);
 message("ARCLIBRE TASK SLEEP REMOVAL REJECTED PASS\r\n");
 reset_children();launch('W');wait_text(0," END");blocked(0);
 if(sscanf(child_output[0],"WRITER READY %x",&w)!=1 || !w)fail("child handle protocol");
 {int m[8]={0};m[0]=28;m[4]=0x808c4;m[5]=1;r.r[0]=17;r.r[1]=(int)m;r.r[2]=children[0];r.r[3]=0;call(0x400e7,&r);}
 wait_dead(1);
 /* File handles belong to FileSwitch, not the TaskWindow slot. */
 close_file(w);
 rd=open_file("Pipe:ArcBlock",0x40);count=0;
 while(!eof(rd)){c=get(rd,&carry);if(carry || c!=((count*7+3)&255))fail("killed writer contents");count++;if(count>=769)fail("writer did not remain blocked");}
 close_file(rd);if(count==0)fail("blocked writer stored nothing");remove_file("Pipe:ArcBlock");
 message("ARCLIBRE PIPE KILL CLEANUP PASS\r\n");
 r.r[0]=task;r.r[1]=0x4b534154;call(0x400dd,&r);
}

int ArcLibre_StreamMain(void) {pseudo();devices();pipes();blocking();message("ARCLIBRE STREAM CONTRACT PASS\r\n");return 0;}
