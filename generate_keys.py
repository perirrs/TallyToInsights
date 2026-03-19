#!/usr/bin/env python3
"""
TallyInsights — Product Key Generator
======================================
KEEP THIS FILE SECRET. Do NOT include it in the distributed application.

The MASTER_SECRET here must exactly match the one in electron/product-key.js.

Usage:
  python generate_keys.py              # Generate keys #1–10
  python generate_keys.py 50           # Generate 50 keys starting at #1
  python generate_keys.py 20 101       # Generate 20 keys starting at #101
  python generate_keys.py validate TALLY-ABCDE-FGHIJ-KLMNO-PQRST
"""

import hmac
import hashlib
import base64
import sys

# ── MUST match electron/product-key.js ────────────────────────────────────
MASTER_SECRET = 'PERIRRS-TALLY-INSIGHTS-OFFLINE-KEY-2024-XK9M7N2P'
# ──────────────────────────────────────────────────────────────────────────

BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'


def _base32_encode(data: bytes) -> str:
    result = ''
    bits = 0
    value = 0
    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            result += BASE32_ALPHABET[(value >> (bits - 5)) & 31]
            bits -= 5
    if bits > 0:
        result += BASE32_ALPHABET[(value << (5 - bits)) & 31]
    return result


def generate_key(serial: int) -> str:
    """Generate a product key for the given serial (1–9999)."""
    assert 1 <= serial <= 9999, 'Serial must be 1–9999'
    buf = serial.to_bytes(4, 'big')
    sig = hmac.new(MASTER_SECRET.encode(), buf, hashlib.sha256).digest()
    code = _base32_encode(sig[:15])  # 24 base32 chars
    return f'TALLY-{code[0:5]}-{code[5:10]}-{code[10:15]}-{code[15:20]}'


def validate_key(key: str) -> int | None:
    """Validate a key; returns serial number or None if invalid."""
    clean = key.upper().strip()
    parts = clean.split('-')
    if len(parts) != 5 or parts[0] != 'TALLY':
        return None
    if not all(len(p) == 5 for p in parts[1:]):
        return None
    encoded = ''.join(parts[1:])

    for serial in range(1, 10000):
        expected = generate_key(serial)
        expected_encoded = ''.join(expected.split('-')[1:])
        if expected_encoded == encoded:
            return serial
    return None


def main():
    args = sys.argv[1:]

    if args and args[0] == 'validate':
        if len(args) < 2:
            print('Usage: python generate_keys.py validate <KEY>')
            sys.exit(1)
        key = args[1]
        serial = validate_key(key)
        if serial is not None:
            print(f'✓ Valid key — Serial #{serial:04d}')
        else:
            print('✗ Invalid key')
        return

    count = int(args[0]) if args else 10
    start = int(args[1]) if len(args) > 1 else 1

    print(f'TallyInsights Product Keys — {count} keys starting at serial #{start}')
    print('=' * 60)
    for i in range(start, start + count):
        print(f'  #{i:04d}  {generate_key(i)}')
    print('=' * 60)
    print(f'Keep these keys secure. Each key is machine-locked on first activation.')


if __name__ == '__main__':
    main()
