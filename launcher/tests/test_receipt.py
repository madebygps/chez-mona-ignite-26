import io
import unittest
from datetime import datetime

from PIL import Image

from chez_mona import labs, receipt

DISHES = labs.by_id(labs.load())


class ReceiptTest(unittest.TestCase):
    def test_escpos_frame(self):
        for width in (384, 576):
            data = receipt.escpos(DISHES["dip"], width)
            self.assertTrue(data.startswith(b"\x1b@\x1ba\x01"))
            self.assertTrue(data.endswith(b"\x1bd\x04\x1dV\x42\x00"))
            self.assertIn(b"Chez Mona", data)
            self.assertIn(b"Dip", data)

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

    def test_preview_is_png(self):
        png = receipt.preview_png(DISHES["fried-chicken"], 576)
        self.assertEqual(Image.open(io.BytesIO(png)).width, 576)

    def test_ticket_carries_order_and_dish_id_qr(self):
        order = receipt.Order(7, datetime(2026, 11, 18, 9, 5))
        items = receipt.ticket_layout(DISHES["fried-chicken"], order)
        texts = [i.text for i in items if isinstance(i, receipt.Line)]
        self.assertIn("Order #007", texts)
        self.assertIn("Wed Nov 18, 9:05 AM", texts)
        self.assertEqual([i.data for i in items if isinstance(i, receipt.Qr)], ["fried-chicken"])
        data = receipt.ticket_escpos(DISHES["fried-chicken"], order, 576)
        self.assertTrue(data.endswith(b"\x1bd\x04\x1dV\x42\x00"))
        self.assertIn(b"Fried Chicken", data)
        png = receipt.ticket_png(DISHES["fried-chicken"], order, 576)
        self.assertEqual(Image.open(io.BytesIO(png)).width, 576)


if __name__ == "__main__":
    unittest.main()
