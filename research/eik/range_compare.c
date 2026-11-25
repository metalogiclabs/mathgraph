/* Host differential evidence, 2026-11-25, not independent reference qualification.
 * Reconstruct rrr.c: python variants.py original.c rrr.c
 * Reconstruct variants: python degree.py rrr.c both15.c both15
 *                       python degree.py rrr.c both31.c both31
 *                       python adaptive.py rrr.c adaptive-both.c both
 * Baseline SHA256: 3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4
 * Candidate SHA256:
 * both15 7a59f775d93e4a37f745e88fb997b0d3d132894a853751952a7dbd706e40434d
 * both31 f32769c47320cd837ddd6985b0949b2b9e5c8500e5bee5276b755d403c5e7c86
 * adaptive-both 8c6fb01dc70cc4328862acdf78d47f77eb6897e1eac95248b892fe6b2f4408e2
 * gcc -O2 -shared -fPIC -include stdint.h rrr.c -o rrr.so
 * gcc -O2 -shared -fPIC -include stdint.h CANDIDATE.c -o CANDIDATE.so
 * gcc -O3 range_compare.c -ldl -o range_compare
 * ./range_compare ./rrr.so ./CANDIDATE.so
 * Observed, for each of the three variants:
 * eik_sigmoid 134217728 comparisons 0 mismatches
 * eik_tanh 150994944 comparisons 0 mismatches
 * exit=0
 * Total 855638016. All nine degree reduction variants rejected on performance
 * at official seed 20261125: https://github.com/metalogiclabs/mathgraph/actions/runs/45546268345
 */
#include <stdint.h>
#include <stdio.h>
#include <dlfcn.h>
typedef uint32_t (*fn)(uint32_t);
int main(int argc,char **argv){
 if(argc!=3)return 2;
 void *a=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL),*b=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
 if(!a||!b){fprintf(stderr,"%s\n",dlerror());return 2;}
 const char *names[]={"eik_sigmoid","eik_tanh"};
 /* Include both full regions of the changed coefficient tables and the
    surrounding dispatch ranges. Test both signs, with all mantissas. */
 uint32_t lo[]={0x3e000000u,0x3d000000u};
 uint32_t hi[]={0x42000000u,0x41800000u};
 for(int j=0;j<2;j++){
  fn x=(fn)dlsym(a,names[j]),y=(fn)dlsym(b,names[j]);if(!x||!y)return 2;
  uint64_t n=0,wrong=0;
  for(unsigned sign=0;sign<2;sign++)for(uint32_t i=lo[j];i<hi[j];i++){
   uint32_t w=i|(sign<<31);uint32_t v=x(w),q=y(w);
   if(v!=q){if(wrong<10)fprintf(stderr,"mismatch %s %08x %08x %08x\n",names[j],w,v,q);wrong++;}
   n++;
  }
  printf("%s %llu comparisons %llu mismatches\n",names[j],(unsigned long long)n,(unsigned long long)wrong);fflush(stdout);
  if(wrong)return 1;
 }
 return 0;
}
