/* Native IEEE-754 layout adapter for AsAsm on little-endian Darwin.
 * Original adapter, 2026 ARM2 experiment; Apache-2.0.
 * Field names match AsAsm's usage. No runtime code enters the ARM output. */
#ifndef ARM2_EXPERIMENT_IEEE754_H
#define ARM2_EXPERIMENT_IEEE754_H
#include <float.h>
#include <stdint.h>
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__ || FLT_RADIX != 2 || FLT_MANT_DIG != 24 || DBL_MANT_DIG != 53
#error This adapter requires a little-endian IEEE-754 host
#endif
union ieee754_float {
    float f;
    struct { unsigned int mantissa:23, exponent:8, negative:1; } ieee;
};
union ieee754_double {
    double d;
    struct { unsigned int mantissa1:32, mantissa0:20, exponent:11, negative:1; } ieee;
};
_Static_assert(sizeof(union ieee754_float) == 4, "float layout");
_Static_assert(sizeof(union ieee754_double) == 8, "double layout");
#endif
