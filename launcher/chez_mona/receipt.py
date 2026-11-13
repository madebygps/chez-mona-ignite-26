"""Receipt and fridge ticket layouts as ESC/POS bytes.

The fridge ticket is a kitchen chit with the Mona chef wordmark. The receipt
is a keepsake guest check, with the same wordmark and gingham edges.
"""

from __future__ import annotations

import io
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
EVENT = "Microsoft Ignite 2026"
QR_CAPTION = "Scan to keep the learning going at home"
THANKS = "Merci, chef!"
SIGNATURE = "Chef Mona"
SIGNATURE_FONT = "segoescb.ttf"  # Segoe Script Bold
TICKET_CAPTION = "Take this to any open station and scan it"
TICKET_FOOTER = "4 dishes on the menu. Collect them all."
FONT_A_WIDTH = 12  # dots per character, Font A at normal size
WIDTH_DOTS = 576  # RP326 printable width: 72 mm of 80 mm paper at 203 dpi
QR_TARGET_FRACTION = 0.45
TICKET_QR_FRACTION = 0.5
FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
WORDMARK_FONT = "georgiaz.ttf"  # Georgia Bold Italic
MONA_IMAGE = Path(__file__).with_name("mona-chef.png")  # static/mona-chef.svg, rendered at 512 px

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
    margin: int = 0  # blank columns on each side when wrapping


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

def ticket_layout(dish: dict, at: datetime) -> list[Item]:
    """Fridge ticket. Its QR holds only the dish ID, which the stations scan."""
    return [
        Picture("gingham", gingham),
        Picture("wordmark", wordmark),
        Row(f"{at:%a %b} {at.day}", clock(at)),
        Rule("="),
        Line(f"1x {dish['dish'].upper()}", bold=True),
        Rule(),
        Line("ORDER UP!", bold=True, invert=True),
        Qr(dish["id"], TICKET_QR_FRACTION),
        Line(TICKET_CAPTION, bold=True),
        Rule("="),
        Line(TICKET_FOOTER),
        Line(EVENT),
    ]


# ---------- Keepsake receipt ----------

@dataclass
class Check:
    """One printed receipt. hints holds wrong answers per question, or None if unknown.
    course is the dish position and the dish count, like (2, 4), or None if unknown."""
    at: datetime
    hints: list[int] | None = None
    number: int | None = None
    course: tuple[int, int] | None = None


def rank(hints: int) -> str:
    """Kitchen rank from the total wrong answers."""
    if hints == 0:
        return "HEAD CHEF"
    return "SOUS CHEF" if hints <= 2 else "LINE COOK"


def layout(dish: dict, check: Check) -> list[Item]:
    """Take-home receipt printed at a cooking station. None is a blank line."""
    answered = len(dish["quiz"])
    card = dish["receipt"]
    course = f"DISH {check.course[0]} OF {check.course[1]}" if check.course else ""
    items: list[Item] = [
        Picture("gingham", gingham),
        Picture("wordmark", wordmark),
        Row(f"Receipt #{check.number:03d}",
            f"{check.at:%a %b} {check.at.day}, {check.at:%Y}  {clock(check.at)}")
        if check.number is not None else
        Line(f"{check.at:%a %b} {check.at.day}, {check.at:%Y}  {clock(check.at)}"),
        Rule("="),
        Row(f"1  {dish['dish'].upper()}", course, bold=True),
        None,
        Line(card["product"].upper(), bold=True, invert=True),
        *[Line(point, align="left", indent=3, bullet="- ") for point in card["bullets"]],
        None,
        Rule(),
        Row("QUIZ", f"{answered}/{answered} aced"),
    ]
    if check.hints is not None:
        items.append(Row("RANK", rank(sum(check.hints))))
    items += [
        Row("TIP", card["tip"]),
        Rule(),
        Row("TOTAL", "PRICELESS", bold=True, size=2),
        Rule("="),
        Qr(card["qr"]),
        Line(QR_CAPTION, bold=True),
        None,
        Line(THANKS.upper(), height=2, bold=True),
        Line(EVENT),
        Picture("signature", signature),
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


def gingham(width_dots: int, square: int = 16, rows: int = 2) -> Image.Image:
    """Bistro tablecloth band: black where stripes cross, a checker where one does."""
    image = Image.new("1", (width_dots, square * rows), 1)
    pixels = image.load()
    for y in range(image.height):
        for x in range(width_dots):
            across, down = (x // square) % 2, (y // square) % 2
            if (across and down) or ((across or down) and (x + y) % 2 == 0):
                pixels[x, y] = 0
    return image


def threshold(image: Image.Image, cutoff: int = 140) -> Image.Image:
    """Grayscale to pure black and white, with no dithering."""
    return image.convert("L").point(lambda v: 0 if v < cutoff else 255).convert("1", dither=Image.Dither.NONE)


def mona(size: int) -> Image.Image:
    """The Mona chef mark from the launcher UI, as a black disc."""
    return threshold(Image.open(MONA_IMAGE).convert("L").resize((size, size), Image.LANCZOS))


def wordmark(width_dots: int) -> Image.Image:
    """Mona chef mark beside "Chez Mona" in a serif italic."""
    disc = mona(int(width_dots * 0.2))
    face = font(WORDMARK_FONT, int(width_dots * 0.11))
    gap = width_dots // 28
    left, top, right, bottom = ImageDraw.Draw(disc).textbbox((0, 0), HEADER, font=face)
    x = (width_dots - disc.width - gap - (right - left)) // 2
    image = Image.new("1", (width_dots, disc.height + 8), 1)
    image.paste(disc, (x, 4))
    y = (image.height - (bottom - top)) // 2 - top
    ImageDraw.Draw(image).text((x + disc.width + gap - left, y), HEADER, font=face, fill=0)
    return image


def signature(width_dots: int) -> Image.Image:
    """"Chef Mona" in a script font over a slanted pen stroke."""
    face = font(SIGNATURE_FONT, int(width_dots * 0.06))
    left, top, right, bottom = ImageDraw.Draw(Image.new("1", (1, 1))).textbbox((0, 0), SIGNATURE, font=face)
    image = Image.new("1", (width_dots, bottom - top + 18), 1)
    draw = ImageDraw.Draw(image)
    x = (width_dots - (right - left)) // 2
    draw.text((x - left, 2 - top), SIGNATURE, font=face, fill=0)
    y = bottom - top + 8
    draw.line([(x - 20, y + 6), (x + right - left + 30, y)], fill=0, width=3)
    return image


def qr_code(data: str, target_dots: int) -> tuple[Image.Image, int]:
    """Monochrome QR code at most target_dots wide, and its module size in dots."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.modules_count
    box = max(1, target_dots // modules)
    code = qr.make_image(fill_color="black", back_color="white").get_image()
    return code.convert("1").resize((modules * box, modules * box), Image.NEAREST), box


def qr_image(data: str, width_dots: int, fraction: float = QR_TARGET_FRACTION) -> Image.Image:
    """Monochrome QR code centered on a strip exactly width_dots wide."""
    code, box = qr_code(data, int(width_dots * fraction))
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


# ---------- Preview ----------

LINE_DOTS = 30  # Font A is 12 x 24 dots; the printer adds line spacing
PREVIEW_FONTS = {False: "consola.ttf", True: "consolab.ttf"}
PREVIEW_MARGIN = 24


def _glyphs(text: str, bold: bool, invert: bool = False) -> Image.Image:
    """Text in fixed 12-dot cells, so columns line up as they do on paper."""
    face = font(PREVIEW_FONTS[bold], 22)
    image = Image.new("1", (max(1, len(text)) * FONT_A_WIDTH, LINE_DOTS), int(not invert))
    draw = ImageDraw.Draw(image)
    for i, char in enumerate(text):
        draw.text((i * FONT_A_WIDTH + FONT_A_WIDTH / 2, LINE_DOTS / 2), char, font=face, fill=int(invert), anchor="mm")
    return image


def _line_image(text: str, width_dots: int, align: str = "center", width: int = 1, height: int = 1,
                bold: bool = False, invert: bool = False) -> Image.Image:
    glyphs = _glyphs(text, bold, invert)
    if width > 1 or height > 1:
        glyphs = glyphs.resize((glyphs.width * width, glyphs.height * height), Image.NEAREST)
    line = Image.new("1", (width_dots, glyphs.height), 1)
    x = {"left": 0, "center": (width_dots - glyphs.width) // 2, "right": width_dots - glyphs.width}[align]
    line.paste(glyphs, (max(0, x), 0))
    return line


def render_image(items: list[Item], width_dots: int) -> Image.Image:
    """What render_escpos prints, drawn with Consolas in place of the printer font."""
    columns = width_dots // FONT_A_WIDTH
    blank = Image.new("1", (width_dots, LINE_DOTS), 1)
    parts: list[Image.Image] = []
    for item in items:
        if item is None:
            parts.append(blank)
        elif isinstance(item, Qr):
            parts += [qr_image(item.data, width_dots, item.fraction), blank]
        elif isinstance(item, Picture):
            parts.append(item.draw(width_dots))
        elif isinstance(item, Rule):
            text = (item.char + " ") * columns if item.spaced else item.char * columns
            parts.append(_line_image(text[:columns].rstrip(), width_dots))
        elif isinstance(item, Row):
            parts += [_line_image(line, width_dots, "left", item.size, item.size, item.bold)
                      for line in _row_lines(item, columns // item.size)]
        else:
            align = "left" if item.invert else item.align
            parts += [_line_image(line, width_dots, align, item.width, item.height, item.bold, item.invert)
                      for line in _text_lines(item, columns // item.width)]
    image = Image.new("1", (width_dots + 2 * PREVIEW_MARGIN, sum(p.height for p in parts) + 2 * PREVIEW_MARGIN), 1)
    y = PREVIEW_MARGIN
    for part in parts:
        image.paste(part, (PREVIEW_MARGIN, y))
        y += part.height
    return image


def png(dish: dict, check: Check, width_dots: int = WIDTH_DOTS) -> bytes:
    """The receipt as a PNG, for the station screen."""
    out = io.BytesIO()
    render_image(layout(dish, check), width_dots).save(out, "PNG", optimize=True)
    return out.getvalue()


# ---------- ESC/POS ----------

def escpos(dish: dict, check: Check, width_dots: int = WIDTH_DOTS) -> bytes:
    return render_escpos(layout(dish, check), width_dots)


def ticket_escpos(dish: dict, at: datetime, width_dots: int = WIDTH_DOTS) -> bytes:
    return render_escpos(ticket_layout(dish, at), width_dots)


ALIGN = {"left": 0, "center": 1, "right": 2}


def _style(align: str = "center", width: int = 1, height: int = 1, bold: bool = False, invert: bool = False) -> bytes:
    return (ESC + b"a" + bytes([ALIGN[align]])
            + GS + b"!" + bytes([(width - 1) << 4 | (height - 1)])
            + ESC + b"E" + bytes([int(bold)])
            + GS + b"B" + bytes([int(invert)]))


def _text_lines(item: Line, columns: int) -> list[str]:
    text = plain(item.text)
    if item.invert:
        pad = max(0, columns - len(text))
        return [" " * (pad // 2) + text[:columns] + " " * (pad - pad // 2)]
    start = " " * item.indent + item.bullet
    rest = " " * (item.indent + len(item.bullet))
    return textwrap.wrap(text, columns - 2 * item.margin, initial_indent=start, subsequent_indent=rest) or [""]


def _row_lines(row: Row, columns: int) -> list[str]:
    left, right = plain(row.left), plain(row.right)
    lines = textwrap.wrap(left, columns)
    last = lines.pop() if lines else ""
    if not right or len(last) + len(right) + 1 <= columns:
        return lines + [last + right.rjust(columns - len(last))]
    return lines + ([last] if last else []) + [part.rjust(columns) for part in textwrap.wrap(right, columns)]


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
