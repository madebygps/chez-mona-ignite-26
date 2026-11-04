"""Receipt layout as ESC/POS bytes and as a PNG preview."""

from __future__ import annotations

import io
import re
import textwrap
from dataclasses import dataclass

import qrcode
from PIL import Image, ImageDraw, ImageFont

HEADER = "Chez Mona"
FOOTER = "Microsoft Ignite 2026"
QR_CAPTION = "Scan to learn more"
FONT_A_WIDTH = 12  # dots per character, Font A at normal size
QR_TARGET_FRACTION = 0.55

ESC, GS = b"\x1b", b"\x1d"


@dataclass
class Line:
    text: str
    big: bool = False
    bold: bool = False


def plain(text: str) -> str:
    """Strip the small Markdown subset used in content and keep printable ASCII."""
    text = re.sub(r"\*\*|`", "", text)
    return text.encode("ascii", "replace").decode("ascii")


def layout(dish: dict) -> list[Line | str | None]:
    """Receipt as a list of Lines, the string 'QR', and None for a blank line."""
    return [
        Line(HEADER, big=True, bold=True),
        None,
        Line(dish["dish"], bold=True),
        Line(dish["lab"]),
        None,
        Line(dish["receipt"]["learned"]),
        "QR",
        Line(QR_CAPTION),
        None,
        Line(FOOTER),
    ]


def qr_image(url: str, width_dots: int) -> Image.Image:
    """Monochrome QR code centered on a strip exactly width_dots wide."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    modules = qr.modules_count
    box = max(1, int(width_dots * QR_TARGET_FRACTION) // modules)
    code = qr.make_image(fill_color="black", back_color="white").get_image()
    code = code.convert("1").resize((modules * box, modules * box), Image.NEAREST)
    quiet = 4 * box
    strip = Image.new("1", (width_dots, code.height + 2 * quiet), 1)
    strip.paste(code, ((width_dots - code.width) // 2, quiet))
    return strip


def raster(image: Image.Image) -> bytes:
    """GS v 0 raster bit image. Width must be a multiple of 8."""
    image = image.convert("1")
    width, height = image.size
    if width % 8:
        raise ValueError("raster width must be a multiple of 8")
    # PIL mode "1" packs 1 as white; printers expect 1 as black.
    data = bytes(b ^ 0xFF for b in image.tobytes())
    x_bytes = width // 8
    return GS + b"v0\x00" + bytes([x_bytes & 0xFF, x_bytes >> 8, height & 0xFF, height >> 8]) + data


def escpos(dish: dict, width_dots: int) -> bytes:
    columns = width_dots // FONT_A_WIDTH
    out = bytearray(ESC + b"@" + ESC + b"a\x01")
    for item in layout(dish):
        if item is None:
            out += b"\n"
        elif item == "QR":
            out += raster(qr_image(dish["receipt"]["qr"], width_dots))
            out += b"\n"
        else:
            size = b"\x11" if item.big else b"\x00"
            cols = columns // 2 if item.big else columns
            out += GS + b"!" + size + ESC + b"E" + (b"\x01" if item.bold else b"\x00")
            for line in textwrap.wrap(plain(item.text), cols) or [""]:
                out += line.encode("ascii") + b"\n"
            out += GS + b"!\x00" + ESC + b"E\x00"
    # Feed past the cutter, then partial cut.
    out += ESC + b"d\x04" + GS + b"V\x42\x00"
    return bytes(out)


def preview_png(dish: dict, width_dots: int) -> bytes:
    """Approximate picture of the printed receipt, for dry runs and staff checks."""
    columns = width_dots // FONT_A_WIDTH
    normal = ImageFont.load_default(size=22)
    big = ImageFont.load_default(size=44)
    margin, line_h, big_h = 24, 30, 58
    pieces: list[tuple[str, object]] = []
    for item in layout(dish):
        if item is None:
            pieces.append(("blank", None))
        elif item == "QR":
            pieces.append(("image", qr_image(dish["receipt"]["qr"], width_dots)))
        else:
            cols = columns // 2 if item.big else columns
            for line in textwrap.wrap(plain(item.text), cols) or [""]:
                pieces.append(("big" if item.big else "bold" if item.bold else "text", line))
    height = margin * 2 + sum(
        p.height if kind == "image" else big_h if kind == "big" else line_h
        for kind, p in pieces
    )
    canvas = Image.new("L", (width_dots, height), 255)
    draw = ImageDraw.Draw(canvas)
    y = margin
    for kind, piece in pieces:
        if kind == "image":
            canvas.paste(piece.convert("L"), (0, y))
            y += piece.height
        elif kind == "blank":
            y += line_h
        else:
            font = big if kind == "big" else normal
            stroke = 0 if kind == "text" else 1
            w = draw.textlength(piece, font=font)
            draw.text(((width_dots - w) / 2, y), piece, font=font, fill=0, stroke_width=stroke, stroke_fill=0)
            y += big_h if kind == "big" else line_h
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()
