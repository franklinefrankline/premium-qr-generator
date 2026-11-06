import base64
import unittest
from io import BytesIO

from PIL import Image

from app import app, make_qr_code, normalize_url


class QRGeneratorTests(unittest.TestCase):
    CASES = (
        ("192.168.4.1", "http://192.168.4.1"),
        ("192.168.1.100", "http://192.168.1.100"),
        ("192.168.4.1:8080", "http://192.168.4.1:8080"),
        ("http://192.168.4.1", "http://192.168.4.1"),
        ("https://example.com", "https://example.com"),
        ("http://192.168.1.100:5000", "http://192.168.1.100:5000"),
        ("https://example.com:8443", "https://example.com:8443"),
    )

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_generator_explains_network_requirements(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="protocol-select"', response.data)
        self.assertIn(b"Access Point mode", response.data)
        self.assertIn(b"Station mode", response.data)

    def test_requested_urls_generate_exact_qr_and_download(self):
        for submitted_url, expected_url in self.CASES:
            with self.subTest(submitted_url=submitted_url):
                response = self.client.post(
                    "/generate",
                    json={"url": submitted_url, "protocol": "auto"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["url"], expected_url)

                qr = make_qr_code(expected_url)
                encoded_data = b"".join(segment.data for segment in qr.data_list)
                self.assertEqual(encoded_data.decode("utf-8"), expected_url)

                preview_bytes = base64.b64decode(response.json["image"].split(",", 1)[1])
                with Image.open(BytesIO(preview_bytes)) as preview:
                    self.assertEqual(preview.format, "PNG")
                    self.assertEqual(preview.mode, "RGB")
                    colors = {color for _, color in preview.getcolors(maxcolors=2)}
                    self.assertEqual(colors, {(6, 78, 59), (255, 255, 255)})

                download = self.client.get(response.json["download_url"])
                self.assertEqual(download.status_code, 200)
                self.assertEqual(download.mimetype, "image/png")
                self.assertTrue(download.data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(download.data, preview_bytes)

    def test_protocol_selection_only_applies_when_scheme_is_missing(self):
        self.assertEqual(normalize_url("192.168.4.1", "https"), "https://192.168.4.1")
        self.assertEqual(normalize_url("example.com", "http"), "http://example.com")
        self.assertEqual(normalize_url("http://192.168.4.1", "https"), "http://192.168.4.1")

    def test_rejects_malformed_ip_and_port(self):
        for invalid_url in ("192.168.1.999", "192.168.4.1:abc", "192.168.4.1:65536"):
            with self.subTest(invalid_url=invalid_url):
                response = self.client.post("/generate", json={"url": invalid_url})
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
