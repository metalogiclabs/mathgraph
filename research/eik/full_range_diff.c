/* Finite source-relative comparison. This is not a correctly-rounded reference. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

typedef uint32_t (*kernel)(uint32_t);
int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s control.so candidate.so function lo hi\n", argv[0]);
        return 2;
    }
    char *end;
    uint64_t lo = strtoull(argv[4], &end, 0);
    if (*end || lo >= (1ull << 32)) return 2;
    uint64_t hi = strtoull(argv[5], &end, 0);
    if (*end || hi > (1ull << 32) || hi <= lo) return 2;
    void *a = dlopen(argv[1], RTLD_NOW), *b = dlopen(argv[2], RTLD_NOW);
    if (!a || !b) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    kernel control = (kernel)dlsym(a, argv[3]), candidate = (kernel)dlsym(b, argv[3]);
    if (!control || !candidate) return 2;
    uint64_t wrong = 0;
    for (uint64_t w = lo; w < hi; ++w) {
        uint32_t expected = control((uint32_t)w), got = candidate((uint32_t)w);
        if (expected != got) {
            if (wrong < 8)
                printf("mismatch input=%08x control=%08x candidate=%08x\n", (uint32_t)w, expected, got);
            ++wrong;
        }
    }
    printf("{\"function\":\"%s\",\"lo\":%llu,\"hi\":%llu,\"words\":%llu,\"mismatches\":%llu}\n",
           argv[3], (unsigned long long)lo, (unsigned long long)hi,
           (unsigned long long)(hi-lo), (unsigned long long)wrong);
    return wrong != 0;
}
