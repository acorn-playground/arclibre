/* SPDX-License-Identifier: Apache-2.0
 * Host adapter for the unmodified public check_sprite_area C implementation.
 * Tests feed bounded sprite areas; this is an oracle, not guest runtime code.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#define tracef(...) ((void)0)
#define OS_ReadModeVariable 0x35
#define _IN(n) 0
#define _OUT(n) 0
struct error { int number; }; typedef struct error _kernel_oserror;
static _kernel_oserror *_swix(int swi,int flags,int mode,int variable,int *out) {
 (void)flags; if(swi!=OS_ReadModeVariable || variable!=9) abort();
 static _kernel_oserror error;
 int type=(unsigned)mode>>27;
 if(type>=1 && type<=6){*out=type-1;return NULL;}
 return &error;
}
#include "SpriteOp.c"
int main(int argc,char **argv) {
 if(argc!=2)return 2;FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 char buffer[4096]={0};size_t n=fread(buffer,1,sizeof(buffer),f);fclose(f);
 if(n<16)return 2;printf("%d\n",check_sprite_area(buffer));return 0;
}
