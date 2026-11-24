from pathlib import Path
from django.core.exceptions import ValidationError

ALLOWED_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".glb"}
def validate_upload_extension(upload):
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError("Uploads must be 10 MB or smaller.")
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Allowed uploads: JPG, PNG, WEBP, PDF and GLB.")
    signatures = {
        ".jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
        ".png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        ".pdf": lambda data: data.startswith(b"%PDF-"),
        ".glb": lambda data: data.startswith(b"glTF"),
    }
    position = upload.tell() if hasattr(upload, "tell") else None
    sample = upload.read(12)
    if position is not None: upload.seek(position)
    if not signatures[extension](sample):
        raise ValidationError("The uploaded file contents do not match its extension.")
