import unittest
from datetime import datetime

from PIL import Image

from chez_mona import labs, receipt

DISHES = labs.by_id(labs.load())
AT = datetime(2026, 11, 18, 10, 42)


def printed_lines(items, width):
    """Every text line the printer gets, with the character columns it has."""
    columns = width // receipt.FONT_A_WIDTH
    for item in items:
        if isinstance(item, receipt.Line):
            for line in receipt._text_lines(item, columns // item.width):
                yield line, columns // item.width
        elif isinstance(item, receipt.Row):
            for line in receipt._row_lines(item, columns // item.size):
                yield line, columns // item.size


class ReceiptTest(unittest.TestCase):
    def test_escpos_frame(self):
        for width in (384, 576):
            data = receipt.escpos(DISHES["dip"], receipt.Check(AT, [0, 1]), width)
            self.assertTrue(data.startswith(b"\x1b@\x1ba\x01"))
            self.assertTrue(data.endswith(b"\x1bd\x04\x1dV\x42\x00"))
            for text in (b"Thank you for cooking", b"DIP", b"GUEST CHECK", b"Cooking station", b"PRICELESS", b"Scan to continue learning"):
                self.assertIn(text, data)
            self.assertNotIn(b"No.", data)

    def test_receipt_lists_what_you_learned_not_the_questions(self):
        dish = DISHES["omelette"]
        texts = [line for line, _ in printed_lines(receipt.layout(dish, receipt.Check(AT)), 576)]
        self.assertIn(" - A canvas is an interactive panel in the", texts)
        self.assertIn("   Copilot app.", texts)
        self.assertFalse(any(dish["quiz"][0]["question"] in t for t in texts))

    def test_hints_decide_the_stamp_and_hint_line(self):
        def rows(check):
            return [i.left for i in receipt.layout(DISHES["soup"], check) if isinstance(i, receipt.Row)]

        self.assertTrue(receipt.Check(AT, hints=[0, 0]).perfect())
        self.assertFalse(receipt.Check(AT, hints=[0, 2]).perfect())
        self.assertFalse(receipt.Check(AT).perfect())
        self.assertIn("HINTS USED", rows(receipt.Check(AT, hints=[0, 2])))
        self.assertNotIn("HINTS USED", rows(receipt.Check(AT)))

    def test_text_fits_the_paper(self):
        order = receipt.Order(7, AT, "W")
        for width in (384, 576):
            for dish in DISHES.values():
                for items in (receipt.layout(dish, receipt.Check(AT, [3, 3])),
                              receipt.ticket_layout(dish, order)):
                    for line, columns in printed_lines(items, width):
                        self.assertLessEqual(len(line), columns, line)

    def test_pictures_span_the_paper(self):
        for width in (384, 576):
            for item in receipt.layout(DISHES["dip"], receipt.Check(AT, hints=[0, 0])):
                if isinstance(item, receipt.Picture):
                    image = item.draw(width)
                    self.assertEqual(image.width, width, item.name)
                    receipt.raster(image)

    def test_raster_header_matches_qr(self):
        for width in (384, 576):
            image = receipt.qr_image(DISHES["soup"]["receipt"]["qr"], width)
            self.assertEqual(image.width, width)
            data = receipt.raster(image)
            self.assertEqual(data[:4], b"\x1dv0\x00")
            x_bytes = data[4] | data[5] << 8
            height = data[6] | data[7] << 8
            self.assertEqual((x_bytes, height), (width // 8, image.height))
            self.assertEqual(len(data), 8 + x_bytes * height)

    def test_raster_black_is_one(self):
        image = Image.new("1", (8, 1), 0)
        self.assertEqual(receipt.raster(image)[8:], b"\xff")

    def test_plain_strips_markup_and_non_ascii(self):
        self.assertEqual(receipt.plain("Use `send_and_wait` **now** \u2713"), "Use send_and_wait now ?")

    def test_ticket_carries_order_and_dish_id_qr(self):
        order = receipt.Order(7, datetime(2026, 11, 18, 9, 5))
        items = receipt.ticket_layout(DISHES["fried-chicken"], order)
        self.assertIn("#007", [i.text for i in items if isinstance(i, receipt.Line)])
        self.assertIn(("Wed Nov 18", "9:05 AM"), [(i.left, i.right) for i in items if isinstance(i, receipt.Row)])
        self.assertEqual([i.data for i in items if isinstance(i, receipt.Qr)], ["fried-chicken"])
        data = receipt.ticket_escpos(DISHES["fried-chicken"], order, 576)
        self.assertTrue(data.endswith(b"\x1bd\x04\x1dV\x42\x00"))
        self.assertIn(b"1x FRIED CHICKEN", data)

    def test_fridge_letter_keeps_order_numbers_apart(self):
        self.assertEqual(receipt.Order(42, AT, "A").label(), "A-042")
        self.assertEqual(receipt.Order(42, AT).label(), "042")
        items = receipt.ticket_layout(DISHES["dip"], receipt.Order(7, AT, "B"))
        self.assertIn("#B-007", [i.text for i in items if isinstance(i, receipt.Line)])


if __name__ == "__main__":
    unittest.main()
