/* Darwin build adapter, 2026 ARM2 experiment. Apache-2.0.
 * Native byte order only; target ARM format remains configured separately. */
#ifndef ARM2_EXPERIMENT_SYS_ENDIAN_H
#define ARM2_EXPERIMENT_SYS_ENDIAN_H
#include <machine/endian.h>
#ifndef _BYTE_ORDER
#define _BYTE_ORDER __BYTE_ORDER__
#define _LITTLE_ENDIAN __ORDER_LITTLE_ENDIAN__
#define _BIG_ENDIAN __ORDER_BIG_ENDIAN__
#endif
#endif
