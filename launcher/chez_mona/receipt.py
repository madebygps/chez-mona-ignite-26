"""Receipt and fridge ticket layouts as ESC/POS bytes and as PNG previews."""

from __future__ import annotations

import io
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont

HEADER = "Chez Mona"
FOOTER = "Microsoft Ignite 2026"
QR_CAPTION = "Scan to learn more"
TICKET_TITLE = "Order ticket"
TICKET_CAPTION = "Scan at any open cooking station"
FONT_A_WIDTH = 12  # dots per character, Font A at normal size
QR_TARGET_FRACTION = 0.55
TICKET_QR_FRACTION = 0.6

ESC, GS = b"\x1b", b"\x1d"


@dataclass
class Line:
    text: str
    big: bool = False
    bold: bool = False


@dataclass
class Qr:
    data: str
    fraction: float = QR_TARGET_FRACTION


def plain(text: str) -> str:
    """Strip the small Markdown subset used in content and keep printable ASCII."""
    text = re.sub(r"\*\*|`", "", text)
    return text.encode("ascii", "replace").decode("ascii")


Item = Line | Qr | None


def layout(dish: dict) -> list[Item]:
    """Take-home receipt printed at a cooking station. None is a blank line."""
    return [
        Line(HEADER, big=True, bold=True),
        None,
        Line(dish["dish"], bold=True),
        Line(dish["lab"]),
        None,
        Line(dish["receipt"]["learned"]),
        Qr(dish["receipt"]["qr"]),
        Line(QR_CAPTION),
        None,
        Line(FOOTER),
    ]


@dataclass
class Order:
    number: int
    at: datetime

    def label(self) -> str:
        return f"{self.number:03d}"


def ticket_layout(dish: dict, order: Order) -> list[Item]:
    """Fridge ticket. Its QR holds only the dish ID, which the stations scan."""
    when = f"{order.at:%a %b} {order.at.day}, {order.at:%I:%M %p}".replace(" 0", " ")
    return [
        Line(HEADER, big=True, bold=True),
        Line(TICKET_TITLE),
        None,
        Line(f"Order #{order.label()}"),
        Line(when),
        None,
        Line(dish["dish"], big=True, bold=True),
        Line(dish["lab"]),
        Qr(dish["id"], TICKET_QR_FRACTION),
        Line(TICKET_CAPTION, bold=True),
        None,
        Line(FOOTER),
    ]


def qr_image(data: str, width_dots: int, fraction: float = QR_TARGET_FRACTION) -> Image.Image:
    """Monochrome QR code centered on a strip exactly width_dots wide."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.modules_count
    box = max(1, int(width_dots * fraction) // modules)
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
    return render_escpos(layout(dish), width_dots)


def ticket_escpos(dish: dict, order: Order, width_dots: int) -> bytes:
    return render_escpos(ticket_layout(dish, order), width_dots)


def render_escpos(items: list[Item], width_dots: int) -> bytes:
    columns = width_dots // FONT_A_WIDTH
    out = bytearray(ESC + b"@" + ESC + b"a\x01")
    for item in items:
        if item is None:
            out += b"\n"
        elif isinstance(item, Qr):
            out += raster(qr_image(item.data, width_dots, item.fraction))
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
    return render_png(layout(dish), width_dots)


def ticket_png(dish: dict, order: Order, width_dots: int) -> bytes:
    return render_png(ticket_layout(dish, order), width_dots)


def render_png(items: list[Item], width_dots: int) -> bytes:
    """Approximate picture of the printed paper, for dry runs and staff checks."""
    columns = width_dots // FONT_A_WIDTH
    normal = ImageFont.load_default(size=22)
    big = ImageFont.load_default(size=44)
    margin, line_h, big_h = 24, 30, 58
    pieces: list[tuple[str, object]] = []
    for item in items:
        if item is None:
            pieces.append(("blank", None))
        elif isinstance(item, Qr):
            pieces.append(("image", qr_image(item.data, width_dots, item.fraction)))
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
