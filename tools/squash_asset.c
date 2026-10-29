/* Host-only driver for the pinned public Squash C algorithms. Apache-2.0. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cssr.h"
#include "zssr.h"
int main(int argc, char **argv) {
    assert(argc == 3);
    FILE *f = fopen(argv[1], "rb"); assert(f);
    assert(!fseek(f, 0, SEEK_END)); long n = ftell(f); rewind(f);
    assert(n > 0 && n < 25*1024);
    char *in = calloc(n+16, 1), *out = calloc(4096+16, 1), *back = calloc(25*1024+16, 1);
    assert(in && out && back && fread(in, 1, n, f) == n); fclose(f);
    compress_state *cs = calloc(1, sizeof(*cs)); cs->starting = -1;
    char *cursor = in; unsigned size = 4096;
    assert(compress_store_store(&cursor, n, out, &size, cs, 0) == output_ok);
    assert(cursor == in+n && size < 4096);
    zcat_state *zs = calloc(1, sizeof(*zs)); zs->starting = -1;
    unsigned remaining = size; zcat_result result;
    unsigned decoded = zcat_store_store(out, back, &remaining, 25*1024, 0, zs, &result);
    assert(result == zcat_ok && remaining == 0 && decoded == n && !memcmp(in, back, n));
    f = fopen(argv[2], "wb"); assert(f && fwrite(out, 1, size, f) == size); fclose(f);
    printf("Squash: %ld -> %u bytes; original decoder round-trip verified\n", n, size);
    free(cs); free(zs); free(in); free(out); free(back); return 0;
}
