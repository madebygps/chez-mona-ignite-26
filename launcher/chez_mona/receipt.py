"""Receipt and fridge ticket layouts as ESC/POS bytes.

The fridge ticket is a plain kitchen chit. The receipt is a keepsake guest
check, with a raster wordmark, gingham edges and a rubber stamp.
"""

from __future__ import annotations

import os
import re
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

HEADER = "Chez Mona"
TAGLINE = "Cuisine agentique"
EVENT = "Microsoft Ignite 2026"
SERVED_BY = "GitHub Copilot"
STATION = "Cooking station"
QR_CAPTION = "Scan to continue learning"
THANKS = "Merci! Have a nice day"
THANKS_LINE = "Thank you for cooking at Chez Mona"
TICKET_BAR = "Chez Mona  *  Kitchen ticket"
TICKET_CAPTION = ">> Scan at any open station <<"
TICKET_DURATION = "about 5 min"
FONT_A_WIDTH = 12  # dots per character, Font A at normal size
WIDTH_DOTS = 576  # RP326 printable width: 72 mm of 80 mm paper at 203 dpi
QR_TARGET_FRACTION = 0.45
TICKET_QR_FRACTION = 0.6
FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
WORDMARK_FONT = "georgiaz.ttf"  # Georgia Bold Italic
STAMP_FONT = "consolab.ttf"  # Consolas Bold

ESC, GS = b"\x1b", b"\x1d"


@dataclass
class Line:
    text: str
    align: str = "center"
    width: int = 1  # character width multiplier, 1 to 8
    height: int = 1
    bold: bool = False
    invert: bool = False  # white on black, padded to a full width bar
    indent: int = 0
    bullet: str = ""
    letterspace: bool = False  # "C U I S I N E", when it fits


@dataclass
class Row:
    """Left and right text on one line, like a menu price."""
    left: str
    right: str
    bold: bool = False
    size: int = 1


@dataclass
class Rule:
    char: str = "-"
    spaced: bool = False


@dataclass
class Qr:
    data: str
    fraction: float = QR_TARGET_FRACTION


@dataclass
class Picture:
    """Raster art drawn for the paper width: a callable from width in dots to an image."""
    name: str
    draw: Callable[[int], Image.Image]


Item = Line | Row | Rule | Qr | Picture | None


def plain(text: str) -> str:
    """Strip the small Markdown subset used in content and keep printable ASCII."""
    text = re.sub(r"\*\*|`", "", text)
    return text.encode("ascii", "replace").decode("ascii")


# ---------- Fridge ticket ----------

@dataclass
class Order:
    """A fridge ticket. The fridge's letter keeps the two fridges' numbers apart: A-042."""
    number: int
    at: datetime
    prefix: str = ""

    def label(self) -> str:
        return f"{self.prefix}-{self.number:03d}" if self.prefix else f"{self.number:03d}"


def ticket_layout(dish: dict, order: Order) -> list[Item]:
    """Fridge ticket. Its QR holds only the dish ID, which the stations scan."""
    return [
        Line(TICKET_BAR.upper(), bold=True, invert=True),
        None,
        Line(f"#{order.label()}", width=3, height=3, bold=True),
        Row(f"{order.at:%a %b} {order.at.day}", clock(order.at)),
        Rule(spaced=True),
        None,
        Line(f"1x {dish['dish'].upper()}", width=2, height=2, bold=True),
        Line(f"{dish['lab']} lab  |  {TICKET_DURATION}"),
        None,
        Qr(dish["id"], TICKET_QR_FRACTION),
        Line(TICKET_CAPTION.upper(), bold=True, invert=True),
        None,
        Rule(spaced=True),
        Line(EVENT),
    ]


# ---------- Keepsake receipt ----------

@dataclass
class Check:
    """One printed receipt. hints holds wrong answers per question, or None if unknown."""
    at: datetime
    hints: list[int] | None = None

    def perfect(self) -> bool:
        return self.hints is not None and not any(self.hints)


def layout(dish: dict, check: Check) -> list[Item]:
    """Take-home receipt printed at a cooking station. None is a blank line."""
    answered = len(dish["quiz"])
    stamp_words = ("PERFECT", "SCORE") if check.perfect() else ("CHEF", "APPROVED")
    items: list[Item] = [
        Picture("gingham", gingham),
        None,
        Picture("wordmark", wordmark),
        Line(TAGLINE.upper(), bold=True, letterspace=True),
        Line(EVENT),
        None,
        Rule("="),
        Line("GUEST CHECK", align="left", bold=True),
        Row(STATION, f"{check.at:%a %b} {check.at.day}, {check.at:%Y}  {clock(check.at)}"),
        Row("Served by", SERVED_BY),
        Rule("="),
        None,
        Row(f"1  {dish['dish'].upper()}", "1 lab", bold=True),
        Line(dish["lab"], align="left", indent=3),
        None,
        Line("TODAY YOU LEARNED", bold=True, invert=True),
        None,
        *[Line(point, align="left", indent=1, bullet="- ") for point in dish["receipt"]["learned"]],
        None,
        Rule(),
        Row("SUBTOTAL", f"{answered}/{answered} correct"),
    ]
    if check.hints is not None:
        items.append(Row("HINTS USED", str(sum(check.hints))))
    items += [
        Row("TIP", "Ship it!"),
        Rule(),
        Row("TOTAL", "PRICELESS", bold=True, size=2),
        Rule("="),
        None,
        Picture("stamp", lambda width: stamp(width, *stamp_words)),
        None,
        Rule(spaced=True),
        Qr(dish["receipt"]["qr"]),
        Line(QR_CAPTION, bold=True),
        Rule(spaced=True),
        None,
        Line(THANKS.upper(), height=2, bold=True),
        Line(THANKS_LINE),
        None,
        Picture("gingham", gingham),
    ]
    return items


def clock(at: datetime) -> str:
    return f"{at:%I:%M %p}".lstrip("0")


# ---------- Raster art ----------

def font(name: str, size: int) -> ImageFont.ImageFont:
    """A Windows font, or Pillow's built in font where it is missing."""
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


def gingham(width_dots: int, square: int = 16, rows: int = 3) -> Image.Image:
    """Bistro tablecloth band: black where stripes cross, a checker where one does."""
    image = Image.new("1", (width_dots, square * rows), 1)
    pixels = image.load()
    for y in range(image.height):
        for x in range(width_dots):
            across, down = (x // square) % 2, (y // square) % 2
            if (across and down) or ((across or down) and (x + y) % 2 == 0):
                pixels[x, y] = 0
    return image


def chef_hat(size: int) -> Image.Image:
    """Toque outline: three puffs and a band, drawn solid then hollowed out."""
    s = size
    line = max(4, s // 20)
    puffs = ((0.27, 0.45, 0.19), (0.50, 0.32, 0.24), (0.73, 0.45, 0.19))
    image = Image.new("1", (s, s), 1)
    draw = ImageDraw.Draw(image)

    def shapes(grow: float, fill: int) -> None:
        for cx, cy, r in puffs:
            r = r * s + grow
            draw.ellipse([cx * s - r, cy * s - r, cx * s + r, cy * s + r], fill=fill)
        draw.rectangle([0.24 * s - grow, 0.50 * s - grow, 0.76 * s + grow, 0.94 * s + grow], fill=fill)

    shapes(0, 0)
    shapes(-line, 1)
    draw.line([0.24 * s, 0.70 * s, 0.76 * s, 0.70 * s], fill=0, width=line)
    for x in (0.40, 0.60):
        draw.line([x * s, 0.74 * s, x * s, 0.90 * s], fill=0, width=max(3, line - 1))
    return image


def wordmark(width_dots: int) -> Image.Image:
    """Chef hat over "Chez Mona" in a serif italic."""
    hat = chef_hat(int(width_dots * 0.19))
    face = font(WORDMARK_FONT, int(width_dots * 0.16))
    left, top, right, bottom = ImageDraw.Draw(hat).textbbox((0, 0), HEADER, font=face)
    image = Image.new("1", (width_dots, hat.height + bottom - top + 24), 1)
    image.paste(hat, ((width_dots - hat.width) // 2, 0))
    ImageDraw.Draw(image).text(((width_dots - (right - left)) // 2 - left, hat.height + 8 - top), HEADER, font=face, fill=0)
    return image


def stamp(width_dots: int, top: str, bottom: str, angle: float = -12) -> Image.Image:
    """A tilted rubber stamp, centered on a strip width_dots wide."""
    size = int(width_dots * 0.4)
    image = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(image)
    middle = size / 2
    draw.ellipse([4, 4, size - 4, size - 4], outline=0, width=max(4, size // 32))
    draw.ellipse([size * 0.08, size * 0.08, size * 0.92, size * 0.92], outline=0, width=max(2, size // 76))
    big, small = font(STAMP_FONT, size // 6), font(STAMP_FONT, size // 8)
    draw.text((middle, middle - size * 0.10), top, font=big, fill=0, anchor="mm")
    draw.text((middle, middle + size * 0.10), bottom, font=small, fill=0, anchor="mm")
    for dx in (-0.26, 0, 0.26):
        for dy in (-0.30, 0.29):
            draw.text((middle + dx * size, middle + dy * size), "*", font=small, fill=0, anchor="mm")
    image = image.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
    strip = Image.new("1", (width_dots, size), 1)
    strip.paste(image.point(lambda v: 0 if v < 140 else 255).convert("1"), ((width_dots - size) // 2, 0))
    return strip


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


# ---------- ESC/POS ----------

def escpos(dish: dict, check: Check, width_dots: int = WIDTH_DOTS) -> bytes:
    return render_escpos(layout(dish, check), width_dots)


def ticket_escpos(dish: dict, order: Order, width_dots: int = WIDTH_DOTS) -> bytes:
    return render_escpos(ticket_layout(dish, order), width_dots)


ALIGN = {"left": 0, "center": 1, "right": 2}


def _style(align: str = "center", width: int = 1, height: int = 1, bold: bool = False, invert: bool = False) -> bytes:
    return (ESC + b"a" + bytes([ALIGN[align]])
            + GS + b"!" + bytes([(width - 1) << 4 | (height - 1)])
            + ESC + b"E" + bytes([int(bold)])
            + GS + b"B" + bytes([int(invert)]))


def _text_lines(item: Line, columns: int) -> list[str]:
    text = plain(item.text)
    if item.letterspace and len(text) * 2 - 1 <= columns:
        text = " ".join(text)
    if item.invert:
        pad = max(0, columns - len(text))
        return [" " * (pad // 2) + text[:columns] + " " * (pad - pad // 2)]
    start = " " * item.indent + item.bullet
    rest = " " * (item.indent + len(item.bullet))
    return textwrap.wrap(text, columns, initial_indent=start, subsequent_indent=rest) or [""]


def _row_lines(row: Row, columns: int) -> list[str]:
    left, right = plain(row.left), plain(row.right)
    if len(left) + len(right) + 1 > columns:
        return [left, right.rjust(columns)] if left else [right.rjust(columns)]
    return [left + right.rjust(columns - len(left))]


def render_escpos(items: list[Item], width_dots: int) -> bytes:
    columns = width_dots // FONT_A_WIDTH
    out = bytearray(ESC + b"@")
    for item in items:
        if item is None:
            out += _style() + b"\n"
        elif isinstance(item, Qr):
            out += _style() + raster(qr_image(item.data, width_dots, item.fraction)) + b"\n"
        elif isinstance(item, Picture):
            out += _style() + raster(item.draw(width_dots))
        elif isinstance(item, Rule):
            text = (item.char + " ") * columns if item.spaced else item.char * columns
            out += _style() + text[:columns].rstrip().encode("ascii") + b"\n"
        elif isinstance(item, Row):
            out += _style("left", item.size, item.size, item.bold)
            for line in _row_lines(item, columns // item.size):
                out += line.encode("ascii") + b"\n"
        else:
            align = "left" if item.invert else item.align
            out += _style(align, item.width, item.height, item.bold, item.invert)
            for line in _text_lines(item, columns // item.width):
                out += line.encode("ascii") + b"\n"
    # Reset styles, feed past the cutter, then partial cut.
    out += _style() + ESC + b"d\x04" + GS + b"V\x42\x00"
    return bytes(out)
