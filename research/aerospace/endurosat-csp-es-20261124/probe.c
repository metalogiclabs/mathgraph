#include <csp/csp.h>
#include <csp/arch/csp_time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "csp_dedup.h"

static uint32_t now_ms;
uint32_t __wrap_csp_get_ms(void) { return now_ms; }

static int observe(uint32_t timestamp, unsigned char payload)
{
	csp_packet_t packet = {0};
	packet.id = (csp_id_t){.pri = 1, .src = 2, .dst = 3, .dport = 10, .sport = 20};
	packet.length = 1;
	packet.data[0] = payload;
	now_ms = timestamp;
	return csp_dedup_is_duplicate(&packet);
}

int main(int argc, char **argv)
{
	if (argc != 5) return 2;
	csp_conf.version = (uint8_t)strtoul(argv[1], NULL, 0);
	uint32_t start = (uint32_t)strtoull(argv[2], NULL, 0);
	uint32_t elapsed = (uint32_t)strtoull(argv[3], NULL, 0);
	unsigned others = (unsigned)strtoul(argv[4], NULL, 0);
	int first = observe(start, 1);
	int other_errors = 0;
	for (unsigned i = 0; i < others; ++i)
		other_errors += observe(start, (unsigned char)(i + 2));
	int repeated = observe(start + elapsed, 1);
	printf("%u\t%u\t%u\t%u\t%d\t%d\t%d\n", csp_conf.version,
	       start, elapsed, others, first, other_errors, repeated);
	return 0;
}
