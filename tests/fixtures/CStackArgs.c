/* SPDX-License-Identifier: Apache-2.0 */
/* Separate translation unit: prevent constant folding of APCS stack arguments. */
void ArcLibre_StackLeaf(unsigned *out, unsigned a, unsigned b, unsigned c,
                       unsigned d, unsigned e, unsigned f)
{
    out[0] = a | b | c | d;
    out[1] = e;
    out[2] = f;
}

unsigned ArcLibre_StackFrame(unsigned a, unsigned b, unsigned c, unsigned d,
                            unsigned e, unsigned f, unsigned g)
{
    volatile unsigned scratch[300];
    scratch[0] = a; scratch[129] = b; scratch[299] = c;
    return scratch[0] + scratch[129] + scratch[299] + d + e + f + g;
}
