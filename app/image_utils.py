"""
Resize + compress uploaded images before saving.
Keeps file sizes small while preserving enough quality for display.
"""
from io import BytesIO
from PIL import Image

# Max dimensions per use-case (width, height)
SIZES = {
    "avatar":  (400,  400),
    "banner":  (1200, 500),
    "market":  (1200, 600),
}
QUALITY = 82


def process_image(data: bytes, kind: str) -> tuple[bytes, str]:
    """
    Resize and recompress image bytes.
    Returns (compressed_bytes, '.jpg') — always outputs JPEG (except animated GIF).
    """
    img = Image.open(BytesIO(data))

    # Preserve animated GIFs as-is
    if getattr(img, "is_animated", False):
        return data, ".gif"

    # Convert palette / RGBA → RGB for JPEG output
    if img.mode in ("P", "RGBA", "LA"):
        bg = Image.new("RGB", img.size, (10, 10, 12))
        if img.mode in ("RGBA", "LA"):
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    max_w, max_h = SIZES.get(kind, (1200, 600))
    img.thumbnail((max_w, max_h), Image.LANCZOS)

    out = BytesIO()
    img.save(out, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
    return out.getvalue(), ".jpg"
