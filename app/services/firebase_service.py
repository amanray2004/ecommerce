import uuid
from pathlib import Path
import shutil

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

try:
    import firebase_admin
    from firebase_admin import credentials, storage
except Exception:  # pragma: no cover
    firebase_admin = None
    credentials = None
    storage = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK once during startup."""

    settings = get_settings()
    if not settings.firebase_bucket or not settings.firebase_credentials_path:
        return

    if firebase_admin is None:
        raise RuntimeError("firebase-admin package is not installed.")

    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred, {"storageBucket": settings.firebase_bucket})


def upload_product_image(tenant_name: str, image: UploadFile) -> tuple[str, str]:
    """Upload image and return (public_url, object_path)."""

    settings = get_settings()
    ext = image.filename.rsplit(".", 1)[-1].lower() if image.filename and "." in image.filename else "jpg"
    object_rel_path = f"{tenant_name}/products/{uuid.uuid4()}.{ext}"

    # Dev fallback: store images locally when Firebase is not configured.
    if firebase_admin is None or not firebase_admin._apps:
        uploads_dir = Path("uploads")
        local_path = uploads_dir / object_rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as output:
            shutil.copyfileobj(image.file, output)
        return f"/uploads/{object_rel_path}", f"local:{object_rel_path}"

    object_path = object_rel_path

    bucket = storage.bucket(settings.firebase_bucket)
    blob = bucket.blob(object_path)
    blob.upload_from_file(image.file, content_type=image.content_type or "image/jpeg")
    blob.make_public()

    return blob.public_url, object_path


def delete_product_image(object_path: str) -> None:
    if not object_path:
        return

    if object_path.startswith("local:"):
        local_rel = object_path.split("local:", 1)[1]
        local_file = Path("uploads") / local_rel
        if local_file.exists():
            local_file.unlink()
        return

    settings = get_settings()
    if firebase_admin is None or not firebase_admin._apps:
        return

    bucket = storage.bucket(settings.firebase_bucket)
    blob = bucket.blob(object_path)
    blob.delete()
