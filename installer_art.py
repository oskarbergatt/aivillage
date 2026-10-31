"""Small original pixel-art assets for the installer builders (no image dependencies)."""
from pathlib import Path
import struct


def _pixel(x: int, y: int) -> tuple[int, int, int]:
    """A 64x64 village scene, returned in RGB."""
    if y < 39:
        color = (105, 174, 190) if y < 25 else (136, 194, 188)
        if (x - 48) ** 2 + (y - 12) ** 2 < 36:
            color = (246, 218, 141)
    else:
        color = (92, 148, 82) if (x // 4 + y // 4) % 3 else (104, 158, 90)
    if 12 <= x < 49 and 27 <= y < 53:
        color = (226, 214, 188)
    if 7 <= x < 54 and 17 <= y < 30 and abs(x - 30) <= (y - 14) * 2:
        color = (158, 74, 62) if y % 4 else (124, 54, 46)
    if 27 <= x < 35 and 37 <= y < 53:
        color = (96, 68, 44)
    if (17 <= x < 23 or 39 <= x < 45) and 33 <= y < 40:
        color = (250, 214, 138)
    if 3 <= x < 8 and 33 <= y < 50:
        color = (96, 68, 44)
    if 0 <= x < 12 and 25 <= y < 39 and (x - 6) ** 2 + (y - 32) ** 2 < 44:
        color = (66, 118, 72)
    return color


def _write_bitmap(path: Path, width: int, height: int, pixel) -> None:
    """Write an uncompressed 24-bit Windows bitmap."""
    stride = (width * 3 + 3) & ~3
    data_size = stride * height
    header = struct.pack("<2sIHHI", b"BM", 54 + data_size, 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                          data_size, 2835, 2835, 0, 0)
    with path.open("wb") as out:
        out.write(header)
        for y in range(height - 1, -1, -1):
            row = bytearray()
            for x in range(width):
                r, g, b = pixel(x, y)
                row.extend((b, g, r))
            row.extend(b"\0" * (stride - len(row)))
            out.write(row)


def write_bitmap(path: Path, width: int, height: int) -> None:
    """Scale the icon scene with crisp nearest-neighbor pixels."""
    _write_bitmap(path, width, height,
                  lambda x, y: _pixel(x * 64 // width, y * 64 // height))


def _background_pixel(x: int, y: int, width: int, height: int, arrow: bool) -> tuple[int, int, int]:
    """A pale village landscape with a clear center for installer controls."""
    x, y = x * 160 // width, y * 105 // height
    color = (232, 241, 224) if y < 63 else (188, 214, 170)
    if y >= 79:
        color = (145, 187, 125) if (x // 8 + y // 4) % 3 else (154, 195, 134)
    if (x - 132) ** 2 + (y - 17) ** 2 < 64:
        color = (250, 224, 155)
    if arrow and ((72 <= x < 87 and 51 <= y < 54) or
                  (84 <= x < 90 and abs(y - 52) <= 90 - x)):
        color = (120, 145, 119)
    for cx in (11, 146):
        if cx - 5 <= x < cx + 6 and 73 <= y < 99:
            color = (169, 141, 105)
        if (x - cx) ** 2 + (y - 70) ** 2 < 180:
            color = (130, 177, 121)
    for left in (23, 108):
        if left <= x < left + 26 and 77 <= y < 96:
            color = (231, 214, 184)
        if left - 3 <= x < left + 29 and 70 <= y < 79 and abs(x - (left + 13)) <= (y - 67) * 2:
            color = (185, 126, 110)
        if left + 10 <= x < left + 16 and 84 <= y < 96:
            color = (148, 111, 86)
    return color


def write_background_bitmap(path: Path, width: int, height: int, *, arrow: bool = True) -> None:
    _write_bitmap(path, width, height,
                  lambda x, y: _background_pixel(x, y, width, height, arrow))


def write_svg(path: Path) -> None:
    path.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" shape-rendering="crispEdges">
<rect width="64" height="64" fill="#69aebe"/><rect y="39" width="64" height="25" fill="#5c9452"/>
<circle cx="48" cy="12" r="6" fill="#f6da8d"/><rect x="12" y="27" width="37" height="26" fill="#e2d6bc"/>
<path d="M7 29 L30 15 L54 29 Z" fill="#9e4a3e"/><rect x="27" y="37" width="8" height="16" fill="#60442c"/>
<path d="M17 33h6v7h-6z M39 33h6v7h-6z" fill="#fada8a"/></svg>\n''', encoding="utf-8")


def write_ico(path: Path) -> None:
    """Write a 32-bit Windows icon with the same village artwork."""
    size = 32
    pixels = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            r, g, b = _pixel(x * 2, y * 2)
            pixels.extend((b, g, r, 255))
    mask = b"\0" * (4 * size)
    dib = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                      len(pixels), 0, 0, 0, 0) + pixels + mask
    directory = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(dib), 22)
    path.write_bytes(directory + entry + dib)
