import base64
import io
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def file_to_base64(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')


def get_mime_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.mp4': 'video/mp4',
    }
    return mime_map.get(ext, 'application/octet-stream')


def make_data_uri(file_path: str) -> str:
    mime = get_mime_type(file_path)
    b64 = file_to_base64(file_path)
    return f"data:{mime};base64,{b64}"


def make_data_uri_from_bytes(data: bytes, mime_type: str) -> str:
    b64 = bytes_to_base64(data)
    return f"data:{mime_type};base64,{b64}"


def compress_image(image_data: bytes, max_kb: int = 2800, max_width: int = 900, max_height: int = 900) -> tuple[bytes, str]:
    if not HAS_PIL:
        return image_data, 'image/jpeg'

    img = Image.open(io.BytesIO(image_data))
    if img.mode in ('RGBA', 'LA', 'PA'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    w, h = img.size
    ratio = min(max_width / w, max_height / h, 1.0)
    if ratio < 1.0:
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    for quality in [85, 75, 65, 55, 45, 35, 25]:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        if buf.tell() / 1024 <= max_kb:
            return buf.getvalue(), 'image/jpeg'

    for scale in [0.7, 0.5, 0.4]:
        w2, h2 = img.size
        small = img.resize((int(w2 * scale), int(h2 * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        small.save(buf, format='JPEG', quality=40, optimize=True)
        if buf.tell() / 1024 <= max_kb:
            return buf.getvalue(), 'image/jpeg'

    buf = io.BytesIO()
    img.resize((400, 600), Image.LANCZOS).save(buf, format='JPEG', quality=30, optimize=True)
    return buf.getvalue(), 'image/jpeg'


def is_svg(filename: str) -> bool:
    return Path(filename).suffix.lower() == '.svg'


def is_pdf(filename: str) -> bool:
    return Path(filename).suffix.lower() == '.pdf'


def svg_to_data_uri(svg_data: bytes) -> str:
    b64 = base64.b64encode(svg_data).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64}"


def pdf_to_image(pdf_data: bytes, max_width: int = 900, max_height: int = 900) -> tuple[bytes, str]:
    if not HAS_FITZ:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF support. Install with: pip install PyMuPDF")
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = doc[0]
    zoom = min(max_width / page.rect.width, max_height / page.rect.height, 2.0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_data = pix.tobytes("png")
    doc.close()
    return compress_image(img_data, max_kb=2800, max_width=max_width, max_height=max_height)


def process_asset(data: bytes, filename: str) -> tuple[str, bytes, str]:
    """Process an asset file and return (data_uri, processed_bytes, mime_type).
    Handles SVG, PDF, and raster images."""
    if is_svg(filename):
        data_uri = svg_to_data_uri(data)
        return data_uri, data, 'image/svg+xml'
    elif is_pdf(filename):
        img_bytes, mime = pdf_to_image(data)
        data_uri = make_data_uri_from_bytes(img_bytes, mime)
        return data_uri, img_bytes, mime
    else:
        img_bytes, mime = compress_image(data)
        data_uri = make_data_uri_from_bytes(img_bytes, mime)
        return data_uri, img_bytes, mime
