#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check Sound_Configure against VIDC registers and independently timed DMA bytes."""
import json
from pathlib import Path


def verify(path):
    rows = json.loads(Path(path).read_text())
    cases = [(c, p) for p in (48, 80) for c in (1, 2, 4, 8)]
    assert len(rows) == 2 * len(cases)
    results = []
    for (channels, period), start, end in zip(cases, rows[::2], rows[1::2]):
        assert start['marker'] == 'ARCLIBRE SOUND RATE START'
        assert end['marker'] == 'ARCLIBRE SOUND RATE END'
        byte_period = period // channels
        sfr = 0x100 | (byte_period - 2)
        for row in (start, end):
            assert (row['channels'], row['period_us'], row['reported_period_us']) == (channels, period, period)
            assert row['sfr'] == sfr, (channels, period, hex(row['sfr']), hex(sfr))
        ticks = end['ticks'] - start['ticks']
        count = end['bytes'] - start['bytes']
        # A440 master scheduler is 24 MHz. Each DMA event emits 16 bytes;
        # the endpoints can straddle one event, so allow one event of error.
        expected = ticks / (24 * byte_period)
        # Includes printing the start marker, which can scroll the screen.
        assert 0.19 < ticks / 24_000_000 < 0.5
        assert abs(count - expected) <= 16, (channels, period, count, expected)
        results.append(dict(channels=channels, sample_period_us=period,
                            sfr=sfr, elapsed_ticks=ticks, emitted_bytes=count,
                            expected_bytes=expected, error_bytes=count-expected))
    return results


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(sys.argv[1]), indent=2))
