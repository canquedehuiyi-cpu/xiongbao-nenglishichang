# -*- coding: utf-8 -*-
"""Downscale rendered page PNGs and flag near-empty / sparse pages by ink coverage.
Usage: python page_scan.py <png_prefix> <page_count>
Writes <prefix><i>_s.png; prints per-page ink fraction and flags.
Thresholds: ink < 0.005 NEAR_EMPTY (widow/blank page suspect); < 0.02 SPARSE (verify visually)."""
import sys
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    prefix, n = sys.argv[1], int(sys.argv[2])
    flags = []
    for i in range(1, n + 1):
        src = f'{prefix}{i}.png'
        try:
            im = Image.open(src).convert('RGB')
        except Exception as e:
            print(f'page {i} OPEN_FAIL {e}')
            continue
        im.thumbnail((1400, 1979))
        im.save(f'{prefix}{i}_s.png')
        g = im.convert('L')
        hist = g.histogram()
        ink = sum(hist[:200]) / float(im.size[0] * im.size[1])
        tag = 'NEAR_EMPTY' if ink < 0.005 else ('SPARSE' if ink < 0.02 else 'OK')
        if tag != 'OK':
            flags.append((i, tag, round(ink, 4)))
        print(f'page {i} ink={ink:.4f} {tag}')
    print('FLAGS', flags if flags else 'none')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('ERROR', type(e).__name__, e)
        sys.exit(1)