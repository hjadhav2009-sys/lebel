import hashlib
from pathlib import Path

from app.renderers.base import RendererError

FONT_PATHS={
    "mms_default_sans":[
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans.ttf"),
    ]
}


def resolve_font(font_key:str)->dict:
    if font_key not in FONT_PATHS:raise RendererError("FONT_NOT_AVAILABLE",f"Unapproved font key: {font_key}")
    path=next((item for item in FONT_PATHS[font_key] if item.is_file()),None)
    if not path:raise RendererError("FONT_NOT_AVAILABLE",f"Backend font for {font_key} is unavailable.")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return {"font_key":font_key,"font_path":str(path),"font_family":"DejaVu Sans","font_sha256":digest}
