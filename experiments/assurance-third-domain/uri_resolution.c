/* RFC 3986 relative-reference resolution harness; research only.
 * Source library is checked out separately at a pinned Git commit.
 * No claim of an upstream defect or owner-approved behavioral change. */
#include <stdio.h>
#include <string.h>
#include <uriparser/Uri.h>
int main(int argc, char **argv) {
    UriUriA base = {0}, ref = {0}, out = {0};
    const char *err = NULL;
    char buf[4096];
    int written = 0, rc = 0;
    if (argc != 3) return 2;
    if (uriParseSingleUriA(&base, argv[1], &err) != URI_SUCCESS) return 3;
    if (uriParseSingleUriA(&ref, argv[2], &err) != URI_SUCCESS) { rc = 4; goto cleanup; }
    if (uriAddBaseUriA(&out, &ref, &base) != URI_SUCCESS) { rc = 5; goto cleanup; }
    if (uriToStringA(buf, &out, sizeof(buf), &written) != URI_SUCCESS) { rc = 6; goto cleanup; }
    puts(buf);
cleanup:
    uriFreeUriMembersA(&out);
    uriFreeUriMembersA(&ref);
    uriFreeUriMembersA(&base);
    return rc;
}
