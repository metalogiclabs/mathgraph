#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
typedef uint32_t (*fn)(uint32_t);
static uint64_t checks;
static void word(fn *a,fn *b,uint32_t w) {
 for(unsigned j=0;j<3;j++) {uint32_t x=a[j](w),y=b[j](w);checks++;if(x!=y){fprintf(stderr,"mismatch fn=%u input=%08x baseline=%08x candidate=%08x\n",j,w,x,y);exit(1);}}
}
int main(int argc,char**argv) {
 if(argc!=3)return 2;
 void *a=dlopen(argv[1],RTLD_NOW),*b=dlopen(argv[2],RTLD_NOW);if(!a||!b){puts(dlerror());return 2;}
 char *n[]={"eik_sigmoid","eik_tanh","eik_exp"};fn aa[3],bb[3];for(unsigned j=0;j<3;j++){aa[j]=(fn)dlsym(a,n[j]);bb[j]=(fn)dlsym(b,n[j]);if(!aa[j]||!bb[j])return 2;}
 uint32_t state=0x3c6ef372u;
 for(uint32_t i=0;i<(1u<<21);i++){state=1664525u*state+1013904223u;word(aa,bb,state);}
 for(unsigned sign=0;sign<2;sign++)for(unsigned e=0;e<256;e++)for(int d=-1024;d<=1024;d++)word(aa,bb,(sign<<31)+(e<<23)+(uint32_t)d);
 for(unsigned sign=0;sign<2;sign++)for(uint32_t w=0x3d800000u;w<0x43000000u;w+=1u<<16)for(int d=-8;d<=8;d++)word(aa,bb,(sign<<31)+w+(uint32_t)d);
 printf("%llu checked, zero mismatches\n",(unsigned long long)checks);
 return 0;
}
