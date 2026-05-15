"""
Generates assets/icon.ico for the TallyInsights Electron app.
Uses only Python stdlib — no Pillow or other dependencies needed.
Creates a 32x32 icon with the TallyInsights colour scheme.
"""

import os
import struct
import math


def make_ico(filename, size=32):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    # ── Draw pixels (BGRA, bottom-to-top row order for BMP) ──────────────────
    pixels = []
    cx, cy = size / 2, size / 2
    r_outer = size / 2 - 1
    r_inner = size / 2 - 5

    for y in range(size - 1, -1, -1):   # BMP stores rows bottom-up
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= r_inner:
                # Inner circle — bright indigo
                pixels += [0xFF, 0x99, 0x46, 0xFF]   # BGRA #4699FF
            elif dist <= r_outer:
                # Ring — dark slate blue
                pixels += [0x8B, 0x3A, 0x1E, 0xFF]   # BGRA #1E3A8B
            else:
                # Outside — fully transparent
                pixels += [0x00, 0x00, 0x00, 0x00]

    pixel_data = bytes(pixels)                  # 32*32*4 = 4 096 bytes
    and_mask   = bytes(size * (size // 8))      # all-zero = opaque (not used for 32-bit)

    bmp_header = struct.pack(
        '<IiiHHIIiiII',
        40,               # biSize
        size,             # biWidth
        size * 2,         # biHeight (XOR + AND combined in ICO format)
        1,                # biPlanes
        32,               # biBitCount
        0,                # biCompression (BI_RGB)
        len(pixel_data),  # biSizeImage
        0, 0, 0, 0,       # pels/metre, colours used/important
    )

    image_data = bmp_header + pixel_data + and_mask

    # ICONDIR  (6 bytes)
    icon_dir = struct.pack('<HHH', 0, 1, 1)

    # ICONDIRENTRY  (16 bytes);  image starts right after dir + 1 entry
    offset = 6 + 16
    entry = struct.pack(
        '<BBBBHHII',
        size, size,        # width, height
        0,                 # colour count (0 = ≥256)
        0,                 # reserved
        1,                 # planes
        32,                # bit depth
        len(image_data),
        offset,
    )

    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with open(filename, 'wb') as f:
        f.write(icon_dir + entry + image_data)

    print(f'Icon created: {filename}')


if __name__ == '__main__':
    make_ico('assets/icon.ico')
