/* SPDX-License-Identifier: Apache-2.0 */
/* Real Squash SWIs: fast/restartable cross-decoding, errors and guard bytes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <kernel.h>
static unsigned char plain[16000], packed[32016], back[32016];
static unsigned char cw[31760], dw[17424];
static void message(const char *s){_kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r);}
static void fail(const char *s){message(s);message("ARCLIBRE SQUASH FAIL\r\n");exit(1);}
static void call(int swi,_kernel_swi_regs *r){_kernel_oserror *e=_kernel_swi(swi,r,r);if(e)fail(e->errmess);}
static void guards(void){int i;for(i=0;i<8;i++)if(cw[i]!=0xa5||cw[31752+i]!=0xa5||dw[i]!=0xa5||dw[17416+i]!=0xa5||packed[i]!=0xa5||packed[32008+i]!=0xa5||back[i]!=0xa5||back[32008+i]!=0xa5)fail("guard overwritten");}
static int transform(int dec,int stream,unsigned char *in,int size,unsigned char *out){
 _kernel_swi_regs r;int ip=0,op=0,first=1,iterations=0,ni,no;
 do {
  if(++iterations>20000)fail("transform made no progress");
  ni=size-ip;if(stream&&ni>113)ni=113;no=32000-op;if(stream&&no>61)no=61;
  r.r[0]=(first?0:1)|(ip+ni<size?2:0)|(!stream&&dec?4:0);r.r[1]=(int)(dec?dw+8:cw+8);r.r[2]=(int)(in+ip);r.r[3]=ni;r.r[4]=(int)(out+op);r.r[5]=no;
  call(0x42700+dec,&r);
  if(r.r[1]!=(int)(dec?dw+8:cw+8)||r.r[3]<0||r.r[3]>ni||r.r[5]<0||r.r[5]>no)fail("invalid remainder registers");
  ip+=ni-r.r[3];op+=no-r.r[5];first=0;
  if(r.r[2]!=(int)(in+ip)||r.r[4]!=(int)(out+op)||r.r[0]<0||r.r[0]>2)fail("invalid cursor/status registers");
  if(!dec&&r.r[0]==1&&r.r[3])fail("compress input exhausted count");
  guards();
 }while(r.r[0]);
 if(ip!=size)fail("input not consumed");return op;
}
static void error(int swi,int flags,int ws,int expected){_kernel_swi_regs r;_kernel_oserror *e;r.r[0]=flags;r.r[1]=ws;r.r[2]=(int)plain;r.r[3]=10;r.r[4]=(int)(back+8);r.r[5]=100;e=_kernel_swi(swi,&r,&r);if(!e||e->errnum!=expected){char s[100];sprintf(s,"ERROR wanted %X got %X: %s",expected,e?e->errnum:0,e?e->errmess:"no error");fail(s);}guards();}
static void boundaries(void){
 _kernel_swi_regs r;int flags,i;
 for(flags=0;flags<=2;flags+=2){
  r.r[0]=flags;r.r[1]=(int)(cw+8);r.r[2]=(int)plain;r.r[3]=0;r.r[4]=(int)(packed+8);r.r[5]=32;call(0x42700,&r);
  if(r.r[0]!=(flags?1:0)||r.r[2]!=(int)plain||r.r[3]||r.r[4]!=(int)(packed+8)||r.r[5]!=32)fail("empty input contract");
 }
 plain[0]=0xe7;
 for(i=2;i<=4;i+=2){
  memset(packed+8,0xa5,32);
  r.r[0]=0;r.r[1]=(int)(cw+8);r.r[2]=(int)plain;r.r[3]=1;r.r[4]=(int)(packed+8);r.r[5]=i;call(0x42700,&r);
  if(r.r[0]!=2||packed[8+i]!=0xa5)fail("short output contract");
  r.r[0]=1;r.r[5]=32-((unsigned char *)r.r[4]-(packed+8));call(0x42700,&r);
  if(r.r[0]||r.r[3]||r.r[4]!=(int)(packed+13)||packed[13]!=0xa5)fail("short output continuation");
  if(transform(1,0,packed+8,5,back+8)!=1||back[8]!=0xe7)fail("short output roundtrip");
 }
 memset(cw+8,0,31744);*(unsigned *)(cw+8)=14;error(0x42700,1,(int)(cw+8),0x923);
 memset(dw+8,0,17408);*(unsigned *)(dw+8)=14;error(0x42701,1,(int)(dw+8),0x923);
 guards();message("ARCLIBRE SQUASH BOUNDARIES PASS\r\n");
}
static unsigned char alt[17424], enc[2][4096], original[2][2048], decoded[2][2048];
static void interleaved(void){
 _kernel_swi_regs r;int k,i,j,ip[2]={0,0},op[2]={0,0},status[2]={1,1},first[2]={1,1},lens[2],sizes[2]={1024,2048},ni,no;
 memset(alt,0xa5,sizeof(alt));
 for(k=0;k<2;k++){
  for(i=0;i<sizes[k];i++)original[k][i]=k?i%11:i;
  lens[k]=transform(0,0,original[k],sizes[k],enc[k]);
 }
 for(j=0;j<10000&&(status[0]||status[1]);j++)for(k=0;k<2;k++)if(status[k]){
  ni=lens[k]-ip[k];if(ni>(k?31:17))ni=k?31:17;no=k?61:7;
  if(op[k]+no>2048)no=2048-op[k];
  r.r[0]=(first[k]?0:1)|(ip[k]+ni<lens[k]?2:0);r.r[1]=(int)(k?alt+8:dw+8);r.r[2]=(int)(enc[k]+ip[k]);r.r[3]=ni;r.r[4]=(int)(decoded[k]+op[k]);r.r[5]=no;
  call(0x42701,&r);ip[k]+=ni-r.r[3];op[k]+=no-r.r[5];status[k]=r.r[0];first[k]=0;
  if(ip[k]>lens[k]||op[k]>sizes[k]||status[k]<0||status[k]>2)fail("interleaved cursor/status");
 }
 for(k=0;k<2;k++)if(status[k]||ip[k]!=lens[k]||op[k]!=sizes[k]||memcmp(original[k],decoded[k],sizes[k]))fail("interleaved decode mismatch");
 for(i=0;i<8;i++)if(alt[i]!=0xa5||alt[17416+i]!=0xa5)fail("alternate workspace guard");
 guards();message("ARCLIBRE SQUASH INTERLEAVED PASS\r\n");
}
int ArcLibre_SquashMain(void){
 _kernel_swi_regs r;int task,n,v,i,stream,len,got;unsigned x=0x12345678;char text[120];
 static const int sizes[]={1,256,8192,16000};
 r.r[0]=310;r.r[1]=0x4b534154;r.r[2]=(int)"Squash contracts";r.r[3]=-1;call(0x400c0,&r);task=r.r[1];
 memset(cw,0xa5,sizeof(cw));memset(dw,0xa5,sizeof(dw));memset(packed,0xa5,sizeof(packed));memset(back,0xa5,sizeof(back));
 r.r[0]=8;r.r[1]=16000;call(0x42700,&r);if(r.r[0]!=31744||r.r[1]!=24012)fail("compression size query");
 r.r[0]=8;r.r[1]=-1;call(0x42700,&r);if(r.r[0]!=31744||r.r[1]!=-1)fail("unknown compression size query");
 r.r[0]=8;r.r[1]=16000;call(0x42701,&r);if(r.r[0]!=17408||r.r[1]!=-1)fail("decompression size query");
 boundaries();interleaved();
 for(v=0;v<4;v++){
  n=sizes[v];for(i=0;i<n;i++){x^=x<<13;x^=x>>17;x^=x<<5;plain[i]=v==0?0xe7:v==1?i:v==2?i%7:x;}
  for(stream=0;stream<2;stream++){
   len=transform(0,stream,plain,n,packed+8);
   sprintf(text,"ARCLIBRE SQUASH VECTOR %d %d %X %d\r\n",v,stream,(unsigned)(packed+8),len);message(text);
   got=transform(1,0,packed+8,len,back+8);if(got!=n||memcmp(plain,back+8,n))fail("fast decode mismatch");
   got=transform(1,1,packed+8,len,back+8);if(got!=n||memcmp(plain,back+8,n))fail("restartable decode mismatch");
  }
 }
 error(0x42700,24,(int)(cw+8),0x924);error(0x42701,24,(int)(dw+8),0x924);
 error(0x42702,8,(int)(cw+8),0x920);error(0x42700,0,0x4000000,0x921);
 memset(plain,0,10);error(0x42701,0,(int)(dw+8),0x922);
 r.r[0]=task;r.r[1]=0x4b534154;call(0x400dd,&r);message("ARCLIBRE SQUASH PASS\r\n");return 0;
}
