#include <csp/csp.h>
#include <csp/csp_rtable.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned counted;
static bool count(void *ctx, csp_route_t *route)
{
	(void)ctx; (void)route;
	counted++;
	return true;
}
static unsigned route_count(void)
{
	counted = 0;
	csp_rtable_iterate(count, NULL);
	return counted;
}
int main(int argc, char **argv)
{
	if (argc != 2) return 2;
	csp_conf.version = (unsigned)strtoul(argv[1], NULL, 0);
	csp_iface_t iface = {.name = "SYNTHETIC"};
	csp_rtable_free();
	printf("capacity\t%d\n", CSP_RTABLE_SIZE);
	printf("op\tkey\treturn\tcount\tfound\tvia\n");
	for (unsigned address = 1; address <= CSP_RTABLE_SIZE + 1; ++address) {
		int rc = csp_rtable_set(address, -1, &iface, CSP_NO_VIA_ADDRESS);
		csp_route_t *route = csp_rtable_find_route(address);
		printf("insert\t%u\t%d\t%u\t%d\t%u\n", address, rc, route_count(), route != NULL,
		       route ? route->via : 0);
	}
	for (unsigned address = 1; address <= CSP_RTABLE_SIZE + 1; ++address) {
		csp_route_t *route = csp_rtable_find_route(address);
		printf("lookup\t%u\t0\t%u\t%d\t%u\n", address, route_count(), route != NULL,
		       route ? route->via : 0);
	}
	int rc = csp_rtable_set(1, -1, &iface, 7);
	csp_route_t *route = csp_rtable_find_route(1);
	printf("update\t1\t%d\t%u\t%d\t%u\n", rc, route_count(), route != NULL,
	       route ? route->via : 0);
	for (unsigned address = 1; address <= CSP_RTABLE_SIZE + 1; ++address) {
		route = csp_rtable_find_route(address);
		printf("postlookup\t%u\t0\t%u\t%d\t%u\n", address, route_count(), route != NULL,
		       route ? route->via : 0);
	}
	rc = csp_rtable_set(2, -1, NULL, CSP_NO_VIA_ADDRESS);
	route = csp_rtable_find_route(2);
	printf("reject-null\t2\t%d\t%u\t%d\t%u\n", rc, route_count(), route != NULL,
	       route ? route->via : 0);
	csp_rtable_free();
	printf("clear\t1\t0\t%u\t%d\t0\n", route_count(), csp_rtable_find_route(1) != NULL);
	return 0;
}
