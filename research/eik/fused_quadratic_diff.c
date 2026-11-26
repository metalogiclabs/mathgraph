/* Full affected numerical family on both signs, compared with published #49.
 * Research harness only; candidate exports and compiler flags are unchanged.
 */
#include <dlfcn.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef uint32_t (*kernel)(uint32_t);

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    void *a = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    void *b = dlopen(argv[2], RTLD_NOW | RTLD_LOCAL);
    if (!a || !b) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    kernel control = (kernel)dlsym(a, "direct_arm_tanh");
    kernel candidate = (kernel)dlsym(b, "direct_arm_tanh");
    if (!control || !candidate) return 2;
    uint64_t checked = 0, bad = 0;
    for (uint32_t w = 0x3c000000u; w < 0x3e000000u; ++w) {
        for (uint32_t s = 0; s < 2; ++s) {
            uint32_t x = w | (s << 31), want = control(x), got = candidate(x);
            ++checked;
            if (want != got) {
                if (bad < 8) fprintf(stderr, "%08x: %08x != %08x\n", x, got, want);
                ++bad;
            }
        }
    }
    printf("{\"words_checked\":%" PRIu64 ",\"mismatches\":%" PRIu64 "}\n", checked, bad);
    return bad != 0;
}
