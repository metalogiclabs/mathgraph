#include <csp/csp.h>
#include <csp/csp_rtable.h>
#include <stdio.h>

int main(void) {
	csp_iface_t iface = {.name = "TEST"};
	csp_conf.version = 2;
	csp_rtable_free();
	for (unsigned int i = 1; i <= CSP_RTABLE_SIZE + 1; i++) {
		int rc = csp_rtable_set(i, -1, &iface, CSP_NO_VIA_ADDRESS);
		printf("route %u: rc=%d, lookup=%s\n", i, rc,
		       csp_rtable_find_route(i) ? "found" : "NULL");
	}
	return 0;
}
