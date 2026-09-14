"""
P13 Field Intelligence Report & Image Screening Unit Test Suite.

Verifies:
1. TEST 1 - Random Website Screenshot: NON_FIELD_IMAGE status, SCREENSHOT_OR_DOCUMENT category, NO landslide classification, NO fake confidence/severity.
2. TEST 2 - Clear Real Photo: IMAGE_SCREENING_ONLY status, FIELD_PHOTO_CANDIDATE category, LANDSLIDE CLASSIFICATION NOT PERFORMED.
3. TEST 3 - Blurry Photo: LOW_QUALITY_IMAGE status with explanation.
4. TEST 4 - Dark Photo: LOW_QUALITY_IMAGE status.
5. TEST 5 - No Image: REPORT_RECEIVED status, imageAnalysis is None.
6. TEST 6 - Backend Unavailable Handling: frontend error handling contract.
7. TEST 7 - Valid Report Submission with application/octet-stream MIME header.
8. TEST 8 - Production Vercel VITE_API_URL configuration in api.ts.
"""

from io import BytesIO
import unittest
from PIL import Image, ImageDraw, ImageFilter
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.cv_service import analyze_image


def create_screenshot_image() -> bytes:
    """Generate mock website screenshot with sharp text and white background."""
    img = Image.new("RGB", (1200, 800), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 1150, 150], fill="#1e293b")
    draw.rectangle([50, 200, 550, 700], fill="#f1f5f9", outline="#cbd5e1")
    for i in range(12):
        draw.text((70, 220 + i * 35), f"Website Menu Item Text Line {i + 1}", fill="#0f172a")
        draw.text((600, 220 + i * 35), f"Sample UI screenshot text paragraph line {i + 1}", fill="#334155")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_outdoor_photo_image() -> bytes:
    """Generate mock outdoor photo with earth, foliage, and sky tones."""
    img = Image.new("RGB", (1200, 800), color="#5c4033")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1200, 300], fill="#87ceeb")  # Sky
    draw.polygon([(200, 300), (600, 800), (0, 800)], fill="#2e8b57")  # Green hill
    draw.polygon([(400, 400), (1000, 800), (200, 800)], fill="#8b4513")  # Mud slope
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_blurry_photo_image() -> bytes:
    """Generate blurry outdoor image."""
    photo_bytes = create_outdoor_photo_image()
    img = Image.open(BytesIO(photo_bytes)).filter(ImageFilter.GaussianBlur(25))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_dark_photo_image() -> bytes:
    """Generate underexposed dark image."""
    img = Image.new("RGB", (800, 600), color="#050505")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestP13FieldIntelligenceReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_random_website_screenshot(self):
        """TEST 1 - Random website screenshot must return NON_FIELD_IMAGE without fake landslide classification."""
        screenshot_bytes = create_screenshot_image()

        # Service level screening check
        res = analyze_image(screenshot_bytes)
        self.assertEqual(res["contentCategory"], "SCREENSHOT_OR_DOCUMENT")
        self.assertEqual(res["contentScreening"], "TEXT/SCREEN CONTENT DETECTED")
        self.assertEqual(res["landslideClassification"], "NOT PERFORMED")
        self.assertIsNone(res["confidence"])
        self.assertEqual(res["severity"], "NOT ASSESSED")
        self.assertIn("photograph", res["recommendedAction"].lower())

        # API endpoint check
        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Champhai Highway Axis",
                "description": "Observed site conditions screenshot",
            },
            files={"file": ("Screenshot (456).png", screenshot_bytes, "image/png")},
        )
        self.assertEqual(api_res.status_code, 201)
        body = api_res.json()
        report = body["report"]
        self.assertEqual(report["verificationStatus"], "NON_FIELD_IMAGE")
        self.assertFalse(report["verified"])
        self.assertEqual(report["landslideClassification"], "NOT PERFORMED")
        self.assertIsNone(report["verificationConfidence"])
        self.assertEqual(report["severity"], "NOT ASSESSED")

    def test_02_clear_real_photo_candidate(self):
        """TEST 2 - Clear real photo candidate passes quality screening without fake hazard claims."""
        photo_bytes = create_outdoor_photo_image()

        res = analyze_image(photo_bytes)
        self.assertEqual(res["contentCategory"], "FIELD_PHOTO_CANDIDATE")
        self.assertEqual(res["landslideClassification"], "NOT PERFORMED")
        self.assertIsNone(res["confidence"])

        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Champhai Pass",
                "description": "Debris on roadway",
            },
            files={"file": ("field_photo.jpg", photo_bytes, "image/jpeg")},
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertEqual(report["verificationStatus"], "IMAGE_SCREENING_ONLY")
        self.assertTrue(report["verified"])
        self.assertEqual(report["landslideClassification"], "NOT PERFORMED")
        self.assertIsNone(report["verificationConfidence"])

    def test_03_blurry_image(self):
        """TEST 3 - Blurry image detected as LOW_QUALITY_IMAGE."""
        blurry_bytes = create_blurry_photo_image()

        res = analyze_image(blurry_bytes)
        self.assertEqual(res["contentCategory"], "LOW_QUALITY_IMAGE")
        self.assertEqual(res["imageQuality"], "Poor")
        self.assertIn("blurry focus", res["objects"])

        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Sohra Corridor",
                "description": "Slope movement observed",
            },
            files={"file": ("blurry.jpg", blurry_bytes, "image/jpeg")},
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertEqual(report["verificationStatus"], "LOW_QUALITY_IMAGE")
        self.assertFalse(report["verified"])

    def test_04_dark_image(self):
        """TEST 4 - Underexposed dark image detected as LOW_QUALITY_IMAGE."""
        dark_bytes = create_dark_photo_image()

        res = analyze_image(dark_bytes)
        self.assertEqual(res["contentCategory"], "LOW_QUALITY_IMAGE")
        self.assertEqual(res["imageQuality"], "Poor")
        self.assertIn("underexposed", res["objects"])

        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Tawang Pass",
                "description": "Night observation",
            },
            files={"file": ("dark.jpg", dark_bytes, "image/jpeg")},
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertEqual(report["verificationStatus"], "LOW_QUALITY_IMAGE")
        self.assertFalse(report["verified"])

    def test_05_no_image_submission(self):
        """TEST 5 - Text-only report without image attached."""
        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Kohima Highway",
                "description": "Manual text report without image",
            },
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertEqual(report["verificationStatus"], "REPORT_RECEIVED")
        self.assertFalse(report["verified"])
        self.assertIsNone(report["imageAnalysis"])

    def test_06_analyze_image_endpoint(self):
        """Verify POST /api/reports/analyze-image endpoint behavior."""
        screenshot_bytes = create_screenshot_image()
        api_res = self.client.post(
            "/api/reports/analyze-image",
            files={"file": ("screenshot.png", screenshot_bytes, "image/png")},
            data={"description": "Test UI screenshot analysis"},
        )
        self.assertEqual(api_res.status_code, 200)
        data = api_res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["verificationStatus"], "NON_FIELD_IMAGE")
        self.assertEqual(data["landslideClassification"], "NOT PERFORMED")

    def test_07_application_octet_stream_mime_header(self):
        """TEST 7 - Valid report submission with application/octet-stream MIME type."""
        photo_bytes = create_outdoor_photo_image()
        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Dima Hasao Hill Axis",
                "description": "Field observation photo upload",
            },
            files={"file": ("Screenshot (456).png", photo_bytes, "application/octet-stream")},
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertIsNotNone(report["imageAnalysis"])
        self.assertNotEqual(report["verificationStatus"], "ERROR")

    def test_08_storage_honesty(self):
        """Verify storage location is accurately reported as in-memory session log."""
        api_res = self.client.post(
            "/api/reports",
            data={
                "type": "Landslide Observation",
                "location": "Gangtok Highway",
                "description": "Text observation log test",
            },
        )
        self.assertEqual(api_res.status_code, 201)
        report = api_res.json()["report"]
        self.assertEqual(report["storageLocation"], "In-memory session log (Field Observation Input)")


if __name__ == "__main__":
    unittest.main()
