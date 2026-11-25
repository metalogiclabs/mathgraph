#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "monitor.h"

float kias;
static uint32_t callbacks;
void handlerLPC_KIAS_0(void) { ++callbacks; }

int main(int argc, char **argv) {
  if (sizeof(float) != sizeof(uint32_t)) return 66;
  if (argc < 2) return 64;
  for (int i = 1; i < argc; ++i) {
    char *end;
    kias = strtof(argv[i], &end);
    if (end == argv[i] || *end != '\0' || !isfinite(kias)) return 65;
    step();
    uint32_t bits;
    memcpy(&bits, &kias, sizeof(bits));
    printf("%08" PRIx32 " %" PRIu32 "\n", bits, callbacks);
  }
  return 0;
}
