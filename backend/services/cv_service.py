from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter


def analyze_image(contents: bytes) -> dict:
    """Screen image quality and content category without claiming unvalidated hazard detection."""
    try:
        original = Image.open(BytesIO(contents)).convert("RGB")
    except Exception:
        return {
            "imageAccepted": False,
            "contentCategory": "UNSUPPORTED_IMAGE",
            "imageQuality": "N/A",
            "contentScreening": "UNSUPPORTED_FORMAT",
            "landslideClassification": "NOT PERFORMED",
            "verificationMode": "AI-assisted image screening",
            "verificationConfidence": None,
            "classification": "Unclassified",
            "confidence": None,
            "severity": "NOT ASSESSED",
            "objects": ["unsupported file format or corrupt image"],
            "detectedIndicators": ["unsupported file format"],
            "descriptionMatch": False,
            "recommendedAction": "Uploaded file could not be processed as a valid image.",
            "modelSource": "image-quality-screening-only",
            "is_trained": False,
        }

    width, height = original.size
    image = original.copy()
    image.thumbnail((640, 640))
    array = np.asarray(image, dtype=np.float32) / 255.0

    gray_img = image.convert("L")
    gray_arr = np.asarray(gray_img, dtype=np.float32)

    # Blur detection via Laplacian variance
    if gray_arr.shape[0] > 4 and gray_arr.shape[1] > 4:
        laplacian = np.abs(
            gray_arr[1:-1, 2:] + gray_arr[1:-1, :-2] + gray_arr[2:, 1:-1] + gray_arr[:-2, 1:-1] - 4 * gray_arr[1:-1, 1:-1]
        )
        blur_var = float(laplacian.var())
    else:
        blur_var = 0.0

    edges = np.asarray(gray_img.filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0

    red = array[:, :, 0]
    green = array[:, :, 1]
    blue = array[:, :, 2]

    # Natural earth / vegetation / terrain color ratio
    earth_mask = (red > blue * 1.05) & (green > blue * 0.9) & (red > 0.12)
    earth_ratio = float(earth_mask.mean())

    dark_ratio = float((array.mean(axis=2) < 0.20).mean())
    bright_ratio = float((array.mean(axis=2) > 0.82).mean())
    edge_density = float((edges > 0.18).mean())

    # Text / Document / UI edge deltas (sharp orthogonal gradient changes)
    dx = np.abs(gray_arr[:, 1:] - gray_arr[:, :-1])
    dy = np.abs(gray_arr[1:, :] - gray_arr[:-1, :])
    sharp_h_edges = float((dy > 30).mean())
    sharp_v_edges = float((dx > 30).mean())

    indicators = []
    is_low_res = width < 320 or height < 240
    is_blurry = blur_var < 5.0 and not is_low_res
    is_dark = dark_ratio > 0.65
    is_overexposed = bright_ratio > 0.85 and earth_ratio >= 0.15

    is_screenshot = (
        (bright_ratio > 0.35 and earth_ratio < 0.15) or
        (sharp_h_edges + sharp_v_edges > 0.03 and earth_ratio < 0.15) or
        (edge_density > 0.03 and earth_ratio < 0.10 and (bright_ratio > 0.30 or dark_ratio > 0.40)) or
        (earth_ratio < 0.05 and (bright_ratio > 0.25 or (dark_ratio > 0.50 and (sharp_h_edges + sharp_v_edges > 0.01))))
    )

    if is_screenshot:
        content_category = "SCREENSHOT_OR_DOCUMENT"
        content_screening = "TEXT/SCREEN CONTENT DETECTED"
        image_quality = "Good" if not (is_low_res or is_blurry or is_dark) else "Poor"
        indicators.append("screenshot / document text content detected")
        recommended_action = "Please upload a clear photograph captured at the reported incident location. NexSolve's current image module performs image-quality/content screening only; it does not confirm landslides from photographs."
    elif is_low_res or is_blurry or is_dark or is_overexposed:
        content_category = "LOW_QUALITY_IMAGE"
        content_screening = "LOW_QUALITY_OR_BLURRY"
        image_quality = "Poor"
        if is_low_res: indicators.append("low resolution")
        if is_blurry: indicators.append("blurry focus")
        if is_dark: indicators.append("underexposed")
        if is_overexposed: indicators.append("overexposed")
        recommended_action = "Please provide a clearer, properly exposed photograph of the incident area for field assessment."
    else:
        content_category = "FIELD_PHOTO_CANDIDATE"
        content_screening = "NATURAL_FIELD_PHOTO"
        image_quality = "Good"
        indicators.append("image dimensions, exposure, and natural scene composition acceptable")
        recommended_action = "Image passed quality screening. NexSolve's current image module performs image-quality/content screening only; it does not confirm landslides from photographs."

    return {
        "imageAccepted": content_category == "FIELD_PHOTO_CANDIDATE",
        "contentCategory": content_category,
        "imageQuality": image_quality,
        "contentScreening": content_screening,
        "landslideClassification": "NOT PERFORMED",
        "verificationMode": "AI-assisted image screening",
        "verificationConfidence": None,
        "classification": "Unclassified",
        "confidence": None,
        "severity": "NOT ASSESSED",
        "objects": indicators,
        "detectedIndicators": indicators,
        "recommendedAction": recommended_action,
        "modelSource": "image-quality-screening-only",
        "is_trained": False,
    }

