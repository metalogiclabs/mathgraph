#include <csp/csp.h>
#include <csp/csp_id.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char payload_byte(unsigned i) { return (unsigned char)(37 * i + 11); }
static int payload_ok(const csp_packet_t *p, unsigned length)
{
	for (unsigned i = 0; i < length; i++)
		if (p->data[i] != payload_byte(i)) return 0;
	return 1;
}

int main(void)
{
	unsigned id, version, fixup, length, pri, src, dst, dport, sport, flags;
	char operation, hex[32];
	while (scanf("%u %c %u %u %u %u %u %u %u %u %u %31s", &id, &operation,
	             &version, &fixup, &length, &pri, &src, &dst, &dport, &sport, &flags, hex) == 12) {
		if (length > CSP_BUFFER_SIZE) return 2;
		csp_conf.version = version;
		csp_packet_t packet = {0};
		packet.id = (csp_id_t){.pri = pri, .src = src, .dst = dst, .dport = dport, .sport = sport, .flags = flags};
		csp_id_t input_id = packet.id;
		for (unsigned i = 0; i < length; ++i) packet.data[i] = payload_byte(i);
		packet.length = length;
		int header = csp_id_setup_rx(&packet);
		if (operation == 'E') {
			if (fixup) csp_id_prepend_fixup_cspv1(&packet); else csp_id_prepend(&packet);
			printf("%u E ", id);
			for (int i = 0; i < header; ++i) printf("%02x", packet.frame_begin[i]);
			printf(" %u %td %d %d", packet.frame_length, packet.frame_begin - (unsigned char *)&packet,
			       payload_ok(&packet, length), !memcmp(&packet.id, &input_id, sizeof(input_id)));
			memset(&packet.id, 0, sizeof(packet.id));
			int rc = fixup ? csp_id_strip_fixup_cspv1(&packet) : csp_id_strip(&packet);
			printf(" %d\n", rc == 0 && packet.length == length && !memcmp(&packet.id, &input_id, sizeof(input_id)));
		} else if (operation == 'D') {
			unsigned bytes = (unsigned)strlen(hex) / 2;
			if (strcmp(hex, "-") == 0) bytes = 0;
			if (bytes > (unsigned)header) return 3;
			for (unsigned i = 0; i < bytes; ++i) {
				unsigned byte;
				if (sscanf(hex + 2 * i, "%2x", &byte) != 1) return 4;
				packet.frame_begin[i] = byte;
			}
			packet.frame_length = bytes + length;
			if (bytes < (unsigned)header && length) return 5;
			packet.length = 0x1234;
			int rc = fixup ? csp_id_strip_fixup_cspv1(&packet) : csp_id_strip(&packet);
			printf("%u D %d %u %u %u %u %u %u %u %d %td\n", id, rc, packet.length,
			       packet.id.pri, packet.id.src, packet.id.dst, packet.id.dport, packet.id.sport,
			       packet.id.flags, payload_ok(&packet, length), packet.frame_begin - (unsigned char *)&packet);
		} else return 6;
	}
	return feof(stdin) ? 0 : 7;
}
