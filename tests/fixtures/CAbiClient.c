/* SPDX-License-Identifier: Apache-2.0 */
/* Exercise the real original C runtime through its public APCS-26 entry table. */
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <kernel.h>
#include <setjmp.h>
extern int setjmp(jmp_buf) __asm__("ArcLibre_setjmp") __attribute__((returns_twice));
extern void longjmp(jmp_buf,int) __asm__("ArcLibre_longjmp") __attribute__((noreturn));
extern void ArcLibre_StackLeaf_O2(unsigned *,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
extern void ArcLibre_StackLeaf_Os(unsigned *,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
extern unsigned ArcLibre_StackFrame_O2(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
extern unsigned ArcLibre_StackFrame_Os(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
static jmp_buf environment;
static volatile int jump_depth;
static int jump_nested(int n,int value) {
 volatile int pad[256];pad[0]=n;jump_depth++;
 if(n)return jump_nested(n-1,value)+pad[0];
 longjmp(environment,value);
}
static char *const names[]={"alpha","beta","gamma"};
static int values[]={9,-4,17,0,3};
static volatile int numerator=-107,denominator=13;
static volatile unsigned unumerator=4000000000U,udenominator=17;
static volatile double angle=0.25;
static int format(char *s,const char *fmt,...) {
 va_list ap;int n;va_start(ap,fmt);n=vsprintf(s,fmt,ap);va_end(ap);return n;
}
static int compare(const void *a,const void *b) {return *(const int *)a-*(const int *)b;}
static void message(const char *s) {_kernel_swi_regs r;r.r[0]=(int)s;_kernel_swi(2,&r,&r);}
int ArcLibre_CAbiMain(void) {
 char text[160],*heap;int i,key=3,*found,jump;
 unsigned stack_args[5]={0x11223344U,0,0,0,0x55667788U};
 ArcLibre_StackLeaf_O2(stack_args+1,1,2,4,8,0x87654321U,0xfedcba98U);
 if(stack_args[1]!=15 || stack_args[2]!=0x87654321U || stack_args[3]!=0xfedcba98U)goto failed;
 ArcLibre_StackLeaf_Os(stack_args+1,16,32,64,128,0x13579bdfU,0x2468ace0U);
 if(stack_args[1]!=240 || stack_args[2]!=0x13579bdfU || stack_args[3]!=0x2468ace0U)goto failed;
 if(stack_args[0]!=0x11223344U || stack_args[4]!=0x55667788U)goto failed;
 if(ArcLibre_StackFrame_O2(1,2,4,8,16,32,64)!=127)goto failed;
 if(ArcLibre_StackFrame_Os(128,256,512,1024,2048,4096,8192)!=16256)goto failed;
 message("STACK ARGUMENTS O2/Os PASS\r\n");
 if(sizeof(jmp_buf)!=22*4)goto failed;
 jump=setjmp(environment);if(!jump)jump_nested(32,7);
 sprintf(text,"JUMP 7: %d depth %d\r\n",jump,jump_depth);message(text);
 if(jump!=7 || jump_depth!=33)goto failed;
 jump_depth=0;jump=setjmp(environment);if(!jump)jump_nested(2,0);
 sprintf(text,"JUMP 0: %d depth %d\r\n",jump,jump_depth);message(text);
 if(jump!=1 || jump_depth!=3)goto failed;
 if(numerator/denominator!=-8 || numerator%denominator!=-3)goto failed;
 if(unumerator/udenominator!=235294117U || unumerator%udenominator!=11)goto failed;
 if(strcmp(names[1],"beta"))goto failed;
 if(format(text,"%s %d %u %08X %.3f",names[2],-107,13U,0x1234ABCDU,1.25)!=28)goto failed;
 if(strcmp(text,"gamma -107 13 1234ABCD 1.250"))goto failed;
 heap=malloc(37);if(!heap)goto failed;
 for(i=0;i<37;i++)heap[i]=(char)(i*7);
 heap=realloc(heap,4097);if(!heap)goto failed;
 for(i=0;i<37;i++)if(heap[i]!=(char)(i*7))goto failed;
 free(heap);
 qsort(values,5,sizeof(int),compare);found=bsearch(&key,values,5,sizeof(int),compare);
 if(!found || *found!=3 || values[0]!=-4 || values[4]!=17)goto failed;
 if(fabs(sin(angle)-0.24740395925452294)>1e-10 || fabs(atan(angle)-0.24497866312686414)>1e-10 || sqrt(9.0)!=3.0)goto failed;
 message("ARCLIBRE C ABI PASS\r\n");return 0;
failed:message("ARCLIBRE C ABI FAIL\r\n");return 1;
}
