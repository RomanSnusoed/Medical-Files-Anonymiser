from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageEnhance

WINDOWS_TESSERACT_PATHS = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
)


def _resolve_candidate(cmd: Optional[str]) -> Optional[str]:
    """Return a usable path to *cmd* if it exists, otherwise ``None``."""

    if not cmd:
        return None

    candidate = Path(cmd).expanduser()
    if candidate.is_file():
        return str(candidate)

    which_cmd = shutil.which(cmd)
    if which_cmd:
        return which_cmd

    return None


def resolve_tesseract_cmd() -> str:
    """Determine the path to the Tesseract executable.

    Priority order:
      1. ``TESSERACT_CMD`` environment variable.
      2. Existing ``pytesseract`` configuration.
      3. Common Windows installation directories.
      4. ``shutil.which('tesseract')``.

    Raises:
        FileNotFoundError: If no valid Tesseract executable can be found.
    """

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd is not None:
        resolved_env = _resolve_candidate(env_cmd)
        if resolved_env:
            return resolved_env
        raise FileNotFoundError(
            f"TESSERACT_CMD is set to '{env_cmd}', but that file does not exist."
        )

    current_setting = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
    resolved_current = _resolve_candidate(current_setting)
    if resolved_current:
        return resolved_current

    if os.name == "nt":
        for windows_path in WINDOWS_TESSERACT_PATHS:
            resolved_windows = _resolve_candidate(windows_path)
            if resolved_windows:
                return resolved_windows

    resolved_default = _resolve_candidate("tesseract")
    if resolved_default:
        return resolved_default

    raise FileNotFoundError(
        "Unable to locate the Tesseract executable. Install Tesseract or set the "
        "TESSERACT_CMD environment variable to its full path."
    )


def ensure_tesseract_cmd() -> str:
    """Ensure ``pytesseract`` is configured with a valid Tesseract executable."""

    resolved_cmd = resolve_tesseract_cmd()
    pytesseract.pytesseract.tesseract_cmd = resolved_cmd
    return resolved_cmd


def preprocess_image(image_path):
    """Preprocess the image for better OCR results."""

    img = Image.open(image_path)
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    img = img.convert("L")  # Convert to grayscale

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(4)  # Increase contrast
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.5)  # Increase brightness

    return img


def correct_image_orientation(image):
    """Detect and correct the orientation of *image* using Tesseract OSD."""

    ensure_tesseract_cmd()

    try:
        osd = pytesseract.image_to_osd(image)
        rotation_angle = int(re.search(r"Rotate: (\d+)", osd).group(1))
        if rotation_angle != 0:
            print(f"Rotating image by {rotation_angle} degrees")
            image = image.rotate(-rotation_angle, expand=True)
    except Exception as e:  # pragma: no cover - logging path
        print(f"Error detecting orientation: {e}")
    return image
