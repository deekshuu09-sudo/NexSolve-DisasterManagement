from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter


def analyze_image(contents: bytes) -> dict:
    """Screen image quality without claiming unvalidated hazard detection."""
    original = Image.open(BytesIO(contents)).convert("RGB")
    width, height = original.size
    image = original.copy()
    image.thumbnail((640, 640))
    array = np.asarray(image, dtype=np.float32) / 255.0
    gray = np.asarray(image.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0

    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]
    earth_ratio = float(((red > blue * 1.15) & (green > blue * 1.05) & (red > 0.25)).mean())
    dark_ratio = float((array.mean(axis=2) < 0.28).mean())
    edge_density = float((gray > 0.18).mean())
    bright_ratio = float((array.mean(axis=2) > 0.72).mean())

    quality_score = min(100.0, (min(width, height) / 720) * 55 + (1 - dark_ratio) * 20 + (1 - bright_ratio) * 25)
    image_quality = "Good" if width >= 320 and height >= 240 else "Poor"
    indicators = []
    if width < 320 or height < 240:
        indicators.append("low resolution")
    if dark_ratio > 0.65:
        indicators.append("underexposed")
    if bright_ratio > 0.85:
        indicators.append("overexposed")
    if edge_density > 0.2:
        indicators.append("high edge density")
    if not indicators:
        indicators.append("image dimensions and exposure acceptable")
    severity = "Low" if image_quality == "Good" else "Moderate"
    return {
        "imageAccepted": image_quality == "Good",
        "imageQuality": image_quality,
        "verificationMode": "AI-assisted image screening",
        "verificationConfidence": round(quality_score, 1),
        "classification": "Unclassified",
        "confidence": round(quality_score, 1),
        "severity": severity,
        "objects": indicators,
        "detectedIndicators": indicators,
        "recommendedAction": "Image passed quality screening; landslide classification requires a validated landslide vision model." if image_quality == "Good" else "Request a clearer image before field verification.",
        "modelSource": "image-quality-screening-only",
        "is_trained": False,
    }
